#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/fanotify.h>
#include <unistd.h>

#include <cerrno>
#include <unordered_map>

using namespace std;

static void handle_events(int fd) {
    const struct fanotify_event_metadata *metadata;
    struct fanotify_event_metadata buf[200];
    ssize_t len;
    char path[PATH_MAX];
    ssize_t path_len;
    char procfd_path[PATH_MAX];
    struct fanotify_response response;

    // fanotify fd 이벤트 처리
    for (;;) {
        // 이벤트 읽기
        len = read(fd, buf, sizeof(buf));
        if (len == -1 && errno != EAGAIN) {
            perror("read");
            exit(EXIT_FAILURE);
        }
        if (len <= 0)
            break;

        metadata = buf;
        // 버퍼 내 이벤트 모두 처리
        while (FAN_EVENT_OK(metadata, len)) {
            // 버전 체크
            if (metadata->vers != FANOTIFY_METADATA_VERSION) {
                fprintf(stderr, "Mismatch of fanotify metadata version.\n");
                exit(EXIT_FAILURE);
            }

            // queue overflow가 일어난 경우 metadata->fd에 FAN_NOFD가 기록됨
            // 아닌 경우 정상적인 fd가 기록됨
            if (metadata->fd >= 0) {
                if (metadata->mask & FAN_OPEN_PERM) {
                    printf("FAN_OPEN_PERM: ");

                    response.fd = metadata->fd;
                    response.response = FAN_ALLOW;
                    write(fd, &response, sizeof(response));
                }

                snprintf(procfd_path, sizeof(procfd_path),
                         "/proc/self/fd/%d", metadata->fd);
                path_len = readlink(procfd_path, path, sizeof(path) - 1);
                if (path_len = -1) {
                    perror("readlink");
                    exit(EXIT_FAILURE);
                }

                path[path_len] = '\0';
                printf("File %s\n", path);

                close(metadata->fd);
            }
            metadata = FAN_EVENT_NEXT(metadata, len);
        }
    }
}

int main(int argc, char *argv[]) {
    unordered_map<string, string> next_open_of;

    if (argc != 2) {
        fprintf(stderr, "Usage: ./opentrace <DIR_TO_TRACE>");
        exit(EXIT_FAILURE);
    }

    // 파일 액세스를 감지하는 이벤트 리스너 파일 디스크립터 생성
    int fanotify_fd = fanotify_init(
        FAN_CLOEXEC | FAN_CLASS_PRE_CONTENT | FAN_NONBLOCK,
        O_RDONLY | O_LARGEFILE);

    if (fanotify_fd == -1) {
        perror("fanotify_init");
        exit(EXIT_FAILURE);
    }

    // 이벤트 리스닝 범위 및 종류 마스킹
    if (fanotify_mark(
            fanotify_fd,                      // fd
            FAN_MARK_ADD | FAN_MARK_ONLYDIR,  // 동작 및 범위
            FAN_OPEN_PERM,                    // 감지 이벤트
            AT_FDCWD,                         // dirfd
            argv[1]) == -1) {                 // pathname
        perror("fanotify_mark");
        exit(EXIT_FAILURE);
    }

    // polling으로 stdin과 fanotify 이벤트 감지
    nfds_t nfds = 2;
    struct pollfd fds[2];

    fds[0].fd = STDIN_FILENO;
    fds[0].events = POLLIN;

    fds[1].fd = fanotify_fd;
    fds[1].events = POLLIN;

    // 이벤트 루프
    int poll_num;
    char buf;

    while (1) {
        poll_num = poll(fds, nfds, -1);
        if (poll_num == -1) {
            if (errno == EINTR)  // interrupted by signal
                continue;        // ignore
            perror("poll");
            exit(EXIT_FAILURE);
        }

        if (poll_num > 0) {
            if (fds[0].revents & POLLIN) {
                while (read(STDIN_FILENO, &buf, 1) > 0 && buf != '\n')
                    continue;
                break;
            }
            if (fds[1].revents & POLLIN) {
                handle_events(fanotify_fd);
            }
        }
    }

    printf("Listening for events stopped.\n");
    exit(EXIT_SUCCESS);
}