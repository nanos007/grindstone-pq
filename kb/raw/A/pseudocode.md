# Agent A — Byte-exact grind pseudocode (GRINDSTONE v1)

Scope: n = 16, NIST L1, SHA-256 only. Python-style pseudocode with byte strings. `‖` = concatenation.
Decisions and sources: see `ambiguities.md`. Items marked **[OUR CHOICE]** are GRINDSTONE definitions, not author-specified bytes. Status: draft, not yet executed. Phase 4 `ref/` must implement this and freeze test vectors.

## Common primitives

```python
def toByte(x, L):            # FIPS 205 Alg. 3: big-endian, fixed width
    return x.to_bytes(L, 'big')

def base_2b(X, b, out_len):  # FIPS 205 Alg. 4: MSB-first ("big-endian bit order")
    i = bits = total = 0; out = []
    for _ in range(out_len):
        while bits < b:
            total = (total << 8) | X[i]; i += 1; bits += 8
        bits -= b
        out.append((total >> bits) & ((1 << b) - 1))
    return out

def bit(X, j):               # bit j of byte string X, j = 0 is the MSB of X[0]
    return (X[j >> 3] >> (7 - (j & 7))) & 1

def sha256(x): ...           # FIPS 180-4
def hmac_sha256(K, x): ...   # FIPS 198-1; K is 16 bytes, zero-padded to 64
def mgf1_sha256(seed, L):    # RFC 8017 B.2.1
    return (sha256(seed + toByte(0,4)) + sha256(seed + toByte(1,4)) + ...)[:L]

# FIPS 205 §11.2.1 (SHA2, category 1)
def H_msg(R, PKseed, PKroot, M, m):
    return mgf1_sha256(R + PKseed + sha256(R + PKseed + PKroot + M), m)
def PRF_msg(SKprf, opt_rand, M):
    return hmac_sha256(SKprf, opt_rand + M)[:16]
def Th(PKseed, ADRSc, Mx):   # F / H / T_l: PK.seed padded to one 64-B block (midstate)
    return sha256(PKseed + toByte(0, 48) + ADRSc + Mx)[:16]
```

Compression accounting rule: a SHA-256 message of L bytes uses ⌈(L+9)/64⌉ compressions. Blocks that are identical across attempts are computed once (a midstate) and not charged per attempt.

## §0 Per-parameter derived constants (REPO@ceee8ed rows with F+C / P+FP)

m = ⌈k·a/8⌉ + ⌈(h−h′)/8⌉ + ⌈h′/8⌉ (FIPS 205 §9). FORS+C zero bits = [(k−1)a, ka), MSB-first from `digest[0]`.

| q_s | h | d | a | k | m (B) | ⌈ka/8⌉ | zero bits | byte masks that must be 0 |
|---|---|---|---|---|---|---|---|---|
| 2^40 | 44 | 4 | 16 | 8 | 23 | 16 | [112,128) | d[14]&0xFF d[15]&0xFF |
| 2^40 | 40 | 5 | 14 | 11 | 25 | 20 | [140,154) | d[17]&0x0F d[18]&0xFF d[19]&0xC0 |
| 2^30 | 36 | 3 | 14 | 9 | 21 | 16 | [112,126) | d[14]&0xFF d[15]&0xFC |
| 2^30 | 33 | 3 | 15 | 9 | 22 | 17 | [120,135) | d[15]&0xFF d[16]&0xFE |
| 2^30 | 32 | 4 | 14 | 10 | 22 | 18 | [126,140) | d[15]&0x03 d[16]&0xFF d[17]&0xF0 |
| 2^20 | 24 | 2 | 16 | 8 | 20 | 16 | [112,128) | d[14]&0xFF d[15]&0xFF |
| 2^20 | 20 | 2 | 15 | 10 | 23 | 19 | [135,150) | d[16]&0x01 d[17]&0xFF d[18]&0xFC |

All m ≤ 32, so one MGF1 output block suffices for FORS+C. The GPU only needs `digest[0:⌈ka/8⌉]`.

PORS+FP rows (t = k·2^a, b = ⌈log2 t⌉, H_msg output 512 bits, ν = ⌊(512−h)/b⌋; P_enough = P(≥ k distinct values < t among ν iid b-bit blocks), our DP, not verified by a second implementation):

| q_s | h | d | a | k | t | b | s = t − 2^(b−1) | ν | P_enough |
|---|---|---|---|---|---|---|---|---|---|
| 2^40 | 44 | 4 | 16 | 8 | 524288 | 19 | 262144 | 24 | 1.000000 |
| 2^40 | 40 | 5 | 14 | 11 | 180224 | 18 | 49152 | 26 | 0.998608 |
| 2^30 | 36 | 3 | 14 | 9 | 147456 | 18 | 16384 | 26 | 0.992219 |
| 2^30 | 33 | 3 | 15 | 9 | 294912 | 19 | 32768 | 25 | 0.987414 |
| 2^30 | 32 | 4 | 14 | 10 | 163840 | 18 | 32768 | 26 | 0.996361 |
| 2^20 | 24 | 2 | 16 | 8 | 524288 | 19 | 262144 | 25 | 1.000000 |
| 2^20 | 20 | 2 | 15 | 10 | 327680 | 19 | 65536 | 25 | 0.993520 |

(With 256 bits P_enough would be only 0.07–0.15 for non-power-of-two t; with 768 bits it is ≥ 0.99999.)

---

## §1 WOTS+C grind (per hypertree layer)

```python
# Inputs: PKseed(16), layer(int), tree(int, < 2^64), leaf(int, < 2^32: keypair index in XMSS tree),
#         m(16) = value being signed (subtree root, or FORS/PORS pk at layer 0), lg_w in {4,8}, S
WOTSC_GRIND = 7                                     # [OUR CHOICE] = SPHINCS+C ref type value
len1 = 128 // lg_w                                  # 32 (w=16) or 16 (w=256); z = z_b = 0
ADRSc = toByte(layer,1) + toByte(tree,8) + toByte(WOTSC_GRIND,1) \
        + toByte(leaf,4) + toByte(0,8)              # 22 bytes
mid = sha256_compress(IV, PKseed + toByte(0,48))    # computed once per key

def wots_c_grind(mid, ADRSc, m, lg_w, S, cmax=2**32):
    for count in range(cmax):                       # lowest valid count wins
        blk = ADRSc + m + toByte(count,4)           # 42 bytes
        blk += b'\x80' + toByte(0,13) + toByte((64+42)*8, 8)   # len = 848 bits = 0x350
        d = sha256_compress(mid, blk)[:16]          # 1 compression / attempt
        a = base_2b(d, lg_w, len1)
        if sum(a) == S:                             # (z = 0: no zero-chain test)
            return count, a, count + 1              # tries = count + 1
    return FAIL
# Signature carries toByte(count,4). Verifier recomputes d and checks sum(a) == S.
```
p = ν/w^len1 (KN eq. 1). E[tries] = 65.7 / 1335.3 / 748.0 / 30143.4 for (w,S) = (16,240) / (16,304) / (256,2040) / (256,2840) (our recomputation, matches plan §3.5).
GPU note: W0–W8 of block 2 are fixed per instance. count occupies bytes 38–41 (W9 low half, W10 high half).

## §2 FORS+C R-grind (KN's chosen layout; counter not transmitted)

```python
# Inputs: SKprf(16), PKseed(16), PKroot(16), M(32 sighash), a, k, h, d; opt_rand = PKseed
def fors_c_R_grind(SKprf, PKseed, PKroot, M, a, k, h, d, imax=2**32):
    m = ceil(k*a/8) + ceil((h - h//d)/8) + ceil((h//d)/8)
    for i in range(imax):
        R = hmac_sha256(SKprf, PKseed + M + toByte(i,4))[:16]   # [OUR CHOICE] ctr after M, BE
        digest = H_msg(R, PKseed, PKroot, M, m)
        if all(bit(digest, j) == 0 for j in range((k-1)*a, k*a)):
            return R, digest, i + 1                 # R goes in the signature; i is discarded
    return FAIL
```
Compressions per attempt: HMAC inner 1 + outer 1 (ipad/opad midstates of SK.prf cached), H_msg inner 2 (80 B) + MGF1 block 2 (68 B) = **6**. Without HMAC midstates: 8. REPO model: 4.
Equivalent acceptance via FIPS 205: `base_2b(digest[:ceil(k*a/8)], a, k)[k-1] == 0`.
Downstream (not part of grind): md = digest[0:⌈ka/8⌉], idx_tree / idx_leaf per FIPS 205 Alg. 19 l.7–10, fors_sign over trees 0..k−2 only.

## §3 FORS+C ctr-grind (original SPHINCS+C layout; counter transmitted)

```python
def fors_c_ctr_grind(SKprf, PKseed, PKroot, M, a, k, h, d, cmax=2**32):
    m = ceil(k*a/8) + ceil((h - h//d)/8) + ceil((h//d)/8)
    R = PRF_msg(SKprf, PKseed, M)                   # unmodified FIPS 205, once
    pre = R + PKseed + PKroot + M[:16]              # exactly 64 bytes -> inner midstate, once
    for c in range(cmax):                           # [OUR CHOICE] start at 0 (SPXC code starts at 1)
        inner = sha256(R + PKseed + PKroot + M + toByte(c,4))  # 84 B; per attempt only block 2:
                                                    # M[16:32] ‖ c(4) ‖ 0x80 ‖ 0^...‖ len=672 bits
        digest = mgf1_sha256(R + PKseed + inner, m) # 68 B -> 2 compressions
        if all(bit(digest, j) == 0 for j in range((k-1)*a, k*a)):
            return R, c, digest, c + 1
    return FAIL
# Signature: R(16) ‖ toByte(c,4) ‖ FORS+C sig ‖ HT sig   (c placed right after R as in SPXC code)
```
Compressions per attempt: **3** (inner block 2 + outer 2). +4 B signature size versus §2.
Exploratory variant **[OUR CHOICE, not in any source, needs Red Team review]**: `digest = mgf1_sha256(R + PKseed + inner0 + toByte(c,4), m)`, with `inner0 = sha256(R‖PKseed‖PKroot‖M)` computed once. The first 64 B are fixed, so each attempt costs **1** compression. Report only as a layout-engineering bound.

## §4 PORS+FP R-grind + acceptance

```python
# Inputs as §2 plus t = k * 2**a, m_max (from REPO compute_mmax via Agent B)
def octopus_size(X, t):                    # X: k distinct leaf indices in [0, t)
    hgt = (t - 1).bit_length()             # ceil(log2 t)
    s = t - (1 << (hgt - 1))               # left-filled tree: leaves < 2s at depth hgt,
    I = sorted(i for i in X if i < 2*s)    #   leaves >= 2s sit at level 1 as node (i - s)
    P = sorted(i - s for i in X if i >= 2*s)
    auth = 0
    for lvl in range(hgt):
        nxt = []; j = 0
        while j < len(I):
            x = I[j]
            if j + 1 < len(I) and I[j+1] == x ^ 1: j += 2   # sibling known
            else: auth += 1; j += 1                         # sibling goes to Auth
            if not nxt or nxt[-1] != x >> 1: nxt.append(x >> 1)
        I = sorted(nxt + P) if lvl == 0 else nxt
    return auth                            # I == [0] (root) at exit

def hash_to_subset(y, t, k, h):            # KN Algorithm 1 (p.25)
    b = (t - 1).bit_length()
    tau = int.from_bytes(y, 'big') >> (8*len(y) - h)           # first h bits
    nu = (8*len(y) - h) // b
    X = []
    for i in range(nu):                    # blocks b_1..b_nu, MSB-first after tau
        v = sum(bit(y, h + i*b + j) << (b-1-j) for j in range(b))
        if v < t and v not in X and len(X) < k: X.append(v)
    if len(X) < k: return None             # attempt fails (counts as a try)
    return tau, sorted(X)

def pors_fp_grind(SKprf, PKseed, PKroot, M, a, k, h, d, m_max, imax=2**32):
    t = k * 2**a
    for i in range(imax):
        R = hmac_sha256(SKprf, PKseed + M + toByte(i,4))[:16]   # same as §2
        y = H_msg(R, PKseed, PKroot, M, 64)                     # [OUR CHOICE] 512-bit output
        r = hash_to_subset(y, t, k, h)
        if r is None: continue
        tau, X = r
        if octopus_size(X, t) <= m_max:
            idx_tree, idx_leaf = tau >> (h//d), tau & ((1 << (h//d)) - 1)   # [GUESS]
            return R, X, idx_tree, idx_leaf, i + 1
    return FAIL
```
Compressions per attempt: PRF_msg 2 + H_msg inner 2 + MGF1 shared block 1 + 2 MGF1 tails = **7** (REPO: 4). Plus integer work for subset + Octopus (≤ ν + hgt·k steps).
Expected tries = 2^{log2E(m_max)} / P_enough (table §0). The first factor comes from the Abri–Katz PMF (`interleave_cost_table(k·2^a, k)`).
`octopus_size` was cross-checked by us against a brute-force count of {sibling(v) : v on some leaf→root path, sibling(v) not on any path}: 2,400 random cases over t ∈ {8, 9, 12, 100, 147456, 163840, 180224, 524288}, all equal. The tree geometry matches REPO `pmf_leftfilled` (h = ⌈log2 t⌉, x = 2(t − 2^{h−1}) bottom leaves) and SHRINCS-CPP `pors_octopus` (s = T − 2^{B−1}).
Verifier side (not ground): pad Auth to m_max (KN §10), reject if |S| > m_max.

## §5 Summary of per-attempt cost (compressions, M = 32 B)

| component | layout | per attempt | REPO model | transmitted grind data |
|---|---|---|---|---|
| WOTS+C | ADRSc* ‖ m ‖ ctr4 after PK.seed midstate | 1 | 1 (`C_Th1c`) | 4 B ctr × d |
| FORS+C | R-grind (PRF_msg ctr) | 6 (8 naive HMAC) | 4 | none (R already sent) |
| FORS+C | ctr in inner H_msg | 3 | n/a | 4 B ctr |
| FORS+C | ctr in MGF1 seed (exploratory) | 1 | n/a | 4 B ctr |
| PORS+FP | R-grind, 512-bit H_msg | 7 + Octopus | 4 | none |
