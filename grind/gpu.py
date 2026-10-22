"""NVRTC kernels: E0 calibration and the streaming, time-sliced grinders.

All grind kernels share cuda/grind_common.cuh: a launch visits each live slot once and runs at
most `budget` rounds on it, so every launch stays far below the Windows WDDM watchdog (~2 s).
`Grinder` keeps a fixed pool of slots on the device, harvests solved slots after each launch and
refills them from an instance source, so the GPU stays full until a job's last instances.
"""
import time
from functools import lru_cache
from pathlib import Path

import cupy as cp
import numpy as np

CUDA_DIR = Path(__file__).resolve().parents[1] / "cuda"
NVRTC_OPTS = ("--gpu-architecture=sm_89", "-std=c++17", f"-I{CUDA_DIR.as_posix()}")

PENDING = 0xFFFFFFFE
FAILED = 0xFFFFFFFF
EMPTY = 0xFFFFFFFD  # slot without an instance; kernels skip anything != PENDING

FORS_KERNELS = {"R": "grind_fors_c_R", "ctr": "grind_fors_c_ctr", "pors": "grind_pors_fp"}
COMPRESSIONS = {"wots": 1, "R": 6, "ctr": 3, "pors": 7}


@lru_cache(maxsize=None)
def module(name):
    # CuPy writes the source with the locale codec (cp1252 on Windows): keep it ASCII.
    # Non-ASCII only appears in comments, and #included headers are read by NVRTC directly.
    src = (CUDA_DIR / name).read_text(encoding="utf-8").encode("ascii", "replace").decode()
    return cp.RawModule(code=src, options=NVRTC_OPTS)


@lru_cache(maxsize=None)
def sm_count():
    return cp.cuda.runtime.getDeviceProperties(0)["multiProcessorCount"]


def bench_raw(seconds=10.0, threads=256, blocks_per_sm=32, iters=4096):
    """Sustained single-block compressions/s. Returns list of (t_end, rate) per launch."""
    k = module("bench_raw_sha256.cu").get_function("bench_raw")
    blocks = sm_count() * blocks_per_sm
    mid = cp.asarray(np.arange(8, dtype=np.uint32) * 0x9E3779B9)
    sink = cp.zeros(blocks * threads, dtype=cp.uint32)
    start, stop = cp.cuda.Event(), cp.cuda.Event()
    per_launch = blocks * threads * iters
    out = []
    t0 = time.time()
    while time.time() - t0 < seconds:
        start.record()
        k((blocks,), (threads,), (mid, np.uint32(iters), sink))
        stop.record()
        stop.synchronize()
        ms = cp.cuda.get_elapsed_time(start, stop)
        out.append((time.time() - t0, per_launch / (ms / 1e3)))
    return out


class Grinder:
    """Streams instances through a fixed device slot pool.

    kernel: (module file, entry base name); group: "w32" (warp per instance) or "blk" (256-thread
    block per instance, for heavy grinds); params: uint32 array matching the kernel's params struct.
    """

    THREADS = 256

    def __init__(self, kernel, rec_words, params, max_tries, group="w32", capacity=None,
                 target_launch_s=0.25):
        file, name = kernel
        self.fn = module(file).get_function(f"{name}_{group}")
        self.group = group
        self.lanes = 32 if group == "w32" else self.THREADS
        resident = sm_count() * (1536 // self.THREADS)  # sm_89: 1536 threads / SM
        self.grid = resident * (4 if group == "w32" else 1)
        conc = resident * (self.THREADS // 32) if group == "w32" else resident
        self.capacity = capacity or conc * 8
        self.rec_words = rec_words
        self.params = cp.asarray(np.asarray(params, dtype=np.uint32))
        self.max_tries = int(max_tries)
        self.target = target_launch_s
        self.budget = 1
        self.kernel_ms = 0.0
        self.launches = 0

    def _launch(self, recs, next_base, result, queue):
        queue.fill(0)
        start, stop = cp.cuda.Event(), cp.cuda.Event()
        start.record()
        self.fn((self.grid,), (self.THREADS,),
                (recs, self.params, np.uint32(self.capacity), np.uint32(self.budget),
                 np.uint32(self.max_tries), queue, next_base, result))
        stop.record()
        stop.synchronize()
        ms = cp.cuda.get_elapsed_time(start, stop)
        self.kernel_ms += ms
        self.launches += 1
        # adapt rounds-per-launch towards the target launch time
        scale = (self.target * 1e3) / max(ms, 1e-3)
        self.budget = int(min(max(self.budget * min(max(scale, 0.25), 4.0), 1), 1 << 20))
        return ms

    def run(self, source, n_total, on_progress=None):
        """source(i0, n) -> (n, rec_words) uint32 records for global instances i0..i0+n.

        Returns uint32 counters for all n_total instances (FAILED if max_tries exhausted)."""
        cap = self.capacity
        recs = cp.zeros((cap, self.rec_words), dtype=cp.uint32)
        next_base = cp.zeros(cap, dtype=cp.uint32)
        result = cp.full(cap, EMPTY, dtype=cp.uint32)
        queue = cp.zeros(1, dtype=cp.uint32)
        slot_inst = np.full(cap, -1, dtype=np.int64)
        out = np.full(n_total, PENDING, dtype=np.uint32)
        issued = done = 0

        def fill(slots):
            nonlocal issued
            k = min(len(slots), n_total - issued)
            if k <= 0:
                return
            sl = cp.asarray(slots[:k])
            recs[sl] = cp.asarray(np.asarray(source(issued, k), dtype=np.uint32))
            next_base[sl] = 0
            result[sl] = PENDING
            slot_inst[slots[:k]] = np.arange(issued, issued + k)
            issued += k

        fill(np.arange(cap))
        while done < n_total:
            self._launch(recs, next_base, result, queue)
            res = result.get()
            fin = np.nonzero((res != PENDING) & (res != EMPTY))[0]
            if len(fin):
                out[slot_inst[fin]] = res[fin]
                done += len(fin)
                slot_inst[fin] = -1
                result[cp.asarray(fin)] = EMPTY
                fill(fin)
            if on_progress:
                on_progress(done, n_total)
        return out


# ---------------------------------------------------------------- WOTS+C

def _cap(max_tries, ctr_bytes):
    """A ctr_bytes-wide counter allows at most 2^(8·ctr_bytes) tries."""
    return min(max_tries, 1 << (8 * ctr_bytes)) if ctr_bytes < 4 else max_tries


def wots_params(params, ctr_off, ctr_le=False, ctr_bytes=4):
    from ref.wots_c import zmask_words
    return np.array([params.len1, params.logw, params.S, *zmask_words(params),
                     ctr_off, int(ctr_le), ctr_bytes], dtype=np.uint32)


def wots_grinder(params, ctr_off, ctr_le=False, ctr_bytes=4, max_tries=1 << 30, group="w32", **kw):
    return Grinder(("grind_wots_c.cu", "grind_wots_c"), 24, wots_params(params, ctr_off, ctr_le, ctr_bytes),
                   _cap(max_tries, ctr_bytes), group=group, **kw)


def grind_wots_c(mids, tmpls, ctr_off, params, ctr_le=False, max_tries=1 << 30, ctr_bytes=4, group="w32"):
    """Batch WOTS+C grind. mids: (N,8), tmpls: (N,16) uint32. Returns (counters, None, kernel_ms)."""
    recs = np.concatenate([np.asarray(mids, dtype=np.uint32), np.asarray(tmpls, dtype=np.uint32)], axis=1)
    g = wots_grinder(params, ctr_off, ctr_le, ctr_bytes, max_tries, group)
    c = g.run(lambda i0, n: recs[i0:i0 + n], len(recs))
    return c, None, g.kernel_ms


# ---------------------------------------------------------------- FORS+C / PORS+FP

def _be_words(b):
    return np.frombuffer(b, dtype=">u4").astype(np.uint32)


def fors_records(sk_prf, pk_seed, pk_root, msgs, layout):
    """Instance records (N, 32) for grind_fors_c.cu. msgs: list of 32-byte sighashes."""
    import hashlib
    import hmac
    from grind import sha_np
    from ref import sha2
    n = len(msgs)
    rec = np.zeros((n, 32), dtype=np.uint32)
    rec[:, 16:20] = _be_words(pk_seed)
    rec[:, 20:24] = _be_words(pk_root)
    rec[:, 24:32] = sha_np.be_words(b"".join(msgs), n, 8)
    if layout in ("R", "pors"):
        key = sha2.HmacKey(sk_prf)
        rec[:, 0:8] = key.istate
        rec[:, 8:16] = key.ostate
    elif layout == "ctr":
        rs = b"".join(hmac.new(sk_prf, pk_seed + m, hashlib.sha256).digest()[:16] for m in msgs)
        rec[:, 8:12] = sha_np.be_words(rs, n, 4)
        blk = np.concatenate([rec[:, 8:12], rec[:, 16:20], rec[:, 20:24], rec[:, 24:28]], axis=1)
        rec[:, 0:8] = sha_np.compress(sha_np.iv(n), blk)
    else:
        raise ValueError(layout)
    return rec


def fors_params(layout, k, a, h=0, m_max=0):
    from ref.fors_c import zero_mask_words
    t = k << a
    zm = zero_mask_words(k, a) if layout != "pors" else [0] * 8
    return np.array([*zm, k, t, (t - 1).bit_length(), h, m_max], dtype=np.uint32)


def fors_grinder(layout, k, a, h=0, m_max=0, max_tries=1 << 31, group="w32", **kw):
    return Grinder(("grind_fors_c.cu", FORS_KERNELS[layout]), 32, fors_params(layout, k, a, h, m_max),
                   max_tries, group=group, **kw)


def grind_fors(rec, layout, k, a, h=0, m_max=0, max_tries=1 << 31, group="w32"):
    """Batch FORS+C (layout R / ctr) or PORS+FP (layout pors) grind. Returns (counters, None, ms)."""
    rec = np.asarray(rec, dtype=np.uint32)
    g = fors_grinder(layout, k, a, h, m_max, max_tries, group)
    c = g.run(lambda i0, n: rec[i0:i0 + n], len(rec))
    return c, None, g.kernel_ms


if __name__ == "__main__":
    rates = bench_raw(10.0)
    r = np.array([x[1] for x in rates])
    print(f"launches={len(r)} median={np.median(r)/1e9:.3f} Gcomp/s min={r.min()/1e9:.3f} max={r.max()/1e9:.3f}")
