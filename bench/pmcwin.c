/*
 * pmcwin: count hardware events on running processes for a fixed window.
 *
 *   pmcwin SECONDS PID [PID ...]
 *
 * Attaches to every thread of each PID (user mode only, so it works with
 * perf_event_paranoid=2 on processes of the same user), waits SECONDS and
 * prints one line per PID:
 *
 *   pid comm nthreads task_s cycles instructions dram_fills pf_dram_fills l2pf_miss
 *
 * task_s       CPU time the threads ran in the window (software task-clock)
 * cycles       core cycles in user mode   -> cycles/task_s = clock while running
 * instructions user-mode instructions      -> IPC
 * dram_fills   Zen2 PMC 0x43 umask 0x48: L1D fills served from DRAM (local
 *              0x08 + remote 0x40), 64 B each. Demand fills only: prefetches
 *              and write-backs are not counted, so this is a lower bound on
 *              memory traffic, good for comparing layouts.
 * pf_dram_fills PMC 0x5A umask 0x48: L1D hardware-prefetch fills from DRAM.
 * l2pf_miss    PMC 0x72: L2 prefetches that missed L2 and L3 (go to DRAM).
 *              dram_fills + pf_dram_fills + l2pf_miss ~ lines read from DRAM.
 *
 * Build: gcc -O2 -o pmcwin pmcwin.c
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <linux/perf_event.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <unistd.h>

#define NEV 6
#define MAXT 4096
#define MAXP 1024

static int open_ev(pid_t tid, uint32_t type, uint64_t config)
{
    struct perf_event_attr a;
    memset(&a, 0, sizeof(a));
    a.size = sizeof(a);
    a.type = type;
    a.config = config;
    a.disabled = 1;
    a.exclude_kernel = 1;
    a.exclude_hv = 1;
    a.read_format = PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING;
    return (int)syscall(SYS_perf_event_open, &a, tid, -1, -1, 0);
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: pmcwin SECONDS PID [PID ...]\n");
        return 1;
    }
    int secs = atoi(argv[1]);
    const uint32_t type[NEV] = {PERF_TYPE_SOFTWARE, PERF_TYPE_HARDWARE,
                                PERF_TYPE_HARDWARE, PERF_TYPE_RAW,
                                PERF_TYPE_RAW, PERF_TYPE_RAW};
    const uint64_t conf[NEV] = {PERF_COUNT_SW_TASK_CLOCK, PERF_COUNT_HW_CPU_CYCLES,
                                PERF_COUNT_HW_INSTRUCTIONS, 0x4843, 0x485A, 0xFF72};
    int npid = argc - 2;
    static int fd[MAXT][NEV];
    static int owner[MAXT];
    int nt = 0;

    for (int p = 0; p < npid; p++) {
        char path[64];
        snprintf(path, sizeof(path), "/proc/%s/task", argv[p + 2]);
        DIR *d = opendir(path);
        if (!d)
            continue;
        struct dirent *e;
        while ((e = readdir(d)) && nt < MAXT) {
            if (e->d_name[0] == '.')
                continue;
            pid_t tid = atoi(e->d_name);
            for (int k = 0; k < NEV; k++) {
                fd[nt][k] = open_ev(tid, type[k], conf[k]);
                if (fd[nt][k] < 0)
                    perror("perf_event_open");
            }
            owner[nt++] = p;
        }
        closedir(d);
    }
    for (int t = 0; t < nt; t++)
        for (int k = 0; k < NEV; k++)
            if (fd[t][k] >= 0)
                ioctl(fd[t][k], PERF_EVENT_IOC_ENABLE, 0);
    sleep(secs);

    static double sum[MAXP][NEV];
    static int nthr[MAXP];
    for (int t = 0; t < nt; t++) {
        for (int k = 0; k < NEV; k++) {
            uint64_t v[3] = {0, 0, 0};
            if (fd[t][k] >= 0 && read(fd[t][k], v, sizeof(v)) == sizeof(v)) {
                double scale = (v[2] > 0 && v[2] < v[1]) ? (double)v[1] / v[2] : 1.0;
                if (owner[t] < MAXP)
                    sum[owner[t]][k] += v[0] * scale;
            }
        }
        if (owner[t] < MAXP)
            nthr[owner[t]]++;
    }
    for (int p = 0; p < npid && p < MAXP; p++) {
        char path[64], comm[64] = "?";
        snprintf(path, sizeof(path), "/proc/%s/comm", argv[p + 2]);
        FILE *f = fopen(path, "r");
        if (f) {
            if (fscanf(f, "%63s", comm) != 1)
                strcpy(comm, "?");
            fclose(f);
        }
        printf("%s %s %d %.3f %.0f %.0f %.0f %.0f %.0f\n", argv[p + 2], comm, nthr[p],
               sum[p][0] * 1e-9, sum[p][1], sum[p][2], sum[p][3], sum[p][4], sum[p][5]);
    }
    return 0;
}
