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
  `probe-result.txt` in the app's external files directory. It also keeps
  `probe-log.txt` in the same directory: a crash-proof error log — a run
  section is opened before the probe starts, every stdout/stderr chunk is
  flushed into it as it arrives, signal handlers append a CRASH line if the
  probe dies by a signal, and a clean exit records its code (the file is
  append-only across runs, rotated past 256 KB).
- `ProbeMainActivity.java` — a plain launcher screen: one button runs the
  probe as a child `SDLActivity`; on return it displays
  `probe-result.txt` for screenshotting. If a run was attempted but left
  no fresh result (a native crash kills the process before the result can
  be written), it shows the `probe-log.txt` tail instead, under a
  "last run crashed" label; a **Show error log** button reads the log at
  any time. The launcher appends its own timestamped lines to the log.
- SDL is upstream's pin, **3.4.16** (the exact archive
  `Tools/vendor.sh` fetches; the workflow verifies its SHA-256), built
  shared for arm64-v8a; SDLActivity loads `SDL3` then `main`.
- The SDL **Java** layer is a dispatch-time choice: `host` (default) uses
  the game shell's staged SDL 3.4.2 Java from the pinned MYSOREZ tree —
  whether that Java drives the 3.4.16 native library is itself one of
  C0's questions; `upstream` uses SDL 3.4.16's own Java.
- The **device-creation mode** is a second dispatch-time choice,
  `device_mode`: `plain` (default) is the probe exactly as upstream
  wrote it — `SDL_CreateGPUDevice` with SDL's default requirements,
  which include the Vulkan features `depthClamp` and
  `shaderClipDistance`. `compat` compiles the probe TU with
  `-DSDL_CreateGPUDevice=probe_compat_create_gpu_device`, routing its
  call into the shim, which creates the device via
  `SDL_CreateGPUDeviceWithProperties` with the depth-clamping and
  clip-distance feature properties set false (SDL_gpu.h:2380–2381) —
  SDL's documented remedy for GPUs that lack them, like the owner's
  Mali-G52 (record §8). The probe source stays byte-identical in both
  modes, and the probe log's run header names the mode that ran.
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
results screen showing the capability table — screenshot it. If the app
instead dies and comes back with a "last run crashed" screen, screenshot
that: it is the dead run's `probe-log.txt`, partial table and crash line
included — that log is the evidence the run existed to produce.
