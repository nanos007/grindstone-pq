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


def success_prob(p: WotsParams):
    """ν / w^len1 · 2^-z_bits, ν = Σ_j (−1)^j C(len1, j) C(S + len1 − j·w − 1, len1 − 1)."""
    nu = 0
    for j in range(p.len1 + 1):
        top = p.S + p.len1 - j * p.w - 1
        if top < p.len1 - 1:
            break
        nu += (-1) ** j * comb(p.len1, j) * comb(top, p.len1 - 1)
    return Fraction(nu, p.w ** p.len1) / (1 << p.z_bits)


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
