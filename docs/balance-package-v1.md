# Reforged Balance Package v1 — Build & Verification Report

**Deliverable:** `~/workspace/projects/reforged-android/m1/!ReforgedBalance-v1.big`
**Size:** 3,195,285 bytes · **Entries:** 301 · **SHA-256:** `f40abbad3244fa3784071ee038ae008eba23a0979340af6bd4b1169cff93842c`
**Install state:** separate package, mounts alongside `!ReforgedFixes-v3.big` (sha `4dffe024…891b`, phone-verified). All gates were run in the **combined state** (fixes v3 + balance v1 together), in both configurations (Community Patch mounted with the with-mods marker; patch-free retail), and in both mount orders.
**Builder:** `~/workspace/projects/reforged-android/balance/work/build_balance.py` · **Manifest:** `balance/work/balance-manifest.json` (1,082 block dispositions, 35 locomotor repairs, 5 module strips, 205 documented drops).

---

## 1. Per-file classification + disposition

Source tree: `audit/reforged/GeneralsMD/Code/Data/INI/` (Reforged HEAD 61dbc59, v4.0.0). "Delivered" counts are the builder's block counts on the shipped artifact.

| Reforged file | Contents | Delivered | Route |
|---|---|---|---|
| **BalanceReforged.ini** (6,369 ln) | 350 Object/ObjectReskin blocks (347+3), 18 Weapon edits, 9 Armor, 2 Locomotor; 502 module ops (126 ReplaceModule, 376 AddModule) | **350 objects** (344 split-append, of which 118 ride inside fixes-v3 superset entries; 3 jet-crash objects as merged definitions; see §3), **18 weapons** in-place, **9 armor + 2 locomotor** as directory file | Split-append at the Community Patch's per-object split paths (the M1 design rule); weapon edits in-place in a superset `Weapon.ini` |
| **WeaponReforged.ini** | 10 weapon blocks | **10** (6 turned out to be edits of weapons the patch already defines → applied in-place in the superset `Weapon.ini`; 4 genuinely new → directory file `Weapon\ReforgedBalance.ini`) | Superset + directory (see §3, duplicate trap) |
| **ObjectCreationListReforged.ini** | 59 OCL blocks | **37** (13 Turkiye excluded; 9 Paradrop OCLs excluded — fixes v3 already ships those exact definitions) | Directory file |
| **CommandSetReforged.ini** | 145 blocks (106 CommandButton + 39 CommandSet) | **32 buttons** (directory file), **16 sets** (full monolith, see §3); excluded: 96 Turkiye-flagged (name or content references the Turkiye faction), 1 `Command_ForceAttack` | Buttons: directory file (duplicates merge — proven safe). Sets: monolith `Data\INI\CommandSet.ini` carrying all 472 patch sets with the 16 edits substituted |
| **FXListReforged.ini** | 139 FXList blocks | **139**, minus 13 `ScreenDistortion` sub-blocks stripped (the effect class does not exist in MYSOREZ — 0 hits in its FXList parser) | Directory file |
| **ParticleSystemReforged.ini** | 298 ParticleSystem blocks (edits of retail systems + new systems the shipped FX lists reference) | **298**, minus 192 field lines of 4 kinds the host parser does not know (`FireLook` ×182, `ExplosionDebrisTrail` ×7, `GroundCollision` ×2, `FlipbookGrid` ×1) | Directory file (find-or-create + field merge in the host — safe for edits) |
| **SpecialPowerReforged.ini** | 11 blocks | **2** (`SuperweaponFrenzy`, `Early_SuperweaponFrenzy` — edits of retail powers, applied in-place in a superset `SpecialPower.ini`); excluded: 8 Turkiye, 1 already shipped by fixes v3 | Superset monolith (same duplicate trap as Weapon) |
| **UpgradeReforged.ini** | 17 blocks | **3** stock edits (`Upgrade_AmericaMOAB`, `Upgrade_AmericaSentryDroneGun`, `Upgrade_ChinaNeutronShells`); 14 Turkiye excluded | Directory file (host merges upgrades unconditionally) |
| **MultiplayerReforged.ini** | 8 MultiplayerColor blocks | **8** | Directory file |
| **ScienceReforged.ini** | 19 blocks | **0 new** — 16 Turkiye; the 3 stock blocks are the Demo Rebel Ambush sciences fixes v3 already ships | — |
| **AIDataReforged.ini** | Turkiye faction AI data | 0 — faction not delivered | Excluded (faction) |
| **PlayerTemplateReforged.ini** | Turkiye player template | 0 | Excluded (faction) |
| **TurkiyeReforged.ini / TurkiyeWeaponReforged.ini** | The Turkiye faction itself | 0 | Excluded (faction: needs Reforged-engine reskin substitution plus art/voices/CSF text that do not exist on the host) |
| **CampaignReforged.ini + SpeechReforged.ini (1,355 DialogEvents) + VideoReforged.ini** | Classic-campaign restoration bundle | 0 | Excluded — shell/campaign layer, a separate candidate package; not part of the skirmish balance layer |
| **ControlBarProReforged.ini (15 schemes) + ControlBarSchemeReforged.ini** | Reforged UI schemes | 0 | Excluded — Reforged's own UI layout; the host runs its own ControlBar Pro. The scheme file also references texture `ReforgedChinaBeacon`, absent on the host |
| **WindowTransitionsReforged.ini** | Window transitions | 0 | Excluded — bound to Reforged `.wnd` files not present on the host |
| **ModernWater.ini** | Water renderer settings | 0 | Excluded — renderer-coupled, no host counterpart semantics |
| **Mouse.ini / MappedImages** | Cursor + image mappings | 0 | Out of scope (art/cursor layer, not balance data) |
| **FixesReforged.ini** | The fixes layer | — | Already delivered as `!ReforgedFixes-v3.big`; not redone |

**Totals:** 1,082 block dispositions recorded; **delivered ≈ 880 blocks** across 301 package entries (288 per-object split files + FireFieldSmall + Weapon/SpecialPower/CommandSet supersets + 9 directory files); **excluded ≈ 200 blocks**, every one with a stated reason above (faction ~150, campaign/UI bundle, duplicates of fixes v3 content, 1 host-unsupported button).

### Package entries by kind
- 288 object split files (patch paths; 101 of them are supersets = fixes v3 entry bytes with the balance overlay inserted *before* the fixes overlay, matching Reforged's own Balance→Fixes order, so the entry degrades gracefully to the fixes-only state if the fixes copy ever wins the path)
- 1 object split file with new objects (FireFieldSmall + 3 jet-crash definitions)
- 3 superset monoliths: `Weapon.ini` (fixes v3's + 24 in-place edits), `SpecialPower.ini` (patch's + 2 edits), `CommandSet.ini` (all 472 sets, 16 edited)
- 9 directory files (`ReforgedBalance.ini` in Weapon, Armor, Locomotor, ObjectCreationList, Upgrade, CommandButton, FXList, ParticleSystem, Multiplayer)

---

## 2. Locomotor repairs (the fixes-v2 construction, extended)

35 Balance blocks replace an AIUpdate-family module (Comanche, Marauder, Overlord Gattling, Scud Storm missiles, Crusader, Paladin, BattleMaster, Scorpion, Hacker…). Per the standing rule, each got a trailing repair block restating the object's original Locomotor lines extracted from its patch base — **with one refinement the testbed forced** (see §3.4): surfaces the replacement segment already specifies in-segment are *not* restated.

- 28 objects: standard restatement.
- 4 Scud Storm missile variants: **no repair** — their replacement `MissileAIUpdate` segment itself carries `Locomotor = SET_NORMAL SCUDStormMissileHighLocomotor` (Reforged's intended new set); restating the original would throw (re-specification) and would also be wrong.
- 3 Overlord Gattling Cannon variants: **no repair** — the base AI module holds no locomotor sets at all (contained turret), so carry-over would restore nothing.

5 `IdleHackerUpdate` AddModule segments (the 5 Hacker objects) were **stripped**: that behavior type is Reforged-invented and does not exist in MYSOREZ (12 of the 13 behavior types Balance installs exist on the host). The rest of each Hacker block is delivered intact.

---

## 3. Host limitations found by the testbed (all reproduced minimally, all routed around)

### 3.1 Duplicate-definition trap in directory passes (Weapon, SpecialPower)
A second definition of an existing name in a directory file is fatal for stores whose parser requires override mode: the first balance build crashed the load with
`[INI] ERROR in load('Data\INI\Weapon\reforgedbalance.ini') - exception caught (unrecognized type)` — 6 of WeaponReforged's 10 "new" weapons in fact already exist in the patch's `Weapon.ini`. Route: in-place edits in superset monoliths; directory files carry only genuinely new names.

### 3.2 Two sequential ReplaceModule ops on a reskin-created template throw
The 3 jet-crash objects are `ObjectReskin` + `Object` pairs whose Object block performs **two** ReplaceModule ops on the clone. Minimal repro on the testbed (single-entry probe packages): reskin alone ✓, either ReplaceModule alone ✓, **both together ✗** —
`[INI] field parser threw an unrecognized exception type` / `[LINE: 49 - FILE: 'Data\INI\Object\shared\system\firefieldsmall.ini'] Error reading field 'ReplaceModule'`.
Route: the reskin+replace composition is resolved by hand into plain `Object` definitions that are semantically identical to the clone Reforged's engine produces (FireFieldSmall's fields, the reskin's Draw, FireWeaponUpdate with the new weapon, DeletionUpdate with the new lifetimes 6000/1000/1000). All other 344 object overlays — including multi-ReplaceModule overlays on normal templates (Scorpion has 5) — parse verbatim.

### 3.3 CommandSet duplicates throw; form masking is the delivery route
`ControlBar::parseCommandSetDefinition` throws `INI_INVALID_DATA` on any duplicate set unless the load type is `INI_LOAD_CREATE_OVERRIDES`; the store loads with `INI_LOAD_OVERWRITE` (ControlBar.cpp:1244-1247). The directory-file build died in the headless audit:
`[GX-RELEASECRASH] ReleaseCrash reason='Error parsing INI file 'Data\INI\CommandSet\reforgedbalance.ini' in block starting 'CommandSet Infa_ChinaCommandCenterCommandSetUpgrade '`.
Route (the loader's own PLAN-027 form masking, INI.cpp): a mod-source monolith `Data\INI\CommandSet.ini` makes the loader skip all lower directory files for the store — so the package ships the full 472-set inventory as a monolith with the 16 edits substituted. Each set is then defined exactly once in both configurations. Command**Button** duplicates, by contrast, only `DEBUG_CRASH` (non-fatal in this build) and merge into the existing button — proven in the same headless run: `load('Data\INI\CommandButton\reforgedbalance.ini') END`, `filesRead=18`, no error.

### 3.4 Locomotor re-specification throw
`AIUpdateModuleData::parseLocomotorSet` throws when a surface is specified twice in one module. First combined build died at `chem_scudstormmissile.ini` line 88, `Error reading field 'Locomotor'`, because the repair restated SET_NORMAL over the replacement segment's own in-segment set. The repair rule in §2 is the fix.

---

## 4. Tick rate — Reforged's own 60-steps/s conversion vs MYSOREZ's 60 Hz variant

*(Owner steer: do not treat MYSOREZ's 60 Hz variant as equivalent to Reforged's conversion. Findings below are from Reforged's repo/data and from the MYSOREZ source in the testbed tree.)*

### 4.1 What Reforged's conversion actually is
Reforged has run **60 logic steps/second since v3.0**. Its own gate script states the contract: `gate-60hz.ps1` — "60 logic frames a second", a p99.9 frame budget of 16.7 ms, "216000 logic frames" per hour, and a hard rule that a tick is never dropped. This is an **engine-level conversion with data left deliberately rate-independent**:

- **Re-based (engine side, not data):** the step rate itself; scenario/campaign frame numbers are shimmed ×2 — `GeneralsMD/Code/Data/Scenarios/gate60hz.txt`: *"The frames are 30 Hz, so 18000 is logic frame 36000"* (legacy 30 Hz frame references are doubled at load); the music crossfade was converted from drawn-frame counting to game-time counting; `PORTING.md` pins deterministic behavior to "logic at 60 Hz" (lockstep CRCs are computed on the 60 Hz step stream).
- **Left alone (the data — i.e., everything in this package):** Reforged ships **no re-based copies of the base INI files**; its data layer is the same overlay files ported here. The values are overwhelmingly in **rate-independent units**: speeds in dist/sec and turn rates in deg/sec (retail Locomotor.ini's own comments), times in milliseconds (DelayBetweenShots, ClipReloadTime, lifetimes… `MinLifetime = 6000` etc.). They mean the same thing at 30 or 60 steps/s — the engine just integrates them in finer steps. The balance package's 2 Locomotor blocks are per-second *balance* changes, not ×2 re-basing (e.g. the new `SCUDStormMissileHighLocomotor`, Speed 400 vs EA's 300).
- **Frame-denominated exceptions (the honest residue):** a small number of values are denominated in *frames* and therefore halve in wall-clock duration at 60 steps/s unless the engine compensates: particle `SystemLifetime` is in frames (sampled diff of the 233 systems Balance edits vs retail: only 2 changed at all — 0→1 and 500→10 — and neither is a ×2 rescale; Reforged re-tuned them as balance against its rewritten particle engine, not as rate conversion), and a few tuning comments speak in frames ("fires 3 frames sooner", "first shell 24 frames later"). At the port's 30 Hz these specific values last twice as long in wall-clock terms as in Reforged at 60 steps/s. Everything else in the package is unit-safe.
- **Presentation:** "Smooth Motion" (render interpolation between steps) is a separate toggle in Reforged, off by default — it is not part of the simulation conversion.

**Bottom line for the future port:** faithful 60-steps/s = Reforged's engine contract (never-drop tick, ×2 scenario-frame shim, game-time-based audio crossfade, 60 Hz CRC stream) run over *this same data unchanged*, plus a deliberate decision on the handful of frame-denominated particle lifetimes. No data re-basing is required or present in Reforged itself.

### 4.2 What MYSOREZ's 60 Hz variant mechanically does (source evidence)
It is a compile-time variant, not the shipping default: CMake option `SAGE_HIGH_FPS_SIM` (OFF by default, `cmake/config-build.cmake:25-31`) → compile definition `GENERALS_ONLINE_HIGH_FPS_SERVER`. Its purpose is GeneralsOnline PC-client lockstep compatibility — the 60 Hz and 30 Hz client populations are kept separate (distinct client IDs `gen_online_60hz` vs `gen_online_30hz`). Mechanically:

- `LOGICFRAMES_PER_SECOND = WWSyncPerSecond` flips 30 → 60 (Core `GameCommon.h:68`).
- GameLogic gains a **legacy-frame tracker** (`m_frameLegacy` / `m_frameLegacyLast`, `HasLegacyFrameAdvanced()`) that fires on every *second* step — but it is consulted at **selected AI sites only** (`AI.cpp:362`, `TurretAI.cpp:680`, `DeployStyleAIUpdate.cpp:241,261`): a partial, call-site-by-call-site compensation, not a systematic conversion.
- `FRAME_GROUPING_CAP` doubles 32 → 64.
- There is **no** data re-basing, **no** scenario-frame shim, and **no** render interpolation in this variant.

**Equivalence: NOT established and not claimed.** The two conversions share only the step count. Reforged's is a whole-engine contract with a never-drop guarantee and compatibility shims; MYSOREZ's is a lockstep-matching tick doubling with spot legacy-frame compensation at four AI call sites. The balance data in this package is unit-safe under both (§4.1), so the package is correct at the port's standard 30 Hz today and remains correct under a future faithful Reforged-style 60-steps port.

---

## 5. Four gates — combined state, both configs, final artifact

Baselines (fixes-only, from the fixes missions): patch LOCO table 2,109 lines (`audit-v3-patch.stderr.log`), retail 2,107 (`audit-v3-retail.stderr.log`).

### (i) Full INI load — zero `[INI] ERROR` — **PASS, both configs, both mount orders**
- Patch, balance-first (`balfin-patch`, 14,302 log lines): `INI_ERROR=0`; config proof in-log: `[gxbig] mod !ReforgedBalance-v1.big installed, community patch mounted anyway (launcher switch)` and `[gxbig] community patch mounted: …/500_900_CommunityPatch_CoreINI.big`.
- Retail, balance-first (`balfin-retail`): `INI_ERROR=0`.
- Patch + retail with fixes staged first (`balfin2-ffpatch`, `balfin2-ffretail`): `INI_ERROR=0` in both (graceful degradation confirmed on the final artifact).
- All 8 engine-init directory files show load END lines (Armor, FXList, Locomotor, Multiplayer, ObjectCreationList, ParticleSystem, Upgrade, Weapon). CommandButton/CommandSet load in the ControlBar phase — exercised by the headless audit path (§iv), where both loaded clean (`CommandButton\reforgedbalance.ini` END, `filesRead=18`; CommandSet monolith + masked directory pass).

### (ii) Locomotor audit — **PASS, both configs, both orders**
Diff vs the fixes-only table is exactly three added lines and nothing else, in every run:
```
> [LOCOAUDIT] Reforged_BigJetCrashImpact NOAI
> [LOCOAUDIT] Reforged_JetCrashFire NOAI
> [LOCOAUDIT] Reforged_JetCrashImpact NOAI
```
(The 3 new templates are fire-field clones with no AI module — NOAI is correct.) No object loses or changes movement data vs the combined baseline; the 35 AI-module replacements all land with their locomotor sets intact (28 restated, 4 in-segment, 3 none-by-design).

### (iii) Reference audit — **PASS: UNRESOLVED = 0**
Audit over the balance delta (25,179 delivered lines) in the combined state, universe = retail winners ∪ patch winners ∪ fixes v3 definitions ∪ balance definitions (case-insensitive; ObjectReskin definitions folded into the Object store; space-indented retail headers tolerated):
```
refs=4130 resolved-both=4122 engine-resolved=7 inherited-retail=1 UNRESOLVED=0
```
- Coverage includes the cross-reference classes beyond the fixes-era field map: `ProjectileObject`→Object, OCL `ObjectNames`→Object, FXList ParticleSystem `Name`→ParticleSystem, CommandSet slot lines→CommandButton.
- `engine-resolved=7`: `ProjectileObject = NONE` — the engine's null-template sentinel, not a lookup.
- `inherited-retail=1`: `ParticleSystem :: CraterDebris` — referenced by `FX_CraterBombExplosion`; the *identical* reference exists in unmodded retail (`Data_INI_FXList.ini` line 7831) and no definition exists anywhere in the retail corpus — a pre-existing retail dangling reference the edit inherits verbatim; the host tolerates it exactly as retail does (FX sub-effect resolves to nothing). Not introduced by this package.
- Cross-package references verified in both directions (e.g. balance's `SupW_OCL_SDILinkLasers` → `SupW_SDILasers`, defined by fixes v3's `SDILasers.ini` reskin — present in the combined state).

### (iv) Instantiation audit — **PASS, both configs**
Headless audit (`GX_INSTAUDIT=1`), natural mount order:
- Patch: `inst-balcomb-patch: COMPLETE after 3 segment(s)` — `[INSTAUDIT] DONE total=2121 ok=2119 null=0 throw=0 skipped=2`; crash set = `CabooseFullOfTerrorists`, `Infa_ChinaBunker` — exactly the known no-mod baseline pair (harness artifacts).
- Retail: `[INSTAUDIT] DONE total=2119 ok=2117 null=0 throw=0 skipped=2`; crash set = the same pair.
(2121 vs 2119 total = the patch config defines 2 more templates; the +3 balance templates instantiate cleanly in both.)

---

## 6. Known limitations / notes

- **Verification ceiling:** the testbed proves INI load, template state, reference resolution, and instantiation. It cannot prove in-game behavior (no GPU); the phone remains the final arbiter, as with fixes v3. CommandButton/CommandSet are parsed in the ControlBar phase, which the windowed probe never reaches (DXVK abort) — they *were* exercised by the headless audit path, which initializes that far.
- **Stripped content is behavior-only, never silent:** 13 ScreenDistortion FX sub-blocks, 192 unsupported ParticleSystem field lines, 5 IdleHackerUpdate segments — each class is a host-engine absence (the module/effect/field does not exist in MYSOREZ), recorded in the manifest. If the host ever gains them, the strips are one builder change away from shipping.
- **Frame-denominated values** (§4.1) run at the port's 30 Hz semantics until a faithful 60-steps port lands; this matches how every other ZH mod behaves on the port today.
- Nothing was pushed anywhere; the repo upload is a separate step. The fixes package is untouched (byte-identical, sha `4dffe024…891b`).
