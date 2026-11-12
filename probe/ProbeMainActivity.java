package com.louay.zerohour.gpuprobe;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Typeface;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;

/**
 * Launcher screen for the stage-C0 GPU probe. Runs upstream's SDL probe as a
 * child SDLActivity and displays the capability table the native harness
 * leaves behind in probe-result.txt (this app's external files directory),
 * ready to screenshot. All UI is built in code; the app ships no resources.
 */
public class ProbeMainActivity extends Activity {

    private TextView mResultView;

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
            mResultView.setText("Running... the probe screen opens; when it finishes you return here and the table appears.");
            startActivity(new Intent(this, org.libsdl.app.SDLActivity.class));
        });
        root.addView(run);

        mResultView = new TextView(this);
        mResultView.setTypeface(Typeface.MONOSPACE);
        mResultView.setTextSize(11);
        mResultView.setTextIsSelectable(true);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(mResultView);
        root.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));

        setContentView(root);
        showResult();
    }

    @Override
    protected void onResume() {
        super.onResume();
        showResult();
    }

    private void showResult() {
        File dir = getExternalFilesDir(null);
        File result = (dir == null) ? null : new File(dir, "probe-result.txt");
        if (result != null && result.isFile()) {
            mResultView.setText(readFully(result));
        } else {
            mResultView.setText("No probe result yet.\n\n"
                    + "Tap \"Run GPU probe\". When the probe finishes you return "
                    + "here and the capability table appears on this screen - "
                    + "screenshot it.\n\n"
                    + "(The same table is saved as probe-result.txt in this "
                    + "app's files folder.)");
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
            return "Could not read result file: " + e.getMessage();
        }
    }
}
