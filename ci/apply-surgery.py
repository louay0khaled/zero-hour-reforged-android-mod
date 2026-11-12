#!/usr/bin/env python3
"""Zero Hour Reforged — package-id surgery on a pristine MYSOREZ checkout.
CI version of the v1 local apply-surgery.py (phases 1a/1b/1c/1d/1e/1f/1g):
  1a applicationId + version defaults in android/app/build.gradle
  1b native hardcoded /data/user/<uid>/<old id>/files/ paths (7 files)
  1c app_name label in every locale's strings.xml
  1d UpdateManager update channel repointed at this repo (no OTA overwrite)
  1e Reforged 60-steps launcher option (v1.5): pref reforged_60_steps, a
     switch card replacing the dead Simulation Rate card on the Graphics
     tab, GeneralsZHActivity loads libmainrf60.so when it is on, and the
     card's strings in every locale
  1f Online Mode launcher option (v1.7): pref reforged_online_mode, a
     switch card under the Reforged Engine card on the Graphics tab; while
     it is on, GeneralsZHActivity never loads libmainrf60.so (the standard
     engine runs, whatever the 60-steps pref says) and ModManager (phase 2)
     keeps the bundled mod switched off -- together the stock identity
     GeneralsOnline lobbies check for; the card's strings in every locale
  1g Online Mode engine (v1.8): while Online Mode is on, GeneralsZHActivity
     loads the host's own 60 Hz engine (libmain60.so, built in CI from a
     pristine second checkout of the pinned tree, SAGE_HIGH_FPS_SIM=ON, no
     overlay) instead of the standard engine -- the 60 Hz GeneralsOnline
     population runs exactly that engine, so the session joins it and
     holds lockstep with it; GeneralsOnlineSession.clientId mirrors the
     new branch; the upstream UpdateManager engine-override load path is
     removed (the APK's engines are the only engines); the Online Mode
     card text (phase 1f strings) says what the mode now does
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
    ('(project.androidVersionCode as Integer) : 10402)', '(project.androidVersionCode as Integer) : 9)'),
    ("project.androidVersionName : '1.4.2')", "project.androidVersionName : '1.8')"),
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

# ---------------- Phase 1f: Online Mode launcher option (v1.7) ----------------
# GeneralsOnline lobbies gate a join on two CRCs (see the wave-8 record):
# exe_crc (engine version + the stock .scb scripts; engine code is never
# hashed) and ini_crc (every INI line read at init). This build reads as a
# different game to the lobby whenever the bundled Reforged mod is mounted
# (its INI lines enter ini_crc and the host refuses the Community Patch
# whenever any data mod is on) or the 60-steps engine runs (its version
# stamp enters exe_crc). Online mode packages the stock identity in one
# switch: pref reforged_online_mode (default OFF) -- while it is on,
# ModManager (phase 2) keeps the bundled mod switched off through the same
# order prefs the Mods screen uses, and GeneralsZHActivity never loads
# libmainrf60.so. The player's own reforged_60_steps pref is never
# overwritten: the veto lives in the launch decision, not in the pref.
edit('android/app/src/main/java/com/generalsx/zerohour/SetupActivity.java', [
    ("""    static void setReforged60(android.content.Context ctx, boolean on) {
        ctx.getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit()
            .putBoolean(PREF_REFORGED_60, on)
            .apply();
    }""",
     """    static void setReforged60(android.content.Context ctx, boolean on) {
        ctx.getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit()
            .putBoolean(PREF_REFORGED_60, on)
            .apply();
    }

    // GeneralsX @feature Zero Hour Reforged 12/11/2026 Online mode: while
    // it is on, GeneralsOnline lobbies must see this build exactly as a
    // stock one -- the bundled Reforged mod switched off (ModManager,
    // phase 2) and the host's own 60 Hz engine loaded (GeneralsZHActivity,
    // since v1.8; the standard engine in v1.7). Its
    // own pref, default OFF; the 60-steps pref is never rewritten by it.
    static final String PREF_REFORGED_ONLINE = "reforged_online_mode";

    static boolean getOnlineMode(android.content.Context ctx) {
        return ctx.getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .getBoolean(PREF_REFORGED_ONLINE, false);
    }

    static void setOnlineMode(android.content.Context ctx, boolean on) {
        ctx.getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit()
            .putBoolean(PREF_REFORGED_ONLINE, on)
            .apply();
    }"""),
    ('                buildReforged60Section(page);',
     """                buildReforged60Section(page);
                buildOnlineModeSection(page);"""),
    ("""        sw.setOnCheckedChangeListener((button, checked) -> setReforged60(this, checked));
        UiKit.helpText(content, getString(R.string.setup_reforged60_help));
    }""",
     """        sw.setOnCheckedChangeListener((button, checked) -> setReforged60(this, checked));
        UiKit.helpText(content, getString(R.string.setup_reforged60_help));
    }

    // GeneralsX @feature Zero Hour Reforged 12/11/2026 The Online Mode
    // card, directly under the Reforged Engine card on the Graphics tab.
    // Zero Hour only, like the card above it -- but deliberately NO
    // library-presence gate: the mod half of the mode matters even on a
    // build without libmainrf60.so. Toggling writes the pref and hands the
    // mod state to ModManager.applyOnlineMode, which snapshots the
    // bundled mod's switch state on entry and restores it on exit.
    private void buildOnlineModeSection(LinearLayout root) {
        if (isGeneralsSelected(this)) {
            return;
        }
        LinearLayout content = UiKit.card(root);
        UiKit.sectionHeader(content, R.drawable.ic_gzh_chip,
            getString(R.string.setup_card_online_mode), true);
        com.google.android.material.materialswitch.MaterialSwitch sw = UiKit.switchRow(content,
            getString(R.string.setup_online_mode_title), getString(R.string.setup_online_mode_desc));
        sw.setChecked(getOnlineMode(this));
        sw.setOnCheckedChangeListener((button, checked) -> {
            setOnlineMode(this, checked);
            ModManager.applyOnlineMode(this, checked);
        });
        UiKit.helpText(content, getString(R.string.setup_online_mode_help));
    }"""),
])

edit('android/app/src/main/java/com/generalsx/zerohour/GeneralsZHActivity.java', [
    ("""        // the standard engine rather than failing to start.
        if (!SetupActivity.isGeneralsSelected(this)
                && SetupActivity.getReforged60(this)""",
     """        // the standard engine rather than failing to start. Online mode
        // (v1.7) vetoes this branch without touching the player's own
        // 60-steps pref: while it is on, the standard engine always runs.
        if (!SetupActivity.isGeneralsSelected(this)
                && SetupActivity.getReforged60(this)
                && !SetupActivity.getOnlineMode(this)"""),
])

# Online card strings in every locale, inserted right after the 60-steps
# help line phase 1e put in (the anchor string name exists in all locales).
_ONLINE_STRINGS_EN = [
    ('setup_card_online_mode', 'Online Mode'),
    ('setup_online_mode_title', 'Online mode'),
    ('setup_online_mode_desc', 'Turns the Reforged mod off and plays online games on the original 60 Hz engine, so GeneralsOnline lobbies accept this build and 60 Hz games stay in sync.'),
    ('setup_online_mode_help', 'Online lobbies only accept the standard data. While online mode is on, the Reforged mod stays off and online games run on the original 60 Hz engine \u2014 the same engine the original app ships \u2014 even if the 60-steps switch is on. Turn it off and the mod and your engine choice come back exactly as they were.'),
]
_ONLINE_STRINGS_AR = [
    ('setup_card_online_mode', 'وضع الأونلاين'),
    ('setup_online_mode_title', 'وضع الأونلاين'),
    ('setup_online_mode_desc', 'يوقف مود ريفورجيد ويشغّل مباريات الأونلاين بمحرك الـ60 هرتز الأصلي، فتقبل ردهات GeneralsOnline هذه النسخة وتبقى مباريات الـ60 هرتز متزامنة.'),
    ('setup_online_mode_help', 'ردهات الأونلاين لا تقبل إلا البيانات القياسية. ما دام وضع الأونلاين يعمل، يبقى مود ريفورجيد موقوفًا وتعمل مباريات الأونلاين بمحرك الـ60 هرتز الأصلي — وهو محرك التطبيق الأصلي نفسه — حتى لو كان مفتاح الـ60 خطوة يعمل. أوقف الوضع فيعود المود واختيار المحرك تمامًا كما كانا.'),
]
for d in os.listdir(resdir):
    p = os.path.join(resdir, d, 'strings.xml')
    if not (d.startswith('values') and os.path.isfile(p)):
        continue
    s = open(p, encoding='utf-8').read()
    if 'name="setup_card_online_mode"' in s:
        continue
    entries = _ONLINE_STRINGS_AR if d == 'values-ar' else _ONLINE_STRINGS_EN
    block = ''.join(f'\n    <string name="{n}">{t}</string>' for n, t in entries)
    lines = s.split('\n')
    idx = next((i for i, ln in enumerate(lines) if 'name="setup_reforged60_help"' in ln), None)
    if idx is None:
        idx = next(i for i, ln in enumerate(lines) if '</resources>' in ln)
        lines.insert(idx, block.lstrip('\n'))
    else:
        lines.insert(idx + 1, block.lstrip('\n'))
    open(p, 'w', encoding='utf-8').write('\n'.join(lines))
    print('online strings', os.path.join(d, 'strings.xml'))

# ---------------- Phase 1g: Online Mode engine = host's own 60 Hz (v1.8) ----------------
# The 60 Hz GeneralsOnline population runs the host's own libmain60.so: its
# version is unstamped (its exe_crc equals the stock value, which is how
# those players sit in the normal lobby) and its simulation is the host's
# HIGH_FPS conversion. The Reforged 60-steps engine can never join them --
# its version stamp moves exe_crc and its converted simulation is a
# different stream (wave-8 record, section 7.2). From v1.8 the APK also
# ships the genuine article: CI builds a pristine second checkout of the
# pinned tree with SAGE_HIGH_FPS_SIM=ON (no overlay, exactly the host's
# own build-dual-hz.sh pass 1) and packages its z_generals output as
# libmain60.so. While Online Mode is on, that is the engine that runs.
# Offline, nothing changes: the 60-steps pref still rules (libmainrf60.so),
# and libmain60.so is never loaded outside Online Mode -- in particular
# sim_hz cannot select it, because phase 1e replaced the sim_hz branch in
# getLibraries() and GeneralsOnlineActivity's crossplay flow (which writes
# sim_hz) is disabled by the signed settings in this build.
edit('android/app/src/main/java/com/generalsx/zerohour/GeneralsZHActivity.java', [
    ("""        // the standard engine rather than failing to start. Online mode
        // (v1.7) vetoes this branch without touching the player's own
        // 60-steps pref: while it is on, the standard engine always runs.
        if (!SetupActivity.isGeneralsSelected(this)
                && SetupActivity.getReforged60(this)
                && !SetupActivity.getOnlineMode(this)""",
     """        // the standard engine rather than failing to start. Online mode
        // vetoes this branch without touching the player's own 60-steps
        // pref: while it is on, the branch below runs instead.
        // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.8) Online
        // mode's engine: the host's own 60 Hz build (engines[1] is
        // "main60"), shipped since v1.8 from a pristine second checkout
        // of the pinned upstream tree (SAGE_HIGH_FPS_SIM=ON, no overlay
        // -- the host's own build-dual-hz.sh pass 1). A GeneralsOnline
        // session under it presents exactly a stock dual-Hz install's
        // identity -- unstamped version (exe_crc), the 60 Hz client id
        // (GeneralsOnlineSession.clientId mirrors this branch) -- so it
        // joins the 60 Hz population and holds lockstep with it, which
        // the Reforged 60-steps engine never can. Zero Hour only, like
        // the branch below; if the library is somehow missing, fall
        // through to the standard engine (the v1.7 behaviour) rather
        // than failing to start.
        if (!SetupActivity.isGeneralsSelected(this)
                && SetupActivity.getOnlineMode(this)
                && new java.io.File(getApplicationInfo().nativeLibraryDir, "lib" + engines[1] + ".so").isFile()) {
            engine = engines[1];
        }
        if (!SetupActivity.isGeneralsSelected(this)
                && SetupActivity.getReforged60(this)
                && !SetupActivity.getOnlineMode(this)"""),
    # The UpdateManager engine override is removed at its only point of
    # use. Proof it could never fire in this build is in the wave-8
    # record (section 8.4): the phase-1d channel serves no manifest, and
    # any manifest would have to be signed with the upstream ECDSA key,
    # which this project does not hold. The removal makes "the APK's
    # engines are the only engines" structural instead of circumstantial
    # -- from v1.8 that also covers libmain60.so, whose whole value online
    # is being exactly the file this APK installed. UpdateManager itself
    # is untouched; its checks simply find no loadable engine here.
    ("""    // GeneralsX @feature Android port 27/09/2026 An engine delivered by UpdateManager (signed
    // manifest, SHA-256 checked, built against this APK's own libraries) runs instead of the
    // APK's. Only the engine library is replaced; SDL3 and everything the engine links against
    // or dlopen()s by name still come from the APK, which is why the manifest has to name the
    // exact libraries it was built with. Null means the APK's own engine.
    private String mEngineOverridePath;""",
     """    // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.8) The
    // upstream UpdateManager engine override that stood here is REMOVED,
    // not merely unused: no downloaded engine is ever loaded in this
    // build, for "main", "main60" or "mainrf60" -- the libraries in the
    // APK are the only engines. See loadLibraries() below and the wave-8
    // record, section 8.4."""),
    ("""    @Override
    public void loadLibraries() {
        for (String lib : getLibraries()) {
            // Signed engine updates are Zero Hour's (UpdateManager.ENGINE_LIBS).
            if ("main".equals(lib) || "main60".equals(lib)) {
                int seq = UpdateManager.activeEngineSeq(this);
                if (seq > 0 && UpdateManager.noteEngineBoot(this, seq)) {
                    String path = UpdateManager.activeEngineLibrary(this, "lib" + lib + ".so");
                    if (path != null) {
                        try {
                            System.load(path);
                            mEngineOverridePath = path;
                            Log.i(TAG, "Loaded updated engine " + seq + ": " + path);
                            continue;
                        } catch (UnsatisfiedLinkError e) {
                            Log.e(TAG, "updated engine " + seq + " failed to load; using the APK's", e);
                        }
                    }
                }
            }
            System.loadLibrary(lib);
        }
    }

    @Override
    protected String getMainSharedObject() {
        return mEngineOverridePath != null ? mEngineOverridePath : super.getMainSharedObject();
    }""",
     """    @Override
    public void loadLibraries() {
        // Zero Hour Reforged (v1.8): no UpdateManager engine override --
        // the APK's own libraries always load, exactly as every shipped
        // build of this project has in fact run (the repointed channel
        // has never delivered an engine to it).
        for (String lib : getLibraries()) {
            System.loadLibrary(lib);
        }
    }"""),
])

# The launcher's GeneralsOnline client id must announce the engine that
# will actually run (the file's own header comment demands the mirror).
# Pristine keys it on sim_hz, but this build's getLibraries() has not
# honoured sim_hz since v1.5 -- with libmain60.so now in the APK, the
# pristine condition could announce 60 Hz for a session the standard or
# Reforged engine would run. Key it on the online-mode branch instead:
# 60 Hz is announced exactly when getLibraries() loads libmain60.so.
edit('android/app/src/main/java/com/generalsx/zerohour/GeneralsOnlineSession.java', [
    ("""    static String clientId( Context ctx ) {
        if (ctx != null
                && SetupActivity.getSimHz(ctx) == SetupActivity.SIM_HZ_CROSSPLAY
                && new java.io.File(ctx.getApplicationInfo().nativeLibraryDir,
                        "libmain60.so").isFile()) {
            return "gen_online_60hz";
        }
        return CLIENT_ID;
    }""",
     """    static String clientId( Context ctx ) {
        // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.8) The
        // mirror rule above now resolves through Online Mode: this
        // build's GeneralsZHActivity.getLibraries() has not honoured
        // sim_hz since v1.5 (the Reforged 60-steps branch replaced the
        // crossplay branch, and the crossplay flow that writes sim_hz is
        // disabled by the signed settings), so keying the id on sim_hz
        // could announce an engine that will not run. The 60 Hz engine
        // runs when Online Mode is on and libmain60.so is in the APK --
        // the exact condition under which getLibraries() loads it --
        // and in no other case.
        if (ctx != null
                && SetupActivity.getOnlineMode(ctx)
                && new java.io.File(ctx.getApplicationInfo().nativeLibraryDir,
                        "libmain60.so").isFile()) {
            return "gen_online_60hz";
        }
        return CLIENT_ID;
    }"""),
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

print('SURGERY (phases 1a-1g) DONE')
