# ReforgedFixes-v2 — corrective package: locomotor carry-over repair

**Artifact:** `~/workspace/projects/reforged-android/m1/!ReforgedFixes-v2.big`
**Size:** 2,609,666 bytes · **Entries:** 185 (same paths as v1) · **SHA-256:** `971692b0a9e07df2cbd6b979a69255f352fea2bbd6cf5080de8e5be2bf330a6d`
**Supersedes:** `!ReforgedFixes-v1.big` (`ca0b8430…`), which is **unsafe**: it crashes the game at runtime (owner-confirmed SIGSEGV, see §1). v2 = v1 with exactly 16 entries changed, each by one appended repair block; all other 169 entries are byte-identical to v1 (builder assertion + reparse/hash verification, `fixes/work/build_v2.py`).

**Verification (final):** patch-mounted config — full INI load (Mouse.ini END reached, 14,239 log lines), **zero `[INI] ERROR`**; patch-free retail config — full INI load (4,852 lines), **zero `[INI] ERROR`**. Locomotor audit (§4): in **both** configs the v2 table is identical to its baseline for **every one of the 2,100+ templates**, the only difference being the package's own added reskin template `SupW_SDILasers` (NOAI, already the case in v1, unrelated to locomotors). Runs: `testbed/runs/audit-v2-patch.stderr.log`, `audit-v2-retail.stderr.log`; tables in `fixes/work/audit/`.

---

## 1. The defect (as established by the parent agent; confirmed here empirically)

Reforged's engine carries a replaced AI module's locomotor sets into the replacement module (`ThingTemplate::parseReplaceModule` in the Reforged clone, its "port defect 33" fix). MYSOREZ's `parseReplaceModule` has no carry-over: it removes the old module data and parses the replacement fresh, and FixesReforged's AI-module replacement blocks restate no `Locomotor` lines. Every delivered `ReplaceModule` of an AIUpdate-family module therefore left the object's replacement AI module with an **empty** `m_locomotorTemplates` → `getCurLocomotor()` NULL → SIGSEGV in `ChinookAIUpdate::isAllowedToAdjustDestination()` when the unit follows a waypoint path (the owner's crash, via `ScriptEngine::doTeamFollowWaypoints`). v1's testbed gates verified parsing only; this runtime class was uncovered. §4's audit now covers it.

## 2. Affected-object inventory (static, complete)

Method (`fixes/work/inventory_v2.py`, data `inventory-v2.json`): all 153 module-op events in the 221 FixesReforged blocks were resolved to module types — Replace/Add segments from their own module lines, RemoveModule tags resolved against the shipped v1 base definitions — and classified against the AIUpdate family (every Behavior type whose ModuleData derives from `AIUpdateModuleData`, i.e. `isAiModuleData()==true`: AIUpdateInterface, ChinookAIUpdate, TransportAIUpdate, SupplyTruckAIUpdate, DeliverPayloadAIUpdate, DeployStyleAIUpdate, JetAIUpdate, DozerAIUpdate, WorkerAIUpdate, HackInternetAIUpdate, AssaultTransportAIUpdate, MissileAIUpdate, POWTruckAIUpdate, RailedTransportAIUpdate, FlightDeckBehavior). **0 events left unresolved.**

**Result: exactly 16 events, all `ReplaceModule`, on 16 objects:**

| Fixes block | Object | Replaced module (tag) | Type | Original locomotor sets (from base def) |
|---|---|---|---|---|
| 25 | AirF_AmericaVehicleChinook | ModuleTag_07 | ChinookAIUpdate | SET_NORMAL ChinookLocomotor; SET_TAXIING BasicHelicopterTaxiLocomotor |
| 26 | Lazr_AmericaVehicleChinook | ModuleTag_07 | ChinookAIUpdate | same |
| 27 | SupW_AmericaVehicleChinook | ModuleTag_07 | ChinookAIUpdate | same |
| 33 | AirF_AmericaVehicleHumvee | ModuleTag_03 | TransportAIUpdate | SET_NORMAL HumveeLocomotor |
| 34 | Lazr_AmericaVehicleHumvee | ModuleTag_03 | TransportAIUpdate | same |
| 35 | SupW_AmericaVehicleHumvee | ModuleTag_03 | TransportAIUpdate | same |
| 64 | AmericaVehicleSentryDrone | ModuleTag_04 | DeployStyleAIUpdate | SET_NORMAL SentryLocomotor |
| 65 | AirF_AmericaVehicleSentryDrone | ModuleTag_04 | DeployStyleAIUpdate | same |
| 66 | Lazr_AmericaVehicleSentryDrone | ModuleTag_04 | DeployStyleAIUpdate | same |
| 67 | SupW_AmericaVehicleSentryDrone | ModuleTag_04 | DeployStyleAIUpdate | same |
| 101 | Tank_ChinaTankECM | ModuleTag_03 | AIUpdateInterface | SET_NORMAL GattlingTankLocomotor |
| 102 | Infa_ChinaTankECM | ModuleTag_03 | AIUpdateInterface | same |
| 103 | Nuke_ChinaTankECM | ModuleTag_03 | AIUpdateInterface | same |
| 109 | Infa_ChinaVehicleNukeLauncher | ModuleTag_04 | DeployStyleAIUpdate | SET_NORMAL ChinaNukeCannonLocomotor |
| 110 | Nuke_ChinaVehicleNukeLauncher | ModuleTag_04 | DeployStyleAIUpdate | same |
| 111 | ChinaVehicleNukeLauncher | ModuleTag_04 | DeployStyleAIUpdate | same |

Negative results (checked, not affected):
- **19 AddModule events — none AI-family** (SquishCollide, WeaponSetUpgrade, FireWeaponWhenDeadBehavior, SlowDeathBehavior, StatusBitsUpgrade, OCLSpecialPower, Sabotage crate collides). An AddModule of an AI type would have triggered the same loss via `ModuleInfo::clearAiModuleInfo()`; there are none.
- **11 RemoveModule events — none AI-family** (LocomotorSetUpgrade, SlowDeathBehavior variants, projectile/dummy modules). No object ends up with a removed-but-not-replaced AI module.
- No Fixes block for any affected object restates `Locomotor` lines of its own (the re-specification throw in `parseLocomotorSet` is therefore not in play), and each affected object has exactly one AI-affecting block.
- The 3 excluded v1 blocks (idx 191–193) and both reskin blocks contain no AI-family ops.

## 3. The corrected construction, and why it lands in the right module data

For each affected entry, v2 appends one trailing block at the very end of the shipped file (after base definition + Fixes overlay):

```
; ==== ReforgedFixes-v2 locomotor carry-over repair ====
; (comment explaining the above)
Object <Name>
  Locomotor = <original set lines, verbatim from the object's base definition>
  ...
End
```

Code evidence (MYSOREZ source, testbed tree @ a520ed1):

- `Locomotor` is a **ThingTemplate-level field** whose parser is `AIUpdateModuleData::parseLocomotorSet` (ThingTemplate field table: `{ "Locomotor", AIUpdateModuleData::parseLocomotorSet, nullptr, 0 }`). It writes into `tt->friend_getAIModuleInfo()` — the template's *current* AI module data (first `m_behaviorModuleInfo` entry with `isAiModuleData()`).
- The repair block parses **after** the overlay's `ReplaceModule` segment has completed, so the template's only AI module at that moment is the fresh replacement, whose `m_locomotorTemplates` is empty. `parseLocomotorSet` fills the named sets; the "re-specifying a LocomotorSet is no longer allowed" throw fires only for a non-empty set under `INI_LOAD_OVERWRITE`, which cannot occur here.
- The restated lines are copied verbatim from the object's own base definition in the same shipped file (the patch split definition — the same source v1's delivery is built on, and the definition that wins in retail config too, where the entry parses in pass 2 on top of the retail template: base part re-installs the AI module + sets, overlay replaces it, repair restates the same sets). Both configs therefore converge to the identical final state — which §4 confirms empirically.
- This reproduces exactly Reforged's carry-over semantics: the replacement module ends up holding the replaced module's original locomotor sets, and nothing else about the Reforged edit changes.

## 4. Proof beyond parsing — the locomotor audit

**Instrument (TESTBED-ONLY, never shipped):** `ThingFactory::testbedDumpLocomotorAudit()` added to the testbed engine (declaration in `ThingFactory.h`, body in `ThingFactory.cpp`, one call in `GameEngine::init` immediately after the `TheThingFactory` `initSubsystem` load; the data-only package contains no engine code). It was first hooked at the end of `postProcessLoad()` — that never fires in this VM because the DXVK/lavapipe device init aborts during subsystem init, before `postProcessLoadAll()`; the earlier hook point is sound because object templates come only from ThingFactory's own INI dirs and `resolveNames()` (postProcessLoad) does not touch module data. For every template it prints `[LOCOAUDIT] <name> TOTAL <n> SETS <set>:<count> …` (or `NOAI`), reading the public `AIUpdateModuleData::m_locomotorTemplates` of `friend_getAIModuleInfo()`.

**Runs** (all via `testbed/run-probe.sh`, rc=134 = the known post-load lavapipe abort in every run, after the full INI load):

| Run | Config | Templates dumped | `[INI] ERROR` |
|---|---|---|---|
| audit-base-retail | retail data alone | 2,104 | 0 |
| audit-base-patch | patch alone (UserData) | 2,106 | 0 |
| audit-baseonly-retail | base-only BIG (v1 entries minus overlays), retail | 2,104 | 0 |
| audit-v1-patch / audit-v1-retail | v1 package | 2,107 / 2,105 | 0 |
| audit-v2-patch / audit-v2-retail | **v2 package** | 2,107 / 2,105 | 0 |

Baselines are per-config on purpose: patch data and retail data differ slightly (12 diff lines between the two baseline tables), and in retail config the package's entries impose the patch base definitions in pass 2 — so the retail comparator is the base-only BIG (identical base content, no overlays), not raw retail.

**Defect reproduction (v1 vs baseline):** in *both* configs the diff is exactly 33 lines = the same 16 objects dropping to `TOTAL 0`, plus the added `SupW_SDILasers` template. The empirical defect set equals the static inventory set (§2) — no more, no fewer.

**Repair proof (v2 vs baseline):** in *both* configs the diff is exactly **one line** — the added `SupW_SDILasers NOAI` template line (the package's reskin entry, present identically in v1; not locomotor-related). Every other template, including all 16 repaired objects with their per-set breakdowns, is byte-identical to baseline. v2-vs-v1 full-table diff = 32 lines in each config = precisely the 16 repaired rows.

The 16 repaired rows (patch config; retail config identical):

```
AirF_AmericaVehicleChinook     baseline TOTAL 2 SETS 0:1 5:1 | v1 TOTAL 0 | v2 TOTAL 2 SETS 0:1 5:1
Lazr_AmericaVehicleChinook     baseline TOTAL 2 SETS 0:1 5:1 | v1 TOTAL 0 | v2 TOTAL 2 SETS 0:1 5:1
SupW_AmericaVehicleChinook     baseline TOTAL 2 SETS 0:1 5:1 | v1 TOTAL 0 | v2 TOTAL 2 SETS 0:1 5:1
AirF_AmericaVehicleHumvee      baseline TOTAL 1 SETS 0:1     | v1 TOTAL 0 | v2 TOTAL 1 SETS 0:1
Lazr_AmericaVehicleHumvee      baseline TOTAL 1 SETS 0:1     | v1 TOTAL 0 | v2 TOTAL 1 SETS 0:1
SupW_AmericaVehicleHumvee      baseline TOTAL 1 SETS 0:1     | v1 TOTAL 0 | v2 TOTAL 1 SETS 0:1
AmericaVehicleSentryDrone      baseline TOTAL 1 SETS 0:1     | v1 TOTAL 0 | v2 TOTAL 1 SETS 0:1
AirF_AmericaVehicleSentryDrone baseline TOTAL 1 SETS 0:1     | v1 TOTAL 0 | v2 TOTAL 1 SETS 0:1
Lazr_AmericaVehicleSentryDrone baseline TOTAL 1 SETS 0:1     | v1 TOTAL 0 | v2 TOTAL 1 SETS 0:1
SupW_AmericaVehicleSentryDrone baseline TOTAL 1 SETS 0:1     | v1 TOTAL 0 | v2 TOTAL 1 SETS 0:1
Tank_ChinaTankECM              baseline TOTAL 1 SETS 0:1     | v1 TOTAL 0 | v2 TOTAL 1 SETS 0:1
Infa_ChinaTankECM              baseline TOTAL 1 SETS 0:1     | v1 TOTAL 0 | v2 TOTAL 1 SETS 0:1
Nuke_ChinaTankECM              baseline TOTAL 1 SETS 0:1     | v1 TOTAL 0 | v2 TOTAL 1 SETS 0:1
ChinaVehicleNukeLauncher       baseline TOTAL 1 SETS 0:1     | v1 TOTAL 0 | v2 TOTAL 1 SETS 0:1
Infa_ChinaVehicleNukeLauncher  baseline TOTAL 1 SETS 0:1     | v1 TOTAL 0 | v2 TOTAL 1 SETS 0:1
Nuke_ChinaVehicleNukeLauncher  baseline TOTAL 1 SETS 0:1     | v1 TOTAL 0 | v2 TOTAL 1 SETS 0:1
```
(Set keys: 0 = LOCOMOTORSET_NORMAL, 5 = LOCOMOTORSET_TAXIING.)

## 5. What v2 does not change / could not repair

- **Nothing else is changed.** Every non-affected entry is byte-identical to v1; the 16 changed entries differ only by the appended repair block. v1's known non-deliveries (idx 191–193, the dropped `ReforgedLaserPink.tga` line, the ChassisTwo/Three op substitution) are inherited unchanged and documented in the v1 report.
- **No affected object was left unrepaired.** All 16 inventory objects are repaired and audit-proven in both configs.
- Scope note: the audit proves the *template data* state (locomotor sets present, identical to baseline) for every object in both delivery configs. It cannot execute gameplay in this VM (no GPU; the engine aborts in lavapipe after data load), so a live in-match drive test remains a phone-side check — but the crash mechanism (empty locomotor map on the replaced AI module) is exactly the state the audit measures, and that state is now identical to the un-modded game for all 2,100+ templates.

## 6. Artifacts & reproducibility

- Package: `~/workspace/projects/reforged-android/m1/!ReforgedFixes-v2.big` (2,609,666 B, SHA-256 `971692b0…6d`).
- Builder: `fixes/work/build_v2.py` (deterministic from v1 + `inventory-v2.json`); inventory: `fixes/work/inventory_v2.py` → `inventory-v2.json`; base-only comparator: `fixes/work/!BaseOnly.big`.
- Audit tables: `fixes/work/audit/audit-*.txt`; run logs: `testbed/runs/audit-*.stderr.log`.
- Testbed engine changes are confined to the local testbed tree (`testbed/src`: `ThingFactory.h/.cpp`, `GameEngine.cpp` — all marked TESTBED-ONLY) and are **not** part of the shipped data package.
