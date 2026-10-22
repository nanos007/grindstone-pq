// FORS+C / PORS+FP grinding (kb/raw/A/pseudocode.md §2–§4). M is a 32-byte sighash.
//
// Instance record, 32 u32 (big-endian word values):
//   R / PORS layouts: [0:8] HMAC ipad midstate, [8:16] opad midstate, [16:20] PK.seed,
//                     [20:24] PK.root, [24:32] M
//   ctr layout:       [0:8] midstate of R‖PK.seed‖PK.root‖M[:16], [8:12] R, [12:16] unused,
//                     [16:20] PK.seed, [20:24] PK.root, [24:32] M
//
// Per-attempt compressions: R = 6, ctr = 3, PORS = 7 (+ subset/Octopus integer work).
// Driven by grind_common.cuh (time-sliced, warp- or block-per-instance, lowest counter wins).
#include "grind_common.cuh"

#define REC 32

struct ForsParams {
    u32 zmask[8];   // digest bits that must be zero (FORS+C)
    u32 k, t, b, h, m_max;  // PORS+FP
};

// HMAC(SK.prf, PK.seed ‖ M ‖ ctr)[:16] -> R[4]. 2 compressions.
__device__ __forceinline__ void prf_r(const u32 *rec, u32 ctr, u32 R[4]) {
    u32 st[8], w[16];
#pragma unroll
    for (int i = 0; i < 8; i++) st[i] = rec[i];
#pragma unroll
    for (int i = 0; i < 4; i++) w[i] = rec[16 + i];
#pragma unroll
    for (int i = 0; i < 8; i++) w[4 + i] = rec[24 + i];
    w[12] = ctr; w[13] = 0x80000000u; w[14] = 0; w[15] = (64 + 52) * 8;
    sha256_compress(st, w);
#pragma unroll
    for (int i = 0; i < 8; i++) w[i] = st[i];
    w[8] = 0x80000000u;
#pragma unroll
    for (int i = 9; i < 15; i++) w[i] = 0;
    w[15] = (64 + 32) * 8;
#pragma unroll
    for (int i = 0; i < 8; i++) st[i] = rec[8 + i];
    sha256_compress(st, w);
#pragma unroll
    for (int i = 0; i < 4; i++) R[i] = st[i];
}

// inner = SHA-256(R ‖ PK.seed ‖ PK.root ‖ M). 2 compressions.
__device__ __forceinline__ void hmsg_inner(const u32 *rec, const u32 R[4], u32 inner[8]) {
    u32 w[16];
    sha256_init(inner);
#pragma unroll
    for (int i = 0; i < 4; i++) { w[i] = R[i]; w[4 + i] = rec[16 + i]; w[8 + i] = rec[20 + i]; w[12 + i] = rec[24 + i]; }
    sha256_compress(inner, w);
#pragma unroll
    for (int i = 0; i < 4; i++) w[i] = rec[28 + i];
    w[4] = 0x80000000u;
#pragma unroll
    for (int i = 5; i < 15; i++) w[i] = 0;
    w[15] = 80 * 8;
    sha256_compress(inner, w);
}

// First MGF1 block (R ‖ PK.seed ‖ inner) -> st. 1 compression.
__device__ __forceinline__ void mgf1_first(const u32 *rec, const u32 R[4], const u32 inner[8], u32 st[8]) {
    u32 w[16];
    sha256_init(st);
#pragma unroll
    for (int i = 0; i < 4; i++) { w[i] = R[i]; w[4 + i] = rec[16 + i]; }
#pragma unroll
    for (int i = 0; i < 8; i++) w[8 + i] = inner[i];
    sha256_compress(st, w);
}

// MGF1 output block j from the shared first-block state. 1 compression.
__device__ __forceinline__ void mgf1_block(const u32 first[8], u32 j, u32 out[8]) {
    u32 w[16];
#pragma unroll
    for (int i = 0; i < 8; i++) out[i] = first[i];
    w[0] = j; w[1] = 0x80000000u;
#pragma unroll
    for (int i = 2; i < 15; i++) w[i] = 0;
    w[15] = 68 * 8;
    sha256_compress(out, w);
}

__device__ __forceinline__ bool zero_ok(const u32 dg[8], const ForsParams &p) {
    u32 acc = 0;
#pragma unroll
    for (int i = 0; i < 8; i++) acc |= dg[i] & p.zmask[i];
    return acc == 0;
}

// ---------------------------------------------------------------- PORS+FP acceptance

__device__ __forceinline__ u32 bits_at(const u32 y[16], u32 pos, u32 b) {
    u32 wi = pos >> 5, off = pos & 31;
    unsigned long long hi = ((unsigned long long)y[wi] << 32) | (wi + 1 < 16 ? y[wi + 1] : 0u);
    return (u32)(hi >> (64 - off - b)) & ((1u << b) - 1);
}

__device__ bool pors_accept(const u32 y[16], const ForsParams &p) {
    u32 X[16];
    u32 n = 0;
    u32 nu = (512 - p.h) / p.b;
    for (u32 i = 0; i < nu && n < p.k; i++) {
        u32 v = bits_at(y, p.h + i * p.b, p.b);
        if (v >= p.t) continue;
        bool dup = false;
        for (u32 j = 0; j < n; j++) dup |= X[j] == v;
        if (!dup) X[n++] = v;
    }
    if (n < p.k) return false;
    // insertion sort
    for (u32 i = 1; i < n; i++) {
        u32 v = X[i], j = i;
        while (j > 0 && X[j - 1] > v) { X[j] = X[j - 1]; j--; }
        X[j] = v;
    }
    u32 hgt = 32 - __clz(p.t - 1);
    u32 s = p.t - (1u << (hgt - 1));
    u32 I[16], P[16], nI = 0, nP = 0;
    for (u32 i = 0; i < n; i++) {
        if (X[i] < 2 * s) I[nI++] = X[i];
        else P[nP++] = X[i] - s;
    }
    u32 auth = 0;
    for (u32 lvl = 0; lvl < hgt; lvl++) {
        u32 nxt[16], nn = 0, j = 0;
        while (j < nI) {
            u32 x = I[j];
            if (j + 1 < nI && I[j + 1] == (x ^ 1)) j += 2;
            else { auth++; j++; }
            if (nn == 0 || nxt[nn - 1] != (x >> 1)) nxt[nn++] = x >> 1;
        }
        if (auth > p.m_max) return false;
        if (lvl == 0 && nP) {  // merge sorted nxt and P
            u32 a = 0, c = 0, o = 0;
            while (a < nn || c < nP) {
                if (c >= nP || (a < nn && nxt[a] <= P[c])) I[o++] = nxt[a++];
                else I[o++] = P[c++];
            }
            nI = o;
        } else {
            for (u32 q = 0; q < nn; q++) I[q] = nxt[q];
            nI = nn;
        }
    }
    return auth <= p.m_max;
}

// ---------------------------------------------------------------- attempts

__device__ __forceinline__ bool attempt_R(const u32 *rec, u32 ctr, const ForsParams &p) {
    u32 R[4], inner[8], first[8], dg[8];
    prf_r(rec, ctr, R);
    hmsg_inner(rec, R, inner);
    mgf1_first(rec, R, inner, first);
    mgf1_block(first, 0, dg);
    return zero_ok(dg, p);
}

__device__ __forceinline__ bool attempt_ctr(const u32 *rec, u32 ctr, const ForsParams &p) {
    u32 inner[8], w[16], first[8], dg[8];
#pragma unroll
    for (int i = 0; i < 8; i++) inner[i] = rec[i];
#pragma unroll
    for (int i = 0; i < 4; i++) w[i] = rec[28 + i];
    w[4] = ctr; w[5] = 0x80000000u;
#pragma unroll
    for (int i = 6; i < 15; i++) w[i] = 0;
    w[15] = 84 * 8;
    sha256_compress(inner, w);
    mgf1_first(rec, rec + 8, inner, first);
    mgf1_block(first, 0, dg);
    return zero_ok(dg, p);
}

__device__ __forceinline__ bool attempt_pors(const u32 *rec, u32 ctr, const ForsParams &p) {
    u32 R[4], inner[8], first[8], y[16];
    prf_r(rec, ctr, R);
    hmsg_inner(rec, R, inner);
    mgf1_first(rec, R, inner, first);
    mgf1_block(first, 0, y);
    mgf1_block(first, 1, y + 8);
    return pors_accept(y, p);
}

template <int MODE>
struct ForsAttempt {
    const u32 *recs;
    ForsParams p;

    __device__ bool operator()(u32 inst, u32 ctr) const {
        const u32 *rec = recs + inst * REC;
        if (MODE == 0) return attempt_R(rec, ctr, p);
        if (MODE == 1) return attempt_ctr(rec, ctr, p);
        return attempt_pors(rec, ctr, p);
    }
};

typedef ForsAttempt<0> AttemptR;
typedef ForsAttempt<1> AttemptCtr;
typedef ForsAttempt<2> AttemptPors;

GRIND_ENTRY(grind_fors_c_R, AttemptR, ForsParams)
GRIND_ENTRY(grind_fors_c_ctr, AttemptCtr, ForsParams)
GRIND_ENTRY(grind_pors_fp, AttemptPors, ForsParams)
