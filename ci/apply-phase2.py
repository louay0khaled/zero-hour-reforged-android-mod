#!/usr/bin/env python3
"""Phase 2 (CI version): bundle the Reforged data as ONE merged package and
install it as a single enabled mod on first game-folder setup:
  - merged: !Reforged-v1.big -- the two engine-native packages merged into a
            single archive: every path of !ReforgedFixes-v3.big (sha256
            0f314b9e...) and !ReforgedBalance-v2.big (sha256 c736128f...),
            with the balance bytes winning the 102 shared paths, exactly as
            when the pair mounted fixes-first / balance-last. Mechanical
            equivalence of the merge is proven path-by-path in
            hidden_files/ws2-mod-merge.md. Bytes live in this repo at
            ci/assets/!Reforged-v1.big.
One mod replaces the pair because the launcher's mod analysis warns about
every pair of enabled mods that change the same INI files (the pair shared
102 by design), and pre-v1.1 (no kind declaration) it even flagged the pair
as two total conversions. The migration in the generated
ensureBundledReforgedData removes the app-installed legacy folders
(ReforgedFixes / ReforgedBalance) and their stored-order entries once the
merged folder is in place.
Online mode (v1.7): the injected block also carries applyOnlineMode --
the launcher's Online Mode switch (surgery phase 1f) snapshots the merged
mod's switch state here on entry and restores it on exit, through the
same listMods/saveOrder mechanism the Mods screen uses; and a first
install that happens while online mode is on installs the mod switched
off with the snapshot pre-recorded as enabled, so leaving the mode later
restores the default-install state.

Layout: REFORGED_SRC (env) points at the MYSOREZ checkout; default is the
parent of this repo's checkout (the CI workflow checks the overlay repo out
into <workspace>/reforged-overlay and MYSOREZ at <workspace>). The asset is
sha256-verified before anything is copied."""
import hashlib, os, shutil, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
OVERLAY = os.path.dirname(_HERE)
SRC = os.environ.get('REFORGED_SRC') or os.path.dirname(OVERLAY)
JAVA = os.path.join(SRC, 'android/app/src/main/java/com/generalsx/zerohour')
MERGED_SHA256 = 'a80534063888a5a22a3c2548d2d7a5d9a6bd7d2df1f88c22744b26668dce680a'

def edit(path, old, new):
    s = open(path, encoding='utf-8').read()
    if old not in s:
        sys.exit(f'PATTERN NOT FOUND in {path}: {old[:70]!r}')
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1))
    print('edited', os.path.basename(path))

def sha256_of(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()

print('phase2 target tree:', SRC)

# 0) verify + stage the merged bundled package from this repo
merged_src = os.path.join(_HERE, 'assets', '!Reforged-v1.big')
h = sha256_of(merged_src)
if h != MERGED_SHA256:
    sys.exit(f'MERGED SHA MISMATCH: {h}')
print('merged package verified:', h)

# 1) assets
asset_dir = os.path.join(SRC, 'android/app/src/main/assets/reforged')
os.makedirs(asset_dir, exist_ok=True)
shutil.copy(merged_src, os.path.join(asset_dir, '!Reforged-v1.big'))
print('asset copied:', '!Reforged-v1.big', os.path.getsize(merged_src), 'bytes')

# 2) ModManager.ensureBundledReforgedData: per-package install + enable.
mm = os.path.join(JAVA, 'ModManager.java')
method = '''
    // GeneralsX @feature Zero Hour Reforged 12/11/2026 The Reforged data ships
    // as ONE merged package bundled in the APK (assets/reforged): the fixes
    // package and the balance package merged into a single archive, every
    // path byte-identical to the old two-mod stack (balance bytes win the
    // shared paths). The first time a Zero Hour game folder is in place, copy
    // it into mods/ if it is not already installed and switch it on. End of
    // the order is the highest priority. A folder the player installed by
    // hand is never copied over; like a bundled one it is switched on the
    // first time this app sees it, and a switch state already recorded for
    // it is never overridden. A folder this app itself installed is refreshed
    // in place when an app update ships different bundled bytes.
    // Migration (v1.6): the pre-merge pair (ReforgedFixes / ReforgedBalance
    // folders) is removed once the merged folder is in place -- only the
    // exact folders this app itself installed; a hand-named folder is never
    // deleted. The stored order is rebuilt from the folders that remain, so
    // the removed pair's "1|name"/"0|name" entries go with them.
    static final String BUNDLED_DIR = "Reforged";
    private static final String BUNDLED_ASSET = "reforged/!Reforged-v1.big";
    private static final String BUNDLED_FILE = "!Reforged-v1.big";
    private static final String LEGACY_FIXES_DIR = "ReforgedFixes";
    private static final String LEGACY_BALANCE_DIR = "ReforgedBalance";

    private static File findBundledDir(File root, String needle) {
        File[] children = root.listFiles(File::isDirectory);
        if (children == null) {
            return null;
        }
        for (File child : children) {
            File[] files = child.listFiles();
            if (files == null) {
                continue;
            }
            for (File f : files) {
                String n = f.getName().toLowerCase(Locale.US);
                if (n.contains(needle) && (n.endsWith(".big") || n.endsWith(".gib"))) {
                    return child;
                }
            }
        }
        return null;
    }

    private static boolean installBundled(Context ctx, File root, String dirName,
                                            String asset, String fileName,
                                            String modIni) {
        File dir = new File(root, dirName);
        try {
            if (!dir.isDirectory() && !dir.mkdirs()) {
                return false;
            }
            try (java.io.InputStream in = ctx.getAssets().open(asset);
                 java.io.OutputStream os = new java.io.FileOutputStream(
                     new File(dir, fileName))) {
                byte[] buf = new byte[65536];
                int r;
                while ((r = in.read(buf)) != -1) {
                    os.write(buf, 0, r);
                }
            }
            try (FileWriter w = new FileWriter(new File(dir, "mod.ini"))) {
                w.write(modIni);
            } catch (IOException ignored) {
                // The folder name alone still lists fine.
            }
            return true;
        } catch (IOException e) {
            android.util.Log.w("ModManager", "bundled Reforged install failed: " + dirName, e);
            return false;
        }
    }

    private static byte[] readAllBytes(java.io.InputStream in) throws IOException {
        java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
        byte[] buf = new byte[65536];
        int r;
        while ((r = in.read(buf)) != -1) {
            bos.write(buf, 0, r);
        }
        return bos.toByteArray();
    }

    private static void deleteRecursive(File f) {
        File[] children = f.listFiles();
        if (children != null) {
            for (File child : children) {
                deleteRecursive(child);
            }
        }
        f.delete();
    }

    // GeneralsX @bugfix Zero Hour Reforged 10/11/2026 Refresh a folder this app
    // itself installed (the caller passes only the exact bundled folder name)
    // when the bundled content has moved on: an app update replaces the APK
    // but never the mods/ folders, so without this the install would keep the
    // previous version's package forever -- the v1.0 balance folder kept its
    // data-side locomotor restatements, which the patched engine throws on.
    // The package file is re-copied when its size or SHA-256 differs from the
    // asset; mod.ini is rewritten when its text differs (folders installed by
    // v1.0 predate the kind declaration). The stored mod order is not touched
    // here, so a switch state the player recorded survives the refresh.
    private static void refreshBundled(Context ctx, File dir, String asset,
                                       String fileName, String modIni) {
        try {
            byte[] want;
            try (java.io.InputStream in = ctx.getAssets().open(asset)) {
                want = readAllBytes(in);
            }
            File cur = new File(dir, fileName);
            boolean stale = true;
            if (cur.isFile() && cur.length() == want.length) {
                byte[] have;
                try (java.io.InputStream in = new java.io.FileInputStream(cur)) {
                    have = readAllBytes(in);
                }
                java.security.MessageDigest md =
                        java.security.MessageDigest.getInstance("SHA-256");
                stale = !java.security.MessageDigest.isEqual(
                        md.digest(want), md.digest(have));
            }
            if (stale) {
                try (java.io.OutputStream os = new java.io.FileOutputStream(cur)) {
                    os.write(want);
                }
            }
            File iniFile = new File(dir, "mod.ini");
            String current = null;
            if (iniFile.isFile()) {
                try (java.io.InputStream in = new java.io.FileInputStream(iniFile)) {
                    current = new String(readAllBytes(in),
                            java.nio.charset.StandardCharsets.UTF_8);
                } catch (IOException ignored) {
                    // Rewritten below.
                }
            }
            if (!modIni.equals(current)) {
                try (FileWriter w = new FileWriter(iniFile)) {
                    w.write(modIni);
                } catch (IOException ignored) {
                    // The folder name alone still lists fine.
                }
            }
        } catch (Exception e) {
            android.util.Log.w("ModManager", "bundled Reforged refresh failed: " + dir.getName(), e);
        }
    }

    static void ensureBundledReforgedData(Context ctx) {
        if (!SetupActivity.GAME_ZERO_HOUR.equals(SetupActivity.getSelectedGame(ctx))) {
            return;
        }
        File root = modsRoot(ctx);
        if (root == null) {
            return;
        }
        final String mergedIni =
                "name = Reforged\\n"
                + "kind = gameplay\\n"
                + "version = v1\\n"
                + "author = Reforged (Olcay Seygan) - Android package\\n"
                + "description = The Reforged fixes and balance packages merged into one, bundled with Zero Hour Reforged.\\n";
        File mergedDir = findBundledDir(root, "reforged-v1");
        if (mergedDir == null) {
            if (installBundled(ctx, root, BUNDLED_DIR, BUNDLED_ASSET,
                    BUNDLED_FILE, mergedIni)) {
                mergedDir = new File(root, BUNDLED_DIR);
            }
        } else if (mergedDir.getName().equals(BUNDLED_DIR)) {
            // Our own folder: refresh it if this build ships different bytes.
            // A folder the player named themselves is left exactly as it is.
            refreshBundled(ctx, mergedDir, BUNDLED_ASSET,
                    BUNDLED_FILE, mergedIni);
        }
        if (mergedDir == null) {
            return;
        }
        // GeneralsX @feature Zero Hour Reforged 12/11/2026 Migration: the merged
        // folder is in place, so the pre-merge pair leaves the install. Only
        // the exact app-installed folders are removed (a hand-named folder is
        // never deleted, as before); the order rebuild below drops their
        // stored entries, and a last-enabled pointer at a removed folder is
        // cleared here (that pref lives in this class).
        for (String legacyName : new String[]{LEGACY_FIXES_DIR, LEGACY_BALANCE_DIR}) {
            File legacy = new File(root, legacyName);
            if (legacy.isDirectory()) {
                deleteRecursive(legacy);
            }
        }
        String lastEnabled = lastEnabled(ctx);
        if (LEGACY_FIXES_DIR.equals(lastEnabled) || LEGACY_BALANCE_DIR.equals(lastEnabled)) {
            ctx.getSharedPreferences(SetupActivity.PREFS_NAME, Context.MODE_PRIVATE)
                    .edit().remove(PREF_LAST_ENABLED).apply();
        }
        // GeneralsX @bugfix Zero Hour Reforged 10/11/2026 A Reforged folder is
        // switched on only at its first sight in this app -- no entry for it
        // in the stored order yet; a folder that already has an entry keeps
        // the switch it records, on or off.
        List<String> stored = readOrder(ctx);
        boolean mergedKnown = hasOrderEntry(stored, mergedDir.getName());
        List<Mod> mods = listMods(ctx);
        Mod mergedMod = null;
        List<Mod> rest = new java.util.ArrayList<>();
        for (Mod mod : mods) {
            if (mod.dir.getName().equals(mergedDir.getName())) {
                mergedMod = mod;
            } else {
                rest.add(mod);
            }
        }
        List<Mod> ordered = new java.util.ArrayList<>(rest);
        if (mergedMod != null) {
            if (!mergedKnown) {
                // GeneralsX @feature Zero Hour Reforged 12/11/2026 First
                // sight while online mode is on: the mod installs in the
                // online state instead -- switched off, with the pre-mode
                // snapshot recorded as enabled, so leaving online mode
                // restores the default-install state.
                if (SetupActivity.getOnlineMode(ctx)) {
                    mergedMod.enabled = false;
                    android.content.SharedPreferences prefs =
                            ctx.getSharedPreferences(SetupActivity.PREFS_NAME,
                                    Context.MODE_PRIVATE);
                    if (!prefs.contains(PREF_ONLINE_SNAPSHOT_MOD)) {
                        prefs.edit().putInt(PREF_ONLINE_SNAPSHOT_MOD, 1).apply();
                    }
                } else {
                    mergedMod.enabled = true;
                }
            }
            ordered.add(mergedMod);
        }
        saveOrder(ctx, ordered);
    }

    /** Whether the stored order already carries an entry ("1|name" / "0|name") for a folder. */
    private static boolean hasOrderEntry(List<String> entries, String dirName) {
        for (String entry : entries) {
            if (entry.length() > 2 && entry.substring(2).equals(dirName)) {
                return true;
            }
        }
        return false;
    }

    // GeneralsX @feature Zero Hour Reforged 12/11/2026 Online mode
    // (SetupActivity, surgery phase 1f): while it is on, the bundled
    // Reforged mod must be switched off, so GeneralsOnline sees the stock
    // data set. The mod's own switch state is snapshotted on entry and
    // restored on exit -- a mod the player had switched off by hand stays
    // off. The switch itself goes through listMods/saveOrder, the exact
    // mechanism the Mods screen uses, so every screen keeps showing the
    // same state. The snapshot lives in the setup prefs next to the
    // online-mode pref itself.
    private static final String PREF_ONLINE_SNAPSHOT_MOD =
            "reforged_online_snapshot_mod";

    static void applyOnlineMode(Context ctx, boolean entering) {
        File root = modsRoot(ctx);
        if (root == null) {
            return;
        }
        File bundledDir = findBundledDir(root, "reforged-v1");
        android.content.SharedPreferences prefs = ctx.getSharedPreferences(
                SetupActivity.PREFS_NAME, Context.MODE_PRIVATE);
        List<Mod> mods = listMods(ctx);
        Mod bundled = null;
        if (bundledDir != null) {
            for (Mod mod : mods) {
                if (mod.dir.getName().equals(bundledDir.getName())) {
                    bundled = mod;
                    break;
                }
            }
        }
        if (entering) {
            if (bundled == null || prefs.contains(PREF_ONLINE_SNAPSHOT_MOD)) {
                return;
            }
            prefs.edit()
                    .putInt(PREF_ONLINE_SNAPSHOT_MOD, bundled.enabled ? 1 : 0)
                    .apply();
            if (bundled.enabled) {
                bundled.enabled = false;
                saveOrder(ctx, mods);
            }
        } else {
            if (!prefs.contains(PREF_ONLINE_SNAPSHOT_MOD)) {
                return;
            }
            boolean restore = prefs.getInt(PREF_ONLINE_SNAPSHOT_MOD, 1) == 1;
            prefs.edit().remove(PREF_ONLINE_SNAPSHOT_MOD).apply();
            if (bundled != null && bundled.enabled != restore) {
                bundled.enabled = restore;
                saveOrder(ctx, mods);
            }
        }
    }

'''
edit(mm, '    private static List<String> readOrder(Context ctx) {',
     method + '    private static List<String> readOrder(Context ctx) {')

# 3) SetupActivity hooks: after a folder is saved, and at launcher start.
sa = os.path.join(JAVA, 'SetupActivity.java')
edit(sa, '                saveGamePath(path);\n',
         '                saveGamePath(path);\n'
         '                ModManager.ensureBundledReforgedData(this);\n')
edit(sa, '        super.onCreate(savedInstanceState);\n',
         '        super.onCreate(savedInstanceState);\n'
         '        ModManager.ensureBundledReforgedData(this);\n')

print('PHASE 2 DONE')
