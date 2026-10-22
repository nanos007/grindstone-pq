"""Deterministic grind instances, GPU records, and reference checks for the campaign.

All randomness derives from SHA-256("grindstone" ‖ run_id ‖ config_id ‖ i ‖ j) (doc §4.6), so a
run_id fully reproduces its inputs. WOTS+C instances each get their own PK.seed, ADRS_c and m;
FORS+C / PORS+FP instances share one key per config and differ in the 32-byte sighash M.
"""
import hashlib
import hmac
import struct

import numpy as np

from grind import sha_np
from ref import fors_c, wots_c

LAYOUT = wots_c.WotsLayout()   # campaign layout: ADRS_c(22) ‖ m(16) ‖ ctr(4, BE)
ADRS_LEN, M_LEN = 22, 16
CTR_OFF = ADRS_LEN + M_LEN
TAIL_LEN = CTR_OFF + LAYOUT.ctr_bytes
FAILED = 0xFFFFFFFF  # = grind.gpu.FAILED; not imported so pool workers skip loading CuPy


def _prefix(run_id, config_id):
    return b"grindstone" + run_id.encode() + config_id.encode()


def stream(run_id, config_id, i0, n, nbytes):
    """(n, nbytes) uint8: per-instance pseudo-random bytes for instances i0 .. i0+n."""
    base = hashlib.sha256(_prefix(run_id, config_id))
    blocks = -(-nbytes // 32)
    out = bytearray()
    for i in range(i0, i0 + n):
        ib = struct.pack(">Q", i)
        for j in range(blocks):
            h = base.copy()
            h.update(ib + bytes([j]))
            out += h.digest()[:min(32, nbytes - 32 * j)]
    return np.frombuffer(bytes(out), dtype=np.uint8).reshape(n, nbytes)


# ---------------------------------------------------------------- WOTS+C

def wots_materials(run_id, config_id, i0, n):
    raw = stream(run_id, config_id, i0, n, 16 + ADRS_LEN + M_LEN)
    return {"seed": raw[:, :16], "adrs": raw[:, 16:16 + ADRS_LEN], "m": raw[:, 16 + ADRS_LEN:]}


def wots_records(mat):
    """(n, 24) uint32: PK.seed midstate (8) ‖ final-block template (16), as gpu.grind_wots_c."""
    n = len(mat["seed"])
    seedblk = np.zeros((n, 64), dtype=np.uint8)
    seedblk[:, :16] = mat["seed"]
    mid = sha_np.compress(sha_np.iv(n), seedblk.view(">u4").astype(np.uint32))
    blk = np.zeros((n, 64), dtype=np.uint8)
    blk[:, :ADRS_LEN] = mat["adrs"]
    blk[:, ADRS_LEN:CTR_OFF] = mat["m"]
    blk[:, TAIL_LEN] = 0x80
    blk[:, 56:] = np.frombuffer(struct.pack(">Q", (64 + TAIL_LEN) * 8), dtype=np.uint8)
    return np.concatenate([mid, blk.view(">u4").astype(np.uint32)], axis=1)


def _wots_d(seed_h, adrs, m, count):
    h = seed_h.copy()
    h.update(wots_c.tail(adrs, m, count, LAYOUT))
    return h.digest()[:16]


def wots_check(args):
    """Worker: (rows, params, full) -> list of bad indices.

    rows: [(idx, seed, adrs, m, counter)]. Every counter must be accepted; with full=True the
    whole prefix [0, counter) is re-ground with hashlib and must be rejected (minimality)."""
    rows, p, full = args
    bad = []
    for idx, seed, adrs, m, c in rows:
        sh = hashlib.sha256(seed + bytes(48))
        if c == FAILED:
            bad.append(idx)
            continue
        if not wots_c.accept(_wots_d(sh, adrs, m, c), p):
            bad.append(idx)
            continue
        if full and any(wots_c.accept(_wots_d(sh, adrs, m, j), p) for j in range(c)):
            bad.append(idx)
    return bad


def wots_rows(mat, counters, idx):
    return [(int(i), bytes(mat["seed"][i]), bytes(mat["adrs"][i]), bytes(mat["m"][i]), int(counters[i]))
            for i in idx]


# ---------------------------------------------------------------- FORS+C / PORS+FP

def fors_key(run_id, config_id):
    raw = stream(run_id, config_id + "/key", 0, 1, 48)[0].tobytes()
    return raw[:16], raw[16:32], raw[32:48]  # SK.prf, PK.seed, PK.root


def fors_msgs(run_id, config_id, i0, n):
    return [r.tobytes() for r in stream(run_id, config_id, i0, n, 32)]


def fors_records(run_id, cfg, msgs):
    from grind import gpu
    sk, seed, root = fors_key(run_id, cfg.id)
    return gpu.fors_records(sk, seed, root, msgs, cfg.kind)


def _digest(kind, sk, seed, root, m, c):
    if kind == "ctr":
        r = hmac.new(sk, seed + m, hashlib.sha256).digest()[:16]
        inner = hashlib.sha256(r + seed + root + m + c.to_bytes(4, "big")).digest()
        return hashlib.sha256(r + seed + inner + bytes(4)).digest()
    r = fors_c.prf_r(sk, seed, m, c)
    return fors_c.h_msg(r, seed, root, m, 64 if kind == "pors" else 32)


def _accepted(kind, dg, cfg):
    if kind == "pors":
        return fors_c.pors_accept(dg, cfg.k << cfg.a, cfg.k, cfg.h, cfg.m_max)
    return fors_c.zero_bits_ok(dg, cfg.k, cfg.a)


def fors_check(args):
    """Worker: (rows, cfg, key, full) -> bad indices. rows: [(idx, msg, counter)]."""
    rows, cfg, (sk, seed, root), full = args
    bad = []
    for idx, m, c in rows:
        if c == FAILED or not _accepted(cfg.kind, _digest(cfg.kind, sk, seed, root, m, c), cfg):
            bad.append(idx)
            continue
        if full and any(_accepted(cfg.kind, _digest(cfg.kind, sk, seed, root, m, j), cfg) for j in range(c)):
            bad.append(idx)
    return bad
