import os

import numpy as np
import pytest

from ref import sha2, wots_c

# doc §3.5 table: expected tries per layer
TABLE = [
    (16, 32, 240, 65.7),
    (16, 32, 304, 1335),
    (256, 16, 2040, 748),
    (256, 16, 2840, 30143),
]


@pytest.mark.parametrize("w,len1,S,expected", TABLE)
def test_expected_tries(w, len1, S, expected):
    p = wots_c.WotsParams(w=w, len1=len1, S=S)
    assert float(1 / wots_c.success_prob(p)) == pytest.approx(expected, rel=1e-3)


def test_probabilities_sum_to_one():
    w, len1 = 16, 8
    total = sum(wots_c.success_prob(wots_c.WotsParams(w, len1, s)) for s in range(len1 * (w - 1) + 1))
    assert total == 1


def test_digits_msb_first():
    assert wots_c.digits(bytes([0xAB, 0xCD]), 4, 4) == [0xA, 0xB, 0xC, 0xD]


@pytest.mark.parametrize("lay", [wots_c.WotsLayout(), wots_c.WotsLayout(ctr_le=True),
                                 wots_c.WotsLayout(ctr_in_adrs=True)])
def test_template_matches_th(lay):
    seed, adrs, m = os.urandom(16), os.urandom(22), os.urandom(16)
    st = sha2.seed_midstate(seed)
    words, off = wots_c.final_block_template(adrs, m, lay)
    for count in (0, 1, 0x01020304):
        blk = bytearray(np.array(words, dtype=">u4").tobytes())
        blk[off:off + 4] = count.to_bytes(4, "little" if lay.ctr_le else "big")
        got = np.array(sha2.compress(st, bytes(blk))[:4], dtype=">u4").tobytes()
        assert got == sha2.th(st, wots_c.tail(adrs, m, count, lay), b"")


cupy = pytest.importorskip("cupy")


@pytest.mark.parametrize("lay", [wots_c.WotsLayout(), wots_c.WotsLayout(ctr_le=True)])
def test_gpu_matches_reference(lay):
    from grind import gpu
    p = wots_c.WotsParams(w=16, len1=32, S=240, z_bits=2)
    mids, tm, refs = [], [], []
    for _ in range(64):
        seed, adrs, m = os.urandom(16), os.urandom(22), os.urandom(16)
        st = sha2.seed_midstate(seed)
        t, off = wots_c.final_block_template(adrs, m, lay)
        mids.append(st)
        tm.append(t)
        refs.append(wots_c.grind(st, adrs, m, p, lay))
    c, _, _ = gpu.grind_wots_c(np.array(mids), np.array(tm), off, p, ctr_le=lay.ctr_le)
    assert list(c) == refs


def test_shrincs_tail_matches_spec():
    # SHRINCS.md H_grind: sha256(pk_seed ‖ 0^48 ‖ ADRS[:10] ‖ digest(32) ‖ 0^4 ‖ ctr_BE2)[:16]
    import hashlib
    seed, adrs, dg = os.urandom(16), os.urandom(10), os.urandom(32)
    st = sha2.seed_midstate(seed)
    for c in (0, 1, 0xBEEF):
        want = hashlib.sha256(seed + bytes(48) + adrs + dg + bytes(4) + c.to_bytes(2, "big")).digest()[:16]
        assert sha2.th(st, wots_c.tail(adrs, dg, c, wots_c.SHRINCS), b"") == want


def test_shrincs_gpu_cpu_match_reference():
    from grind import cpu, gpu
    p = wots_c.WotsParams(w=16, len1=32, S=240)
    lay = wots_c.SHRINCS
    st = sha2.seed_midstate(os.urandom(16))
    mids, tm, refs = [], [], []
    for _ in range(64):
        adrs, dg = os.urandom(10), os.urandom(32)
        t, off = wots_c.final_block_template(adrs, dg, lay)
        mids.append(st)
        tm.append(t)
        refs.append(wots_c.grind(st, adrs, dg, p, lay))
    g, _, _ = gpu.grind_wots_c(np.array(mids), np.array(tm), off, p, ctr_bytes=2)
    c, _, _ = cpu.grind_wots_c(mids, tm, off, p, ctr_bytes=2)
    assert list(g) == refs and list(c) == refs


def test_shrincs_counter_exhaustion():
    """With an impossible target the 2-byte counter must stop at 2^16 tries on all paths."""
    from grind import cpu, gpu
    p = wots_c.WotsParams(w=16, len1=32, S=0)  # all-zero digits: p = 2^-128
    st = sha2.seed_midstate(os.urandom(16))
    t, off = wots_c.final_block_template(os.urandom(10), os.urandom(32), wots_c.SHRINCS)
    g, _, _ = gpu.grind_wots_c(np.array([st]), np.array([t]), off, p, ctr_bytes=2)
    c, _, _ = cpu.grind_wots_c([st], [t], off, p, ctr_bytes=2)
    assert g[0] == 0xFFFFFFFF and c[0] == 0xFFFFFFFF
