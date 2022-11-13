// 동작: 2회 순차 열고 읽기를 수행한다. 이때 첫 번째에는 직후 열린 파일을 기록하고, 두 번째에는 기록을 바탕으로 파일을 미리 연다.
// 목적
// - openahead의 성능 향상 가능성 확인
// - inode, dnode 캐시 유무에 따른 openahead의 성능 향상 기여도 확인

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
    int sz;

    dirpath = argv[1];
    strcat(dirpath, "/");
    if ((dir = opendir(dirpath)) == NULL) {
        perror("opendir");
    }

    while ((ent = readdir(dir)) != NULL) {
        if (!strncmp(ent->d_name, ".", 1)) continue;
        file_count++;
    }

    
    int index = 0;

    int fd[file_count];
    char next_opened_filepath[file_count][FILENAME_MAX];

    double start_time[file_count], end_time[file_count];
    double total_read_time, read_start_time, read_end_time;
    double total_open_time, open_start_time, open_end_time;
    
    memset(next_opened_filepath, 0, sizeof(next_opened_filepath));

    // int drop_cache_fd = open("/proc/sys/vm/drop_caches", O_WRONLY);
    for (int loop = 1; loop < 3; loop++) {
        // sync();
        // sleep(5);
        // write(drop_cache_fd, "3", 1);
        // sleep(5);

        seekdir(dir, SEEK_SET);
        memset(fd, 0, sizeof(fd));
        index = 0;
        total_read_time = 0;
        total_open_time = 0;

        // double total_start_time = get_time();
        while ((ent = readdir(dir)) != NULL) {
            if (!strncmp(ent->d_name, ".", 1)) continue;
            memset(filepath, 0, sizeof(filepath));
            strcpy(filepath, argv[1]);
            strcat(filepath, ent->d_name);

            // start_time[index] = get_time();

            open_start_time = get_time();
            if (!fd[index] && ((fd[index] = open(filepath, O_RDONLY)) == -1)) {
                perror("open file failed");
            }

            // openahead next single file
            if (next_opened_filepath[index][0] != '\0') {
                if((fd[index + 1] = open(next_opened_filepath[index], O_RDONLY)) == -1){
                    perror("openahead failed");
                }
            }
            open_end_time = get_time();

            if (index != 0) {
                strcpy(next_opened_filepath[index - 1], filepath);
            }

            read_start_time = get_time();
            if ((sz = read(fd[index], buf, BUFSIZ)) == -1) {
                perror("read failed");
            }
            read_end_time = get_time();

            total_open_time += open_end_time - open_start_time;
            total_read_time += read_end_time - read_start_time;

            // end_time[index] = get_time();
            memset(buf, 0, sizeof(buf));
            index++;
        }
        // double total_end_time = get_time();

        // close all file
        for (index = 0; index < file_count; index++) {
            close(fd[index]);
        }

        printf("loop %d) total open time: %lf\ttotal read time: %lf\n", loop, total_open_time, total_read_time);
    }

    return 0;
}
