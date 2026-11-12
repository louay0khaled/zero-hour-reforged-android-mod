# Stage C, slices C0 + C2 — Reforged GPU probe / renderer harness APK

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

## Slice C2 — the renderer selfcheck harness

With the workflow input `harness=renderer`, the same APK also carries
the Reforged engine's **own** renderer selfchecks, so C2 can prove the
engine's real renderer initialises on the phone — not a proxy:

- Payloads: upstream's `sdl_gpu_frame_selfcheck` (creates a GPU device
  through `SdlGpuFrame::Create` — the engine's production call site,
  carrying the C1 §5 Android compat fix — clears, readback value checks,
  depth-format fallback, pipeline/sampler creation, offscreen Present)
  and `sdl_gpu_depth_format_selfcheck` (the depth-format selection the
  C0 table priced; D24S8 preferred). Both are existing upstream CMake
  targets linking `posixd3d9`.
- Built from source in CI: the workflow checks out the pinned Reforged
  tree (`61dbc59`), applies the formalised C1 patch set in `patches/`
  (`reforged-c1-android.patch`, byte-equivalent to the C1 compile-proof
  diff; `gamespy-android-pthread.patch` into the vendored GameSpy tree
  after `vendor.sh`), builds a host `build_fingerprint` (C1 blocker B4),
  and compiles both targets with NDK r27c — the exact sequence rehearsed
  locally before this wiring landed (record: stage-c-c1-plan.md §7).
- Packaging: the two binaries ride in the APK as
  `libsdl_gpu_frame_selfcheck.so` / `libsdl_gpu_depth_format_selfcheck.so`
  next to `libmain.so` (the manifest's `extractNativeLibs=true` makes
  them real executable files). They are AArch64 PIEs needing only system
  libraries.
- Running: the launcher shows a **Run renderer selfcheck** button only
  when the payloads are packaged. A tap writes `renderer` into
  `harness-mode.txt`; the shim then runs both payloads as **child
  processes** (frame first) with `SDL_VIDEODRIVER=offscreen`, teeing
  their output into the same `probe-result.txt` / `probe-log.txt`
  plumbing, and the run's exit code is the frame selfcheck's when
  nonzero, else the depth one's (0 pass, 1 fail, 77 skip — the
  payloads' own convention). Child processes, not in-process linking:
  the engine closure carries its own vendored, statically linked SDL
  while the harness runs on the shared SDL — two SDL implementations in
  one process is the hazard the stage-C plan flags — and a dying payload
  cannot take the harness (and its log) down with it. Deviation from
  the §6 sketch recorded in stage-c-c1-plan.md §7.
- Frame-entry fix (first device run, 2026-11-12): the depth payload
  passed (exit 0) but the frame payload **skipped at startup with
  exit 77** — `SDL_Init: Application didn't initialize properly, did
  you include SDL_main.h…`. Cause (record: stage-c-c1-plan.md §8):
  on Android SDL3 is built with `SDL_MAIN_NEEDED`, so `SDL_Init`
  refuses until SDL's own entry trampoline has set the main-ready
  flag — and the bare child process has no SDLActivity/JNI
  trampoline. (The depth payload never initialises SDL, which is
  why it was unaffected.) Fix: a third patch in `patches/`,
  `reforged-frame-selfcheck-entry.patch`, applied after the C1 set —
  it renames the test TU's `main` to a body function (that one TU
  only) and adds a small launcher TU whose entry calls
  `SDL_SetMainReady()` first, the one act of SDL's Android
  trampoline an offscreen test needs. Android-guarded in CMake, so
  other platforms' builds are untouched. The renderer re-run uses
  the same dispatch inputs as the first run (below); PASS is the
  closing line `payload exit codes: frame 0, depth 0`.
- `device_mode` does **not** apply to the payloads: they create their
  device inside the engine, through the fixed call site. The log's
  harness line says so on every renderer run.

## Build

Actions → **Build Reforged GPU Probe (stage C0/C2)** → Run workflow:

- C0 probe: defaults (`harness=probe`) → artifact **`ReforgedGpuProbe-apk`**.
- C2 renderer: `harness=renderer`, `sdl_java=upstream`,
  `device_mode=plain` → artifact **`ReforgedRendererSelfcheck-apk`**
  (same APK package; installs over the C0 build).

The APK is debug-signed on purpose: it is a disposable probe, not the game.

## On the phone

Install the APK, open **Reforged GPU Probe**, tap **Run GPU probe**. The
probe screen is blank while it works; when it finishes you return to the
results screen showing the capability table — screenshot it. If the app
instead dies and comes back with a "last run crashed" screen, screenshot
that: it is the dead run's `probe-log.txt`, partial table and crash line
included — that log is the evidence the run existed to produce.

On a renderer build there is a second button, **Run renderer
selfcheck**: the screen returns showing the selfchecks' output and
verdict lines (per-payload exit codes at the end; combined exit 0 =
PASS). Screenshot that screen — or, if anything died, the error-log
screen it falls back to.
