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
 * Launcher screen for the stage-C0 GPU probe. Runs upstream's SDL probe as a
 * child SDLActivity and displays the capability table the native harness
 * leaves behind in probe-result.txt (this app's external files directory),
 * ready to screenshot. All UI is built in code; the app ships no resources.
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
        title.setText("Reforged GPU Probe (stage C0)");
        title.setTextSize(18);
        root.addView(title);

        Button run = new Button(this);
        run.setText("Run GPU probe");
        run.setOnClickListener(v -> {
            long now = System.currentTimeMillis();
            prefs().edit().putLong("run_started_at", now).apply();
            appendLog("starting probe activity (Run tapped)");
            mLaunchedChild = true;
            mMode = MODE_AUTO;
            mResultView.setText("Running... the probe screen opens; when it finishes you return here and the table appears.");
            startActivity(new Intent(this, org.libsdl.app.SDLActivity.class));
        });
        root.addView(run);

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

    @Override
    protected void onResume() {
        super.onResume();
        if (mLaunchedChild) {
            mLaunchedChild = false;
            File result = resultFile();
            long startedAt = prefs().getLong("run_started_at", 0);
            if (isFreshResult(result, startedAt)) {
                appendLog("resumed; fresh probe result present (" + result.length() + " bytes)");
            } else {
                appendLog("resumed WITHOUT a fresh probe result - the last run left no table");
            }
        }
        showContent();
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
        return "No probe result yet.\n\n"
                + "Tap \"Run GPU probe\". When the probe finishes you return "
                + "here and the capability table appears on this screen - "
                + "screenshot it.\n\n"
                + "(The same table is saved as probe-result.txt in this "
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
                Math.max(tail.lastIndexOf("CRASH:"),
                        tail.lastIndexOf("===== probe run end")));
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
