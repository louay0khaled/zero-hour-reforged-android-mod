# CI overlay — how the APK is built on GitHub Actions

The Zero Hour Reforged APK is **not** built from a copy of the game engine
in this repo. The engine tree (MYSOREZ's GeneralsZH Android port) is several
GB; instead, `.github/workflows/build-apk.yml` rebuilds it from upstream on
every run and applies this repo's small overlay on top:

1. **Check out** `MYSOREZ/GeneralsZH-Android-Port` at the pinned commit
   `a520ed1` (plus its DXVK submodule) **twice** — the base tree and
   `reforged-src/`, our own engine tree — and check out this repo into
   `reforged-overlay/`. Since v1.9 the build is **separated**: the base
   tree receives identity surgery + our launcher page only and builds the
   host's own engines their way; the engine patches go to `reforged-src/`
   alone, which builds our two engines (the 60-steps engine and, since
   v1.10, the enhanced standard engine).
2. **Apply the overlay** (this folder) — the ten patches to `reforged-src/`;
   the surgery + phase 2 to the base tree (the surgery's phase 1b also
   runs, in paths mode, on `reforged-src/`). One exception: the
   packaging-script patch applies to **both** trees — it is build tooling
   only (the script ships nothing, touches no engine or launcher code),
   and the base tree cannot be packaged without it (the pristine script
   has no `assembleRelease` knob and no staging knob for
   `libmainrf60.so`):
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
     other's saves cleanly. Since v1.9 `reforged-src/` is configured with
     the flip ON and its `libmain.so` output ships as `libmainrf60.so`;
     since v1.10 the same build dir is then reconfigured with the flip
     OFF — the tree's existing standard configuration — and that output
     ships as `libmainrf.so`.
   - `patches/step-perf.patch` — the M2 wave-7 per-step perf ports
     (v1.6), applied after the gradle-task patch: four upstream-measured,
     checksum-identical logic/client savings (CRC register-local fold,
     by-template counting index, GPS Scrambler search short-circuit,
     projectile hide/show cache) that cut the per-step cost whose excess
     halves the 60-steps rate in dense battles.
   - `patches/speed-pacing-fix.patch` — the M2 wave-7 pacing fix (v1.6):
     every hard-coded retail-30 session/slider pace now keys off the
     build's own LOGICFRAMES_PER_SECOND, so a same-rate 60-steps LAN
     session runs at normal game speed instead of half, and the speed
     slider stays a relative control in both engines. Value-identical in
     the 30-steps build.
   - `patches/rf60-frontend.patch` — the M2 wave-8 front-end cadence fix
     (v1.7), applied last: in the flipped build only, the shell branch of
     GameEngine::update asks the frame pacer for the build's own
     LOGICFRAMES_PER_SECOND, so menus, settings and the online lobby run
     at 60 like the host's own 60 Hz build (which gets there by raising
     GENERALS_ONLINE_HIGH_FPS_LIMIT -- a macro this build must not raise:
     it also seeds GeneralsOnline session latency data and is
     static_asserted equal to WWSyncPerSecond). The standard library
     compiles the pristine line, unchanged.
   - `patches/package-android-zh-gradle-task.patch` — lets the upstream
     packaging script run `assembleRelease` (via `GX_GRADLE_TASK`), checks
     the release output path, and adds the `GX_REFORGED60_LIB` knob that
     stages the flipped engine as `libmainrf60.so` (never `libmain60.so`)
     and the `GX_REFORGED_LIB` knob (v1.10) that stages the standard build
     as `libmainrf.so` (never `libmain.so` — in the separated build that
     name belongs to the host's own engine; the launcher loads ours only
     through the Reforged page's enhanced-engine switch).
   - `apply-surgery.py` — runs in two modes. On the **base tree**
     (`full`, the default): new applicationId
     `com.louay.zerohour.reforged`, version 11 / "1.10", the native
     hardcoded data paths repointed to the new id, the "Zero Hour
     Reforged" label in all locales, the OTA update channel pointed at
     this repo (so upstream engine updates can never overwrite this
     build), and (phase 1e, v1.9) the **Reforged page**: a sixth
     bottom-navigation tab that is ours alone, carrying the 60-steps
     engine switch (pref `reforged_60_steps`, default OFF — the card
     that sat on the Graphics tab in v1.5–v1.8, moved here), the
     enhanced standard engine switch (pref `reforged_enhanced_30`,
     default OFF — v1.10; the two engine switches are alternatives and
     engaging one visibly disengages the other) and the bundled mod
     switch; their pages are untouched, so the Simulation Rate card
     works again. `GeneralsZHActivity.getLibraries()` keeps the host's
     own sim_hz selection with our engaged engines taking precedence
     (60-steps first, then the enhanced standard — they are the
     player's explicit choices on our page);
     `GeneralsOnlineSession.clientId()` keeps the host's own sim_hz
     keying with a guard in front for each of our engines, so their
     states announce the id those engines actually compiled in
     (`gen_online_30hz`); and the upstream UpdateManager
     engine-override load path stays removed from `GeneralsZHActivity`
     — the APK's engines are the only engines. On the **Reforged
     tree** (`REFORGED_SURGERY_MODE=paths`): phase 1b only, because
     that tree's engine binaries carry the same hardcoded old-id data
     paths and must resolve this app's files directory.
   - `apply-phase2.py` — bundles the Reforged data as ONE merged package
     (`ci/assets/!Reforged-v1.big`, sha256-verified by the script before
     use) and adds the launcher code that installs + enables it as a single
     mod on first run. The merged archive carries every path of the two
     engine-native packages it replaces (fixes v3 + balance v2), with the
     balance bytes winning the 102 shared paths — byte-identical per path
     to the old two-mod stack (proof in the project record). On installs
     that still hold the pre-merge pair, the generated code removes the
     app-installed `ReforgedFixes` / `ReforgedBalance` folders and their
     stored-order entries once the merged folder is in place. The pair was
     merged because the launcher's mod analysis warned about the two mods
     on every visit (they share INI files by design). Since v1.9 the
     generated code also carries the Online Mode settlement and the
     Reforged page's mod-switch helpers: `migrateOnlineModeState` runs
     at the head of `ensureBundledReforgedData` and lands a v1.7/v1.8
     install that was left with Online Mode on in exactly the state
     leaving the mode would have produced — the mod returns to its
     snapshotted switch state through the same stored-order mechanism
     the Mods screen uses, and both leftover prefs are removed — while
     `bundledModEnabled` / `setBundledModEnabled` read and write that
     same stored-order state for the page's switch, so the page and the
     Mods screen are two handles on one state, never two states.
3. **Build** exactly like upstream's own `build-android.yml` (same pinned
   NDK/Gradle/vcpkg/CMake preset `android-vulkan`, arm64), with the v1
   build's target list (both `libmain.so` and `libgenerals.so`) and strip
   list, then package a release APK. Since v1.9 the base tree builds
   **their way**: pass 1 with `SAGE_HIGH_FPS_SIM=ON` builds both game
   targets and sets `libmain60.so` + `libgenerals60.so` aside; pass 2
   reconfigures standard and builds the shipped `libmain.so` +
   `libgenerals.so` + DXVK + hooks — upstream's `build-dual-hz.sh`
   shape, with the packaging script's own pristine `GX_SECOND_GAME_LIB`
   / `GX_SECOND_BASE_GAME_LIB` knobs staging the 60 Hz pair. Our engines
   are built separately in `reforged-src`, which is configured twice:
   with `REFORGED_60_STEPS=ON` (staged as `libmainrf60.so` through the
   overlay's `GX_REFORGED60_LIB` knob) and then with the flip OFF
   (staged as `libmainrf.so` through `GX_REFORGED_LIB`). The APK guard
   requires exactly `libmain.so` + `libmain60.so` + `libgenerals.so` +
   `libgenerals60.so` + `libmainrf60.so` + `libmainrf.so`; the `*60.so`
   set must be exactly
   `{libgenerals60.so, libmain60.so, libmainrf60.so}`.
4. **Upload** the APK as the workflow artifact **`ZeroHourReforged-apk`**
   (plus symbol tables for all six engines for crash symbolization,
   and build logs).

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
