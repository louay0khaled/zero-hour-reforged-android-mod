#!/usr/bin/env python3
"""Zero Hour Reforged — package-id surgery on a pristine MYSOREZ checkout.
CI version of the v1 local apply-surgery.py. Since v1.9 the build is
SEPARATED (owner order 2026-11-12): the base app is the host's own build
(their dual-Hz engines, their launcher, their settings), and everything
of ours lives on our own launcher page + in our own engine library. The
phases are:
  1a applicationId + version defaults in android/app/build.gradle
  1b native hardcoded /data/user/<uid>/<old id>/files/ paths (7 files) --
     app identity for EVERY engine binary this APK ships, so it runs in
     both modes below (base tree and Reforged-engine tree alike)
  1c app_name label in every locale's strings.xml
  1d UpdateManager update channel repointed at this repo (no OTA overwrite)
  1e the Reforged page (v1.9): a sixth bottom-navigation tab that is
     ours alone, carrying the Reforged 60-steps engine switch (pref
     reforged_60_steps, default OFF -- the card that sat on the Graphics
     tab in v1.5-v1.8, moved here unchanged in substance) and the bundled
     Reforged mod switch (phase 2 supplies the state). Their pages are
     untouched: the Simulation Rate card works again because libmain60.so
     really ships, GeneralsZHActivity keeps the host's own sim_hz engine
     selection with the engaged 60-steps engine taking precedence (it is
     the player's explicit choice on our page), GeneralsOnlineSession's
     clientId keeps the host's own sim_hz keying with a guard so the
     60-steps state announces the id its engine actually compiled in, and
     the upstream UpdateManager engine-override load path stays removed
     (kept from v1.8: the APK's engines are the only engines -- an engine
     substitution would silently break the unmodified-base promise).
     (v1.7's Online Mode card and v1.8's online-first engine branch are
     DELETED: no pool-impersonation machinery remains.)
The phase-3 engine change (locomotor carry-over, ThingTemplate.cpp) is NOT
here: it ships as ci/patches/engine-carryover.patch and is applied with
`git apply` before this script runs (Reforged-engine tree only since v1.9).
One patch applies to BOTH trees: package-android-zh-gradle-task.patch --
build tooling only (the packaging script ships nothing and touches no
engine or launcher code), and the base tree cannot be packaged without it
(the pristine script has no release-task knob and no staging knob for
libmainrf60.so).

Modes (env REFORGED_SURGERY_MODE):
  full  (default) -- the base tree: phases 1a-1e + the post-check.
  paths           -- the Reforged-engine tree: phase 1b + the post-check
                     only (that tree contributes exactly one native
                     library, libmainrf60.so; its Java/resources are
                     never packaged, but its engine binary carries the
                     same hardcoded old-id data paths and must resolve
                     this app's files directory).

Layout: REFORGED_SRC (env) points at the MYSOREZ checkout; default is the
parent of this repo's checkout (the CI workflow checks the overlay repo out
into <workspace>/reforged-overlay and MYSOREZ at <workspace>)."""
import os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
OVERLAY = os.path.dirname(_HERE)
SRC = os.environ.get('REFORGED_SRC') or os.path.dirname(OVERLAY)
MODE = os.environ.get('REFORGED_SURGERY_MODE', 'full')
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

_PATH_FILES = ['Core/GameEngine/Include/Common/GXControlScheme.h',
               'Core/GameEngine/Include/Common/GXLogging.h',
               'Core/GameEngine/Include/Common/GXManagedMods.h',
               'Core/GameEngine/Include/Common/GXMouseMode.h',
               'Core/GameEngine/Include/Common/GXRemoteConfig.h',
               'Core/GameEngine/Include/Common/GXSubtitles.h',
               'Core/Main/AndroidCrashHandler.cpp']

def post_check():
    leftover = [f for f in _PATH_FILES
                if f'/data/user/%d/{OLD_ID}/files/' in
                open(os.path.join(SRC, f), encoding='utf-8').read()]
    if leftover:
        sys.exit(f'OLD-ID PATHS REMAIN in: {leftover}')

print('surgery target tree:', SRC, '| mode:', MODE)

# ---------------- Phase 1a: applicationId + version ----------------
if MODE == 'full':
    edit('android/app/build.gradle', [
        ("applicationId 'com.generalsx.zerohour'", f"applicationId '{NEW_ID}'"),
        ('(project.androidVersionCode as Integer) : 10402)', '(project.androidVersionCode as Integer) : 10)'),
        ("project.androidVersionName : '1.4.2')", "project.androidVersionName : '1.9')"),
    ])

# ---------------- Phase 1b: native hardcoded data paths ----------------
# Identity, not a feature: every engine binary shipped in this APK (the
# host's own three and our 60-steps engine alike) resolves the app's
# private files directory through these paths; under this package id the
# old id's directory belongs to another app and is not even readable.
for f in _PATH_FILES:
    edit(f, [('/data/user/%d/com.generalsx.zerohour/files/', f'/data/user/%d/{NEW_ID}/files/')])

if MODE == 'paths':
    post_check()
    print('SURGERY (phase 1b only, mode=paths) DONE')
    sys.exit(0)

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

# ---------------- Phase 1e: the Reforged page (v1.9) ----------------
# Everything of ours lives on ONE new bottom-navigation tab, built exactly
# the way the shell builds its own five: a TAB_* constant, a menu entry in
# buildBottomNav(), a tabTitle() case, a showTab() case. Their pages are
# not edited at all -- in particular the Simulation Rate card keeps its
# pristine body and works again, because libmain60.so really ships now.
# The page carries two switches, both Zero Hour only:
#  * the Reforged 60-steps engine (libmainrf60.so, from the patched tree):
#    its own pref (reforged_60_steps, default OFF) -- never a sim_hz
#    value, because GeneralsOnlineActivity's crossplay flow writes sim_hz
#    itself and must never enable this engine;
#  * the bundled Reforged mod, through the ModManager helpers phase 2
#    injects -- the same listMods/saveOrder state the Mods screen shows,
#    so there is one switch state with two handles, never two states.
# The page text states the separation plainly: the original app's online
# games are played with the original engines and the mod off, and both
# choices stay the player's, in the open. No mode rearranges them quietly
# (v1.7's Online Mode and v1.8's online-first branch are deleted).
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
    ('    private static final int TAB_HELP = 5;',
     """    private static final int TAB_HELP = 5;
    // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.9) Our own page:
    // the one bottom-navigation destination this build adds.
    private static final int TAB_REFORGED = 6;"""),
    ('        menu.add(Menu.NONE, TAB_HELP, 4, R.string.nav_tab_help).setIcon(R.drawable.ic_gzh_info);',
     """        menu.add(Menu.NONE, TAB_HELP, 4, R.string.nav_tab_help).setIcon(R.drawable.ic_gzh_info);
        menu.add(Menu.NONE, TAB_REFORGED, 5, R.string.nav_tab_reforged).setIcon(R.drawable.ic_gzh_chip);"""),
    ('            case TAB_HELP:      return R.string.nav_tab_help;',
     """            case TAB_HELP:      return R.string.nav_tab_help;
            case TAB_REFORGED:  return R.string.nav_tab_reforged;"""),
    ("""            case TAB_HELP:
                buildHelpSection(page);
                break;""",
     """            case TAB_HELP:
                buildHelpSection(page);
                break;
            case TAB_REFORGED:
                buildReforgedPage(page);
                break;"""),
    ("""    private int tabTitle(int tab) {""",
     """    // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.9) The Reforged
    // page. Everything this build adds over the original app lives behind
    // this one destination and nothing of ours lives anywhere else; the
    // five original pages are upstream's own, untouched. The intro card
    // states the separation plainly, including what the original app's
    // online games need (the original engines, and the mod below off) --
    // both switches sit here, in the open, and stay the player's. The two
    // content cards are Zero Hour only, like the data they govern.
    private void buildReforgedPage(LinearLayout page) {
        LinearLayout intro = UiKit.card(page);
        UiKit.sectionHeader(intro, R.drawable.ic_gzh_chip,
            getString(R.string.setup_card_reforged_page), true);
        UiKit.supporting(intro, getString(R.string.setup_reforged_page_intro));
        if (isGeneralsSelected(this)) {
            return;
        }
        buildReforgedEngineCard(page);
        buildReforgedModCard(page);
    }

    // The Reforged 60-steps engine switch: the card that sat on the
    // Graphics tab in v1.5-v1.8, moved to our own page with its gates
    // (the library must actually be in the APK; the page itself owns the
    // Zero Hour gate now). The switch writes only the player's own
    // reforged_60_steps pref; GeneralsZHActivity.getLibraries() gives
    // that choice precedence over the Simulation Rate selection, because
    // exactly one engine can load and this is the explicit one.
    private void buildReforgedEngineCard(LinearLayout root) {
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
    }

    // The bundled Reforged mod switch: ModManager's own state (the same
    // stored order the Mods screen edits), never a parallel pref -- the
    // page reads it when it is built and writes it through the same
    // helpers, so the two handles can never disagree. A mod that is not
    // installed yet gets an honest line instead of a dead switch.
    private void buildReforgedModCard(LinearLayout root) {
        LinearLayout content = UiKit.card(root);
        UiKit.sectionHeader(content, R.drawable.ic_gzh_chip,
            getString(R.string.setup_card_reforged_mod), true);
        Boolean enabled = ModManager.bundledModEnabled(this);
        if (enabled == null) {
            UiKit.supporting(content, getString(R.string.setup_reforged_mod_absent));
            return;
        }
        com.google.android.material.materialswitch.MaterialSwitch sw = UiKit.switchRow(content,
            getString(R.string.setup_reforged_mod_title), getString(R.string.setup_reforged_mod_desc));
        sw.setChecked(enabled);
        sw.setOnCheckedChangeListener((button, checked) ->
            ModManager.setBundledModEnabled(this, checked));
        UiKit.helpText(content, getString(R.string.setup_reforged_mod_help));
    }

    private int tabTitle(int tab) {"""),
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
        // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.9) The
        // Reforged page's 60-steps engine takes precedence over the
        // Simulation Rate selection below: exactly one engine can load,
        // and this engagement is the player's explicit choice on our own
        // page. Zero Hour only (the base game has no 60-steps library),
        // the player's own switch only (never sim_hz -- GeneralsOnline-
        // Activity writes that pref itself), and only when the library
        // is actually in the APK. With the switch off, the host's own
        // selection runs exactly as upstream wrote it.
        if (!SetupActivity.isGeneralsSelected(this)
                && SetupActivity.getReforged60(this)
                && new java.io.File(getApplicationInfo().nativeLibraryDir, "libmainrf60.so").isFile()) {
            engine = "mainrf60";
        } else if (SetupActivity.getSimHz(this) == SetupActivity.SIM_HZ_CROSSPLAY
                && new java.io.File(getApplicationInfo().nativeLibraryDir, "lib" + engines[1] + ".so").isFile()) {
            engine = engines[1];
        }"""),
    # The UpdateManager engine override stays removed at its only point of
    # use (kept from v1.8, wave-8 record section 8.4: proof it could never
    # fire in this build -- the phase-1d channel serves no manifest, and
    # any manifest would have to be signed with the upstream ECDSA key,
    # which this project does not hold). Under the v1.9 separation the
    # point is sharper: the base app's promise is the host's engines
    # exactly as this APK installed them, and a downloaded substitute
    # would silently void it. UpdateManager itself is untouched; its
    # checks simply find no loadable engine here.
    ("""    // GeneralsX @feature Android port 27/09/2026 An engine delivered by UpdateManager (signed
    // manifest, SHA-256 checked, built against this APK's own libraries) runs instead of the
    // APK's. Only the engine library is replaced; SDL3 and everything the engine links against
    // or dlopen()s by name still come from the APK, which is why the manifest has to name the
    // exact libraries it was built with. Null means the APK's own engine.
    private String mEngineOverridePath;""",
     """    // GeneralsX @feature Zero Hour Reforged 12/11/2026 The upstream
    // UpdateManager engine override that stood here is REMOVED, not
    // merely unused (v1.8, kept in v1.9): no downloaded engine is ever
    // loaded in this build -- the libraries in the APK are the only
    // engines, the host's own exactly as installed and ours under our
    // own name. See loadLibraries() below and the wave-8 record,
    // section 8.4."""),
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
        // Zero Hour Reforged (v1.8, kept in v1.9): no UpdateManager
        // engine override -- the APK's own libraries always load,
        // exactly as every shipped build of this project has in fact
        // run (the repointed channel has never delivered an engine).
        for (String lib : getLibraries()) {
            System.loadLibrary(lib);
        }
    }"""),
])

# The launcher's GeneralsOnline client id must announce the engine that
# will actually run (the file's own header comment demands the mirror).
# For the host's own engines the pristine sim_hz keying is truthful again
# in v1.9 -- both of their libraries really ship, and getLibraries()
# honours sim_hz exactly as upstream wrote it -- so the pristine body
# below stands, with ONE guard in front of it: when the Reforged page's
# 60-steps engine is engaged it takes precedence in getLibraries(), and
# its compiled-in GENERALS_ONLINE_CLIENT_ID is "gen_online_30hz" (it is
# NOT built with GENERALS_ONLINE_HIGH_FPS_SERVER; the workflow strings-
# checks both facts on every build). The guard returns this class's own
# constant for exactly the states where that engine loads, so the
# announcement never claims the host's 60 Hz for our engine.
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
        // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.9) The
        // mirror rule above resolves through the host's own keying
        // again -- with both host engines really in the APK, the sim_hz
        // condition below names the engine getLibraries() will load.
        // One state is ours, not theirs: the Reforged page's 60-steps
        // engine takes precedence in getLibraries() when it is engaged,
        // under exactly the condition mirrored here, and its compiled-in
        // id is CLIENT_ID (it is not a HIGH_FPS build) -- so it is
        // announced as what it is, never as the host's 60 Hz engine.
        if (ctx != null
                && !SetupActivity.isGeneralsSelected(ctx)
                && SetupActivity.getReforged60(ctx)
                && new java.io.File(ctx.getApplicationInfo().nativeLibraryDir,
                        "libmainrf60.so").isFile()) {
            return CLIENT_ID;
        }
        if (ctx != null
                && SetupActivity.getSimHz(ctx) == SetupActivity.SIM_HZ_CROSSPLAY
                && new java.io.File(ctx.getApplicationInfo().nativeLibraryDir,
                        "libmain60.so").isFile()) {
            return "gen_online_60hz";
        }
        return CLIENT_ID;
    }"""),
])

# Engine card strings in every locale, inserted right after the sim-rate
# toast line (the anchor string name exists in all locales; its text is
# translated). AAPT2 law: an apostrophe inside a string resource must
# reach the XML escaped as \' or mergeReleaseResources rejects the string
# ("unescaped apostrophe in string") -- hence the \\' in the Python
# literals below, which puts a literal backslash before the apostrophe in
# the XML. The help text is revised in v1.9: the v1.5 sentence "this mode
# plays no network games" predates the separation -- the honest rule now
# is that this engine plays network games only against this same build.
_RF60_STRINGS_EN = [
    ('setup_card_reforged60', 'Reforged Engine'),
    ('setup_reforged60_title', 'Reforged engine \u2014 60 steps per second (experimental)'),
    ('setup_reforged60_desc', "Reforged\\'s own doubled simulation rate: smoother motion and faster response, at the cost of heavier work for the processor."),
    ('setup_reforged60_help', "The engine is chosen when the game starts, so the change applies the next time you launch it. Save games and replays belong to the rate that made them: each engine refuses the other\\'s, cleanly. Online, this engine plays only against this same build; for the original app\\'s online games, leave this off and use the Simulation Rate card on the Graphics tab. If large battles slow down, switch it off."),
]
_RF60_STRINGS_AR = [
    ('setup_card_reforged60', 'محرك ريفورجيد'),
    ('setup_reforged60_title', 'محرك ريفورجيد — 60 خطوة بالثانية (تجريبي)'),
    ('setup_reforged60_desc', 'محاكاة ريفورجيد الأصلية بمعدل مضاعف: حركة أنعم واستجابة أسرع، مقابل شغل أثقل على المعالج.'),
    ('setup_reforged60_help', 'يُختار المحرك عند بدء اللعبة، فيسري التغيير عند تشغيلها في المرة القادمة. ملفات الحفظ والإعادات تخص المعدل الذي صنعها: كل محرك يرفض ملفات الآخر بشكل نظيف. عبر الأونلاين، لا يلعب هذا المحرك إلا ضد هذه النسخة نفسها؛ ولمباريات التطبيق الأصلي عبر الأونلاين أوقف هذا الخيار واستخدم بطاقة معدل المحاكاة في تبويب الرسوميات. إذا تراجعت السلاسة في المعارك الكبيرة، أوقف هذا الخيار.'),
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

# Reforged page strings in every locale (the tab label, the intro card,
# the mod card), inserted right after the nav_tab_help line -- the shell's
# own navigation family, so ours sits with its kin. No name here exists
# upstream (the proof battery censuses them against pristine per locale).
_PAGE_STRINGS_EN = [
    ('nav_tab_reforged', 'Reforged'),
    ('setup_card_reforged_page', 'Reforged'),
    ('setup_reforged_page_intro', 'Everything on this page is what this build adds, and nothing of it lives anywhere else. Every other page of this launcher is the original app, untouched. The original online games belong to the original engines, with the Reforged mod below switched off; both switches are here, in the open, and the choice stays yours.'),
    ('setup_card_reforged_mod', 'Reforged Mod'),
    ('setup_reforged_mod_title', 'Reforged data mod'),
    ('setup_reforged_mod_desc', 'The Reforged fixes and balance package bundled with this build, as one mod.'),
    ('setup_reforged_mod_help', 'The same switch the Mods screen shows: one state, two places, never two states. The original online games need it off; offline, the choice is yours.'),
    ('setup_reforged_mod_absent', 'Not installed yet. It installs itself the first time a Zero Hour game folder is set up.'),
]
_PAGE_STRINGS_AR = [
    ('nav_tab_reforged', 'ريفورجيد'),
    ('setup_card_reforged_page', 'ريفورجيد'),
    ('setup_reforged_page_intro', 'كل ما في هذه الصفحة يخص هذه النسخة وحدها، ولا يوجد منه شيء في أي مكان آخر. بقية صفحات هذا المشغّل هي التطبيق الأصلي دون أي مساس. مباريات الأونلاين الأصلية تخص المحركات الأصلية، مع إيقاف مود ريفورجيد التالي؛ والمفتاحان هنا، في العلن، والاختيار يبقى لك.'),
    ('setup_card_reforged_mod', 'مود ريفورجيد'),
    ('setup_reforged_mod_title', 'مود بيانات ريفورجيد'),
    ('setup_reforged_mod_desc', 'حزمة إصلاحات وتوازن ريفورجيد المرفقة مع هذه النسخة، في مود واحد.'),
    ('setup_reforged_mod_help', 'المفتاح نفسه الذي تظهره شاشة المودات: حالة واحدة في مكانين، لا حالتان أبدًا. مباريات الأونلاين الأصلية تحتاج إيقافه؛ وخارج الأونلاين، الاختيار لك.'),
    ('setup_reforged_mod_absent', 'غير مثبّت بعد. يثبّت نفسه تلقائيًا عند إعداد مجلد لعبة زيرو أور لأول مرة.'),
]
for d in os.listdir(resdir):
    p = os.path.join(resdir, d, 'strings.xml')
    if not (d.startswith('values') and os.path.isfile(p)):
        continue
    s = open(p, encoding='utf-8').read()
    if 'name="nav_tab_reforged"' in s:
        continue
    entries = _PAGE_STRINGS_AR if d == 'values-ar' else _PAGE_STRINGS_EN
    block = ''.join(f'\n    <string name="{n}">{t}</string>' for n, t in entries)
    lines = s.split('\n')
    idx = next((i for i, ln in enumerate(lines) if 'name="nav_tab_help"' in ln), None)
    if idx is None:
        idx = next(i for i, ln in enumerate(lines) if '</resources>' in ln)
        lines.insert(idx, block.lstrip('\n'))
    else:
        lines.insert(idx + 1, block.lstrip('\n'))
    open(p, 'w', encoding='utf-8').write('\n'.join(lines))
    print('page strings', os.path.join(d, 'strings.xml'))

# ---------------- post-check: no old-id native paths remain ----------------
post_check()

print('SURGERY (phases 1a-1e, mode=full) DONE')
