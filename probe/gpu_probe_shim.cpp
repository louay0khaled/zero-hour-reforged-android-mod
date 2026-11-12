/*
 * Android harness for upstream's sdl_gpu_probe (stage C, slice C0).
 *
 * This file is scaffolding, not probe logic. It provides the SDL_main entry
 * point SDLActivity calls, runs the probe (whose `main` is renamed to
 * `probe_main` at compile time — see CMakeLists.txt; the probe source itself
 * is byte-identical to upstream and SHA-256-verified in CI), captures
 * everything the probe prints to stdout, and leaves the captured table in two
 * places:
 *   - probe-result.txt in the app's external files directory, which the
 *     launcher activity (ProbeMainActivity) displays for screenshotting;
 *   - logcat, one SDL_Log call per table line.
 */

#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>

#include <cstdio>
#include <string>
#include <thread>
#include <unistd.h>

/* Defined by sdl_gpu_probe.cpp (its main, renamed at compile time). */
int probe_main();

namespace {

std::string g_captured;

void DrainStdout(int fd)
{
    char buffer[4096];
    ssize_t n;
    while ((n = read(fd, buffer, sizeof(buffer))) > 0) {
        g_captured.append(buffer, static_cast<size_t>(n));
    }
}

void LogLineByLine(const std::string &text)
{
    size_t start = 0;
    while (start < text.size()) {
        size_t end = text.find('\n', start);
        if (end == std::string::npos) {
            end = text.size();
        }
        SDL_Log("%s", text.substr(start, end - start).c_str());
        start = end + 1;
    }
}

void WriteResultFile(const std::string &text)
{
    const char *external = SDL_GetAndroidExternalStoragePath();
    if (external == NULL) {
        SDL_Log("probe harness: no external storage path; result is in logcat only");
        return;
    }
    std::string path = external;
    if (!path.empty() && path.back() != '/') {
        path += '/';
    }
    path += "probe-result.txt";
    if (FILE *f = std::fopen(path.c_str(), "w")) {
        std::fputs(text.c_str(), f);
        std::fclose(f);
        SDL_Log("probe harness: wrote %s", path.c_str());
    } else {
        SDL_Log("probe harness: could not open %s for writing", path.c_str());
    }
}

} // namespace

int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;

    int exit_code;
    int pipe_fds[2];
    if (pipe(pipe_fds) == 0) {
        int saved_stdout = dup(STDOUT_FILENO);
        dup2(pipe_fds[1], STDOUT_FILENO);
        /* Unbuffered: every printf the probe makes reaches the pipe at once,
           and the reader thread drains it concurrently (no pipe-full stall). */
        std::setvbuf(stdout, NULL, _IONBF, 0);
        std::thread drain(DrainStdout, pipe_fds[0]);
        exit_code = probe_main();
        std::fflush(stdout);
        dup2(saved_stdout, STDOUT_FILENO);
        close(pipe_fds[1]);
        close(saved_stdout);
        drain.join();
        close(pipe_fds[0]);
    } else {
        /* Capture unavailable: still run the probe so its exit code and its
           own stdout destination carry what they can. */
        exit_code = probe_main();
        g_captured = "(stdout capture unavailable in harness; probe ran without capture)\n";
    }

    SDL_Log("=== sdl_gpu_probe output (exit code %d) ===", exit_code);
    LogLineByLine(g_captured);
    SDL_Log("=== sdl_gpu_probe end ===");
    WriteResultFile(g_captured);
    return exit_code;
}
