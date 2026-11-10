"""Build !ReforgedFixes-v3.big = v2 (185 entries, byte-identical) + 3 new
directory-form definition files carrying the pure-data Reforged definitions
that v2's delivered blocks reference but that exist in neither retail ZH
data nor the Community Patch (reference audit, fixes-package-v3 mission):

  Data\\INI\\SpecialPower\\ReforgedMissing.ini
      SpecialPower Demo_SuperweaponRebelAmbush   (SpecialPowerReforged.ini)
  Data\\INI\\ObjectCreationList\\ReforgedMissing.ini
      9x ObjectCreationList {AirF,Lazr,SupW}_SUPERWEAPON_Paradrop{1,2,3}
                                                 (ObjectCreationListReforged.ini)
  Data\\INI\\Science\\ReforgedMissing.ini
      Science Demo_SCIENCE_RebelAmbush{1,2,3}    (ScienceReforged.ini)

Directory-form files load additively in BOTH configurations: the GX loader
loads Data\\INI\\<Store>.ini (winner per path) AND every Data\\INI\\<Store>\\*.ini
file; directory files from lower archives are suppressed only when the
monolith itself came from a mod archive, which is not the case here (the
monoliths come from the patch / retail). The new names collide with nothing
in either configuration, so the definitions take effect everywhere.

Blocks are extracted BYTE-FAITHFULLY from the Reforged source files.
Deterministic; verifies by reparse + SHA-256.
"""
import sys, os, hashlib
sys.path.insert(0, '/home/hatch/workspace/projects/reforged-android/testbed/tools')
from bigtool import read_big, write_big

BASE = '/home/hatch/workspace/projects/reforged-android'
V2 = os.path.join(BASE, 'm1/!ReforgedFixes-v2.big')
OUT = os.path.join(BASE, 'm1/!ReforgedFixes-v3.big')
RFG = os.path.join(BASE, 'audit/reforged/GeneralsMD/Code/Data/INI')

def extract_block_bytes(path, header):
    """Return the raw bytes of the top-level block starting at the exact
    header line, through its closing 'End' line, inclusive."""
    raw = open(path, 'rb').read()
    lines = raw.split(b'\n')
    for i, ln in enumerate(lines):
        if ln.rstrip(b'\r') == header:
            out = [ln]
            j = i + 1
            while j < len(lines) and lines[j].rstrip(b'\r') != b'End':
                out.append(lines[j])
                j += 1
            assert j < len(lines), f'no End for {header!r} in {path}'
            out.append(lines[j])
            return b'\n'.join(out) + b'\n'
    raise AssertionError(f'header {header!r} not found in {path}')

def make_file(comment_lines, blocks):
    head = b'\r\n'.join(b'; ' + c for c in comment_lines) + b'\r\n\r\n'
    body = b'\r\n'.join(b.rstrip(b'\n').replace(b'\n', b'\r\n') for b in blocks)
    return head + body + b'\r\n'

def main():
    raw, total, count, idx, entries = read_big(V2)
    pkg = [(n, raw[o:o + s]) for n, o, s in entries]
    assert len(pkg) == 185, len(pkg)

    sp_blk = extract_block_bytes(os.path.join(RFG, 'SpecialPowerReforged.ini'),
                                 b'SpecialPower Demo_SuperweaponRebelAmbush')
    sp_file = make_file([
        b'ReforgedFixes v3: definitions referenced by delivered blocks but',
        b'missing from retail ZH data and the Community Patch.',
        b'Verbatim from Reforged SpecialPowerReforged.ini (GPL-3.0).',
    ], [sp_blk])

    ocl_blocks = []
    for gen in (b'AirF', b'Lazr', b'SupW'):
        for lvl in (b'1', b'2', b'3'):
            ocl_blocks.append(extract_block_bytes(
                os.path.join(RFG, 'ObjectCreationListReforged.ini'),
                b'ObjectCreationList ' + gen + b'_SUPERWEAPON_Paradrop' + lvl))
    ocl_file = make_file([
        b'ReforgedFixes v3: definitions referenced by delivered blocks but',
        b'missing from retail ZH data and the Community Patch.',
        b'Verbatim from Reforged ObjectCreationListReforged.ini (GPL-3.0).',
    ], ocl_blocks)

    sc_blocks = [extract_block_bytes(os.path.join(RFG, 'ScienceReforged.ini'),
                                     b'Science Demo_SCIENCE_RebelAmbush' + lvl)
                 for lvl in (b'1', b'2', b'3')]
    sc_file = make_file([
        b'ReforgedFixes v3: definitions referenced by delivered blocks but',
        b'missing from retail ZH data and the Community Patch.',
        b'Verbatim from Reforged ScienceReforged.ini (GPL-3.0).',
    ], sc_blocks)

    new_entries = [
        ('Data\\INI\\SpecialPower\\ReforgedMissing.ini', sp_file),
        ('Data\\INI\\ObjectCreationList\\ReforgedMissing.ini', ocl_file),
        ('Data\\INI\\Science\\ReforgedMissing.ini', sc_file),
    ]
    all_entries = pkg + new_entries
    write_big(all_entries, OUT)

    # verify: reparse, entry count, byte-identity of inherited entries,
    # payload SHA-256 of every entry vs intent.
    raw3, total3, count3, idx3, entries3 = read_big(OUT)
    assert count3 == 188, count3
    got = {n: raw3[o:o + s] for n, o, s in entries3}
    for n, data in all_entries:
        assert got[n] == data, f'payload mismatch: {n}'
    print(f'v3 written: {OUT}')
    print(f'entries: {count3} (185 inherited byte-identical + 3 new)')
    for n, data in new_entries:
        print(f'  NEW {n}: {len(data)} bytes sha256={hashlib.sha256(data).hexdigest()[:16]}')
    blob = open(OUT, 'rb').read()
    print(f'size: {len(blob)} bytes')
    print(f'sha256: {hashlib.sha256(blob).hexdigest()}')

if __name__ == '__main__':
    main()
