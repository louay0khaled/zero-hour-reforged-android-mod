package com.louay.zerohour.gpuprobe;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Typeface;
import android.os.Build;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * Launcher screen for the stage-C harness app (slices C0 + C2). Runs one of
 * two instruments as a child SDLActivity and displays what the native
 * harness leaves behind in probe-result.txt (this app's external files
 * directory), ready to screenshot:
 *
 *   - "Run GPU probe" (C0): upstream's SDL GPU capability probe.
 *   - "Run renderer selfcheck" (C2, shown only when the selfcheck
 *     payloads are packaged in this APK): the Reforged engine's own
 *     sdl_gpu_frame/depth_format selfchecks. Route B (plan section
 *     10): the depth selfcheck still runs as a child process of the
 *     native shim's activity, but the frame selfcheck - which died
 *     inside SDL_Init as a bare child process - now runs as a shared
 *     library under its own SDLActivity (FrameCheckActivity, separate
 *     process) and leaves its output in frame-result.txt. This
 *     launcher chains the two activities and merges both halves into
 *     probe-result.txt under the renderer's usual verdict line.
 *
 * The choice reaches the native side through harness-mode.txt in the same
 * directory, rewritten on every tap. All UI is built in code; the app
 * ships no resources.
 *
 * Error log: the native harness also keeps probe-log.txt in the same
 * directory - a run section is opened before the probe starts, every output
 * chunk is flushed into it as it arrives, and a signal handler names the
 * crash if the probe dies by one. A native crash kills this whole process
 * before probe-result.txt can be written, so when a run was attempted but
 * no fresh result exists, this screen shows the log tail instead, under an
 * honest label. The launcher appends its own timestamped lines to the same
 * log (app start, Run tapped, resume verdict), so a relaunch after a crash
 * leaves its own evidence line right after the unclosed run section.
 */
public class ProbeMainActivity extends Activity {

    // Arabic label for the crashed-run view, "last run crashed - here is
    // its log". Written with unicode escapes so this source file stays pure
    // ASCII and compiles identically under any javac default charset.
    private static final String CRASH_LABEL =
            "\u0622\u062E\u0631 \u062A\u0634\u063A\u064A\u0644 "
            + "\u0627\u0646\u0647\u0627\u0631 \u2014 \u0647\u0627\u062F "
            + "\u0633\u062C\u0644\u0648";

    private static final int MODE_AUTO = 0;
    private static final int MODE_LOG = 1;
    private static final int MODE_RESULT = 2;

    private TextView mResultView;
    private Button mLogToggle;
    private int mMode = MODE_AUTO;
    private boolean mShowingLog = false;
    private boolean mLaunchedChild = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(24, 24, 24, 24);

        TextView title = new TextView(this);
        title.setText("Reforged GPU Probe (stage C0/C2)");
        title.setTextSize(18);
        root.addView(title);

        Button run = new Button(this);
        run.setText("Run GPU probe");
        run.setOnClickListener(v -> startInstrument("gpu-probe",
                "Running... the probe screen opens; when it finishes you return here and the table appears."));
        root.addView(run);

        if (rendererPayloadPresent()) {
            Button runRenderer = new Button(this);
            runRenderer.setText("Run renderer selfcheck");
            runRenderer.setOnClickListener(v -> startRenderer());
            root.addView(runRenderer);
        }

        mLogToggle = new Button(this);
        mLogToggle.setText("Show error log");
        mLogToggle.setOnClickListener(v -> {
            mMode = mShowingLog ? MODE_RESULT : MODE_LOG;
            showContent();
        });
        root.addView(mLogToggle);

        mResultView = new TextView(this);
        mResultView.setTypeface(Typeface.MONOSPACE);
        mResultView.setTextSize(11);
        mResultView.setTextIsSelectable(true);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(mResultView);
        root.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));

        setContentView(root);

        String startLine = "app started; device " + Build.MANUFACTURER + " " + Build.MODEL
                + ", Android " + Build.VERSION.RELEASE + " (SDK " + Build.VERSION.SDK_INT + ")"
                + "; SDL Java layer: " + sdlJavaLayerGuess();
        if (previousRunLooksUnclosed()) {
            startLine += "; NOTE: the previous probe run has no exit record - it died with the process";
        }
        appendLog(startLine);
        showContent();
    }

    // One launch path for both instruments: record the tap (the result
    // file only counts as this run's when it is newer than this moment),
    // tell the native side which instrument to run, leave the launcher's
    // own line in the error log, and open the SDL activity.
    private void startInstrument(String harness, String busyText) {
        long now = System.currentTimeMillis();
        prefs().edit().putLong("run_started_at", now).putString("last_harness", harness).apply();
        if (!"renderer".equals(harness)) {
            // A non-renderer run abandons any half-finished renderer chain.
            prefs().edit().putInt("renderer_phase", 0).apply();
        }
        writeHarnessMode(harness);
        appendLog("starting " + harness + " activity (Run tapped)");
        mLaunchedChild = true;
        mMode = MODE_AUTO;
        mResultView.setText(busyText);
        startActivity(new Intent(this, org.libsdl.app.SDLActivity.class));
    }

    // Route B renderer launch: clear the previous run's frame/depth
    // evidence files (so a stale frame-result.txt can never be merged
    // as this run's), mark phase 1 (the harness activity runs the
    // depth half), then take the normal launch path. onResume chains
    // phase 2 (FrameCheckActivity) when the harness activity returns,
    // and merges when that returns.
    private void startRenderer() {
        File dir = getExternalFilesDir(null);
        if (dir != null) {
            deleteQuietly(new File(dir, "frame-result.txt"));
            deleteQuietly(new File(dir, "renderer-depth.txt"));
        }
        prefs().edit().putInt("renderer_phase", 1).apply();
        startInstrument("renderer",
                "Running... two screens open in turn: first the harness (depth selfcheck), "
                + "then the frame selfcheck in its own screen. When both finish you return "
                + "here and the merged verdict appears.");
    }

    @Override
    protected void onResume() {
        super.onResume();
        boolean returnedFromChild = mLaunchedChild;
        if (mLaunchedChild) {
            mLaunchedChild = false;
            File result = resultFile();
            long startedAt = prefs().getLong("run_started_at", 0);
            String harness = prefs().getString("last_harness", "gpu-probe");
            if (isFreshResult(result, startedAt)) {
                appendLog("resumed; fresh " + harness + " result present (" + result.length() + " bytes)");
            } else {
                appendLog("resumed WITHOUT a fresh " + harness + " result - the last run left no output file");
            }
        }
        // Route B renderer chain. Phase 1 -> 2 fires only on the resume
        // that follows the harness activity, so a cold start with a
        // stale phase 1 never launches anything unasked. Phase 2 merges
        // on any resume that finds it set: normally the return from
        // FrameCheckActivity, but if this process died while the frame
        // activity ran, the merge still happens here on relaunch.
        String chainHarness = prefs().getString("last_harness", "gpu-probe");
        int phase = prefs().getInt("renderer_phase", 0);
        if ("renderer".equals(chainHarness) && phase == 1 && returnedFromChild) {
            prefs().edit().putInt("renderer_phase", 2).apply();
            appendLog("depth half finished; starting frame selfcheck activity (route B)");
            mLaunchedChild = true;
            mMode = MODE_AUTO;
            mResultView.setText("Depth selfcheck done. Running the frame selfcheck in its own screen...");
            startActivity(new Intent(this, FrameCheckActivity.class));
            return;
        }
        if ("renderer".equals(chainHarness) && phase == 2) {
            prefs().edit().putInt("renderer_phase", 0).apply();
            mergeRendererResults();
        }
        showContent();
    }

    // Route B merge: the frame activity's process has exited (or died).
    // Fold frame-result.txt and the depth half's captured output into
    // probe-result.txt under the same closing line the combined runs
    // always used, and append the frame section to the error log so
    // the forensic record holds both halves. The frame file is then
    // deleted - it has been consumed, and the next run must never
    // mistake it for its own.
    private void mergeRendererResults() {
        File dir = getExternalFilesDir(null);
        if (dir == null) {
            appendLog("renderer merge skipped - no external files directory");
            return;
        }
        File frameFile = new File(dir, "frame-result.txt");
        String frameText;
        String frameCode;
        if (frameFile.isFile() && frameFile.length() > 0) {
            frameText = readFully(frameFile);
            frameCode = parseFrameCode(frameText);
        } else {
            frameText = "(the frame selfcheck produced no frame-result.txt - its process died "
                    + "before its entry could write, or the storage path was unavailable)\n";
            frameCode = "no result file";
        }
        File depthCodeFile = new File(dir, "renderer-depth.txt");
        String depthCode = depthCodeFile.isFile() ? readFully(depthCodeFile).trim() : "unknown";
        if (depthCode.isEmpty()) {
            depthCode = "unknown";
        }
        File result = resultFile();
        String depthText = (result != null && result.isFile())
                ? readFully(result)
                : "(the depth half left no captured output)\n";
        String merged = frameText
                + (frameText.endsWith("\n") ? "" : "\n")
                + "\n[harness] --- depth selfcheck (child process of the harness activity) ---\n"
                + depthText
                + (depthText.endsWith("\n") ? "" : "\n")
                + "[harness] payload exit codes: frame " + frameCode + ", depth " + depthCode + "\n";
        if (result != null) {
            try (FileOutputStream out = new FileOutputStream(result, false)) {
                out.write(merged.getBytes("UTF-8"));
                out.getFD().sync();
            } catch (Throwable ignored) {
                // The log append below still carries the verdict.
            }
        }
        appendRawLog("\n===== renderer frame section (frame-result.txt, written by the FrameCheckActivity process) =====\n"
                + frameText
                + (frameText.endsWith("\n") ? "" : "\n")
                + "===== renderer frame section end =====\n");
        appendLog("renderer merge complete; payload exit codes: frame " + frameCode + ", depth " + depthCode);
        deleteQuietly(frameFile);
    }

    // The frame payload's verdict channel: the entry TU appends a
    // "[framecheck] body returned N" trailer (SDLActivity never hands
    // SDL_main's return value to the launcher), and its crash handler
    // appends a "[crumb] CRASH: signal S ..." line when it dies by one.
    private static String parseFrameCode(String frameText) {
        String marker = "[framecheck] body returned ";
        int at = frameText.lastIndexOf(marker);
        if (at >= 0) {
            int i = at + marker.length();
            int j = i;
            if (j < frameText.length() && frameText.charAt(j) == '-') {
                j++;
            }
            while (j < frameText.length() && Character.isDigit(frameText.charAt(j))) {
                j++;
            }
            if (j > i) {
                return frameText.substring(i, j);
            }
        }
        String crash = "CRASH: signal ";
        int c = frameText.lastIndexOf(crash);
        if (c >= 0) {
            int i = c + crash.length();
            int j = i;
            while (j < frameText.length() && Character.isDigit(frameText.charAt(j))) {
                j++;
            }
            if (j > i) {
                return "crashed (signal " + frameText.substring(i, j) + ")";
            }
        }
        return "unknown";
    }

    // ------------------------------------------------------------------
    // Display
    // ------------------------------------------------------------------

    private void showContent() {
        File result = resultFile();
        File log = logFile();
        long startedAt = prefs().getLong("run_started_at", 0);
        boolean fresh = isFreshResult(result, startedAt);
        boolean haveLog = log != null && log.isFile() && log.length() > 0;

        if (mMode == MODE_LOG) {
            showLog("(error log - probe-log.txt, newest last)");
            return;
        }
        if (mMode == MODE_RESULT) {
            if (result != null && result.isFile()) {
                showText(readFully(result));
            } else {
                showText(placeholderText());
            }
            return;
        }
        // MODE_AUTO
        if (fresh) {
            showText(readFully(result));
        } else if (startedAt > 0 && haveLog) {
            mShowingLog = true;
            mLogToggle.setText("Show result");
            mResultView.setText(CRASH_LABEL + "\n\n"
                    + "(The last probe run did not finish, so no result table "
                    + "was written. This is its error log, probe-log.txt, "
                    + "newest last.)\n\n"
                    + readTail(log, 16384));
        } else if (result != null && result.isFile()) {
            showText(readFully(result));
        } else {
            showText(placeholderText());
        }
    }

    private void showLog(String heading) {
        mShowingLog = true;
        mLogToggle.setText("Show result");
        File log = logFile();
        if (log != null && log.isFile() && log.length() > 0) {
            mResultView.setText(heading + "\n\n" + readTail(log, 16384));
        } else {
            mResultView.setText(heading + "\n\n(the error log is empty)");
        }
    }

    private void showText(String text) {
        mShowingLog = false;
        mLogToggle.setText("Show error log");
        mResultView.setText(text);
    }

    private static String placeholderText() {
        return "No result yet.\n\n"
                + "Tap \"Run GPU probe\" for the capability table, or \"Run "
                + "renderer selfcheck\" (when present) for the engine's own "
                + "renderer verdict. When the run finishes you return here "
                + "and its output appears on this screen - screenshot it.\n\n"
                + "(The same output is saved as probe-result.txt in this "
                + "app's files folder. If a run crashes, its error log is "
                + "kept in probe-log.txt in the same folder - tap \"Show "
                + "error log\" to read it.)";
    }

    private boolean isFreshResult(File result, long startedAt) {
        if (result == null || !result.isFile()) {
            return false;
        }
        if (startedAt == 0) {
            return true;
        }
        return result.lastModified() >= startedAt - 2000;
    }

    // True when the log's newest native run section was opened but never
    // closed by an exit or crash record - i.e. the process died mid-run.
    private boolean previousRunLooksUnclosed() {
        File log = logFile();
        if (log == null || !log.isFile() || log.length() == 0) {
            return false;
        }
        String tail = readTail(log, 65536);
        int lastStart = lastRunHeaderIndex(tail);
        if (lastStart < 0) {
            return false;
        }
        int lastEnd = Math.max(tail.lastIndexOf("probe exited normally"),
                Math.max(tail.lastIndexOf("renderer run finished"),
                        Math.max(tail.lastIndexOf("CRASH:"),
                                tail.lastIndexOf("===== probe run end"))));
        return lastStart > lastEnd;
    }

    // Index of the last "===== probe run " header that opens a run section
    // (the run-END line shares the prefix but continues with "end").
    private static int lastRunHeaderIndex(String text) {
        int idx = -1;
        int from = 0;
        while (true) {
            int hit = text.indexOf("===== probe run ", from);
            if (hit < 0) {
                return idx;
            }
            if (!text.startsWith("===== probe run end", hit)) {
                idx = hit;
            }
            from = hit + 1;
        }
    }

    // ------------------------------------------------------------------
    // Files + logging
    // ------------------------------------------------------------------

    private SharedPreferences prefs() {
        return getSharedPreferences("probe_ui", MODE_PRIVATE);
    }

    private File resultFile() {
        File dir = getExternalFilesDir(null);
        return (dir == null) ? null : new File(dir, "probe-result.txt");
    }

    private File logFile() {
        File dir = getExternalFilesDir(null);
        return (dir == null) ? null : new File(dir, "probe-log.txt");
    }

    // The C2 payloads ride in the APK under lib*.so names next to the
    // harness library; the renderer button exists only when this build
    // actually carries them (the workflow's harness=renderer mode).
    private boolean rendererPayloadPresent() {
        try {
            String libDir = getApplicationInfo().nativeLibraryDir;
            return libDir != null
                    && new File(libDir, "libsdl_gpu_frame_selfcheck.so").isFile()
                    && new File(libDir, "libsdl_gpu_depth_format_selfcheck.so").isFile();
        } catch (Throwable t) {
            return false;
        }
    }

    // The native shim reads this file at SDL_main; the first token is the
    // instrument name. A failed write leaves the shim at its gpu-probe
    // default, which the log's harness line then shows honestly.
    private void writeHarnessMode(String harness) {
        try {
            File dir = getExternalFilesDir(null);
            if (dir == null) {
                return;
            }
            File mode = new File(dir, "harness-mode.txt");
            try (FileOutputStream out = new FileOutputStream(mode, false)) {
                out.write((harness + "\n").getBytes("UTF-8"));
                out.getFD().sync();
            }
        } catch (Throwable ignored) {
            // Mode selection must never take the launcher down.
        }
    }

    private void appendLog(String msg) {
        try {
            File log = logFile();
            if (log == null) {
                return;
            }
            String line = timestampNow() + " [launcher] " + msg + "\n";
            try (FileOutputStream out = new FileOutputStream(log, true)) {
                out.write(line.getBytes("UTF-8"));
                out.getFD().sync();
            }
        } catch (Throwable ignored) {
            // Logging must never take the launcher down.
        }
    }

    // Raw multi-line append to the error log, no timestamp prefix -
    // used by the route B merge to fold the frame activity's own
    // output section into the forensic record verbatim.
    private void appendRawLog(String text) {
        try {
            File log = logFile();
            if (log == null) {
                return;
            }
            try (FileOutputStream out = new FileOutputStream(log, true)) {
                out.write(text.getBytes("UTF-8"));
                out.getFD().sync();
            }
        } catch (Throwable ignored) {
            // Logging must never take the launcher down.
        }
    }

    private static void deleteQuietly(File f) {
        try {
            if (f != null && f.isFile()) {
                f.delete();
            }
        } catch (Throwable ignored) {
            // A stale evidence file is untidy, never fatal.
        }
    }

    private static String timestampNow() {
        return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date());
    }

    // Upstream 3.4.16's Java layer ships SDLSensorManager; the host-staged
    // 3.4.2 layer does not (see the C0 record's deviation 5). A cheap,
    // honest marker of which Java layer this APK actually carries.
    private static String sdlJavaLayerGuess() {
        try {
            Class.forName("org.libsdl.app.SDLSensorManager");
            return "upstream-style (SDLSensorManager class present)";
        } catch (Throwable t) {
            return "host-staged-style (no SDLSensorManager class)";
        }
    }

    private static String readFully(File file) {
        try (FileInputStream in = new FileInputStream(file)) {
            byte[] data = new byte[(int) file.length()];
            int off = 0;
            int n;
            while (off < data.length && (n = in.read(data, off, data.length - off)) > 0) {
                off += n;
            }
            return new String(data, 0, off, "UTF-8");
        } catch (IOException e) {
            return "Could not read file: " + e.getMessage();
        }
    }

    private static String readTail(File file, int maxBytes) {
        try (RandomAccessFile raf = new RandomAccessFile(file, "r")) {
            long len = raf.length();
            if (len <= maxBytes) {
                return readFully(file);
            }
            raf.seek(len - maxBytes);
            byte[] data = new byte[maxBytes];
            raf.readFully(data);
            String text = new String(data, "UTF-8");
            int nl = text.indexOf('\n');
            return (nl >= 0 && nl + 1 < text.length()) ? text.substring(nl + 1) : text;
        } catch (IOException e) {
            return "Could not read file: " + e.getMessage();
        }
    }
}
