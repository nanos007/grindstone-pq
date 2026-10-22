// Time-sliced, resumable grinding driver shared by all grind kernels.
//
// Each instance has a result slot (PENDING until solved) and a next_base counter. A launch
// visits every instance once (via a global queue) and runs at most `budget` rounds on it,
// so a launch stays well under the Windows WDDM watchdog (~2 s) and the host can harvest
// finished slots and refill them between launches.
//
// GROUP = 32: one warp per instance, lowest successful lane via __ballot_sync.
// GROUP = blockDim.x (256): one block per instance, lowest successful thread via shared atomicMin.
// Either way the round covers counters [base, base + GROUP) and the smallest accepted counter in
// the first successful round is reported, which equals the sequential reference's answer.
#pragma once
#include "sha256.cuh"

#define PENDING 0xfffffffeu
#define FAILED  0xffffffffu

struct Slice {
    u32 n_inst;
    u32 budget;     // rounds per instance per launch
    u32 max_tries;  // counters >= max_tries are never accepted; reaching it gives FAILED
};

template <class Attempt>
__device__ void drive_warp(const Slice &s, u32 *queue, u32 *next_base, u32 *result, Attempt attempt) {
    const u32 lane = threadIdx.x & 31;
    for (;;) {
        u32 inst;
        if (lane == 0) inst = atomicAdd(queue, 1);
        inst = __shfl_sync(0xffffffffu, inst, 0);
        if (inst >= s.n_inst) return;
        if (result[inst] != PENDING) continue;
        u32 base = next_base[inst];
        u32 found = PENDING;
        for (u32 r = 0; r < s.budget; r++, base += 32) {
            if (base >= s.max_tries) { found = FAILED; break; }
            u32 ctr = base + lane;
            bool ok = ctr < s.max_tries && attempt(inst, ctr);
            u32 ballot = __ballot_sync(0xffffffffu, ok);
            if (ballot) { found = base + __ffs(ballot) - 1; break; }
        }
        if (lane == 0) {
            next_base[inst] = base;
            result[inst] = found;
        }
    }
}

template <class Attempt>
__device__ void drive_block(const Slice &s, u32 *queue, u32 *next_base, u32 *result, Attempt attempt) {
    __shared__ u32 sh_inst, sh_min;
    const u32 tid = threadIdx.x, G = blockDim.x;
    for (;;) {
        if (tid == 0) sh_inst = atomicAdd(queue, 1);
        __syncthreads();
        u32 inst = sh_inst;
        if (inst >= s.n_inst) return;
        if (result[inst] != PENDING) { __syncthreads(); continue; }
        u32 base = next_base[inst];
        u32 found = PENDING;
        for (u32 r = 0; r < s.budget; r++, base += G) {
            if (base >= s.max_tries) { found = FAILED; break; }
            if (tid == 0) sh_min = 0xffffffffu;
            __syncthreads();
            u32 ctr = base + tid;
            bool ok = ctr < s.max_tries && attempt(inst, ctr);
            if (ok) atomicMin(&sh_min, ctr);
            if (__syncthreads_or(ok)) { found = sh_min; break; }
        }
        if (tid == 0) {
            next_base[inst] = base;
            result[inst] = found;
        }
        __syncthreads();
    }
}

// Expands to the two extern "C" entry points (_w32 and _blk) for one attempt functor type.
#define GRIND_ENTRY(NAME, FUNCTOR, PARAMS)                                                        \
    extern "C" __global__ void NAME##_w32(const u32 *recs, const PARAMS *pp, u32 n_inst,         \
                                          u32 budget, u32 max_tries, u32 *queue,                 \
                                          u32 *next_base, u32 *result) {                         \
        FUNCTOR f{recs, *pp};                                                                     \
        drive_warp(Slice{n_inst, budget, max_tries}, queue, next_base, result, f);                \
    }                                                                                             \
    extern "C" __global__ void NAME##_blk(const u32 *recs, const PARAMS *pp, u32 n_inst,         \
                                          u32 budget, u32 max_tries, u32 *queue,                 \
                                          u32 *next_base, u32 *result) {                         \
        FUNCTOR f{recs, *pp};                                                                     \
        drive_block(Slice{n_inst, budget, max_tries}, queue, next_base, result, f);               \
    }
