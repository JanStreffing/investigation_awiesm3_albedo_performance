/* Minimal SIGPROF program-counter sampler, LD_PRELOAD-able, no ptrace or perf needed.
 * Active only if PCS_ENABLE=1. PCS_DELAY=<s> starts the timer only after that many seconds, so that
 * the signals miss the start-up (on levante's Lustre they broke XIOS's collective nc_create_par). Samples the interrupted instruction pointer every
 * PCS_USEC microseconds of CPU time (default 1000) into an open-addressing hash table.
 * At exit writes <PCS_OUT>.samples ("hexaddr count") and <PCS_OUT>.maps (/proc/self/maps).
 * Build: gcc -O2 -fPIC -shared -o libpcsampler.so pcsampler.c
 */
#define _GNU_SOURCE
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <ucontext.h>
#include <unistd.h>
#include <time.h>
#include <pthread.h>

#define NBUCKET (1u << 20)
static unsigned long keys[NBUCKET];
static unsigned int counts[NBUCKET];
static volatile unsigned long total, dropped;
static char outbase[512];
static unsigned int binsec = 10;           /* time-bin width, PCS_BIN seconds */
static unsigned int bins[NBUCKET];         /* time bin of each key */
static double t0;

static void handler(int sig, siginfo_t *si, void *uc_) {
    (void)sig; (void)si;
    ucontext_t *uc = (ucontext_t *)uc_;
    unsigned long pc = (unsigned long)uc->uc_mcontext.gregs[REG_RIP];
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    unsigned int bin = (unsigned int)((ts.tv_sec + ts.tv_nsec * 1e-9 - t0) / binsec);
    unsigned int h = (unsigned int)(((pc >> 2) ^ ((unsigned long)bin << 40)) * 2654435761u) & (NBUCKET - 1);
    for (unsigned int i = 0; i < 64; i++) {
        unsigned int b = (h + i) & (NBUCKET - 1);
        if (keys[b] == pc && bins[b] == bin) { counts[b]++; total++; return; }
        if (keys[b] == 0) { keys[b] = pc; bins[b] = bin; counts[b] = 1; total++; return; }
    }
    dropped++;
}

static void dump(void) {
    struct itimerval off = {{0, 0}, {0, 0}};
    setitimer(ITIMER_PROF, &off, NULL);
    char fn[600];
    snprintf(fn, sizeof fn, "%s.samples", outbase);
    FILE *f = fopen(fn, "w");
    if (f) {
        fprintf(f, "# total %lu dropped %lu t0 %.3f binsec %u\n", total, dropped, t0, binsec);
        for (unsigned int b = 0; b < NBUCKET; b++)
            if (keys[b]) fprintf(f, "%lx %u %u\n", keys[b], counts[b], bins[b]);
        fclose(f);
    }
    snprintf(fn, sizeof fn, "%s.maps", outbase);
    FILE *in = fopen("/proc/self/maps", "r"), *out = fopen(fn, "w");
    if (in && out) { char line[4096]; while (fgets(line, sizeof line, in)) fputs(line, out); }
    if (in) fclose(in);
    if (out) fclose(out);
}

static struct itimerval it_on;
static int delay_sec;

static void *delayed_start(void *arg) {
    (void)arg;
    sleep(delay_sec);
    setitimer(ITIMER_PROF, &it_on, NULL);
    return NULL;
}

__attribute__((constructor)) static void start(void) {
    const char *en = getenv("PCS_ENABLE");
    if (!en || strcmp(en, "1") != 0) return;
    const char *o = getenv("PCS_OUT");
    snprintf(outbase, sizeof outbase, "%s", o ? o : "pcs");
    int usec = getenv("PCS_USEC") ? atoi(getenv("PCS_USEC")) : 1000;
    if (getenv("PCS_BIN")) binsec = (unsigned int)atoi(getenv("PCS_BIN"));
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    t0 = ts.tv_sec + ts.tv_nsec * 1e-9;
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = handler;
    sa.sa_flags = SA_SIGINFO | SA_RESTART;
    sigaction(SIGPROF, &sa, NULL);
    it_on.it_interval.tv_usec = usec;
    it_on.it_value.tv_usec = usec;
    delay_sec = getenv("PCS_DELAY") ? atoi(getenv("PCS_DELAY")) : 0;
    if (delay_sec > 0) {
        pthread_t th;
        pthread_attr_t at;
        pthread_attr_init(&at);
        pthread_attr_setdetachstate(&at, PTHREAD_CREATE_DETACHED);
        if (pthread_create(&th, &at, delayed_start, NULL) != 0) setitimer(ITIMER_PROF, &it_on, NULL);
    } else {
        setitimer(ITIMER_PROF, &it_on, NULL);
    }
    atexit(dump);
}
