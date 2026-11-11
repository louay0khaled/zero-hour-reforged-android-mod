# CI overlay — how the APK is built on GitHub Actions

The Zero Hour Reforged APK is **not** built from a copy of the game engine
in this repo. The engine tree (MYSOREZ's GeneralsZH Android port) is several
GB; instead, `.github/workflows/build-apk.yml` rebuilds it from upstream on
every run and applies this repo's small overlay on top:

1. **Check out** `MYSOREZ/GeneralsZH-Android-Port` at the pinned commit
   `a520ed1` (plus its DXVK submodule), and check out this repo into
   `reforged-overlay/`.
2. **Apply the overlay** (this folder):
   - `patches/engine-carryover.patch` — the locomotor carry-over in
     `ThingTemplate.cpp` (a replaced AI module no longer loses the object's
     Locomotor sets), ported from the Reforged engine.
   - `patches/smooth-motion.patch` — smooth motion (render interpolation),
     ported from the Reforged engine and applied after the carry-over
     patch: on a display faster than the 30 Hz logic, models are drawn
     between their last two logic transforms and restored right after the
     render, so gameplay and replay checksums are untouched. On by
     default; `-nosmoothmotion` opts out for a run.
  - `patches/perf-graphics.patch` — the M2 performance + graphics bundle
     (v1.3), applied after smooth-motion: the Reforged lighting style
     ("the light has weight": each map's lights rebalanced toward the sun
     as the map loads; default on, `LightingStyle` INI field or
     `-lighting classic` restores 2003 light), the tree buffer count
     1 → 8 and the bridge vertex buffer 12000 → 32000 (dense woodland and
     long bridges no longer blink out / go missing), and per-program
     uniform caching in the GLES translator (uniform state is no longer
     re-uploaded on every program switch). Presentation-only throughout:
     replay checksums are byte-identical to v1.2.
   - `patches/hitch-removal.patch` — the M2 wave-3 hitch bundle (v1.4),
     applied after perf-graphics: the audio cache floor rises 4 MB → 64 MB
     in both audio managers (upstream measured 3,508 disk re-reads per match
     against the retail floor, ~35 with the new one), and spent dynamic
     lights (muzzle flashes) are pooled and stepped on the logic clock
     instead of being allocated per shot and faded per render frame.
     Playback/presentation only; replay checksums byte-identical to v1.3.
   - `patches/60foundations.patch` — the M2 wave-6 foundations (v1.4),
     applied after hitch-removal: the Reforged 60-steps conversion call
     sites (slices 6a–6e) in the 30-steps engine with the flip define OFF —
     every conversion is an algebraic identity at the retail rate, so logic
     is bit-identical to v1.3.
   - `patches/60flip.patch` — the M2 wave-6 flip (v1.5, slice 6f), applied
     after 60foundations: the `REFORGED_60_STEPS` CMake option and the
     GameCommon.h rate branch it drives (LOGICFRAMES_PER_SECOND 60 in the
     flipped build only; WWSyncPerSecond untouched), the remaining deferred
     conversion items (the fire-cycle hold, the FireWeaponCollide
     once-a-retail-frame gate, the parseFrictionPerSec divisor switch —
     all inert or identical at the retail rate), the RF60 version stamp,
     and the GameState save rate stamp that makes each engine refuse the
     other's saves cleanly. The workflow builds the tree twice: standard
     (libmain.so) and flipped (libmainrf60.so).
   - `patches/package-android-zh-gradle-task.patch` — lets the upstream
     packaging script run `assembleRelease` (via `GX_GRADLE_TASK`), checks
     the release output path, and adds the `GX_REFORGED60_LIB` knob that
     stages the flipped engine as `libmainrf60.so` (never `libmain60.so`).
   - `apply-surgery.py` — new applicationId `com.louay.zerohour.reforged`,
     version 6 / "1.5", the native hardcoded data paths repointed to the
     new id, the "Zero Hour Reforged" label in all locales, the OTA
     update channel pointed at this repo (so upstream engine updates can
     never overwrite the patched build), and (phase 1e) the Reforged
     60-steps launcher switch: pref `reforged_60_steps` (default OFF)
     replacing the dead Simulation Rate card on the Graphics tab, shown
     only when Zero Hour is selected and `libmainrf60.so` is in the APK.
   - `apply-phase2.py` — bundles the two Reforged data packages as APK
     assets and adds the launcher code that installs + enables them as
     mods on first run (fixes first, balance last = highest priority).
     Both assets are sha256-verified by the script before use:
     - fixes: `ci/assets/!ReforgedFixes-v3.big` — the *engine-native*
       variant of the fixes package (the data-side locomotor restatements
       removed; the patched engine carries the sets natively). **Not** the
       same bytes as `packages/!ReforgedFixes-v3.big`, which targets the
       *unpatched* engine.
     - balance: `ci/assets/!ReforgedBalance-v2.big` — the *engine-native*
       variant of the balance package (the v2 content with its data-side
       locomotor restatement blocks removed; on the patched engine those
       restatements throw during INI load and the game does not start).
       **Not** the same bytes as `packages/!ReforgedBalance-v2.big`, which
       stays byte-identical for the *unpatched* engine.
3. **Build** exactly like upstream's own `build-android.yml` (same pinned
   NDK/Gradle/vcpkg/CMake preset `android-vulkan`, arm64), with the v1
   build's target list (both `libmain.so` and `libgenerals.so`) and strip
   list, then package a release APK. Since v1.5 the Zero Hour engine is
   built a second time with `REFORGED_60_STEPS=ON` (same build dir,
   sequential; the standard `libmain.so` is stashed and restored around
   the pass) and packaged as `libmainrf60.so`; the APK guard requires
   exactly `libmain.so` + `libmainrf60.so` + `libgenerals.so` and bans
   every other `*60.so` name.
4. **Upload** the APK as the workflow artifact **`ZeroHourReforged-apk`**
   (plus symbol tables for both Zero Hour engines for crash
   symbolization, and build logs).

## Signing

Signing deliberately stays **local**: the CI artifact is the AGP release
output signed with the project's own committed debug keystore — the exact
pre-signing state of the local v1 build. No keystore or secret is stored
on GitHub. Publishing a version = download the artifact, re-sign it
locally with the dedicated `zh-reforged` keystore, and attach it to a
GitHub Release.

## Building the next version

Actions tab → **Build Zero Hour Reforged APK** → *Run workflow*. For a new
release, set the `version_code` / `version_name` inputs (they must move
together and versionCode must increase); leave them blank to rebuild the
committed defaults. When the run finishes, download the
`ZeroHourReforged-apk` artifact, verify, re-sign locally, and publish.
