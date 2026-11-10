# v6 Verification — corrected mod built & proven locally (addendum to local-testbed-report.md)

Date: 2026-11-10. All work local, real MYSOREZ engine in the testbed, no phone involved.
Artifact: `~/workspace/projects/reforged-android/m1/!ReforgedData-v6.big`.

## 1. The patch's split file (entry b source)

- Source archive: `~/workspace/projects/zh-kotlin-engine/data/500_900_CommunityPatch_CoreINI.big`
  (12,828,460 B, 2,269 files).
- Entry: `Data\INI\Object\Faction\AmericaAirForce\Unit\AirF_AmericaTankMicrowave.ini`
  at offset 2,825,876 — **4,952 B, 160 lines, CRLF**, SHA-256
  `c9015f71ea3d164489be329f3fb429b6ea73014046bc6a09bba54b7d3e374183`.
- Read in full: it is a **complete, standalone Object definition** for `AirF_AmericaTankMicrowave`
  (`Object AirF_AmericaTankMicrowave` at line 1 through the closing `End` at line 160 — Draw,
  ArmorSet, WeaponSet, Body, all Behaviors, Geometry present). It is the file that re-set the
  field in run R6. Its cameo block (lines 4–8) ends with
  `UpgradeCameo5 = Upgrade_AmericaCompositeArmor` (line 8).

## 2. The one-line change

Exactly one line differs between the patch's split file and v6's copy (line-based diff, 160 lines both):

```
-UpgradeCameo5 = Upgrade_AmericaCompositeArmor
+UpgradeCameo5 = None
```

(line 8; everything else byte-identical, CRLF preserved). v6 split payload: 4,927 B,
SHA-256 `521e01454d96e4492dbf8c6a612dbd1c7de445f5f217305372385fdb1f4c35dc`.

## 3. The v6 BIG — construction & verification

Entries:
- (a) `Data\INI\Object\AirforceGeneral.ini` — the v5 payload, 717,934 B,
  SHA-256 `5633300f2f1c7a32e9c9bbbc0ffc33783bffe4b1dabb102f8c88a6377a3dd30d`
  (identical to `m1/AirforceGeneral-v5.ini` and to the payload inside `!ReforgedData-v5.big`,
  both hash-checked).
- (b) `Data\INI\Object\Faction\AmericaAirForce\Unit\AirF_AmericaTankMicrowave.ini` — §2 payload.

Built with `testbed/tools/bigtool.py`; verified by full reparse: BIGF magic ok, 2 files,
header total 723,004 == actual file size, and **both payloads' SHA-256 match their sources**.
`!ReforgedData-v6.big`: 723,004 B, SHA-256
`4f896bcf5a187f7dd4575f375d9d2c28482293fa14e99de22072b52aaab7be4b`.

A fingerprint twin (`v6work/!ProbeV6-Lines.big`, 724,003 B) is identical except entry (b)
carries 37 appended `;GXPROBE line fingerprint` comment lines (probe split payload SHA-256
`7122927cf3550928ca85b0de2d3c050f8c28e0f3b46a5c1314e3de628ca095c5`); it also reparse-verified.

## 4. Run R8 — fingerprint, R6 configuration (patch mounted + marker + probe v6, `!` game-root channel)

Log: `testbed/runs/r8-v6-fingerprint.stderr.log`. The phone-failing configuration, replicated:

```
[gxbig] mod !ProbeV6-Lines.big installed, community patch mounted anyway (launcher switch)
[gxbig] community patch mounted: .../GeneralsOnlineGameData/500_900_CommunityPatch_CoreINI.big
[INI] load('Data\INI\Object\airforcegeneral.ini') START
[INI] load - processed total 564 lines
...
[INI] load('Data\INI\Object\faction\americaairforce\unit\airf_americatankmicrowave.ini') START
[INI] load - processed total 39 lines
[INI] load('Data\INI\Object\faction\americaairforce\unit\airf_americatankmicrowave.ini') END
```

**39 = 2 (the patch copy's count in R6) + 37 (our fingerprint)** — the copy of the split file
parsed in the subdirectory pass is OURS, winner-per-path at the Faction path above the mounted
patch. Zero `[INI] ERROR` lines in the whole run.

## 5. Run R9 — no-patch configuration, clean v6

Log: `testbed/runs/r9-v6-nopatch.stderr.log`.

```
[gxbig] loaded: .../runtime/!ReforgedData-v6.big
[INI] load('Data\INI\Object\airforcegeneral.ini') START
[INI] load - processed total 564 lines
[INI] load('Data\INI\Object\faction\americaairforce\unit\airf_americatankmicrowave.ini') START
[INI] load - processed total 2 lines
[INI] load('Data\INI\Object\faction\americaairforce\unit\airf_americatankmicrowave.ini') END
```

No regression: the monolith parses at exactly 564 lines; the mod's own split file is enumerated
and parsed in pass 2 even with no patch present (2 lines = the Object block, clean payload, no
fingerprint); **zero `[INI] ERROR` lines**. (Run ends in the known post-load DXVK/lavapipe
abort — the testbed ceiling from the main report §1; all INI evidence precedes it.)

## 6. Proof chain & bottom line

No stronger in-engine observable for the final template value exists in this build (no template
dump/console), so the proof is the chain: (i) the previous report's §4 code verdict —
`ControlBar::setPortraitByObject` hides any cameo slot whose name doesn't resolve to an Upgrade,
so `None` can never draw the Composite Armor icon; (ii) parse order + field-merge (later file
wins), measured in R4/R6 and re-confirmed here — the Faction file parses *after* the monolith;
(iii) R8's fingerprint — in the patch-mounted configuration the Faction file that parses is
v6's, so the **last writer** of `UpgradeCameo5` is v6's `None`; (iv) R9 — patch-free, both v6
files parse cleanly and both carry `None`.

**Bottom line: v6 delivers the change in BOTH phone configurations.** Patch mounted (the R6
phone state): entry (b) wins the Faction path and is the final writer ⇒ `UpgradeCameo5 = None`
⇒ armor cameo hidden. Patch not mounted (excluded by the engine's data-mod detection, or not
installed): entry (a) sets `None` in pass 1 and entry (b) re-affirms it in pass 2 ⇒ same final
value. This also validates the M1 design rule from the main report §6: Reforged changes to
patch-redefined objects must ship at the patch's Faction paths, not only in the monoliths.
