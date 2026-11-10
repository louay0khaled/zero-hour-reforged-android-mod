#!/usr/bin/env python3
"""Phase 2 (CI version): bundle the Reforged data packages as APK assets and
install them as enabled mods on first game-folder setup:
  - fixes:   !ReforgedFixes-v3.big   (engine-native variant of the v3 package:
             v3 content with the 16 data-side Locomotor restatement blocks
             dropped -- the patched engine carries the sets over natively and
             restating them would now throw in parseLocomotorSet). Bytes live
             in this repo at ci/assets/!ReforgedFixes-v3.big.
  - balance: !ReforgedBalance-v2.big (the owner-verified v2 file, byte-identical;
             v1 is NOT used -- its jet-taxi locomotor block freezes jets here).
             Bytes live in this repo at packages/!ReforgedBalance-v2.big.
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
BALANCE_SHA256 = '96bae34477b9bf38ee1f78e32915da99b8a2243fa476712f96ba1bce0c76e7f4'

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
bal_src = os.path.join(OVERLAY, 'packages', '!ReforgedBalance-v2.big')
h = sha256_of(bal_src)
if h != BALANCE_SHA256:
    sys.exit(f'BALANCE V2 SHA MISMATCH: {h}')
print('balance v2 verified:', h)

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
    // package). A package the user installed by hand is left exactly as it is.
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

    static void ensureBundledReforgedData(Context ctx) {
        if (!SetupActivity.GAME_ZERO_HOUR.equals(SetupActivity.getSelectedGame(ctx))) {
            return;
        }
        File root = modsRoot(ctx);
        if (root == null) {
            return;
        }
        File fixesDir = findBundledDir(root, "reforgedfixes");
        File balanceDir = findBundledDir(root, "reforgedbalance");
        boolean installedAny = false;
        if (fixesDir == null) {
            if (installBundled(ctx, root, BUNDLED_FIXES_DIR, BUNDLED_FIXES_ASSET,
                    BUNDLED_FIXES_FILE,
                    "name = Reforged Fixes\\n"
                    + "version = v3\\n"
                    + "author = Reforged (Olcay Seygan) - Android package\\n"
                    + "description = The Reforged engine fixes, bundled with Zero Hour Reforged.\\n")) {
                fixesDir = new File(root, BUNDLED_FIXES_DIR);
                installedAny = true;
            }
        }
        if (balanceDir == null) {
            if (installBundled(ctx, root, BUNDLED_BALANCE_DIR, BUNDLED_BALANCE_ASSET,
                    BUNDLED_BALANCE_FILE,
                    "name = Reforged Balance\\n"
                    + "version = v2\\n"
                    + "author = Reforged (Olcay Seygan) - Android package\\n"
                    + "description = The Reforged balance layer, bundled with Zero Hour Reforged.\\n")) {
                balanceDir = new File(root, BUNDLED_BALANCE_DIR);
                installedAny = true;
            }
        }
        if (!installedAny) {
            return;
        }
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
            if (fixesDir.getName().equals(BUNDLED_FIXES_DIR)) {
                fixesMod.enabled = true;
            }
            ordered.add(fixesMod);
        }
        if (balanceMod != null) {
            if (balanceDir.getName().equals(BUNDLED_BALANCE_DIR)) {
                balanceMod.enabled = true;
            }
            ordered.add(balanceMod);
        }
        saveOrder(ctx, ordered);
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
