"""Build !ReforgedFixes-v1.big from FixesReforged.ini.

Delivery design (all proven in the testbed):
- Object blocks: appended verbatim as overlay blocks at the END of the Community
  Patch split file that defines the object (entry path = the patch's path; the
  mod wins that path in patch config and parses in pass 2 in retail config).
- ObjectReskin: appended (minus the ReplaceTexture line) to the split file of
  its source object.
- Weapon blocks: edited IN PLACE into the patch's Weapon.ini (weapon
  redefinition in a second block is a hard error in this engine, so the fields
  are written into the existing weapon definition).
- Excluded: idx 191/192/193 (reference OCLs that exist only in
  ObjectCreationListReforged.ini, not shipped).
"""
import sys, re, json, hashlib
sys.path.insert(0, '/home/hatch/workspace/projects/reforged-android/fixes/work')
sys.path.insert(0, '/home/hatch/workspace/projects/reforged-android/testbed/tools')
import parse_blocks
from bigtool import write_big, read_big, verify

BS = chr(92)
PATCH_BIG = '/home/hatch/workspace/projects/zh-kotlin-engine/data/500_900_CommunityPatch_CoreINI.big'
SRC = '/home/hatch/workspace/projects/reforged-android/audit/reforged/GeneralsMD/Code/Data/INI/FixesReforged.ini'
OUT = '/home/hatch/workspace/projects/reforged-android/m1/!ReforgedFixes-v1.big'
EXCLUDE_BLOCKS = {191, 192, 193}
DROP_LINES = {194: 'ReplaceTexture'}   # block index -> field name whose line is dropped

raw, t, c, i, entries = read_big(PATCH_BIG)
patch = {n: raw[o:o+s] for n, o, s in entries}
plan = json.load(open('/home/hatch/workspace/projects/reforged-android/fixes/work/plan.json'))
src_text = open(SRC, 'rb').read().decode('ascii')
segs, blocks = parse_blocks.segment_file(src_text)

def block_text(b, drop_field=None):
    out = []
    for ln in b['lines']:
        if drop_field and re.match(r'^\s+' + drop_field + r'\s*=', ln):
            continue
        out.append(ln)
    return '\r\n'.join(l.rstrip('\r') for l in out) + '\r\n'

# group overlays per entry path
overlays = {}   # path -> list of (block_index, text)
manifest = []
for e in plan:
    idx = e['index']; b = blocks[idx]
    if e['route'] == 'weapon-inplace':
        continue
    if idx in EXCLUDE_BLOCKS:
        manifest.append(dict(index=idx, header=b['header'], disposition='excluded',
                             reason='references Reforged-only OCL(s)'))
        continue
    if e['route'] == 'split-append':
        path = e['patch_paths'][0]
    elif e['route'] == 'reskin-append':
        path = e['patch_paths'][0]
    drop = DROP_LINES.get(idx)
    overlays.setdefault(path, []).append((idx, block_text(b, drop)))
    manifest.append(dict(index=idx, header=b['header'],
                         disposition='split-append' if e['route'] == 'split-append' else 'reskin-append',
                         path=path, dropped_line=drop))

# --- Weapon.ini in-place edits ---
weapon_blocks = [e for e in plan if e['route'] == 'weapon-inplace']
wini = patch['Data\\INI\\Weapon.ini'].decode('ascii')
wlines = wini.split('\n')
# locate weapon block spans (col-0 'Weapon X' .. col-0 'End')
def find_weapon(lines, name):
    for k, ln in enumerate(lines):
        if ln.rstrip('\r').strip() == 'Weapon ' + name:
            j = k + 1
            while j < len(lines) and lines[j].rstrip('\r') != 'End':
                j += 1
            return k, j
    return None
weapon_report = []
for e in weapon_blocks:
    b = blocks[e['index']]
    span = find_weapon(wlines, e['name'])
    assert span, 'weapon not found in patch Weapon.ini: ' + e['name']
    k, j = span
    changes = []
    for ln in b['lines'][1:-1]:
        s = ln.rstrip('\r').strip()
        if not s or s.startswith(';'):
            continue
        m = re.match(r'^(\w+)\s*=\s*(.+)$', s)
        assert m, 'unparsed weapon field line: ' + s
        field, value = m.group(1), m.group(2).strip()
        hit = None
        for q in range(k + 1, j):
            fm = re.match(r'^(\s*)' + field + r'\s*=', wlines[q].rstrip('\r'))
            if fm:
                hit = q; break
        if hit is not None:
            old = wlines[hit].rstrip('\r')
            indent = re.match(r'^(\s*)', old).group(1)
            wlines[hit] = f'{indent}{field} = {value}\r'
            changes.append(f'{field}: replaced ({old.strip()[:60]})')
        else:
            wlines.insert(k + 1, f'{field} = {value}\r')
            j += 1
            changes.append(f'{field}: inserted')
    weapon_report.append(dict(index=e['index'], header=b['header'], changes=changes))
    manifest.append(dict(index=e['index'], header=b['header'], disposition='weapon-inplace',
                         path='Data\\INI\\Weapon.ini', changes=changes))
weapon_ini_new = '\n'.join(wlines)

# --- assemble entries ---
entries_out = []
entry_manifest = []
for path, ovs in sorted(overlays.items()):
    base = patch[path].decode('ascii')
    if not base.endswith('\n'):
        base += '\r\n'
    txt = base + '\r\n; ==== Reforged fixes overlay (appended by ReforgedFixes-v1) ====\r\n'
    for idx, otext in ovs:
        txt += '\r\n' + otext
    entries_out.append((path, txt.encode('ascii')))
    entry_manifest.append(dict(path=path, base_bytes=len(patch[path]),
                               final_bytes=len(txt.encode('ascii')),
                               overlay_blocks=[o[0] for o in ovs]))
entries_out.append(('Data\\INI\\Weapon.ini', weapon_ini_new.encode('ascii')))
entries_out.sort(key=lambda x: x[0])

write_big(entries_out, OUT)
ents = verify(OUT)
# verify payload hashes against intended
ok = True
for (name, off, size), (want_name, want_data) in zip(ents, entries_out):
    h = hashlib.sha256(read_big(OUT)[0][off:off+size]).hexdigest()
    hw = hashlib.sha256(want_data).hexdigest()
    if name != want_name or h != hw:
        ok = False; print('MISMATCH', name)
print('payload verification:', 'ALL MATCH' if ok else 'FAILED')
import os
print('package size:', os.path.getsize(OUT), 'sha256:', hashlib.sha256(open(OUT, 'rb').read()).hexdigest())
print('entries:', len(entries_out))
json.dump(dict(manifest=sorted(manifest, key=lambda m: m['index']),
               entries=entry_manifest, weapon_report=weapon_report),
          open('/home/hatch/workspace/projects/reforged-android/fixes/work/package-manifest.json', 'w'), indent=1)
print('manifest written')
