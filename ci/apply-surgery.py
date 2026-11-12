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
  1e the Reforged page (v1.9; entry moved in v1.11): our own launcher
     page, entered from a row on the Home page -- Material's
     BottomNavigationView accepts at most five items, and the sixth
     bottom-navigation item v1.9/v1.10 added threw at inflation and
     took the whole settings interface down with it (v1.10 device
     verdict). Their five nav items are untouched. The page carries
     the Reforged 60-steps engine switch (pref
     reforged_60_steps, default OFF -- the card that sat on the Graphics
     tab in v1.5-v1.8, moved here unchanged in substance) and the bundled
     Reforged mod switch (phase 2 supplies the state). Since v1.10 the
     engine card carries a second switch, for the enhanced standard
     engine (libmainrf.so -- the same patched tree at the standard rate,
     pref reforged_enhanced_30, default OFF); the two engine switches
     are alternatives and engaging one disengages the other, in the
     open. Their pages are untouched: the Simulation Rate card works
     again because libmain60.so really ships, GeneralsZHActivity keeps
     the host's own sim_hz engine selection with the engaged Reforged
     engines taking precedence (60-steps first, then the enhanced
     standard -- they are the player's explicit choices on our page),
     GeneralsOnlineSession's clientId keeps the host's own sim_hz
     keying with guards so our engines' states announce the id they
     actually compiled in, and
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
        ('(project.androidVersionCode as Integer) : 10402)', '(project.androidVersionCode as Integer) : 13)'),
        ("project.androidVersionName : '1.4.2')", "project.androidVersionName : '1.12')"),
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
# The page carries the engine switches and the mod switch, all Zero
# Hour only:
#  * the Reforged 60-steps engine (libmainrf60.so, from the patched tree):
#    its own pref (reforged_60_steps, default OFF) -- never a sim_hz
#    value, because GeneralsOnlineActivity's crossplay flow writes sim_hz
#    itself and must never enable this engine;
#  * the enhanced standard engine (libmainrf.so, the same patched tree
#    at the standard rate -- v1.10): its own pref again
#    (reforged_enhanced_30, default OFF). The two engine switches are
#    alternatives, never a stack: the card's listeners disengage the
#    other engine when one is engaged, so the page never displays a
#    state the engine selection would read differently;
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
    }

    // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.10) The enhanced
    // standard engine (libmainrf.so): the same patched tree as the
    // 60-steps engine, built at the standard rate -- the engine that
    // shipped as this build's standard library in v1.0-v1.8, under its
    // own name since v1.10 so the base tree's libmain.so stays the
    // host's own. Its own pref again, never sim_hz, for the same reason
    // as the 60-steps pref above. The two engine switches on our page
    // are alternatives (engaging one disengages the other -- see
    // buildReforgedEngineCard); GeneralsZHActivity.getLibraries() still
    // gives the 60-steps engine precedence if both prefs are ever on.
    static final String PREF_REFORGED_30 = "reforged_enhanced_30";

    static boolean getReforgedEnhanced30(android.content.Context ctx) {
        return ctx.getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .getBoolean(PREF_REFORGED_30, false);
    }

    static void setReforgedEnhanced30(android.content.Context ctx, boolean on) {
        ctx.getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit()
            .putBoolean(PREF_REFORGED_30, on)
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
        buildReforgedWifiCard(page);
    }

    // The Reforged engine card: the card that sat on the Graphics tab
    // in v1.5-v1.8, moved to our own page. Since v1.10 it carries BOTH
    // of our engines -- the 60-steps engine and the enhanced standard
    // engine -- each row gated on its library actually being in the
    // APK, and the card renders only when at least one of them is (the
    // page itself owns the Zero Hour gate now). The two switches are
    // alternatives, never a stack: engaging one disengages the other,
    // in the open -- the other switch visibly flips off and its pref is
    // cleared -- so the page can never display a state that
    // GeneralsZHActivity.getLibraries() would read differently. (That
    // selection still arbitrates 60-steps-first if hand-edited prefs
    // ever turn both on.) Each switch writes only its own pref.
    private void buildReforgedEngineCard(LinearLayout root) {
        boolean have60 = new java.io.File(getApplicationInfo().nativeLibraryDir, "libmainrf60.so").isFile();
        boolean have30 = new java.io.File(getApplicationInfo().nativeLibraryDir, "libmainrf.so").isFile();
        if (!have60 && !have30) {
            return;
        }
        LinearLayout content = UiKit.card(root);
        UiKit.sectionHeader(content, R.drawable.ic_gzh_chip,
            getString(R.string.setup_card_reforged60), true);
        com.google.android.material.materialswitch.MaterialSwitch sw60 = null;
        com.google.android.material.materialswitch.MaterialSwitch sw30 = null;
        if (have60) {
            sw60 = UiKit.switchRow(content,
                getString(R.string.setup_reforged60_title), getString(R.string.setup_reforged60_desc));
            sw60.setChecked(getReforged60(this));
            UiKit.helpText(content, getString(R.string.setup_reforged60_help));
        }
        if (have30) {
            sw30 = UiKit.switchRow(content,
                getString(R.string.setup_reforged30_title), getString(R.string.setup_reforged30_desc));
            sw30.setChecked(getReforgedEnhanced30(this));
            UiKit.helpText(content, getString(R.string.setup_reforged30_help));
        }
        final com.google.android.material.materialswitch.MaterialSwitch fsw60 = sw60;
        final com.google.android.material.materialswitch.MaterialSwitch fsw30 = sw30;
        if (fsw60 != null) {
            fsw60.setOnCheckedChangeListener((button, checked) -> {
                setReforged60(this, checked);
                if (checked && fsw30 != null && fsw30.isChecked()) {
                    fsw30.setChecked(false);
                }
            });
        }
        if (fsw30 != null) {
            fsw30.setOnCheckedChangeListener((button, checked) -> {
                setReforgedEnhanced30(this, checked);
                if (checked && fsw60 != null && fsw60.isChecked()) {
                    fsw60.setChecked(false);
                }
            });
        }
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
    ("""        UiKit.helpText(content, getString(R.string.setup_reforged_mod_help));
    }

    private int tabTitle(int tab) {""",
     """        UiKit.helpText(content, getString(R.string.setup_reforged_mod_help));
    }

    // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.12) The WiFi-play
    // card. A match between two of our builds stands or falls on identity:
    // the game compares the engine and data identities of both phones when
    // the match starts and keeps comparing while it runs, so any difference
    // -- the engine switch above, the mod state above -- ends the match at
    // the start. The card does two things only: it SAYS what this phone is
    // currently set to, in words the player can compare against the other
    // phone's screen, and it offers the two reference profiles as one tap
    // each, applied through the same pref setters and mod helpers the cards
    // above use, so the prepared state is exactly the state those cards
    // display. Nothing here touches the original pages or their games.
    private void buildReforgedWifiCard(LinearLayout root) {
        LinearLayout content = UiKit.card(root);
        UiKit.sectionHeader(content, R.drawable.ic_gzh_chip,
            getString(R.string.setup_card_reforged_wifi), true);
        UiKit.supporting(content, getString(R.string.setup_reforged_wifi_intro));
        String engine = getReforged60(this)
            ? getString(R.string.setup_reforged_wifi_engine60)
            : getReforgedEnhanced30(this)
                ? getString(R.string.setup_reforged_wifi_engine30)
                : getString(R.string.setup_reforged_wifi_engine_stock);
        Boolean mod = ModManager.bundledModEnabled(this);
        String modState = mod == null
            ? getString(R.string.setup_reforged_mod_absent)
            : mod ? getString(R.string.setup_reforged_wifi_mod_on)
                  : getString(R.string.setup_reforged_wifi_mod_off);
        // The data identity is more than the mod: the same mod over a game
        // folder without the Community Patch reads a different INI stream
        // than the same mod over one with it, and the identity check cannot
        // tell the player which half differed. The card can: the patch is a
        // file in the game folder, and the folder is the launcher's own.
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
            engine, modState, patchState));
        UiKit.button(content, UiKit.BTN_TONAL, R.drawable.ic_gzh_chip,
            getString(R.string.setup_reforged_wifi_prepare30), () -> {
                setReforgedEnhanced30(this, true);
                setReforged60(this, false);
                if (ModManager.bundledModEnabled(this) != null) {
                    ModManager.setBundledModEnabled(this, true);
                }
                content.post(() -> showTab(TAB_REFORGED));
            });
        UiKit.button(content, UiKit.BTN_TONAL, R.drawable.ic_gzh_chip,
            getString(R.string.setup_reforged_wifi_prepare60), () -> {
                setReforged60(this, true);
                setReforgedEnhanced30(this, false);
                if (ModManager.bundledModEnabled(this) != null) {
                    ModManager.setBundledModEnabled(this, true);
                }
                content.post(() -> showTab(TAB_REFORGED));
            });
        UiKit.helpText(content, getString(R.string.setup_reforged_wifi_help));
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
        // is actually in the APK. The enhanced standard engine (v1.10)
        // sits between the two under the same gates and yields to the
        // 60-steps branch. With both our switches off, the host's own
        // selection runs exactly as upstream wrote it.
        if (!SetupActivity.isGeneralsSelected(this)
                && SetupActivity.getReforged60(this)
                && new java.io.File(getApplicationInfo().nativeLibraryDir, "libmainrf60.so").isFile()) {
            engine = "mainrf60";
        } else if (SetupActivity.getSimHz(this) == SetupActivity.SIM_HZ_CROSSPLAY
                && new java.io.File(getApplicationInfo().nativeLibraryDir, "lib" + engines[1] + ".so").isFile()) {
            engine = engines[1];
        }"""),
    ("""            engine = "mainrf60";
        } else if (SetupActivity.getSimHz(this) == SetupActivity.SIM_HZ_CROSSPLAY""",
     """            engine = "mainrf60";
        } else if (!SetupActivity.isGeneralsSelected(this)
                && SetupActivity.getReforgedEnhanced30(this)
                && new java.io.File(getApplicationInfo().nativeLibraryDir, "libmainrf.so").isFile()) {
            // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.10)
            // The enhanced standard engine: our own build of the patched
            // tree at the standard rate. The same three gates as the
            // 60-steps branch above (Zero Hour only, the player's own
            // switch, the library really in the APK), and it yields to
            // that branch -- our page keeps the two switches mutually
            // exclusive, so this order only ever arbitrates hand-edited
            // prefs, never a state the page can display.
            engine = "mainrf";
        } else if (SetupActivity.getSimHz(this) == SetupActivity.SIM_HZ_CROSSPLAY"""),
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
# below stands, with guards in front of it for OUR engines: when the
# Reforged page's 60-steps engine (v1.9) or enhanced standard engine
# (v1.10) is engaged it takes precedence in getLibraries(), and its
# compiled-in GENERALS_ONLINE_CLIENT_ID is "gen_online_30hz" (neither is
# built with GENERALS_ONLINE_HIGH_FPS_SERVER; the workflow strings-
# checks both facts on every build). The guards return this class's own
# constant for exactly the states where those engines load, so the
# announcement never claims the host's 60 Hz for one of our engines --
# the enhanced-30 state needs its guard exactly as much as the 60-steps
# one: without it, a Simulation Rate selection of 60 would announce the
# host's 60 Hz id while our standard engine runs.
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
        // Two states are ours, not theirs: the Reforged page's engines
        // take precedence in getLibraries() when they are engaged,
        // under exactly the conditions mirrored here, and their
        // compiled-in id is CLIENT_ID (neither is a HIGH_FPS build) --
        // so they are announced as what they are, never as the host's
        // 60 Hz engine.
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
    ("""                && new java.io.File(ctx.getApplicationInfo().nativeLibraryDir,
                        "libmainrf60.so").isFile()) {
            return CLIENT_ID;
        }
        if (ctx != null
                && SetupActivity.getSimHz(ctx) == SetupActivity.SIM_HZ_CROSSPLAY""",
     """                && new java.io.File(ctx.getApplicationInfo().nativeLibraryDir,
                        "libmainrf60.so").isFile()) {
            return CLIENT_ID;
        }
        // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.10) The
        // enhanced standard engine's state is ours in the same way:
        // when it is engaged it is the engine getLibraries() loads (it
        // yields only to the 60-steps guard above, whose engine also
        // announces CLIENT_ID), under exactly the condition mirrored
        // here, and its compiled-in id is likewise CLIENT_ID. Without
        // this guard the sim_hz keying below would announce the host's
        // 60 Hz for our standard engine whenever the Simulation Rate
        // selection stands at 60.
        if (ctx != null
                && !SetupActivity.isGeneralsSelected(ctx)
                && SetupActivity.getReforgedEnhanced30(ctx)
                && new java.io.File(ctx.getApplicationInfo().nativeLibraryDir,
                        "libmainrf.so").isFile()) {
            return CLIENT_ID;
        }
        if (ctx != null
                && SetupActivity.getSimHz(ctx) == SetupActivity.SIM_HZ_CROSSPLAY"""),
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

# Enhanced standard engine strings in every locale (v1.10), inserted
# right after the 60-steps help line the loop above put in (the anchor
# string name exists in all locales by then). Same AAPT2 escaping law
# as above. The texts are honest in the 60-steps card's register: this
# engine is ours, it plays network games only against this same build,
# and the two engine switches are alternatives, never a stack.
_RF30_STRINGS_EN = [
    ('setup_reforged30_title', 'Reforged engine \u2014 standard rate, enhanced (experimental)'),
    ('setup_reforged30_desc', "This build\\'s own standard-rate engine, carrying our smoothness, performance and graphics work."),
    ('setup_reforged30_help', "The engine is chosen when the game starts, so the change applies the next time you launch it. This engine is ours, so online it plays only against this same build; for the original app\\'s online games, leave both engine switches on this page off and use the Simulation Rate card on the Graphics tab. Our two engine switches are alternatives: turning one on turns the other off."),
]
_RF30_STRINGS_AR = [
    ('setup_reforged30_title', 'محرك ريفورجيد — المعدل القياسي، محسَّن (تجريبي)'),
    ('setup_reforged30_desc', 'محرك هذه النسخة بالمعدل القياسي نفسه، حاملًا أعمال السلاسة والأداء والرسوميات الخاصة بنا.'),
    ('setup_reforged30_help', 'يُختار المحرك عند بدء اللعبة، فيسري التغيير عند تشغيلها في المرة القادمة. هذا المحرك محركنا، فلا يلعب عبر الأونلاين إلا ضد هذه النسخة نفسها؛ ولمباريات التطبيق الأصلي عبر الأونلاين أوقف مفتاحَي المحرك في هذه الصفحة واستخدم بطاقة معدل المحاكاة في تبويب الرسوميات. مفتاحا محركينا بديلان: تشغيل أحدهما يوقف الآخر.'),
]
for d in os.listdir(resdir):
    p = os.path.join(resdir, d, 'strings.xml')
    if not (d.startswith('values') and os.path.isfile(p)):
        continue
    s = open(p, encoding='utf-8').read()
    if 'name="setup_reforged30_title"' in s:
        continue
    entries = _RF30_STRINGS_AR if d == 'values-ar' else _RF30_STRINGS_EN
    block = ''.join(f'\n    <string name="{n}">{t}</string>' for n, t in entries)
    lines = s.split('\n')
    idx = next((i for i, ln in enumerate(lines) if 'name="setup_reforged60_help"' in ln), None)
    if idx is None:
        idx = next(i for i, ln in enumerate(lines) if '</resources>' in ln)
        lines.insert(idx, block.lstrip('\n'))
    else:
        lines.insert(idx + 1, block.lstrip('\n'))
    open(p, 'w', encoding='utf-8').write('\n'.join(lines))
    print('rf30 strings', os.path.join(d, 'strings.xml'))

# Reforged page strings in every locale (the tab label, the intro card,
# the mod card), inserted right after the nav_tab_help line -- the shell's
# own navigation family, so ours sits with its kin. No name here exists
# upstream (the proof battery censuses them against pristine per locale).
_PAGE_STRINGS_EN = [
    ('nav_tab_reforged', 'Reforged'),
    ('setup_card_reforged_page', 'Reforged'),
    ('setup_reforged_home_row_desc', 'Our engines and the Reforged mod, on their own page'),
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
    ('setup_reforged_home_row_desc', 'محركاتنا ومود ريفورجيد، بصفحة لحالها'),
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

# WiFi-play card strings in every locale (v1.12), same insertion point and
# discipline as the page strings above. No name here exists upstream.
_WIFI_STRINGS_EN = [
    ('setup_card_reforged_wifi', 'WiFi Play'),
    ('setup_reforged_wifi_intro', 'Two phones, one build: a WiFi match between our builds needs both phones set the same on this page -- the same engine, the same mod state. The game compares both identities when the match starts and keeps comparing while it runs; a difference on either phone ends the match at the start.'),
    ('setup_reforged_wifi_state', 'This phone: engine %1$s · Reforged mod %2$s · Community Patch %3$s'),
    ('setup_reforged_wifi_patch_on', 'installed'),
    ('setup_reforged_wifi_patch_off', 'missing'),
    ('setup_reforged_wifi_engine60', 'Reforged 60'),
    ('setup_reforged_wifi_engine30', 'Reforged 30 (enhanced)'),
    ('setup_reforged_wifi_engine_stock', 'Original'),
    ('setup_reforged_wifi_mod_on', 'on'),
    ('setup_reforged_wifi_mod_off', 'off'),
    ('setup_reforged_wifi_prepare30', 'Prepare WiFi play: Reforged 30 + mod'),
    ('setup_reforged_wifi_prepare60', 'Prepare WiFi play: Reforged 60 + mod'),
    ('setup_reforged_wifi_help', 'Press the same Prepare button on both phones, then compare the line above on both screens -- it must read the same before you start. Games on the original engines are set up on the original pages; this card is only for matches between our builds.'),
]
_WIFI_STRINGS_AR = [
    ('setup_card_reforged_wifi', 'اللعب عبر الوايفاي'),
    ('setup_reforged_wifi_intro', 'هاتفان وبناء واحد: مباراة وايفاي بين نسخنا تحتاج أن يضبط الهاتفان الشيء نفسه من هذه الصفحة — نفس المحرك ونفس حالة المود. اللعبة تقارن هويتي الهاتفين عند بدء المباراة وتظل تقارن أثناءها؛ وأي اختلاف في أي هاتف ينهي المباراة من بدايتها.'),
    ('setup_reforged_wifi_state', 'هذا الهاتف: المحرك %1$s · مود ريفورجيد %2$s · باتش المجتمع %3$s'),
    ('setup_reforged_wifi_patch_on', 'موجود'),
    ('setup_reforged_wifi_patch_off', 'غير موجود'),
    ('setup_reforged_wifi_engine60', 'ريفورجيد 60'),
    ('setup_reforged_wifi_engine30', 'ريفورجيد 30 (المحسّن)'),
    ('setup_reforged_wifi_engine_stock', 'الأصلي'),
    ('setup_reforged_wifi_mod_on', 'شغال'),
    ('setup_reforged_wifi_mod_off', 'مطفي'),
    ('setup_reforged_wifi_prepare30', 'جهّز للعب الوايفاي: ريفورجيد 30 + المود'),
    ('setup_reforged_wifi_prepare60', 'جهّز للعب الوايفاي: ريفورجيد 60 + المود'),
    ('setup_reforged_wifi_help', 'اضغط زر التجهيز نفسه على الهاتفين، ثم قارن السطر أعلاه على الشاشتين — لازم يقرأ الشيء نفسه قبل أن تبدأ. مباريات المحركات الأصلية تُجهّز من الصفحات الأصلية؛ هذه البطاقة لمباريات بين نسخنا فقط.'),
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
