#!/usr/bin/env python3
"""Phase 3 (CI, v1.15): the Stage C3 tests page.

Everything here serves ONE addition: a tests page of its own in the
launcher (owner ruling 2026-11-14: C3 ships inside v1.15 as tests on a
separate page, the shipped engines untouched). Concretely:

  * SetupActivity gains a TAB_TESTS page (same showTab() machinery and
    the same Home entry-row pattern as the Reforged page -- NOT a
    bottom-navigation item; the bar is full at five, see phase 1e).
    The page explains the tests, runs them, and shows the verdict
    lines plus the captured offscreen frame.
  * FrameCheckActivity (new file) is the C2 route-B activity: an
    SDLActivity subclass in its own ":framecheck" process whose only
    customisation is the library list -- it loads libmainrfx.so, the
    Reforged engine's frame selfcheck + C3 offscreen phase, whose
    SDL_main writes frame-result.txt (and frame-capture.bmp) into the
    app's external files directory. Process isolation keeps the
    payload's statically linked SDL away from the game's, exactly as
    proven on device in C2.
  * The tests page writes zh-gamedata-path.txt (the installed game
    folder) into the same directory before launching, so the
    payload's content probe can report the data side.
  * package-android-zh.sh learns the GX_REFORGEDX_LIB knob, mirroring
    GX_REFORGED_LIB / GX_REFORGED60_LIB: when set, the payload is
    staged into jniLibs as libmainrfx.so.
  * Strings: nav_tab_tests + the setup_tests_* set go into every
    locale file that carries nav_tab_reforged (Arabic translated,
    the rest English -- Android falls back to values/ where a locale
    lacks a string, and every referenced name exists in values/).

The shipped engines' code paths are not edited by this script at
all: the only SetupActivity hooks are the new page and one
maybeRefreshTestsPage() call in onResume that no-ops unless a test
run is in flight.

Layout: REFORGED_SRC (env) points at the MYSOREZ checkout; default is
the parent of this overlay, matching apply-surgery.py/apply-phase2.py.
Run AFTER apply-surgery.py (mode=full) and apply-phase2.py.
"""

import glob
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
OVERLAY = os.path.dirname(_HERE)
SRC = os.environ.get('REFORGED_SRC') or os.path.dirname(OVERLAY)

APP = os.path.join(SRC, 'android', 'app', 'src', 'main')
JAVA_DIR = os.path.join(APP, 'java', 'com', 'generalsx', 'zerohour')
SETUP = os.path.join(JAVA_DIR, 'SetupActivity.java')
MANIFEST = os.path.join(APP, 'AndroidManifest.xml')
PACKAGE_SH = os.path.join(SRC, 'scripts', 'build', 'android',
                          'package-android-zh.sh')
RES = os.path.join(APP, 'res')


def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        if s.count(old) != 1:
            sys.exit(f'phase3: anchor not unique/found in {path}: {old[:70]!r} '
                     f'(count={s.count(old)})')
        s = s.replace(old, new, 1)
    open(path, 'w', encoding='utf-8').write(s)
    print('edited', os.path.relpath(path, SRC))


print('phase3 target tree:', SRC)

# ---------------- 1) FrameCheckActivity.java (new file) ----------------
FRAMECHECK_JAVA = '''package com.generalsx.zerohour;

import org.libsdl.apprfx.SDLActivity;

import android.os.Bundle;

/**
 * Stage C3 tests (v1.15): the activity that runs the Reforged
 * engine's frame selfcheck + offscreen phase.
 *
 * The payload is packaged as a shared library, libmainrfx.so, whose
 * SDL_main is the selfcheck entry from the frame-entry patch: it
 * redirects its output into frame-result.txt in this app's external
 * files directory, runs the C2 renderer checks, then the C3
 * offscreen phase (a windowless GPU device rendering a bounded run
 * of frames into its own target, the final frame captured to
 * frame-capture.bmp), and appends its return code to the file,
 * because an activity process's stdout is logcat, which the launcher
 * cannot read. SetupActivity's tests page launches this activity and
 * reads the file when it comes back to the foreground.
 *
 * The only customisation SDLActivity needs is the library list:
 * loading just the payload library makes getMainSharedObject()
 * resolve to it (SDLActivity's default takes the last listed
 * library), and its JNI_OnLoad -- from the engine's own statically
 * linked SDL 3.4.16, the same version as this Java layer -- registers
 * the SDLActivity natives. No separate SDL3 library is loaded: the
 * payload carries its SDL inside itself.
 *
 * This activity runs in its own process (see the manifest's
 * android:process=":framecheck"), so the payload's SDL never shares
 * a process with the game's -- the two-SDL hazard the stage-C plan
 * flags, avoided by isolation, exactly as proven on device in C2
 * (2026-11-12). It never touches the shipped engines.
 */
public class FrameCheckActivity extends SDLActivity {

    @Override
    protected String[] getLibraries() {
        return new String[] { "mainrfx" };
    }

    // v1.15.2 stage markers: the Java side of the tests process
    // leaves a trail in frame-result.txt BEFORE any native code
    // runs, so a death before SDL_main (the v1.15 failure: native
    // crash ~1 s in, no result file at all) is bisectable from the
    // log alone. The payload's entry truncates the file when
    // SDL_main starts, so surviving markers mean main never ran.
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        markJavaStage("oncreate-enter");
        super.onCreate(savedInstanceState);
        markJavaStage("oncreate-done");
    }

    @Override
    public void loadLibraries() {
        markJavaStage("load-enter");
        super.loadLibraries();
        markJavaStage("load-done");
    }

    private void markJavaStage(String stage) {
        try {
            java.io.File dir = getExternalFilesDir(null);
            if (dir == null) return;
            java.io.FileWriter w = new java.io.FileWriter(
                new java.io.File(dir, "frame-result.txt"), true);
            w.write("[javastage] " + stage + "\\n");
            w.close();
        } catch (Exception ignored) {}
    }
}
'''
fc_path = os.path.join(JAVA_DIR, 'FrameCheckActivity.java')
if os.path.exists(fc_path):
    sys.exit('phase3: FrameCheckActivity.java already exists -- refusing to overwrite')
open(fc_path, 'w', encoding='utf-8').write(FRAMECHECK_JAVA)
print('wrote', os.path.relpath(fc_path, SRC))

# ---------------- 1b) RfxGameActivity.java (new file) ----------------
RFXGAME_JAVA = '''package com.generalsx.zerohour;

import org.libsdl.apprfx.SDLActivity;

import android.os.Bundle;
import android.system.Os;

/**
 * Stage C4 tests (v1.18): the activity that runs the Reforged
 * engine itself as a game.
 *
 * The payload is packaged as libmainrfxgame.so: the full Reforged
 * game (PosixMain's SDL_main) built as a shared library by the C4
 * CMake patch. This activity hands it the two things a desktop
 * launch would: the install root (the game folder the owner picked
 * in this launcher, passed as SDL_main's first argument, -root --
 * PosixMain chdir()s there itself) and a writable user-data
 * directory (ZH_USER_DATA_DIR, read once by the engine's early
 * options; an isolated rfx-user folder under this app's external
 * files, so the game's own saves/settings never mix with the
 * shipped engines' -- sharing those is Stage C6 parity work).
 *
 * It runs in its own process (the manifest's :rfxgame), under the
 * same isolated SDL 3.4.16 Java layer as the C3 payload -- never
 * the host shell's 3.4.2 layer, and never in a process with the
 * shipped engines. Touch control proper is Stage C5; this slice
 * proves the engine opens its window, reaches its main menu and
 * shell map, starts a skirmish, and quits cleanly.
 */
public class RfxGameActivity extends SDLActivity {

    @Override
    protected String[] getLibraries() {
        return new String[] { "mainrfxgame" };
    }

    @Override
    protected String[] getArguments() {
        String root = SetupActivity.getSavedGamePath(this);
        java.io.File odir = overlayDir();
        if (odir != null
                && new java.io.File(odir, ".rfx-overlay-version").isFile()) {
            return new String[] { "-fullscreen", "-root", root == null ? "" : root,
                "-overlay", odir.getAbsolutePath() };
        }
        return new String[] { "-fullscreen", "-root", root == null ? "" : root };
    }

    private static final String OVERLAY_REV = "1";

    private java.io.File overlayDir() {
        java.io.File base = getExternalFilesDir(null);
        return base == null ? null
            : new java.io.File(base, "rfx-overlay");
    }

    // Stage C4 (v1.22): the fork's own data -- its *Reforged.ini
    // set, cursors, scripts, window files and HUD textures --
    // ships upstream as an overlay directory searched before the
    // install root (PosixMain -overlay, the fork's P1 decision
    // 9). It rides in the APK as assets/rfx-overlay.zip, staged
    // in CI by the fork's own Tools/stage-overlay.sh, and is
    // extracted here, once per OVERLAY_REV, before the engine
    // starts. Failure leaves the marker absent, getArguments()
    // then omits -overlay, and the launch degrades to the
    // pre-overlay behaviour -- never worse.
    private void ensureOverlay() {
        try {
            java.io.File dir = overlayDir();
            if (dir == null) return;
            java.io.File marker =
                new java.io.File(dir, ".rfx-overlay-version");
            if (marker.isFile()) {
                java.io.BufferedReader r = new java.io.BufferedReader(
                    new java.io.FileReader(marker));
                String v = r.readLine();
                r.close();
                if (OVERLAY_REV.equals(v)) {
                    markGameStage("overlay-ready");
                    return;
                }
            }
            markGameStage("overlay-extract-begin");
            java.util.zip.ZipInputStream zin =
                new java.util.zip.ZipInputStream(
                    getAssets().open("rfx-overlay.zip"));
            byte[] buf = new byte[65536];
            java.util.zip.ZipEntry e;
            while ((e = zin.getNextEntry()) != null) {
                String name = e.getName();
                if (name.contains("..")) continue;
                java.io.File out = new java.io.File(dir, name);
                if (e.isDirectory()) {
                    out.mkdirs();
                    continue;
                }
                java.io.File parent = out.getParentFile();
                if (parent != null) parent.mkdirs();
                java.io.FileOutputStream fos =
                    new java.io.FileOutputStream(out);
                int n;
                while ((n = zin.read(buf)) > 0) fos.write(buf, 0, n);
                fos.close();
            }
            zin.close();
            java.io.FileWriter w = new java.io.FileWriter(marker);
            w.write(OVERLAY_REV);
            w.close();
            markGameStage("overlay-ready");
        } catch (Exception ex) {
            markGameStage("overlay-failed");
        }
    }

    // The engine reads ZH_USER_DATA_DIR once, before SDL_main runs;
    // the variable must exist before loadLibraries() inside
    // super.onCreate, so it is set first thing here.
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        markGameStage("oncreate-enter");
        try {
            java.io.File userDir =
                new java.io.File(getExternalFilesDir(null), "rfx-user");
            userDir.mkdirs();
            Os.setenv("ZH_USER_DATA_DIR",
                userDir.getAbsolutePath(), true);
        } catch (Exception ignored) {}
        // v1.26: ZH_RENDER_SCALE is NOT set. The scaled path renders the
        // shell broken below 100 (v1.25 device finding); rendering stays
        // clamped to full size until the viewport-scaling fix passes its
        // device gate, when this block and the setup slider return.
        // C4 diagnostics (v1.19): the engine's debug channel also
        // writes to stderr, which Android discards for app processes;
        // redirect fd 2 to a file in the external files dir before
        // the engine starts, so the shared test log can carry it.
        try {
            java.io.File errFile =
                new java.io.File(getExternalFilesDir(null), "rfxgame-stderr.txt");
            java.io.FileOutputStream errOut =
                new java.io.FileOutputStream(errFile, false);
            Os.dup2(errOut.getFD(), 2);
            markGameStage("stderr-redirected");
        } catch (Exception e) {
            markGameStage("stderr-redirect-failed");
        }
        ensureOverlay();
        super.onCreate(savedInstanceState);
        markGameStage("oncreate-done");
        // (v1.24) Keep the screen on while the game runs.
        // (v1.24.1) The status and navigation bars are hidden by SDL
        // itself: the engine is launched with -fullscreen (see
        // getArguments), and SDL's fullscreen window is what makes
        // Android hide the bars. The legacy systemUiVisibility flags
        // this activity used in v1.24 are ignored on Android 16 --
        // device-proven, the bars stayed -- so they are gone.
        try {
            getWindow().addFlags(
                android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        } catch (Exception ignored) {}
    }

    @Override
    public void loadLibraries() {
        markGameStage("load-enter");
        super.loadLibraries();
        markGameStage("load-done");
    }

    private void markGameStage(String stage) {
        try {
            java.io.File dir = getExternalFilesDir(null);
            if (dir == null) return;
            java.io.FileWriter w = new java.io.FileWriter(
                new java.io.File(dir, "rfxgame-stage.txt"), true);
            w.write("[javastage] " + stage + "\\n");
            w.close();
        } catch (Exception ignored) {}
    }
}
'''
rg_path = os.path.join(JAVA_DIR, 'RfxGameActivity.java')
if os.path.exists(rg_path):
    sys.exit('phase3: RfxGameActivity.java already exists -- refusing to overwrite')
open(rg_path, 'w', encoding='utf-8').write(RFXGAME_JAVA)
print('wrote', os.path.relpath(rg_path, SRC))

# ---------------- 2) Manifest: register the activity ----------------
edit(MANIFEST, [(
    '    </application>',
    '''        <activity
            android:name=".FrameCheckActivity"
            android:exported="false"
            android:process=":framecheck"
            android:configChanges="orientation|keyboardHidden|keyboard|navigation|screenSize|screenLayout|smallestScreenSize|density|layoutDirection|locale|fontScale|uiMode"
            android:theme="@android:style/Theme.NoTitleBar.Fullscreen" />
        <activity
            android:name=".RfxGameActivity"
            android:exported="false"
            android:screenOrientation="landscape"
            android:process=":rfxgame"
            android:configChanges="orientation|keyboardHidden|keyboard|navigation|screenSize|screenLayout|smallestScreenSize|density|layoutDirection|locale|fontScale|uiMode"
            android:theme="@android:style/Theme.NoTitleBar.Fullscreen" />
    </application>''',
)])

# ---------------- 3) SetupActivity: the tests page ----------------
edit(SETUP, [
    # 3a) the tab id, right after the Reforged page's
    ('''    private static final int TAB_REFORGED = 6;''',
     '''    private static final int TAB_REFORGED = 6;
    // GeneralsX @feature Zero Hour Reforged 14/11/2026 (v1.15) The Stage C3
    // tests page. Same arrangement as the Reforged page: a showTab() page
    // id entered from a Home row, never a bottom-navigation item.
    private static final int TAB_TESTS = 7;'''),
    # 3b) its title
    ('''            case TAB_REFORGED:  return R.string.nav_tab_reforged;''',
     '''            case TAB_REFORGED:  return R.string.nav_tab_reforged;
            case TAB_TESTS:      return R.string.nav_tab_tests;'''),
    # 3c) its showTab() case
    ('''            case TAB_REFORGED:
                buildReforgedPage(page);
                break;''',
     '''            case TAB_REFORGED:
                buildReforgedPage(page);
                break;
            case TAB_TESTS:
                buildTestsPage(page);
                break;'''),
    # 3d) the Home entry row, mirroring the Reforged page's row
    ('''        LinearLayout reforgedEntry = UiKit.card(page);
        UiKit.listRow(reforgedEntry, R.drawable.ic_gzh_chip,
            getString(R.string.nav_tab_reforged),
            getString(R.string.setup_reforged_home_row_desc),
            () -> showTab(TAB_REFORGED));''',
     '''        LinearLayout reforgedEntry = UiKit.card(page);
        UiKit.listRow(reforgedEntry, R.drawable.ic_gzh_chip,
            getString(R.string.nav_tab_reforged),
            getString(R.string.setup_reforged_home_row_desc),
            () -> showTab(TAB_REFORGED));

        // GeneralsX @feature Zero Hour Reforged 14/11/2026 (v1.15) The entry
        // to the Stage C3 tests page, next to the Reforged page's row.
        LinearLayout testsEntry = UiKit.card(page);
        UiKit.listRow(testsEntry, R.drawable.ic_gzh_chip,
            getString(R.string.nav_tab_tests),
            getString(R.string.setup_tests_home_row_desc),
            () -> showTab(TAB_TESTS));'''),
    # 3e) onResume: pick up a finished test run
    ('''        // Once per process, not on every return to this screen.''',
     '''        maybeRefreshTestsPage();
        // Once per process, not on every return to this screen.'''),
    # 3f) the page builder + run/refresh helpers, before tabTitle()
    ('''    private int tabTitle(int tab) {''',
     '''    // GeneralsX @feature Zero Hour Reforged 14/11/2026 (v1.15) Stage C3
    // tests page. Runs libmainrfx.so (the Reforged engine's selfcheck +
    // offscreen first-frame phase) in its own process via
    // FrameCheckActivity and renders the verdict file it leaves behind.
    // The shipped engines are never loaded by any of this.
    private static final String PREF_RFX_TESTS_RUNNING = "rfx_tests_running";
    private static final String PREF_RFX_TESTS_STARTED_AT = "rfx_tests_started_at";
    private static final String RFX_LOG_FILE = "test-log.txt";
    private String mRfxLogShown;
    private static final String RFX_RESULT_FILE = "frame-result.txt";
    private static final String RFX_CAPTURE_FILE = "frame-capture.bmp";
    private static final String RFX_GAMEDATA_MARKER = "zh-gamedata-path.txt";

    private void onLaunchRfxGame() {
        startActivity(new android.content.Intent(this, RfxGameActivity.class));
    }

    private void onRunRfxTests() {
        java.io.File dir = getExternalFilesDir(null);
        if (dir == null) {
            return;
        }
        // The payload's content probe reads the game folder path from
        // this marker, in the same external files directory its result
        // file lands in.
        try {
            java.io.FileOutputStream out = new java.io.FileOutputStream(
                new java.io.File(dir, RFX_GAMEDATA_MARKER));
            String gamePath = getSavedGamePath(this);
            out.write((gamePath == null ? "" : gamePath).getBytes("UTF-8"));
            out.close();
        } catch (Exception ignored) {}
        // No stale result may pose as this run's.
        new java.io.File(dir, RFX_RESULT_FILE).delete();
        new java.io.File(dir, RFX_CAPTURE_FILE).delete();
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit()
            .putBoolean(PREF_RFX_TESTS_RUNNING, true)
            .putLong(PREF_RFX_TESTS_STARTED_AT,
                System.currentTimeMillis()).apply();
        mRfxLogShown = null;
        startActivity(new android.content.Intent(this, FrameCheckActivity.class));
    }

    private void maybeRefreshTestsPage() {
        android.content.SharedPreferences prefs =
            getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        if (!prefs.getBoolean(PREF_RFX_TESTS_RUNNING, false)) {
            return;
        }
        java.io.File dir = getExternalFilesDir(null);
        if (dir == null) {
            return;
        }
        java.io.File result = new java.io.File(dir, RFX_RESULT_FILE);
        if (result.isFile() && result.length() > 0) {
            prefs.edit().putBoolean(PREF_RFX_TESTS_RUNNING, false)
                .apply();
            if (currentTab == TAB_TESTS && contentHost != null) {
                showTab(TAB_TESTS);
            }
            return;
        }
        // No result file: if the system recorded the framecheck
        // process exiting after this run started, the run is over --
        // it died without writing. Clear the flag so the page can
        // say so (and point at the logs) instead of showing
        // "running" forever, which is what v1.15 did.
        long startedAt = prefs.getLong(PREF_RFX_TESTS_STARTED_AT, 0);
        if (startedAt > 0 && rfxFramecheckExitAfter(startedAt) != null) {
            prefs.edit().putBoolean(PREF_RFX_TESTS_RUNNING, false)
                .apply();
            if (currentTab == TAB_TESTS && contentHost != null) {
                showTab(TAB_TESTS);
            }
        }
    }

    private void buildTestsPage(LinearLayout page) {
        LinearLayout intro = UiKit.card(page);
        UiKit.sectionHeader(intro, R.drawable.ic_gzh_chip,
            getString(R.string.setup_card_tests_page), true);
        UiKit.supporting(intro, getString(R.string.setup_tests_intro));

        java.io.File dir = getExternalFilesDir(null);
        java.io.File result = dir == null ? null
            : new java.io.File(dir, RFX_RESULT_FILE);
        boolean haveResult = result != null && result.isFile()
            && result.length() > 0;
        boolean running = getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .getBoolean(PREF_RFX_TESTS_RUNNING, false);
        long rfxStartedAt = getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .getLong(PREF_RFX_TESTS_STARTED_AT, 0);
        boolean died = !running && !haveResult && rfxStartedAt > 0
            && rfxFramecheckExitAfter(rfxStartedAt) != null;

        LinearLayout run = UiKit.card(page);
        UiKit.supporting(run, getString(died
            ? R.string.setup_tests_died
            : running ? R.string.setup_tests_running
            : haveResult ? R.string.setup_tests_done
                         : R.string.setup_tests_no_results));
        UiKit.button(run, UiKit.BTN_PRIMARY, R.drawable.ic_gzh_chip,
            getString(R.string.setup_tests_run), this::onRunRfxTests);

        // GeneralsX @feature Zero Hour Reforged 19/11/2026 (v1.18) Stage C4:
        // the Reforged engine itself as a playable window, launched from
        // the same tests page, in its own process (RfxGameActivity).
        LinearLayout gameCard = UiKit.card(page);
        UiKit.sectionHeader(gameCard, R.drawable.ic_gzh_chip,
            getString(R.string.setup_tests_game_title), true);
        UiKit.supporting(gameCard, getString(R.string.setup_tests_game_desc));
        UiKit.button(gameCard, UiKit.BTN_PRIMARY, R.drawable.ic_gzh_chip,
            getString(R.string.setup_tests_game_launch), this::onLaunchRfxGame);

        if (haveResult) {
            LinearLayout results = UiKit.card(page);
            UiKit.sectionHeader(results, R.drawable.ic_gzh_chip,
                getString(R.string.setup_tests_results_title), true);
            android.widget.TextView tv = new android.widget.TextView(this);
            tv.setText(readTextFileQuietly(result));
            tv.setTextSize(11);
            tv.setTypeface(android.graphics.Typeface.MONOSPACE);
            tv.setTextIsSelectable(true);
            results.addView(tv);
            java.io.File capture = new java.io.File(dir, RFX_CAPTURE_FILE);
            if (capture.isFile() && capture.length() > 0) {
                UiKit.supporting(results,
                    getString(R.string.setup_tests_capture_title));
                android.graphics.Bitmap bmp =
                    android.graphics.BitmapFactory.decodeFile(
                        capture.getAbsolutePath());
                if (bmp != null) {
                    android.widget.ImageView iv =
                        new android.widget.ImageView(this);
                    iv.setImageBitmap(bmp);
                    iv.setAdjustViewBounds(true);
                    results.addView(iv);
                }
            }
        }

        // The dedicated logs card (v1.15.1, the owner's request):
        // one place that shows WHY a run ended -- the result file
        // plus the system's own exit record for the test process --
        // and shares it in one tap.
        LinearLayout logs = UiKit.card(page);
        UiKit.sectionHeader(logs, R.drawable.ic_gzh_chip,
            getString(R.string.setup_tests_logs_title), true);
        UiKit.supporting(logs, getString(R.string.setup_tests_logs_desc));
        UiKit.button(logs, UiKit.BTN_TONAL, R.drawable.ic_gzh_chip,
            getString(R.string.setup_tests_logs_show), this::onShowRfxLogs);
        UiKit.button(logs, UiKit.BTN_OUTLINE, R.drawable.ic_gzh_chip,
            getString(R.string.setup_tests_logs_share),
            this::onShareRfxLog);
        UiKit.button(logs, UiKit.BTN_OUTLINE, R.drawable.ic_gzh_chip,
            getString(R.string.setup_tests_logs_copy), this::onCopyRfxLog);
        if (mRfxLogShown != null) {
            android.widget.TextView lv = new android.widget.TextView(this);
            lv.setText(mRfxLogShown);
            lv.setTextSize(11);
            lv.setTypeface(android.graphics.Typeface.MONOSPACE);
            lv.setTextIsSelectable(true);
            logs.addView(lv);
        }
    }

    // The system's own record of how the :framecheck process last
    // exited at or after the given time -- the difference between
    // "still running" and "the system closed it", straight from
    // ActivityManager (API 30+; null on older systems).
    private android.app.ApplicationExitInfo rfxFramecheckExitAfter(
            long startedAt) {
        if (android.os.Build.VERSION.SDK_INT < 30) {
            return null;
        }
        try {
            android.app.ActivityManager am =
                (android.app.ActivityManager)
                    getSystemService(ACTIVITY_SERVICE);
            java.util.List<android.app.ApplicationExitInfo> exits =
                am.getHistoricalProcessExitReasons(
                    getPackageName(), 0, 10);
            for (android.app.ApplicationExitInfo e : exits) {
                if (e.getProcessName() != null
                        && e.getProcessName().endsWith(":framecheck")
                        && e.getTimestamp() >= startedAt) {
                    return e;
                }
            }
        } catch (Exception ignored) {}
        return null;
    }

    private static String rfxExitReasonName(int reason) {
        switch (reason) {
            case 1: return "EXIT_SELF";
            case 2: return "SIGNALED";
            case 3: return "LOW_MEMORY";
            case 4: return "CRASH";
            case 5: return "CRASH_NATIVE";
            case 6: return "ANR";
            case 7: return "INITIALIZATION_FAILURE";
            case 9: return "EXCESSIVE_RESOURCE_USAGE";
            case 10: return "USER_REQUESTED";
            case 11: return "USER_STOPPED";
            default: return "REASON_" + reason;
        }
    }

    private static String rfxTime(long ms) {
        return new java.text.SimpleDateFormat("yyyy/MM/dd HH:mm:ss",
            java.util.Locale.US).format(new java.util.Date(ms));
    }

    private String buildRfxTestLog() {
        StringBuilder sb = new StringBuilder();
        sb.append("Zero Hour Reforged -- test log\\n");
        try {
            android.content.pm.PackageInfo pi = getPackageManager()
                .getPackageInfo(getPackageName(), 0);
            sb.append("app: ").append(pi.versionName).append(" (")
              .append(pi.getLongVersionCode()).append(")\\n");
        } catch (Exception ignored) {}
        sb.append("device: ").append(android.os.Build.MANUFACTURER)
          .append(' ').append(android.os.Build.MODEL)
          .append(", Android ").append(android.os.Build.VERSION.RELEASE)
          .append(" (SDK ").append(android.os.Build.VERSION.SDK_INT)
          .append(")\\n");
        sb.append("now: ").append(rfxTime(System.currentTimeMillis()))
          .append("\\n");
        android.content.SharedPreferences prefs =
            getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        long startedAt = prefs.getLong(PREF_RFX_TESTS_STARTED_AT, 0);
        sb.append("run state: running=")
          .append(prefs.getBoolean(PREF_RFX_TESTS_RUNNING, false))
          .append(", started=")
          .append(startedAt > 0 ? rfxTime(startedAt) : "-").append("\\n");
        java.io.File dir = getExternalFilesDir(null);
        if (dir == null) {
            sb.append("external files dir: unavailable\\n");
            return sb.toString();
        }
        java.io.File result = new java.io.File(dir, RFX_RESULT_FILE);
        if (result.isFile()) {
            sb.append("frame-result.txt: ").append(result.length())
              .append(" bytes, modified ")
              .append(rfxTime(result.lastModified())).append("\\n");
            sb.append("---- frame-result.txt ----\\n");
            sb.append(readTextFileQuietly(result));
            sb.append("\\n---- end frame-result.txt ----\\n");
        } else {
            sb.append("frame-result.txt: MISSING\\n");
        }
        java.io.File capture = new java.io.File(dir, RFX_CAPTURE_FILE);
        sb.append("frame-capture.bmp: ");
        if (capture.isFile()) {
            sb.append(capture.length()).append(" bytes, modified ")
              .append(rfxTime(capture.lastModified())).append("\\n");
        } else {
            sb.append("MISSING\\n");
        }
        sb.append("---- process exits (system record) ----\\n");
        if (android.os.Build.VERSION.SDK_INT >= 30) {
            try {
                android.app.ActivityManager am =
                    (android.app.ActivityManager)
                        getSystemService(ACTIVITY_SERVICE);
                java.util.List<android.app.ApplicationExitInfo> exits =
                    am.getHistoricalProcessExitReasons(
                        getPackageName(), 0, 10);
                if (exits.isEmpty()) {
                    sb.append("(none recorded)\\n");
                }
                for (android.app.ApplicationExitInfo e : exits) {
                    sb.append(rfxTime(e.getTimestamp())).append(' ')
                      .append(e.getProcessName()).append(' ')
                      .append(rfxExitReasonName(e.getReason()));
                    if (e.getDescription() != null) {
                        sb.append(" -- ").append(e.getDescription());
                    }
                    sb.append("\\n");
                }
                int traces = 0;
                for (android.app.ApplicationExitInfo e : exits) {
                    if (traces >= 2) break;
                    if (!e.getProcessName().endsWith(":framecheck")) {
                        continue;
                    }
                    try {
                        java.io.InputStream tin = e.getTraceInputStream();
                        if (tin == null) continue;
                        java.io.ByteArrayOutputStream bos =
                            new java.io.ByteArrayOutputStream();
                        byte[] buf = new byte[4096];
                        int total = 0;
                        int n;
                        while (total < 8192
                                && (n = tin.read(buf)) > 0) {
                            bos.write(buf, 0, n);
                            total += n;
                        }
                        tin.close();
                        sb.append("---- tombstone for ")
                          .append(rfxTime(e.getTimestamp()))
                          .append(" ----\\n");
                        sb.append(bos.toString("UTF-8")).append("\\n");
                        traces++;
                    } catch (Exception ignored) {}
                }
            } catch (Exception ex) {
                sb.append("(unavailable: ").append(ex).append(")\\n");
            }
        } else {
            sb.append("(needs Android 11+)\\n");
        }
        return sb.toString();
    }

    private void onShowRfxLogs() {
        mRfxLogShown = buildRfxTestLog();
        java.io.File dir = getExternalFilesDir(null);
        if (dir != null) {
            writeTextFileQuietly(new java.io.File(dir, RFX_LOG_FILE),
                mRfxLogShown);
        }
        showTab(TAB_TESTS);
    }

    private void onShareRfxLog() {
        String log = buildRfxTestLog();
        java.io.File dir = getExternalFilesDir(null);
        if (dir != null) {
            writeTextFileQuietly(new java.io.File(dir, RFX_LOG_FILE),
                log);
        }
        android.content.Intent send = new android.content.Intent(
            android.content.Intent.ACTION_SEND);
        send.putExtra(android.content.Intent.EXTRA_TEXT, log);
        // v1.24.1: attach a zip of the FULL evidence files as well. The
        // text above carries only the first 64 KB of each file, so the
        // end of a long session (where the failures live) never survived
        // a text share; the zip carries every byte of every file.
        java.io.File zip = buildRfxLogZip(dir);
        if (zip != null) {
            try {
                android.net.Uri uri = androidx.core.content.FileProvider
                    .getUriForFile(this,
                        getPackageName() + ".fileprovider", zip);
                send.setType("application/zip");
                send.putExtra(android.content.Intent.EXTRA_STREAM, uri);
                send.addFlags(
                    android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION);
            } catch (Exception ignored) {
                send.setType("text/plain");
            }
        } else {
            send.setType("text/plain");
        }
        startActivity(android.content.Intent.createChooser(send,
            getString(R.string.setup_tests_logs_title)));
    }

    private java.io.File buildRfxLogZip(java.io.File dir) {
        if (dir == null) {
            return null;
        }
        try {
            java.util.ArrayList<java.io.File> files =
                new java.util.ArrayList<java.io.File>();
            files.add(new java.io.File(dir, RFX_RESULT_FILE));
            String gamePath = getSavedGamePath();
            if (gamePath != null) {
                files.add(new java.io.File(gamePath, "test-rec.txt"));
            }
            files.add(new java.io.File(dir, "rfxgame-stage.txt"));
            files.add(new java.io.File(dir, "rfxgame-stderr.txt"));
            java.io.File glog = new java.io.File(dir,
                "rfx-user/Logs/DebugLogFile.txt");
            if (!glog.isFile()) {
                glog = new java.io.File(dir,
                    "rfx-user/DebugLogFile.txt");
            }
            files.add(glog);
            files.add(new java.io.File(dir, RFX_CAPTURE_FILE));
            java.io.File zip = new java.io.File(getCacheDir(),
                "zh-reforged-test-logs.zip");
            java.util.zip.ZipOutputStream zout =
                new java.util.zip.ZipOutputStream(
                    new java.io.FileOutputStream(zip));
            byte[] buf = new byte[65536];
            boolean any = false;
            for (java.io.File f : files) {
                if (!f.isFile()) {
                    continue;
                }
                zout.putNextEntry(
                    new java.util.zip.ZipEntry(f.getName()));
                java.io.FileInputStream in =
                    new java.io.FileInputStream(f);
                int n;
                while ((n = in.read(buf)) > 0) {
                    zout.write(buf, 0, n);
                }
                in.close();
                zout.closeEntry();
                any = true;
            }
            zout.close();
            return any ? zip : null;
        } catch (Exception e) {
            return null;
        }
    }

    private void onCopyRfxLog() {
        android.content.ClipboardManager cm =
            (android.content.ClipboardManager)
                getSystemService(CLIPBOARD_SERVICE);
        if (cm != null) {
            cm.setPrimaryClip(android.content.ClipData.newPlainText(
                "rfx-test-log", buildRfxTestLog()));
        }
        Toast.makeText(this, R.string.setup_tests_logs_copied,
            Toast.LENGTH_SHORT).show();
    }

    private static void writeTextFileQuietly(java.io.File f,
            String text) {
        try {
            java.io.FileOutputStream out =
                new java.io.FileOutputStream(f);
            out.write(text.getBytes("UTF-8"));
            out.close();
        } catch (Exception ignored) {}
    }

    private static String readTextFileQuietly(java.io.File f) {
        try {
            java.io.FileInputStream in = new java.io.FileInputStream(f);
            byte[] buf = new byte[(int) Math.min(f.length(), 65536)];
            int n = in.read(buf);
            in.close();
            return n > 0 ? new String(buf, 0, n, "UTF-8") : "";
        } catch (Exception e) {
            return "";
        }
    }

    private static String readTextTailQuietly(java.io.File f,
            int maxBytes) {
        try {
            long len = f.length();
            if (len <= 0) {
                return "";
            }
            int n = (int) Math.min(len, maxBytes);
            java.io.RandomAccessFile raf =
                new java.io.RandomAccessFile(f, "r");
            raf.seek(len - n);
            byte[] buf = new byte[n];
            int off = 0;
            while (off < n) {
                int r = raf.read(buf, off, n - off);
                if (r < 0) {
                    break;
                }
                off += r;
            }
            raf.close();
            return off > 0 ? new String(buf, 0, off, "UTF-8") : "";
        } catch (Exception e) {
            return "";
        }
    }

    private int tabTitle(int tab) {'''),
])


# ---------------- 3e) v1.17: the test recorder switch + log ----------------
# The recorder's marker joins the host's diagnostics arrays (the card, the
# game-folder handling and the refresh logic already exist); the engine
# side is GXTestRecorder.h (marker gx_testrec.txt -> test-rec.txt). The
# shared test log also appends test-rec.txt from the game folder.
edit(SETUP, [
    ("""        "gx_trace.txt", "gx_perf.txt", "gx_gles_gputimer.txt", "gx_audio_trace.txt", "gx_net_trace.txt",""",
     """        "gx_trace.txt", "gx_perf.txt", "gx_testrec.txt", "gx_gles_gputimer.txt", "gx_audio_trace.txt", "gx_net_trace.txt","""),
    ("""        R.string.setup_switch_gx_trace, R.string.setup_switch_gx_perf, R.string.setup_switch_gpu_timer,""",
     """        R.string.setup_switch_gx_trace, R.string.setup_switch_gx_perf, R.string.setup_switch_gx_testrec, R.string.setup_switch_gpu_timer,"""),
    ("""        R.string.setup_switch_gx_trace_desc, R.string.setup_switch_gx_perf_desc, R.string.setup_switch_gpu_timer_desc,""",
     """        R.string.setup_switch_gx_trace_desc, R.string.setup_switch_gx_perf_desc, R.string.setup_switch_gx_testrec_desc, R.string.setup_switch_gpu_timer_desc,"""),
    ("""        } else {
            sb.append("frame-result.txt: MISSING\\n");
        }
        java.io.File capture = new java.io.File(dir, RFX_CAPTURE_FILE);""",
     """        } else {
            sb.append("frame-result.txt: MISSING\\n");
        }
        // Zero Hour Reforged (v1.17): the test recorder's numbers file
        // lives in the game folder (the engine writes it next to its
        // marker); append it so one shared log carries everything.
        java.io.File testRec = null;
        String testRecPath = getSavedGamePath();
        if (testRecPath != null) {
            testRec = new java.io.File(testRecPath, "test-rec.txt");
        }
        if (testRec != null && testRec.isFile()) {
            sb.append("test-rec.txt: ").append(testRec.length())
              .append(" bytes, modified ")
              .append(rfxTime(testRec.lastModified())).append("\\n");
            sb.append("---- test-rec.txt ----\\n");
            sb.append(readTextFileQuietly(testRec));
            sb.append("\\n---- end test-rec.txt ----\\n");
        } else {
            sb.append("test-rec.txt: MISSING\\n");
        }
        java.io.File capture = new java.io.File(dir, RFX_CAPTURE_FILE);"""),
])

# ---------------- 3f) v1.19: C4 diagnostics in the shared test log ----
# The C4 game run leaves its evidence in the external files dir
# (rfxgame-stage.txt from RfxGameActivity, rfxgame-stderr.txt from the
# fd-2 redirect) and in the engine's own debug log under the isolated
# user dir; append all three so one shared log carries the whole run.
edit(SETUP, [
    ("""        } else {
            sb.append("test-rec.txt: MISSING\\n");
        }
        java.io.File capture = new java.io.File(dir, RFX_CAPTURE_FILE);""",
     """        } else {
            sb.append("test-rec.txt: MISSING\\n");
        }
        // C4 diagnostics (v1.19): the Reforged game run's evidence.
        java.io.File gstage = new java.io.File(dir, "rfxgame-stage.txt");
        if (gstage.isFile()) {
            sb.append("rfxgame-stage.txt: ").append(gstage.length())
              .append(" bytes, modified ")
              .append(rfxTime(gstage.lastModified())).append("\\n");
            sb.append("---- rfxgame-stage.txt ----\\n");
            sb.append(readTextFileQuietly(gstage));
            sb.append("\\n---- end rfxgame-stage.txt ----\\n");
        } else {
            sb.append("rfxgame-stage.txt: MISSING\\n");
        }
        java.io.File gerr = new java.io.File(dir, "rfxgame-stderr.txt");
        if (gerr.isFile()) {
            sb.append("rfxgame-stderr.txt: ").append(gerr.length())
              .append(" bytes, modified ")
              .append(rfxTime(gerr.lastModified())).append("\\n");
            sb.append("---- rfxgame-stderr.txt ----\\n");
            sb.append(readTextFileQuietly(gerr));
            sb.append("\\n---- tail of rfxgame-stderr.txt ----\\n");
            sb.append(readTextTailQuietly(gerr, 24576));
            sb.append("\\n---- end rfxgame-stderr.txt ----\\n");
        } else {
            sb.append("rfxgame-stderr.txt: MISSING\\n");
        }
        java.io.File glog = new java.io.File(dir, "rfx-user/Logs/DebugLogFile.txt");
        if (!glog.isFile()) {
            glog = new java.io.File(dir, "rfx-user/DebugLogFile.txt");
        }
        if (glog.isFile()) {
            sb.append("DebugLogFile.txt: ").append(glog.length())
              .append(" bytes, modified ")
              .append(rfxTime(glog.lastModified())).append("\\n");
            sb.append("---- DebugLogFile.txt ----\\n");
            sb.append(readTextFileQuietly(glog));
            sb.append("\\n---- tail of DebugLogFile.txt ----\\n");
            sb.append(readTextTailQuietly(glog, 24576));
            sb.append("\\n---- end DebugLogFile.txt ----\\n");
        } else {
            sb.append("DebugLogFile.txt: MISSING\\n");
        }
        java.io.File capture = new java.io.File(dir, RFX_CAPTURE_FILE);"""),
])


# ---------------- 4) Packaging knob for libmainrfx.so ----------------
edit(PACKAGE_SH, [(
    '''    cp "${GX_ENGINE_LIB}" "${JNILIBS}/libmainz60.so"
    echo "Packaging the pure 60-steps engine: libmainz60.so ($(du -h "${GX_ENGINE_LIB}" | cut -f1))"
fi''',
    '''    cp "${GX_ENGINE_LIB}" "${JNILIBS}/libmainz60.so"
    echo "Packaging the pure 60-steps engine: libmainz60.so ($(du -h "${GX_ENGINE_LIB}" | cut -f1))"
fi

# GeneralsX @feature Zero Hour Reforged 14/11/2026 (v1.15) The Stage C3 test
# payload: the Reforged engine's frame selfcheck + offscreen phase, loaded
# only by the launcher's tests page (FrameCheckActivity, own process). Not
# an engine the game ever loads.
if [[ -n "${GX_REFORGEDX_LIB:-}" ]]; then
    if [[ ! -f "${GX_REFORGEDX_LIB}" ]]; then
        echo "ERROR: GX_REFORGEDX_LIB points at a file that does not exist: ${GX_REFORGEDX_LIB}"
        exit 1
    fi
    cp "${GX_REFORGEDX_LIB}" "${JNILIBS}/libmainrfx.so"
    echo "Packaging the Reforged C3 test payload: libmainrfx.so ($(du -h \"${GX_REFORGEDX_LIB}\" | cut -f1))"
fi

# GeneralsX @feature Zero Hour Reforged 19/11/2026 (v1.18) The Stage C4 game
# library: the Reforged engine itself as a playable window, loaded only by
# the launcher's tests page (RfxGameActivity, own process). Not an engine
# the game ever loads.
if [[ -n \"${GX_REFORGEDX_GAME_LIB:-}\" ]]; then
    if [[ ! -f \"${GX_REFORGEDX_GAME_LIB}\" ]]; then
        echo \"ERROR: GX_REFORGEDX_GAME_LIB points at a file that does not exist: ${GX_REFORGEDX_GAME_LIB}\"
        exit 1
    fi
    cp \"${GX_REFORGEDX_GAME_LIB}\" \"${JNILIBS}/libmainrfxgame.so\"
    echo \"Packaging the Reforged C4 game library: libmainrfxgame.so ($(du -h \"${GX_REFORGEDX_GAME_LIB}\" | cut -f1))\"
fi
''',
)])
# ---------------- 4b) v1.24.1 purge, relocated after ALL staging ---------
# Run #41 proved the first placement (right after the engine cp blocks in
# section 4) useless: the SDL/ANGLE/DXVK staging further down the script
# re-staged everything the purge removed, and the workflow's own verify
# step caught the full set still in the APK. The purge now sits after the
# last staging action in the script (the assets listing + engine build
# number), immediately before the gradle section, and it verifies itself.
edit(PACKAGE_SH, [(
    '''echo "==> Engine build number: ${ENGINE_BUILD}"

# --- 4. gradle ---------------------------------------------------------------''',
    '''echo "==> Engine build number: ${ENGINE_BUILD}"

# GeneralsX @purge Zero Hour Reforged 20/11/2026 (v1.24.1, owner's order:
# remove everything MYSOREZ-related that this app no longer needs) The old
# engine left the package in v1.20; its support libraries and its Adreno
# driver asset are dead weight -- the Reforged libraries link only against
# Android system libraries (readelf-verified on the shipped APK). Placed
# AFTER all staging and BEFORE gradle (run #41: purging earlier in the
# script is useless, the staging below it re-stages everything), and it
# verifies itself so a missed file fails the packaging, not the release.
for gxdead in libEGL_angle.so libGLESv2_angle.so libadrenotools.so libdxvk_d3d8.so libdxvk_d3d9.so libfile_redirect_hook.so libgamespy.so libgsl_alloc_hook.so libhook_impl.so libmain_hook.so libopenal.so libSDL3.so libSDL3_image.so libc++_shared.so; do
    rm -f "${JNILIBS}/${gxdead}"
done
rm -rf "${DEFAULT_DRIVER_ASSETS}"
rm -f "${ASSETS}/dxvk.conf"
for gxdead in libEGL_angle.so libGLESv2_angle.so libadrenotools.so libdxvk_d3d8.so libdxvk_d3d9.so libfile_redirect_hook.so libgamespy.so libgsl_alloc_hook.so libhook_impl.so libmain_hook.so libopenal.so libSDL3.so libSDL3_image.so libc++_shared.so; do
    if [[ -e "${JNILIBS}/${gxdead}" ]]; then
        echo "ERROR: purge failed, ${gxdead} is still staged in ${JNILIBS}"
        exit 1
    fi
done
if [[ -d "${DEFAULT_DRIVER_ASSETS}" || -f "${ASSETS}/dxvk.conf" ]]; then
    echo "ERROR: purge failed, old-engine assets are still staged"
    exit 1
fi
echo "Purged the old engine's support libraries and driver assets (v1.24.1)"

# --- 4. gradle ---------------------------------------------------------------''',
)])


# ---------------- 5) Strings in every locale that has the Reforged tab ----
STRINGS_EN = [
    ('nav_tab_tests', 'Reforged Tests'),
    ('setup_tests_home_row_desc', 'Stage C engine tests: offscreen first frame'),
    ('setup_card_tests_page', 'Reforged engine tests'),
    ('setup_tests_intro', 'These tests run the Reforged engine itself (libmainrfx) in complete isolation: it creates its GPU device, renders frames offscreen -- with no window -- and saves the captured frame. The engines you play with are never touched.'),
    ('setup_tests_run', 'Run the tests'),
    ('setup_tests_running', 'The tests are running in their own process -- come back to this page in a few seconds.'),
    ('setup_tests_done', 'The latest results are below.'),
    ('setup_tests_no_results', 'No results yet -- run the tests first.'),
    ('setup_tests_results_title', 'Results'),
    ('setup_tests_capture_title', 'The captured offscreen frame:'),
    ('setup_tests_logs_title', 'Test logs'),
    ('setup_tests_logs_desc', 'The full record of a test run: the result file, and the system note of why the test process exited (a crash, or the memory killer), ready to share.'),
    ('setup_tests_logs_show', 'Show the logs'),
    ('setup_tests_logs_share', 'Share the log'),
    ('setup_tests_logs_copy', 'Copy the log'),
    ('setup_tests_logs_copied', 'Log copied'),
    ('setup_switch_gx_testrec', 'Test recorder'),
    ('setup_switch_gx_testrec_desc', 'Records the numbers of a test match into test-rec.txt in the game folder: match start, the engine CRC at frames 100/200/300, memory use every minute, and LAN lobby events. Turn on before a test match (solo or LAN), then share the file or the test log. (gx_testrec.txt)'),
    ('setup_tests_died', 'The test process ended with no result -- the system closed it. Open the test logs below to see why, and share them.'),
    ('setup_tests_game_title', 'The Reforged game itself (Stage C4)'),
    ('setup_tests_game_desc', 'Launches the full Reforged engine as a game window -- its own main menu and shell map -- in its own process. The engines you play with are never touched. Experimental: touch controls arrive in a later stage.'),
    ('setup_tests_game_launch', 'Launch the Reforged game'),
]
STRINGS_AR = [
    ('nav_tab_tests', 'اختبارات ريفورجيد'),
    ('setup_tests_home_row_desc', 'اختبارات محرك المرحلة C: أول فريم دون شاشة'),
    ('setup_card_tests_page', 'اختبارات محرك ريفورجيد'),
    ('setup_tests_intro', 'هذه الاختبارات تشغّل محرك ريفورجيد نفسه (libmainrfx) بمعزل تام: ينشئ جهاز الرسوم، ويرسم فريمات دون شاشة، ويحفظ الفريم الملتقط. المحركات التي تلعب بها لا تُمسّ أبدًا.'),
    ('setup_tests_run', 'تشغيل الاختبارات'),
    ('setup_tests_running', 'الاختبارات شغّالة بعملية منفصلة -- ارجع لهذه الصفحة بعد ثوانٍ.'),
    ('setup_tests_done', 'آخر النتائج بالأسفل.'),
    ('setup_tests_no_results', 'لا نتائج بعد -- شغّل الاختبارات أولًا.'),
    ('setup_tests_results_title', 'النتائج'),
    ('setup_tests_capture_title', 'الفريم الملتقط دون شاشة:'),
    ('setup_tests_logs_title', 'سجلات الاختبارات'),
    ('setup_tests_logs_desc', 'سجل كامل لتشغيل الاختبار: ملف النتيجة، وملاحظة النظام نفسه عن سبب خروج عملية الاختبار (انهيار، أو قتل بسبب الذاكرة)، جاهز للمشاركة.'),
    ('setup_tests_logs_show', 'عرض السجلات'),
    ('setup_tests_logs_share', 'مشاركة السجل'),
    ('setup_tests_logs_copy', 'نسخ السجل'),
    ('setup_tests_logs_copied', 'نُسخ السجل'),
    ('setup_switch_gx_testrec', 'مسجّل الاختبارات'),
    ('setup_switch_gx_testrec_desc', 'يسجّل أرقام مباراة الاختبار في ملف test-rec.txt داخل مجلد اللعبة: بداية المباراة، وبصمة المحرك عند الفريمات 100/200/300، واستهلاك الذاكرة كل دقيقة، وأحداث لوبي الشبكة المحلية. فعّله قبل مباراة اختبار (فردية أو شبكية)، ثم شارك الملف أو سجل الاختبارات. (gx_testrec.txt)'),
    ('setup_tests_died', 'انتهت عملية الاختبار دون أي نتيجة -- النظام أغلقها. افتح سجلات الاختبارات بالأسفل لمعرفة السبب ومشاركتها.'),
    ('setup_tests_game_title', 'لعبة ريفورجيد نفسها (المرحلة C4)'),
    ('setup_tests_game_desc', 'تشغّل محرك ريفورجيد الكامل كنافذة لعبة -- قائمته الرئيسية وخريطة القشرة -- بعملية منفصلة. المحركات التي تلعب بها لا تُمسّ أبدًا. تجريبي: التحكم باللمس يأتي بمرحلة لاحقة.'),
    ('setup_tests_game_launch', 'تشغيل لعبة ريفورجيد'),
]


def xml_escape(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace("'", "\\'"))


count = 0
for strings_xml in sorted(glob.glob(os.path.join(RES, 'values*', 'strings.xml'))):
    s = open(strings_xml, encoding='utf-8').read()
    anchor = None
    for line in s.split('\n'):
        if 'name="nav_tab_reforged"' in line:
            anchor = line
            break
    if anchor is None:
        continue
    if 'name="nav_tab_tests"' in s:
        sys.exit(f'phase3: {strings_xml} already carries nav_tab_tests')
    is_ar = os.path.basename(os.path.dirname(strings_xml)) == 'values-ar'
    block = ''.join(
        f'\n    <string name="{name}">{xml_escape(text)}</string>'
        for name, text in (STRINGS_AR if is_ar else STRINGS_EN))
    s = s.replace(anchor, anchor + block, 1)
    open(strings_xml, 'w', encoding='utf-8').write(s)
    count += 1
if count < 10:
    sys.exit(f'phase3: only {count} locale files carried nav_tab_reforged -- expected 10+')
print(f'strings added to {count} locale files')


# ---------------- 6a) v1.25: the render-resolution slider (Reforged) ------
# The engine half shipped inert in v1.24 (SdlGpuFrame's ZH_RENDER_SCALE knob,
# clamped [0.5, 1.0]); this wires the launcher end: a slider card next to the
# menu-text-size card, a SharedPreferences percent, and (in RfxGameActivity's
# onCreate above) the env var set before the engine starts.
edit(SETUP, [
    ('''                buildUiScaleSection(page);
''',
     '''                buildUiScaleSection(page);
                buildRfxRenderScaleSection(page);
'''),
    ('''    private void buildUiScaleSection(LinearLayout root) {
''',
     '''    // GeneralsX @feature Reforged render resolution 20/11/2026 (v1.25):
    // the Reforged engine renders at this fraction of the panel and
    // upscales (SdlGpuFrame's ZH_RENDER_SCALE). Stored as a plain percent
    // in SharedPreferences; RfxGameActivity turns it into the env var
    // before the engine starts. 100 = full resolution.
    private Slider rfxRenderScaleSlider;
    private TextView rfxRenderScaleLabel;

    private static final String PREF_RFX_RENDER_SCALE = "rfx_render_scale";

    static int getRfxRenderScalePercent(android.content.Context ctx) {
        int percent = ctx.getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .getInt(PREF_RFX_RENDER_SCALE, 100);
        return Math.max(50, Math.min(100, percent));
    }

    private void writeRfxRenderScalePercent(int percent) {
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit()
            .putInt(PREF_RFX_RENDER_SCALE,
                Math.max(50, Math.min(100, percent))).apply();
    }

    private void buildRfxRenderScaleSection(LinearLayout root) {
        LinearLayout content = UiKit.card(root);
        rfxRenderScaleLabel = UiKit.sectionHeader(content, R.drawable.ic_gzh_sliders,
            getString(R.string.setup_card_render_scale), true);

        int startPercent = getRfxRenderScalePercent(this);
        rfxRenderScaleSlider = new Slider(this);
        rfxRenderScaleSlider.setValueFrom(50f);
        rfxRenderScaleSlider.setValueTo(100f);
        rfxRenderScaleSlider.setStepSize(5f);
        rfxRenderScaleSlider.setValue(100f);
        rfxRenderScaleSlider.setEnabled(false);
        rfxRenderScaleSlider.setLabelBehavior(LabelFormatter.LABEL_GONE);
        rfxRenderScaleSlider.setTrackActiveTintList(UiKit.tint(this, R.color.gzh_primary));
        rfxRenderScaleSlider.setTrackInactiveTintList(UiKit.tint(this, R.color.gzh_surface_container_highest));
        rfxRenderScaleSlider.setThumbTintList(UiKit.tint(this, R.color.gzh_primary));
        rfxRenderScaleSlider.setHaloTintList(UiKit.tint(this, R.color.gzh_ripple_primary));
        updateRfxRenderScaleLabel(100);
        rfxRenderScaleSlider.addOnChangeListener((slider, value, fromUser) -> updateRfxRenderScaleLabel((int) value));
        LinearLayout.LayoutParams sliderLp = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        sliderLp.topMargin = UiKit.dim(this, R.dimen.gzh_item_gap_tight);
        content.addView(rfxRenderScaleSlider, sliderLp);

        UiKit.button(content, UiKit.BTN_PRIMARY, R.drawable.ic_gzh_check,
            getString(R.string.setup_button_apply_render_scale), () -> {
                writeRfxRenderScalePercent((int) rfxRenderScaleSlider.getValue());
                Toast.makeText(this, R.string.setup_toast_text_size_saved, Toast.LENGTH_LONG).show();
            });

        UiKit.helpText(content, getString(R.string.setup_render_scale_help));
    }

    private void updateRfxRenderScaleLabel(int percent) {
        if (rfxRenderScaleLabel != null) {
            rfxRenderScaleLabel.setText(getString(R.string.setup_text_size_label, percent));
        }
    }

    private void buildUiScaleSection(LinearLayout root) {
'''),
])

# ---------------- 6b) v1.25: render-scale strings, every locale ----------
RENDER_SCALE_STRINGS = {
    'values': [
        ('setup_card_render_scale', 'Render Resolution'),
        ('setup_button_apply_render_scale', 'Apply Render Resolution'),
        ('setup_render_scale_help', "Temporarily locked at 100 (full quality) while this feature is being fixed. It will return in an update."),
    ],
    'values-ar': [
        ('setup_card_render_scale', 'دقة العرض'),
        ('setup_button_apply_render_scale', 'تطبيق دقة العرض'),
        ('setup_render_scale_help', 'مقفلة مؤقتًا على 100 (الجودة الكاملة) ريثما تُصلَح هذه الميزة. ستعود في تحديث قادم.'),
    ],
    'values-de': [
        ('setup_card_render_scale', 'Renderauflösung'),
        ('setup_button_apply_render_scale', 'Renderauflösung anwenden'),
        ('setup_render_scale_help', 'Rendert das Reforged-Spiel mit diesem Prozentsatz der Bildschirmauflösung und streckt es wieder auf Vollbild. Niedrigere Werte (z. B. 75) laufen auf schwächeren Handys flüssiger, mit etwas weniger Schärfe. 100 ist volle Qualität. Wird beim nächsten Spielstart wirksam, nicht sofort.'),
    ],
    'values-es': [
        ('setup_card_render_scale', 'Resolución de renderizado'),
        ('setup_button_apply_render_scale', 'Aplicar resolución de renderizado'),
        ('setup_render_scale_help', 'Renderiza el juego Reforged con este porcentaje de la resolución de tu pantalla y lo estira a pantalla completa. Los valores más bajos (prueba 75) van más fluidos en teléfonos débiles, con algo menos de nitidez. 100 es la calidad completa. Se aplica la próxima vez que inicies el juego, no al instante.'),
    ],
    'values-fa': [
        ('setup_card_render_scale', 'وضوح رندر'),
        ('setup_button_apply_render_scale', 'اعمال وضوح رندر'),
        ('setup_render_scale_help', 'بازی ریفورجد را با این درصد از وضوح صفحه‌نمایش رندر می‌کند و به تمام‌صفحه می‌کشد. مقادیر کمتر (۷۵ را امتحان کنید) روی گوشی‌های ضعیف‌تر روان‌تر اجرا می‌شود، با کمی کاهش وضوح. ۱۰۰ کیفیت کامل است. از اجرای بعدی بازی اعمال می‌شود، نه فوراً.'),
    ],
    'values-fr': [
        ('setup_card_render_scale', 'Résolution de rendu'),
        ('setup_button_apply_render_scale', 'Appliquer la résolution de rendu'),
        ('setup_render_scale_help', "Affiche le jeu Reforged à ce pourcentage de la résolution de votre écran, puis l'étire en plein écran. Des valeurs plus basses (essayez 75) sont plus fluides sur les téléphones modestes, avec un peu moins de netteté. 100 est la qualité maximale. Prend effet au prochain lancement du jeu, pas immédiatement."),
    ],
    'values-b+isv': [
        ('setup_card_render_scale', 'Razrěšenje renderovanja'),
        ('setup_button_apply_render_scale', 'Priměniti razrěšenje renderovanja'),
        ('setup_render_scale_help', 'Renderuje igru Reforged pri tomto procentu razrěšenja ekrana i raztegaje ju na cěly ekran. Nižše hodnoty (poprobuj 75) rabotajut plavněje na slabyh telefonah, s někoj utratom ostrosti. 100 je polna jakość. Dějstvuje od slědujuščego zapuska igry, ne srazu.'),
    ],
    'values-ko': [
        ('setup_card_render_scale', '렌더 해상도'),
        ('setup_button_apply_render_scale', '렌더 해상도 적용'),
        ('setup_render_scale_help', '화면 해상도의 이 비율로 Reforged 게임을 렌더링한 뒤 전체 화면으로 확대합니다. 낮은 값(75 권장)은 약한 휴대폰에서 더 부드럽게 실행되며 선명도가 약간 떨어집니다. 100이 최고 화질입니다. 다음에 게임을 실행할 때 적용되며 즉시 적용되지 않습니다.'),
    ],
    'values-pl': [
        ('setup_card_render_scale', 'Rozdzielczość renderowania'),
        ('setup_button_apply_render_scale', 'Zastosuj rozdzielczość renderowania'),
        ('setup_render_scale_help', 'Renderuje grę Reforged w tym procencie rozdzielczości ekranu i rozciąga ją do pełnego ekranu. Niższe wartości (spróbuj 75) działają płynniej na słabszych telefonach, kosztem ostrości. 100 to pełna jakość. Obowiązuje od następnego uruchomienia gry, nie od razu.'),
    ],
    'values-pt-rBR': [
        ('setup_card_render_scale', 'Resolução de renderização'),
        ('setup_button_apply_render_scale', 'Aplicar resolução de renderização'),
        ('setup_render_scale_help', 'Renderiza o jogo Reforged nesta porcentagem da resolução da tela e o estica para tela cheia. Valores menores (tente 75) rodam mais suaves em celulares fracos, com alguma perda de nitidez. 100 é a qualidade total. Entra em vigor na próxima vez que você abrir o jogo, não na hora.'),
    ],
    'values-ru': [
        ('setup_card_render_scale', 'Разрешение рендера'),
        ('setup_button_apply_render_scale', 'Применить разрешение рендера'),
        ('setup_render_scale_help', 'Рендерит игру Reforged в этом проценте разрешения экрана и растягивает на весь экран. Меньшие значения (попробуйте 75) работают плавнее на слабых телефонах, с некоторой потерей резкости. 100 — полное качество. Применяется при следующем запуске игры, не сразу.'),
    ],
    'values-uk': [
        ('setup_card_render_scale', 'Роздільна здатність рендера'),
        ('setup_button_apply_render_scale', 'Застосувати роздільну здатність рендера'),
        ('setup_render_scale_help', 'Рендерить гру Reforged у цьому відсотку роздільної здатності екрана й розтягує на весь екран. Менші значення (спробуйте 75) працюють плавніше на слабких телефонах, із деякою втратою різкості. 100 — повна якість. Застосовується під час наступного запуску гри, не одразу.'),
    ],
    'values-zh': [
        ('setup_card_render_scale', '渲染分辨率'),
        ('setup_button_apply_render_scale', '应用渲染分辨率'),
        ('setup_render_scale_help', '以屏幕分辨率的此百分比渲染 Reforged 游戏，再拉伸至全屏。较低的值（可试 75）在较弱的手机上运行更流畅，但清晰度会有所下降。100 为完整画质。下次启动游戏时生效，不会立即生效。'),
    ],
}

count = 0
for strings_xml in sorted(glob.glob(os.path.join(RES, 'values*', 'strings.xml'))):
    s = open(strings_xml, encoding='utf-8').read()
    anchor = None
    for line in s.split('\n'):
        if 'name="setup_tests_game_launch"' in line:
            anchor = line
            break
    if anchor is None:
        continue
    if 'name="setup_card_render_scale"' in s:
        sys.exit(f'phase3: {strings_xml} already carries setup_card_render_scale')
    locale = os.path.basename(os.path.dirname(strings_xml))
    block = ''.join(
        f'\n    <string name="{name}">{xml_escape(text)}</string>'
        for name, text in RENDER_SCALE_STRINGS.get(locale, RENDER_SCALE_STRINGS['values']))
    s = s.replace(anchor, anchor + block, 1)
    open(strings_xml, 'w', encoding='utf-8').write(s)
    count += 1
if count < 10:
    sys.exit(f'phase3: only {count} locale files carried the tests strings -- expected 10+')
print(f'render-scale strings added to {count} locale files')


# ---------------- 7) v1.25 ADOPTION: Reforged reskin + developer credit + C6/C7
# (Reforged the only engine entry, on the shared user-data folder).
# The reskin is a palette + shape pass: the shell's look is role-based
# (colors.xml roles through ThemeHelper/UiKit), so retuning the roles and
# the corner radii re-skins every screen at once. Palette: near-black
# blue-steel surfaces, Reforged gold primary, off-white text.

# ---------------- 7a) colors.xml palette (regex per role; values only) ---
import re
COLORS = os.path.join(RES, 'values', 'colors.xml')
REFORGED_PALETTE = {
    'gzh_background': '#0B0E13',
    'gzh_surface': '#10141B',
    'gzh_surface_container_low': '#12161F',
    'gzh_surface_container': '#161C26',
    'gzh_surface_container_high': '#1E2634',
    'gzh_surface_container_highest': '#283242',
    'gzh_on_surface': '#ECEEF2',
    'gzh_on_surface_variant': '#A8B0BE',
    'gzh_on_surface_faint': '#8B94A5',
    'gzh_outline': '#46536A',
    'gzh_outline_variant': '#232B38',
    'gzh_primary': '#E3B341',
    'gzh_on_primary': '#241A02',
    'gzh_primary_container': '#4A3A10',
    'gzh_on_primary_container': '#F5D67A',
    'gzh_primary_dark': '#0B0E13',
    'gzh_accent': '#E3B341',
    'gzh_secondary': '#9FB4C8',
    'gzh_on_secondary': '#16222E',
    'gzh_secondary_container': '#2A3644',
    'gzh_on_secondary_container': '#D7E3EE',
    'gzh_on_surface_disabled': '#61ECEEF2',
    'gzh_container_disabled': '#1FECEEF2',
    'gzh_ripple_light': '#1FECEEF2',
    'gzh_ripple_primary': '#33E3B341',
}
xml = open(COLORS, encoding='utf-8').read()
for name, value in REFORGED_PALETTE.items():
    xml, n = re.subn(r'(<color name="' + name + r'">)#[0-9A-Fa-f]+(</color>)',
                     r'\g<1>' + value + r'\g<2>', xml)
    if n != 1:
        sys.exit('phase3: palette role %s matched %d times' % (name, n))
open(COLORS, 'w', encoding='utf-8').write(xml)
print('reforged palette applied to colors.xml (%d roles)' % len(REFORGED_PALETTE))

# ---------------- 7b) angular shapes: dimens + UiKit radii ---------------
edit(os.path.join(RES, 'values', 'dimens.xml'), [
    ('<dimen name="gzh_radius_card">24dp</dimen>',
     '<dimen name="gzh_radius_card">6dp</dimen>'),
    ('<dimen name="gzh_radius_row">16dp</dimen>',
     '<dimen name="gzh_radius_row">4dp</dimen>'),
    ('<dimen name="gzh_radius_field">16dp</dimen>',
     '<dimen name="gzh_radius_field">4dp</dimen>'),
])
edit(os.path.join(JAVA_DIR, 'UiKit.java'), [
    ('        b.setCornerRadius(dp(c, 26));',
     '        b.setCornerRadius(dp(c, 6));'),
    ('            b.setCornerRadius(dp(c, 22));',
     '            b.setCornerRadius(dp(c, 6));'),
])

# ---------------- 7c) C7: the launch path starts the Reforged engine -----
# launchGameNow() (and its rotation-completion twin) named the old engine's
# activity; its native libraries have not shipped since v1.24.1's purge, so
# the entry was already dead -- it now starts RfxGameActivity, keeping the
# mod safe-start wrapper, the language override and the rotation settle.
setup_src = open(SETUP, encoding='utf-8').read()
launch_old = 'startActivity(new Intent(this, GeneralsZHActivity.class));'
if setup_src.count(launch_old) != 2:
    sys.exit('phase3: expected 2 GeneralsZHActivity launch sites, found %d'
             % setup_src.count(launch_old))
setup_src = setup_src.replace(launch_old,
    'startActivity(new Intent(this, RfxGameActivity.class));')
open(SETUP, 'w', encoding='utf-8').write(setup_src)

# ---------------- 7d) C7: pin the game selection to Zero Hour ------------
# The Generals/Zero Hour picker chose between the old engines. With one
# engine it only misleads (the Reforged page even hides itself when Generals
# is picked), so the picker goes and the selection is pinned where the page
# is built.
edit(SETUP, [
    ("""        final boolean generals = isGeneralsSelected(this);
""",
     """        // v1.25 (C7 adoption): one engine -- Zero Hour Reforged. The game
        // selection is pinned to Zero Hour; the picker that chose between the
        // old engines is removed below.
        if (isGeneralsSelected(this)) {
            setSelectedGame(this, GAME_ZERO_HOUR);
        }
        final boolean generals = false;
"""),
])
setup_src = open(SETUP, encoding='utf-8').read()
span_start = setup_src.index('        CharSequence[] games = new CharSequence[] {')
span_end_marker = '        UiKit.supporting(game, getString(R.string.setup_game_desc));'
span_end = setup_src.index(span_end_marker) + len(span_end_marker)
setup_src = (setup_src[:span_start]
    + '        // (the Generals/Zero Hour segmented picker stood here; v1.25 removed it)\n'
    + setup_src[span_end:])
open(SETUP, 'w', encoding='utf-8').write(setup_src)

# ---------------- 7e) developer credit on the Home page ------------------
edit(SETUP, [
    ("""        // The one thing this app exists to do, as the first thing on it.
        UiKit.button(page, UiKit.BTN_PRIMARY, R.drawable.ic_gzh_play,
            getString(R.string.setup_button_launch_game), this::onLaunchGame);
""",
     """        // The one thing this app exists to do, as the first thing on it.
        UiKit.button(page, UiKit.BTN_PRIMARY, R.drawable.ic_gzh_play,
            getString(R.string.setup_button_launch_game), this::onLaunchGame);

        // v1.25: the developer credit, centred under the launch button.
        TextView developerCredit = UiKit.supporting(page,
            getString(R.string.setup_developer_credit));
        developerCredit.setGravity(android.view.Gravity.CENTER);
"""),
])

# ---------------- 7f+7g) C6 shared user-data folder: REVERTED in v1.25.1
# v1.25 moved the engine onto the shared MYSOREZ data folder (7g) and
# pointed the tests page at its log first (7f). v1.25 then crashed with a
# SIGSEGV at every startup, inside engine init, before the menu -- while
# v1.24.1 on the private rfx-user folder played to a full victory on the
# same phone. Until the shared folder's files (written by another engine)
# are proven innocent, the engine keeps its private folder: NO edits in
# this section, so RfxGameActivity and the tests page stay exactly as the
# base shell (and v1.24.1) shipped them.

# ---------------- 7h) the credit string, every locale --------------------
CREDIT_STRINGS = {
    'values': 'Developer: Louay Khaled',
    'values-ar': 'المطوّر: لؤي خالد',
    'values-b+isv': 'Razvojnik: Louay Khaled',
    'values-de': 'Entwickler: Louay Khaled',
    'values-es': 'Desarrollador: Louay Khaled',
    'values-fa': 'توسعه‌دهنده: لؤي خالد',
    'values-fr': 'Développeur : Louay Khaled',
    'values-ko': '개발자: Louay Khaled',
    'values-pl': 'Twórca: Louay Khaled',
    'values-pt-rBR': 'Desenvolvedor: Louay Khaled',
    'values-ru': 'Разработчик: Louay Khaled',
    'values-uk': 'Розробник: Louay Khaled',
    'values-zh': '开发者：Louay Khaled',
}
credit_added = 0
for strings_xml in sorted(glob.glob(os.path.join(RES, 'values*', 'strings.xml'))):
    locale = os.path.basename(os.path.dirname(strings_xml))
    if locale not in CREDIT_STRINGS:
        continue
    xml = open(strings_xml, encoding='utf-8').read()
    if 'name="setup_developer_credit"' in xml:
        sys.exit('phase3: %s already carries setup_developer_credit' % strings_xml)
    lines = xml.split('\n')
    for idx, line in enumerate(lines):
        if 'name="setup_tests_game_launch"' in line:
            indent = line[:len(line) - len(line.lstrip())]
            lines.insert(idx + 1, indent + '<string name="setup_developer_credit">'
                         + xml_escape(CREDIT_STRINGS[locale]) + '</string>')
            credit_added += 1
            break
    else:
        sys.exit('phase3: no setup_tests_game_launch anchor in %s' % strings_xml)
    open(strings_xml, 'w', encoding='utf-8').write('\n'.join(lines))
if credit_added < 10:
    sys.exit('phase3: developer credit added to only %d locales' % credit_added)
print('developer credit string added to %d locale files' % credit_added)

print('PHASE 3 DONE')
