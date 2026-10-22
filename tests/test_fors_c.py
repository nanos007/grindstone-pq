import hashlib
import os
import random

import pytest

from ref import fors_c


def test_compressions_per_attempt():
    # kb/raw/A/pseudocode.md §5
    assert fors_c.count_compressions("R") == 6
    assert fors_c.count_compressions("ctr") == 3
    assert fors_c.count_compressions("R", pors=True) == 7


@pytest.mark.parametrize("k,a,h,d,m", [(8, 16, 44, 4, 23), (11, 14, 40, 5, 25), (9, 14, 36, 3, 21),
                                         (9, 15, 33, 3, 22), (10, 14, 32, 4, 22), (8, 16, 24, 2, 20),
                                         (10, 15, 20, 2, 23)])
def test_digest_len(k, a, h, d, m):
    assert fors_c.digest_len(k, a, h, d) == m


def test_zero_mask_matches_bit_rule():
    for k, a in ((11, 14), (10, 15), (9, 14)):
        mask = fors_c.zero_mask_words(k, a)
        for _ in range(2000):
            dg = os.urandom(32)
            words = [int.from_bytes(dg[4 * i:4 * i + 4], "big") for i in range(8)]
            via_mask = all(w & mk == 0 for w, mk in zip(words, mask))
            assert via_mask == fors_c.zero_bits_ok(dg, k, a)


def test_h_msg_matches_fips205_form():
    r, s, root, m = os.urandom(16), os.urandom(16), os.urandom(16), os.urandom(32)
    inner = hashlib.sha256(r + s + root + m).digest()
    want = hashlib.sha256(r + s + inner + b"\0\0\0\0").digest() + hashlib.sha256(r + s + inner + b"\0\0\0\1").digest()
    assert fors_c.h_msg(r, s, root, m, 40) == want[:40]


def _brute_octopus(xs, t):
    hgt = (t - 1).bit_length()
    s = t - (1 << (hgt - 1))
    # node ids: (level, index); leaves < 2s at level 0, others at level 1 as (i - s)
    on_path = set()
    for x in xs:
        lvl, v = (0, x) if x < 2 * s else (1, x - s)
        while lvl < hgt:
            on_path.add((lvl, v))
            lvl, v = lvl + 1, v >> 1
    return sum(1 for (lvl, v) in on_path if (lvl, v ^ 1) not in on_path)


@pytest.mark.parametrize("t", [8, 9, 12, 100, 147456, 524288])
def test_octopus_vs_bruteforce(t):
    rng = random.Random(t)
    for _ in range(200):
        k = rng.randint(1, min(11, t))
        xs = sorted(rng.sample(range(t), k))
        assert fors_c.octopus_size(xs, t) == _brute_octopus(xs, t)


# kb/constructions/grind_pseudocode.md §0 (Agent A's DP)
@pytest.mark.parametrize("h,a,k,want", [(44, 16, 8, 1.0), (40, 14, 11, 0.998608), (36, 14, 9, 0.992219),
                                         (33, 15, 9, 0.987414), (32, 14, 10, 0.996361),
                                         (24, 16, 8, 1.0), (20, 15, 10, 0.993520)])
def test_p_enough_table(h, a, k, want):
    assert fors_c.p_enough(k << a, k, h) == pytest.approx(want, abs=1e-6)


def test_p_enough_monte_carlo():
    t, k, h = 3 * 2 ** 5, 10, 400  # b = 7, nu = 16: P_enough ~ 0.6
    rng = random.Random(1)
    n = 20000
    hits = sum(fors_c.hash_to_subset(rng.randbytes(64), t, k, h) is not None for _ in range(n))
    assert hits / n == pytest.approx(fors_c.p_enough(t, k, h), abs=0.015)


cupy = pytest.importorskip("cupy")


@pytest.mark.parametrize("layout", ["R", "ctr"])
def test_gpu_fors_matches_reference(layout):
    from grind import gpu
    sk, seed, root = os.urandom(16), os.urandom(16), os.urandom(16)
    k, a, h, d = 11, 7, 40, 5
    msgs = [os.urandom(32) for _ in range(64)]
    fn = fors_c.grind_R if layout == "R" else fors_c.grind_ctr
    refs = [fn(sk, seed, root, m, k, a, h, d) for m in msgs]
    c, _, _ = gpu.grind_fors(gpu.fors_records(sk, seed, root, msgs, layout), layout, k, a)
    assert list(c) == refs


def test_gpu_pors_matches_reference():
    from grind import gpu
    sk, seed, root = os.urandom(16), os.urandom(16), os.urandom(16)
    k, a, h, m_max = 10, 6, 20, 40
    msgs = [os.urandom(32) for _ in range(64)]
    refs = [fors_c.grind_pors(sk, seed, root, m, k, a, h, m_max) for m in msgs]
    c, _, _ = gpu.grind_fors(gpu.fors_records(sk, seed, root, msgs, "pors"), "pors", k, a, h=h, m_max=m_max)
    assert list(c) == refs
