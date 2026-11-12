/*
 * Android harness for upstream's sdl_gpu_probe (stage C, slice C0).
 *
 * This file is scaffolding, not probe logic. It provides the SDL_main entry
 * point SDLActivity calls, runs the probe (whose `main` is renamed to
 * `probe_main` at compile time — see CMakeLists.txt; the probe source itself
 * is byte-identical to upstream and SHA-256-verified in CI), captures
 * everything the probe prints, and leaves the evidence in three places:
 *
 *   - probe-result.txt in the app's external files directory: the captured
 *     stdout table, written when the probe returns — the launcher activity
 *     (ProbeMainActivity) displays it for screenshotting;
 *   - logcat, one SDL_Log call per table line;
 *   - probe-log.txt in the same directory: a crash-proof forensic log. A run
 *     section is appended BEFORE the probe starts, every stdout/stderr chunk
 *     is teed into it as it arrives (write + fdatasync per chunk), installed
 *     signal handlers append a CRASH line naming the signal if the probe
 *     dies by one, and a clean exit records its code. A native crash kills
 *     the process before probe-result.txt can be written — the log is what
 *     survives, and the launcher screen falls back to showing it.
 *
 * Device creation has two modes, chosen at build time (CMake option
 * PROBE_DEVICE_MODE; see CMakeLists.txt):
 *   - plain (default): the probe calls SDL_CreateGPUDevice exactly as
 *     upstream wrote it, with SDL's documented default requirements —
 *     which include the Vulkan core features depthClamp and
 *     shaderClipDistance.
 *   - compat: the probe TU is additionally compiled with
 *     -DSDL_CreateGPUDevice=probe_compat_create_gpu_device, so its one
 *     creation call lands in this file instead. The forwarder below has
 *     the plain call's exact signature, fills the same properties the
 *     plain call fills (SDL_gpu.c's SDL_GPU_FillProperties, mirrored),
 *     additionally sets the depth-clamping and clip-distance feature
 *     properties to false (SDL_gpu.h:2380-2381 — SDL's documented remedy
 *     for devices like the owner's Mali-G52, which implements neither
 *     feature; stage-c-c0-probe.md §8), and creates the device with
 *     SDL_CreateGPUDeviceWithProperties. The probe source file stays
 *     byte-identical in both modes; the run header in probe-log.txt
 *     names the mode that ran.
 */

#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>

#include <cstdio>
#include <cstring>
#include <ctime>
#include <fcntl.h>
#include <signal.h>
#include <string>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>

/* Defined by sdl_gpu_probe.cpp (its main, renamed at compile time). */
int probe_main();

#if defined(PROBE_DEVICE_COMPAT)
/*
 * Compat device creation (see the file header). Compiled only in compat
 * builds; the probe TU's -D rename makes SDL's own header declare this
 * symbol with the plain call's signature in the probe TU, and the
 * definition here must match it exactly: same parameter types, C linkage.
 *
 * The property filling mirrors SDL 3.4.16's SDL_GPU_FillProperties
 * (src/gpu/SDL_gpu.c) statement for statement — a shader-format boolean
 * is set true for each format flag the caller passed, the debug flag and
 * the (possibly NULL) driver name are passed through — and then the two
 * feature properties the plain call leaves at their default true are
 * set false. Nothing else is set: sampler anisotropy and indirect-draw
 * first instance keep SDL's defaults, because the Mali-G52 has both
 * (stage-c-c0-probe.md §8.4).
 */
extern "C" SDL_GPUDevice *probe_compat_create_gpu_device(SDL_GPUShaderFormat format_flags,
                                                         bool debug_mode,
                                                         const char *name)
{
    SDL_PropertiesID props = SDL_CreateProperties();
    if (format_flags & SDL_GPU_SHADERFORMAT_PRIVATE) {
        SDL_SetBooleanProperty(props, SDL_PROP_GPU_DEVICE_CREATE_SHADERS_PRIVATE_BOOLEAN, true);
    }
    if (format_flags & SDL_GPU_SHADERFORMAT_SPIRV) {
        SDL_SetBooleanProperty(props, SDL_PROP_GPU_DEVICE_CREATE_SHADERS_SPIRV_BOOLEAN, true);
    }
    if (format_flags & SDL_GPU_SHADERFORMAT_DXBC) {
        SDL_SetBooleanProperty(props, SDL_PROP_GPU_DEVICE_CREATE_SHADERS_DXBC_BOOLEAN, true);
    }
    if (format_flags & SDL_GPU_SHADERFORMAT_DXIL) {
        SDL_SetBooleanProperty(props, SDL_PROP_GPU_DEVICE_CREATE_SHADERS_DXIL_BOOLEAN, true);
    }
    if (format_flags & SDL_GPU_SHADERFORMAT_MSL) {
        SDL_SetBooleanProperty(props, SDL_PROP_GPU_DEVICE_CREATE_SHADERS_MSL_BOOLEAN, true);
    }
    if (format_flags & SDL_GPU_SHADERFORMAT_METALLIB) {
        SDL_SetBooleanProperty(props, SDL_PROP_GPU_DEVICE_CREATE_SHADERS_METALLIB_BOOLEAN, true);
    }
    SDL_SetBooleanProperty(props, SDL_PROP_GPU_DEVICE_CREATE_DEBUGMODE_BOOLEAN, debug_mode);
    SDL_SetStringProperty(props, SDL_PROP_GPU_DEVICE_CREATE_NAME_STRING, name);
    /* The whole point of compat mode: run without the two features the
       owner's Mali-G52 does not implement (SDL_gpu.h:2380-2381). */
    SDL_SetBooleanProperty(props, SDL_PROP_GPU_DEVICE_CREATE_FEATURE_CLIP_DISTANCE_BOOLEAN, false);
    SDL_SetBooleanProperty(props, SDL_PROP_GPU_DEVICE_CREATE_FEATURE_DEPTH_CLAMPING_BOOLEAN, false);
    SDL_GPUDevice *device = SDL_CreateGPUDeviceWithProperties(props);
    SDL_DestroyProperties(props);
    return device;
}
#endif /* PROBE_DEVICE_COMPAT */

namespace {

/* ------------------------------------------------------------------ */
/* Forensic log (probe-log.txt)                                        */
/* ------------------------------------------------------------------ */

constexpr long kLogCapBytes = 256 * 1024;  /* rotate when a run starts past this */
constexpr long kLogKeepBytes = 128 * 1024; /* tail window kept on rotation      */

std::string g_externalDir;                 /* resolved once, lazily (see below) */
volatile sig_atomic_t g_logFd = -1;        /* O_APPEND fd, or -1 when no log    */

std::string TimestampNow()
{
    char buf[32];
    std::time_t t = std::time(NULL);
    struct tm tmv;
    localtime_r(&t, &tmv);
    if (std::strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &tmv) == 0) {
        return "unknown-time";
    }
    return buf;
}

/* Append bytes to the log and push them to storage immediately: whatever a
   dying probe managed to print must already be in the file, not in a buffer. */
void LogRaw(const char *data, size_t len)
{
    int fd = static_cast<int>(g_logFd);
    if (fd < 0) {
        return;
    }
    size_t off = 0;
    while (off < len) {
        ssize_t w = write(fd, data + off, len - off);
        if (w <= 0) {
            break;
        }
        off += static_cast<size_t>(w);
    }
    fdatasync(fd);
}

void LogText(const std::string &s)
{
    LogRaw(s.data(), s.size());
}

void LogLine(const std::string &s)
{
    LogText(s);
    LogRaw("\n", 1);
}

/* Keep the log bounded across runs: when it has grown past the cap, rewrite
   it keeping only the newest run sections (from the first run header inside
   the last kLogKeepBytes) behind a rotation marker. Runs at probe start,
   before the append fd is opened. */
void RotateLogIfNeeded(const std::string &path)
{
    struct stat st;
    if (stat(path.c_str(), &st) != 0 || st.st_size <= kLogCapBytes) {
        return;
    }
    std::string tail;
    if (FILE *in = std::fopen(path.c_str(), "rb")) {
        long start = static_cast<long>(st.st_size) - kLogKeepBytes;
        if (start > 0 && std::fseek(in, start, SEEK_SET) == 0) {
            char buf[8192];
            size_t n;
            while ((n = std::fread(buf, 1, sizeof(buf), in)) > 0) {
                tail.append(buf, n);
            }
        }
        std::fclose(in);
    }
    /* The first run-OPENING header inside the window (the run-end line
       shares the "===== probe run " prefix but continues with "end"). */
    size_t hdr = std::string::npos;
    for (size_t pos = tail.find("===== probe run "); pos != std::string::npos;
         pos = tail.find("===== probe run ", pos + 1)) {
        if (tail.compare(pos, 19, "===== probe run end") != 0) {
            hdr = pos;
            break;
        }
    }
    std::string kept = (hdr == std::string::npos) ? std::string() : tail.substr(hdr);
    if (FILE *out = std::fopen(path.c_str(), "wb")) {
        char marker[192];
        std::snprintf(marker, sizeof(marker),
                      "[harness] log rotated: file was %lld bytes (cap %ld); oldest runs dropped\n",
                      static_cast<long long>(st.st_size), kLogCapBytes);
        std::fputs(marker, out);
        if (!kept.empty()) {
            std::fwrite(kept.data(), 1, kept.size(), out);
        }
        std::fclose(out);
    }
}

/* ------- crash marker: async-signal-safe appends only ------- */

void BufAppendStr(char *&p, const char *s)
{
    while (*s) {
        *p++ = *s++;
    }
}

void BufAppendUint(char *&p, unsigned long v)
{
    char tmp[24];
    int i = 0;
    do {
        tmp[i++] = static_cast<char>('0' + (v % 10));
        v /= 10;
    } while (v != 0);
    while (i > 0) {
        *p++ = tmp[--i];
    }
}

void BufAppendHex(char *&p, unsigned long v)
{
    *p++ = '0';
    *p++ = 'x';
    char tmp[16];
    int i = 0;
    do {
        unsigned long d = v & 0xFul;
        tmp[i++] = static_cast<char>(d < 10 ? '0' + d : 'a' + (d - 10));
        v >>= 4;
    } while (v != 0);
    while (i > 0) {
        *p++ = tmp[--i];
    }
}

/* Last forensic act of a dying process: name the signal and the fault
   address, using write() only (async-signal-safe), then restore the default
   disposition and re-raise so the process dies exactly as it would have
   without us (Android still gets its tombstone). */
void CrashSignalHandler(int sig, siginfo_t *info, void * /*context*/)
{
    int fd = static_cast<int>(g_logFd);
    if (fd >= 0) {
        char buf[224];
        char *p = buf;
        BufAppendStr(p, "[harness] CRASH: signal ");
        BufAppendUint(p, static_cast<unsigned long>(sig));
        BufAppendStr(p, " at address ");
        BufAppendHex(p, static_cast<unsigned long>(
                            reinterpret_cast<uintptr_t>(info ? info->si_addr : NULL)));
        BufAppendStr(p, " -- the probe did not return; whatever it printed is above\n");
        ssize_t r = write(fd, buf, static_cast<size_t>(p - buf));
        (void)r;
        fsync(fd);
    }
    signal(sig, SIG_DFL);
    raise(sig);
    _exit(128 + sig);
}

void InstallCrashHandlers()
{
    struct sigaction sa;
    std::memset(&sa, 0, sizeof(sa));
    sa.sa_sigaction = CrashSignalHandler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_SIGINFO;
    const int sigs[] = {SIGSEGV, SIGABRT, SIGBUS, SIGFPE, SIGILL};
    for (int s : sigs) {
        sigaction(s, &sa, NULL);
    }
}

/* ------------------------------------------------------------------ */
/* Output capture                                                      */
/* ------------------------------------------------------------------ */

std::string g_captured;

/* Drain one captured stream. The stdout stream also feeds the result-table
   capture; every chunk of either stream is teed into the forensic log the
   moment it arrives. */
void DrainPipe(int fd, bool intoCapture)
{
    char buffer[4096];
    ssize_t n;
    while ((n = read(fd, buffer, sizeof(buffer))) > 0) {
        LogRaw(buffer, static_cast<size_t>(n));
        if (intoCapture) {
            g_captured.append(buffer, static_cast<size_t>(n));
        }
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

/* The app's external files directory, resolved once. NULL from SDL (JNI not
   ready) leaves the harness logcat-only for that run instead of failing. */
const std::string &ExternalDir()
{
    if (g_externalDir.empty()) {
        const char *external = SDL_GetAndroidExternalStoragePath();
        if (external != NULL) {
            g_externalDir = external;
            if (!g_externalDir.empty() && g_externalDir.back() != '/') {
                g_externalDir += '/';
            }
        }
    }
    return g_externalDir;
}

void WriteResultFile(const std::string &text)
{
    const std::string &dir = ExternalDir();
    if (dir.empty()) {
        SDL_Log("probe harness: no external storage path; result is in logcat only");
        return;
    }
    std::string path = dir + "probe-result.txt";
    if (FILE *f = std::fopen(path.c_str(), "w")) {
        std::fputs(text.c_str(), f);
        std::fclose(f);
        SDL_Log("probe harness: wrote %s", path.c_str());
    } else {
        SDL_Log("probe harness: could not open %s for writing", path.c_str());
    }
}

/* Open the forensic log for this run (rotating first if needed) and write
   the run header + start record BEFORE the probe runs, so even a probe that
   dies on its first instruction leaves a marked, dated section behind. */
void OpenLog()
{
    const std::string &dir = ExternalDir();
    if (dir.empty()) {
        SDL_Log("probe harness: no external storage path; forensic log unavailable this run");
        return;
    }
    std::string path = dir + "probe-log.txt";
    RotateLogIfNeeded(path);
    int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (fd < 0) {
        SDL_Log("probe harness: could not open %s; forensic log unavailable this run", path.c_str());
        return;
    }
    g_logFd = fd;

    char header[256];
    std::snprintf(header, sizeof(header), "===== probe run %s (pid %d) =====\n",
                  TimestampNow().c_str(), static_cast<int>(getpid()));
    LogText(header);
    int linked = SDL_GetVersion();
    char versions[192];
    std::snprintf(versions, sizeof(versions),
                  "[harness] probe starting; SDL compiled %d.%d.%d, linked %d.%d.%d\n",
                  SDL_MAJOR_VERSION, SDL_MINOR_VERSION, SDL_MICRO_VERSION,
                  linked / 1000000, (linked / 1000) % 1000, linked % 1000);
    LogText(versions);
#if defined(PROBE_DEVICE_COMPAT)
    LogText("[harness] device mode: compat (SDL_CreateGPUDeviceWithProperties; "
            "feature.depth_clamping=false, feature.clip_distance=false)\n");
#else
    LogText("[harness] device mode: plain (SDL_CreateGPUDevice with SDL defaults)\n");
#endif
}

} // namespace

int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;

    OpenLog();
    InstallCrashHandlers();

    int exit_code;
    int out_fds[2] = {-1, -1};
    int err_fds[2] = {-1, -1};
    bool captureOut = (pipe(out_fds) == 0);
    if (captureOut) {
        int saved_stdout = dup(STDOUT_FILENO);
        dup2(out_fds[1], STDOUT_FILENO);
        /* Unbuffered: every printf the probe makes reaches the pipe at once,
           and the reader thread drains it concurrently (no pipe-full stall). */
        std::setvbuf(stdout, NULL, _IONBF, 0);
        std::thread drainOut(DrainPipe, out_fds[0], true);

        /* stderr gets its own pipe and drain: its chunks are teed into the
           forensic log like stdout's, but kept out of the clean result
           table (driver noise does not belong in the capability table). */
        int saved_stderr = -1;
        std::thread drainErr;
        bool captureErr = (pipe(err_fds) == 0);
        if (captureErr) {
            saved_stderr = dup(STDERR_FILENO);
            dup2(err_fds[1], STDERR_FILENO);
            drainErr = std::thread(DrainPipe, err_fds[0], false);
        }

        exit_code = probe_main();

        std::fflush(stdout);
        std::fflush(stderr);
        dup2(saved_stdout, STDOUT_FILENO);
        close(out_fds[1]);
        close(saved_stdout);
        drainOut.join();
        close(out_fds[0]);
        if (captureErr) {
            dup2(saved_stderr, STDERR_FILENO);
            close(err_fds[1]);
            close(saved_stderr);
            drainErr.join();
            close(err_fds[0]);
        }
    } else {
        /* Capture unavailable: still run the probe so its exit code and its
           own stdout destination carry what they can. */
        LogLine("[harness] stdout capture unavailable this run (pipe failed); probe runs uncaptured");
        exit_code = probe_main();
        g_captured = "(stdout capture unavailable in harness; probe ran without capture)\n";
    }

    {
        char tail[192];
        std::snprintf(tail, sizeof(tail), "[harness] probe exited normally; exit code %d\n",
                      exit_code);
        LogText(tail);
        LogLine("===== probe run end " + TimestampNow() + " =====");
    }
    if (g_logFd >= 0) {
        close(static_cast<int>(g_logFd));
        g_logFd = -1;
    }

    SDL_Log("=== sdl_gpu_probe output (exit code %d) ===", exit_code);
    LogLineByLine(g_captured);
    SDL_Log("=== sdl_gpu_probe end ===");
    WriteResultFile(g_captured);
    return exit_code;
}
