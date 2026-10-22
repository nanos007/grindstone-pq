/* E5 calibration: SHA-NI self-test and single-block compressions/s across threads.
 * Usage: bench_cpu <threads> <seconds> */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "sha256_ni.h"
#include "threads.h"

static const uint32_t IV[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                               0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};

static double now(void) {
    struct timespec ts;
    timespec_get(&ts, TIME_UTC);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

typedef struct {
    double seconds;
    unsigned long long count;
    uint32_t sink;
} job_t;

static THREAD_RET worker(void *p) {
    job_t *j = (job_t *)p;
    uint8_t blk[64] = {0};
    blk[42] = 0x80;
    blk[62] = 0x03; blk[63] = 0x50;  /* (64 + 42) * 8 bits */
    uint32_t acc = 0;
    unsigned long long n = 0;
    double t0 = now();
    while (now() - t0 < j->seconds) {
        for (int i = 0; i < 65536; i++) {
            uint32_t st[8];
            memcpy(st, IV, sizeof st);
            memcpy(blk, &n, 8);
            memcpy(blk + 8, &acc, 4);
            sha256_compress_ni(st, blk);
            acc ^= st[0];
            n++;
        }
    }
    j->count = n;
    j->sink = acc;
    return 0;
}

static int selftest(void) {
    /* SHA-256("abc") */
    uint8_t blk[64] = {'a', 'b', 'c', 0x80};
    blk[63] = 24;
    uint32_t st[8];
    memcpy(st, IV, sizeof st);
    sha256_compress_ni(st, blk);
    return st[0] == 0xba7816bf && st[7] == 0xf20015ad;
}

int main(int argc, char **argv) {
    int nt = argc > 1 ? atoi(argv[1]) : 1;
    double secs = argc > 2 ? atof(argv[2]) : 5.0;
    if (!selftest()) { fprintf(stderr, "SHA-NI selftest FAILED\n"); return 1; }
    job_t jobs[256];
    for (int i = 0; i < nt; i++) jobs[i].seconds = secs;
    double t0 = now();
    run_threads(nt, worker, jobs, sizeof(job_t));
    double dt = now() - t0;
    unsigned long long total = 0;
    for (int i = 0; i < nt; i++) total += jobs[i].count;
    printf("{\"threads\": %d, \"seconds\": %.3f, \"compressions\": %llu, \"rate\": %.0f}\n",
           nt, dt, total, total / dt);
    return 0;
}
