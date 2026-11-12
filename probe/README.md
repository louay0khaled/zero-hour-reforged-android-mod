# Stage C, slice C0 — Reforged GPU probe APK

A throwaway Android app (`com.louay.zerohour.gpuprobe`) whose only job is to
run Reforged's own GPU capability probe on a real phone and show the table.
It answers stage C's gating question — can the owner's Mali-G52 meet
Reforged's SDL-GPU (Vulkan) renderer requirements — before any engine code
is touched. Full record: the project's
`hidden_files/stage-c-c0-probe.md`.

## What runs

- `sdl_gpu_probe.cpp` — upstream's probe, **byte-identical** to
  `GeneralsMD/Code/Tests/sdl_gpu_probe.cpp` in
  olcayseygan/cncgeneralszh-reforged @ `61dbc59`
  (SHA-256 `dc8bbf25bfd6153139cb744b600782629faa90a0320aa05cf11de0f26a5d28f0`;
  the workflow re-verifies the hash before building). It creates an SDL GPU
  device and reports driver/name/version, the sampled/target/depth formats
  the game needs (BC1/BC2/BC3 for the DDS art, B8G8R8A8, D24S8/D32S8), MSAA
  sample counts, and swapchain format/present modes on a claimed window.
- `gpu_probe_shim.cpp` — the Android harness (scaffolding only): provides
  `SDL_main`, invokes the probe (its `main` is renamed to `probe_main` at
  compile time), captures its stdout, mirrors it to logcat and writes it to
  `probe-result.txt` in the app's external files directory.
- `ProbeMainActivity.java` — a plain launcher screen: one button runs the
  probe as a child `SDLActivity`; on return it displays
  `probe-result.txt` for screenshotting.
- SDL is upstream's pin, **3.4.16** (the exact archive
  `Tools/vendor.sh` fetches; the workflow verifies its SHA-256), built
  shared for arm64-v8a; SDLActivity loads `SDL3` then `main`.
- The SDL **Java** layer is a dispatch-time choice: `host` (default) uses
  the game shell's staged SDL 3.4.2 Java from the pinned MYSOREZ tree —
  whether that Java drives the 3.4.16 native library is itself one of
  C0's questions; `upstream` uses SDL 3.4.16's own Java.
- Side artefact: `test_detround.cpp` + `include/Lib/DetRound.h` (also
  byte-identical, hash-pinned) are compiled in CI with the NDK clang and
  Reforged's determinism flags — the plan's §3.12 spelling check.

## Build

Actions → **Build Reforged GPU Probe (stage C0)** → Run workflow
(`sdl_java` = `host` first) → artifact **`ReforgedGpuProbe-apk`**.
The APK is debug-signed on purpose: it is a disposable probe, not the game.

## On the phone

Install the APK, open **Reforged GPU Probe**, tap **Run GPU probe**. The
probe screen is blank while it works; when it finishes you return to the
results screen showing the capability table — screenshot it.
