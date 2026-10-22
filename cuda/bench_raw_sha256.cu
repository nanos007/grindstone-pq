// E0: raw SHA-256 compressions/sec from a cached midstate (one block per iteration).
#include "sha256.cuh"

extern "C" __global__ void bench_raw(const u32 *mid, u32 iters, u32 *sink) {
    u32 tid = blockIdx.x * blockDim.x + threadIdx.x;
    u32 acc = 0;
    for (u32 it = 0; it < iters; it++) {
        u32 st[8], w[16];
#pragma unroll
        for (int i = 0; i < 8; i++) st[i] = mid[i];
        // Last block of a 42-byte WOTS+C-like tail: data words vary with (tid, it).
#pragma unroll
        for (int i = 0; i < 16; i++) w[i] = 0;
        w[0] = tid; w[1] = it; w[2] = acc;
        w[10] = 0x00008000u;  // 0x80 padding byte at offset 42
        w[15] = (64 + 42) * 8;
        sha256_compress(st, w);
        acc ^= st[0];
    }
    sink[tid] = acc;
}
