"""
GRINDSTONE reference cost model for Bitcoin-tuned SPHINCS+ variants.

Plain-Python port of the cost model in BlockstreamResearch/SPHINCS-Parameters
at commit ceee8ed67e8b69ae2d8efd10065b5a550c330018 (2026-08-26):

  * costs.sage        -- sizes, signing / verification / keygen hash counts,
                         WOTS+C nu, worst_case(), PORS+FP m_max selection
  * security.sage     -- FORS / PORS+FP classical security level
  * octopus_pmf.py    -- Octopus auth-set PMF -> log2 E[work] (MIT, Abri-Katz,
                         https://github.com/MehdiAbri/PORS-FP), vendored below

Function names follow the originals; each docstring cites file:line.
Exact integer / Fraction arithmetic is used wherever the sage code is exact
(nu, w^l, binomials, sizes, hash counts). The sage RealField(100) parts
(security sum, worst_case tail) are done in log-space float64 here; see the
docstrings for the numerical caveats.

Extensions beyond the repo (clearly marked "GRINDSTONE extension"):
  * z zero-chains for WOTS+C (paper ePrint 2025/2203 Sec. 5); the repo fixes z=0.
  * explicit m_max override for PORS+FP (the repo derives m_max from a
    signing-time ratio rule, compute_mmax).
  * randomness_size / hash convention as arguments, so the paper tables
    (R = 32 B, "uncached" convention, Dec 2025) and the repo HEAD
    (R = 16 B, "cached" convention) can both be reproduced.

Scheme names (as in costs.sage): "SPX", "W+C", "W+C_F+C", "W+C_P+FP".
"""
from __future__ import annotations

import math
from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
from math import ceil, comb, floor
from typing import Dict, List, Optional, Tuple

# =============================================================================
# Constants  (costs.sage:38-63)
# =============================================================================

hashbytes = 16          # costs.sage:38   n = 16 bytes (NIST L1)
counter_size = 4        # costs.sage:39   WOTS+C counter, 32 bits
randomness_size = 16    # costs.sage:40   R at repo HEAD ceee8ed

#: R size used for the published tables of ePrint 2025/2203 (Dec 2025),
#: which state "PRF_msg output to be 256 bits" (Sec. 13). All paper sizes are
#: exactly repo-HEAD size + 16.
PAPER_RANDOMNESS_SIZE = 32

#: Hash-cost convention. "cached" = repo HEAD default (PK.seed midstate cached),
#: "uncached" = original convention used for the paper tables. costs.sage:45-56
DEFAULT_CONVENTION = "cached"

C_Th1 = 1      # costs.sage:58
C_Th1c = 1     # costs.sage:59
C_Hmsg = 2     # costs.sage:61
C_PRFmsg = 2   # costs.sage:62
C_PRF = 1      # costs.sage:63

SCHEMES = ("SPX", "W+C", "W+C_F+C", "W+C_P+FP")


def C_Th2(convention: str = DEFAULT_CONVENTION) -> int:
    """Compressions for a 2-input tweakable hash. costs.sage:60"""
    _check_conv(convention)
    return 1 if convention == "cached" else 2


def _check_conv(convention: str) -> None:
    assert convention in ("cached", "uncached"), convention


def compute_Th(n: int, convention: str = DEFAULT_CONVENTION) -> int:
    """Compression calls for a tweakable hash over n hash-sized values.

    costs.sage:65-74
      cached:   ceil((22*8 + 128*n + 65) / 512)
      uncached: ceil((128 + 96 + 128*n + 65) / 512)
    """
    _check_conv(convention)
    if convention == "cached":
        return -(-(22 * 8 + 128 * n + 65) // 512)
    return -(-(128 + 96 + 128 * n + 65) // 512)


# =============================================================================
# Reference parameter sets  (costs.sage:85-131)
# Format: (scheme, q_s, h, d, a, k, w, l, swn, bold)
# =============================================================================

PARAMETER_SETS = [
    ("SPX", 64, 63, 7, 12, 14, 16, 35, 0, True),
    ("W+C", 40, 44, 4, 16, 8, 16, 32, 240, False),
    ("W+C", 40, 44, 4, 16, 8, 16, 32, 304, False),
    ("W+C", 40, 44, 4, 16, 8, 256, 16, 2040, False),
    ("W+C", 40, 40, 5, 14, 11, 256, 16, 2040, False),
    ("W+C", 40, 40, 5, 14, 11, 256, 16, 2840, False),
    ("W+C_F+C", 40, 44, 4, 16, 8, 16, 32, 240, False),
    ("W+C_F+C", 40, 40, 5, 14, 11, 256, 16, 2040, True),
    ("W+C_P+FP", 40, 44, 4, 16, 8, 16, 32, 240, False),
    ("W+C_P+FP", 40, 40, 5, 14, 11, 256, 16, 2040, True),
    ("W+C", 30, 36, 3, 14, 9, 16, 32, 240, False),
    ("W+C", 30, 33, 3, 15, 9, 16, 32, 240, False),
    ("W+C", 30, 33, 3, 15, 9, 16, 32, 304, False),
    ("W+C", 30, 33, 3, 15, 9, 256, 16, 2040, False),
    ("W+C", 30, 32, 4, 14, 10, 256, 16, 2040, False),
    ("W+C", 30, 32, 4, 14, 10, 256, 16, 2840, False),
    ("W+C_F+C", 30, 36, 3, 14, 9, 16, 32, 240, False),
    ("W+C_F+C", 30, 33, 3, 15, 9, 16, 32, 240, False),
    ("W+C_F+C", 30, 33, 3, 15, 9, 256, 16, 2040, False),
    ("W+C_F+C", 30, 32, 4, 14, 10, 256, 16, 2040, True),
    ("W+C_P+FP", 30, 36, 3, 14, 9, 16, 32, 240, False),
    ("W+C_P+FP", 30, 33, 3, 15, 9, 16, 32, 240, False),
    ("W+C_P+FP", 30, 32, 4, 14, 10, 256, 16, 2040, True),
    ("W+C", 20, 24, 2, 16, 8, 16, 32, 240, False),
    ("W+C", 20, 24, 2, 16, 8, 256, 16, 2040, False),
    ("W+C_F+C", 20, 24, 2, 16, 8, 16, 32, 240, False),
    ("W+C_P+FP", 20, 24, 2, 16, 8, 16, 32, 240, False),
    ("W+C", 20, 20, 2, 15, 10, 256, 16, 2040, False),
    ("W+C_F+C", 20, 20, 2, 15, 10, 256, 16, 2040, False),
    ("W+C_P+FP", 20, 20, 2, 15, 10, 256, 16, 2040, False),
]


# =============================================================================
# WOTS helpers  (costs.sage:144-205)
# =============================================================================

def _log2_int(w: int) -> int:
    lg = w.bit_length() - 1
    assert 1 << lg == w, "w must be a power of two"
    return lg


def compute_wots_len1(w: int) -> int:
    """len1 = ceil(8n / log2 w). costs.sage:159,163"""
    return -(-(hashbytes * 8) // _log2_int(w))


def compute_wots_l(scheme: str, w: int, z: int = 0) -> int:
    """WOTS chain count. costs.sage:144-163

    SPX (WOTS-TW): l = l1 + l2,  l2 = floor(log_w(l1*(w-1))) + 1
    WOTS+C:        l = l1 - z    (z zero-chains omitted; GRINDSTONE extension,
                                  paper Sec. 5 "l = len1 - z"; repo has z = 0)
    """
    l1 = compute_wots_len1(w)
    if scheme == "SPX":
        assert z == 0
        return l1 + _wots_len2(l1, w)
    return l1 - z


def _wots_len2(l1: int, w: int) -> int:
    # floor(log_w(l1*(w-1))) + 1, computed exactly with integers
    c, l2 = l1 * (w - 1), 0
    while c >= 1:
        c //= w
        l2 += 1
    return l2


def compute_wots_tw_worst_steps(l1: int, l2: int, w: int) -> int:
    """Worst-case WOTS-TW verification chain steps per layer. costs.sage:165-182"""
    C = l1 * (w - 1)
    ds, rem = 0, C
    while rem > 0:
        ds += rem % w
        rem //= w
    return l1 * (w - 1) + l2 * (w - 1) - ds


def compute_nu(l: int, paramsum: int, w: int) -> int:
    """Number of base-w l-digit strings with digit sum exactly S_{w,n}.

    costs.sage:184-205 (paper ePrint 2025/2203 Sec. 5.1 eq. (1)):
        nu = sum_{j=0}^{l} (-1)^j C(l,j) C(S + l - j*w - 1, l - 1)
    Exact integer. As in the original, returns 1 (not 0) if nu == 0.
    """
    nu = 0
    for j in range(l + 1):
        n = (paramsum + l) - j * w - 1
        b2 = comb(n, l - 1) if (n >= l - 1 and l - 1 >= 0) else 0
        nu += (-1) ** j * comb(l, j) * b2
    if nu == 0:
        nu = 1
    return nu


def wots_c_success_prob(w: int, len1: int, swn: int, z: int = 0, z_b: int = 0) -> Fraction:
    """WOTS+C per-attempt success probability (exact Fraction).

    Paper ePrint 2025/2203 Sec. 5.1:  p_nu = nu / (w^l * 2^{z_b}).
    costs.sage:409-410 uses p = nu(l, S, w) / w^l with l = len1, z = z_b = 0.

    GRINDSTONE extension for z zero-chains (paper Sec. 5 condition 2): the
    digest must give len1 digits with the last z equal to 0 and the remaining
    l = len1 - z summing to S, so p = nu(len1 - z, S, w) / w^len1.
    (The paper's "w^l" in the denominator is ambiguous when z > 0; we use
    w^len1, which is the probability actually seen by the grinder.)
    """
    l = len1 - z
    nu = compute_nu(l, swn, w)
    return Fraction(nu, w ** len1 * 2 ** z_b)


def wots_c_expected_tries(w: int, len1: int, swn: int, z: int = 0, z_b: int = 0) -> float:
    """Expected WOTS+C attempts per hypertree layer = 1/p (geometric mean)."""
    p = wots_c_success_prob(w, len1, swn, z, z_b)
    return float(1 / p)


def wots_c_mean_sum(w: int, len1: int) -> int:
    """S_{w,n} with the fewest expected tries: floor(len1*(w-1)/2) (paper Sec. 5)."""
    return (len1 * (w - 1)) // 2


# =============================================================================
# PORS helpers  (costs.sage:211-248) + vendored octopus_pmf.py (MIT)
# =============================================================================

def compute_pors_tree_geometry(k: int, a: int) -> Tuple[int, int, int]:
    """(t, subtree_height, extra_leaves) for t = k*2^a. costs.sage:211-223"""
    t = k * (2 ** a)
    subtree_height = t.bit_length() - 1        # floor(log2 t), exact
    return t, subtree_height, t - 2 ** subtree_height


# ---- octopus_pmf.py:14-328 (Copyright Mehdi Abri, MIT), unchanged logic ----

def _comb0(n: int, k: int) -> int:
    """octopus_pmf.py:14-17"""
    if n < 0 or k < 0 or k > n:
        return 0
    return math.comb(n, k)


def _P(x: int, j: int, s: int) -> float:
    """octopus_pmf.py:19-26"""
    if x % 2 != 0 or j < 0 or s < 0 or j > x or 2 * s > j:
        return 0.0
    num = _comb0(x // 2, j - s) * _comb0(j - s, s) * (2 ** (j - 2 * s))
    den = _comb0(x, j)
    if den == 0:
        return 0.0
    return num / den


@lru_cache(maxsize=None)
def _M(ell: int, L: int, R: int, kL: int, kR: int, c: int = 0) -> Dict[int, float]:
    """Upper-level recursion M_h(L,R,kL,kR,c). octopus_pmf.py:31-256"""
    if ell == 0:
        return {0: 1.0}
    if not (0 <= kL <= L and 0 <= kR <= R):
        return {}
    out: Dict[int, float] = defaultdict(float)
    P, comb_ = _P, _comb0
    if L % 2 == 0:
        if c == 0:
            for rL in range(0, kL // 2 + 1):
                wL = P(L, kL, rL)
                if wL == 0.0:
                    continue
                for rR in range(0, kR // 2 + 1):
                    wR = P(R, kR, rR)
                    if wR == 0.0:
                        continue
                    singles = (kL + kR) - 2 * (rL + rR)
                    nxt = _M(ell - 1, L // 2, R // 2, kL - rL, kR - rR, 0)
                    w = wL * wR
                    for m_sub, p_sub in nxt.items():
                        out[singles + m_sub] += w * p_sub
        elif c == +1:
            if R < 1 or kR < 1:
                return {}
            if R == 1:
                for rL in range(0, kL // 2 + 1):
                    wL = P(L, kL, rL)
                    if wL == 0.0:
                        continue
                    singles = (kL + kR) - 2 * rL
                    nxt = _M(ell - 1, L // 2, 0, kL - rL, kR, +1)
                    for m_sub, p_sub in nxt.items():
                        out[singles + m_sub] += wL * p_sub
            else:
                denom = comb_(R - 1, kR - 1)
                if denom == 0:
                    return {}
                wY1 = comb_(R - 2, kR - 2) / denom
                wY0 = comb_(R - 2, kR - 1) / denom
                for rL in range(0, kL // 2 + 1):
                    wL = P(L, kL, rL)
                    if wL == 0.0:
                        continue
                    for y, wy in ((1, wY1), (0, wY0)):
                        if wy == 0.0:
                            continue
                        for rRp in range(0, (kR - 1 - y) // 2 + 1):
                            wRp = P(R - 2, kR - 1 - y, rRp)
                            if wRp == 0.0:
                                continue
                            rR = y + rRp
                            singles = (kL + kR) - 2 * (rL + rR)
                            nxt = _M(ell - 1, L // 2, R // 2, kL - rL, kR - rR, +1)
                            w = wL * wy * wRp
                            for m_sub, p_sub in nxt.items():
                                out[singles + m_sub] += w * p_sub
        else:  # c == -1
            if R == 0 or R == 1:
                if kR != 0:
                    return {}
                for rL in range(0, kL // 2 + 1):
                    wL = P(L, kL, rL)
                    if wL == 0.0:
                        continue
                    singles = (kL + kR) - 2 * rL
                    nxt = _M(ell - 1, L // 2, 0, kL - rL, kR, -1)
                    for m_sub, p_sub in nxt.items():
                        out[singles + m_sub] += wL * p_sub
            else:
                denom = comb_(R - 1, kR)
                if denom == 0:
                    return {}
                wZ0 = comb_(R - 2, kR) / denom
                wZ1 = comb_(R - 2, kR - 1) / denom
                for rL in range(0, kL // 2 + 1):
                    wL = P(L, kL, rL)
                    if wL == 0.0:
                        continue
                    for zz, wz in ((0, wZ0), (1, wZ1)):
                        if wz == 0.0:
                            continue
                        for rRp in range(0, (kR - zz) // 2 + 1):
                            wRp = P(R - 2, kR - zz, rRp)
                            if wRp == 0.0:
                                continue
                            singles = (kL + kR) - 2 * (rL + rRp)
                            c_next = +1 if zz == 1 else -1
                            nxt = _M(ell - 1, L // 2, R // 2, kL - rL, kR - rRp, c_next)
                            w = wL * wz * wRp
                            for m_sub, p_sub in nxt.items():
                                out[singles + m_sub] += w * p_sub
    else:
        denomL = comb_(L, kL)
        if denomL == 0:
            return {}
        if c == 0:
            denomR = comb_(R, kR)
            if denomR == 0:
                return {}
            for xL in (0, 1):
                w_xL = comb_(L - 1, kL - xL) / denomL if 0 <= kL - xL <= L - 1 else 0.0
                if w_xL == 0.0:
                    continue
                for xR in (0, 1):
                    w_xR = comb_(R - 1, kR - xR) / denomR if 0 <= kR - xR <= R - 1 else 0.0
                    if w_xR == 0.0:
                        continue
                    kL_in, kR_in = kL - xL, kR - xR
                    for rL in range(0, kL_in // 2 + 1):
                        wL = P(L - 1, kL_in, rL)
                        if wL == 0.0:
                            continue
                        for rR in range(0, kR_in // 2 + 1):
                            wR = P(R - 1, kR_in, rR)
                            if wR == 0.0:
                                continue
                            bm = xL * xR
                            singles = (kL + kR) - 2 * (rL + rR + bm)
                            kL_next = kL - xL - rL
                            kR_next = kR - xR - rR + (xL + xR - bm)
                            c_next = +1 if (xL + xR) >= 1 else -1
                            nxt = _M(ell - 1, (L - 1) // 2, (R - 1) // 2 + 1,
                                     kL_next, kR_next, c_next)
                            w = w_xL * w_xR * wL * wR
                            for m_sub, p_sub in nxt.items():
                                out[singles + m_sub] += w * p_sub
        elif c == +1:
            if R < 1 or kR < 1:
                return {}
            for xL in (0, 1):
                w_xL = comb_(L - 1, kL - xL) / denomL if 0 <= kL - xL <= L - 1 else 0.0
                if w_xL == 0.0:
                    continue
                kL_in, kR_in = kL - xL, kR - 1
                for rL in range(0, kL_in // 2 + 1):
                    wL = P(L - 1, kL_in, rL)
                    if wL == 0.0:
                        continue
                    for rR in range(0, kR_in // 2 + 1):
                        wR = P(R - 1, kR_in, rR)
                        if wR == 0.0:
                            continue
                        singles = (kL + kR) - 2 * (rL + rR + xL)
                        nxt = _M(ell - 1, (L - 1) // 2, (R - 1) // 2 + 1,
                                 kL - xL - rL, kR - rR, +1)
                        w = w_xL * wL * wR
                        for m_sub, p_sub in nxt.items():
                            out[singles + m_sub] += w * p_sub
        else:  # c == -1
            if R < 1:
                return {}
            for xL in (0, 1):
                w_xL = comb_(L - 1, kL - xL) / denomL if 0 <= kL - xL <= L - 1 else 0.0
                if w_xL == 0.0:
                    continue
                kL_in, kR_in = kL - xL, kR
                for rL in range(0, kL_in // 2 + 1):
                    wL = P(L - 1, kL_in, rL)
                    if wL == 0.0:
                        continue
                    for rR in range(0, kR_in // 2 + 1):
                        wR = P(R - 1, kR_in, rR)
                        if wR == 0.0:
                            continue
                        singles = (kL + kR) - 2 * (rL + rR)
                        c_next = +1 if xL == 1 else -1
                        nxt = _M(ell - 1, (L - 1) // 2, (R - 1) // 2 + 1,
                                 kL - xL - rL, kR - rR + xL, c_next)
                        w = w_xL * wL * wR
                        for m_sub, p_sub in nxt.items():
                            out[singles + m_sub] += w * p_sub
    return dict(out)


def pmf_leftfilled(t: int, k: int) -> Dict[int, float]:
    """PMF of the Octopus auth-set size for k distinct leaves of a left-filled
    tree with t leaves (Abri-Katz Theorem 3). octopus_pmf.py:261-307"""
    if not (1 <= k <= t):
        return {}
    h = (t - 1).bit_length()
    p = 1 << (h - 1) if h > 0 else 1
    L = t - p
    x = 2 * L
    pmf: Dict[int, float] = defaultdict(float)
    denom = _comb0(t, k)
    if denom == 0:
        return {}
    for j in range(0, min(k, x) + 1):
        wj = _comb0(x, j) * _comb0(t - x, k - j) / denom
        if wj == 0.0:
            continue
        for s in range(0, j // 2 + 1):
            ws = _P(x, j, s)
            if ws == 0.0:
                continue
            singles_bottom = j - 2 * s
            upper = _M(max(h - 1, 0), L if h > 0 else 0, (p - L) if h > 0 else 0,
                       j - s, k - j, 0)
            w = wj * ws
            for m_up, p_up in upper.items():
                pmf[singles_bottom + m_up] += w * p_up
    return dict(pmf)


def interleave_cost_table(t: int, k: int) -> List[Tuple[int, float]]:
    """[(m_max, log2 E[work])]: E[work] = 1/P(|S| <= m_max). octopus_pmf.py:312-328"""
    pmf = pmf_leftfilled(t, k)
    if not pmf:
        return []
    run, table = 0.0, []
    for m in range(max(pmf) + 1):
        run += pmf.get(m, 0.0)
        if run > 0:
            table.append((m, -math.log2(run)))
    return table


_interleave_table_cache: Dict[Tuple[int, int], Dict[int, float]] = {}


def log2_exp_work_from_mmax(t: int, k: int, mmax: int) -> float:
    """log2 expected PORS+FP grinding attempts for bound m_max. costs.sage:227-244"""
    key = (int(t), int(k))
    table = _interleave_table_cache.get(key)
    if table is None:
        table = dict(interleave_cost_table(*key))
        _interleave_table_cache[key] = table
    if mmax in table:
        return table[mmax]
    lowers = [m for m in table if m <= mmax]
    if not lowers:
        raise ValueError("mmax below supported range for these (t,k).")
    return table[max(lowers)]


def exp_work_from_mmax(t: int, k: int, mmax: int) -> float:
    """Expected PORS+FP attempts = 2^log2_exp_work. costs.sage:246-248"""
    return 2.0 ** log2_exp_work_from_mmax(t, k, mmax)


# =============================================================================
# Grinding tail  (costs.sage:254-289)
# =============================================================================

def _binom_cdf_lt(d: int, k: int, p: float) -> float:
    """P(X < d) for X ~ Bin(k, p); log-space, pure Python (d is small)."""
    if k < d:
        return 1.0
    lq = math.log1p(-p)
    lp = math.log(p)
    terms = [math.lgamma(k + 1) - math.lgamma(i + 1) - math.lgamma(k - i + 1)
             + i * lp + (k - i) * lq for i in range(d)]
    m = max(terms)
    return math.exp(m) * sum(math.exp(x - m) for x in terms)


try:  # the original uses scipy.stats.binom.cdf; prefer it for bit-identical results
    from scipy.stats import binom as _scipy_binom  # type: ignore
except Exception:  # pragma: no cover
    _scipy_binom = None


def worst_case(p, q, d: int, max_k: int = 10 ** 11) -> int:
    """Smallest k with P(fewer than d successes in k Bernoulli(p) trials) < q.

    costs.sage:254-289 (doubling + binary search over scipy binom.cdf).
    Used with q = 2^-30: the analytic "WC Search" of ePrint 2025/2203
    Tables 1-2. For d WOTS+C layers this is the negative-binomial quantile.
    Uses scipy when available (as the original), else a log-space fallback.
    """
    return _worst_case_cached(float(p), float(q), int(d), int(max_k), _scipy_binom is not None)


@lru_cache(maxsize=None)
def _worst_case_cached(p_f: float, q_f: float, d_i: int, max_k: int, use_scipy: bool) -> int:
    def tail_prob(k):
        if k < d_i:
            return 1.0
        if use_scipy:
            return float(_scipy_binom.cdf(d_i - 1, int(k), p_f))
        return _binom_cdf_lt(d_i, int(k), p_f)

    k_low, k_high = d_i - 1, max(d_i, 1)
    while tail_prob(k_high) >= q_f:
        k_high *= 2
        if k_high > max_k:
            raise RuntimeError("Could not find k below given max_k")
    while k_low + 1 < k_high:
        k_mid = (k_low + k_high) // 2
        if tail_prob(k_mid) < q_f:
            k_high = k_mid
        else:
            k_low = k_mid
    return k_high


def geometric_quantile(p: float, q: float) -> float:
    """Tries t with P(T > t) = q for a geometric grinder: ln(q)/ln(1-p).
    (Project plan Sec. 3.5 tail model; single-instance analogue of worst_case.)"""
    return math.log(q) / math.log1p(-p)


# =============================================================================
# Security  (security.sage:82-152)
# =============================================================================

def _logsumexp(xs):
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def compute_security(q_s: int, h: int, k: int, a: int, scheme_type: str,
                     hashbytes_: int = hashbytes) -> float:
    """Classical security bits of FORS / PORS+FP under q_s signatures.

    security.sage:102-152:
      sigma = sum_r Bin(q_s, 2^-h)[r] * P(forge | r)
        FORS:    P = (1 - (1 - 1/t)^r)^k,          t = 2^a
        PORS+FP: P = C(min(r*k, t), k) / C(t, k),  t = k*2^a
      bits = -log2(max(2^-8n, sigma))
    Port note: sage uses RealField(100); here everything is in natural-log
    space with float64 (lgamma/log1p/expm1), accurate to ~1e-9 bits, which
    only matters for tuples within ~1e-9 bits of the 128-bit threshold.
    Stop rule identical: r > q_s/2^h and contribution < 2^-1250.
    """
    leaves = 2 ** h
    lp = -h * math.log(2)
    l1p = math.log1p(-1.0 / leaves)
    if scheme_type == "FORS":
        t = 2 ** a
        l_miss = math.log1p(-1.0 / t)

        def log_forge(r):
            return k * math.log(-math.expm1(r * l_miss))
    else:
        t = k * 2 ** a
        log_ctk = math.log(comb(t, k))

        def log_forge(r):
            m = min(r * k, t)
            c = comb(m, k)
            return -math.inf if c == 0 else math.log(c) - log_ctk

    lq = math.lgamma(q_s + 1)
    terms = []
    r = 1
    stop = -1250 * math.log(2)
    while True:
        lhit = lq - math.lgamma(r + 1) - math.lgamma(q_s - r + 1) + r * lp + (q_s - r) * l1p
        contrib = lhit + log_forge(r)
        if contrib != -math.inf:
            terms.append(contrib)
        r += 1
        if r > q_s / leaves and contrib < stop:
            break
    log_sigma = _logsumexp(terms) if terms else -math.inf
    log_pre = -8 * hashbytes_ * math.log(2)
    return -max(log_pre, log_sigma) / math.log(2)


# =============================================================================
# Core computation  (costs.sage:295-546)
# =============================================================================

def compute_size(h: int, d: int, a: int, k: int, w: int, scheme: str, mmax: int = 0,
                 z: int = 0, randomness_size_: Optional[int] = None) -> int:
    """Signature size in bytes. costs.sage:295-328

    R + d*(h'*n + l*n + counter[W+C]) + FTS, with FTS =
      FORS:    k*n + k*a*n;  FORS+C: (k-1)*n + (k-1)*a*n;  PORS+FP: (k+mmax)*n
    z (GRINDSTONE extension) removes z WOTS+C chains per layer.
    randomness_size_: None -> repo HEAD value (16); paper tables use 32.
    """
    assert h % d == 0, "h must be divisible by d"
    R = randomness_size if randomness_size_ is None else randomness_size_
    has_wc = scheme != "SPX"
    l = compute_wots_l(scheme, w, z)
    hp = h // d
    hyper = d * (hp * hashbytes + l * hashbytes + counter_size * int(has_wc))
    if scheme == "W+C_P+FP":
        fts = (k + mmax) * hashbytes
    elif scheme == "W+C_F+C":
        fts = (k - 1) * hashbytes + (k - 1) * a * hashbytes
    else:
        fts = k * hashbytes + k * a * hashbytes
    return hyper + fts + R


def compute_mmax(h_prime: int, l: int, w: int, d_wots_expected_search: int, d: int,
                 k: int, a: int, convention: str = DEFAULT_CONVENTION) -> int:
    """PORS+FP m_max: smallest value (from (k-1)a - ceil(350/n), +1 per step,
    max 20 steps) whose expected signing compressions are < 1.11x FORS+C's.
    costs.sage:331-358"""
    Th2 = C_Th2(convention)
    Thl = compute_Th(l, convention)
    Thk1 = compute_Th(k - 1, convention)
    merkle = (2 ** h_prime * (l * C_PRF + l * (w - 1) * C_Th1 + Thl)) + (2 ** h_prime - 1) * Th2
    hyper = d * merkle + d_wots_expected_search * C_Th1c
    fors_c_fixed = (k - 1) * (2 ** a) * C_PRF + (k - 1) * (2 ** a) * C_Th1 \
        + (k - 1) * (2 ** a - 1) * Th2 + Thk1
    fors_c_total = fors_c_fixed + 2 ** a * (C_Hmsg + C_PRFmsg)
    spx_fc = hyper + fors_c_total
    t, sub, extra = compute_pors_tree_geometry(k, a)
    pors_fixed = t * C_PRF + t * C_Th1 + ((2 ** sub - 1) + extra) * Th2
    mmax = (k - 1) * a - ceil(350 / hashbytes)
    for i in range(20):
        attempts = ceil(exp_work_from_mmax(t, k, mmax))
        spx_pors = hyper + pors_fixed + attempts * (C_Hmsg + C_PRFmsg)
        if spx_pors / spx_fc < 1.11 or i == 19:
            return mmax
        mmax += 1
    return mmax


def compute_keygen_time(h: int, d: int, w: int, scheme: str, z: int = 0,
                        convention: str = DEFAULT_CONVENTION) -> int:
    """Keygen compressions (top XMSS tree). costs.sage:361-383"""
    assert h % d == 0
    hp = h // d
    l = compute_wots_l(scheme, w, z)
    return 2 ** hp * (l * C_PRF + l * (w - 1) * C_Th1 + compute_Th(l, convention)) \
        + (2 ** hp - 1) * C_Th2(convention)


def compute_signing_time(h: int, d: int, a: int, k: int, w: int, swn: int, scheme: str,
                         z: int = 0, mmax: Optional[int] = None,
                         convention: str = DEFAULT_CONVENTION,
                         q_worst: float = 2.0 ** -30) -> dict:
    """Signing cost (expected) in hash calls and compressions. costs.sage:386-488

    Returned keys follow the original ('hashes', 'compressions', 'exp_search',
    'worst_search', 'mmax'; exp/worst search in *hash calls*, FTS attempts
    counted as h_msg = 2 hash calls each, exactly as costs.sage) plus
    GRINDSTONE per-component fields:
      wots_c_tries_per_layer  exact 1/p (float, not ceil'd)
      wots_c_worst_tries      worst_case(p, q, d) over all d layers
      fts_tries               FORS+C: 2^a; PORS+FP: ceil(2^log2work) (as repo)
      fts_tries_exact         PORS+FP: 2^log2work unrounded
      fts_worst_tries         worst_case(1/fts_tries, q, 1)
    mmax: None -> derived with compute_mmax (repo rule); int -> override
    (GRINDSTONE extension, for enumerating the PORS+FP grinding knob).
    """
    assert h % d == 0
    has_wc = scheme != "SPX"
    hp = h // d
    l = compute_wots_l(scheme, w, z)
    Th2 = C_Th2(convention)
    Thl = compute_Th(l, convention)
    Thk = compute_Th(k, convention)
    out = {"wots_c_tries_per_layer": 0.0, "wots_c_worst_tries": 0,
           "fts_tries": 0, "fts_tries_exact": 0.0, "fts_worst_tries": 0}

    if has_wc:
        len1 = compute_wots_len1(w)
        p = wots_c_success_prob(w, len1, swn, z)
        d_wots_expected_search = d * ceil(1 / p)            # costs.sage:410
        d_wots_worst_search = worst_case(p, q_worst, d)      # costs.sage:411
        out["wots_c_tries_per_layer"] = float(1 / p)
        out["wots_c_worst_tries"] = d_wots_worst_search
    else:
        d_wots_expected_search = d_wots_worst_search = 0

    h_merkle = 2 ** hp * (l + l * (w - 1) + 1) + (2 ** hp - 1)
    c_merkle = 2 ** hp * (l * C_PRF + l * (w - 1) * C_Th1 + Thl) + (2 ** hp - 1) * Th2
    h_hyper = d * h_merkle + d_wots_expected_search
    c_hyper = d * c_merkle + d_wots_expected_search * C_Th1c
    h_msg = 2
    c_msg = C_Hmsg + C_PRFmsg

    if scheme == "W+C_F+C":
        Thk1 = compute_Th(k - 1, convention)
        h_fixed = (k - 1) * (2 ** a) * 2 + (k - 1) * (2 ** a - 1) + 1
        c_fixed = (k - 1) * (2 ** a) * C_PRF + (k - 1) * (2 ** a) * C_Th1 \
            + (k - 1) * (2 ** a - 1) * Th2 + Thk1
        tries = 2 ** a
        worst = worst_case(Fraction(1, 2 ** a), q_worst, 1)
        out.update(fts_tries=tries, fts_tries_exact=float(tries), fts_worst_tries=worst)
        out.update(hashes=h_hyper + h_fixed + tries * h_msg,
                   compressions=c_hyper + c_fixed + tries * c_msg,
                   exp_search=d_wots_expected_search + tries * h_msg,
                   worst_search=d_wots_worst_search + worst * h_msg, mmax=0)
        return out
    if scheme == "W+C_P+FP":
        t, sub, extra = compute_pors_tree_geometry(k, a)
        h_fixed = 2 * t + (2 ** sub - 1) + extra
        c_fixed = t * C_PRF + t * C_Th1 + ((2 ** sub - 1) + extra) * Th2
        if mmax is None:
            mmax = compute_mmax(hp, l, w, d_wots_expected_search, d, k, a, convention)
        exact = exp_work_from_mmax(t, k, mmax)
        tries = ceil(exact)
        worst = worst_case(1.0 / tries, q_worst, 1)
        out.update(fts_tries=tries, fts_tries_exact=exact, fts_worst_tries=worst)
        out.update(hashes=h_hyper + h_fixed + tries * h_msg,
                   compressions=c_hyper + c_fixed + tries * c_msg,
                   exp_search=d_wots_expected_search + tries * h_msg,
                   worst_search=d_wots_worst_search + worst * h_msg, mmax=mmax)
        return out
    h_fixed = k * (2 ** a) * 2 + k * (2 ** a - 1) + 1
    c_fixed = k * (2 ** a) * C_PRF + k * (2 ** a) * C_Th1 + k * (2 ** a - 1) * Th2 + Thk
    out.update(hashes=h_fixed + h_msg + h_hyper, compressions=c_fixed + c_msg + c_hyper,
               exp_search=d_wots_expected_search, worst_search=d_wots_worst_search, mmax=0)
    return out


def compute_verification_time(h: int, d: int, a: int, k: int, w: int, swn: int, scheme: str,
                              mmax: int = 0, z: int = 0,
                              convention: str = DEFAULT_CONVENTION) -> dict:
    """Verification cost. costs.sage:490-546
    WOTS+C per layer: ((w-1)*l - S) chain steps + Th1c + Thl (deterministic).
    """
    has_wc = scheme != "SPX"
    l = compute_wots_l(scheme, w, z)
    Th2 = C_Th2(convention)
    Thl = compute_Th(l, convention)
    Thk = compute_Th(k, convention)
    if has_wc:
        h_wots = (w - 1) * l - swn + 2
        c_wots = ((w - 1) * l - swn) * C_Th1 + C_Th1c + Thl
        c_wots_worst = c_wots
    else:
        h_wots = (w - 1) * l // 2 + 1
        c_wots = (w - 1) * l // 2 * C_Th1 + Thl
        l1 = compute_wots_len1(w)
        c_wots_worst = compute_wots_tw_worst_steps(l1, _wots_len2(l1, w), w) * C_Th1 + Thl
    if scheme == "W+C_F+C":
        h_fts = (k - 1) + (k - 1) * a + 1
        c_fts = (k - 1) * C_Th1 + (k - 1) * a * Th2 + compute_Th(k - 1, convention)
    elif scheme == "W+C_P+FP":
        h_fts = k + mmax
        c_fts = k * C_Th1 + mmax * Th2
    else:
        h_fts = k + k * a + 1
        c_fts = k * C_Th1 + k * a * Th2 + Thk
    return {
        "hashes": 1 + h_fts + d * h_wots + h,
        "compressions": C_Hmsg + c_fts + d * c_wots + h * Th2,
        "compressions_worst": C_Hmsg + c_fts + d * c_wots_worst + h * Th2,
    }


def compute_single(scheme: str, q_s_log2: int, h: int, d: int, a: int, k: int, w: int,
                   swn: int, z: int = 0, mmax: Optional[int] = None,
                   convention: str = DEFAULT_CONVENTION,
                   randomness_size_: Optional[int] = None,
                   with_security: bool = True) -> dict:
    """All metrics for one tuple (cf. costs.sage:552-594 compute_all_results and
    687-712 compute_single)."""
    sign = compute_signing_time(h, d, a, k, w, swn, scheme, z=z, mmax=mmax,
                                convention=convention)
    m = sign["mmax"]
    ver = compute_verification_time(h, d, a, k, w, swn, scheme, m, z=z, convention=convention)
    size = compute_size(h, d, a, k, w, scheme, m, z=z, randomness_size_=randomness_size_)
    res = {
        "scheme": scheme, "q_s": q_s_log2, "h": h, "d": d, "a": a, "k": k, "w": w,
        "l": compute_wots_l(scheme, w, z), "z": z, "swn": swn, "mmax": m, "size": size,
        "keygen_compressions": compute_keygen_time(h, d, w, scheme, z, convention),
        "sign_hashes": sign["hashes"], "sign_compressions": sign["compressions"],
        "exp_search": sign["exp_search"], "worst_search": sign["worst_search"],
        "verify_hashes": ver["hashes"], "verify_compressions": ver["compressions"],
        "verify_compressions_worst": ver["compressions_worst"],
        "wots_c_tries_per_layer": sign["wots_c_tries_per_layer"],
        "wots_c_worst_tries": sign["wots_c_worst_tries"],
        "fts_tries": sign["fts_tries"], "fts_tries_exact": sign["fts_tries_exact"],
        "fts_worst_tries": sign["fts_worst_tries"],
    }
    if with_security:
        st = "PORS+FP" if scheme == "W+C_P+FP" else "FORS"
        res["security"] = compute_security(2 ** q_s_log2, h, k, a, st)
    return res


if __name__ == "__main__":  # pragma: no cover
    import sys
    conv = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONVENTION
    R = PAPER_RANDOMNESS_SIZE if conv == "uncached" else None
    for s, q, h, d, a, k, w, _l, swn, bold in PARAMETER_SETS:
        r = compute_single(s, q, h, d, a, k, w, swn, convention=conv, randomness_size_=R)
        print(f"{s:9s} 2^{q} {h:3d} {d:2d} {a:3d} {k:3d} {w:4d} {swn:5d} size={r['size']:5d} "
              f"mmax={r['mmax']:3d} sign_h={r['sign_hashes']:>10} exp={r['exp_search']:>8} "
              f"worst={r['worst_search']:>9} ver_h={r['verify_hashes']:6d} "
              f"ver_c={r['verify_compressions']:6d} sec={r['security']:.1f}{' *' if bold else ''}")
