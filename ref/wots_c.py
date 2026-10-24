"""WOTS+C grinding reference (Kudinov–Nick §5): d = Th(P, T*_adrs, m ‖ count).

Byte layout is a `WotsLayout`, so the open ambiguities (doc §3.5, items 2–3) are settled in
one place. The grind returns the smallest accepted counter, i.e. tries = counter + 1.
"""
import struct
from dataclasses import dataclass
from fractions import Fraction
from math import comb

from . import sha2


@dataclass(frozen=True)
class WotsLayout:
    ctr_bytes: int = 4
    ctr_le: bool = False      # FIPS 205 toByte is big-endian
    ctr_in_adrs: bool = False  # original SPHINCS+C variant: counter inside ADRS, not after m
    shrincs: bool = False      # SHRINCS H_grind: ADRS[:10] ‖ digest(32) ‖ 0^4 ‖ ctr (2 B, BE)


SHRINCS = WotsLayout(ctr_bytes=2, shrincs=True)


@dataclass(frozen=True)
class WotsParams:
    w: int
    len1: int
    S: int
    z_bits: int = 0   # trailing bits of d that must be zero

    @property
    def logw(self):
        return self.w.bit_length() - 1


def _nu(w, l, S):
    """Number of l-digit base-w vectors summing to S: Σ_j (−1)^j C(l, j) C(S + l − j·w − 1, l − 1)."""
    nu = 0
    for j in range(l + 1):
        top = S + l - j * w - 1
        if top < l - 1:
            break
        nu += (-1) ** j * comb(l, j) * comb(top, l - 1)
    return nu


def success_prob(p: WotsParams):
    """ν(len1 − z, S) / w^len1 · 2^-min(z_bits, unused).

    The trailing z_bits first cover the unused bits of d past the len1 digits (z_b, independent of the
    sum), then whole trailing digits (z zero chains, which leave len1 − z digits to sum to S).
    """
    unused = 8 * sha2.N - p.len1 * p.logw
    inside = max(0, p.z_bits - unused)
    if inside % p.logw:
        raise ValueError("z_bits must end on a digit boundary")
    z = inside // p.logw
    return Fraction(_nu(p.w, p.len1 - z, p.S), p.w ** p.len1) / (1 << min(p.z_bits, unused))


def digits(d, logw, count):
    """FIPS 205 base_2b: MSB-first digits of logw bits."""
    x = int.from_bytes(d, "big")
    total = len(d) * 8
    return [(x >> (total - (i + 1) * logw)) & ((1 << logw) - 1) for i in range(count)]


def accept(d, p: WotsParams):
    if p.z_bits and int.from_bytes(d, "big") & ((1 << p.z_bits) - 1):
        return False
    return sum(digits(d, p.logw, p.len1)) == p.S


def tail(adrs_c, m, count, lay: WotsLayout):
    c = count.to_bytes(lay.ctr_bytes, "little" if lay.ctr_le else "big")
    if lay.shrincs:
        assert len(adrs_c) == 10 and len(m) == 32
        return adrs_c + m + b"\x00" * 4 + c
    if lay.ctr_in_adrs:
        # counter overwrites the last ctr_bytes of ADRS_c
        return adrs_c[:-lay.ctr_bytes] + c + m
    return adrs_c + m + c


def ctr_offset(adrs_c, m, lay: WotsLayout):
    if lay.shrincs:
        return len(adrs_c) + len(m) + 4
    return len(adrs_c) - lay.ctr_bytes if lay.ctr_in_adrs else len(adrs_c) + len(m)


def grind(seed_state, adrs_c, m, p: WotsParams, lay=WotsLayout(), max_tries=1 << 32, ctr=sha2.NULL):
    max_tries = min(max_tries, 1 << (8 * lay.ctr_bytes))
    for count in range(max_tries):
        d = sha2.th(seed_state, tail(adrs_c, m, count, lay), b"", ctr)
        if accept(d, p):
            return count
    return None


def final_block_template(adrs_c, m, lay: WotsLayout):
    """16 big-endian words of the last block (counter bytes zero) + counter offset, for the GPU.

    Requires the whole tail to fit one block after the 64-byte seed block (≤ 55 bytes)."""
    t = tail(adrs_c, m, 0, lay)
    assert len(t) <= 55, "tail must fit a single block"
    total = 64 + len(t)
    blk = t + b"\x80" + b"\x00" * (55 - len(t)) + struct.pack(">Q", total * 8)
    return list(struct.unpack(">16I", blk)), ctr_offset(adrs_c, m, lay)


def zmask_words(p: WotsParams, n=sha2.N):
    """Mask over d's 4 big-endian words selecting the trailing z_bits."""
    x = (1 << p.z_bits) - 1
    return [(x >> (32 * (3 - i))) & 0xFFFFFFFF for i in range(n // 4)]
