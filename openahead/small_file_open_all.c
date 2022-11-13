// 동작: 4kb 작은 파일을 모두 열고, 모두 읽는 시간을 각각 측정한다.
// 목적: upper bound로 단축 가능한 open 오버헤드를 확인한다.

#include <dirent.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

double get_time() {
    double ms;
    int s;
    struct timespec spec;

    clock_gettime(CLOCK_REALTIME, &spec);
    s = spec.tv_sec;
    ms = spec.tv_nsec / 10e8;
    return s + ms;
}

int main(int argc, char* argv[]) {
    char buf[BUFSIZ];
    char* dirpath;
    char filepath[FILENAME_MAX];
    DIR* dir;
    struct dirent* ent;
    int file_count = 0;
    int status;

    dirpath = argv[1];
    strcat(dirpath, "/");
    if ((dir = opendir(dirpath)) == NULL) {
        perror("opendir");
    }

    while ((ent = readdir(dir)) != NULL) {
        if (!strncmp(ent->d_name, ".", 1)) continue;
        file_count++;
    }

    int fd[file_count];
    double start_time[file_count];
    double end_time[file_count];
    int index = 0;

    seekdir(dir, SEEK_SET);

    double total_start_time = get_time();
    while ((ent = readdir(dir)) != NULL) {
        if (!strncmp(ent->d_name, ".", 1)) continue;
        memset(filepath, 0, sizeof(filepath));
        strcpy(filepath, argv[1]);
        strcat(filepath, ent->d_name);
        // printf("open: %s\n", ent->d_name);
        if ((fd[index++] = open(filepath, O_RDONLY)) == -1) {
            perror("open file failed");
        }
    }
    double total_end_time = get_time();

    printf("open %d small file total time: %lf\n", file_count, total_end_time - total_start_time);

    total_start_time = get_time();
    for (index = 0; index < file_count; index++) {
        start_time[index] = get_time();
        if ((status = read(fd[index], buf, BUFSIZ)) == -1) {
            perror("read failed");
        }
        end_time[index] = get_time();
        memset(buf, 0, sizeof(buf));
    }
    total_end_time = get_time();

    printf("read %d small file total time: %lf\n", file_count, total_end_time - total_start_time);

    return 0;
}
