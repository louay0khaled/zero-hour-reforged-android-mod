#!/usr/bin/env python3
"""Zero Hour Reforged — package-id surgery on a pristine MYSOREZ checkout.
CI version of the v1 local apply-surgery.py (phases 1a/1b/1c/1d only):
  1a applicationId + version defaults in android/app/build.gradle
  1b native hardcoded /data/user/<uid>/<old id>/files/ paths (7 files)
  1c app_name label in every locale's strings.xml
  1d UpdateManager update channel repointed at this repo (no OTA overwrite)
The phase-3 engine change (locomotor carry-over, ThingTemplate.cpp) is NOT
here: it ships as ci/patches/engine-carryover.patch and is applied with
`git apply` before this script runs.

Layout: REFORGED_SRC (env) points at the MYSOREZ checkout; default is the
parent of this repo's checkout (the CI workflow checks the overlay repo out
into <workspace>/reforged-overlay and MYSOREZ at <workspace>)."""
import os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
OVERLAY = os.path.dirname(_HERE)
SRC = os.environ.get('REFORGED_SRC') or os.path.dirname(OVERLAY)
NEW_ID = 'com.louay.zerohour.reforged'
OLD_ID = 'com.generalsx.zerohour'

def edit(path, subs, must=True):
    p = os.path.join(SRC, path)
    s = open(p, encoding='utf-8').read()
    for old, new in subs:
        if old not in s:
            if must: sys.exit(f'PATTERN NOT FOUND in {path}: {old[:70]!r}')
            continue
        s = s.replace(old, new)
    open(p, 'w', encoding='utf-8').write(s)
    print('edited', path)

print('surgery target tree:', SRC)

# ---------------- Phase 1a: applicationId + version ----------------
edit('android/app/build.gradle', [
    ("applicationId 'com.generalsx.zerohour'", f"applicationId '{NEW_ID}'"),
    ('(project.androidVersionCode as Integer) : 10402)', '(project.androidVersionCode as Integer) : 3)'),
    ("project.androidVersionName : '1.4.2')", "project.androidVersionName : '1.2')"),
])

# ---------------- Phase 1b: native hardcoded data paths ----------------
for f in ['Core/GameEngine/Include/Common/GXControlScheme.h',
          'Core/GameEngine/Include/Common/GXLogging.h',
          'Core/GameEngine/Include/Common/GXManagedMods.h',
          'Core/GameEngine/Include/Common/GXMouseMode.h',
          'Core/GameEngine/Include/Common/GXRemoteConfig.h',
          'Core/GameEngine/Include/Common/GXSubtitles.h',
          'Core/Main/AndroidCrashHandler.cpp']:
    edit(f, [('/data/user/%d/com.generalsx.zerohour/files/', f'/data/user/%d/{NEW_ID}/files/')])

# ---------------- Phase 1c: app label in every locale ----------------
resdir = os.path.join(SRC, 'android/app/src/main/res')
for d in os.listdir(resdir):
    p = os.path.join(resdir, d, 'strings.xml')
    if d.startswith('values') and os.path.isfile(p):
        s = open(p, encoding='utf-8').read()
        s2 = s.replace('<string name="app_name">Generals</string>',
                       '<string name="app_name">Zero Hour Reforged</string>')
        if s2 != s:
            open(p, 'w', encoding='utf-8').write(s2)
            print('label  ', os.path.join(d, 'strings.xml'))

# ---------------- Phase 1d: update channel repoint ----------------
# The upstream OTA channel would download unpatched upstream engines over
# this build (and their native paths name the old package id). The Reforged
# build has no OTA channel: point the root at the project repo, which serves
# no update branches, so every check resolves to "no update".
edit('android/app/src/main/java/com/generalsx/zerohour/UpdateManager.java', [
    ('"https://raw.githubusercontent.com/MYSOREZ/GeneralsZH-Android-Port/"',
     '"https://raw.githubusercontent.com/louay0khaled/zero-hour-reforged-android-mod/main/"'),
])

# ---------------- post-check: no old-id native paths remain ----------------
leftover = []
for f in ['Core/GameEngine/Include/Common/GXControlScheme.h',
          'Core/GameEngine/Include/Common/GXLogging.h',
          'Core/GameEngine/Include/Common/GXManagedMods.h',
          'Core/GameEngine/Include/Common/GXMouseMode.h',
          'Core/GameEngine/Include/Common/GXRemoteConfig.h',
          'Core/GameEngine/Include/Common/GXSubtitles.h',
          'Core/Main/AndroidCrashHandler.cpp']:
    if f'/data/user/%d/{OLD_ID}/files/' in open(os.path.join(SRC, f), encoding='utf-8').read():
        leftover.append(f)
if leftover:
    sys.exit(f'OLD-ID PATHS REMAIN in: {leftover}')

print('SURGERY (phases 1a-1d) DONE')
