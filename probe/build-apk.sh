#!/usr/bin/env bash
# Stage C, slice C0 — package the probe APK by hand (aapt2 + d8 + zipalign +
# apksigner) from the CMake-built native libraries. No Gradle: for a
# throwaway two-activity app the manual pipeline has no version surface.
#
# Required environment:
#   PROBE_DIR         this directory (AndroidManifest.xml, ProbeMainActivity.java)
#   JAVA_SRC_DIR      directory containing org/libsdl/app/*.java (the SDL Java
#                     layer selected by the workflow: host-staged or upstream)
#   NATIVE_BUILD_DIR  CMake build tree holding libmain.so and libSDL3.so
#   NDK_HOME          Android NDK root (for libc++_shared.so)
#   ANDROID_JAR       path to platforms/android-34/android.jar
#   BUILD_TOOLS       Android build-tools dir (aapt2, d8, zipalign, apksigner)
#   OUT_APK           output APK path
# Optional environment:
#   PAYLOAD_DIR       stage C2: directory holding the engine selfcheck
#                     payloads under their final lib*.so names; every file
#                     in it is packaged into lib/arm64-v8a/ next to
#                     libmain.so. The shim finds and executes the depth
#                     payload; the frame payload is a shared library its
#                     own SDLActivity (FrameCheckActivity) loads.
#                     A renderer build without its payloads is a broken
#                     artifact, so a set-but-missing/empty PAYLOAD_DIR
#                     fails the packaging loudly.
set -euo pipefail

for v in PROBE_DIR JAVA_SRC_DIR NATIVE_BUILD_DIR NDK_HOME ANDROID_JAR BUILD_TOOLS OUT_APK; do
    if [ -z "${!v:-}" ]; then echo "build-apk.sh: $v is not set" >&2; exit 1; fi
done

# The selected SDL Java layer must actually be on disk. Probe workflow
# run #1 died at the find in step 1 because JAVA_SRC_DIR pointed at the
# host repo's android/app/src/main/java-sdl — a generated, gitignored
# directory that a fresh checkout never contains (the workflow now stages
# it itself). Fail here with a readable message instead of find's bare one.
if [ ! -d "$JAVA_SRC_DIR" ]; then
    echo "build-apk.sh: JAVA_SRC_DIR does not exist: $JAVA_SRC_DIR" >&2; exit 1
fi
if ! find "$JAVA_SRC_DIR" -name 'SDLActivity.java' -type f | grep -q .; then
    echo "build-apk.sh: no SDLActivity.java under JAVA_SRC_DIR: $JAVA_SRC_DIR" >&2; exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

LIBMAIN="$(find "$NATIVE_BUILD_DIR" -name libmain.so -type f | head -n 1)"
LIBSDL="$(find "$NATIVE_BUILD_DIR" -name libSDL3.so -type f | head -n 1)"
LIBCXX="$NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so"
for f in "$LIBMAIN" "$LIBSDL" "$LIBCXX"; do
    if [ ! -f "$f" ]; then echo "build-apk.sh: missing native library: $f" >&2; exit 1; fi
done
echo "native libs:"
ls -la "$LIBMAIN" "$LIBSDL" "$LIBCXX"

PAYLOADS=()
if [ -n "${PAYLOAD_DIR:-}" ]; then
    if [ ! -d "$PAYLOAD_DIR" ]; then
        echo "build-apk.sh: PAYLOAD_DIR does not exist: $PAYLOAD_DIR" >&2; exit 1
    fi
    while IFS= read -r p; do PAYLOADS+=("$p"); done < <(find "$PAYLOAD_DIR" -maxdepth 1 -type f | sort)
    if [ "${#PAYLOADS[@]}" -eq 0 ]; then
        echo "build-apk.sh: PAYLOAD_DIR is empty: $PAYLOAD_DIR" >&2; exit 1
    fi
    echo "payload libs (stage C2 renderer selfchecks):"
    ls -la "${PAYLOADS[@]}"
fi

# 1) Java: launcher activity + the selected SDL Java layer.
mkdir -p "$WORK/classes"
find "$JAVA_SRC_DIR" -name '*.java' > "$WORK/sources.txt"
echo "$PROBE_DIR/ProbeMainActivity.java" >> "$WORK/sources.txt"
echo "$PROBE_DIR/FrameCheckActivity.java" >> "$WORK/sources.txt"
echo "java sources:"; cat "$WORK/sources.txt"
JAVAC_CP="$ANDROID_JAR"
if [ -n "${EXTRA_CP:-}" ]; then JAVAC_CP="$JAVAC_CP:$EXTRA_CP"; fi
javac -source 8 -target 8 -cp "$JAVAC_CP" -d "$WORK/classes" @"$WORK/sources.txt"

# 2) Dex. Notes from local verification (2026-11-12): build-tools 34.0.0's
#    d8 (R8 8.2.2-dev) dies with an internal NullPointerException on these
#    SDL classes, so the workflow supplies a pinned standalone R8 jar
#    (R8_JAR, hash-verified) and dexing runs through it; d8 also rejects a
#    bare classes directory, so the classes go in as a jar. EXTRA_DEX_JARS,
#    when set, adds library jars whose classes the app references at
#    runtime — the host-staged SDL Java needs AndroidX Core's WindowCompat.
(cd "$WORK/classes" && zip -q -r "$WORK/app-classes.jar" .)
mkdir -p "$WORK/dex" # R8 requires the --output directory to exist already
DEX_INPUTS=("$WORK/app-classes.jar")
if [ -n "${EXTRA_DEX_JARS:-}" ]; then
    # shellcheck disable=SC2206
    DEX_INPUTS+=($EXTRA_DEX_JARS)
fi
if [ -n "${R8_JAR:-}" ]; then
    java -cp "$R8_JAR" com.android.tools.r8.D8 --min-api 28 --output "$WORK/dex" "${DEX_INPUTS[@]}"
else
    "$BUILD_TOOLS/d8" --min-api 28 --output "$WORK/dex" "${DEX_INPUTS[@]}"
fi

# 3) Base APK from the manifest, then add dex + native libs.
"$BUILD_TOOLS/aapt2" link -o "$WORK/probe-unsigned.apk" \
    --manifest "$PROBE_DIR/AndroidManifest.xml" \
    -I "$ANDROID_JAR" --min-sdk-version 28 --target-sdk-version 34
(
    cd "$WORK"
    zip -q probe-unsigned.apk -j dex/classes.dex
    mkdir -p lib/arm64-v8a
    cp "$LIBMAIN" "$LIBSDL" "$LIBCXX" lib/arm64-v8a/
    if [ "${#PAYLOADS[@]}" -gt 0 ]; then
        cp "${PAYLOADS[@]}" lib/arm64-v8a/
    fi
    zip -q -r probe-unsigned.apk lib
)

# 4) Align and debug-sign (throwaway probe: the owner's signing hold covers
#    the game, not this disposable capability test).
"$BUILD_TOOLS/zipalign" -f -p 4 "$WORK/probe-unsigned.apk" "$WORK/probe-aligned.apk"
keytool -genkeypair -keystore "$WORK/debug.keystore" -alias androiddebugkey \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass android -keypass android \
    -dname "CN=Android Debug,O=Android,C=US" > /dev/null 2>&1
"$BUILD_TOOLS/apksigner" sign --ks "$WORK/debug.keystore" \
    --ks-pass pass:android --key-pass pass:android \
    --out "$OUT_APK" "$WORK/probe-aligned.apk"

# 5) Loud verification of the product: signature, identity, contents.
"$BUILD_TOOLS/apksigner" verify "$OUT_APK"
"$BUILD_TOOLS/aapt2" dump badging "$OUT_APK" | head -n 6
unzip -l "$OUT_APK"
sha256sum "$OUT_APK"
