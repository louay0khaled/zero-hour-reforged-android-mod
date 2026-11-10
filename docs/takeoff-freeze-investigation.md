# Takeoff Freeze Investigation — jets stall at the airfield side-exit taxi

**Date:** 2026-11-10 (urgent subagent mission)
**Trigger:** owner, phone, fixes v3 + balance v1 installed: «في خطأ بإقلاع الطائرات بتجمد لما تطلع», clarified: **all** jets freeze **when they come out from the side** — leaving their parking spots toward the runway, not on the lift-off roll. Screenshot: Air Force base, Raptors parked on the apron ~10 min into a match, game itself running (58 fps counter).

## Verdict (up front)

**Outcome (A) — our shipped data caused it, via an engine-coupling the data silently assumes.**

- **Implicated entry:** `Data\INI\Locomotor\ReforgedBalance.ini` in `!ReforgedBalance-v1.big` — the **`Locomotor BasicJetTaxiLocomotor`** override block, the one taxi template every jet in the game shares (`Locomotor = SET_TAXIING BasicJetTaxiLocomotor` in every faction's air file).
- **Implicated fields (shipped → base):** `Appearance FOUR_WHEELS → TREADS`, `Braking 50 → 999999`, `TurnRate 120 → 180`, `TurnRateDamaged 120 → 180`. The shipped values are **verbatim Reforged** (BalanceReforged.ini:554) — the translation was faithful; the defect is that Reforged authored these values **for its own rewritten locomotor drive, which does not exist in MYSOREZ** (see §3). On the host's stock wheeled drive, a jet leaving a side parking spot cannot complete the first tight taxi turn and is braked to a permanent stop by the drive's own anti-donut failsafe.
- **Not a frame-rate artifact:** all implicated values are per-second quantities (dist/sec², deg/sec) with identical meaning at 30 Hz and 60 steps/s. The missing piece is a code path, not a unit conversion; the stall would occur on this engine at any step rate.
- **Fix built and gate-verified:** `!ReforgedBalance-v2.big` — v1 with exactly that one block withheld (see §5). The fixes package is **not** implicated (it ships no Locomotor entry and no airfield entry at all).

---

## 1. Inventory — every aircraft-relevant delta in both packages

### 1a. The balance package's 2 locomotor edits (`Data\INI\Locomotor\ReforgedBalance.ini`, 1,093 B)

Host parse semantics (MYSOREZ `Locomotor.cpp:607`, `LocomotorStore::parseLocomotorTemplateDefinition`): a same-named block is found by name and its fields are parsed **into the existing template** — a field-level override. So an override block changes exactly the fields it names; everything else keeps its base value.

**Edit 1 — `BasicJetTaxiLocomotor` (an OVERRIDE of an existing shared template) — THE CULPRIT.**

| Field | Retail base (`Data_INI_Locomotor.ini:3127`) | Patch base (patch `Locomotor.ini:2615`) | Reforged source (`BalanceReforged.ini:554`) | Shipped in balance v1 |
|---|---|---|---|---|
| Surfaces | GROUND | GROUND | — (inherited) | — (inherited) |
| Speed / SpeedDamaged | 50 / 50 | 50.0 / 50.0 | — | — |
| Acceleration(/Damaged) | 100 / 100 | 100.0 / 100.0 | — | — |
| MinTurnSpeed | 0 | 0.0 | — | — |
| ZAxisBehavior | NO_Z_MOTIVE_FORCE | NO_Z_MOTIVE_FORCE | — | — |
| **Appearance** | **TREADS** | **TREADS** | **FOUR_WHEELS** | **FOUR_WHEELS** |
| **Braking** | **999999** | **999999.0** | **50** | **50** |
| **TurnRate** | **180** | **180.0** | **120** | **120** |
| **TurnRateDamaged** | **180** | **180.0** | **120** | **120** |

Retail and patch bases are identical — the patch never touched this template, so the delta is ours alone in both configurations. Shipped = Reforged verbatim (field-for-field, confirmed against `audit/reforged/.../BalanceReforged.ini` lines 554–560). Authorship: **Reforged**, not our translation. EA's own comment on the retail template states the design intent Reforged reversed: `Appearance = TREADS ; so we can turn in place...`.

**Edit 2 — `SCUDStormMissileHighLocomotor` (a NEW template).** Absent from retail and from the patch (0 hits in both `Locomotor.ini` files); referenced only by the balance Scud Storm missile objects' in-segment `Locomotor = SET_NORMAL SCUDStormMissileHighLocomotor`. Air-surface THRUST missile locomotor — no interaction with jets, airfields, or taxi. **Cleared.**

### 1b. Per-object aircraft blocks, both packages (full census — appendix method in §6)

Every aircraft entry in both packages was extracted and its appended overlay censused for takeoff-path constructs (`JetAIUpdate` fields, `Locomotor =` lines, `PhysicsBehavior`, `Body`):

- **Fixes v3 (18 aircraft entries):** overlays contain only `ArmorSet` (countermeasures armor on upgrade), `UnitSpecificSounds`, `SoundAmbient`, a portrait/cameo line — **no JetAIUpdate field, no locomotor line, no physics, anywhere.** It also ships **no Locomotor-store entry and no Airfield entry at all** (entry-list grep: zero hits for `locomotor`/`airfield`).
- **Balance v1 (54 aircraft entries):** fixed-wing jets carry only `SubObjectsUpgrade` (visual flare/armor subobjects), `ArmorSet`, `UnitSpecificSounds`, and `JetSlowDeathBehavior` replacements (death/crash FX+OCL only — active after the jet is already destroyed). **No fixed-wing jet block in either package touches JetAIUpdate data, a locomotor assignment, or physics.**
- **The single exception class — the three Comanches** (`AmericaVehicleComanche` + AirF/Lazr variants): their balance overlays **do** replace the AI module (hence the `JetAIUpdate` census flag — helicopters share the JetAIUpdate class) and received the standard locomotor repairs, which restate the object's **own base lines verbatim** (`SET_NORMAL ComancheLocomotor`, `SET_TAXIING BasicHelicopterTaxiLocomotor`, per `balance-manifest.json`). `BasicHelicopterTaxiLocomotor` itself was **not** overridden by either package. Helicopters do not use the runway or `BasicJetTaxiLocomotor`. **Cleared** (and not the reported symptom: owner says jets, from the airfield side spots).
- **The Airfield object itself:** neither package ships any airfield entry (the only Building entries in balance v1 are China bunkers/cannons/towers, GLA buildings, tunnels — no `AmericaAirfield`/`ChinaAirfield`; fixes v3 ships none). `ParkingPlaceBehavior` data, parking/runway geometry, and production-exit data are **stock** in the owner's install. **Cleared.**
- **Locomotor repairs (35) in balance v1:** sets restated on AI-module replacements — Comanche (above) plus ground vehicles/missiles. Gate (ii) of the balance mission proved no object's locomotor **sets** changed vs baseline; and no repair touches the taxi **template's fields**. **Cleared.**

**Net inventory result:** exactly ONE shipped delta sits on the shared takeoff path — the `BasicJetTaxiLocomotor` override of §1a.

---

## 2. The taxi path, from the host's code (MYSOREZ `JetAIUpdate.cpp`)

`JetOrHeliTaxiState` (line 474) drives the parking→runway phase with `LOCOMOTORSET_TAXIING` selected (line 505). For `FROM_PARKING` on a normal airfield (lines 567–581) it hand-builds a 2–3 node path:

1. *(only when the parking heading differs from the runway direction by > PI/128 — i.e. the normal side-spot case)* an **intermediate point**: the intersection of the line out of the parking spot along the parking heading with the perpendicular through `runwayPrep` — a short first leg straight out of the spot, then a sharp turn;
2. `runwayPrep`;
3. `runwayStart`.

The state demands precision: `setAdjustsDestination(false)` — *"precision is necessary"* — and sets the locomotor `setUltraAccurate(true)` (lines 640–644). The state succeeds only when the locomotor actually delivers the jet onto these nodes. With the stock **TREADS** template this is trivial: the treads drive rotates the jet in place toward each node (`rotateTowardsPosition` first thing in `moveTowardsPositionTreads`, `Locomotor.cpp`), `Braking 999999` stops it dead exactly on the node, and the braking-snap in `locoUpdate_moveTowardsPosition` settles it precisely.

## 3. Why FOUR_WHEELS stalls it on this engine — and why Reforged's engine doesn't

**The host's wheeled drive** (`Locomotor::moveTowardsPositionWheels`, MYSOREZ `Locomotor.cpp`) is EA's truck drive, with three properties that combine into a permanent stall at the side-exit turn:

1. **No turning in place.** *"Wheeled vehicles can only turn while moving"* — turn authority scales with `actualSpeed/turnSpeed` (turnSpeed floored at maxSpeed/4 = 12.5). From a standstill in a parking spot, facing along the parking heading, the jet must describe a driving arc to change heading.
2. **The >15° projection veto.** When the relative angle to the goal exceeds 15° (`FIFTEEN_DEGREES`), the drive projects its turning arc ½ second ahead (`halfPos`, `nextPos`); if either projected point is on terrain the pathfinder deems invalid for this locomotor, it applies **zero motive force and returns** — rotation only, no drive. Around an airfield's side spots the arc readily crosses the building's blocked footprint cells (the jet ignores its producer as a *collision* obstacle, but `validMovementTerrain` is a terrain check, not a collision check).
3. **The anti-donut failsafe converts circling into a freeze.** `DONUT_DISTANCE = 4.0 * PATHFIND_CELL_SIZE_F` (= 40 units), `DONUT_TIME_DELAY_SECONDS = 2.5` (`Locomotor.cpp:55–56`): while `onPathDistToGoal < 40`, a timer runs; once expired, `IS_BRAKING` is forced, and with Braking = 50 the braking branch drives `goalSpeed = actualSpeed − getBraking()` → **0**. The first taxi leg (parking spot → intermediate point) is short and the tight corner keeps the jet inside donut distance of its node while it maneuvers — 2.5 s is nothing. The jet brakes to a stop and the move state neither completes (it never lands precisely on the node under ultra-accurate rules) nor fails. **Frozen at the side exit — for every jet, at every airfield, every time.** Exactly the owner's report, including "all of them" (one shared template) and "from the side" (the FROM_PARKING path with its intermediate-point turn; the takeoff roll itself, once reached, is a straight line and would work).

**Reforged's engine carries the other half of this change.** Reforged's own comment over the very block we shipped (`BalanceReforged.ini:545–552`):

> "On four wheels it drives the vehicle drive (**Locomotor::isGroundVehicle**), which is now the jet's alone: it brakes for a corner and rounds it, **crawls round one too tight for its turning circle instead of spinning**, and slows to a stop at the end of the taxi. **Turning on its spot** to its parking heading or onto the runway eases in and out (**Locomotor::locoUpdate_moveTowardsAngle**). Speed is EA's. Scenarios/jetrunway.txt has the numbers."

And in Reforged's `Locomotor.cpp`: `isGroundVehicle(obj)` is defined as `obj->isKindOf(KINDOF_AIRCRAFT) && m_template->m_appearance == LOCO_WHEELS_FOUR` (line ~1224) — *"Only a jet taxiing on its nose wheel (BasicJetTaxiLocomotor in BalanceReforged.ini), with the precision its taxi asks for"*; taxiing jets get a special tight steering radius `JET_TAXI_MIN_RADIUS_BODY_LENGTHS = 0.75f` (*"an airfield's taxiway corners are a jet's length apart"*, line 83) and helicopter-style spot turning in the drive (line 1149). **MYSOREZ contains no `isGroundVehicle` symbol at all** (grep over its `Locomotor.cpp`/`.h`: zero hits) — none of this machinery exists on the host. The data block is only half of a data+engine feature; we shipped the data half.

**Classification.** This is filed as **(A)** because the proximate, correctable cause is a data entry we shipped, and reverting it fully restores stock behavior on this host. The mechanism has a (B) flavor — the host engine behaves exactly as EA designed for trucks; it is not a MYSOREZ bug — but the taxonomy's (B) ("engine bug our data merely exposes") does not fit: nothing in the host is defective. The accurate one-liner for the owner: **the balance package included one Reforged change that only works with Reforged's engine code, which the port doesn't have; the data is now withheld until that engine work is ported (an M2 item), at which point the block can be re-enabled.**

### Ranked suspects
1. **`BasicJetTaxiLocomotor` override (balance v1)** — proven mechanism, matches every element of the report (all jets / side exit / permanent stop / game otherwise healthy). **Confidence: high.**
2. Everything else shipped — excluded by the §1 census: no other takeoff-path delta exists in either package.
3. Stock host behavior — excluded: with the override withheld (v2), taxi uses the identical template the port has always run; the owner's pre-balance play (fixes v3 period, phone-verified) had working jets.

---

## 4. Fix — `!ReforgedBalance-v2.big`

Built by post-processing v1: **all 301 entries byte-identical to v1 except** `Data\INI\Locomotor\ReforgedBalance.ini`, from which only the `Locomotor BasicJetTaxiLocomotor … End` block was removed (the new `SCUDStormMissileHighLocomotor` definition is kept intact; a comment in the file records why the taxi override is withheld on this host). Effective result: jets taxi on the untouched base template (TREADS, Braking 999999, TurnRate 180) in both configurations; every other balance change is preserved.

- **Path:** `~/workspace/projects/reforged-android/m1/!ReforgedBalance-v2.big`
- **Size:** 3,195,419 bytes · **Entries:** 301
- **SHA-256:** `96bae34477b9bf38ee1f78e32915da99b8a2243fa476712f96ba1bce0c76e7f4`
- **Install:** replaces balance v1 (same mods folder; disable/delete v1, enable v2; fixes v3 stays).

### Four gates — combined state (fixes v3 + balance v2), both configurations

| Gate | Patch-mounted (marker) | Patch-free retail |
|---|---|---|
| (i) Full INI load | **0 `[INI] ERROR`** (14,302 log lines; in-log proof: "community patch mounted anyway (launcher switch)") | **0 `[INI] ERROR`** |
| (ii) Locomotor audit | table **identical to v1-combined final**; vs fixes-only baseline exactly the same +3 known NOAI lines (`Reforged_BigJetCrashImpact`, `Reforged_JetCrashFire`, `Reforged_JetCrashImpact`) | identical to v1-combined final; same +3 vs baseline |
| (iii) Reference audit | **UNRESOLVED = 0** (refs=4130, resolved-both=4122, engine-resolved=7, inherited-retail=1 `CraterDebris` — same totals as v1) | (same run covers both configs) |
| (iv) Instantiation audit | total=2121, **ok=2119**, crash set = baseline pair only (`CabooseFullOfTerrorists`, `Infa_ChinaBunker`) | total=2119, **ok=2117**, crash set = baseline pair only |

Gate runs: `testbed/runs/balv2-patch.stderr.log`, `balv2-retail.stderr.log` (runner `run-probe2.sh` with `BALBIG` = v2), `inst-balv2comb-patch/retail` (driver = `run-inst2.sh` variant staged on v2), reference audit = `gate_ref_balance.py` repointed at v2.

**Residual risk (stated plainly):** the gates prove data integrity, not gameplay — the testbed cannot run a match. The phone check is one minute: enable v2 instead of v1, build any jet, and watch it taxi out of its side spot and take off. Expected: stock taxi behavior (pivot-and-go), all balance numbers unchanged. If jets *still* stall with v2, the next suspect would be outside both packages — but per §1 no other shipped delta can produce this symptom.

---

## 5. Appendix — census method

For every entry under `Data\INI\Object\` in each package whose name matches `Jet|Comanche|Helicopter`, the appended overlay section (after the builder's `; ==== Reforged (fixes|balance) overlay` marker) was scanned for `Behavior =` types and for the takeoff-path constructs `JetAIUpdate`, `Locomotor =`, `Physics`, `Body =`, plus `ArmorSet`/`UnitSpecificSounds`. Spot-checked in full text: Raptor (fixes: ArmorSet only; balance: 2× SubObjectsUpgrade), MIG (balance: 2× SubObjectsUpgrade), Aurora & Stealth Fighter & CargoPlane (balance: JetSlowDeathBehavior + SubObjectsUpgrade; Stealth fixes: sounds only), and all four "empty-tag" overlays (SpectreGunship1, SupW Aurora, CarpetBomber ×2) — portraits/cameos/voices/ambient sound only. Full per-file results are reproducible with `bigtool.py` + the markers; headline counts: fixes v3 — 18 aircraft entries, zero takeoff-path constructs; balance v1 — 54 aircraft entries, takeoff-path constructs only in the 3 Comanche overlays (AI-module replacement + own-base locomotor restatements; helicopter taxi template not overridden).

## 6. Evidence index
- Shipped files: `m1/!ReforgedBalance-v1.big` (Locomotor entry, 1,093 B), `m1/!ReforgedFixes-v3.big` (no Locomotor/Airfield entries).
- Bases: `zh-kotlin-engine/out/extract/Data_INI_Locomotor.ini:3127` (retail); patch `Locomotor.ini:2615` (from `500_900_CommunityPatch_CoreINI.big`).
- Reforged data: `audit/reforged/GeneralsMD/Code/Data/INI/BalanceReforged.ini:545–560`.
- Reforged engine: `audit/reforged/.../GameLogic/Object/Locomotor.cpp:60, 83, 1149, 1224–1245`.
- Host engine: `testbed/src/GeneralsMD/Code/GameEngine/Source/GameLogic/Object/Update/AIUpdate/JetAIUpdate.cpp:474–693`; `.../Object/Locomotor.cpp:55–56, 607–640, 948+, moveTowardsPositionWheels, moveTowardsPositionTreads`.
