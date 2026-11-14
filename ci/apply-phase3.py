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

import org.libsdl.app.SDLActivity;

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
}
'''
fc_path = os.path.join(JAVA_DIR, 'FrameCheckActivity.java')
if os.path.exists(fc_path):
    sys.exit('phase3: FrameCheckActivity.java already exists -- refusing to overwrite')
open(fc_path, 'w', encoding='utf-8').write(FRAMECHECK_JAVA)
print('wrote', os.path.relpath(fc_path, SRC))

# ---------------- 2) Manifest: register the activity ----------------
edit(MANIFEST, [(
    '    </application>',
    '''        <activity
            android:name=".FrameCheckActivity"
            android:exported="false"
            android:process=":framecheck"
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
    private static final String RFX_RESULT_FILE = "frame-result.txt";
    private static final String RFX_CAPTURE_FILE = "frame-capture.bmp";
    private static final String RFX_GAMEDATA_MARKER = "zh-gamedata-path.txt";

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
            .putBoolean(PREF_RFX_TESTS_RUNNING, true).apply();
        startActivity(new android.content.Intent(this, FrameCheckActivity.class));
    }

    private void maybeRefreshTestsPage() {
        if (!getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
                .getBoolean(PREF_RFX_TESTS_RUNNING, false)) {
            return;
        }
        java.io.File dir = getExternalFilesDir(null);
        if (dir == null) {
            return;
        }
        java.io.File result = new java.io.File(dir, RFX_RESULT_FILE);
        if (!result.isFile() || result.length() == 0) {
            return;  // still running (or died without a file)
        }
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit()
            .putBoolean(PREF_RFX_TESTS_RUNNING, false).apply();
        if (currentTab == TAB_TESTS && contentHost != null) {
            showTab(TAB_TESTS);
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

        LinearLayout run = UiKit.card(page);
        UiKit.supporting(run, getString(running
            ? R.string.setup_tests_running
            : haveResult ? R.string.setup_tests_done
                         : R.string.setup_tests_no_results));
        UiKit.button(run, UiKit.BTN_PRIMARY, R.drawable.ic_gzh_chip,
            getString(R.string.setup_tests_run), this::onRunRfxTests);

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

    private int tabTitle(int tab) {'''),
])

# ---------------- 4) Packaging knob for libmainrfx.so ----------------
edit(PACKAGE_SH, [(
    '''    cp "${GX_REFORGED_LIB}" "${JNILIBS}/libmainrf.so"
    echo "Packaging the Reforged enhanced standard engine: libmainrf.so ($(du -h "${GX_REFORGED_LIB}" | cut -f1))"
fi''',
    '''    cp "${GX_REFORGED_LIB}" "${JNILIBS}/libmainrf.so"
    echo "Packaging the Reforged enhanced standard engine: libmainrf.so ($(du -h "${GX_REFORGED_LIB}" | cut -f1))"
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
    echo "Packaging the Reforged C3 test payload: libmainrfx.so ($(du -h "${GX_REFORGEDX_LIB}" | cut -f1))"
fi''',
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

print('PHASE 3 DONE')
