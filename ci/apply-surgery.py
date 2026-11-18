#!/usr/bin/env python3
"""Zero Hour Reforged — package-id surgery on a pristine MYSOREZ checkout.
CI version of the v1 local apply-surgery.py. Since v1.16 (owner
orders 2026-11-17) the build is PURE AND SINGLE-ENGINED: the APK
carries exactly one play engine, libmainz60.so -- a true 60-steps
build of the stock MYSOREZ engine (pristine tree + the n60 patch
set: foundations, flip, stamp, pacing) -- plus the Stage C test
payload libmainrfx.so. No Reforged data is bundled (phase 2 no
longer runs; the user's game folder is played exactly as it is),
the two Reforged play engines of v1.13-v1.15 are removed, and
there is no engine switch anywhere: GeneralsZHActivity names the
one library directly. The launcher shell is still the host's, with
our page in it. The phases are:
  1a applicationId + version defaults in android/app/build.gradle
  1b native hardcoded /data/user/<uid>/<old id>/files/ paths (7 files) --
     app identity for EVERY engine binary this APK ships, so it runs in
     both modes below (base tree and engine tree alike)
  1c app_name label in every locale's strings.xml
  1d UpdateManager update channel repointed at this repo (no OTA overwrite)
  1e the Reforged page (v1.9; entry moved in v1.11): our own launcher
     page, entered from a row on the Home page -- Material's
     BottomNavigationView accepts at most five items, and the sixth
     bottom-navigation item v1.9/v1.10 added threw at inflation and
     took the whole settings interface down with it (v1.10 device
     verdict). Their five nav items are untouched. Since v1.16 the
     page carries only the WiFi-play status card (no engine choice
     exists). Phase 1e also settles the shell around the removed
     engines: getSelectedGame always answers Zero Hour (no Generals
     library ships), the Simulation Rate section is not built (it
     chose between the host's engines), GeneralsZHActivity loads
     exactly libmainz60, and GeneralsOnlineSession's clientId is
     this class's own constant unconditionally (the engine compiles
     it in). The upstream UpdateManager engine-override load path
     stays removed (kept from v1.8: the APK's engine is the only
     engine).
package-android-zh-gradle-task.patch applies to BOTH trees --
build tooling only (the packaging script ships nothing and touches
no engine or launcher code), and the base tree cannot be packaged
without it (the pristine script has no release-task knob and no
staging knob for libmainz60.so).

Modes (env REFORGED_SURGERY_MODE):
  full  (default) -- the base tree: phases 1a-1e + the post-check.
  paths           -- the engine tree: phase 1b + the post-check only
                     (that tree contributes the one play engine
                     library, libmainz60.so; its Java/resources are
                     never packaged, but its engine binary carries
                     the same hardcoded old-id data paths and must
                     resolve this app's files directory).

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
        ('(project.androidVersionCode as Integer) : 10402)', '(project.androidVersionCode as Integer) : 22)'),
        ("project.androidVersionName : '1.4.2')", "project.androidVersionName : '1.17')"),
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

# ---------------- Phase 1e: the Reforged page (v1.9; entry fixed v1.11) --
# Everything of ours lives on ONE page of its own, rendered by showTab()
# like any of the shell's pages: a TAB_* constant, a tabTitle() case, a
# showTab() case -- and, since v1.11, an entry row on the Home page
# instead of a bottom-navigation item. v1.9/v1.10 added a sixth menu item
# to buildBottomNav(); Material's BottomNavigationView hard-caps at five
# items, so the nav threw at inflation and the whole settings interface
# fell back to the plain-widget UI (v1.10 device verdict, 2026-11-12).
# Their pages are not edited at all -- in particular the Simulation Rate
# card keeps its pristine body and works again, because libmain60.so
# really ships now.
# The page carries the WiFi-play status card, all Zero Hour only.
# v1.16: there is no engine choice and no bundled data -- the app
# ships one play engine (libmainz60.so, the pure 60-steps build on
# the stock base) and plays the user's game folder exactly as it
# is; phase 2 does not run anymore.
# The same edit list settles the shell around the removed engines:
# getSelectedGame always answers Zero Hour, and the Simulation Rate
# section (which chose between the host's engines) is not built.
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

    // Zero Hour Reforged (v1.16): no engine pref exists anymore. This
    // app ships exactly one play engine -- libmainz60.so, the pure
    // 60-steps build on the stock base -- and GeneralsZHActivity names
    // it directly. The v1.13-v1.15 engine pref, its accessors and
    // its switch are gone, and with them the stale-engine trap: a
    // pref could lie about which library the process had actually
    // loaded; a constant cannot."""),
    ('    private static final int TAB_HELP = 5;',
     """    private static final int TAB_HELP = 5;
    // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.9) Our own page.
    // Not a bottom-navigation item: the bar is full at five (see the Home
    // entry row below); this is the page id showTab() renders.
    private static final int TAB_REFORGED = 6;"""),
    ("""        // The one thing this app exists to do, as the first thing on it.
        UiKit.button(page, UiKit.BTN_PRIMARY, R.drawable.ic_gzh_play,
            getString(R.string.setup_button_launch_game), this::onLaunchGame);""",
     """        // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.11) The entry
        // to our own page, on the Home page -- the way the Mods screen is
        // entered from its row in the card above. There is deliberately no
        // bottom-navigation item for it: Material's BottomNavigationView
        // accepts at most five items, and the sixth added in v1.9/v1.10
        // threw at inflation and took the whole settings interface down
        // with it (device verdict on v1.10). Their five items stay
        // untouched; showTab() renders our page like any other.
        LinearLayout reforgedEntry = UiKit.card(page);
        UiKit.listRow(reforgedEntry, R.drawable.ic_gzh_chip,
            getString(R.string.nav_tab_reforged),
            getString(R.string.setup_reforged_home_row_desc),
            () -> showTab(TAB_REFORGED));

        // The one thing this app exists to do, as the first thing on it.
        UiKit.button(page, UiKit.BTN_PRIMARY, R.drawable.ic_gzh_play,
            getString(R.string.setup_button_launch_game), this::onLaunchGame);"""),
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
     """    // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.9; v1.13) The
    // Reforged page. v1.16: this app ships one play engine and no
    // bundled data, so the page carries only the WiFi-play status
    // card, and its intro says exactly that. The page is Zero Hour
    // only, like the app (the game getter never answers Generals
    // since v1.13, so the gate below always passes).
    private void buildReforgedPage(LinearLayout page) {
        LinearLayout intro = UiKit.card(page);
        UiKit.sectionHeader(intro, R.drawable.ic_gzh_chip,
            getString(R.string.setup_card_reforged_page), true);
        UiKit.supporting(intro, getString(R.string.setup_reforged_page_intro));
        if (isGeneralsSelected(this)) {
            return;
        }
        buildReforgedWifiCard(page);
    }

    // Zero Hour Reforged (v1.16) The WiFi-play card is a status card
    // now. There is one engine in this app, so there is nothing to
    // align and nothing to prepare: a WiFi match stands or falls on
    // both phones running THIS build over game folders with the same
    // Community Patch state, and the card says exactly that, in words
    // the player can compare against the other phone's screen. It
    // reads no files and writes no prefs -- the v1.12-v1.15 card's
    // folder scan (and its fresh-install crash, fixed in v1.15.4)
    // died with the engine choice it served.
    private void buildReforgedWifiCard(LinearLayout root) {
        LinearLayout content = UiKit.card(root);
        UiKit.sectionHeader(content, R.drawable.ic_gzh_chip,
            getString(R.string.setup_card_reforged_wifi), true);
        UiKit.supporting(content, getString(R.string.setup_reforged_wifi_intro));
        UiKit.supporting(content, getString(R.string.setup_reforged_wifi_state));
        UiKit.helpText(content, getString(R.string.setup_reforged_wifi_help));
    }

    private int tabTitle(int tab) {"""),

    # GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.13) This app is
    # Zero Hour only: the host's engines were removed by the owner's
    # order, and with them every Generals library -- a Generals selection
    # would start a game whose engine is not in the APK. The getter
    # settles every install (including one left on Generals by an older
    # build) on Zero Hour; the Home page's game picker reads this same
    # getter, displays Zero Hour, and its Generals tap lands back here.
    ("""    static String getSelectedGame(android.content.Context ctx) {
        String game = ctx.getSharedPreferences(PREFS_NAME, MODE_PRIVATE).getString(PREF_GAME, GAME_ZERO_HOUR);
        return GAME_GENERALS.equals(game) ? GAME_GENERALS : GAME_ZERO_HOUR;
    }""",
     """    static String getSelectedGame(android.content.Context ctx) {
        // Zero Hour Reforged (v1.13): Zero Hour only -- see the note in
        // the surgery script. The stored pref is left alone; it is
        // simply never honoured with a Generals answer.
        return GAME_ZERO_HOUR;
    }"""),
    # The Simulation Rate section selected between the host's two
    # engines; neither ships since v1.13, so the section is not built.
    # The method itself stays in the class, uncalled. The engine choice
    # (our standard engine / our 60-steps engine) is the Reforged
    # page's engine card.
    ("""                buildSimRateSection(page);""",
     """                // Zero Hour Reforged (v1.13): no Simulation Rate
                // section -- the host engines it selected no longer
                // ship, and there is no engine choice anywhere
                // (v1.16: one play engine, libmainz60.so)."""),
])

edit('android/app/src/main/java/com/generalsx/zerohour/GeneralsZHActivity.java', [
    ("""        final String[] engines = SetupActivity.engineLibraries(this);
        String engine = engines[0];
        if (SetupActivity.getSimHz(this) == SetupActivity.SIM_HZ_CROSSPLAY
                && new java.io.File(getApplicationInfo().nativeLibraryDir, "lib" + engines[1] + ".so").isFile()) {
            engine = engines[1];
        }""",
     """        // Zero Hour Reforged (v1.16): this app ships exactly ONE play
        // engine -- libmainz60.so, the pure 60-steps build on the
        // stock base -- so there is no choice to read and no fallback
        // to hide behind: if the library were missing, loadLibrary
        // would fail loud at once instead of silently starting a
        // different engine. The v1.13-v1.15 pref ternary that stood
        // here was the stale-engine trap (a switch could name a
        // library the process had never loaded); a constant cannot
        // lie.
        String engine = "mainz60";"""),
    # The UpdateManager engine override stays removed at its only point of
    # use (kept from v1.8, wave-8 record section 8.4: proof it could never
    # fire in this build -- the phase-1d channel serves no manifest, and
    # any manifest would have to be signed with the upstream ECDSA key,
    # which this project does not hold). Since v1.13 the point is
    # sharper still: the APK's two Reforged engines are the only engines
    # this app has, and a downloaded substitute would silently void
    # that. UpdateManager itself is untouched; its checks simply find
    # no loadable engine here.
    ("""    // GeneralsX @feature Android port 27/09/2026 An engine delivered by UpdateManager (signed
    // manifest, SHA-256 checked, built against this APK's own libraries) runs instead of the
    // APK's. Only the engine library is replaced; SDL3 and everything the engine links against
    // or dlopen()s by name still come from the APK, which is why the manifest has to name the
    // exact libraries it was built with. Null means the APK's own engine.
    private String mEngineOverridePath;""",
     """    // GeneralsX @feature Zero Hour Reforged 12/11/2026 The upstream
    // UpdateManager engine override that stood here is REMOVED, not
    // merely unused (v1.8, kept since): no downloaded engine is ever
    // loaded in this build -- the two Reforged libraries in the APK
    // are the only engines this app has. See loadLibraries() below
    // and the wave-8 record, section 8.4."""),
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
# Since v1.13 both engines in the APK are ours and both are compiled
# with this class's own CLIENT_ID ("gen_online_30hz" -- neither is
# built with GENERALS_ONLINE_HIGH_FPS_SERVER; the workflow strings-
# checks the fact on every build), so the announcement is the constant
# unconditionally. The host keying that stood here announced the host's
# 60 Hz id when the host's 60 Hz library was selected and present;
# that library no longer ships.
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
        // Zero Hour Reforged (v1.13): both engines this app ships are
        // ours, and both are compiled with this class's own CLIENT_ID
        // ("gen_online_30hz" -- neither is a HIGH_FPS build; the
        // workflow strings-checks the fact on every build). The host
        // keying that stood here announced the host's 60 Hz id for
        // the host's 60 Hz library; that library no longer ships, so
        // the honest answer is unconditional.
        return CLIENT_ID;
    }"""),
])

# ---------------- v1.16: no bundled data, no mod locks ----------------
# Phase 2 does not run anymore: there is no bundled package, so the
# v1.13 ModManagerActivity locks and the mods-count filter (which
# referenced ModManager.BUNDLED_DIR, a phase-2 definition) are gone
# with it -- the host's mod UI stands exactly as upstream wrote it.

# (v1.16: the rf60 switch strings died with the switch -- no card
# consumes them, so they are no longer inserted into any locale.)

# Reforged page strings in every locale (the tab label, the intro card,
# the mod card), inserted right after the nav_tab_help line -- the shell's
# own navigation family, so ours sits with its kin. No name here exists
# upstream (the proof battery censuses them against pristine per locale).
_PAGE_STRINGS_EN = [
    ('nav_tab_reforged', 'Reforged'),
    ('setup_card_reforged_page', 'Reforged'),
    ('setup_reforged_home_row_desc', 'One pure 60-steps engine and WiFi play, on their own page'),
    ('setup_reforged_page_intro', 'This app runs one engine: a pure 60-steps build on the stock game, with no Reforged data added -- your game folder is played exactly as it is. The WiFi-play card is below. The original app and its online games live in the original app, not in this one.'),
]
_PAGE_STRINGS_AR = [
    ('nav_tab_reforged', 'ريفورجيد'),
    ('setup_card_reforged_page', 'ريفورجيد'),
    ('setup_reforged_home_row_desc', 'محرك 60 خطوة نقي واللعب عبر الوايفاي، بصفحة لحالها'),
    ('setup_reforged_page_intro', 'هذا التطبيق يعمل بمحرك واحد: بناء 60 خطوة نقي على اللعبة الأصلية، دون أي بيانات ريفورجيد مضافة — مجلد لعبتك يُلعب كما هو تمامًا. بطاقة اللعب عبر الوايفاي في الأسفل. التطبيق الأصلي ومبارياته عبر الأونلاين يعيشان في التطبيق الأصلي، لا في هذا.'),
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

# WiFi-play card strings in every locale (v1.12), same insertion point and
# discipline as the page strings above. No name here exists upstream.
_WIFI_STRINGS_EN = [
    ('setup_card_reforged_wifi', 'WiFi Play'),
    ('setup_reforged_wifi_intro', 'Two phones, one build: a WiFi match needs both phones running this exact build (1.16, the pure 60-steps engine), over game folders with the same Community Patch state. The game compares both identities when the match starts and keeps comparing while it runs; a difference on either phone ends the match at the start.'),
    ('setup_reforged_wifi_state', 'This phone: Zero Hour Reforged 1.16 - pure 60-steps engine (Z60)'),
    ('setup_reforged_wifi_help', 'Compare this card on both phones before you start -- both must read the same build. If a match ever reports a mismatch, export the logs from both phones: the [GX-CRC] lines name the identity that differed.'),
]
_WIFI_STRINGS_AR = [
    ('setup_card_reforged_wifi', 'اللعب عبر الوايفاي'),
    ('setup_reforged_wifi_intro', 'هاتفان وبناء واحد: مباراة الوايفاي تحتاج أن يعمل الهاتفان على هذا البناء بالضبط (1.16، محرك 60 خطوة النقي)، فوق مجلدَي لعبة بحالة باتش مجتمع واحدة. اللعبة تقارن هويتي الهاتفين عند بدء المباراة وتظل تقارن أثناءها؛ وأي اختلاف في أي هاتف ينهي المباراة من بدايتها.'),
    ('setup_reforged_wifi_state', 'هذا الهاتف: زيرو أور ريفورجيد 1.16 - محرك 60 خطوة نقي (Z60)'),
    ('setup_reforged_wifi_help', 'قارن هذه البطاقة على الهاتفين قبل أن تبدأ — لازم يقرأا البناء نفسه. إذا أبلغت مباراة يومًا عن عدم تطابق، صدّر السجلات من الهاتفين: سطور [GX-CRC] تسمّي الهوية التي اختلفت.'),
]
for d in os.listdir(resdir):
    p = os.path.join(resdir, d, 'strings.xml')
    if not (d.startswith('values') and os.path.isfile(p)):
        continue
    s = open(p, encoding='utf-8').read()
    if 'name="setup_card_reforged_wifi"' in s:
        continue
    entries = _WIFI_STRINGS_AR if d == 'values-ar' else _WIFI_STRINGS_EN
    block = ''.join(f'\n    <string name="{n}">{t}</string>' for n, t in entries)
    lines = s.split('\n')
    idx = next((i for i, ln in enumerate(lines) if 'name="nav_tab_help"' in ln), None)
    if idx is None:
        idx = next(i for i, ln in enumerate(lines) if '</resources>' in ln)
        lines.insert(idx, block.lstrip('\n'))
    else:
        lines.insert(idx + 1, block.lstrip('\n'))
    open(p, 'w', encoding='utf-8').write('\n'.join(lines))
    print('wifi strings', os.path.join(d, 'strings.xml'))

# ---------------- post-check: no old-id native paths remain ----------------
post_check()

print('SURGERY (phases 1a-1e, mode=full) DONE')
