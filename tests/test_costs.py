"""
Tests for grindstone/ref/costs.py (port of BlockstreamResearch/SPHINCS-Parameters
costs.sage @ ceee8ed).

Two reference profiles:
  * PAPER: ePrint 2025/2203 Tables 1-2 (v. 2025-12-05/08): R = 32 B,
    "uncached" hash convention (SPX row verify = 2387 compr.).
  * REPO:  costs.sage HEAD ceee8ed: R = 16 B, "cached" convention
    (golden values from tests/fixtures.json "variants" in the repo).
"""
import math
import os
import sys
from fractions import Fraction
from itertools import product

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ref"))
import costs as c  # noqa: E402

PAPER = dict(convention="uncached", randomness_size_=c.PAPER_RANDOMNESS_SIZE)
REPO = dict(convention="cached", randomness_size_=None)


def _sci(x):
    """Paper prints values >= 10^5 as 'NNN * 10^4' (rounded)."""
    return x if x < 100_000 else round(x / 1e4)


# ---------------------------------------------------------------------------
# (a) Kudinov-Nick headline rows: 3128 B @2^20, 3440 B @2^30, 4036 B @2^40
# ---------------------------------------------------------------------------
# All three are W+C P+FP rows (Table 1 bold rows for 2^40 / 2^30; Table 2 row
# h=24 for 2^20 -- note Table 2 also lists a smaller 2^20 P+FP row, 2856 B).
HEADLINE = [
    # scheme,  q,  h, d,  a,  k,   w,  S,    expected bytes
    ("W+C_P+FP", 20, 24, 2, 16, 8, 16, 240, 3128),
    ("W+C_P+FP", 30, 32, 4, 14, 10, 256, 2040, 3440),
    ("W+C_P+FP", 40, 40, 5, 14, 11, 256, 2040, 4036),
]


@pytest.mark.parametrize("scheme,q,h,d,a,k,w,S,expected", HEADLINE)
def test_headline_sizes_paper(scheme, q, h, d, a, k, w, S, expected):
    r = c.compute_single(scheme, q, h, d, a, k, w, S, **PAPER)
    assert abs(r["size"] - expected) <= 1
    assert r["security"] >= 128.0


@pytest.mark.parametrize("scheme,q,h,d,a,k,w,S,expected", HEADLINE)
def test_headline_sizes_repo_head_is_16B_smaller(scheme, q, h, d, a, k, w, S, expected):
    # Repo HEAD shrank R from 32 B to 16 B; every row is exactly 16 B smaller.
    r = c.compute_single(scheme, q, h, d, a, k, w, S, with_security=False, **REPO)
    assert r["size"] == expected - 16


# Full Tables 1-2 of ePrint 2025/2203:
# scheme, q, h, d, a, k, w, S, size, exp_search, wc_search, ver_hashes, ver_compr
PAPER_TABLE = [
    ("W+C", 40, 44, 4, 16, 8, 16, 240, 4976, 264, 1907, 1150, 1357),
    ("W+C", 40, 44, 4, 16, 8, 16, 304, 4976, 5344, 39021, 894, 1101),
    ("W+C", 40, 44, 4, 16, 8, 256, 2040, 3952, 2996, 21854, 8350, 8541),
    ("W+C", 40, 40, 5, 14, 11, 256, 2040, 4612, 3745, 23589, 10417, 10635),
    ("W+C", 40, 40, 5, 14, 11, 256, 2840, 4612, 15, 95, 6417, 6635),
    ("W+C_F+C", 40, 44, 4, 16, 8, 16, 240, 4704, 13, 273, 1133, 1324),
    ("W+C_F+C", 40, 40, 5, 14, 11, 256, 2040, 4372, 36513, 70, 10402, 10606),
    ("W+C_P+FP", 40, 44, 4, 16, 8, 16, 240, 4480, 24, 507, 1118, 1292),
    ("W+C_P+FP", 40, 40, 5, 14, 11, 256, 2040, 4036, 23, 462, 10380, 10559),
    ("W+C", 30, 36, 3, 14, 9, 16, 240, 4316, 198, 1745, 899, 1088),
    ("W+C", 30, 33, 3, 15, 9, 16, 240, 4412, 198, 1745, 905, 1100),
    ("W+C", 30, 33, 3, 15, 9, 16, 304, 4412, 4008, 35705, 713, 908),
    ("W+C", 30, 33, 3, 15, 9, 256, 2040, 3644, 2247, 19997, 6305, 6488),
    ("W+C", 30, 32, 4, 14, 10, 256, 2040, 3984, 2996, 21854, 8352, 8544),
    ("W+C", 30, 32, 4, 14, 10, 256, 2840, 3984, 12, 88, 5152, 5344),
    ("W+C_F+C", 30, 36, 3, 14, 9, 16, 240, 4076, 32966, 68, 884, 1059),
    ("W+C_F+C", 30, 33, 3, 15, 9, 16, 240, 4156, 65734, 136, 889, 1069),
    ("W+C_F+C", 30, 33, 3, 15, 9, 256, 2040, 3388, 67783, 138, 6289, 6457),
    ("W+C_F+C", 30, 32, 4, 14, 10, 256, 2040, 3744, 35764, 70, 8337, 8514),
    ("W+C_P+FP", 30, 36, 3, 14, 9, 16, 240, 3788, 31, 653, 865, 1019),
    ("W+C_P+FP", 30, 33, 3, 15, 9, 16, 240, 3900, 16, 339, 872, 1033),
    ("W+C_P+FP", 30, 32, 4, 14, 10, 256, 2040, 3440, 20, 411, 8317, 8472),
    ("W+C", 20, 24, 2, 16, 8, 16, 240, 3624, 132, 1566, 646, 817),
    ("W+C", 20, 24, 2, 16, 8, 256, 2040, 3112, 1498, 17952, 4246, 4409),
    ("W+C_F+C", 20, 24, 2, 16, 8, 16, 240, 3352, 13, 273, 629, 784),
    ("W+C_P+FP", 20, 24, 2, 16, 8, 16, 240, 3128, 24, 507, 614, 752),
    ("W+C", 20, 20, 2, 15, 10, 256, 2040, 3432, 1498, 17952, 4266, 4448),
    ("W+C_F+C", 20, 20, 2, 15, 10, 256, 2040, 3176, 67034, 138, 4250, 4416),
    ("W+C_P+FP", 20, 20, 2, 15, 10, 256, 2040, 2856, 53, 1111, 4229, 4372),
]


@pytest.mark.parametrize("row", PAPER_TABLE, ids=lambda r: f"{r[0]}-2^{r[1]}-{r[2]}-{r[6]}-{r[7]}")
def test_paper_tables_full_row(row):
    s, q, h, d, a, k, w, S, size, exp_s, wc_s, ver_h, ver_c = row
    r = c.compute_single(s, q, h, d, a, k, w, S, with_security=False, **PAPER)
    assert r["size"] == size
    assert r["verify_hashes"] == ver_h
    assert r["verify_compressions"] == ver_c
    # numbers >= 10^5 are printed in units of 10^4 in the paper
    assert _sci(r["exp_search"]) == exp_s
    assert _sci(r["worst_search"]) == wc_s


def test_paper_spx_baseline():
    r = c.compute_single("SPX", 64, 63, 7, 12, 14, 16, 0, **PAPER)
    assert (r["size"], r["verify_hashes"], r["verify_compressions"]) == (7872, 2088, 2387)
    assert round(r["sign_hashes"] / 1e4) == 219
    assert r["security"] >= 128.0


# Repo HEAD golden values: SPHINCS-Parameters/tests/fixtures.json "variants"
REPO_FIXTURES = {
    ("W+C", 44, 4, 8, 16, 16, 240): (4960, 1069055, 5849347, 1185),
    ("W+C", 40, 5, 11, 14, 256, 2040): (4596, 1050111, 5794969, 10441),
    ("W+C", 40, 5, 11, 14, 256, 2840): (4596, 1050111, 5941944, 6441),
    ("W+C_F+C", 44, 4, 8, 16, 16, 240): (4688, 1069055, 5914880, 1168),
    ("W+C_F+C", 40, 5, 11, 14, 256, 2040): (4356, 1050111, 5811349, 10425),
    ("W+C_F+C", 20, 2, 10, 15, 256, 2040): (3160, 4200447, 9418194, 4261),
    ("W+C_P+FP", 44, 4, 8, 16, 16, 240): (4464, 1069055, 6337159, 1151),
    ("W+C_P+FP", 40, 5, 11, 14, 256, 2040): (4020, 1050111, 6237515, 10401),
    ("W+C_P+FP", 24, 2, 8, 16, 16, 240): (3112, 2138111, 6337029, 631),
}


@pytest.mark.parametrize("key", list(REPO_FIXTURES))
def test_repo_fixture_variants(key):
    s, h, d, k, a, w, S = key
    size, kg, sg, sv = REPO_FIXTURES[key]
    r = c.compute_single(s, 40, h, d, a, k, w, S, with_security=False, **REPO)
    assert (r["size"], r["keygen_compressions"], r["sign_compressions"],
            r["verify_compressions"]) == (size, kg, sg, sv)


def test_repo_spx_baseline_fixture():
    r = c.compute_single("SPX", 64, 63, 7, 12, 14, 16, 0, with_security=False, **REPO)
    assert (r["size"], r["keygen_compressions"], r["sign_compressions"],
            r["verify_compressions"], r["verify_compressions_worst"]) == \
        (7856, 292351, 2218483, 2155, 3891)


def test_security_pass_set_matches_repo():
    # fixtures.json _comment_w_grid_2026_08_21: 6,479 (h,d,k,a) combos pass
    # FORS security >= 128 at q_s = 2^40 on the canonical grid.
    pairs = [(h, d) for h in range(40, 51) for d in range(2, 26) if h % d == 0]
    ok = {}
    n = 0
    for h, d in pairs:
        for k in range(6, 25):
            for a in range(8, 21):
                if (h, k, a) not in ok:
                    ok[(h, k, a)] = c.compute_security(2 ** 40, h, k, a, "FORS") >= 128.0
                n += ok[(h, k, a)]
    assert n == 6479


# ---------------------------------------------------------------------------
# (b) WOTS+C expected tries per layer (project plan Sec. 3.5 table)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("w,len1,S,expected,ndigits", [
    (16, 32, 240, 65.7, 1),
    (16, 32, 304, 1335, 0),
    (256, 16, 2040, 748, 0),
    (256, 16, 2840, 30143, 0),
])
def test_wots_c_expected_tries(w, len1, S, expected, ndigits):
    assert c.compute_wots_len1(w) == len1
    assert round(c.wots_c_expected_tries(w, len1, S), ndigits) == expected


def test_nu_matches_polynomial_coefficient():
    # nu = coefficient of x^S in (1 + x + ... + x^{w-1})^l  (paper Sec. 5.1)
    for w, l in [(4, 5), (16, 4), (8, 6)]:
        poly = [1]
        for _ in range(l):
            new = [0] * (len(poly) + w - 1)
            for i, cf in enumerate(poly):
                for j in range(w):
                    new[i + j] += cf
            poly = new
        for S in range(0, l * (w - 1) + 1):
            assert c.compute_nu(l, S, w) == poly[S]


def test_wots_c_zero_chain_probability_bruteforce():
    # z zero chains: P(last z digits == 0 and first len1-z sum to S), brute force
    w, len1, z = 4, 5, 1
    for S in range(0, (len1 - z) * (w - 1) + 1):
        good = sum(1 for t in product(range(w), repeat=len1)
                   if all(x == 0 for x in t[len1 - z:]) and sum(t[:len1 - z]) == S)
        p = c.wots_c_success_prob(w, len1, S, z=z)
        assert good > 0 and p == Fraction(good, w ** len1)


def test_mean_sum_is_optimal():
    for w in (16, 256):
        len1 = c.compute_wots_len1(w)
        s0 = c.wots_c_mean_sum(w, len1)
        best = min(range(0, len1 * (w - 1) + 1), key=lambda S: c.wots_c_expected_tries(w, len1, S))
        assert c.compute_nu(len1, best, w) == c.compute_nu(len1, s0, w)


def test_worst_case_geometric_single_instance():
    # d = 1: worst_case is the geometric 1 - 2^-30 quantile, ~ 20.79 * 2^a
    for a in (8, 14, 16, 20):
        k = c.worst_case(Fraction(1, 2 ** a), 2.0 ** -30, 1)
        assert k == math.ceil(c.geometric_quantile(2.0 ** -a, 2.0 ** -30)) or \
            abs(k - c.geometric_quantile(2.0 ** -a, 2.0 ** -30)) <= 1


def test_pure_python_worst_case_matches_scipy():
    if c._scipy_binom is None:
        pytest.skip("scipy not installed")
    for p, d in [(1 / 65.7, 4), (1 / 748, 5), (2.0 ** -14, 1)]:
        saved = c._scipy_binom
        try:
            ref = c.worst_case(p, 2.0 ** -30, d)
            c._scipy_binom = None
            alt = c.worst_case(p, 2.0 ** -30, d)
        finally:
            c._scipy_binom = saved
        assert abs(ref - alt) <= 1
