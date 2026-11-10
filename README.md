# Zero Hour Reforged — on Android

**Reforged's data layer, running on your phone** — as a mod for the
[MYSOREZ GeneralsZH Android port](https://github.com/MYSOREZ/GeneralsZH-Android-Port).

> مشروع «ريفورجد على أندرويد»: طبقة بيانات Reforged (إصلاحات EA 1.04) شغّالة على الهاتف
> كمود فوق بورت MYSOREZ — مبنية ومتحقق منها بمختبر محرك محلي، ومثبتة على جهاز حقيقي.

## Status

- **M1 complete (2026-11-10):** the full *FixesReforged* layer runs on a real phone
  (Redmi 14C) as a managed mod — phone-verified end to end.
- Current package: **`packages/!ReforgedFixes-v3.big`** (188 entries, 2,620,655 bytes,
  SHA-256 `4dffe0243977b3a20e190631d07fcfb1869172c3af3a4361422b4c54ce8b891b`).
- 217 of 221 *FixesReforged* changes delivered faithfully; 3 small Particle Cannon
  Uplink blocks remain undelivered (their death OCLs ship with a later layer) and one
  texture-reference line was dropped (the texture itself is a Reforged asset).
  Full accounting in `docs/fixes-package-v3.md`.

## Install

1. You need the MYSOREZ Android port installed with your own legally owned
   *Command & Conquer Generals Zero Hour* data.
2. Copy `!ReforgedFixes-v3.big` into the Zero Hour game folder's `mods/` directory.
3. In the port's launcher, open **Mods** and switch the package **ON**.
4. Launch the game. That's it — no other files, no settings.

To remove it, switch it off (or delete it) in the same Mods screen.

## What the package changes

*FixesReforged* is not a balance mod: it corrects mistakes in EA's 1.04 data —
a general's unit that missed a fix its base version got, an armor upgrade whose
icon shows but never applies, a module pointing at the wrong faction's sound.
Examples: the Air Force Microwave Tank no longer advertises Composite Armor it
cannot buy; the King Raptor's armor upgrade actually applies; Laser/Superweapon
supply Chinooks unload at the correct speed; the EMP Patriot no longer disables
its owner's own vehicles and aircraft; the Nuke Cannon can no longer fire neutron
shells before they are bought. The upstream file documents every block.

## How it is built — and why it took three versions

The port's mod system mounts archives *above* the game's data, and objects merge
field-by-field in parse order. Two properties of this host shaped the delivery:

- The **GeneralsOnline Community Patch** (mounted on most installs) redefines every
  object in split files under `Data\INI\Object\Faction\...`, which parse *after* the
  classic monolith files. Edits therefore ship **inside copies of the patch's split
  files** (split-append), where they are the last writer in both patch-mounted and
  patch-free installs.
- The host engine has **no locomotor carry-over** for `ReplaceModule` (a feature
  Reforged added to its own engine), and several Reforged fixes name templates that
  exist only in Reforged's data files. v1 and v2 crashed on a real phone for exactly
  those two reasons; both failure classes are documented in `docs/`.

Every package is verified in a **local testbed**: the port's own engine, built for
Linux from the MYSOREZ source, must pass four gates in both configurations
(patch-mounted and patch-free) before anything ships:

1. **Parse gate** — full INI load, zero `[INI] ERROR`.
2. **Locomotor gate** — a template audit proving no object loses its movement data.
3. **Reference gate** — every name referenced by the package resolves in the
   target data set (missing pure-data definitions ship inside the package).
4. **Instantiation gate** — every one of the ~2,100 object templates is actually
   constructed in the engine, per configuration.

## Repository layout

- `packages/` — the shippable mod package(s).
- `tools/` — the BIG archive writer/reader and the package builder scripts.
- `docs/` — the testbed report and the per-version verification reports.

## Credits & lineage

- Game and original data © Electronic Arts; the Generals / Zero Hour source was
  released by EA under the GNU GPL v3 (see `LICENSE.md`).
- [Reforged](https://github.com/olcayseygan/cncgeneralszh-reforged) by Olcay Seygan —
  the fixes, and the engine features this data was written for.
- [GeneralsZH Android Port](https://github.com/MYSOREZ/GeneralsZH-Android-Port) —
  the host this mod runs on.
- The GeneralsOnline Community Patch — the split-file data layout this package
  is built to cooperate with.

This is an independent, non-commercial fan project. It contains **no game assets**
(no models, textures or audio) — only INI configuration data derived from the
GPL-released sources above. You must own the game to use it.

## License

GNU General Public License v3 — see `LICENSE.md`.
