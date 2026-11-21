#!/usr/bin/env python3
"""Phase 3 (CI, v1.30): the Reforged product pass over the host shell.

What this script makes of the MYSOREZ launcher (owner's launcher order,
2026-11-20: a clean product shareable among friends, not a scattered
lab):

  * RfxGameActivity (new file) is the product's game activity: it runs
    the Reforged engine (libmainrfxgame.so) in its own ":rfxgame"
    process, keeps the app's data in its own external folder
    (ZeroHourReforged/ on the shared storage, so saves survive an
    uninstall), writes the run log there automatically (a Settings
    switch can turn it off), passes the game-text language to the
    engine (-language + the Registry.ini Language line) and bridges
    the launcher's interface-size setting (GXUiScale in Options.ini)
    to the engine as GX_UI_SCALE.
  * The C3 test payload is GONE: no FrameCheckActivity, no tests
    page, and libmainrfx.so is on the packaging purge list and the
    workflow's forbidden list, so it can never ship again. The CI
    selfcheck target remains as a build-only gate in the workflow.
  * Help & About gains a Support & Log card (the run log's viewer and
    share path, transplanted from the old tests page and retargeted
    at the app's own folder).
  * The adoption reskin (section 7): Reforged palette and shapes, the
    game pinned to Zero Hour, the launch path starting
    RfxGameActivity, the developer credit on Home, in every locale.

v1.30 delta (the only changes over the v1.29 script):
  * the graphics presets write two keys for High/Ultra
    (StaticGameLOD + ClassicGraphics = no, committee Q5), with a
    one-time migration for existing High/Ultra installs and an
    honest classic-on note in the preset card;
  * RfxGameActivity gains the LAN multicast lock the engine's
    udp.cpp calls by name (committee appendix, section 334.4).

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

# ---------------- 1) FrameCheckActivity: REMOVED in v1.29 --------
# The C3 test payload and its activity are gone (owner's launcher
# order, 2026-11-20): the product ships the game only. The CI
# selfcheck target remains as a build-only gate in the workflow;
# libmainrfx.so is on the packaging purge list (section 4b) and
# on the workflow's forbidden list, so it can never ship again.

# ---------------- 1b) RfxGameActivity.java (new file) ----------------
RFXGAME_JAVA = '''
package com.generalsx.zerohour;

import org.libsdl.apprfx.SDLActivity;

import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.system.Os;
import android.util.Log;

/**
 * Zero Hour Reforged (v1.29): the activity that runs the Reforged
 * engine itself as a game -- the product's one play path.
 *
 * The payload is packaged as libmainrfxgame.so: the full Reforged
 * game (PosixMain's SDL_main) built as a shared library by the C4
 * CMake patch. This activity hands it what a desktop launch would:
 * the install root (the game folder the owner picked in this
 * launcher, passed as -root; PosixMain chdir()s there itself), the
 * fork's data overlay (-overlay), the game-text language the owner
 * picked in the launcher (-language, with Registry.ini synced to
 * the same token so the engine's font/language files follow), and
 * a writable user-data directory (ZH_USER_DATA_DIR).
 *
 * The user data lives in the app's OWN folder on the device storage,
 * ZeroHourReforged/User at the root of the shared storage (owner's
 * order, v1.29): saves, settings, replays and the run logs sit where
 * the owner can see, copy and share them, and they survive an
 * uninstall. Data from the pre-1.29 private folder is migrated once,
 * on the first launch that finds it. The run log (engine stderr +
 * stage markers) is written by default; a "logging_off" marker file
 * in the user folder -- the Settings switch owns it -- turns it off.
 *
 * It runs in its own process (the manifest's :rfxgame), under the
 * isolated SDL 3.4.16 Java layer -- never the host shell's layer,
 * and never in a process with another engine.
 */
public class RfxGameActivity extends SDLActivity {

    @Override
    protected String[] getLibraries() {
        return new String[] { "mainrfxgame" };
    }

    // ------------------------------------------------------------------
    // The app's own folder on the device storage (v1.29)
    // ------------------------------------------------------------------

    /** <shared storage>/ZeroHourReforged, or null when unavailable. */
    public static java.io.File rfxRoot(android.content.Context ctx) {
        try {
            java.io.File sd =
                android.os.Environment.getExternalStorageDirectory();
            if (sd == null) return null;
            java.io.File root = new java.io.File(sd, "ZeroHourReforged");
            root.mkdirs();
            return root.isDirectory() ? root : null;
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * The engine's user-data directory: <own folder>/User, falling
     * back to the pre-1.29 app-external rfx-user folder when the
     * shared storage is unavailable, so a launch never fails on it.
     */
    public static java.io.File userDataDir(android.content.Context ctx) {
        java.io.File root = rfxRoot(ctx);
        if (root != null) {
            java.io.File user = new java.io.File(root, "User");
            user.mkdirs();
            if (user.isDirectory()) return user;
        }
        java.io.File ext = ctx.getExternalFilesDir(null);
        java.io.File legacy = ext == null ? null
            : new java.io.File(ext, "rfx-user");
        if (legacy != null) legacy.mkdirs();
        return legacy;
    }

    private java.io.File logFile(String name) {
        java.io.File root = rfxRoot(this);
        if (root != null) return new java.io.File(root, name);
        return new java.io.File(getExternalFilesDir(null), name);
    }

    private boolean mLoggingOff = false;

    private boolean loggingOff(java.io.File userDir) {
        return userDir != null
            && new java.io.File(userDir, "logging_off").isFile();
    }

    // One-time migration of the pre-1.29 private user folder into the
    // own folder (v1.29): copy, then rename the old folder aside as a
    // backup, so the move happens exactly once and nothing is lost.
    private void migrateLegacyUserData(java.io.File userDir) {
        try {
            if (userDir == null) return;
            java.io.File ext = getExternalFilesDir(null);
            if (ext == null) return;
            java.io.File legacy = new java.io.File(ext, "rfx-user");
            if (!legacy.isDirectory()) return;
            if (legacy.getCanonicalPath().equals(userDir.getCanonicalPath())) return;
            if (!new java.io.File(legacy, "Options.ini").isFile()) return;
            if (new java.io.File(userDir, "Options.ini").isFile()) return;
            copyRecursive(legacy, userDir);
            legacy.renameTo(new java.io.File(ext, "rfx-user-pre129-backup"));
        } catch (Exception ignored) {}
    }

    private static void copyRecursive(java.io.File from, java.io.File to)
            throws java.io.IOException {
        if (from.isDirectory()) {
            to.mkdirs();
            java.io.File[] kids = from.listFiles();
            if (kids != null) {
                for (java.io.File kid : kids) {
                    copyRecursive(kid, new java.io.File(to, kid.getName()));
                }
            }
            return;
        }
        java.io.File parent = to.getParentFile();
        if (parent != null) parent.mkdirs();
        java.io.InputStream in = new java.io.FileInputStream(from);
        java.io.OutputStream out = new java.io.FileOutputStream(to);
        byte[] buf = new byte[65536];
        int n;
        while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        in.close();
        out.close();
    }

    // ------------------------------------------------------------------
    // Game-text language: -language for the string overlay, and
    // Registry.ini for the engine's language/font file selection.
    // Both follow the launcher's one game-text token (LocaleHelper).
    // ------------------------------------------------------------------

    private static final String[] ENGINE_LANGUAGES = {
        "english", "turkish", "german", "ukrainian", "russian", "french",
        "arabic"
    };

    private String engineLanguageToken() {
        try {
            String token = LocaleHelper.getGameTextToken(this);
            if (token == null) return "english";
            token = token.trim().toLowerCase(java.util.Locale.US);
            for (String known : ENGINE_LANGUAGES) {
                if (known.equals(token)) return token;
            }
        } catch (Exception ignored) {}
        return "english";
    }

    // The launcher's interface-size slider saves GXUiScale (percent) in
    // the user folder's Options.ini -- the file our own engine keeps its
    // options in. The engine reads the GX_UI_SCALE environment variable
    // instead (UserUiScale.h), so bridge it here, before the engine
    // library loads in super.onCreate.
    private void applyInterfaceScale(java.io.File userDir) {
        try {
            if (userDir == null) return;
            java.io.File ini = new java.io.File(userDir, "Options.ini");
            if (!ini.isFile()) return;
            java.io.BufferedReader r = new java.io.BufferedReader(
                new java.io.FileReader(ini));
            try {
                String line;
                while ((line = r.readLine()) != null) {
                    String[] parts = line.split("=", 2);
                    if (parts.length == 2
                            && parts[0].trim().equalsIgnoreCase("GXUiScale")) {
                        int pct = Integer.parseInt(parts[1].trim());
                        if (pct > 100 && pct <= 200) {
                            Os.setenv("GX_UI_SCALE",
                                String.valueOf(pct), true);
                        }
                    }
                }
            } finally {
                r.close();
            }
        } catch (Exception ignored) {}
    }

    // Registry.ini lives in the user-data directory, in Options.ini's
    // "key = value" form; the engine reads its "Language" key before
    // anything else loads (registry.cpp). Keep every other line the
    // file carries; set only the Language line, deterministically.
    private void syncRegistryLanguage(java.io.File userDir, String token) {
        try {
            if (userDir == null) return;
            java.io.File reg = new java.io.File(userDir, "Registry.ini");
            StringBuilder out = new StringBuilder();
            if (reg.isFile()) {
                java.io.BufferedReader r = new java.io.BufferedReader(
                    new java.io.FileReader(reg));
                String line;
                while ((line = r.readLine()) != null) {
                    String t = line.trim();
                    int eq = t.indexOf('=');
                    String key = eq >= 0 ? t.substring(0, eq).trim() : t;
                    if (key.equalsIgnoreCase("Language")) continue;
                    out.append(line).append("\\n");
                }
                r.close();
            }
            out.append("Language = ").append(token).append("\\n");
            java.io.FileWriter w = new java.io.FileWriter(reg);
            w.write(out.toString());
            w.close();
        } catch (Exception ignored) {}
    }

    @Override
    protected String[] getArguments() {
        String root = SetupActivity.getSavedGamePath(this);
        java.util.ArrayList<String> args = new java.util.ArrayList<>();
        args.add("-fullscreen");
        args.add("-root");
        args.add(root == null ? "" : root);
        java.io.File odir = overlayDir();
        if (odir != null
                && new java.io.File(odir, ".rfx-overlay-version").isFile()) {
            args.add("-overlay");
            args.add(odir.getAbsolutePath());
        }
        String token = engineLanguageToken();
        if (!"english".equals(token)) {
            args.add("-language");
            args.add(token);
        }
        return args.toArray(new String[0]);
    }

    private static final String OVERLAY_REV = "3";

    private java.io.File overlayDir() {
        java.io.File base = getExternalFilesDir(null);
        return base == null ? null
            : new java.io.File(base, "rfx-overlay");
    }

    // The fork's own data -- its *Reforged.ini set, cursors, scripts,
    // window files, HUD textures and the Arabic language pack --
    // ships as an overlay directory searched before the install root
    // (PosixMain -overlay). It rides in the APK as assets/rfx-overlay.zip,
    // staged in CI by the fork's own Tools/stage-overlay.sh, and is
    // extracted here, once per overlay key (OVERLAY_REV + the app
    // versionCode, so any new build re-extracts), before it starts.
    // Failure leaves the marker absent, getArguments() then omits
    // -overlay, and the launch degrades -- never worse than no overlay.
    private void ensureOverlay() {
        try {
            java.io.File dir = overlayDir();
            if (dir == null) return;
            String overlayKey = OVERLAY_REV;
            try {
                overlayKey = OVERLAY_REV + "@" + getPackageManager()
                    .getPackageInfo(getPackageName(), 0)
                    .getLongVersionCode();
            } catch (Throwable ignored) { }
            java.io.File marker =
                new java.io.File(dir, ".rfx-overlay-version");
            if (marker.isFile()) {
                java.io.BufferedReader r = new java.io.BufferedReader(
                    new java.io.FileReader(marker));
                String v = r.readLine();
                r.close();
                if (overlayKey.equals(v)) {
                    markGameStage("overlay-ready");
                    return;
                }
            }
            // Clean extract: files dropped from the zip must not
            // linger from an older build.
            deleteRecursively(dir);
            dir.mkdirs();
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
            w.write(overlayKey);
            w.close();
            markGameStage("overlay-ready");
        } catch (Exception ex) {
            markGameStage("overlay-failed");
        }
    }

    private static void deleteRecursively(java.io.File f) {
        if (f == null || !f.exists()) return;
        java.io.File[] kids = f.listFiles();
        if (kids != null) {
            for (java.io.File k : kids) deleteRecursively(k);
        }
        f.delete();
    }

    // The engine reads ZH_USER_DATA_DIR once, before SDL_main runs;
    // the variable must exist before loadLibraries() inside
    // super.onCreate, so it is set first thing here.
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        java.io.File userDir = userDataDir(this);
        migrateLegacyUserData(userDir);
        mLoggingOff = loggingOff(userDir);
        markGameStage("oncreate-enter");
        try {
            if (userDir != null) {
                userDir.mkdirs();
                Os.setenv("ZH_USER_DATA_DIR",
                    userDir.getAbsolutePath(), true);
            }
        } catch (Exception ignored) {}
        applyInterfaceScale(userDir);
        syncRegistryLanguage(userDir, engineLanguageToken());
        // v1.26 law, unchanged: ZH_RENDER_SCALE is NOT set. The scaled
        // path renders the shell broken below 100 (v1.25 device
        // finding); rendering stays clamped to full size until the
        // viewport-scaling fix passes its device gate.
        // The run log (v1.29): the engine's debug channel writes to
        // stderr, which Android discards for app processes; redirect
        // fd 2 to rfxgame-stderr.txt in the app's own folder, rotating
        // the previous run's file aside, unless the owner turned the
        // log off in Settings (the logging_off marker).
        if (!mLoggingOff) {
            try {
                java.io.File errFile = logFile("rfxgame-stderr.txt");
                java.io.File prev = logFile("rfxgame-stderr-prev.txt");
                if (errFile.isFile()) {
                    prev.delete();
                    errFile.renameTo(prev);
                }
                java.io.FileOutputStream errOut =
                    new java.io.FileOutputStream(errFile, false);
                Os.dup2(errOut.getFD(), 2);
                markGameStage("stderr-redirected");
            } catch (Exception e) {
                markGameStage("stderr-redirect-failed");
            }
            try {
                java.io.File stage = logFile("rfxgame-stage.txt");
                if (stage.isFile() && stage.length() > 262144) {
                    stage.delete();
                }
            } catch (Exception ignored) {}
        }
        ensureOverlay();
        super.onCreate(savedInstanceState);
        markGameStage("oncreate-done");
        // Keep the screen on while the game runs. The status and
        // navigation bars are hidden by SDL itself: the engine is
        // launched with -fullscreen (see getArguments), and SDL's
        // fullscreen window is what makes Android hide the bars.
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
        if (mLoggingOff) return;
        try {
            java.io.File f = logFile("rfxgame-stage.txt");
            if (f == null) return;
            java.io.FileWriter w = new java.io.FileWriter(f, true);
            w.write("[javastage] " + stage + "\\n");
            w.close();
        } catch (Exception ignored) {}
    }

    // ------------------------------------------------------------------
    // LAN multicast lock (v1.30, committee appendix): many Wi-Fi
    // drivers drop broadcast frames unless the app holds a
    // MulticastLock, which hides LAN games. The engine's udp.cpp
    // calls this method by name (JNI) with true when a LAN
    // broadcast socket opens and false when it closes, so the lock
    // is held only while the LAN lobby or a LAN match is active.
    // The method name and signature are the contract -- do not
    // rename. (Method body verbatim from the host's
    // GeneralsZHActivity; TAG is this activity's own log tag.)
    // ------------------------------------------------------------------

    private static final String TAG = "RfxGame";

    private WifiManager.MulticastLock lanMulticastLock;

    @SuppressWarnings("unused") // called via JNI
    public synchronized void setLanMulticastLock(boolean held) {
        try {
            if (lanMulticastLock == null) {
                WifiManager wifi = (WifiManager) getApplicationContext().getSystemService(WIFI_SERVICE);
                if (wifi == null) return;
                lanMulticastLock = wifi.createMulticastLock("GeneralsZH-LAN");
                lanMulticastLock.setReferenceCounted(true);
            }
            if (held) {
                lanMulticastLock.acquire();
            } else if (lanMulticastLock.isHeld()) {
                lanMulticastLock.release();
            }
            Log.i(TAG, "LAN multicast lock " + (lanMulticastLock.isHeld() ? "held" : "released"));
        } catch (RuntimeException e) {
            Log.w(TAG, "LAN multicast lock unavailable", e);
        }
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
            android:name=".RfxGameActivity"
            android:exported="false"
            android:screenOrientation="landscape"
            android:process=":rfxgame"
            android:configChanges="orientation|keyboardHidden|keyboard|navigation|screenSize|screenLayout|smallestScreenSize|density|layoutDirection|locale|fontScale|uiMode"
            android:theme="@android:style/Theme.NoTitleBar.Fullscreen" />
    </application>''',
)])

# ---------------- 3) SetupActivity: the run log in Help (v1.29) --------
# The tests page is gone (owner's launcher order, 2026-11-20); its log
# machinery is transplanted here, retargeted at the product: the Help &
# About page gains a Support & Log card that shows and shares the game's
# own run log (RfxGameActivity's stage file + stderr + the engine debug
# log, all in the app's own ZeroHourReforged folder). The frame-result /
# capture / test-recorder sections died with the tests page.
edit(SETUP, [
    # 3a) the card, inside buildHelpSection, before the how-it-works card
    ('''        buildSupportSection(page);

        LinearLayout help = UiKit.card(page);''',
     '''        buildSupportSection(page);

        buildRfxLogSection(page);

        LinearLayout help = UiKit.card(page);'''),
    # 3b) the card builder + log machinery, before tabTitle()
    ('''    private int tabTitle(int tab) {''',
     '''    // Zero Hour Reforged (v1.29): the run log lives in Help & About --
    // the game's own evidence (stage file, stderr, the engine debug
    // log) from the app's own folder, shown and shared from one card.
    // The game writes it on every run (RfxGameActivity); the Settings
    // switch can turn the writing off.
    private String mRfxLogShown;
    private static final String RFX_LOG_FILE = "run-log.txt";

    private void buildRfxLogSection(LinearLayout page) {
        LinearLayout logs = UiKit.card(page);
        UiKit.sectionHeader(logs, R.drawable.ic_gzh_doc,
            getString(R.string.setup_runlog_title), true);
        UiKit.supporting(logs, getString(R.string.setup_runlog_desc));
        UiKit.button(logs, UiKit.BTN_TONAL, R.drawable.ic_gzh_doc,
            getString(R.string.setup_runlog_show), this::onShowRfxLog);
        UiKit.button(logs, UiKit.BTN_OUTLINE, R.drawable.ic_gzh_doc,
            getString(R.string.setup_runlog_share), this::onShareRfxLog);
        UiKit.button(logs, UiKit.BTN_OUTLINE, R.drawable.ic_gzh_doc,
            getString(R.string.setup_runlog_copy), this::onCopyRfxLog);
        if (mRfxLogShown != null) {
            android.widget.TextView lv = new android.widget.TextView(this);
            lv.setText(mRfxLogShown);
            lv.setTextSize(11);
            lv.setTypeface(android.graphics.Typeface.MONOSPACE);
            lv.setTextIsSelectable(true);
            logs.addView(lv);
        }
    }

    private static String rfxTime(long ms) {
        return new java.text.SimpleDateFormat("yyyy/MM/dd HH:mm:ss",
            java.util.Locale.US).format(new java.util.Date(ms));
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

    private static void appendLogFile(StringBuilder sb, String name,
            java.io.File f, boolean tail) {
        sb.append(name).append(": ");
        if (f != null && f.isFile()) {
            sb.append(f.length()).append(" bytes, modified ")
              .append(rfxTime(f.lastModified())).append("\\n");
            sb.append("---- ").append(name).append(" ----\\n");
            sb.append(readTextFileQuietly(f));
            if (tail) {
                sb.append("\\n---- tail of ").append(name)
                  .append(" ----\\n");
                sb.append(readTextTailQuietly(f, 24576));
            }
            sb.append("\\n---- end ").append(name).append(" ----\\n");
        } else {
            sb.append("MISSING\\n");
        }
    }

    private String buildRfxGameLog() {
        StringBuilder sb = new StringBuilder();
        sb.append("Zero Hour Reforged -- run log\\n");
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
        java.io.File root = RfxGameActivity.rfxRoot(this);
        java.io.File userDir = RfxGameActivity.userDataDir(this);
        appendLogFile(sb, "rfxgame-stage.txt", root == null ? null
            : new java.io.File(root, "rfxgame-stage.txt"), false);
        appendLogFile(sb, "rfxgame-stderr.txt", root == null ? null
            : new java.io.File(root, "rfxgame-stderr.txt"), true);
        java.io.File glog = null;
        if (userDir != null) {
            glog = new java.io.File(userDir, "Logs/DebugLogFile.txt");
            if (!glog.isFile()) {
                glog = new java.io.File(userDir, "DebugLogFile.txt");
            }
        }
        appendLogFile(sb, "DebugLogFile.txt", glog, true);
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
                    if (e.getProcessName() == null
                            || !e.getProcessName().endsWith(":rfxgame")) {
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

    private void onShowRfxLog() {
        mRfxLogShown = buildRfxGameLog();
        java.io.File root = RfxGameActivity.rfxRoot(this);
        if (root != null) {
            writeTextFileQuietly(new java.io.File(root, RFX_LOG_FILE),
                mRfxLogShown);
        }
        showTab(TAB_HELP);
    }

    private void onShareRfxLog() {
        String log = buildRfxGameLog();
        java.io.File root = RfxGameActivity.rfxRoot(this);
        if (root != null) {
            writeTextFileQuietly(new java.io.File(root, RFX_LOG_FILE),
                log);
        }
        android.content.Intent send = new android.content.Intent(
            android.content.Intent.ACTION_SEND);
        send.putExtra(android.content.Intent.EXTRA_TEXT, log);
        // Attach a zip of the full evidence files as well: the text
        // above carries only the first 64 KB of each file, so the end
        // of a long session (where the failures live) never survived
        // a text share; the zip carries every byte of every file.
        java.io.File zip = buildRfxLogZip();
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
            getString(R.string.setup_runlog_title)));
    }

    private java.io.File buildRfxLogZip() {
        try {
            java.io.File root = RfxGameActivity.rfxRoot(this);
            java.io.File userDir = RfxGameActivity.userDataDir(this);
            java.util.ArrayList<java.io.File> files =
                new java.util.ArrayList<java.io.File>();
            if (root != null) {
                files.add(new java.io.File(root, "rfxgame-stage.txt"));
                files.add(new java.io.File(root, "rfxgame-stderr.txt"));
                files.add(new java.io.File(root,
                    "rfxgame-stderr-prev.txt"));
            }
            if (userDir != null) {
                java.io.File glog = new java.io.File(userDir,
                    "Logs/DebugLogFile.txt");
                if (!glog.isFile()) {
                    glog = new java.io.File(userDir, "DebugLogFile.txt");
                }
                files.add(glog);
            }
            java.io.File zip = new java.io.File(getCacheDir(),
                "zh-reforged-logs.zip");
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
                "rfx-run-log", buildRfxGameLog()));
        }
        Toast.makeText(this, R.string.setup_runlog_copied,
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

# ---------------- 3s) run-log strings, every locale --------------------
RUNLOG_STRINGS_EN = [
    ('setup_runlog_title', 'Run log'),
    ('setup_runlog_desc', 'The game\u2019s own record of its last runs: the stage file, the engine output and the debug log, all in the app\u2019s own ZeroHourReforged folder. Show it here, or share it when something goes wrong.'),
    ('setup_runlog_show', 'Show the log'),
    ('setup_runlog_share', 'Share the log'),
    ('setup_runlog_copy', 'Copy the log'),
    ('setup_runlog_copied', 'Log copied'),
]
RUNLOG_STRINGS_AR = [
    ('setup_runlog_title', 'سجل التشغيل'),
    ('setup_runlog_desc', 'سجل اللعبة نفسه لآخر تشغيلاتها: ملف المراحل ومخرجات المحرك وسجل التصحيح، كلها في مجلد التطبيق الخاص ZeroHourReforged. اعرضه هنا أو شاركه عند حدوث مشكلة.'),
    ('setup_runlog_show', 'عرض السجل'),
    ('setup_runlog_share', 'مشاركة السجل'),
    ('setup_runlog_copy', 'نسخ السجل'),
    ('setup_runlog_copied', 'نُسخ السجل'),
]


def runlog_escape(s):
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
    if 'name="setup_runlog_title"' in s:
        sys.exit(f'phase3: {strings_xml} already carries setup_runlog_title')
    is_ar = os.path.basename(os.path.dirname(strings_xml)) == 'values-ar'
    block = ''.join(
        f'\n    <string name="{name}">{runlog_escape(text)}</string>'
        for name, text in (RUNLOG_STRINGS_AR if is_ar else RUNLOG_STRINGS_EN))
    s = s.replace(anchor, anchor + block, 1)
    open(strings_xml, 'w', encoding='utf-8').write(s)
    count += 1
if count < 10:
    sys.exit(f'phase3: only {count} locale files carried nav_tab_reforged -- expected 10+')
print(f'run-log strings added to {count} locale files')



# ---------------- 4) Packaging knob for libmainrfx.so ----------------
edit(PACKAGE_SH, [(
    '''    cp "${GX_ENGINE_LIB}" "${JNILIBS}/libmainz60.so"
    echo "Packaging the pure 60-steps engine: libmainz60.so ($(du -h "${GX_ENGINE_LIB}" | cut -f1))"
fi''',
    '''    cp "${GX_ENGINE_LIB}" "${JNILIBS}/libmainz60.so"
    echo "Packaging the pure 60-steps engine: libmainz60.so ($(du -h "${GX_ENGINE_LIB}" | cut -f1))"
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
for gxdead in libEGL_angle.so libGLESv2_angle.so libadrenotools.so libdxvk_d3d8.so libdxvk_d3d9.so libfile_redirect_hook.so libgamespy.so libgsl_alloc_hook.so libhook_impl.so libmain_hook.so libmainrfx.so libopenal.so libSDL3.so libSDL3_image.so libc++_shared.so; do
    rm -f "${JNILIBS}/${gxdead}"
done
rm -rf "${DEFAULT_DRIVER_ASSETS}"
rm -f "${ASSETS}/dxvk.conf"
for gxdead in libEGL_angle.so libGLESv2_angle.so libadrenotools.so libdxvk_d3d8.so libdxvk_d3d9.so libfile_redirect_hook.so libgamespy.so libgsl_alloc_hook.so libhook_impl.so libmain_hook.so libmainrfx.so libopenal.so libSDL3.so libSDL3_image.so libc++_shared.so; do
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


def xml_escape(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace("'", "\\'"))





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
    'gzh_tertiary': '#E59A8F',
    'gzh_tertiary_container': '#4A2C28',
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
        if 'name="nav_tab_reforged"' in line:
            indent = line[:len(line) - len(line.lstrip())]
            lines.insert(idx + 1, indent + '<string name="setup_developer_credit">'
                         + xml_escape(CREDIT_STRINGS[locale]) + '</string>')
            credit_added += 1
            break
    else:
        sys.exit('phase3: no nav_tab_reforged anchor in %s' % strings_xml)
    open(strings_xml, 'w', encoding='utf-8').write('\n'.join(lines))
if credit_added < 10:
    sys.exit('phase3: developer credit added to only %d locales' % credit_added)
print('developer credit string added to %d locale files' % credit_added)

# ---------------- 8) v1.29 launcher rebuild: three destinations --------
# Home / Settings / Help (committee section 1). The Graphics and Tools
# tabs die as destinations -- their cards were the old engine's
# plumbing -- and the Settings tab is the old Interface tab, retitled.
# Dead tab ids (and the retired tests id 7) land on Home: a restored
# session can never face a blank page.
edit(SETUP, [
    # 8a) the bottom nav: five items -> three
    ('''        menu.add(Menu.NONE, TAB_HOME, 0, R.string.nav_tab_home).setIcon(R.drawable.ic_gzh_home);
        menu.add(Menu.NONE, TAB_GRAPHICS, 1, R.string.nav_tab_graphics).setIcon(R.drawable.ic_gzh_display);
        menu.add(Menu.NONE, TAB_INTERFACE, 2, R.string.nav_tab_interface).setIcon(R.drawable.ic_gzh_globe);
        menu.add(Menu.NONE, TAB_TOOLS, 3, R.string.nav_tab_tools).setIcon(R.drawable.ic_gzh_wrench);
        menu.add(Menu.NONE, TAB_HELP, 4, R.string.nav_tab_help).setIcon(R.drawable.ic_gzh_info);''',
     '''        menu.add(Menu.NONE, TAB_HOME, 0, R.string.nav_tab_home).setIcon(R.drawable.ic_gzh_home);
        menu.add(Menu.NONE, TAB_INTERFACE, 1, R.string.nav_tab_settings).setIcon(R.drawable.ic_gzh_sliders);
        menu.add(Menu.NONE, TAB_HELP, 2, R.string.nav_tab_help).setIcon(R.drawable.ic_gzh_info);'''),
    # 8b) the Settings tab's title
    ('''            case TAB_INTERFACE: return R.string.nav_tab_interface;''',
     '''            case TAB_INTERFACE: return R.string.nav_tab_settings;'''),
    # 8c) dead-tab guard at the top of showTab
    ('''    private void showTab(int tab) {
        currentTab = tab;''',
     '''    private void showTab(int tab) {
        // v1.29: the Graphics and Tools tabs and the old Reforged and
        // tests pages no longer exist as destinations; anything that
        // still names them (a restored session, a stale caller) lands
        // on Home instead of a blank page.
        if (tab == TAB_GRAPHICS || tab == TAB_TOOLS
                || tab == TAB_REFORGED || tab == 7) {
            tab = TAB_HOME;
        }
        currentTab = tab;'''),
    # 8d) the Graphics case dies with its cards
    ('''            case TAB_GRAPHICS:
                // Zero Hour Reforged (v1.13): no Simulation Rate
                // section -- the host engines it selected no longer
                // ship, and there is no engine choice anywhere
                // (v1.16: one play engine, libmainz60.so).
                // GeneralsX @tweak Android port 02/10/2026 The upscaler lives in the GLES translator
                // (plain GLES and GLES on ANGLE); under Vulkan it does nothing, so it is not offered.
                if (!RENDER_BACKEND_VULKAN.equals(getRenderBackendChoice())) {
                    buildRenderScaleSection(page);
                }
                buildRenderBackendSection(page);
                // Custom Vulkan driver / dxvk.conf only matter when Vulkan is
                // the selected backend -- the GLES/GLES+ANGLE paths never
                // touch DXVK at all, see
                // Core/Libraries/Source/d3d8gles/CMakeLists.txt.
                if (RENDER_BACKEND_VULKAN.equals(getRenderBackendChoice())) {
                    applyRecommendedDriverIfNeeded();
                    buildCustomDriverSection(page);
                    buildDxvkConfigSection(page);
                }
                break;
''',
     ''),
    # 8e) the Tools case dies (the log viewer lives in Help now)
    ('''            case TAB_TOOLS:
                buildLogsSection(page);
                buildDiagnosticsSection(page);
                break;
''',
     ''),
    # 8f) the Reforged page case dies (its content moves to Home)
    ('''            case TAB_REFORGED:
                buildReforgedPage(page);
                break;
''',
     ''),
    # 8g) the per-tab refreshers of dead features stop running (showTab)
    ('''        }

        refreshStatus();
        refreshGeneralsOnlineStatus();
        loadDxvkConfigIntoEditor();
        refreshDiagnosticsSwitches();
        refreshUpdatesStatus();''',
     '''        }

        refreshStatus();'''),
    # 8i) the same refreshers in onResume, plus the UpdateManager
    # auto-check (named deletion: kill the card alone and the invisible
    # network checks would persist)
    ('''        setRequestedOrientation(android.content.pm.ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED);
        refreshStatus();
        refreshGeneralsOnlineStatus();
        loadDxvkConfigIntoEditor();
        refreshDiagnosticsSwitches();
        refreshUpdatesStatus();
        // Once per process, not on every return to this screen.
        if (!sAutoUpdateCheckedThisProcess && UpdateManager.isAutoCheckEnabled(this)) {
            sAutoUpdateCheckedThisProcess = true;
            runUpdateCheck(false);
        }''',
     '''        setRequestedOrientation(android.content.pm.ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED);
        refreshStatus();'''),
    # 8j) the support popup over the first screen dies (lab behaviour);
    # the Vulkan migration call beside it stays
    ('''        moveOffVulkanOnce();
        maybeShowSupportPopup();''',
     '''        moveOffVulkanOnce();'''),
    # 8h) the app-bar log button opens Help, where the run log lives
    ('''            R.drawable.ic_gzh_doc, getString(R.string.setup_button_view_logs), this::onViewLogs);''',
     '''            R.drawable.ic_gzh_doc, getString(R.string.setup_button_view_logs), () -> showTab(TAB_HELP));'''),
])

# ---------------- 8s) the Settings tab string --------------------------
SETTINGS_STRINGS_EN = [
    ('nav_tab_settings', 'Settings'),
]
SETTINGS_STRINGS_AR = [
    ('nav_tab_settings', 'الإعدادات'),
]
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
    if 'name="nav_tab_settings"' in s:
        sys.exit(f'phase3: {strings_xml} already carries nav_tab_settings')
    is_ar = os.path.basename(os.path.dirname(strings_xml)) == 'values-ar'
    block = ''.join(
        f'\n    <string name="{name}">{runlog_escape(text)}</string>'
        for name, text in (SETTINGS_STRINGS_AR if is_ar else SETTINGS_STRINGS_EN))
    s = s.replace(anchor, anchor + block, 1)
    open(strings_xml, 'w', encoding='utf-8').write(s)
    count += 1
if count < 10:
    sys.exit(f'phase3: only {count} locale files carried nav_tab_reforged -- expected 10+')
print(f'settings strings added to {count} locale files')


# ---------------- 9) v1.29 launcher rebuild: Home --------------
# The Reforged page's job moves into Home itself (committee
# section 1): hero, state-aware Play, the folder card, two
# shortcut rows, credit + version. The Mods row, the old page's
# entry row, the GeneralsOnline card and the Updates card die.
edit(SETUP, [
    # 9a) the hero: emblem + title at the top of Home
    ('''        final boolean generals = false;
        LinearLayout game = UiKit.card(page);''',
     '''        final boolean generals = false;
        // v1.29 hero: the launcher's own emblem, then the game's
        // name -- no fabricated art, nothing read from the game
        // folder (absent on a first run).
        android.widget.ImageView heroIcon = new android.widget.ImageView(this);
        heroIcon.setImageResource(R.mipmap.ic_launcher_foreground);
        int heroSize = UiKit.dp(this, 66);
        LinearLayout.LayoutParams heroLp =
            new LinearLayout.LayoutParams(heroSize, heroSize);
        heroLp.gravity = android.view.Gravity.CENTER_HORIZONTAL;
        heroIcon.setLayoutParams(heroLp);
        page.addView(heroIcon);
        TextView heroTitle = UiKit.body(page, getString(R.string.app_name));
        heroTitle.setGravity(android.view.Gravity.CENTER);
        heroTitle.setTextSize(20);
        LinearLayout game = UiKit.card(page);'''),
    # 9b) the Mods row dies (owner ruling D2: no mods this version)
    ('''        // GeneralsX @feature Android port 18/10/2026 The Mods screen (ModManagerActivity): which mods
        // the next game starts with, and in what order.
        // GeneralsX @tweak Android port 19/10/2026 Installed but all off is not "No mods" (owner read
        // it as the mods being gone after an update).
        java.util.List<ModManager.Mod> installedMods = ModManager.listMods(this);
        int modsOn = 0;
        for (ModManager.Mod mod : installedMods) {
            if (mod.enabled) {
                modsOn++;
            }
        }
        UiKit.listRow(game, R.drawable.ic_gzh_folder, getString(R.string.mods_title),
            installedMods.isEmpty() ? getString(R.string.mods_home_none)
                : modsOn == 0 ? getString(R.string.mods_home_all_off, installedMods.size())
                : getString(R.string.mods_home_enabled, modsOn),
            () -> startActivityForResult(new Intent(this, ModManagerActivity.class), REQUEST_MODS));''',
     ''),
    # 9c) the old page's entry row dies (Home IS the page now)
    ('''        // GeneralsX @feature Zero Hour Reforged 12/11/2026 (v1.11) The entry
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
            () -> showTab(TAB_REFORGED));''',
     ''),
    # 9d) Play states its reason instead of bouncing silently
    ('''        // The one thing this app exists to do, as the first thing on it.
        UiKit.button(page, UiKit.BTN_PRIMARY, R.drawable.ic_gzh_play,
            getString(R.string.setup_button_launch_game), this::onLaunchGame);''',
     '''        // The one thing this app exists to do, as the first thing on it.
        // v1.29: no silent bounce -- with no folder, or a folder
        // whose game files are missing, Play disables and the line
        // under it says why (the folder card below shows the rest).
        com.google.android.material.button.MaterialButton playButton =
            UiKit.button(page, UiKit.BTN_PRIMARY, R.drawable.ic_gzh_play,
                getString(R.string.setup_button_launch_game), this::onLaunchGame);
        String homeGamePath = getSavedGamePath();
        boolean homeFolderValid = homeGamePath != null
            && isValidGameFolder(new File(homeGamePath), getSelectedGame(this));
        if (!homeFolderValid) {
            playButton.setEnabled(false);
            UiKit.supporting(page, getString(homeGamePath == null
                ? R.string.setup_home_play_needs_folder
                : R.string.setup_home_play_folder_invalid));
        }'''),
    # 9e) GeneralsOnline + Updates cards die; two shortcut rows and
    # the version line close the page instead
    ('''        // GeneralsX @bugfix Android port 01/08/2026 kept above the advanced
        // settings -- signing into GeneralsOnline is a primary action most
        // people want right after picking their game folder, not something to
        // bury under settings most players never touch.
        buildGeneralsOnlineSection(page);
        buildUpdatesSection(page);''',
     '''        // v1.29: the only shortcuts Home carries -- language and
        // the road to every other setting.
        LinearLayout shortcuts = UiKit.card(page);
        UiKit.listRow(shortcuts, R.drawable.ic_gzh_globe,
            getString(R.string.setup_card_language),
            getString(R.string.setup_home_shortcut_language_desc),
            () -> showTab(TAB_INTERFACE));
        UiKit.listRow(shortcuts, R.drawable.ic_gzh_sliders,
            getString(R.string.setup_card_control_scheme),
            getString(R.string.setup_home_shortcut_controls_desc),
            () -> showTab(TAB_INTERFACE));
        TextView versionLine = UiKit.supporting(page, versionLabel());
        versionLine.setGravity(android.view.Gravity.CENTER);'''),
])

# ---------------- 9s) Home strings -------------------------------
HOME_STRINGS_EN = [
    ('setup_home_play_needs_folder', 'Pick the game folder first (below), then play.'),
    ('setup_home_play_folder_invalid', 'This folder is missing the game files -- pick the full game folder below.'),
    ('setup_home_shortcut_language_desc', 'Launcher language and the game\u2019s text language'),
    ('setup_home_shortcut_controls_desc', 'Controls, graphics, size, theme and logs'),
]
HOME_STRINGS_AR = [
    ('setup_home_play_needs_folder', 'اختر مجلد اللعبة أولًا (بالأسفل)، ثم العب.'),
    ('setup_home_play_folder_invalid', 'هالمجلد ناقصه ملفات اللعبة -- اختر مجلد اللعبة الكامل بالأسفل.'),
    ('setup_home_shortcut_language_desc', 'لغة المشغّل ولغة نصوص اللعبة'),
    ('setup_home_shortcut_controls_desc', 'التحكم والرسومات والحجم والمظهر والسجل'),
]
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
    if 'name="setup_home_play_needs_folder"' in s:
        sys.exit(f'phase3: {strings_xml} already carries setup_home_play_needs_folder')
    is_ar = os.path.basename(os.path.dirname(strings_xml)) == 'values-ar'
    block = ''.join(
        f'\n    <string name="{name}">{runlog_escape(text)}</string>'
        for name, text in (HOME_STRINGS_AR if is_ar else HOME_STRINGS_EN))
    s = s.replace(anchor, anchor + block, 1)
    open(strings_xml, 'w', encoding='utf-8').write(s)
    count += 1
if count < 10:
    sys.exit(f'phase3: only {count} locale files carried nav_tab_reforged -- expected 10+')
print(f'home strings added to {count} locale files')

# ---------------- 9f) the Mods request code dies with its row --------
edit(SETUP, [
    ('''    private static final int REQUEST_MODS = 1004;
''',
     ''),
    ('''        if (requestCode == REQUEST_MODS) {
            // Back on Home: the mods switched on may have changed.
            showTab(currentTab);
            return;
        }
''',
     ''),
])


# ---------------- 10) v1.29 blockers + migrations -------------------
# Committee 5.1 (control_scheme must not lie), 5.2 + 5.4 (one-time
# migrations), the Options.ini re-point (the interface-size slider
# finally writes the file our engine reads), and write-on-release
# sliders (one interaction rule for the whole Settings page).
edit(SETUP, [
    # 10a) readControlScheme: army_buttons defaults ON, as the engine reads it
    ('''    private static boolean[] readControlScheme(File file) {
        boolean[] state = new boolean[CONTROL_SCHEME_KEYS.length];''',
     '''    private static boolean[] readControlScheme(File file) {
        boolean[] state = new boolean[CONTROL_SCHEME_KEYS.length];
        // v1.29 (committee 5.1): army_buttons defaults ON -- the
        // engine (GXControlScheme.h) treats an absent key as 1, so
        // the UI reads it the same way or it reports the opposite
        // of what the game will do.
        state[1] = true;'''),
    # 10b) the stale comment on the missing-file path
    ('''            // No file yet: the Classic scheme.''',
     '''            // No file yet: the defaults above.'''),
    # 10c) writeControlScheme: never delete -- all-off must be writable
    ('''    private static void writeControlScheme(File file, boolean[] state) {
        if (controlSchemeIndex(state) == 0) {
            file.delete();
            return;
        }''',
     '''    private static void writeControlScheme(File file, boolean[] state) {
        // v1.29 (committee 5.1): never delete the file -- an absent
        // army_buttons key means ON to the engine, so "all off" has
        // to be written out explicitly or the switches lie.'''),
    # 10d) the section header no longer carries a preset label
    ('''        TextView status = UiKit.sectionHeader(content, R.drawable.ic_gzh_sliders,
            getString(R.string.setup_card_control_scheme), true);''',
     '''        UiKit.sectionHeader(content, R.drawable.ic_gzh_sliders,
            getString(R.string.setup_card_control_scheme), true);'''),
    # 10e) the preset segmented control dies (redundant with the
    # switches, and its none=Classic definition forced the delete bug)
    ('''        CharSequence[] labels = new CharSequence[] {
            getString(R.string.setup_control_scheme_classic),
            getString(R.string.setup_control_scheme_tactical),
            getString(R.string.setup_control_scheme_custom)
        };
        final int[] descs = new int[] {
            R.string.setup_control_scheme_classic_desc,
            R.string.setup_control_scheme_tactical_desc,
            R.string.setup_control_scheme_custom_desc
        };
        final int current = controlSchemeIndex(state);
        status.setText(labels[current]);
        final com.google.android.material.button.MaterialButtonToggleGroup[] group =
            new com.google.android.material.button.MaterialButtonToggleGroup[1];
        final TextView[] desc = new TextView[1];
        final SwitchCompat[] switches = new SwitchCompat[CONTROL_SCHEME_KEYS.length];

        group[0] = UiKit.segmented(content, labels, current, index -> {
            if (controlSchemeUpdating) {
                return;
            }
            status.setText(labels[index]);
            desc[0].setText(descs[index]);
            if (index == 2) {
                return;
            }
            controlSchemeUpdating = true;
            for (int i = 0; i < switches.length; i++) {
                state[i] = index == 1;
                switches[i].setChecked(state[i]);
            }
            controlSchemeUpdating = false;
            writeControlScheme(file, state);
        });
        desc[0] = UiKit.supporting(content, getString(descs[current]));''',
     '''        final SwitchCompat[] switches = new SwitchCompat[CONTROL_SCHEME_KEYS.length];'''),
    # 10f) the switches write for themselves now
    ('''            switches[i].setOnCheckedChangeListener((button, checked) -> {
                if (controlSchemeUpdating) {
                    return;
                }
                state[option] = checked;
                writeControlScheme(file, state);
                int index = controlSchemeIndex(state);
                controlSchemeUpdating = true;
                group[0].check(group[0].getChildAt(index).getId());
                controlSchemeUpdating = false;
                status.setText(labels[index]);
                desc[0].setText(descs[index]);
            });''',
     '''            switches[i].setOnCheckedChangeListener((button, checked) -> {
                state[option] = checked;
                writeControlScheme(file, state);
            });'''),
    # 10g) Options.ini lives in OUR engine's user folder now
    ('''    private File optionsIniFile() {
        return new File(userDataDir(this), "Options.ini");
    }''',
     '''    private File optionsIniFile() {
        // v1.29: OUR engine's user folder (the app's own
        // ZeroHourReforged/User) -- the host's userDataDir() names
        // the old engine's shared folder, whose Options.ini our
        // engine never reads. RfxGameActivity owns the path.
        java.io.File dir = RfxGameActivity.userDataDir(this);
        return dir != null ? new File(dir, "Options.ini")
            : new File(getFilesDir(), "Options.ini");
    }'''),
    # 10h) text-size slider: write on release, no Apply button
    ('''        UiKit.button(content, UiKit.BTN_PRIMARY, R.drawable.ic_gzh_check,
            getString(R.string.setup_button_apply_text_size), () -> {
                writeUiScalePercent((int) uiScaleSlider.getValue());
                Toast.makeText(this, R.string.setup_toast_text_size_saved, Toast.LENGTH_LONG).show();
            });''',
     '''        // v1.29: sliders write on release -- every other setting
        // on this page applies instantly, so no Apply buttons.
        uiScaleSlider.addOnSliderTouchListener(new Slider.OnSliderTouchListener() {
            @Override public void onStartTrackingTouch(Slider slider) {}
            @Override public void onStopTrackingTouch(Slider slider) {
                writeUiScalePercent((int) slider.getValue());
            }
        });'''),
    # 10i) interface-size slider: same rule
    ('''        UiKit.button(content, UiKit.BTN_PRIMARY, R.drawable.ic_gzh_check,
            getString(R.string.setup_button_apply_interface_scale), () -> {
                writeInterfaceScalePercent((int) interfaceScaleSlider.getValue());
                Toast.makeText(this, R.string.setup_toast_render_scale_saved, Toast.LENGTH_LONG).show();
            });''',
     '''        interfaceScaleSlider.addOnSliderTouchListener(new Slider.OnSliderTouchListener() {
            @Override public void onStartTrackingTouch(Slider slider) {}
            @Override public void onStopTrackingTouch(Slider slider) {
                writeInterfaceScalePercent((int) slider.getValue());
            }
        });'''),
    # 10j) the migrations run once, from onCreate
    ('''        moveOffVulkanOnce();
    }''',
     '''        moveOffVulkanOnce();
        applyV129Migrations();
    }'''),
    # 10k) the migration block itself, before tabTitle()
    ('''    private int tabTitle(int tab) {''',
     '''    // v1.29 one-time migrations (committee 5.2/5.4), run once on
    // the first launch of this version and never again: the retired
    // render-scale pref goes (a stale 75 would silently break the
    // picture the day the engine knob returns), the diagnostic
    // marker files stranded in the game folder go (their switches
    // are gone -- an enabled marker with no way to turn it off is
    // a trap), the dropped GeneralsOnline session is cleared, and
    // any engine the old updater downloaded into files/update/ is
    // deleted -- it could otherwise load instead of this app's own.
    private void applyV129Migrations() {
        android.content.SharedPreferences prefs =
            getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        if (prefs.getBoolean("v129_migrated", false)) {
            return;
        }
        prefs.edit().remove("rfx_render_scale")
            .putBoolean("v129_migrated", true).apply();
        String gamePath = getSavedGamePath();
        if (gamePath != null) {
            String[] markers = {
                "gx_trace.txt", "gx_perf.txt", "gx_gles_gputimer.txt",
                "gx_audio_trace.txt", "gx_net_trace.txt",
                "gx_touch_debug.txt", "gx_testrec.txt", "dxvk_hud.txt",
                "dxvk_validation.txt", "dxvk_verbose_log.txt"
            };
            for (String m : markers) {
                new File(gamePath, m).delete();
            }
        }
        getSharedPreferences("generalsonline_session", MODE_PRIVATE)
            .edit().clear().apply();
        new File(getFilesDir(), "generalsonline_session.txt").delete();
        deleteRecursive(new File(getFilesDir(), "update"));
    }

    private int tabTitle(int tab) {'''),
])

# ---------------- 11) v1.29 Settings + Help additions ---------------
# The graphics preset (owner order 19:57, section 330.1: the
# engine's own StaticGameLOD key -- one tap in the launcher, the
# whole picture set before entering the game), the Logs card (the
# run-log switch, D3: Settings), the Help troubleshooting card with
# the salvaged LAN info row, and the minimal own update banner (D1).
edit(SETUP, [
    # 11a) the Settings page order: Language, Controls, Appearance
    # (theme + scales + preset), Logs
    ('''            case TAB_INTERFACE:
                buildLanguageSection(page);
                buildThemeSection(page);
                buildUiScaleSection(page);
                buildInterfaceScaleSection(page);
                buildControlSchemeSection(page);
                break;''',
     '''            case TAB_INTERFACE:
                buildLanguageSection(page);
                buildControlSchemeSection(page);
                buildThemeSection(page);
                buildUiScaleSection(page);
                buildInterfaceScaleSection(page);
                buildGfxPresetSection(page);
                buildLogSettingsSection(page);
                break;'''),
    # 11b) Help: the remote-fed support card is replaced by our own
    # troubleshooting card (the log card already sits after it)
    ('''        buildSupportSection(page);

        buildRfxLogSection(page);''',
     '''        buildTroubleshootSection(page);

        buildRfxLogSection(page);'''),
    # 11c) the new builders, before tabTitle()
    ('''    private int tabTitle(int tab) {''',
     '''    // v1.29: the graphics preset. One segmented choice writes the
    // engine's own StaticGameLOD key into our Options.ini -- the
    // same bundle the in-game Options menu's detail levels set
    // (GameLOD presets: textures, shadows, particles, effects),
    // chosen here so the player never has to open the game's
    // options. Until the player picks one, the engine's own
    // hardware pick stands (IdealStaticGameLOD, which it writes
    // back after a run); a Custom value means the game's options
    // were fine-tuned by hand and picking a level replaces it.
    private static final String[] GFX_PRESET_KEYS = { "Low", "Medium", "High", "Ultra" };

    private void buildGfxPresetSection(LinearLayout root) {
        LinearLayout content = UiKit.card(root);
        UiKit.sectionHeader(content, R.drawable.ic_gzh_display,
            getString(R.string.setup_card_gfx_preset), true);
        java.util.Map<String, String> ini = readKeyValueFile(optionsIniFile());
        String current = ini.get("StaticGameLOD");
        int checked = 1;
        boolean custom = false;
        boolean explicit = false;
        if (current != null) {
            for (int i = 0; i < GFX_PRESET_KEYS.length; i++) {
                if (GFX_PRESET_KEYS[i].equalsIgnoreCase(current.trim())) {
                    checked = i;
                    explicit = true;
                }
            }
            custom = !explicit;
        }
        if (!explicit && !custom) {
            String ideal = ini.get("IdealStaticGameLOD");
            if (ideal != null) {
                for (int i = 0; i < GFX_PRESET_KEYS.length; i++) {
                    if (GFX_PRESET_KEYS[i].equalsIgnoreCase(ideal.trim())) {
                        checked = i;
                    }
                }
            }
        }
        CharSequence[] labels = new CharSequence[] {
            getString(R.string.setup_gfx_low),
            getString(R.string.setup_gfx_medium),
            getString(R.string.setup_gfx_high),
            getString(R.string.setup_gfx_ultra)
        };
        UiKit.segmented(content, labels, checked, index ->
            writeGfxPreset(GFX_PRESET_KEYS[index]));
        if (custom) {
            UiKit.helpText(content, getString(R.string.setup_gfx_custom_note));
        }
        // v1.30 (committee Q5): honest read-back. The engine's
        // ClassicGraphics defaults ON when the key is absent, and
        // while it is on, the post chain stays off whatever the
        // preset says -- so the note shows exactly while classic
        // is the effective state, and only an explicit "no" (the
        // two-key write above, or unticking Classic in-game)
        // hides it.
        String classic = ini.get("ClassicGraphics");
        if (classic == null || !"no".equalsIgnoreCase(classic.trim())) {
            UiKit.helpText(content, getString(R.string.setup_gfx_classic_on));
        }
        UiKit.helpText(content, getString(R.string.setup_gfx_preset_help));
    }

    private void writeGfxPreset(String level) {
        File file = optionsIniFile();
        java.util.LinkedHashMap<String, String> prefs;
        if (!file.isFile()) {
            prefs = new java.util.LinkedHashMap<>(readKeyValueFile(defaultOptionsIniFile()));
        } else {
            prefs = new java.util.LinkedHashMap<>(readKeyValueFile(file));
        }
        prefs.put("StaticGameLOD", level);
        // v1.30 (committee Q5): High and Ultra MEAN the Reforged
        // look, and the engine's ClassicGraphics default (on)
        // forces the post chain off and the lighting classic no
        // matter what the LOD says -- so a High/Ultra tap clears
        // it in the same write pass. Medium/Low never touch the
        // key, and "yes" is never written by any path.
        if ("High".equals(level) || "Ultra".equals(level)) {
            prefs.put("ClassicGraphics", "no");
        }
        writeKeyValueFile(file, prefs);
    }

    // v1.30 (committee Q5): one-time migration for installs that
    // already sit at High/Ultra from before the two-key preset
    // write existed -- their preset must mean what it says, so
    // ClassicGraphics is cleared once. Medium/Low installs are
    // never touched and "yes" is never written. The marker is set
    // regardless of outcome, so the check runs exactly once.
    private void applyV130ClassicMigration() {
        android.content.SharedPreferences prefs =
            getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        if (prefs.getBoolean("v130_classic_migrated", false)) {
            return;
        }
        try {
            File file = optionsIniFile();
            if (file.isFile()) {
                java.util.LinkedHashMap<String, String> ini =
                    new java.util.LinkedHashMap<>(readKeyValueFile(file));
                String lod = ini.get("StaticGameLOD");
                String classic = ini.get("ClassicGraphics");
                boolean highTier = lod != null
                    && ("High".equalsIgnoreCase(lod.trim())
                        || "Ultra".equalsIgnoreCase(lod.trim()));
                boolean classicOff = classic != null
                    && "no".equalsIgnoreCase(classic.trim());
                if (highTier && !classicOff) {
                    ini.put("ClassicGraphics", "no");
                    writeKeyValueFile(file, ini);
                }
            }
        } catch (Exception ignored) {}
        prefs.edit().putBoolean("v130_classic_migrated", true).apply();
    }

    // v1.29: the Logs card. The switch is the logging_off marker in
    // the game's own user folder -- absent means ON -- the exact
    // file RfxGameActivity reads before it writes a single byte of
    // log (committee 5.3; the marker moved with the data when the
    // owner ordered the app's own external folder).
    private void buildLogSettingsSection(LinearLayout root) {
        LinearLayout content = UiKit.card(root);
        UiKit.sectionHeader(content, R.drawable.ic_gzh_doc,
            getString(R.string.setup_card_logs), true);
        SwitchCompat logging = UiKit.switchRow(content,
            getString(R.string.setup_switch_logging),
            getString(R.string.setup_switch_logging_desc));
        java.io.File userDir = RfxGameActivity.userDataDir(this);
        final java.io.File marker = userDir == null ? null
            : new java.io.File(userDir, "logging_off");
        logging.setChecked(marker == null || !marker.isFile());
        logging.setOnCheckedChangeListener((button, checked) -> {
            if (marker == null) {
                return;
            }
            if (checked) {
                marker.delete();
            } else {
                try {
                    new java.io.FileOutputStream(marker).close();
                } catch (Exception ignored) {}
            }
        });
        UiKit.listRow(content, R.drawable.ic_gzh_doc,
            getString(R.string.setup_log_view_row),
            getString(R.string.setup_log_view_row_desc),
            () -> showTab(TAB_HELP));
    }

    // v1.29: Help's install + troubleshooting card, with the one
    // LAN diagnostic the product ships: what network this phone is
    // on and its local address -- what a WiFi match needs to know.
    private void buildTroubleshootSection(LinearLayout page) {
        LinearLayout card = UiKit.card(page);
        UiKit.sectionHeader(card, R.drawable.ic_gzh_info,
            getString(R.string.setup_trouble_title), true);
        UiKit.supporting(card, getString(R.string.setup_trouble_steps));
        UiKit.listRow(card, R.drawable.ic_gzh_globe,
            getString(R.string.setup_lan_row), lanInfoLine(), null);
    }

    private String lanInfoLine() {
        String transport = "-";
        String address = null;
        try {
            android.net.ConnectivityManager cm =
                (android.net.ConnectivityManager)
                    getSystemService(CONNECTIVITY_SERVICE);
            android.net.Network net = cm == null ? null
                : cm.getActiveNetwork();
            android.net.NetworkCapabilities caps = net == null ? null
                : cm.getNetworkCapabilities(net);
            if (caps != null) {
                if (caps.hasTransport(
                        android.net.NetworkCapabilities.TRANSPORT_WIFI)) {
                    transport = "Wi-Fi";
                } else if (caps.hasTransport(
                        android.net.NetworkCapabilities.TRANSPORT_CELLULAR)) {
                    transport = "Mobile";
                } else if (caps.hasTransport(
                        android.net.NetworkCapabilities.TRANSPORT_ETHERNET)) {
                    transport = "Ethernet";
                }
            }
            java.util.Enumeration<java.net.NetworkInterface> ifs =
                java.net.NetworkInterface.getNetworkInterfaces();
            while (ifs != null && ifs.hasMoreElements() && address == null) {
                java.util.Enumeration<java.net.InetAddress> addrs =
                    ifs.nextElement().getInetAddresses();
                while (addrs.hasMoreElements()) {
                    java.net.InetAddress a = addrs.nextElement();
                    if (!a.isLoopbackAddress()
                            && a instanceof java.net.Inet4Address) {
                        address = a.getHostAddress();
                        break;
                    }
                }
            }
        } catch (Exception ignored) {}
        return address == null ? transport
            : transport + " - " + address;
    }

    private int tabTitle(int tab) {'''),
])

# ---------------- 11s) preset / logs / help strings -----------------
PRODUCT_STRINGS_EN = [
    ('setup_card_gfx_preset', 'Graphics'),
    ('setup_gfx_low', 'Weak'),
    ('setup_gfx_medium', 'Medium'),
    ('setup_gfx_high', 'Strong'),
    ('setup_gfx_ultra', 'Ultra'),
    ('setup_gfx_custom_note', 'Custom -- fine-tuned in the game\u2019s own options. Picking a level here replaces it.'),
    ('setup_gfx_preset_help', 'One choice for the whole picture -- textures, shadows, particles and effects -- set here so you never have to open the game\u2019s options. Applies from the next launch. Until you pick, the game chooses for your phone.'),
    ('setup_gfx_classic_on', 'Classic graphics are on -- post-processing effects are off.'),
    ('setup_card_logs', 'Logs'),
    ('setup_switch_logging', 'Run log'),
    ('setup_switch_logging_desc', 'Records every game run automatically (stage file and engine output) in the app\u2019s own folder, so a problem can be shared and diagnosed. Off stops the recording; logs already written stay.'),
    ('setup_log_view_row', 'View the run log'),
    ('setup_log_view_row_desc', 'In Help & About, with share and copy'),
    ('setup_trouble_title', 'Install & troubleshooting'),
    ('setup_trouble_steps', '1. Copy the whole Zero Hour folder from a PC (about 2-3 GB, with its Data folder inside) onto this phone, for example into Download.\\n2. On Home, tap Select Game Folder and pick that folder.\\n3. If the game will not start, open the run log below and share it.'),
    ('setup_lan_row', 'Local network'),
    ('setup_update_available', 'Update available: %1$s'),
    ('setup_update_open', 'Open the download page'),
]
PRODUCT_STRINGS_AR = [
    ('setup_card_gfx_preset', 'الرسومات'),
    ('setup_gfx_low', 'ضعيف'),
    ('setup_gfx_medium', 'متوسط'),
    ('setup_gfx_high', 'قوي'),
    ('setup_gfx_ultra', 'خارق'),
    ('setup_gfx_custom_note', 'مخصص -- مضبوط بدقة من إعدادات اللعبة نفسها. اختيار مستوى من هنا يستبدله.'),
    ('setup_gfx_preset_help', 'خيار واحد للصورة كلها -- الخامات والظلال والجسيمات والمؤثرات -- اضبطه هنا حتى لا تحتاج فتح إعدادات اللعبة أبدًا. يسري من التشغيل القادم. وحتى تختار، اللعبة تختار ما يناسب هاتفك.'),
    ('setup_gfx_classic_on', 'الرسومات الكلاسيكية مفعّلة -- مؤثرات ما بعد المعالجة متوقفة'),
    ('setup_card_logs', 'السجل'),
    ('setup_switch_logging', 'سجل التشغيل'),
    ('setup_switch_logging_desc', 'يسجّل كل تشغيل للعبة تلقائيًا (ملف المراحل ومخرجات المحرك) في مجلد التطبيق الخاص، حتى تُشارك أي مشكلة وتُشخَّص. الإيقاف يوقف التسجيل؛ والسجلات المكتوبة تبقى.'),
    ('setup_log_view_row', 'عرض سجل التشغيل'),
    ('setup_log_view_row_desc', 'في المساعدة وحول، مع المشاركة والنسخ'),
    ('setup_trouble_title', 'التثبيت وحل المشاكل'),
    ('setup_trouble_steps', '1. انسخ مجلد Zero Hour كاملًا من كمبيوتر (نحو 2-3 غيغابايت، وبداخله مجلد Data) إلى هذا الهاتف، مثلًا داخل التنزيلات.\\n2. من الرئيسية، اضغط «اختيار مجلد اللعبة» واختر ذلك المجلد.\\n3. إذا لم تعمل اللعبة، افتح سجل التشغيل بالأسفل وشاركه.'),
    ('setup_lan_row', 'الشبكة المحلية'),
    ('setup_update_available', 'يوجد تحديث: %1$s'),
    ('setup_update_open', 'فتح صفحة التنزيل'),
]
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
    if 'name="setup_card_gfx_preset"' in s:
        sys.exit(f'phase3: {strings_xml} already carries setup_card_gfx_preset')
    # v1.29.1 repair (run #51): the host already ships setup_switch_logging
    # (+_desc) for its own log switch; appending ours duplicated the keys
    # and aapt mergeReleaseResources failed in every locale. Drop the
    # host's entries first -- our switch, our text.
    for dup_key in ('setup_switch_logging', 'setup_switch_logging_desc'):
        s = re.sub(r'\n[ \t]*<string name="' + dup_key + r'">.*?</string>', '', s, count=1)
    is_ar = os.path.basename(os.path.dirname(strings_xml)) == 'values-ar'
    block = ''.join(
        f'\n    <string name="{name}">{runlog_escape(text)}</string>'
        for name, text in (PRODUCT_STRINGS_AR if is_ar else PRODUCT_STRINGS_EN))
    s = s.replace(anchor, anchor + block, 1)
    open(strings_xml, 'w', encoding='utf-8').write(s)
    count += 1
if count < 10:
    sys.exit(f'phase3: only {count} locale files carried nav_tab_reforged -- expected 10+')
print(f'product strings added to {count} locale files')

# ---------------- 11d) the minimal own update banner (D1) -----------
# Once a day the launcher asks our own repo for its latest release
# and caches the tag; Home shows a small dismissible banner when
# that tag is newer than the running build. Fail-silent throughout:
# no network, no banner, no error -- the game never waits on it.
edit(SETUP, [
    ('''        TextView heroTitle = UiKit.body(page, getString(R.string.app_name));
        heroTitle.setGravity(android.view.Gravity.CENTER);
        heroTitle.setTextSize(20);''',
     '''        TextView heroTitle = UiKit.body(page, getString(R.string.app_name));
        heroTitle.setGravity(android.view.Gravity.CENTER);
        heroTitle.setTextSize(20);
        maybeShowUpdateBanner(page);'''),
    ('''        applyV129Migrations();
    }''',
     '''        applyV129Migrations();
        applyV130ClassicMigration();
        checkForUpdateAsync();
    }'''),
    ('''    private int tabTitle(int tab) {''',
     '''    // v1.29 (D1): our own update signal -- the repo's latest
    // release tag, cached in prefs, checked at most once a day.
    private void checkForUpdateAsync() {
        final android.content.SharedPreferences prefs =
            getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        long last = prefs.getLong("v129_update_checked_at", 0);
        if (System.currentTimeMillis() - last < 24L * 3600L * 1000L) {
            return;
        }
        new Thread(() -> {
            try {
                java.net.HttpURLConnection conn = (java.net.HttpURLConnection)
                    new java.net.URL("https://api.github.com/repos/louay0khaled/"
                        + "zero-hour-reforged-android-mod/releases/latest")
                        .openConnection();
                conn.setConnectTimeout(8000);
                conn.setReadTimeout(8000);
                conn.setRequestProperty("User-Agent", "ZeroHourReforged-Launcher");
                java.io.InputStream in = conn.getInputStream();
                java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
                byte[] buf = new byte[4096];
                int n;
                while ((n = in.read(buf)) > 0) {
                    bos.write(buf, 0, n);
                }
                in.close();
                String body = bos.toString("UTF-8");
                int i = body.indexOf("tag_name");
                int q1 = i < 0 ? -1 : body.indexOf('"', body.indexOf(':', i));
                int q2 = q1 < 0 ? -1 : body.indexOf('"', q1 + 1);
                if (q2 > q1) {
                    String tag = body.substring(q1 + 1, q2);
                    if (tag.startsWith("v")) {
                        tag = tag.substring(1);
                    }
                    prefs.edit().putString("v129_latest_release", tag)
                        .putLong("v129_update_checked_at",
                            System.currentTimeMillis()).apply();
                }
            } catch (Exception ignored) {}
        }).start();
    }

    private static int versionPart(String s, int index) {
        int part = -1;
        int value = 0;
        boolean inNumber = false;
        for (int i = 0; i <= s.length(); i++) {
            char c = i < s.length() ? s.charAt(i) : '.';
            if (c >= '0' && c <= '9') {
                value = value * 10 + (c - '0');
                inNumber = true;
            } else if (inNumber) {
                part++;
                if (part == index) {
                    return value;
                }
                value = 0;
                inNumber = false;
            }
        }
        return 0;
    }

    private static boolean isNewerVersion(String latest, String current) {
        for (int i = 0; i < 4; i++) {
            int x = versionPart(latest, i);
            int y = versionPart(current, i);
            if (x != y) {
                return x > y;
            }
        }
        return false;
    }

    private void maybeShowUpdateBanner(LinearLayout page) {
        android.content.SharedPreferences prefs =
            getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        String latest = prefs.getString("v129_latest_release", null);
        if (latest == null || latest.equals(
                prefs.getString("v129_update_dismissed", ""))) {
            return;
        }
        String current = null;
        try {
            current = getPackageManager()
                .getPackageInfo(getPackageName(), 0).versionName;
        } catch (Exception ignored) {}
        if (current == null || !isNewerVersion(latest, current)) {
            return;
        }
        LinearLayout banner = UiKit.card(page);
        UiKit.supporting(banner,
            getString(R.string.setup_update_available, latest));
        UiKit.button(banner, UiKit.BTN_TONAL, R.drawable.ic_gzh_check,
            getString(R.string.setup_update_open), () -> {
                try {
                    startActivity(new android.content.Intent(
                        android.content.Intent.ACTION_VIEW,
                        android.net.Uri.parse("https://github.com/louay0khaled/"
                            + "zero-hour-reforged-android-mod/releases/latest")));
                } catch (Exception ignored) {}
            });
        UiKit.button(banner, UiKit.BTN_OUTLINE, R.drawable.ic_gzh_check,
            getString(R.string.setup_update_later), () -> {
                prefs.edit().putString("v129_update_dismissed", latest).apply();
                showTab(TAB_HOME);
            });
    }

    private int tabTitle(int tab) {'''),
])

# ---------------- 11t) the banner's dismiss string ------------------
UPDATE_STRINGS_EN = [
    ('setup_update_later', 'Later'),
]
UPDATE_STRINGS_AR = [
    ('setup_update_later', 'لاحقًا'),
]
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
    if 'name="setup_update_later"' in s:
        sys.exit(f'phase3: {strings_xml} already carries setup_update_later')
    is_ar = os.path.basename(os.path.dirname(strings_xml)) == 'values-ar'
    block = ''.join(
        f'\n    <string name="{name}">{runlog_escape(text)}</string>'
        for name, text in (UPDATE_STRINGS_AR if is_ar else UPDATE_STRINGS_EN))
    s = s.replace(anchor, anchor + block, 1)
    open(strings_xml, 'w', encoding='utf-8').write(s)
    count += 1
if count < 10:
    sys.exit(f'phase3: only {count} locale files carried nav_tab_reforged -- expected 10+')
print(f'update strings added to {count} locale files')

# ---------------- 12) v1.29 identity + Arabic + Thmanyah ------------
# Committee section 4 + 5.5 + D5: the tertiary leak closes, the
# icon backdrop takes our gradient, the labels say the product's
# name, Arabic tops the language picker with its own-script names,
# and card headings wear Thmanyah Serif Display (bundled).
LOCALE_HELPER = os.path.join(JAVA_DIR, 'LocaleHelper.java')
UIKIT = os.path.join(JAVA_DIR, 'UiKit.java')

# 12a) the icon backdrop gradient: realkot navy -> our steel
BG_ICON = os.path.join(RES, 'drawable', 'ic_launcher_background.xml')
bg_xml = open(BG_ICON, encoding='utf-8').read()
for old_hex, new_hex in (('#FF23395D', '#FF283242'), ('#FF0A1222', '#FF0B0E13')):
    if bg_xml.count(old_hex) != 1:
        sys.exit('phase3: icon backdrop colour %s matched %d times' % (old_hex, bg_xml.count(old_hex)))
    bg_xml = bg_xml.replace(old_hex, new_hex)
open(BG_ICON, 'w', encoding='utf-8').write(bg_xml)
print('icon backdrop recoloured')

# 12b) the labels: the product's name, everywhere for the drawer
# label and in values + values-ar for the window title
labels_done = 0
for strings_xml in sorted(glob.glob(os.path.join(RES, 'values*', 'strings.xml'))):
    locale = os.path.basename(os.path.dirname(strings_xml))
    s = open(strings_xml, encoding='utf-8').read()
    s, n = re.subn(r'(<string name="app_name">)[^<]*(</string>)',
                   r'\g<1>Zero Hour Reforged\g<2>', s)
    if locale in ('values', 'values-ar'):
        s, n2 = re.subn(r'(<string name="setup_window_title">)[^<]*(</string>)',
                        r'\g<1>Zero Hour Reforged\g<2>', s)
        n += n2
    if n:
        open(strings_xml, 'w', encoding='utf-8').write(s)
        labels_done += 1
print('app labels set in %d locale files' % labels_done)

# 12c) Arabic up the picker + own-script language names
edit(LOCALE_HELPER, [
    ('''    static final String[] SUPPORTED_TAGS = { "", "en", "ru", "de", "uk", "es", "zh", "fr", "ko", "pl", "pt-BR", "isv", "ar", "fa" };''',
     '''    static final String[] SUPPORTED_TAGS = { "", "ar", "en", "ru", "de", "uk", "es", "zh", "fr", "ko", "pl", "pt-BR", "isv", "fa" };'''),
    ('''            case "ukrainian": return "Українська";''',
     '''            case "ukrainian": return "Українська";
            case "arabic":    return "العربية";
            case "persian":   return "فارسی";'''),
])

# 12d) Thmanyah headings: bundle the font, wear it in section headers
import shutil
font_src = os.path.join(OVERLAY, 'fonts', 'thmanyahserifdisplay-Regular.otf')
if not os.path.isfile(font_src):
    sys.exit('phase3: missing overlay font ' + font_src)
font_dst_dir = os.path.join(APP, 'assets', 'fonts')
os.makedirs(font_dst_dir, exist_ok=True)
shutil.copyfile(font_src, os.path.join(font_dst_dir, 'thmanyahserifdisplay-Regular.otf'))
print('thmanyah font staged into assets/fonts')
edit(UIKIT, [
    ('''        titleView.setTextSize(TypedValue.COMPLEX_UNIT_PX, dim(c, R.dimen.gzh_text_title));
        titleView.setTextColor(color(c, R.color.gzh_on_surface));
        titleView.setTypeface(Typeface.DEFAULT_BOLD);''',
     '''        titleView.setTextSize(TypedValue.COMPLEX_UNIT_PX, dim(c, R.dimen.gzh_text_title));
        titleView.setTextColor(color(c, R.color.gzh_on_surface));
        titleView.setTypeface(headingTypeface(c));'''),
    ('''    static TextView sectionHeader(LinearLayout body, int iconRes, CharSequence title, boolean withValue) {''',
     '''    // v1.29 (D5): card headings wear the brand typeface, Thmanyah
    // Serif Display, bundled in assets/fonts. Any failure (missing
    // asset, unreadable file) falls back to the system bold -- a
    // heading must never take its page down with it.
    private static Typeface sHeadingTypeface;
    static Typeface headingTypeface(Context c) {
        if (sHeadingTypeface == null) {
            try {
                sHeadingTypeface = Typeface.createFromAsset(
                    c.getAssets(), "fonts/thmanyahserifdisplay-Regular.otf");
            } catch (Exception e) {
                sHeadingTypeface = Typeface.DEFAULT_BOLD;
            }
        }
        return sHeadingTypeface;
    }

    static TextView sectionHeader(LinearLayout body, int iconRes, CharSequence title, boolean withValue) {'''),
])
edit(SETUP, [
    ('''        heroTitle.setTextSize(20);''',
     '''        heroTitle.setTextSize(20);
        heroTitle.setTypeface(UiKit.headingTypeface(this));'''),
])

# ---------------- 13) v1.29 first-run auto-scan (D6) -----------------
edit(SETUP, [
    ('''        // The one thing this app exists to do, as the first thing on it.''',
     '''        maybeAutoFindGameFolder();

        // The one thing this app exists to do, as the first thing on it.'''),
    ('''    private int tabTitle(int tab) {''',
     '''    // v1.29 (D6): first-run auto-scan. While no game folder is
    // set, look in the obvious places (the storage root and
    // Download / Documents / Games, plus one level inside each)
    // for exactly one valid game folder and adopt it -- the
    // friend who copied the game over and opened the app lands
    // on a ready Play button, not a file hunt. More than one
    // candidate: adopt none (the picker decides). Once per
    // process, and only while unset.
    private boolean mAutoScanDone;

    private void maybeAutoFindGameFolder() {
        if (mAutoScanDone || getSavedGamePath() != null) {
            return;
        }
        mAutoScanDone = true;
        try {
            java.io.File sd = android.os.Environment.getExternalStorageDirectory();
            if (sd == null) {
                return;
            }
            java.util.ArrayList<java.io.File> candidates = new java.util.ArrayList<>();
            java.io.File[] roots = {
                sd, new java.io.File(sd, "Download"),
                new java.io.File(sd, "Documents"), new java.io.File(sd, "Games")
            };
            for (java.io.File root : roots) {
                if (root == null) {
                    continue;
                }
                if (isValidGameFolder(root, getSelectedGame(this))) {
                    candidates.add(root);
                }
                java.io.File[] kids = root.listFiles();
                if (kids != null) {
                    for (java.io.File k : kids) {
                        if (k.isDirectory() && isValidGameFolder(k, getSelectedGame(this))) {
                            candidates.add(k);
                        }
                    }
                }
            }
            if (candidates.size() == 1) {
                String path = candidates.get(0).getAbsolutePath();
                saveGamePath(path);
                Toast.makeText(this, getString(R.string.setup_home_autofound, path),
                    Toast.LENGTH_LONG).show();
            }
        } catch (Exception ignored) {}
    }

    private int tabTitle(int tab) {'''),
])

# ---------------- 13s) the auto-scan string ---------------------------
AUTOFIND_STRINGS_EN = [
    ('setup_home_autofound', 'Found your game in %1$s -- ready to play'),
]
AUTOFIND_STRINGS_AR = [
    ('setup_home_autofound', 'لقينا لعبتك في %1$s -- جاهزة للعب'),
]
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
    if 'name="setup_home_autofound"' in s:
        sys.exit(f'phase3: {strings_xml} already carries setup_home_autofound')
    is_ar = os.path.basename(os.path.dirname(strings_xml)) == 'values-ar'
    block = ''.join(
        f'\n    <string name="{name}">{runlog_escape(text)}</string>'
        for name, text in (AUTOFIND_STRINGS_AR if is_ar else AUTOFIND_STRINGS_EN))
    s = s.replace(anchor, anchor + block, 1)
    open(strings_xml, 'w', encoding='utf-8').write(s)
    count += 1
if count < 10:
    sys.exit(f'phase3: only {count} locale files carried nav_tab_reforged -- expected 10+')
print(f'autofind strings added to {count} locale files')

# ---------------- 14) v1.29 post-edit self-checks ---------------------
# Fail the CI loudly rather than ship a half-rebuilt launcher: every
# deleted symbol must be gone, every kept load-bearing symbol present.
_setup_src = open(SETUP, encoding='utf-8').read()
for _dead in ('TAB_TESTS', 'FrameCheckActivity', 'buildTestsPage',
              'setup_tests_', 'buildRfxRenderScaleSection',
              'maybeRefreshTestsPage'):
    if _dead in _setup_src:
        sys.exit('phase3: dead symbol survived the rebuild: ' + _dead)
for _kept, _minimum in (('RfxGameActivity', 2), ('getSavedGamePath', 3),
                        ('buildRfxLogSection', 2),
                        ('buildGfxPresetSection', 2),
                        ('buildLogSettingsSection', 2),
                        ('applyV129Migrations', 2),
                        ('applyV130ClassicMigration', 2),
                        ('ClassicGraphics', 3),
                        ('setup_gfx_classic_on', 1),
                        ('nav_tab_settings', 1)):
    if _setup_src.count(_kept) < _minimum:
        sys.exit('phase3: kept symbol missing or too rare: ' + _kept)
_rfx_src = open(os.path.join(JAVA_DIR, 'RfxGameActivity.java'),
                encoding='utf-8').read()
if 'logging_off' not in _rfx_src:
    sys.exit('phase3: RfxGameActivity lost its logging_off gate')
if _rfx_src.count('setLanMulticastLock') != 1:
    sys.exit('phase3: RfxGameActivity LAN multicast lock missing/duplicated')
_manifest_src = open(MANIFEST, encoding='utf-8').read()
if 'FrameCheckActivity' in _manifest_src:
    sys.exit('phase3: manifest still registers FrameCheckActivity')
if _manifest_src.count('RfxGameActivity') != 1:
    sys.exit('phase3: manifest RfxGameActivity count != 1')
_pkg_src = open(PACKAGE_SH, encoding='utf-8').read()
if 'GX_REFORGEDX_LIB:' in _pkg_src or 'GX_REFORGEDX_LIB}' in _pkg_src:
    sys.exit('phase3: package script still stages libmainrfx.so')
# v1.29.1 (run #51): aapt dies on duplicate <string> keys and the harness
# never looked at resources -- scan every generated strings.xml now.
import collections as _collections
for _sx in sorted(glob.glob(os.path.join(RES, 'values*', 'strings.xml'))):
    _names = re.findall(r'<string name="([^"]+)"', open(_sx, encoding='utf-8').read())
    _dups = [k for k, c in _collections.Counter(_names).items() if c > 1]
    if _dups:
        sys.exit('phase3: duplicate string keys in ' + _sx + ': ' + ', '.join(_dups))
# v1.30.2 (run #56 device evidence, record section 366): the overlay
# extraction gate must be keyed to the build, and the shipped Arabic
# Language.ini must carry its Language block -- the two defects that
# broke the 1.30 / 1.30.1 Arabic boots.
if 'OVERLAY_REV = "3"' not in _rfx_src:
    sys.exit('phase3: OVERLAY_REV not bumped to 3')
if 'getLongVersionCode' not in _rfx_src or 'overlayKey' not in _rfx_src:
    sys.exit('phase3: overlay extraction is not keyed to the build')
if 'deleteRecursively' not in _rfx_src:
    sys.exit('phase3: overlay clean-extract helper missing')
for _cand in (os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '..', 'probe', 'data', 'arabic',
                           'Language.ini'),
              os.path.join(os.getcwd(), 'probe', 'data', 'arabic',
                           'Language.ini')):
    if os.path.isfile(_cand):
        _lines = [ln.strip() for ln in
                  open(_cand, encoding='utf-8').read().splitlines()
                  if ln.strip() and not ln.strip().startswith(';')]
        if not _lines or _lines[0] != 'Language' or _lines[-1] != 'End':
            sys.exit('phase3: Arabic Language.ini lacks its Language '
                     'block: ' + _cand)
        break
else:
    print('phase3: WARNING Arabic Language.ini not found for the '
          'content gate (skipped)')
print('v1.29/v1.30 self-checks passed')


print('PHASE 3 DONE')
