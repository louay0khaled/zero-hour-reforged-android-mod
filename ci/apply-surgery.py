#!/usr/bin/env python3
"""Zero Hour Reforged — package-id surgery on a pristine MYSOREZ checkout.
CI version of the v1 local apply-surgery.py (phases 1a/1b/1c/1d/1e):
  1a applicationId + version defaults in android/app/build.gradle
  1b native hardcoded /data/user/<uid>/<old id>/files/ paths (7 files)
  1c app_name label in every locale's strings.xml
  1d UpdateManager update channel repointed at this repo (no OTA overwrite)
  1e Reforged 60-steps launcher option (v1.5): pref reforged_60_steps, a
     switch card replacing the dead Simulation Rate card on the Graphics
     tab, GeneralsZHActivity loads libmainrf60.so when it is on, and the
     card's strings in every locale
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
    ('(project.androidVersionCode as Integer) : 10402)', '(project.androidVersionCode as Integer) : 7)'),
    ("project.androidVersionName : '1.4.2')", "project.androidVersionName : '1.6')"),
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

# ---------------- Phase 1e: Reforged 60-steps launcher option (v1.5) ----------------
# The APK now carries a second Zero Hour engine, libmainrf60.so (the faithful
# Reforged 60-steps build; see ci/patches/60flip.patch). This phase gives the
# player the switch for it. Three deliberate choices:
#  * the pref is its own (reforged_60_steps, default OFF) -- never a sim_hz
#    value: GeneralsOnlineActivity's crossplay flow writes sim_hz itself and
#    must never enable this engine;
#  * the switch card takes the Graphics-tab slot of the old Simulation Rate
#    card, whose 60 Hz choice was dead in this build (no libmain60.so ships);
#    the old card's strings stay in the resources, per the codebase's own
#    precedent for retired cards;
#  * the card renders only when Zero Hour is the selected game AND the
#    library is actually in the APK, and GeneralsZHActivity falls back to
#    the standard engine whenever either condition fails.
edit('android/app/src/main/java/com/generalsx/zerohour/SetupActivity.java', [
    ("""    static void setSimHz(android.content.Context ctx, int hz) {
        ctx.getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit()
            .putInt(PREF_SIM_HZ, hz == SIM_HZ_CROSSPLAY ? SIM_HZ_CROSSPLAY : SIM_HZ_RETAIL)
            .apply();
    }""",
     """    static void setSimHz(android.content.Context ctx, int hz) {
        ctx.getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit()
            .putInt(PREF_SIM_HZ, hz == SIM_HZ_CROSSPLAY ? SIM_HZ_CROSSPLAY : SIM_HZ_RETAIL)
            .apply();
    }

    // GeneralsX @feature Zero Hour Reforged 11/11/2026 The Reforged 60-steps
    // engine (libmainrf60.so): a separate pref from sim_hz on purpose.
    // sim_hz selects the GeneralsOnline crossplay engine; this selects the
    // faithful Reforged conversion -- upstream's 60-steps simulation, not
    // the host's 60 Hz mode -- and GeneralsOnlineActivity's crossplay flow
    // writes sim_hz on its own, so the two must never share a pref. Default
    // OFF: the standard engine is the shipped experience until the player
    // opts in. See GeneralsZHActivity.getLibraries().
    static final String PREF_REFORGED_60 = "reforged_60_steps";

    static boolean getReforged60(android.content.Context ctx) {
        return ctx.getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .getBoolean(PREF_REFORGED_60, false);
    }

    static void setReforged60(android.content.Context ctx, boolean on) {
        ctx.getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit()
            .putBoolean(PREF_REFORGED_60, on)
            .apply();
    }"""),
    ('                buildSimRateSection(page);',
     '                buildReforged60Section(page);'),
    ("""    private void buildSimRateSection(LinearLayout root) {
        LinearLayout content = UiKit.card(root);
        TextView status = UiKit.sectionHeader(content, R.drawable.ic_gzh_chip,
            getString(R.string.setup_card_sim_rate), true);

        final int current = getSimHz(this);
        status.setText(getString(current == SIM_HZ_CROSSPLAY
            ? R.string.setup_sim_rate_60_short
            : R.string.setup_sim_rate_30_short));

        CharSequence[] labels = new CharSequence[] {
            getString(R.string.setup_sim_rate_30_short),
            getString(R.string.setup_sim_rate_60_short)
        };
        UiKit.segmented(content, labels, current == SIM_HZ_CROSSPLAY ? 1 : 0, index -> {
            int picked = index == 1 ? SIM_HZ_CROSSPLAY : SIM_HZ_RETAIL;
            if (picked == getSimHz(this)) {
                return;
            }
            setSimHz(this, picked);
            status.setText(getString(picked == SIM_HZ_CROSSPLAY
                ? R.string.setup_sim_rate_60_short
                : R.string.setup_sim_rate_30_short));
            Toast.makeText(this, R.string.setup_toast_sim_rate_saved, Toast.LENGTH_LONG).show();
        });

        UiKit.supporting(content, getString(current == SIM_HZ_CROSSPLAY
            ? (isGeneralsSelected(this) ? R.string.setup_sim_rate_60_desc_generals : R.string.setup_sim_rate_60_desc)
            : (isGeneralsSelected(this) ? R.string.setup_sim_rate_30_desc_generals : R.string.setup_sim_rate_30_desc)));
        UiKit.helpText(content, getString(R.string.setup_sim_rate_help));
    }""",
     """    // GeneralsX @feature Zero Hour Reforged 11/11/2026 This card takes the
    // Graphics-tab slot of the Simulation Rate card it replaces: that card's
    // 60 Hz choice was dead in this build (no libmain60.so ships, so picking
    // it changed nothing), while this build's real second engine is
    // libmainrf60.so. The card renders only when Zero Hour -- the only game
    // the 60-steps engine is built for -- is selected AND the library is
    // actually present in the APK.
    private void buildReforged60Section(LinearLayout root) {
        if (isGeneralsSelected(this)) {
            return;
        }
        if (!new java.io.File(getApplicationInfo().nativeLibraryDir, "libmainrf60.so").isFile()) {
            return;
        }
        LinearLayout content = UiKit.card(root);
        UiKit.sectionHeader(content, R.drawable.ic_gzh_chip,
            getString(R.string.setup_card_reforged60), true);
        com.google.android.material.materialswitch.MaterialSwitch sw = UiKit.switchRow(content,
            getString(R.string.setup_reforged60_title), getString(R.string.setup_reforged60_desc));
        sw.setChecked(getReforged60(this));
        sw.setOnCheckedChangeListener((button, checked) -> setReforged60(this, checked));
        UiKit.helpText(content, getString(R.string.setup_reforged60_help));
    }"""),
])

edit('android/app/src/main/java/com/generalsx/zerohour/GeneralsZHActivity.java', [
    ("""        final String[] engines = SetupActivity.engineLibraries(this);
        String engine = engines[0];
        if (SetupActivity.getSimHz(this) == SetupActivity.SIM_HZ_CROSSPLAY
                && new java.io.File(getApplicationInfo().nativeLibraryDir, "lib" + engines[1] + ".so").isFile()) {
            engine = engines[1];
        }""",
     """        final String[] engines = SetupActivity.engineLibraries(this);
        String engine = engines[0];
        // GeneralsX @feature Zero Hour Reforged 11/11/2026 The Reforged
        // 60-steps engine takes the place of the GeneralsOnline crossplay
        // branch in this build: the APK carries no libmain60.so, so that
        // branch could never fire. Zero Hour only (the base game has no
        // 60-steps library), the player's own switch only (never sim_hz --
        // GeneralsOnlineActivity writes that pref itself), and only when
        // the library is actually in the APK; anything else falls back to
        // the standard engine rather than failing to start.
        if (!SetupActivity.isGeneralsSelected(this)
                && SetupActivity.getReforged60(this)
                && new java.io.File(getApplicationInfo().nativeLibraryDir, "libmainrf60.so").isFile()) {
            engine = "mainrf60";
        }"""),
])

# Card strings in every locale, inserted right after the sim-rate toast line
# (the anchor string name exists in all locales; its text is translated).
# AAPT2 law: an apostrophe inside a string resource must reach the XML
# escaped as \' or mergeReleaseResources rejects the string ("unescaped
# apostrophe in string") -- hence the \\' in the Python literals below,
# which puts a literal backslash before the apostrophe in the XML.
_RF60_STRINGS_EN = [
    ('setup_card_reforged60', 'Reforged Engine'),
    ('setup_reforged60_title', 'Reforged engine \u2014 60 steps per second (experimental)'),
    ('setup_reforged60_desc', "Reforged\\'s own doubled simulation rate: smoother motion and faster response, at the cost of heavier work for the processor."),
    ('setup_reforged60_help', "The engine is chosen when the game starts, so the change applies the next time you launch it. Save games and replays belong to the rate that made them: each engine refuses the other\\'s, cleanly. This mode plays no network games. If large battles slow down, switch it off."),
]
_RF60_STRINGS_AR = [
    ('setup_card_reforged60', 'محرك ريفورجيد'),
    ('setup_reforged60_title', 'محرك ريفورجيد — 60 خطوة بالثانية (تجريبي)'),
    ('setup_reforged60_desc', 'محاكاة ريفورجيد الأصلية بمعدل مضاعف: حركة أنعم واستجابة أسرع، مقابل شغل أثقل على المعالج.'),
    ('setup_reforged60_help', 'يُختار المحرك عند بدء اللعبة، فيسري التغيير عند تشغيلها في المرة القادمة. ملفات الحفظ والإعادات تخص المعدل الذي صنعها: كل محرك يرفض ملفات الآخر بشكل نظيف. هذا الوضع لا يلعب مباريات عبر الشبكة. إذا تراجعت السلاسة في المعارك الكبيرة، أوقف هذا الخيار.'),
]
for d in os.listdir(resdir):
    p = os.path.join(resdir, d, 'strings.xml')
    if not (d.startswith('values') and os.path.isfile(p)):
        continue
    s = open(p, encoding='utf-8').read()
    if 'name="setup_card_reforged60"' in s:
        continue
    entries = _RF60_STRINGS_AR if d == 'values-ar' else _RF60_STRINGS_EN
    block = ''.join(f'\n    <string name="{n}">{t}</string>' for n, t in entries)
    lines = s.split('\n')
    idx = next((i for i, ln in enumerate(lines) if 'name="setup_toast_sim_rate_saved"' in ln), None)
    if idx is None:
        idx = next(i for i, ln in enumerate(lines) if '</resources>' in ln)
        lines.insert(idx, block.lstrip('\n'))
    else:
        lines.insert(idx + 1, block.lstrip('\n'))
    open(p, 'w', encoding='utf-8').write('\n'.join(lines))
    print('rf60 strings', os.path.join(d, 'strings.xml'))

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

print('SURGERY (phases 1a-1e) DONE')
