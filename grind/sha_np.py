"""Vectorised SHA-256 compression over N rows (numpy), for building per-instance midstates."""
import numpy as np

from ref.sha2 import IV, _K

K = np.array(_K, dtype=np.uint32)


def _rotr(x, r):
    return (x >> np.uint32(r)) | (x << np.uint32(32 - r))


def compress(state, block):
    """state: (N, 8) uint32, block: (N, 16) uint32 big-endian words. Returns new (N, 8)."""
    w = [block[:, i].astype(np.uint32) for i in range(16)]
    for i in range(16, 64):
        s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> np.uint32(3))
        s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> np.uint32(10))
        w.append(w[i - 16] + s0 + w[i - 7] + s1)
    a, b, c, d, e, f, g, h = (state[:, i].astype(np.uint32) for i in range(8))
    for i in range(64):
        t1 = h + (_rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i]
        t2 = (_rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))
        h, g, f, e, d, c, b, a = g, f, e, d + t1, c, b, a, t1 + t2
    return state + np.stack([a, b, c, d, e, f, g, h], axis=1)


def iv(n):
    return np.tile(np.array(IV, dtype=np.uint32), (n, 1))


def be_words(buf, n, words):
    """(n, words) uint32 from n·4·words bytes."""
    return np.frombuffer(buf, dtype=">u4").reshape(n, words).astype(np.uint32)
