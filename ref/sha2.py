"""SHA-256 with explicit midstate, and the FIPS 205 SHA-2 primitives (n = 16).

Slow and obviously correct. Every compression goes through `compress`, so callers
can count compressions per grind attempt (doc §3.5 ambiguity 4).
"""
import hashlib
import hmac
import struct

N = 16  # NIST L1

_K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]
IV = (0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19)


class Counter:
    """Counts compression-function calls."""

    def __init__(self):
        self.n = 0


NULL = Counter()


def _rotr(x, r):
    return ((x >> r) | (x << (32 - r))) & 0xFFFFFFFF


def compress(state, block, ctr=NULL):
    """One SHA-256 compression of a 64-byte block into an 8-word state."""
    assert len(block) == 64
    ctr.n += 1
    w = list(struct.unpack(">16I", block))
    for i in range(16, 64):
        s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w.append((w[i - 16] + s0 + w[i - 7] + s1) & 0xFFFFFFFF)
    a, b, c, d, e, f, g, h = state
    for i in range(64):
        S1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
        ch = (e & f) ^ (~e & g)
        t1 = (h + S1 + ch + _K[i] + w[i]) & 0xFFFFFFFF
        S0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (S0 + maj) & 0xFFFFFFFF
        h, g, f, e, d, c, b, a = g, f, e, (d + t1) & 0xFFFFFFFF, c, b, a, (t1 + t2) & 0xFFFFFFFF
    return tuple((x + y) & 0xFFFFFFFF for x, y in zip(state, (a, b, c, d, e, f, g, h)))


def midstate(prefix, ctr=NULL):
    """State after absorbing a prefix whose length is a multiple of 64 bytes."""
    assert len(prefix) % 64 == 0
    st = IV
    for i in range(0, len(prefix), 64):
        st = compress(st, prefix[i:i + 64], ctr)
    return st


def finish(state, tail, prefix_len, ctr=NULL):
    """Absorb `tail` (+ SHA-256 padding) after `prefix_len` bytes already in `state`."""
    total = prefix_len + len(tail)
    padded = tail + b"\x80" + b"\x00" * ((55 - total) % 64) + struct.pack(">Q", total * 8)
    for i in range(0, len(padded), 64):
        state = compress(state, padded[i:i + 64], ctr)
    return struct.pack(">8I", *state)


def sha256(data, ctr=NULL):
    full = len(data) - len(data) % 64
    return finish(midstate(data[:full], ctr), data[full:], full, ctr)


def n_compressions(msg_len):
    """Number of compressions SHA-256 needs for a message of msg_len bytes."""
    return (msg_len + 9 + 63) // 64


# ---------------------------------------------------------------- FIPS 205 §11.2.1 (SHA-2, n = 16)

def pad_seed(pk_seed):
    """PK.seed ‖ toByte(0, 64 − n): the block whose midstate every Th/F/H/T_l call shares."""
    return pk_seed + b"\x00" * (64 - len(pk_seed))


def seed_midstate(pk_seed, ctr=NULL):
    return midstate(pad_seed(pk_seed), ctr)


def th(seed_state, adrs_c, msg, ctr=NULL):
    """Tweakable hash Trunc_n(SHA-256(PK.seed ‖ pad ‖ ADRS_c ‖ M)) from a cached seed midstate."""
    return finish(seed_state, adrs_c + msg, 64, ctr)[:N]


def mgf1_sha256(seed, length, ctr=NULL):
    out = b""
    i = 0
    while len(out) < length:
        out += sha256(seed + struct.pack(">I", i), ctr)
        i += 1
    return out[:length]


def h_msg(r, pk_seed, pk_root, m, out_len, ctr=NULL):
    """H_msg = MGF1-SHA-256(R ‖ PK.seed ‖ SHA-256(R ‖ PK.seed ‖ PK.root ‖ M), m)."""
    inner = sha256(r + pk_seed + pk_root + m, ctr)
    return mgf1_sha256(r + pk_seed + inner, out_len, ctr)


def prf_msg(sk_prf, opt_rand, m, ctr=NULL):
    """PRF_msg = Trunc_n(HMAC-SHA-256(SK.prf, opt_rand ‖ M)), counting compressions."""
    key = sk_prf + b"\x00" * (64 - len(sk_prf))
    ipad = bytes(k ^ 0x36 for k in key)
    opad = bytes(k ^ 0x5C for k in key)
    inner = sha256(ipad + opt_rand + m, ctr)
    return sha256(opad + inner, ctr)[:N]


class HmacKey:
    """HMAC-SHA-256 with precomputed ipad/opad midstates (the GPU layout)."""

    def __init__(self, key):
        key = key + b"\x00" * (64 - len(key))
        self.istate = midstate(bytes(k ^ 0x36 for k in key))
        self.ostate = midstate(bytes(k ^ 0x5C for k in key))

    def mac(self, data, ctr=NULL):
        inner = finish(self.istate, data, 64, ctr)
        return finish(self.ostate, inner, 64, ctr)


def _selftest():
    import os
    for ln in (0, 1, 55, 56, 63, 64, 65, 119, 120, 200):
        d = os.urandom(ln)
        assert sha256(d) == hashlib.sha256(d).digest(), ln
    k, d = os.urandom(16), os.urandom(48)
    want = hmac.new(k, d, hashlib.sha256).digest()
    assert prf_msg(k, d[:16], d[16:]) == want[:N]
    assert HmacKey(k).mac(d) == want


if __name__ == "__main__":
    _selftest()
    print("ok")
