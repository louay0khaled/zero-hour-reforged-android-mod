# ReforgedFixes v3 — reference audit, instantiation audit, and the corrected package

**Date:** 2026-11-10 (subagent mission, second corrective round)
**Artifact:** `~/workspace/projects/reforged-android/m1/!ReforgedFixes-v3.big`
**Entries:** 188 (v2's 185, byte-identical, + 3 new definition files)
**Size:** 2,620,655 bytes
**SHA-256:** `4dffe0243977b3a20e190631d07fcfb1869172c3af3a4361422b4c54ce8b891b`
**Supersedes:** v2 (`971692b0…`, UNSAFE — crashes a fresh skirmish) and v1 (`ca0b8430…`, UNSAFE). The v6 data mod remains the safe package until v3 passes the owner's phone test.

**Verdict: v3 passes the full gate suite in both configurations** (patch-mounted with marker; patch-free retail): zero INI errors, locomotor audit identical to baseline, zero unresolved delivered references, and every instantiable template constructs — including `Demo_GLACommandCenter`, whose v2 construction crash (the phone crash) is reproduced locally on v2 and gone on v3.

---

## 1. What killed v2 (confirmed, reproduced locally)

Owner report 2026-11-10 10:47: v2 installed, new skirmish → immediate crash:
`GameLogic::tryStartNewGame → ThingFactory::newObject → Object::Object → ModuleFactory::newModule → OCLSpecialPower ctor → SpecialPowerModule::SpecialPowerModule +112`.

Root cause: `SpecialPowerModule`'s constructor dereferences `getSpecialPowerTemplate()->isSharedNSync()` for any object not under construction. `INI::parseSpecialPowerTemplate` resolves the name at parse time and stores **nullptr** when the name does not exist in the loaded data — silently, with no `[INI] ERROR`. Names therefore resolve lazily at object construction, a class neither the parse gate nor the v2 locomotor audit could see. v2 delivers an `OCLSpecialPower` module (`ModuleTag_11Demo_Fix`, AddModule) on `Demo_GLACommandCenter` naming `Demo_SuperweaponRebelAmbush`, a SpecialPowerTemplate that exists **only in Reforged's own data** — not in retail ZH data, not in the Community Patch. Command Centers are created at match start → instant crash.

Local reproduction (testbed, patch config, v2 mounted), stack captured under gdb:

```
[INSTAUDIT] TRY Demo_GLACommandCenter
Thread 1 "GeneralsXZH" received signal SIGSEGV
#0 SpecialPowerModule::SpecialPowerModule (…) SpecialPowerModule.cpp:116
#1 OCLSpecialPower::OCLSpecialPower (…) OCLSpecialPower.cpp:152
#2 OCLSpecialPower::friend_newModuleInstance (…) OCLSpecialPower.h:88
#3 Object::Object (…) Object.cpp:412
#4 GameLogic::friend_createObject (…) GameLogic.cpp:4645
#5 ThingFactory::newObject (…) ThingFactory.cpp:340
```

Frame-for-frame the phone's crash chain.

---

## 2. Part 1 — Reference audit (the new gate)

**Method.** Delivered content = line-multiset delta of the package's entries against the Community Patch BIG entries (8,000 delivered lines for v2; paths absent from the patch count in full). Definition corpora use **per-path winner layering**: retail config = INIZH.big per-path over Ini.big (+ PatchINI); patch config = the patch's copy wins per path, retail winners fill paths the patch lacks. Every name-bearing field in the delta was censused and classified against the MYSOREZ parse tables (which fields store pointers at parse, which take phase tokens, which are strings only). Tools: `fixes/work/refaudit.py`, `refaudit2.py`, `refaudit3.py`, `gate_ref.py`; data in `fixes/work/refs/`.

**Result for v2: 302 references extracted; exactly 12 distinct names unresolved in both configurations** — all Reforged-only, all pure data:

| # | Store | Name | Referenced by (delivered block) | Reforged definition |
|---|-------|------|----------------------------------|---------------------|
| 1–9 | ObjectCreationList | `AirF_SUPERWEAPON_Paradrop1/2/3`, `Lazr_SUPERWEAPON_Paradrop1/2/3`, `SupW_SUPERWEAPON_Paradrop1/2/3` | `OCL =` / `UpgradeOCL =` in the replaced OCLSpecialPower modules of `AirF_AmericaCommandCenter`, `Lazr_AmericaCommandCenter`, `SupW_AmericaCommandCenter` | `ObjectCreationListReforged.ini` |
| 10 | SpecialPower | `Demo_SuperweaponRebelAmbush` | `SpecialPowerTemplate =` in `ModuleTag_11Demo_Fix` on `Demo_GLACommandCenter` — **the v2 crasher** | `SpecialPowerReforged.ini` |
| 11–12 | Science | `Demo_SCIENCE_RebelAmbush2`, `Demo_SCIENCE_RebelAmbush3` | `UpgradeOCL =` pairs in `Demo_GLACommandCenter`'s delivered module | `ScienceReforged.ini` |

**Chain root (13th definition shipped):** the shipped power's `RequiredScience = Demo_SCIENCE_RebelAmbush1` is itself Reforged-only (retail has plain `SCIENCE_RebelAmbush1-3` and the Chem sciences, but no `Demo_SCIENCE_*`). All three Demo ambush sciences were shipped so the chain works end to end: Ambush1 (prereq `SCIENCE_GLA` + `SCIENCE_Rank3`) → Ambush2 → Ambush3, cost 1 each.

**Recursive audit of the ship set:** every inner reference of the 13 definitions resolves in both configurations — the Paradrop OCLs' `Transport`/`PutInContainer`/`Payload` objects (`AmericaJetCargoPlane`, `AmericaParachute`, the three generals' Rangers) and the sciences' prerequisites (`SCIENCE_GLA`, `SCIENCE_Rank3`) are all retail. Zero unresolved.

**Cleared suspects** (named by delivered blocks, verified defined in both configs): `SuperweaponParadropAmerica`, `SuperweaponChinaCarpetBomb`, `Nuke_SuperweaponChinaCarpetBomb`, `Early_SuperweaponChinaCarpetBomb`, `Chem_SuperweaponRebelAmbush`, `SuperweaponParticleUplinkCannon`, `SuperweaponArtilleryBarrage`, all `SpecialAbility*` powers, the `Demo_SUPERWEAPON_RebelAmbush1/2/3` OCLs, and all Weapons/Armors/Locomotors/FXLists referenced. Two audit artifacts were resolved as non-defects: `Upgrade_Veterancy_*` names (9 refs) are **synthesized by the engine itself** (`"Upgrade_Veterancy_" + level` in CrateSystem and friends; retail data references them the same way with no template definition), and `Weapon = FINAL <name>` lines are a phase token + name, not a weapon named "FINAL".

---

## 3. Part 3 — How v3 satisfies every reference (no neutralizations)

v3 = v2's 185 entries byte-identical + **3 new directory-form definition files** carrying the verbatim Reforged definitions (byte-faithful extraction from the Reforged sources, GPL-3.0):

| New entry | Bytes | SHA-256 (payload, first 16) | Contents |
|---|---|---|---|
| `Data\INI\SpecialPower\ReforgedMissing.ini` | 605 | `e7a4b4f0d45858e4` | `SpecialPower Demo_SuperweaponRebelAmbush` |
| `Data\INI\ObjectCreationList\ReforgedMissing.ini` | 9,257 | `57452cc987504b7b` | the 9 Paradrop OCLs |
| `Data\INI\Science\ReforgedMissing.ini` | 976 | `2e5f21b50851596a` | `Demo_SCIENCE_RebelAmbush1/2/3` |

**Why this route wins in both configurations** (loader mechanics verified in the MYSOREZ `INI.cpp`): each data store loads **both** the monolith `Data\INI\<Store>.ini` (winner per path) **and** every directory file `Data\INI\<Store>\*.ini`. Directory files from lower archives are suppressed only when the monolith itself came from a mod source (GX form-masking); here the monoliths come from the patch / retail, so mod directory files load additively in both configs, and the 13 names collide with nothing in either. Parse logs confirm loading in both configurations:

```
[INI] load('Data\INI\Science\reforgedmissing.ini') START … END
[INI] load('Data\INI\ObjectCreationList\reforgedmissing.ini') START …
[INI] load('Data\INI\SpecialPower\reforgedmissing.ini') START …
```

No reference had to be neutralized: all 13 definitions are pure data.

---

## 4. Part 2 — Instantiation audit (testbed)

**Harness** (testbed-only, never shipped): `ThingFactory::testbedInstantiateAudit()` — declared beside the v2 locomotor audit, called from `GameEngine::init` after `TheMapCache` creation, gated on `GX_INSTAUDIT`; driver `testbed/run-inst.sh`. It constructs **every** ThingTemplate once via `ThingFactory::newObject` with an empty status mask (not under construction — the phone's crash path). Design decisions, each forced by a measured failure:

- **No forking:** the engine is multithreaded by audit time; forked children inherit other threads' locked allocator futexes and block forever (16/16 children hung). Attribution instead works by **restart**: a crash kills the process with the last `[INSTAUDIT] TRY <name>` line naming the template; the driver records it, adds it to `GX_INST_SKIP`, and relaunches. A 25 s SIGALRM watchdog reports hangs the same way (`[INSTAUDIT] HANG`).
- **Scaffolding a faithful pre-game state** (each item is something a real `startNewGame` provides before creating objects):
  - a real map loaded (`maps\Tournament Desert\Tournament Desert.map` via `TheTerrainLogic->loadMap`) + `Pathfinder::newMap()` — the AIUpdate ctor picks a locomotor through the pathfinder grid, which exists only with a map;
  - `GameClient::reset()` — sizes the drawable lookup vector; without it the first Drawable registration spins forever (`resize(size*2)` never grows an empty vector);
  - a fabricated team: `TeamFactory::initTeam` with an empty Dict registers a `TeamPrototype` owned by the neutral player, then `createTeam` — mandatory because `Object`'s ctor unconditionally calls `getControllingPlayer()->getProductionVeterancyLevel(...)`.
- The audit hook sits after `TheMapCache` creation in `GameEngine::init` because `W3DTerrainLogic::loadMap` refuses to run without it.

**Baselines (must be clean — they define the exclusion set):**

| Config | Templates | OK | Baseline crashers |
|---|---|---|---|
| Patch-mounted, no mod | 2,117 | 2,115 | `CabooseFullOfTerrorists`, `Infa_ChinaBunker` |
| Retail, no mod | 2,115 | 2,113 | `CabooseFullOfTerrorists`, `Infa_ChinaBunker` |

Both baseline crashers are harness-context artifacts, stack-verified, and crash identically with **no mod installed**: `CabooseFullOfTerrorists`' `GarrisonContain::onObjectCreated` spawns its occupants with a null team (a campaign prop never created by bare `newObject` in real play); `Infa_ChinaBunker`'s `GenerateMinefieldBehavior` places mines during construction via an UpgradeMux self-upgrade and dereferences a null in `PartitionManager::getClosestObjects` (challenge-mode object, pre-placed by map scripts in real play). They are excluded from the mod verdict in every config.

**v2 results (the defect, isolated):**

| Config | Templates | OK | Crash set |
|---|---|---|---|
| Patch-mounted + v2 | 2,118 | 2,115 | baseline pair + **`Demo_GLACommandCenter`** |
| Retail + v2 | 2,116 | 2,113 | baseline pair + **`Demo_GLACommandCenter`** |

Exactly one mod-caused crasher, in both configs, with the phone's stack (§1). No siblings: every other delivered-block object constructs — the Paradrop/carpet-bomb Command Centers' power templates exist, and their missing OCLs are activation-time references that gate 1 (not construction) covers.

---

## 5. Gate suite on v3 — both configurations

| Gate | Patch-mounted (marker) | Patch-free retail |
|---|---|---|
| (i) Full INI load, zero `[INI] ERROR` | **0 errors** (`audit-v3-patch`, 14,252 log lines) | **0 errors** (`audit-v3-retail`, 4,865 lines) |
| (ii) Locomotor audit vs un-modded baseline | identical except the package's own `SupW_SDILasers NOAI` line (2,107 vs 2,106 rows) | identical except the same line (2,105 vs 2,104 rows) |
| (iii) Reference audit (`gate_ref.py`) | **UNRESOLVED=0** (refs=302, resolved-both=293, engine-resolved=9) — same run covers both configs by construction | (same) |
| (iv) Instantiation audit | total=2,118, **ok=2,116**, crash set = baseline pair only; `[INSTAUDIT] OK Demo_GLACommandCenter CREATED` | total=2,116, **ok=2,114**, crash set = baseline pair only; `[INSTAUDIT] OK Demo_GLACommandCenter CREATED` |

Package verification: builder reparsed the written BIG and confirmed all 188 entry payloads byte-equal to intent (185 inherited from v2 + 3 new). Size 2,620,655 B; SHA-256 `4dffe0243977b3a20e190631d07fcfb1869172c3af3a4361422b4c54ce8b891b`.

---

## 6. Residual risk — stated plainly

- **The instantiation audit is a construction proxy, not live gameplay.** It proves every template's constructors (the v1 and v2 crash classes) run clean in a map-loaded, team-owned state. It does not run game frames: activation-time behavior of the newly shipped definitions (a Paradrop actually dropping, the Demo ambush actually firing) is exercised only in a real match. The definitions are byte-verbatim Reforged data and every name they reference resolves in both configs, so behavioral parity with Reforged is by construction — but the owner's phone test (fresh skirmish start — the exact moment v2 died — plus, ideally, firing the Demo ambush and a Paradrop once) remains the final gate.
- **Cosmetic:** the three new sciences have no CSF display strings in retail/patch string tables (Reforged ships its own). The ScienceStore parses them fine; at worst a UI label for the Demo ambush sciences renders as a missing-string placeholder. No crash path touches this.
- **Out of scope, unchanged from v2:** the three FixesReforged blocks excluded in v1 (idx191–193, whose OCLs exist only inside Reforged's object files) remain undelivered.
- The two baseline-crash templates (`CabooseFullOfTerrorists`, `Infa_ChinaBunker`) crash on construction in **un-modded** data too, in this harness state; they are pre-existing engine/data quirks of objects that real games only ever create via map scripts, not a v3 concern.

## 7. Tools & evidence

- Builders/audits: `fixes/work/build_v3.py`, `fixes/work/refaudit.py`, `refaudit2.py`, `refaudit3.py`, `fixes/work/gate_ref.py`; audit data in `fixes/work/refs/` (incl. `candidates.json`).
- Testbed harness: `testbed/src` (`ThingFactory::testbedInstantiateAudit`, TESTBED-ONLY), `testbed/run-inst.sh`; logs in `testbed/runs/`: `inst-base-patch.log`, `inst-base-retail.log`, `inst-v2-patch.log`, `inst-v2-retail.log`, `inst-v3-patch.log`, `inst-v3-retail.log` (+ `.bad` crash lists), `audit-v3-patch.stderr.log`, `audit-v3-retail.stderr.log`.
