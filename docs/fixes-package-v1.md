# ReforgedFixes-v1 — full FixesReforged package for the MYSOREZ port, testbed-verified

**Artifact:** `~/workspace/projects/reforged-android/m1/!ReforgedFixes-v1.big`
**Size:** 2,599,033 bytes · **Entries:** 185 · **SHA-256:** `ca0b8430e6080b034e719c4ca12fbec793f43808d81b3b7a8bbe22034aa3df49`
**Source:** `FixesReforged.ini` from the Reforged clone (`audit/reforged/GeneralsMD/Code/Data/INI/FixesReforged.ini`, 7,845 lines, 221 blocks: 213 Object, 7 Weapon, 1 ObjectReskin).
**Verification (final):** patch-mounted config — full INI load, **zero `[INI] ERROR`** (run `pkg-patch-5`, 12,126 log lines, rc=134 = the known post-load lavapipe abort); patch-free retail config — full INI load, **zero `[INI] ERROR`** (run `pkg-retail-1`, 2,741 lines, rc=134). Fingerprint probes +37 on all three test entries in **both** configs (details §4).

All runs are the real MYSOREZ engine (testbed `GeneralsXZH` @ a520ed1) via `testbed/run-probe.sh`; logs in `testbed/runs/`. Work files in `~/workspace/projects/reforged-android/fixes/` (`bisect/`, `probes/`, `work/`).

---

## 1. Phase 1 — the v2/v3 crash mystery: CLOSED

The original `FixesReforged.ini` delivered as a single mod entry `Data\INI\Object\FixesReforged.ini`:

- **Retail config** crashes at source line 104 — `Object Lazr_AmericaVehicleHumvee`, `ReplaceModule ModuleTag_05` (`testbed/runs/p1-retail-orig.stderr.log`).
- **Patch config** crashes earlier, at line 73 — `Object AirF_AmericaInfantryRanger`, `ReplaceModule ModuleTag_Death07` (`testbed/runs/p1-patch-orig.stderr.log`).

Engine bisect (remove the crashing block, re-run, repeat; final variant loads 100% clean — `fixes/bisect/results.json`, `fixes/bisect/bisect-run.log`):

- **72 culprit blocks: 62 ReplaceModule + 3 RemoveModule + all 7 Weapon blocks.** The other 149 blocks parse fine in that position.
- **Mechanism (module ops):** `ReplaceModule`/`RemoveModule` call `removeModuleInfo(tag)` on the object's template and throw `INI_INVALID_DATA` when the template doesn't exist yet or the tag is absent. A single Object-dir file sorts at "f", so most target templates (defined by monoliths that parse later) don't exist yet at that point.
- **Mechanism (Weapon blocks):** `WeaponStore` initialises *after* `ThingFactory` (`GameEngine.cpp`: ThingFactory ~line 749, WeaponStore ~line 767), so no weapons exist when an Object-dir file parses. A `Weapon` block for a weapon that exists later hits the duplicate guard in `WeaponStore::parseWeaponTemplateDefinition`, which **returns without consuming the block body**; the orphaned field lines are then read as unknown top-level tokens and throw. Confirmed individually: blocks idx 9 and idx 106 restored alone onto the otherwise-clean variant both crash (`fixes/bisect/confirm-idx9.stderr.log`, `confirm-idx106.stderr.log`).

**Recorded suspects EXONERATED:**
- `Demo_GLAVehicleTechnicalChassisTwo/Three` **do exist** in vanilla — as `ObjectReskin` definitions in `DemoGeneral.ini` — and their blocks parse fine in the single-file position (DemoGeneral parses before "F…"). They were never the crash cause. (They resurface in §4 for a different, patch-config-only reason.)
- The `ObjectReskin` block idx 194 (with the `ReplaceTexture … ReforgedLaserPink.tga` line) parses fine — texture existence is not checked at parse time.
- AddModule-only blocks never crash; OCL names are **not** resolved at parse time. This is why the v3 phone variant still crashed after removing 10 OCL-referencing blocks: crash #1 was never an OCL block.

## 2. Phase 2 — module-op semantics: **THEY WORK**

Target `AirF_AmericaInfantryRanger` (the patch split file defines `SlowDeathBehavior ModuleTag_Death07`), delivered via the split-file route in patch config. Probes in `fixes/probes/`, logs `testbed/runs/p2*.stderr.log`:

- **P2d control** (split file unmodified): clean, 0 errors, 12,128 lines.
- **P2a** (overlay `ReplaceModule` with bogus tag `ModuleTag_BOGUS77`): **CRASH** — `[LINE: 432] Error reading field 'ReplaceModule'`. The op genuinely executes and validates the tag.
- **P2b** (real `ReplaceModule ModuleTag_Death07` installing `ModuleTag_Death07_Fix`, then a second overlay `RemoveModule ModuleTag_Death07_Fix`): **zero INI errors**, full load — the replacement was really installed (otherwise the remove would have thrown).
- **P2c** (`RemoveModule ModuleTag_Death07_Fix` *without* the preceding replace): **CRASH** at the `RemoveModule` field — the control proving P2b's pass was causal, not accidental.

**Verdict:** `AddModule`/`RemoveModule`/`ReplaceModule` take full effect in `INI_LOAD_OVERWRITE` mode whenever the target template already exists at parse time — which the split-append delivery guarantees (the base definition sits in the same file, above the overlay). No blocks are partial on module-op grounds.

## 3. Phase 3 — the package as built

Design (builder `fixes/work/build_package.py`, manifest `fixes/work/package-manifest.json`):

- **Every one of the 183 unique object targets has exactly one defining path in the Community Patch BIG** — so, contrary to the original plan, **zero monolith copies were needed**. Each Object block is appended verbatim as an overlay block at the end of the patch's split file for that object. The mod wins that path in patch config; in patch-free config the same entry parses in pass 2 on top of the retail template.
- **Weapons cannot be redefined in a second block** (§1), so the 7 Weapon blocks were edited **in place** into the patch's `Weapon.ini` (the phone runs patch-mounted; the patch's weapon set equals retail's). Edits: idx 9 `Lazr_PatriotMissileWeaponAir` (LaserName, FireFX), idx 10 `Lazr_PatriotMissileAssistWeapon` (LaserName, FireFX), idx 106 `DragonTankFlameWeaponUpgraded` (MinimumAttackRange), idx 107 `ArtilleryBarrageDamageWeapon` (RadiusDamageAffects), idx 108 `GattlingBuildingGunAirDummy` (AcceptableAimDelta), idx 119 `Infa_MiniGunnerGunAir` (FireSound), idx 196 `SupW_AuroraFuelBombWeapon` (ProjectileDetonationOCL + ProjectileDetonationFX inserted). A few field edits were no-ops where the patch already carried the Reforged value.
- **Reskin idx 194** (`ObjectReskin SupW_SDILasers`): appended to SDILasers' split file with **only the `ReplaceTexture … ReforgedLaserPink.tga` line dropped** (that texture does not exist on the phone); the rest of the block is delivered.
- **Excluded:** idx 191/192/193 (see §5).

**Dispositions of the 221 blocks:** 210 split-append · 7 weapon-inplace · 1 reskin-append · 3 excluded.
**BIG entries:** 185 = 184 object split files + `Data\INI\Weapon.ini`. All payloads reparse/hash-verified at build time; the two clean full loads in §4 are the end-to-end proof.

## 4. Phase 4 — verification, and the one real defect class it caught

First full-package patch run (`pkg-patch`) had **exactly one** INI error:

```
[INI] ERROR in load('Data\INI\Object\faction\america\unit\americainfantrypilot.ini') - INIException: [LINE: 195 …] Error reading field 'RemoveModule'
```

Root cause (verified by reading both definitions): Fixes block idx 36 (`Object AmericaInfantryPilot`) does `RemoveModule ModuleTag_10`. Retail's Pilot *has* `LocomotorSetUpgrade ModuleTag_10`; **the Community Patch's Pilot split definition dropped that module**, so in patch config the op has nothing to remove and throws. A patch-vs-retail data divergence, not a delivery failure. Iterating the run → fix → re-run cycle surfaced **three** instances of this class, each fixed the same way: the missing retail module block is restored into the shipped base definition (top level, just before the base Object's closing `End`), after which the overlay op executes against it. **Final states match Reforged's intent exactly** (record: `fixes/work/augmentations.json`):

| Entry | Object | Restored module | Overlay op | Final state |
|---|---|---|---|---|
| Faction\America\Unit\AmericaInfantryPilot.ini | AmericaInfantryPilot | Behavior `LocomotorSetUpgrade ModuleTag_10` | `RemoveModule ModuleTag_10` | module absent (= patch state, = Reforged intent) |
| Faction\GLADemolition\Building\Demo_GLABarracks.ini | Demo_GLABarracks | Behavior `ModuleTag_Death17` | `RemoveModule ModuleTag_Death17` | module absent (= Reforged intent) |
| Faction\GLADemolition\Unit\Demo_GLAInfantryTerrorist.ini | Demo_GLAInfantryTerrorist | Behavior `ModuleTag_Death08` | `ReplaceModule ModuleTag_Death08` | `_Fix` behavior installed (= Reforged intent) |

Cautionary note for future work: the first automated fix-up inserted the Pilot module **before the first depth-1 `End` it found — which is the Draw block's DefaultConditionState End (file line 14)** — producing a *worse* crash (`Behavior` token inside a ConditionState). It was caught by GX_TRACE, the package was rebuilt from the deterministic builder, and the insertion was redone against the verified block skeleton (base Object closing End = the patch file's line 188). The loop's later "clean" verdicts during the environment incident (§6) were likewise discarded; only `run-probe.sh` logs read directly were trusted.

**Reskin exception (2 blocks):** `Demo_GLAVehicleTechnicalChassisTwo/Three` are `ObjectReskin`s of ChassisOne. Their Fixes blocks are a single `ReplaceModule ModuleTag_Death_18` — but a reskin template does not carry the *inherited* tag at INI parse time, so the op throws in the split-file position (patch run `pkg-patch-3`, line 191). All three chassis blocks in FixesReforged are **byte-identical**, and ChassisOne (the full object, the reskin source) accepted its `ReplaceModule` cleanly — reskins inherit the source's modules, so the fix reaches Two/Three through One. The two un-executable ops were dropped from their entries and replaced with an explanatory comment in the file. (First drop attempt left an orphaned `End` — the `ReplaceModule` nesting level — which crashed the next run and was removed; runs `pkg-patch-4`/`pkg-patch-5` bracket the fix.)

**Final verification (shipped file, `ca0b8430…`):**

Patch config (`testbed/runs/pkg-patch-5.stderr.log`, 12,126 lines, rc=134):
```
[INI] load('Data\INI\Object\faction\america\unit\americainfantrypilot.ini') END
[INI] load('Data\INI\Mouse.ini') END            ← last file of the load
Buffer allocation failed / Aborted              ← known post-load lavapipe stage
[INI] ERROR count: 0
```
(Patch-only control P2d was 12,128 lines — the package adds no load failures and loses no files.)

Retail config (`testbed/runs/pkg-retail-1.stderr.log`, 2,741 lines, rc=134): **0 `[INI] ERROR`**; our split entries parse in pass 2 there too (`americainfantrypilot.ini` START→END present), load runs to `Mouse.ini` END.

**Fingerprint probes** (probe copies only, +37 comment lines appended per entry; `[INI] load … processed total` per file, `fixes/work/fingerprint.py`):

| Entry | Clean | Probe (patch) | Probe (retail) |
|---|---|---|---|
| USA — AmericaInfantryPilot | 6 | **43** | **43** |
| China — Infa_ChinaInfantryHacker | 8 | **45** | **45** |
| GLA — Demo_GLABarracks | 6 | **43** | **43** |

Exactly +37 in both configs (logs `probe-patch`, `probe-retail`, both also 0 INI errors): our entries are the parsed copies at their pass positions in both worlds.

## 5. What this package does NOT deliver (explicit)

1. **Idx 191/192/193 — the small `AirF/Lazr/SupW_AmericaParticleCannonUplink` blocks (whole blocks, 3).** Their death-module OCLs (`AirF/Lazr/SupW_OCL_ParticleUplinkDeathFinal`, plus `SupW_OCL_SDILinkLasers` in idx 193) exist only in Reforged's `ObjectCreationListReforged.ini`, which this package does not ship. Retail and patch OCL sets are identical (294 names); exactly those 4 names are missing from both. (The large Draw-swap Uplink blocks idx 216–220 reference no missing OCLs and **are** delivered.)
2. **One line of idx 194:** `ReplaceTexture … ReforgedLaserPink.tga` — the texture is Reforged-only content the phone doesn't have. The rest of the reskin block is delivered.
3. **The ChassisTwo/ChassisThree `ReplaceModule ModuleTag_Death_18` ops as written** — un-executable against a reskin template in this engine (§4). Their *effect* is delivered via the identical block on the reskin source, ChassisOne.

Nothing else is missing: no block is partial on module-op grounds (§2), and the three §4 augmentations reach exactly Reforged's intended final states.

## 6. Environment incident (for reproducibility)

Mid-verification the VM lost two system pieces the testbed needs — the FFmpeg 6.x libraries (`libavcodec.so.60` etc.) and `mesa-vulkan-drivers` (lavapipe ICD) — fallout from the testbed setup's long apt run never completing. Symptoms were misleading (engine "clean" runs that never started; an SDL window FATAL). Both were restored from the local apt cache (`dpkg -i` of the cached .debs; `ldd` clean, `lvp_icd.json` back). Two fix-up-loop verdicts from that window were false and were thrown away; every claim in §4 rests on `run-probe.sh` logs inspected directly. If the testbed ever "passes" in seconds with a tiny log again, suspect this first.
