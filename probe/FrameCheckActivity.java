package com.louay.zerohour.gpuprobe;

import org.libsdl.app.SDLActivity;

/**
 * Stage C2, route B (stage-c-c1-plan.md section 10): the activity that
 * runs the Reforged engine's frame selfcheck.
 *
 * The selfcheck is packaged as a shared library,
 * libsdl_gpu_frame_selfcheck.so, whose SDL_main is the selfcheck body
 * wrapped by the entry TU in the frame-entry patch: that wrapper
 * redirects the body's output into frame-result.txt in this app's
 * external files directory and appends the body's return code there,
 * because an activity process's stdout is logcat, which the launcher
 * cannot read. ProbeMainActivity chains this activity after the
 * harness activity (which runs the depth selfcheck) and merges
 * frame-result.txt into probe-log.txt and the displayed verdict.
 *
 * The only customisation SDLActivity needs is the library list:
 * loading just the selfcheck library makes getMainSharedObject()
 * resolve to it (SDLActivity's default takes the last listed
 * library), and its JNI_OnLoad — from the engine's own statically
 * linked SDL 3.4.16, the same version as this Java layer — registers
 * the SDLActivity natives. No separate SDL3 library is loaded: the
 * payload carries its SDL inside itself.
 *
 * This activity runs in its own process (see the manifest's
 * android:process=":framecheck"), so the payload's SDL never shares
 * a process with the harness's shared SDL — two SDL implementations
 * in one process is the hazard the stage-C plan flags, avoided here
 * by isolation. It is also the entry model the real game will use:
 * SDLActivity + a library exporting SDL_main, nothing else.
 */
public class FrameCheckActivity extends SDLActivity {

    @Override
    protected String[] getLibraries() {
        return new String[] { "sdl_gpu_frame_selfcheck" };
    }
}
