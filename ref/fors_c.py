"""FORS+C and PORS+FP grinding references (kb/raw/A/pseudocode.md §2–§4).

Uses hashlib/hmac for speed; `count_compressions` replays one attempt through ref.sha2 to
report the per-attempt compression count (doc §3.5 ambiguity 4).
"""
import hashlib
import hmac
from math import ceil

from . import sha2


def _sha(x):
    return hashlib.sha256(x).digest()


def h_msg(r, pk_seed, pk_root, m, out_len):
    inner = _sha(r + pk_seed + pk_root + m)
    out = b""
    j = 0
    while len(out) < out_len:
        out += _sha(r + pk_seed + inner + j.to_bytes(4, "big"))
        j += 1
    return out[:out_len]


def digest_len(k, a, h, d):
    """FIPS 205 m = ⌈k·a/8⌉ + ⌈(h − h′)/8⌉ + ⌈h′/8⌉."""
    hp = h // d
    return ceil(k * a / 8) + ceil((h - hp) / 8) + ceil(hp / 8)


def zero_bits_ok(digest, k, a):
    """Last a-bit index of md is 0: bits [(k−1)a, ka) MSB-first are all zero."""
    x = int.from_bytes(digest[: ceil(k * a / 8)], "big")
    total = ceil(k * a / 8) * 8
    return (x >> (total - k * a)) & ((1 << a) - 1) == 0


def zero_mask_words(k, a, nwords=8):
    """Big-endian word mask over the digest selecting bits [(k−1)a, ka)."""
    mask = ((1 << a) - 1) << (nwords * 32 - k * a)
    return [(mask >> (32 * (nwords - 1 - i))) & 0xFFFFFFFF for i in range(nwords)]


def prf_r(sk_prf, pk_seed, m, i):
    """R_i = HMAC-SHA-256(SK.prf, opt_rand=PK.seed ‖ M ‖ toByte(i,4))[:16]."""
    return hmac.new(sk_prf, pk_seed + m + i.to_bytes(4, "big"), hashlib.sha256).digest()[:16]


def grind_R(sk_prf, pk_seed, pk_root, m, k, a, h, d, max_tries=1 << 32):
    """KN layout: fresh R per attempt via PRF_msg. Returns winning i (tries = i + 1)."""
    ml = digest_len(k, a, h, d)
    for i in range(max_tries):
        r = prf_r(sk_prf, pk_seed, m, i)
        if zero_bits_ok(h_msg(r, pk_seed, pk_root, m, ml), k, a):
            return i
    return None


def grind_ctr(sk_prf, pk_seed, pk_root, m, k, a, h, d, max_tries=1 << 32):
    """Original SPHINCS+C layout: R fixed, 4-byte counter appended to M in the inner hash."""
    ml = digest_len(k, a, h, d)
    r = hmac.new(sk_prf, pk_seed + m, hashlib.sha256).digest()[:16]
    for c in range(max_tries):
        inner = _sha(r + pk_seed + pk_root + m + c.to_bytes(4, "big"))
        dg = _sha(r + pk_seed + inner + b"\x00\x00\x00\x00")[:ml]
        if zero_bits_ok(dg, k, a):
            return c
    return None


# ---------------------------------------------------------------- PORS+FP

def octopus_size(xs, t):
    """Authentication-set size for leaves xs in a left-filled tree of t leaves (pseudocode §4)."""
    hgt = (t - 1).bit_length()
    s = t - (1 << (hgt - 1))
    I = sorted(i for i in xs if i < 2 * s)
    P = sorted(i - s for i in xs if i >= 2 * s)
    auth = 0
    for lvl in range(hgt):
        nxt = []
        j = 0
        while j < len(I):
            x = I[j]
            if j + 1 < len(I) and I[j + 1] == x ^ 1:
                j += 2
            else:
                auth += 1
                j += 1
            if not nxt or nxt[-1] != x >> 1:
                nxt.append(x >> 1)
        I = sorted(nxt + P) if lvl == 0 else nxt
    return auth


def hash_to_subset(y, t, k, h):
    """KN Algorithm 1: first h bits are τ, then ν blocks of b bits; keep distinct values < t."""
    b = (t - 1).bit_length()
    nbits = 8 * len(y)
    x = int.from_bytes(y, "big")
    nu = (nbits - h) // b
    out = []
    for i in range(nu):
        v = (x >> (nbits - h - (i + 1) * b)) & ((1 << b) - 1)
        if v < t and v not in out and len(out) < k:
            out.append(v)
    return sorted(out) if len(out) == k else None


def p_enough(t, k, h, out_bits=512):
    """P(an attempt yields k distinct values < t), i.e. hash_to_subset does not return None.

    Markov chain over the number of distinct values collected so far (KN §13.3 assumes 1)."""
    b = (t - 1).bit_length()
    nu = (out_bits - h) // b
    dist = [0.0] * (k + 1)
    dist[0] = 1.0
    for _ in range(nu):
        nxt = [0.0] * (k + 1)
        nxt[k] = dist[k]
        for j in range(k):
            q = (t - j) / (1 << b)
            nxt[j + 1] += dist[j] * q
            nxt[j] += dist[j] * (1 - q)
        dist = nxt
    return dist[k]


def pors_accept(y, t, k, h, m_max):
    xs = hash_to_subset(y, t, k, h)
    return xs is not None and octopus_size(xs, t) <= m_max


def grind_pors(sk_prf, pk_seed, pk_root, m, k, a, h, m_max, max_tries=1 << 32):
    t = k << a
    for i in range(max_tries):
        r = prf_r(sk_prf, pk_seed, m, i)
        if pors_accept(h_msg(r, pk_seed, pk_root, m, 64), t, k, h, m_max):
            return i
    return None


# ---------------------------------------------------------------- compression accounting

def count_compressions(layout, msg_len=32, pors=False):
    """Compressions per attempt through ref.sha2, excluding per-key/per-message midstates."""
    c = sha2.Counter()
    key = sha2.HmacKey(b"\x01" * 16)
    seed, root, m = b"\x02" * 16, b"\x03" * 16, b"\x04" * msg_len
    if layout == "R":
        r = key.mac(seed + m + b"\x00" * 4, c)[:16]
        inner = sha2.sha256(r + seed + root + m, c)
        blocks = 2 if pors else 1
        first = sha2.midstate(r + seed + inner[:32], c)  # shared first MGF1 block
        for j in range(blocks):
            sha2.finish(first, j.to_bytes(4, "big"), 64, c)
    elif layout == "ctr":
        r = b"\x05" * 16
        pre = r + seed + root + m[:16]
        mid = sha2.midstate(pre)                          # once per message: not charged
        inner = sha2.finish(mid, m[16:] + b"\x00" * 4, 64, c)
        first = sha2.midstate(r + seed + inner, c)
        sha2.finish(first, b"\x00" * 4, 64, c)
    return c.n
