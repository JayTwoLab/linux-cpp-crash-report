#include <execinfo.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>
#include <cerrno>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace Linux {

class CrashReporter {
public:
    enum class DumpDirMode {
        ExeDir, // 실행 파일(/proc/self/exe) 위치 기준 <exe_dir>/<sub_dir> 자동 설정 및 생성
        Manual  // manual_dir 경로를 수동으로 설정 및 생성
    };

    struct Config {
        DumpDirMode mode = DumpDirMode::ExeDir;
        const char* sub_dir = "dump";     // DumpDirMode::ExeDir 일 때 사용할 하위 폴더명
        const char* manual_dir = nullptr; // DumpDirMode::Manual 일 때 사용할 직접 지정 경로
        bool create_if_missing = true;    // 디렉터리가 없으면 생성할지 여부
    };

    static bool init(const Config& cfg) {
        if (cfg.mode == DumpDirMode::Manual) {
            return set_dump_dir(cfg.manual_dir, cfg.create_if_missing);
        }
        return init_from_executable_dir(cfg.sub_dir, cfg.create_if_missing);
    }

    static bool init_from_executable_dir(const char* sub_dir = "dump", bool create_if_missing = true) {
        char exe_path[PATH_MAX];
        ssize_t len = ::readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
        if (len <= 0) {
            s_dump_dir[0] = '\0';
            return false;
        }
        exe_path[len] = '\0';

        // 실행 파일 경로에서 마지막 '/'를 찾아 디렉터리 경로만 추출
        char* slash = std::strrchr(exe_path, '/');
        if (slash == nullptr) {
            s_dump_dir[0] = '\0';
            return false;
        }

        if (slash == exe_path) {
            exe_path[1] = '\0';
        } else {
            *slash = '\0';
        }

        const char* sub = (sub_dir != nullptr && sub_dir[0] != '\0') ? sub_dir : "dump";

        char target_dir[PATH_MAX];
        int written;
        if (std::strcmp(exe_path, "/") == 0) {
            written = std::snprintf(target_dir, sizeof(target_dir), "/%s", sub);
        } else {
            written = std::snprintf(target_dir, sizeof(target_dir), "%s/%s", exe_path, sub);
        }

        if (written < 0 || static_cast<size_t>(written) >= sizeof(target_dir)) {
            s_dump_dir[0] = '\0';
            return false;
        }

        return set_dump_dir(target_dir, create_if_missing);
    }

    static bool set_dump_dir(const char* dir, bool create_if_missing = true) {
        if (dir == nullptr || dir[0] == '\0') {
            s_dump_dir[0] = '\0';
            return false;
        }

        char normalized[PATH_MAX];
        int n = std::snprintf(normalized, sizeof(normalized), "%s", dir);
        if (n < 0 || static_cast<size_t>(n) >= sizeof(normalized)) {
            s_dump_dir[0] = '\0';
            return false;
        }

        // 끝부분의 불필요한 '/' 제거 (단, 루트 "/" 자체는 유지)
        size_t len = std::strlen(normalized);
        while (len > 1 && normalized[len - 1] == '/') {
            normalized[--len] = '\0';
        }

        if (create_if_missing) {
            if (!ensure_directory_exists(normalized)) {
                s_dump_dir[0] = '\0';
                return false;
            }
        } else {
            struct stat st;
            if (::stat(normalized, &st) != 0 || !S_ISDIR(st.st_mode)) {
                s_dump_dir[0] = '\0';
                return false;
            }
        }

        std::snprintf(s_dump_dir, sizeof(s_dump_dir), "%s", normalized);
        return true;
    }

    static const char* dump_dir() {
        return s_dump_dir;
    }

    static void install_handlers() {
        ::signal(SIGSEGV, &CrashReporter::on_signal);
        ::signal(SIGABRT, &CrashReporter::on_signal);
        ::signal(SIGFPE, &CrashReporter::on_signal);
        ::signal(SIGILL, &CrashReporter::on_signal);
    }

private:
    static char s_dump_dir[PATH_MAX];

    static bool ensure_directory_exists(const char* path) {
        if (path == nullptr || path[0] == '\0') {
            return false;
        }

        char tmp[PATH_MAX];
        int n = std::snprintf(tmp, sizeof(tmp), "%s", path);
        if (n < 0 || static_cast<size_t>(n) >= sizeof(tmp)) {
            return false;
        }

        size_t len = std::strlen(tmp);
        while (len > 1 && tmp[len - 1] == '/') {
            tmp[--len] = '\0';
        }

        // 중간 경로까지 포함해 mkdir -p 형태로 생성
        for (char* p = tmp + 1; *p != '\0'; ++p) {
            if (*p == '/') {
                *p = '\0';
                if (::mkdir(tmp, 0755) != 0 && errno != EEXIST) {
                    return false;
                }
                *p = '/';
            }
        }

        if (::mkdir(tmp, 0755) != 0 && errno != EEXIST) {
            return false;
        }

        struct stat st;
        return (::stat(tmp, &st) == 0 && S_ISDIR(st.st_mode));
    }

    static void on_signal(int sig) {
        time_t now = time(nullptr);
        struct tm tm_info;
        localtime_r(&now, &tm_info);

        int fd = STDERR_FILENO;

        if (s_dump_dir[0] != '\0') {
            char file_path[PATH_MAX];
            int written = std::snprintf(
                file_path, sizeof(file_path),
                "%s/crash_%04d%02d%02d_%02d%02d%02d.log",
                s_dump_dir,
                tm_info.tm_year + 1900, tm_info.tm_mon + 1, tm_info.tm_mday,
                tm_info.tm_hour, tm_info.tm_min, tm_info.tm_sec);

            if (written > 0 && static_cast<size_t>(written) < sizeof(file_path)) {
                int opened = open(file_path, O_CREAT | O_WRONLY | O_APPEND, 0644);
                if (opened >= 0) {
                    fd = opened;
                }
            }
        }

        char header[256];
        int header_len = std::snprintf(
            header, sizeof(header),
            "========================================\n"
            "[CRASH REPORT]\n"
            "Time   : %04d-%02d-%02d %02d:%02d:%02d\n"
            "Signal : %d\n"
            "PID    : %d\n"
            "========================================\n"
            "Backtrace:\n",
            tm_info.tm_year + 1900, tm_info.tm_mon + 1, tm_info.tm_mday,
            tm_info.tm_hour, tm_info.tm_min, tm_info.tm_sec,
            sig,
            static_cast<int>(getpid()));

        if (header_len > 0) {
            write(fd, header, static_cast<size_t>(header_len));
        }

        void* callstack[64];
        const int frames = backtrace(callstack, 64);
        backtrace_symbols_fd(callstack, frames, fd);

        if (fd != STDERR_FILENO) {
            close(fd);
        }

        // 기본 시그널 핸들러로 되돌린 뒤 재발생시켜 원래 종료 코드(139 등) 유지
        ::signal(sig, SIG_DFL);
        ::raise(sig);
    }
};

char CrashReporter::s_dump_dir[PATH_MAX] = {0};

} // namespace Linux

namespace {

void trigger_crash() {
    int* ptr = nullptr; // Initialize pointer to nullptr
    *ptr = 10; // crashes the program because ptr is nullptr and dereferencing it is undefined behavior
}

} // namespace

int main(int argc, char* argv[]) {
    (void)argc;
    (void)argv;

    // 옵션 선택:
    // 1) 실행 파일 경로 기준 <exe_dir>/dump 자동 설정 및 생성
    Linux::CrashReporter::Config cfg;
    cfg.mode = Linux::CrashReporter::DumpDirMode::ExeDir;
    cfg.sub_dir = "dump";
    cfg.create_if_missing = true;

    // 2) 수동 경로 지정이 필요할 때는 위 mode를 Manual로 바꾸고 manual_dir 지정:
    // cfg.mode = Linux::CrashReporter::DumpDirMode::Manual;
    // cfg.manual_dir = "/home/jaytwo/workspace/coredump/dump";
    // cfg.create_if_missing = true;

    if (!Linux::CrashReporter::init(cfg)) {
        std::fprintf(stderr, "[WARN] dump directory configuration failed; replaced with STDERR.\n");
        return 1;
    }

    Linux::CrashReporter::install_handlers();

    trigger_crash(); // This will cause a segmentation fault and invoke the crash reporter

    return 0;
}
