#include <errno.h>
#include <linux/fcntl.h>
#include <linux/limits.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/fanotify.h>
#include <sys/signalfd.h>
#include <unistd.h>

#include <string>
#include <unordered_map>

std::unordered_map<std::string, std::string> hist;
std::string latest_opened_file;

static uint64_t event_mask = (FAN_OPEN | FAN_EVENT_ON_CHILD);

static int handle_events(int fd) {
    const struct fanotify_event_metadata *metadata;
    struct fanotify_event_metadata buf[200];
    ssize_t len;

    char procfd_path[PATH_MAX];
    char path[PATH_MAX];
    ssize_t path_len;

    for (;;) {
        // fanotify fd 이벤트 처리
        if ((len = read(fd, buf, sizeof(buf))) > 0) {
            metadata = buf;
            // 버퍼 내 이벤트 모두 처리
            while (FAN_EVENT_OK(metadata, len)) {
                // 버전 체크
                if (metadata->vers != FANOTIFY_METADATA_VERSION) {
                    fprintf(stderr, "Mismatch of fanotify metadata version.\n");
                    return -1;
                }

                if (metadata->mask & FAN_Q_OVERFLOW) {
                    fprintf(stderr, "Queue Overflow!!");
                    // return -1;
                }

                if (metadata->fd == FAN_NOFD) {
                    fprintf(stderr, "FAN_NOFD Detected!");
                    // return -1;
                }

                // queue overflow가 일어난 경우 metadata->fd에 FAN_NOFD가 기록됨
                // 아닌 경우 정상적인 fd가 기록됨
                if (metadata->fd >= 0) {
                    if (metadata->mask & FAN_OPEN) {
                        printf("FAN_OPEN: ");

                        snprintf(procfd_path, sizeof(procfd_path),
                                 "/proc/self/fd/%d", metadata->fd);
                        path_len = readlink(procfd_path, path, sizeof(path) - 1);
                        if (path_len == -1) {
                            perror("readlink");
                            exit(EXIT_FAILURE);
                        }

                        path[path_len] = '\0';
                        printf("File %s\n", path);

                        close(metadata->fd);
                        fflush(stdout);
                    }
                }
                metadata = FAN_EVENT_NEXT(metadata, len);
            }
        }

        if (len <= 0)
            break;
    }

    return 0;
}

static int initialize_fanotify(char *pathname) {
    // 파일 액세스를 감지하는 이벤트 리스너 파일 디스크립터
    int fanotify_fd = fanotify_init(
        FAN_CLOEXEC | FAN_CLASS_PRE_CONTENT | FAN_NONBLOCK,
        O_CLOEXEC | O_RDONLY | O_LARGEFILE);

    if (fanotify_fd == -1) {
        perror("fanotify_init");
        return -1;
    }

    // 이벤트 리스닝 범위 및 종류 마스킹
    if (fanotify_mark(
            fanotify_fd,        // fd
            FAN_MARK_ADD,       // 동작 및 범위
            event_mask,         // 감지 이벤트
            AT_FDCWD,           // dirfd
            pathname) == -1) {  // pathname
        perror("fanotify_mark");
        return -1;
    }

    return fanotify_fd;
}

static void shutdown_fanotify(int fanotify_fd, char *pathname) {
    fanotify_mark(
        fanotify_fd,      // fd
        FAN_MARK_REMOVE,  // 동작 및 범위
        event_mask,       // 감지 이벤트
        AT_FDCWD,         // dirfd
        pathname);

    close(fanotify_fd);
}

static int initialize_signals() {
    int signal_fd;
    sigset_t sigmask;

    sigemptyset(&sigmask);
    sigaddset(&sigmask, SIGINT);
    sigaddset(&sigmask, SIGTERM);

    if (sigprocmask(SIG_BLOCK, &sigmask, NULL) < 0) {
        fprintf(stderr, "Couldn't block signals: %s\n", strerror(errno));
        return -1;
    }

    if ((signal_fd = signalfd(-1, &sigmask, 0)) < 0) {
        fprintf(stderr, "Couldnt' setup signal fd: %s\n", strerror(errno));
        return -1;
    }

    return signal_fd;
}

static void shutdown_signals(int signal_fd) {
    close(signal_fd);
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: ./opentrace <DIR_TO_TRACE>");
        exit(EXIT_FAILURE);
    }

    int signal_fd;
    int fanotify_fd;

    if ((signal_fd = initialize_signals()) < 0) {
        fprintf(stderr, "Couldn't initialize signals\n");
        exit(EXIT_FAILURE);
    }

    if ((fanotify_fd = initialize_fanotify(argv[1])) < 0) {
        fprintf(stderr, "Couldn't initialize fanotify\n");
        exit(EXIT_FAILURE);
    }

    // polling으로 stdin과 fanotify 이벤트 감지
    nfds_t nfds = 2;
    struct pollfd fds[2];

    enum {
        FD_POLL_SIGNAL = 0,
        FD_POLL_FANOTIFY
    };

    fds[FD_POLL_SIGNAL].fd = signal_fd;
    fds[FD_POLL_SIGNAL].events = POLLIN;
    fds[FD_POLL_FANOTIFY].fd = fanotify_fd;
    fds[FD_POLL_FANOTIFY].events = POLLIN;

    // 이벤트 루프
    while (1) {
        if (poll(fds, nfds, -1) < 0) {
            fprintf(stderr, "Couldn't poll(): %s\n", strerror(errno));
            exit(EXIT_FAILURE);
        }

        if (fds[FD_POLL_SIGNAL].revents & POLLIN) {
            struct signalfd_siginfo sfdi;

            if (read(fds[FD_POLL_SIGNAL].fd, &sfdi, sizeof(sfdi) != sizeof(sfdi))) {
                fprintf(stderr, "Coudln't read signal, wrong size read\n");
                exit(EXIT_FAILURE);
            }

            if (sfdi.ssi_signo == SIGINT || sfdi.ssi_signo == SIGTERM) {
                break;
            } else {
                fprintf(stderr, "Received unexpected signal %d\n", sfdi.ssi_signo);
            }
        }

        if (fds[FD_POLL_FANOTIFY].revents & POLLIN) {
            if (handle_events(fds[FD_POLL_FANOTIFY].fd) < 0) {
                fprintf(stderr, "Fanotify event handling failed!\n");
                break;
            }
        }
    }

    // shutdown_fanotify(fanotify_fd, argv[1]);
    shutdown_signals(signal_fd);

    printf("Listening for events stopped.\n");
    exit(EXIT_SUCCESS);
}