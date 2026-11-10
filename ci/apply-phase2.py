#!/usr/bin/env python3
"""Phase 2 (CI version): bundle the Reforged data packages as APK assets and
install them as enabled mods on first game-folder setup:
  - fixes:   !ReforgedFixes-v3.big   (engine-native variant of the v3 package:
             v3 content with the 16 data-side Locomotor restatement blocks
             dropped -- the patched engine carries the sets over natively and
             restating them would now throw in parseLocomotorSet). Bytes live
             in this repo at ci/assets/!ReforgedFixes-v3.big.
  - balance: !ReforgedBalance-v2.big (the ENGINE-NATIVE variant of the v2
             package: published v2 content with its 38 data-side Locomotor
             restatement blocks dropped -- with the patched engine those
             restatements throw in parseLocomotorSet and the game does not
             start; see the project report start-crash-investigation.md).
             Bytes live in this repo at ci/assets/!ReforgedBalance-v2.big.
             The published packages/!ReforgedBalance-v2.big is NOT used here:
             it stays byte-identical for the unpatched engine.
Balance mounts after fixes (end of the mod order = highest priority), matching
the verified combined state where balance entries supersede fixes entries.

Layout: REFORGED_SRC (env) points at the MYSOREZ checkout; default is the
parent of this repo's checkout (the CI workflow checks the overlay repo out
into <workspace>/reforged-overlay and MYSOREZ at <workspace>). Both assets are
sha256-verified before anything is copied."""
import hashlib, os, shutil, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
OVERLAY = os.path.dirname(_HERE)
SRC = os.environ.get('REFORGED_SRC') or os.path.dirname(OVERLAY)
JAVA = os.path.join(SRC, 'android/app/src/main/java/com/generalsx/zerohour')
FIXES_SHA256 = '0f314b9efd5612d707a7a2f3f0ed061541edc5f0e52ee6cb693caf94b14ac6b5'
BALANCE_SHA256 = 'c736128fd1dc87950445cace87a49fa822928b78c7dd9df0089d1227416bf218'

def edit(path, old, new):
    s = open(path, encoding='utf-8').read()
    if old not in s:
        sys.exit(f'PATTERN NOT FOUND in {path}: {old[:70]!r}')
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1))
    print('edited', os.path.basename(path))

def sha256_of(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()

print('phase2 target tree:', SRC)

# 0) verify + stage the two bundled packages from this repo
fix_src = os.path.join(_HERE, 'assets', '!ReforgedFixes-v3.big')
h = sha256_of(fix_src)
if h != FIXES_SHA256:
    sys.exit(f'FIXES (engine-native) SHA MISMATCH: {h}')
print('fixes engine-native verified:', h)
bal_src = os.path.join(_HERE, 'assets', '!ReforgedBalance-v2.big')
h = sha256_of(bal_src)
if h != BALANCE_SHA256:
    sys.exit(f'BALANCE (engine-native) SHA MISMATCH: {h}')
print('balance engine-native verified:', h)

# 1) assets
asset_dir = os.path.join(SRC, 'android/app/src/main/assets/reforged')
os.makedirs(asset_dir, exist_ok=True)
shutil.copy(fix_src, os.path.join(asset_dir, '!ReforgedFixes-v3.big'))
shutil.copy(bal_src, os.path.join(asset_dir, '!ReforgedBalance-v2.big'))
for f in ('!ReforgedFixes-v3.big', '!ReforgedBalance-v2.big'):
    print('asset copied:', f, os.path.getsize(os.path.join(asset_dir, f)), 'bytes')

# 2) ModManager.ensureBundledReforgedData: per-package install + enable.
mm = os.path.join(JAVA, 'ModManager.java')
method = '''
    // GeneralsX @feature Zero Hour Reforged 10/11/2026 The Reforged data packages
    // are bundled in the APK (assets/reforged): the fixes package and the balance
    // package. The first time a Zero Hour game folder is in place, copy each one
    // that is not already installed into mods/ and switch it on. End of the order
    // is the highest priority, so the fixes go first and the balance last (the
    // balance entries supersede the fixes entries, as in the verified combined
    // package). A package folder the player installed by hand is never copied
    // over; like a bundled one it is switched on the first time this app sees
    // it, and a switch state already recorded for it is never overridden.
    // A folder this app itself installed is refreshed in place when an app
    // update ships different bundled bytes, so an updated install never
    // keeps running the previous version's package.
    static final String BUNDLED_FIXES_DIR = "ReforgedFixes";
    static final String BUNDLED_BALANCE_DIR = "ReforgedBalance";
    private static final String BUNDLED_FIXES_ASSET = "reforged/!ReforgedFixes-v3.big";
    private static final String BUNDLED_FIXES_FILE = "!ReforgedFixes-v3.big";
    private static final String BUNDLED_BALANCE_ASSET = "reforged/!ReforgedBalance-v2.big";
    private static final String BUNDLED_BALANCE_FILE = "!ReforgedBalance-v2.big";

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

    // GeneralsX @bugfix Zero Hour Reforged 10/11/2026 Refresh a folder this app
    // itself installed (the caller passes only the exact bundled folder names)
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
        final String fixesIni =
                "name = Reforged Fixes\\n"
                + "kind = gameplay\\n"
                + "version = v3\\n"
                + "author = Reforged (Olcay Seygan) - Android package\\n"
                + "description = The Reforged engine fixes, bundled with Zero Hour Reforged.\\n";
        final String balanceIni =
                "name = Reforged Balance\\n"
                + "kind = gameplay\\n"
                + "version = v2\\n"
                + "author = Reforged (Olcay Seygan) - Android package\\n"
                + "description = The Reforged balance layer, bundled with Zero Hour Reforged.\\n";
        File fixesDir = findBundledDir(root, "reforgedfixes");
        File balanceDir = findBundledDir(root, "reforgedbalance");
        if (fixesDir == null) {
            if (installBundled(ctx, root, BUNDLED_FIXES_DIR, BUNDLED_FIXES_ASSET,
                    BUNDLED_FIXES_FILE, fixesIni)) {
                fixesDir = new File(root, BUNDLED_FIXES_DIR);
            }
        } else if (fixesDir.getName().equals(BUNDLED_FIXES_DIR)) {
            // Our own folder: refresh it if this build ships different bytes.
            // A folder the player named themselves is left exactly as it is.
            refreshBundled(ctx, fixesDir, BUNDLED_FIXES_ASSET,
                    BUNDLED_FIXES_FILE, fixesIni);
        }
        if (balanceDir == null) {
            if (installBundled(ctx, root, BUNDLED_BALANCE_DIR, BUNDLED_BALANCE_ASSET,
                    BUNDLED_BALANCE_FILE, balanceIni)) {
                balanceDir = new File(root, BUNDLED_BALANCE_DIR);
            }
        } else if (balanceDir.getName().equals(BUNDLED_BALANCE_DIR)) {
            refreshBundled(ctx, balanceDir, BUNDLED_BALANCE_ASSET,
                    BUNDLED_BALANCE_FILE, balanceIni);
        }
        if (fixesDir == null && balanceDir == null) {
            return;
        }
        // GeneralsX @bugfix Zero Hour Reforged 10/11/2026 This step used to run
        // only when this call had just copied a package in, so a folder the
        // player had installed by hand counted as done and was never switched
        // on: the game started plain. It now runs whenever either folder is
        // there. A Reforged folder is switched on only at its first sight in
        // this app -- no entry for it in the stored order yet; a folder that
        // already has an entry keeps the switch it records, on or off.
        List<String> stored = readOrder(ctx);
        boolean fixesKnown = fixesDir != null && hasOrderEntry(stored, fixesDir.getName());
        boolean balanceKnown = balanceDir != null && hasOrderEntry(stored, balanceDir.getName());
        List<Mod> mods = listMods(ctx);
        Mod fixesMod = null;
        Mod balanceMod = null;
        List<Mod> rest = new java.util.ArrayList<>();
        for (Mod mod : mods) {
            if (fixesDir != null && mod.dir.getName().equals(fixesDir.getName())) {
                fixesMod = mod;
            } else if (balanceDir != null && mod.dir.getName().equals(balanceDir.getName())) {
                balanceMod = mod;
            } else {
                rest.add(mod);
            }
        }
        List<Mod> ordered = new java.util.ArrayList<>(rest);
        if (fixesMod != null) {
            if (!fixesKnown) {
                fixesMod.enabled = true;
            }
            ordered.add(fixesMod);
        }
        if (balanceMod != null) {
            if (!balanceKnown) {
                balanceMod.enabled = true;
            }
            ordered.add(balanceMod);
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
