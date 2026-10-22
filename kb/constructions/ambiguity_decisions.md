# Agent A — Resolution of open ambiguities 1–5 (GRINDSTONE v1)

Agent A ("Construction Archaeologist") · compiled 2026-10-22 · scope: n = 16, NIST L1, SHA-256 only.
All decisions here are **GRINDSTONE v1 implementation decisions**, not claims about what Kudinov–Nick (K–N) "really meant". Where a decision is our own design choice, it is marked **[OUR CHOICE]**. Guesses are marked **[GUESS]**.

## Sources consulted (all accessed 2026-10-22)

| id | source | version / date | how accessed |
|---|---|---|---|
| KN | Kudinov, Nick, *Hash-based Signature Schemes for Bitcoin*, https://eprint.iacr.org/2025/2203.pdf | PDF says "Revision 2025-12-05" | full text via fetch (direct curl blocked by Cloudflare) |
| REPO | github.com/BlockstreamResearch/SPHINCS-Parameters | commit `ceee8ed67e8b` (2026-08-26) | git clone |
| SPXC | Hülsing, Kudinov, Ronen, Yogev, *SPHINCS+C: Compressing SPHINCS+ With (Almost) No Cost*, https://eprint.iacr.org/2022/778.pdf | 2022-09-14 | full text via fetch |
| SPXC-CODE | github.com/eyalr0/sphincsplusc (SPHINCS+C reference code; README: "only the reference implementation for shake is supported") | commit `f36a76b` (2022-06-18) | git clone |
| FIPS205 | NIST FIPS 205 (SLH-DSA), https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.205.pdf | Aug 2024 | full text via fetch |
| SHRINCS | github.com/SHRINCS/shrincs-bip, `SHRINCS.md` (authors incl. Kudinov, Nick) | commit `2d1679b` (2026-10-18), Status: Draft | git clone |
| SHRINCS-CPP | github.com/BlockstreamResearch/shrincs-cpp (WIP; "may be incorrect") | commit `7643d95` (2026-05-01) | git clone |
| ABRI | github.com/MehdiAbri/PORS-FP (Abri–Katz PORS+FP tooling) | commit `bdf38ee` (2025-11-13) | git clone |

Clones live (read-only, not executed) in the session scratchpad `...\scratchpad\agentA\`.

---

## Headline findings (things that change the plan)

1. **The FORS+C/PORS+FP per-attempt cost is 6 compressions, not 4, under FIPS 205's SHA-2 instantiation.** REPO models `C_Hmsg = 2` (comment: "PKseed + PKroot (128) + R (256) + m (256)", i.e. a single SHA-256 over 96 B). KN §13.2 (p.35–36) says signing a 256-bit digest "results in two compression function calls for H_msg". FIPS 205 §11.2.1 defines H_msg as **MGF1-SHA-256(R ‖ PK.seed ‖ SHA-256(R ‖ PK.seed ‖ PK.root ‖ M), m)**. That is a nested hash: 2 compressions for the inner hash plus 2 for the outer MGF1 block, so **4**. PRF_msg (HMAC) costs 2 with cached ipad/opad midstates and 4 without. R-grind per attempt is therefore **6** (8 with naive HMAC), against the model's 4. Confidence H on the arithmetic. Whether KN intended a non-FIPS single-SHA-256 H_msg is the main question for the email.
2. **The paper and the repo disagree on |R|.** KN §13 (p.31): "the PRF_msg output to be 256 bits". REPO at `d1e9ff4` (2025-12-03) had `randomness_size = 32`. Commit `31e2cdb` (2026-06-24, "Randomness value change") switched it to `16`. KN Table 1/2 sizes therefore include a 32-byte R, and REPO@ceee8ed sizes come out 16 B smaller. Example: W+C F+C 2^30 (32,4,14,10,256,2040) is 3744 B in KN Table 1, and REPO's `compute_size` formula gives 3728 B (hand-computed, **[not run]**). Agent B should confirm. Compressions per attempt don't change: H_msg is 4 either way, see §4.
3. **SHRINCS (2026-10-18) dropped the grinding variants from its stateless path.** It now uses plain SLH-DSA (WOTS-TW + FORS, h = 45, d = 5, a = 13, k = 10). SHRINCS.md "Why not use a SPHINCS+ variant with smaller signatures…" says SPHINCS+C or PORS+FP "could produce stateless signatures approximately 15% smaller". WOTS+C survives only in the stateful path. It does pin a byte-exact WOTS+C grind (`H_grind`), which we use as a cross-check.
4. **There is no public byte-exact spec for FORS+C or PORS+FP over SHA-256 from the authors.** SPXC-CODE is SHAKE-only. SHRINCS-CPP has a PORS+FP that differs from KN Algorithm 1: a counter-mode SHA-256 XOF with a 32-byte uncompressed ADRS, plus a host-endian counter in a non-HMAC PRF_msg. GRINDSTONE must therefore define its own layouts. They are below.

---

## Ambiguity 1 — Which bits are "the last a bits" for FORS+C

**What sources say**
- KN §9.2 (p.21): "force the hash for the last tree to always open the first leaf. This is equivalent to requiring that the last 𝑎 bits of the digest of the message that is signed by FORS are all zeros." (H)
- SPXC §4.1 (p.8): same wording, with b in place of a. SPXC §7.1 (p.18) describes the implementation as: "We try different values of the counter, until the **first** t′ bits of the resulting messages to be signed by FORS+C are zero." (H) *Internal conflict: last vs. first.*
- SPXC-CODE `ref/hash_shake.c` `hash_message()`: reads the first `SPX_FORS_ZEROED_BYTES = ceil(SPX_FORS_ZERO_LAST_BITS/8)` bytes as a big-endian integer, masks the low `SPX_FORS_ZERO_LAST_BITS` bits, and requires zero. It then takes the FORS message from the bytes **after** that field. The zero field is a dedicated prefix, separate from the k·a FORS bits (e.g. `params-sphincs-shake-128s.h`: a = 13, k = 9, `SPX_FORS_ZERO_LAST_BITS 18`). (H)
- FIPS 205 Alg. 19 lines 6–10 (p.34–35): `md ← digest[0 : ⌈k·a/8⌉]`, then idx_tree, then idx_leaf. Alg. 16/§8 (p.30): `indices ← base_2b(md, a, k)`, and tree i uses `indices[i]`. §4.4 Alg. 4 (p.15–16): base_2b reads "the first out_len·b bits of X … in big-endian bit order". (H)

**Decision (v1).** "Last tree opens leaf 0" ⇔ `base_2b(md, a, k)[k−1] == 0` ⇔ digest bits at positions **[(k−1)·a, k·a)** are all zero. Positions count MSB-first from bit 0 = MSB of `digest[0]`. The ⌈k·a/8⌉·8 − k·a trailing pad bits of md are **not** part of the condition, and neither are idx_tree / idx_leaf bits. m is unchanged: the FIPS 205 formula with the full k. Per-row positions are tabulated in pseudocode.md §0.

**Justification.** The semantic definition (last tree, leaf 0) is unambiguous once tree i is bound to the i-th a-bit chunk of md, and FIPS 205 fixes that binding. SPXC-CODE's prefix-field variant is a different construction: an extra zero field, not the last tree's index. That variant has the same 2^−a success probability, so the cost measurement is unaffected. Only test vectors differ. Confidence: H for the semantics, M that the authors would choose identical bytes.

## Ambiguity 2 — WOTS+C zero-chain index range

**What sources say**
- KN §5 (p.11–12, and footnote 3): "∀𝑖 ∈ [𝑤 − 1 − 𝑧 + 1, 𝑤 − 1] ∶ 𝑎𝑖 = 0", with "omit the last 𝑧 chains". (H)
- SPXC §3 (p.4–5, Alg. 6 l.5): "∀ i ∈ [z] : a_i = 0", i.e. the **first** z chains, with "not including elements for the first z chains". (H)
- SPXC §3.1 (p.7) and KN §5.1 (p.13): an alternative "last z_b bits are equal to zero", "useful when log w does not divide n"; probability × 2^−z_b. (H)
- SPXC-CODE `merkle.c`/`wots.c`: `mask = ~0U << (8−WOTS_ZERO_BITS)`, requires `digest[SPX_N−1] & mask == 0`. That tests the **top** WOTS_ZERO_BITS bits of the last byte. For the shipped w = 128, len1 = 18 config, those bits (120–121) lie inside the last digit's bit range (119–125), not in the 2 unused LSBs. This looks like an implementation quirk. **[GUESS: likely unintended]**
- REPO: z is not a parameter at all (`compute_wots_l` returns l1 for W+C). Every reference row has z = 0. (H)

**Decision (v1).** z = 0 and z_b = 0 for all GRINDSTONE runs. The two sources even disagree on first vs. last. If z > 0 is ever explored (v2), we use KN's intent: the **last** z digits `a[len1−z .. len1−1]` (0-based) must be 0, and those chains are omitted. We read KN's "[w−1−z+1, w−1]" as a typo for [len1−z+1, len1] (1-based). z_b is only allowed when lg_w ∤ 128. It then applies to the unused bit positions [len1·lg_w, 128), i.e. the low bits of d[15], so the condition is independent of the digit sum. For w ∈ {16, 256}, lg_w divides 128 and z_b is undefined, hence 0. Confidence H (it doesn't block v1).

## Ambiguity 3 — Exact tweak T*_adrs and byte layout of m ‖ count

**What sources say**
- KN §5 (p.11–12): `d = Th(P, T*_adrs, m‖count)`, count ∈ {0,1}^r; no type value, no endianness. (H)
- REPO `costs.sage` l.39, l.59: `counter_size = 4`; `C_Th1c = 1  # Tweakable hash, 1-block + counter: PKseed + Tweak + m1 + counter (32)`. (H)
- SPXC §7.2 (p.19) + SPXC-CODE: a new ADRS type **7** "WOTS+C message compression address" with layer, tree, type = 7 and key-pair address. A **32-bit counter is inside the ADRS** at byte offset 24 of the 32-byte ADRS (`SPX_OFFSER_COUNTER 24`), big-endian (`ull_to_bytes`). The hashed message is only the root. The counter starts at 1, and 0 is a "not found" sentinel. (H)
- SHRINCS.md `H_grind` (l.933, stateful path only): `sha256(pk_seed ‖ zeros(48) ‖ ADRS[:10] ‖ digest(32 B) ‖ zeros(4) ‖ counter.to_bytes(2))[:16]`, type `SF_WOTS_C_GRIND = 22`, a **16-bit big-endian** counter, the lowest valid counter wins, and the search stops at 2^16 tries. l.938: "The extra 4 bytes of padding before the counter ensures the counter lines up with the SHA256 message schedule boundaries." (H)
- SHRINCS-CPP `wots_c.cpp`: types `SL_WOTS_GRIND 0x0E` / `SF_WOTS_GRIND 0x03`, a 32-byte uncompressed ADRS with the key-pair address, then the message, then `htonl(ctr)` (4 B big-endian). (H, but WIP code)

**Decision (v1), [OUR CHOICE] where noted.**
- Th instantiation = FIPS 205 SHA-2 L1 form: `d = Trunc16(SHA-256(PK.seed ‖ toByte(0,48) ‖ ADRSc* ‖ m ‖ toByte(count,4)))`.
- `ADRSc*` (22 B) = layer (1) ‖ tree address (8, BE) ‖ type = **7** (1) ‖ key-pair address = leaf index of this WOTS+C instance in its XMSS tree (4, BE) ‖ 8 zero bytes. Type 7 is the first value unused by FIPS 205 (0–6) and matches SPXC's value. **[OUR CHOICE]**
- `m` = the 16-byte value signed (subtree root, or FORS/PORS pk at layer 0). count = **4 bytes, big-endian, unsigned, first try count = 0**, and the lowest valid count wins. The counter is appended, **not** placed in the ADRS (KN notation + REPO model).
- Block 2 after the cached PK.seed midstate: bytes 0–21 ADRSc*, 22–37 m, 38–41 count, 42 = 0x80, 43–55 = 0x00, 56–63 = message bit-length 848 = `00 00 00 00 00 00 03 50`. This is **1 compression**. Note: count straddles schedule words W9/W10. The SHRINCS-style alignment pad is *not* used in v1, to stay byte-faithful to the REPO model; the kernel can pre-compute W0–W8.
- Digits: `a = base_2b(d, lg_w, len1)` (FIPS 205 Alg. 4, MSB-first). For w = 16, `a[2j] = d[j] >> 4` and `a[2j+1] = d[j] & 0xF`; for w = 256, `a[j] = d[j]`. Accept iff `Σ a = S_{w,n}` (and z = z_b = 0).

**Justification.** Every variant above costs exactly 1 compression, so the cost results don't depend on the choice. Only test vectors do. Width: 4 bytes matches REPO size accounting. Note that SHRINCS's 16-bit counter would **not** suffice for high-S rows. For w = 256, S = 2840, p = 3.317e−5, so (1−p)^65536 ≈ e^−2.17 ≈ 0.11, i.e. an 11% chance of failure per layer (our computation). Confidence: H that cost = 1 compression; M on byte-equality with any future author spec.

## Ambiguity 4 — Real H_msg / PRF_msg cost for a 32-byte sighash

SHA-256 blocks for an L-byte message = ⌈(L + 9)/64⌉. With M = 32 B and n = 16:

| function | input bytes | blocks naive | with cacheable midstate | notes |
|---|---|---|---|---|
| H_msg inner `SHA-256(R‖PK.seed‖PK.root‖M)` | 80 (|R| = 16) / 96 (|R| = 32) | 2 / 2 | 2 (R first, so nothing cacheable during R-grind) | |
| H_msg outer, one MGF1 block `SHA-256(R‖PK.seed‖inner‖I2OSP(i,4))` | 68 / 84 | 2 / 2 | the first 64 B are shared by all MGF1 blocks i | m ≤ 32 needs 1 MGF1 block |
| **H_msg total, m ≤ 32 B** | | **4** | **4** | REPO/KN assume 2 |
| H_msg total, m = 64 B (PORS+FP, 2 MGF1 blocks) | | 6 | **5** (2 + 1 shared + 2) | |
| PRF_msg = HMAC-SHA-256(SK.prf (16 B), opt_rand ‖ M [‖ ctr4]) inner | 64 + 48 (+4) = 112/116 | 2 | 1 (ipad midstate) | |
| PRF_msg outer | 64 + 32 = 96 | 2 | 1 (opad midstate) | |
| **PRF_msg total** | | **4** | **2** | REPO assumes 2 (matches the midstate case) |
| FORS+C ctr-grind inner `SHA-256(R‖PK.seed‖PK.root‖M‖ctr4)` | 84 | 2 | 1 (first 64 B fixed) | |

m for every REPO F+C / P+FP row is 20–25 B (FIPS 205 m formula, tabulated in pseudocode.md §0), so all fit one MGF1 block.

**Per-attempt totals (decision: these are the numbers GRINDSTONE reports as "model-faithful-to-FIPS-205"):**
- FORS+C R-grind: PRF_msg 2 + H_msg 4 = **6** (8 without HMAC midstates). REPO: 4.
- FORS+C ctr-grind (counter appended to M inside the inner hash): inner 1 + outer 2 = **3**. PRF_msg runs once per signature, not per attempt.
- PORS+FP R-grind with 512-bit H_msg: PRF_msg 2 + H_msg 5 = **7**. REPO: 4.
- WOTS+C: **1** (H).
- Exploratory, **[OUR CHOICE, not in any source]**: "ctr-in-MGF1-seed" puts the counter after the inner digest: `MGF1(R‖PK.seed‖inner‖ctr4, m)`. The first 64 B (R‖PK.seed‖inner) are fixed, so each attempt costs **1** compression. This changes the H_msg wire format and is only to be reported as an upper bound on what layout engineering could buy. It needs Red Team review before any claim.
- Noted alternative (SHRINCS.md l.1142): "PRF_msg_sl may be replaced with an XOF such as MGF1-SHA-256 … from which the caller can sample multiple randomizers for the purposes of grinding". One 32-byte XOF block yields two 16-B R values, which amortises PRF cost to ≈ 0.5–1 compression per R. Not in v1. Possible v2 kernel.

Confidence H for the arithmetic. Every count assumes the GPU computes complete compressions (no early-exit tricks).

## Ambiguity 5 — Argument order of H_msg

**What sources say.** KN §11 (p.26): `H_msg(PK.seed, PK.root, R, m)`; FIPS 205 §11.2.1: `H_msg(R, PK.seed, PK.root, M)` → bytes `R ‖ PK.seed ‖ PK.root ‖ M`. SHRINCS.md `H_msg_sl` (l.1085): `sha256(R + pk_seed + sha256(R + pk_seed + sl_root + M) + zeros(4))`. That is byte-identical to FIPS 205 for one MGF1 block (`zeros(4)` = I2OSP(0,4)). (H)

**Decision.** The wire format is FIPS 205's (R first). The authors' own SHRINCS spec confirms it. KN's argument order is notation only. Confidence H.

---

## Additional specifications requested

### FORS+C R-grinding (KN's chosen layout, §9.2 p.21, §11 p.26: `R = PRF_msg(SK.prf, opt, m, counter)`)
- `R_i = Trunc16(HMAC-SHA-256(key = SK.prf (16 B), msg = opt_rand (16 B) ‖ M (32 B) ‖ toByte(i, 4)))`, i = 0, 1, 2, … The counter goes **after** M, 4 B big-endian. **[OUR CHOICE]**: KN gives the argument order (…, m, counter) but no bytes. opt_rand = PK.seed (FIPS 205 deterministic variant) for reproducibility. The counter is not transmitted.
- `digest_i = MGF1-SHA-256(R_i ‖ PK.seed ‖ SHA-256(R_i ‖ PK.seed ‖ PK.root ‖ M), m)`.
- Accept iff bits [(k−1)a, ka) of digest_i are zero (Ambiguity 1). E[tries] = 2^a.
- |R| = 16 (FIPS 205 n; REPO@ceee8ed). KN's 32-byte R doesn't change compression counts.

### FORS+C counter-in-H_msg (original SPHINCS+C layout)
- Source: SPXC §7.1 (p.18): "we simply added an extra 4 bytes counter value at the end of the first hashing of the message". SPXC-CODE: `SHAKE256(R ‖ PK ‖ M ‖ ctr_BE4)`, counter starts at 1, stored right after R (`FORS_COUNTER_OFFSET = SPX_N`).
- GRINDSTONE v1: `R = PRF_msg(SK.prf, PK.seed, M)` computed once (unmodified FIPS 205). Then `digest_c = MGF1-SHA-256(R ‖ PK.seed ‖ SHA-256(R ‖ PK.seed ‖ PK.root ‖ M ‖ toByte(c,4)), m)`, c = 0, 1, … ("end of the first hashing" maps to the end of the inner SHA-256). Same acceptance as above. The signature carries R (16) + c (4 B BE) right after R, which is SPXC's position. **c starts at 0** [OUR CHOICE; SPXC's start at 1 is an implementation sentinel].

### PORS+FP (KN §10 Algorithm 1, §13.3; Abri–Katz)
- Same R-grind as FORS+C, but H_msg output length = **64 B (512 bits)**. KN §13.3 (p.36): "512-bit output hash value on expectation should be sufficient … we propose to use a hash function with sufficiently large output size (for example SHA-512)". We stay SHA-256-only via 2 MGF1 blocks. **[OUR CHOICE]**
- Index derivation = KN Algorithm 1 (p.25): τ = first h bits. Then ν = ⌊(512 − h)/b⌋ blocks of b = ⌈log2 t⌉ bits each, MSB-first. Values < t are kept in order of appearance, duplicates are ignored, and collection stops at k distinct. Fewer than k is an attempt failure (counted as a try). X = sorted. t = k·2^a (KN §13 "For PORS+FP the number of leaves is k·2^a"; REPO `compute_pors_tree_geometry`). τ → idx_tree = τ >> h′, idx_leaf = τ mod 2^h′ **[GUESS: KN doesn't spell out the τ split]**.
- Acceptance: |Octopus(X)| ≤ m_max on the left-filled tree of height ⌈log2 t⌉. The geometry is consistent between REPO `octopus_pmf.pmf_leftfilled` and SHRINCS-CPP `pors_octopus`. Pseudocode is in pseudocode.md §4, validated against a brute-force minimal-auth-set count (our script, 2,400 random cases, all equal).
- **Correction factor:** P(≥ k distinct valid among ν blocks) is < 1. Our DP: for 2^30 (32,4,14,10): t = 163840, b = 18, ν = 26, P = 0.996361. Across all REPO P+FP rows it ranges 0.987414–1.000000 (table in pseudocode.md §0). The analytic E[tries] = 2^{log2 E work}/P_enough. REPO assumes P_enough = 1 (KN §13.3: "we assume that a single hash function invocation is sufficient"). This 0–1.3% bias matters for the RQ1 "within 2%" gate.
- SHRINCS-CPP alternative, recorded but not used: a separate XOF `SHA-256(PK.seed-midstate ‖ ADRS_32(type PORS_XOF) ‖ digest32 ‖ blk_BE4)`. It takes c = ⌊256/B⌋ B-bit candidates per 32-B block and discards the leftover bits of each block.

### Ordering inside one signature (for E4)
The FORS+C/PORS+FP grind runs first, because it fixes idx_tree/idx_leaf and therefore which FORS instance is used. Then the k−1 trees (or the PORS tree) are built, then the WOTS+C grind on the FORS pk at layer 0, then subtree root, WOTS+C grind at layer 1, and so on up to d grinds. All d WOTS+C grinds are sequential (each m depends on the layer below).

## Remaining genuinely open (→ email)
1. Did KN/REPO intend H_msg = FIPS 205 MGF1 construction (4 compressions) or a single SHA-256 (2)?
2. |R| = 32 (paper) vs 16 (repo since 2026-06-24): which is canonical?
3. WOTS+C T*_adrs: type value, counter in the ADRS vs. appended, width 4 B vs. SHRINCS's 2 B.
4. Exact PRF_msg counter encoding/position for R-grinding.
5. PORS+FP over SHA-256: output length, the τ split, and whether P_enough < 1 should enter the cost tables.
6. Zero-chain index range (first vs. last z), even though z = 0 in all rows.
