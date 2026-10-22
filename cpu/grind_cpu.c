/* E5 CPU baseline (SHA-NI): same instance format and acceptance rules as the GPU kernels.
 *
 * Usage: grind_cpu wots <threads> <params.bin> <inst.bin> <out.bin>
 *   params.bin: 11 u32 (len1, logw, S, zmask[4], ctr_off, ctr_le, max_tries, ctr_bytes)
 *   inst.bin:   N × (8 u32 midstate + 16 u32 final-block words), little-endian u32
 *   out.bin:    N × (u32 counter, u32 pad, f64 seconds)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "sha256_ni.h"
#include "threads.h"

typedef struct {
    uint32_t len1, logw, target, zmask[4], ctr_off, ctr_le, max_tries, ctr_bytes;
} wots_params;

typedef struct {
    uint32_t counter, pad;
    double seconds;
} result_t;

typedef struct {
    const wots_params *p;
    const uint32_t *inst;
    result_t *out;
    size_t n;
    volatile long *next;
} job_t;

static double now(void) {
    struct timespec ts;
    timespec_get(&ts, TIME_UTC);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static int wots_accept(const uint32_t st[8], const wots_params *p) {
    if ((st[0] & p->zmask[0]) | (st[1] & p->zmask[1]) | (st[2] & p->zmask[2]) | (st[3] & p->zmask[3]))
        return 0;
    uint32_t sum = 0, mask = (1u << p->logw) - 1;
    for (uint32_t i = 0; i < p->len1; i++) {
        uint32_t bit = i * p->logw;
        sum += (st[bit >> 5] >> (32 - p->logw - (bit & 31))) & mask;
    }
    return sum == p->target;
}

static uint32_t grind_one(const wots_params *p, const uint32_t *rec) {
    uint8_t blk[64];
    for (int i = 0; i < 16; i++) {
        uint32_t w = rec[8 + i];
        blk[4 * i] = w >> 24; blk[4 * i + 1] = w >> 16; blk[4 * i + 2] = w >> 8; blk[4 * i + 3] = w;
    }
    for (uint32_t ctr = 0; ctr < p->max_tries; ctr++) {
        for (uint32_t b = 0; b < p->ctr_bytes; b++)
            blk[p->ctr_off + b] = p->ctr_le ? (uint8_t)(ctr >> (8 * b))
                                            : (uint8_t)(ctr >> (8 * (p->ctr_bytes - 1 - b)));
        uint32_t st[8];
        memcpy(st, rec, 32);
        sha256_compress_ni(st, blk);
        if (wots_accept(st, p)) return ctr;
    }
    return 0xffffffffu;
}

static THREAD_RET worker(void *arg) {
    job_t *j = (job_t *)arg;
    for (;;) {
        long i = __atomic_fetch_add(j->next, 1, __ATOMIC_RELAXED);
        if ((size_t)i >= j->n) break;
        double t0 = now();
        j->out[i].counter = grind_one(j->p, j->inst + (size_t)i * 24);
        j->out[i].pad = 0;
        j->out[i].seconds = now() - t0;
    }
    return 0;
}

static void *slurp(const char *path, size_t *len) {
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(1); }
    fseek(f, 0, SEEK_END);
    *len = ftell(f);
    fseek(f, 0, SEEK_SET);
    void *buf = malloc(*len);
    if (fread(buf, 1, *len, f) != *len) { perror(path); exit(1); }
    fclose(f);
    return buf;
}

int main(int argc, char **argv) {
    if (argc != 6 || strcmp(argv[1], "wots")) {
        fprintf(stderr, "usage: grind_cpu wots <threads> <params.bin> <inst.bin> <out.bin>\n");
        return 2;
    }
    int nt = atoi(argv[2]);
    size_t plen, ilen;
    wots_params *p = slurp(argv[3], &plen);
    uint32_t *inst = slurp(argv[4], &ilen);
    size_t n = ilen / (24 * 4);
    result_t *out = calloc(n, sizeof *out);
    volatile long next = 0;
    job_t jobs[256];
    for (int i = 0; i < nt; i++) jobs[i] = (job_t){p, inst, out, n, &next};
    double t0 = now();
    run_threads(nt, worker, jobs, sizeof(job_t));
    double dt = now() - t0;
    FILE *f = fopen(argv[5], "wb");
    fwrite(out, sizeof *out, n, f);
    fclose(f);
    printf("{\"instances\": %zu, \"threads\": %d, \"wall_s\": %.4f}\n", n, nt, dt);
    return 0;
}
