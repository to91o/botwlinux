// Opt-in CPU sampling on Linux: SAVAGEWIND_LINUX_SAMPLE=start_seconds:duration[:interval_us].
// Only the interrupted instruction pointer is captured; the signal handler never allocates, locks or unwinds.
#define _GNU_SOURCE
#if defined(__linux__) && (defined(__x86_64__) || defined(__aarch64__))
#include <errno.h>
#include <link.h>
#include <pthread.h>
#include <signal.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <time.h>
#include <ucontext.h>
#include <unistd.h>

_Static_assert(ATOMIC_LLONG_LOCK_FREE == 2 && ATOMIC_INT_LOCK_FREE == 2, "signal-safe sample counters");
typedef struct { uint64_t pc, ns; unsigned tid; } LinuxSample;
static LinuxSample *samples;
static unsigned capacity;
static atomic_uint used, handlers;
static atomic_bool enabled;

static uint64_t sample_now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000000000ull + t.tv_nsec;
}

static void sample_signal(int sig, siginfo_t *info, void *opaque) {
    (void)sig; (void)info;
    int saved_errno = errno;
    atomic_fetch_add(&handlers, 1);
    if (atomic_load(&enabled)) {
        unsigned i = atomic_fetch_add(&used, 1);
        if (i < capacity) {
            ucontext_t *ctx = opaque;
#ifdef __x86_64__
            samples[i].pc = ctx->uc_mcontext.gregs[REG_RIP];
#else
            samples[i].pc = ctx->uc_mcontext.pc;
#endif
            samples[i].ns = sample_now();
            samples[i].tid = (unsigned)syscall(SYS_gettid);
        }
    }
    atomic_fetch_sub(&handlers, 1);
    errno = saved_errno;
}

static int sample_module(struct dl_phdr_info *info, size_t size, void *arg) {
    (void)size;
    FILE *f = arg;
    uint64_t end = 0;
    for (int i = 0; i < info->dlpi_phnum; i++) {
        const ElfW(Phdr) *p = &info->dlpi_phdr[i];
        if (p->p_type == PT_LOAD && p->p_vaddr + p->p_memsz > end) end = p->p_vaddr + p->p_memsz;
    }
    if (end) fprintf(f, "M %llx %llx %s\n", (unsigned long long)info->dlpi_addr,
                     (unsigned long long)end, *info->dlpi_name ? info->dlpi_name : "/proc/self/exe");
    return 0;
}

static void sample_sleep(double seconds) {
    struct timespec t = {(time_t)seconds, (long)((seconds - (time_t)seconds) * 1e9)};
    while (nanosleep(&t, &t) && errno == EINTR) {}
}

static void *linux_sample_main(void *arg) {
    double start = 0, seconds = 0, interval = 1000;
    if (sscanf(arg, "%lf:%lf:%lf", &start, &seconds, &interval) < 2 ||
        !(start >= 0 && start <= 86400 && seconds > 0 && seconds <= 600 && interval >= 100 && interval <= 1000000))
        return NULL;
    sample_sleep(start);
    struct itimerval previous;
    if (getitimer(ITIMER_PROF, &previous) || previous.it_value.tv_sec || previous.it_value.tv_usec) {
        fprintf(stderr, "[linux-sample] profiling timer already in use\n");
        return NULL;
    }
    capacity = 1u << 20;  // bounded memory use, including with many busy threads
    samples = calloc(capacity, sizeof *samples);
    if (!samples) return NULL;
    struct sigaction sa = {.sa_sigaction = sample_signal, .sa_flags = SA_SIGINFO | SA_RESTART};
    sigemptyset(&sa.sa_mask);
    if (sigaction(SIGPROF, &sa, NULL)) { free(samples); return NULL; }
    struct itimerval timer = {0};
    timer.it_interval.tv_sec = (time_t)(interval / 1e6);
    timer.it_interval.tv_usec = (suseconds_t)interval % 1000000;
    timer.it_value = timer.it_interval;
    atomic_store(&enabled, true);
    if (setitimer(ITIMER_PROF, &timer, NULL)) {
        atomic_store(&enabled, false); free(samples); return NULL;
    }
    fprintf(stderr, "[linux-sample] collecting CPU instruction pointers for %.1f seconds\n", seconds);
    sample_sleep(seconds);
    atomic_store(&enabled, false);
    timer = (struct itimerval){0};
    setitimer(ITIMER_PROF, &timer, NULL);
    while (atomic_load(&handlers)) sample_sleep(0.001);
    // Keep the now-inactive handler installed: a queued SIGPROF must not take its default terminate action.
    const char *out = getenv("SAVAGEWIND_LINUX_SAMPLE_OUT");
    FILE *f = fopen(out && *out ? out : "build/linux-samples.txt", "w");
    unsigned n = atomic_load(&used), count = n < capacity ? n : capacity;
    if (f) {
        char exe[4096];
        ssize_t len = readlink("/proc/self/exe", exe, sizeof exe - 1);
        if (len > 0) { exe[len] = 0; fprintf(f, "E %s\n", exe); }
        dl_iterate_phdr(sample_module, f);
        for (unsigned i = 0; i < count; i++)
            fprintf(f, "S %u %llx %llu\n", samples[i].tid, (unsigned long long)samples[i].pc,
                    (unsigned long long)samples[i].ns);
        fclose(f);
    }
    fprintf(stderr, "[linux-sample] %u samples, %u dropped%s\n", count, n - count, f ? "" : " (output unavailable)");
    free(samples);
    return NULL;
}

__attribute__((constructor)) static void linux_sample_start(void) {
    const char *e = getenv("SAVAGEWIND_LINUX_SAMPLE");
    if (!e || !*e) return;
    pthread_t th;
    if (!pthread_create(&th, NULL, linux_sample_main, (void *)e)) pthread_detach(th);
}
#endif
