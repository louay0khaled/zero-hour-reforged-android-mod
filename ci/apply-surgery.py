#!/usr/bin/env python3
"""Zero Hour Reforged — package-id surgery on a pristine MYSOREZ checkout.
CI version of the v1 local apply-surgery.py. Since v1.13 the build is
OURS ALONE (owner order 2026-11-12, superseding the v1.9 separation):
the host's engines no longer ship -- the APK carries only the two
Reforged engines (libmainrf.so, libmainrf60.so) -- and the bundled
Reforged data is core app data, always on (phase 2 forces it; there is
no mod switch anywhere). The launcher shell is still the host's, with
our page in it. The phases are:
  1a applicationId + version defaults in android/app/build.gradle
  1b native hardcoded /data/user/<uid>/<old id>/files/ paths (7 files) --
     app identity for EVERY engine binary this APK ships, so it runs in
     both modes below (base tree and Reforged-engine tree alike)
  1c app_name label in every locale's strings.xml
  1d UpdateManager update channel repointed at this repo (no OTA overwrite)
  1e the Reforged page (v1.9; entry moved in v1.11): our own launcher
     page, entered from a row on the Home page -- Material's
     BottomNavigationView accepts at most five items, and the sixth
     bottom-navigation item v1.9/v1.10 added threw at inflation and
     took the whole settings interface down with it (v1.10 device
     verdict). Their five nav items are untouched. The page carries
     the engine choice (v1.13: the 60-steps switch, pref
     reforged_60_steps, default OFF; OFF means the standard Reforged
     engine -- there is no separate enhanced-30 switch anymore,
     because the standard engine is simply ours now) and the WiFi-play
     card (v1.12). Phase 1e also settles the shell around the removed
     engines: getSelectedGame always answers Zero Hour (no Generals
     library ships), the Simulation Rate section is not built (it
     chose between the host's engines), GeneralsZHActivity loads
     exactly our two libraries by the page's switch, and
     GeneralsOnlineSession's clientId is this class's own constant
     unconditionally (both our engines compile it in). The upstream
     UpdateManager engine-override load path stays removed (kept from
     v1.8: the APK's engines are the only engines).
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
                     only (that tree contributes the Reforged engine
                     libraries -- libmainrf60.so and, since v1.10,
                     libmainrf.so; its Java/resources are never
                     packaged, but its engine binaries carry the same
                     hardcoded old-id data paths and must resolve this
                     app's files directory).

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
        ('(project.androidVersionCode as Integer) : 10402)', '(project.androidVersionCode as Integer) : 15)'),
        ("project.androidVersionName : '1.4.2')", "project.androidVersionName : '1.14')"),
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
# The page carries the engine choice and the WiFi-play card, all Zero
# Hour only (v1.13):
#  * the Reforged 60-steps engine (libmainrf60.so, from the patched
#    tree): its own pref (reforged_60_steps, default OFF) -- never a
#    sim_hz value. OFF loads the standard Reforged engine
#    (libmainrf.so, the same patched tree at the standard rate): since
#    v1.13 those two are the only engines in the APK, so the choice is
#    a single switch, not a pair of alternatives;
#  * the bundled Reforged data has no switch at all: phase 2 forces it
#    enabled at every launcher start (core app data, not a mod).
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
    // Reforged page. Since v1.13 this app ships only our engines and
    // its Reforged data is built in, so the page is no longer a
    // separation boundary: it carries the engine choice and the
    // WiFi-play card, and its intro says exactly that. The page is
    // Zero Hour only, like the app (the game getter never answers
    // Generals since v1.13, so the gate below always passes).
    private void buildReforgedPage(LinearLayout page) {
        LinearLayout intro = UiKit.card(page);
        UiKit.sectionHeader(intro, R.drawable.ic_gzh_chip,
            getString(R.string.setup_card_reforged_page), true);
        UiKit.supporting(intro, getString(R.string.setup_reforged_page_intro));
        if (isGeneralsSelected(this)) {
            return;
        }
        buildReforgedEngineCard(page);
        buildReforgedWifiCard(page);
    }

    // The Reforged engine card (v1.13): this app ships ONLY our two
    // engines, and this card is the whole engine choice -- the
    // 60-steps engine (libmainrf60.so) behind its switch, and the
    // standard Reforged engine (libmainrf.so) whenever the switch is
    // off. There is no third state and nothing to disengage: the
    // switch writes only its own pref, and
    // GeneralsZHActivity.getLibraries() reads exactly this state.
    private void buildReforgedEngineCard(LinearLayout root) {
        if (!new java.io.File(getApplicationInfo().nativeLibraryDir, "libmainrf60.so").isFile()) {
            return;
        }
        LinearLayout content = UiKit.card(root);
        UiKit.sectionHeader(content, R.drawable.ic_gzh_chip,
            getString(R.string.setup_card_reforged60), true);
        com.google.android.material.materialswitch.MaterialSwitch sw60 = UiKit.switchRow(content,
            getString(R.string.setup_reforged60_title), getString(R.string.setup_reforged60_desc));
        sw60.setChecked(getReforged60(this));
        sw60.setOnCheckedChangeListener((button, checked) -> setReforged60(this, checked));
        UiKit.helpText(content, getString(R.string.setup_reforged60_help));
    }

    private int tabTitle(int tab) {"""),
    ("""        UiKit.helpText(content, getString(R.string.setup_reforged60_help));
    }

    private int tabTitle(int tab) {""",
     """        UiKit.helpText(content, getString(R.string.setup_reforged60_help));
    }

    // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.12; v1.13) The
    // WiFi-play card. A match between two of our builds stands or falls
    // on identity: the game compares the engine and data identities of
    // both phones when the match starts and keeps comparing while it
    // runs. The Reforged data is built into this app -- identical on
    // both phones by construction -- so what the players must align is
    // the engine choice above and the Community Patch state of the
    // game folder. The card does two things only: it SAYS what this
    // phone is set to, in words the player can compare against the
    // other phone's screen, and it offers the two engine profiles as
    // one tap each, applied through the same pref setter the engine
    // card uses, so the prepared state is exactly the state that card
    // displays.
    private void buildReforgedWifiCard(LinearLayout root) {
        LinearLayout content = UiKit.card(root);
        UiKit.sectionHeader(content, R.drawable.ic_gzh_chip,
            getString(R.string.setup_card_reforged_wifi), true);
        UiKit.supporting(content, getString(R.string.setup_reforged_wifi_intro));
        String engine = getReforged60(this)
            ? getString(R.string.setup_reforged_wifi_engine60)
            : getString(R.string.setup_reforged_wifi_engine30);
        // The data identity is more than the engine: the same engine
        // over a game folder without the Community Patch reads a
        // different INI stream than over one with it, and the identity
        // check cannot tell the player which half differed. The card
        // can: the patch is a file in the game folder, and the folder
        // is the launcher's own.
        String patchState = getString(R.string.setup_reforged_wifi_patch_off);
        java.io.File[] folderFiles = new java.io.File(
            getSavedGamePath(this, GAME_ZERO_HOUR)).listFiles();
        if (folderFiles != null) {
            for (java.io.File f : folderFiles) {
                if (f.getName().toLowerCase(java.util.Locale.US)
                        .contains("communitypatch")) {
                    patchState = getString(R.string.setup_reforged_wifi_patch_on);
                    break;
                }
            }
        }
        UiKit.supporting(content, getString(R.string.setup_reforged_wifi_state,
            engine, patchState));
        UiKit.button(content, UiKit.BTN_TONAL, R.drawable.ic_gzh_chip,
            getString(R.string.setup_reforged_wifi_prepare30), () -> {
                setReforged60(this, false);
                content.post(() -> showTab(TAB_REFORGED));
            });
        UiKit.button(content, UiKit.BTN_TONAL, R.drawable.ic_gzh_chip,
            getString(R.string.setup_reforged_wifi_prepare60), () -> {
                setReforged60(this, true);
                content.post(() -> showTab(TAB_REFORGED));
            });
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
                // ship; the engine choice is on the Reforged page."""),
])

edit('android/app/src/main/java/com/generalsx/zerohour/GeneralsZHActivity.java', [
    ("""        final String[] engines = SetupActivity.engineLibraries(this);
        String engine = engines[0];
        if (SetupActivity.getSimHz(this) == SetupActivity.SIM_HZ_CROSSPLAY
                && new java.io.File(getApplicationInfo().nativeLibraryDir, "lib" + engines[1] + ".so").isFile()) {
            engine = engines[1];
        }""",
     """        // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.13) This
        // app ships ONLY the Reforged engines -- the host's libraries
        // were removed by the owner's order -- so the choice is ours
        // alone: the 60-steps engine when the Reforged page's switch
        // is on, the standard Reforged engine otherwise. Both
        // libraries always ship; there is no fallback to a library
        // that does not exist in this APK, and no sim_hz selection
        // (its card is gone with the engines it chose between).
        String engine = SetupActivity.getReforged60(this) ? "mainrf60" : "mainrf";"""),
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

# ---------------- v1.13: the bundled data is not a mod ----------------
# Phase 2 forces the bundled Reforged package enabled at every launcher
# start; these pairs lock its handles in the shell's own mod UI, so no
# screen presents it as an optional add-on: the Mods screen's switch
# for it is disabled, its delete and move paths refuse it, its place
# at the end of the order (its mount priority) cannot be moved across,
# and the Home page's Mods row does not count it. The state machinery
# itself (listMods/saveOrder/writeActiveList) is untouched.
edit('android/app/src/main/java/com/generalsx/zerohour/ModManagerActivity.java', [
    ("""        SwitchCompat toggle = new SwitchCompat(this);
        toggle.setChecked(mod.enabled);
        toggle.setContentDescription(mod.name);
        toggle.setEnabled(!busy);""",
     """        SwitchCompat toggle = new SwitchCompat(this);
        toggle.setChecked(mod.enabled);
        toggle.setContentDescription(mod.name);
        // Zero Hour Reforged (v1.13): the bundled Reforged package is core
        // app data, not a mod -- its switch is locked on.
        toggle.setEnabled(!busy
            && !ModManager.BUNDLED_DIR.equals(mod.dir.getName()));"""),
    ("""    private void confirmDelete(ModManager.Mod mod) {
        if (busy) {
            return;
        }""",
     """    private void confirmDelete(ModManager.Mod mod) {
        if (busy) {
            return;
        }
        // Zero Hour Reforged (v1.13): the bundled Reforged package is core
        // app data -- it cannot be deleted from this screen.
        if (ModManager.BUNDLED_DIR.equals(mod.dir.getName())) {
            return;
        }"""),
    ("""    private void moveToOtherGame(ModManager.Mod mod) {
        if (busy) {
            return;
        }""",
     """    private void moveToOtherGame(ModManager.Mod mod) {
        if (busy) {
            return;
        }
        // Zero Hour Reforged (v1.13): the bundled Reforged package is core
        // app data -- it cannot be moved to the other game's folder.
        if (ModManager.BUNDLED_DIR.equals(mod.dir.getName())) {
            return;
        }"""),
    ("""    private void move(int index, int delta) {
        int target = index + delta;
        if (busy || target < 0 || target >= mods.size()) {
            return;
        }""",
     """    private void move(int index, int delta) {
        int target = index + delta;
        if (busy || target < 0 || target >= mods.size()) {
            return;
        }
        // Zero Hour Reforged (v1.13): the bundled Reforged package is
        // pinned at the end of the order (its mount priority) -- neither
        // it nor anything across it moves.
        if (ModManager.BUNDLED_DIR.equals(mods.get(index).dir.getName())
                || ModManager.BUNDLED_DIR.equals(mods.get(target).dir.getName())) {
            return;
        }"""),
])

edit('android/app/src/main/java/com/generalsx/zerohour/SetupActivity.java', [
    ("""        java.util.List<ModManager.Mod> installedMods = ModManager.listMods(this);
        int modsOn = 0;
        for (ModManager.Mod mod : installedMods) {
            if (mod.enabled) {
                modsOn++;
            }
        }""",
     """        java.util.List<ModManager.Mod> installedMods = ModManager.listMods(this);
        // Zero Hour Reforged (v1.13): the bundled Reforged package is core
        // app data, not a mod -- it is not counted on the Mods row.
        installedMods.removeIf(mod -> ModManager.BUNDLED_DIR.equals(mod.dir.getName()));
        int modsOn = 0;
        for (ModManager.Mod mod : installedMods) {
            if (mod.enabled) {
                modsOn++;
            }
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
    ('setup_reforged60_help', "The engine is chosen when the game starts, so the change applies the next time you launch it. Save games and replays belong to the rate that made them: each engine refuses the other\\'s, cleanly. Network games with this engine run only against this same build. If large battles slow down, switch it off -- the standard Reforged engine is this app\\'s default."),
]
_RF60_STRINGS_AR = [
    ('setup_card_reforged60', 'محرك ريفورجيد'),
    ('setup_reforged60_title', 'محرك ريفورجيد — 60 خطوة بالثانية (تجريبي)'),
    ('setup_reforged60_desc', 'محاكاة ريفورجيد الأصلية بمعدل مضاعف: حركة أنعم واستجابة أسرع، مقابل شغل أثقل على المعالج.'),
    ('setup_reforged60_help', 'يُختار المحرك عند بدء اللعبة، فيسري التغيير عند تشغيلها في المرة القادمة. ملفات الحفظ والإعادات تخص المعدل الذي صنعها: كل محرك يرفض ملفات الآخر بشكل نظيف. مباريات الشبكة بهذا المحرك لا تجري إلا ضد هذه النسخة نفسها. إذا تراجعت السلاسة في المعارك الكبيرة، أوقف هذا الخيار — فمحرك ريفورجيد القياسي هو الافتراضي في هذا التطبيق.'),
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
    ('setup_reforged_home_row_desc', 'Our engines and WiFi play, on their own page'),
    ('setup_reforged_page_intro', 'This app runs only the Reforged engines, with the Reforged data built in -- there is nothing to switch on or off for the data. The engine choice is below. The original app and its online games live in the original app, not in this one.'),
]
_PAGE_STRINGS_AR = [
    ('nav_tab_reforged', 'ريفورجيد'),
    ('setup_card_reforged_page', 'ريفورجيد'),
    ('setup_reforged_home_row_desc', 'محركاتنا واللعب عبر الوايفاي، بصفحة لحالها'),
    ('setup_reforged_page_intro', 'هذا التطبيق يعمل بمحركات ريفورجيد فقط، وبيانات ريفورجيد مدمجة فيه — لا شيء يُشغَّل أو يُطفأ بخصوص البيانات. اختيار المحرك في الأسفل. التطبيق الأصلي ومبارياته عبر الأونلاين يعيشان في التطبيق الأصلي، لا في هذا.'),
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
    ('setup_reforged_wifi_intro', 'Two phones, one build: a WiFi match between our builds needs both phones on the same engine, over game folders with the same Community Patch state. The game compares both identities when the match starts and keeps comparing while it runs; a difference on either phone ends the match at the start.'),
    ('setup_reforged_wifi_state', 'This phone: engine %1$s · Community Patch %2$s'),
    ('setup_reforged_wifi_patch_on', 'installed'),
    ('setup_reforged_wifi_patch_off', 'missing'),
    ('setup_reforged_wifi_engine60', 'Reforged 60'),
    ('setup_reforged_wifi_engine30', 'Reforged 30'),
    ('setup_reforged_wifi_prepare30', 'Prepare WiFi play: Reforged 30'),
    ('setup_reforged_wifi_prepare60', 'Prepare WiFi play: Reforged 60'),
    ('setup_reforged_wifi_help', 'Press the same Prepare button on both phones, then compare the line above on both screens -- it must read the same before you start.'),
]
_WIFI_STRINGS_AR = [
    ('setup_card_reforged_wifi', 'اللعب عبر الوايفاي'),
    ('setup_reforged_wifi_intro', 'هاتفان وبناء واحد: مباراة وايفاي بين نسخنا تحتاج أن يعمل الهاتفان على المحرك نفسه، فوق مجلدَي لعبة بحالة باتش مجتمع واحدة. اللعبة تقارن هويتي الهاتفين عند بدء المباراة وتظل تقارن أثناءها؛ وأي اختلاف في أي هاتف ينهي المباراة من بدايتها.'),
    ('setup_reforged_wifi_state', 'هذا الهاتف: المحرك %1$s · باتش المجتمع %2$s'),
    ('setup_reforged_wifi_patch_on', 'موجود'),
    ('setup_reforged_wifi_patch_off', 'غير موجود'),
    ('setup_reforged_wifi_engine60', 'ريفورجيد 60'),
    ('setup_reforged_wifi_engine30', 'ريفورجيد 30'),
    ('setup_reforged_wifi_prepare30', 'جهّز للعب الوايفاي: ريفورجيد 30'),
    ('setup_reforged_wifi_prepare60', 'جهّز للعب الوايفاي: ريفورجيد 60'),
    ('setup_reforged_wifi_help', 'اضغط زر التجهيز نفسه على الهاتفين، ثم قارن السطر أعلاه على الشاشتين — لازم يقرأ الشيء نفسه قبل أن تبدأ.'),
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
