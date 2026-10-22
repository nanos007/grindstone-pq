// WOTS+C grinding: d = Trunc_16(SHA-256(PK.seed-midstate ‖ tail(count))), accept iff the
// first len1 base-w digits of d sum to S and the zero-bit mask holds (z zero chains at the end
// of d are a zero mask over their bits). One compression per attempt.
//
// The tail block layout (ADRS_c ‖ m ‖ count ‖ padding, SHRINCS, or any other) is built on the
// host. Record per instance (24 u32): [0:8] seed midstate, [8:24] the 16 big-endian words of the
// final block with the counter bytes zeroed; the counter's ctr_bytes go at byte offset ctr_off.
#include "grind_common.cuh"

struct WotsParams {
    u32 len1;       // number of message digits
    u32 logw;       // bits per digit: 1, 2, 4 or 8 (digits never straddle words)
    u32 target;     // required digit sum S
    u32 zmask[4];   // bits of d (words 0..3, big-endian) that must be zero
    u32 ctr_off;    // byte offset of the counter in the final block
    u32 ctr_le;     // 1 = little-endian counter bytes
    u32 ctr_bytes;  // counter width in bytes (4, or 2 for SHRINCS)
};

__device__ __forceinline__ void put_byte(u32 w[16], u32 off, u32 b) {
    w[off >> 2] |= b << ((3 - (off & 3)) * 8);
}

struct WotsAttempt {
    const u32 *recs;
    WotsParams p;

    __device__ bool operator()(u32 inst, u32 ctr) const {
        const u32 *rec = recs + inst * 24;
        u32 w[16], st[8];
#pragma unroll
        for (int i = 0; i < 16; i++) w[i] = rec[8 + i];
        for (u32 b = 0; b < p.ctr_bytes; b++) {
            u32 byte = p.ctr_le ? (ctr >> (8 * b)) : (ctr >> (8 * (p.ctr_bytes - 1 - b)));
            put_byte(w, p.ctr_off + b, byte & 0xff);
        }
#pragma unroll
        for (int i = 0; i < 8; i++) st[i] = rec[i];
        sha256_compress(st, w);
        if ((st[0] & p.zmask[0]) | (st[1] & p.zmask[1]) | (st[2] & p.zmask[2]) | (st[3] & p.zmask[3]))
            return false;
        u32 sum = 0, mask = (1u << p.logw) - 1;
        for (u32 i = 0; i < p.len1; i++) {
            u32 bit = i * p.logw;  // MSB-first bit position in d
            sum += (st[bit >> 5] >> (32 - p.logw - (bit & 31))) & mask;
        }
        return sum == p.target;
    }
};

GRIND_ENTRY(grind_wots_c, WotsAttempt, WotsParams)
