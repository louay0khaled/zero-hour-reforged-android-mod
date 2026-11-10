# Local Testbed Report — MYSOREZ engine built & run locally (no phone)

Date: 2026-11-10. Engine source: MYSOREZ/GeneralsZH-Android-Port @ **a520ed1** (same HEAD as the phone build lineage).
Testbed root: `~/workspace/projects/reforged-android/testbed/` (source `src/`, runtime `runtime/`, logs `runs/`, notes `NOTES.md`).

## 1. Build outcome — SUCCESS

- Full tree obtained despite a failed 713 MB GitHub clone (TLS disconnect): the tree was reconstructed from the
  audit clone's blob:none object store (local fetch of commit a520ed1 + checkout; all blobs were already local).
  No submodules are needed for the Linux build (the DXVK fork submodule is iOS/Android-only; Linux uses FetchContent).
- Dependencies: CI apt list from `.github/workflows/build-linux.yml` installed (note: apt only works here with
  `Acquire::ForceIPv4=true` — default IPv6 stalls). vcpkg bootstrapped at the CI-pinned commit into
  `testbed/vcpkg/` (the first bootstrap in `/opt/vcpkg` was wiped by a VM restart; the restart also rolled back
  the apt packages once — the platform's intent-replay restored them).
- Configure: `cmake --preset linux64-deploy` — RC=0 (vcpkg install ~19 min).
- Build: `cmake --build build/linux64-deploy --target z_generals -j2` — RC=0.
  **Binary: `testbed/src/build/linux64-deploy/GeneralsMD/GeneralsXZH`** (243 MB ELF x86-64, RelWithDebInfo).
- One testbed-only source patch was required: `Core/Libraries/Source/WWVegas/WW3D2/render2dsentence.cpp` used
  `std::vector` in cross-platform RTL code while `#include <vector>` sat inside an `#if defined(__ANDROID__)`
  block; one include line was added outside the guard (marked `TESTBED PATCH` in the file). Behavior-neutral;
  this is a genuine port bug for non-Android builds with this libstdc++.
- Runtime assembly follows the port's own layout (deploy/run scripts): ZH archives in the game folder,
  base-Generals archives in a sibling `Generals/` folder. **Layout matters**: with both games' archives mixed in
  one folder, Generals' `Ini.big` wins shared paths over `INIZH.big` (sorted, first-mounted wins) and the boot
  segfaults in `DamageFXStore::findDamageFX` (hashtable bucket corruption from the mixed data generations).
  With the port's intended two-folder layout, the full INI load completes cleanly on pristine retail data.
- Remaining runtime ceiling: the engine reaches the end of data loading and then aborts in DXVK/lavapipe
  (`LLVM ERROR: out of memory` / `Buffer allocation failed`) — this VM has no GPU and ~6 GB RAM; llvmpipe's
  LLVM JIT + DXVK do not fit. On Linux the render backend is hardwired to Vulkan (`UseVulkanBackend()` returns
  true off-Android), so there is no lighter GLES path locally. **This does not affect any probe**: archive
  mounting and all INI parsing happen before renderer creation, and every run below emitted its full evidence
  before the abort. (Also: no `.csf` string file exists in the local data set — `[CSF] init() - getCSFInfo FAILED`
  — cosmetic for these probes.)

## 2. Game data assembly

- `INIZH.big` was **rebuilt** from the extracted corpus (`zh-kotlin-engine/out/extract`, 135 files) with a
  purpose-written BIG writer (`testbed/tools/bigtool.py`), format validated against retail archives
  (header total == file size; index-size field == first data offset). Reparse verification: all 135 payloads
  byte-identical. Mapping: `Data_INI_Default_X`→`Data\INI\Default\X`, `Data_INI_Object_X`→`Data\INI\Object\X`,
  `MappedImages` subfolders preserved, else `Data\INI\X`. Size 18,764,473 B.
- Retail BIGs are symlinked from `zh-kotlin-engine/data/`; `W3DZH.big` from `~/workspace/user/files/`.
  The CommunityPatch BIG is NOT in the game folder — per the engine's code it belongs in UserData (see §4).
- Competing copies of the test file `Data\INI\Object\AirforceGeneral.ini` across all local archives:
  INIZH (717,959 B, vanilla), CommunityPatch (0 B placeholder), the v5 mod (717,934 B). Nothing else.

## 3. The test mod, verified

`!ReforgedData-v5.big`'s payload is byte-identical to `m1/AirforceGeneral-v5.ini`, whose diff against vanilla
is exactly one line — line 7292, inside `Object AirF_AmericaTankMicrowave` (block starts line 7282):
`UpgradeCameo5 = Upgrade_AmericaCompositeArmor` → `UpgradeCameo5 = None`. Both files: 18,250 raw lines /
564 top-level lines (the engine's `[INI] load` counter counts top-level lines).

## 4. Cameo-display code verdict (may crack the mystery by itself — it does)

The selected-unit panel's upgrade cameos come from exactly one place:
`Core/GameEngine/Source/GameClient/GUI/ControlBar/ControlBar.cpp`, `ControlBar::setPortraitByObject`:

```cpp
AsciiString upgradeName = thing->getUpgradeCameoName(i);
if (upgradeName.isEmpty())            { hide slot; continue; }
const UpgradeTemplate *ut = TheUpgradeCenter->findUpgrade(upgradeName);
if (!ut)                              { hide slot; continue; }
show slot with ut->getButtonImage();
```

(`m_upgradeCameoUpgradeNames[]` is filled by the `UpgradeCameo1..5` INI fields in ThingTemplate.cpp:194-198.
The only other consumer, ProductionUpdate.cpp:1013, merely matches a completed upgrade to dirty the UI.)

**Verdict: a cameo value of `None` — or any name that doesn't resolve to an Upgrade — hides the slot. It can
never draw the Composite Armor icon.** Therefore, if the mod's value had been the one in the live
`AirF_AmericaTankMicrowave` template, the armor icon would have been gone on the phone. The phone symptom
(icon present) logically requires that the template's final value was still `Upgrade_AmericaCompositeArmor`,
i.e. something parsed *after* the mod's file set it back. §5 shows exactly what, measured.

## 5. Probe results (real engine, local runs; stderr logs in `testbed/runs/`)

Mounting channels on Linux share Android's `ArchiveFileSystem` code. Managed mods (`mods_active.txt`) are
Android-only (`GXManagedMods.h`: "Always empty off Android") — locally the `!` and `-mod` channels exercise
the same winner/merge machinery; managed mods additionally mount with overwrite=TRUE, i.e. strictly stronger.

| Run | Setup | Key stderr evidence | Result |
|---|---|---|---|
| R0c | retail only | all 23 archives `[gxbig] loaded:`; full INI load completes; Object dir = 44 files | baseline OK (dies later only in Vulkan, §1) |
| R1 | `!ReforgedData-v5.big` in game root | `[gxbig] loaded: .../!ReforgedData-v5.big`; AirforceGeneral parsed, 564 lines | mod mounts |
| R2 | probe: v5 + 37 appended comment lines | AirforceGeneral **601 lines = 564 + 37** | **the mod's copy is the parsed copy — winner-per-path PROVEN** |
| R3 | probe: v5 + invalid top-level token | `[INI] ERROR in load('Data\INI\Object\airforcegeneral.ini') - exception caught` + `[GX-RELEASECRASH] Uncaught Exception during initialization` | boot dies on the mod's file — it is genuinely parsed, not just listed |
| R7 | `-mod !ReforgedData-v5.big` | exclusion line names the mod; AirforceGeneral 564 lines | `-mod` channel works |
| R4 | CommunityPatch in UserData, no mod | `[gxbig] community patch mounted: ...`; Object dir = **2147 files**; AirforceGeneral = **1 line** (the patch's 0-byte placeholder wins the path); Faction Microwave file parses | patch restructures all object data |
| R5 | patch + `!` v5 mod | `[gxbig] community patch not mounted: a mod is installed (!ReforgedData-v5.big)...`; Object dir = 44 files | engine's designed exclusion works on this channel |
| R6 | patch + `!` v5 mod + `gx_community_patch_with_mods.txt` marker in UserData root | `[gxbig] mod !ReforgedData-v5.big installed, community patch mounted anyway (launcher switch)` + `community patch mounted:`; Object dir = **2147 files**; AirforceGeneral = **564 lines** (mod copy still wins its path); Faction Microwave file parses **afterwards** | **phone symptom reproduced — see §6** |

Patch facts (ArchiveFileSystem::loadMods): the patch is mounted only from
`<UserData>/GeneralsOnlineGameData/500_900_CommunityPatch_CoreINI.big` (UserData here =
`~/.local/share/GeneralsX/GeneralsZH/`), via a name-sorted mount that beats letter-named retail archives but
loses shared paths to `!`-named mods. Markers `gx_no_community_patch.txt` / `gx_community_patch_with_mods.txt`
sit in the UserData root (the launcher's "use the patch with mods too" switch writes the latter).

Parse-order facts (INI::loadDirectory, measured in R4/R6 logs): top-level `Data\INI\Object\*.ini` load first
(AirforceGeneral at log line ~986), subdirectory files load in a second pass
(`Data\INI\Object\faction\americaairforce\unit\airf_americatankmicrowave.ini` at log line ~2576).
Merge facts (ThingFactory::parseObjectDefinition, INI_LOAD_OVERWRITE): an existing template is reused and the
later file's fields overwrite the earlier ones.

## 6. Bottom line — why the phone showed no effect

The v5 mod file is **correct and effective**: mounted, it wins its path (R2), is parsed (R3), and its value
would hide the icon (§4). On the phone it produced no effect because — in the only configuration consistent
with all evidence — **the GeneralsOnline Community Patch was also mounted during those tests**, and the patch
redefines the very same object in a different file that always parses later:

- The patch empties `Data\INI\Object\AirforceGeneral.ini` (0 B) and ships complete per-object definitions
  under `Data\INI\Object\Faction\...`; its `Faction\AmericaAirForce\Unit\AirF_AmericaTankMicrowave.ini`
  contains `UpgradeCameo5 = Upgrade_AmericaCompositeArmor` (extracted and read directly).
- R6 reproduces the phone state end-to-end in the real engine: the mod's AirforceGeneral.ini is parsed with
  `UpgradeCameo5 = None` (564 lines), then the patch's Faction file parses in pass 2 and overwrites the field
  back to `Upgrade_AmericaCompositeArmor`. Final template ⇒ armor icon shown. Exactly the five phone rounds.
- Winner-per-path cannot help here: the patch doesn't fight over the mod's file path — it wins by *file
  location* (subdirectory pass) + *merge order* (later wins). The port's own author documents this exact
  failure mode in loadMods (Contra 007 comment).

Why would the patch be mounted on the phone despite the launcher banner saying it wasn't? The banner is the
launcher's (Java) assessment; the engine decides independently. Two engine-side routes leave the patch
mounted with a managed mod present, both invisible without the log: (a) the launcher's "community patch with
mods" switch/marker is set in his install, or (b) the engine's managed-mod detection (which scans
`m_archiveFileMap` for the managed archive paths) silently misses, so no exclusion triggers. His
`generals-stderr.log` would show which in one line — `[gxbig] community patch mounted:` vs
`not mounted: a mod is installed`. That file was asked for but not yet obtained; the testbed cannot see his
UserData, so this last branch point is stated as the two alternatives, not resolved.

**Consequences for the project (M1 design rule, proven locally):**
1. Any Reforged change to an object the patch redefines must be delivered at the **Faction path**
   (`Data\INI\Object\Faction\<Faction>\Unit\<Object>.ini` etc.) inside the mod — a mod archive mounts above
   the patch, so its copy wins that path and parses in the same pass position.
2. Editing only the monolith files (AirforceGeneral.ini style) is a no-op whenever the patch is mounted,
   regardless of channel (`!`, `-mod`, managed).
3. Alternatively the patch must be off (the engine excludes it automatically when it *detects* the data
   mod — R5 proves the mechanism when detection fires).
4. The same applies at scale to the whole Reforged data layer: its 20 `*Reforged.ini` overlay files target
   the retail layout; against a patch-mounted install they must be translated into the patch's split-file
   layout (or the install must run patch-free).

## 7. Artifacts

- Binary: `~/workspace/projects/reforged-android/testbed/src/build/linux64-deploy/GeneralsMD/GeneralsXZH`
- Build tree: `~/workspace/projects/reforged-android/testbed/` (src/, runtime/, gamedata/, probes/, tools/,
  run-probe.sh, NOTES.md, configure.log, build.log, build2.log)
- Run logs: `~/workspace/projects/reforged-android/testbed/runs/` (r0*, r1-v5mod, r2-lines, r3-corrupt,
  r4-patch, r5-patch-mod, r6-patch-mod-marker, r7-modarg)
- System state restored: the Vulkan ICD manifests temporarily moved during diagnosis were returned to
  `/usr/share/vulkan/icd.d/` (8 files verified present).
