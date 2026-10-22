# GRINDSTONE knowledge base

Merged 2026-10-22 from research agents A–E (Phase 2). Every number used in the paper must trace to
`claims/all_claims.yaml` (145 claims, ids prefixed by agent) or to `data/`.

| Path | Content | From |
|---|---|---|
| `sources/*.yaml` | 28 bibliographic sources with trust level | C (others cite inline in claims) |
| `claims/all_claims.yaml` | All atomic claims, `verified_by_us: false` until reproduced | A–E |
| `constructions/grind_pseudocode.md` | Byte-exact grind layouts, per-row constants | A |
| `constructions/ambiguity_decisions.md` | Decisions for doc §3.5 ambiguities 1–5 | A |
| `params/params_candidates.parquet` | 1,363,309 candidate parameter rows | B |
| `params/shortlist_draft.yaml` | 40-point draft shortlist (not frozen) | B |
| `requirements.md` | 40 developer requirements + open questions | C |
| `hardware.yaml` | Signer-class throughput ladder (cited) | D |
| `fees.py` | bytes → WU → vB → sats | E |
| `raw/A/email_draft.md` | Draft to Kudinov & Nick (not sent; needs owner approval) | A |

## Findings that change the original plan (doc v1.2)

1. **Per-attempt grind cost (A, confirmed by `ref/fors_c.count_compressions`).** FIPS 205-faithful
   SHA-2 instantiation: FORS+C R-grind = 6 compressions (8 without HMAC midstates), FORS+C ctr-grind
   = 3, PORS+FP = 7 (512-bit H_msg), WOTS+C = 1. The repo/paper model counts 4 for FORS+C/PORS+FP.
   Doc §3.5 and §4.0 should be updated.
2. **R size (A, B).** Paper Tables 1–2 use 32-byte R; repo `ceee8ed` and FIPS 205 use 16 bytes, so
   repo sizes are exactly 16 B smaller (3,128 → 3,112 etc.). B's model reproduces all 30 paper rows
   exactly with R = 32.
3. **PORS+FP failure mass (A).** With a 512-bit H_msg, an attempt yields < k distinct indices with
   probability up to 1.3%; analytic expected work must be divided by P_enough (0.987–1.000). Measured
   on GPU for k=11, a=14, m_max=118: 111,075 tries vs 110,790 corrected analytic (+0.26%, n=20,000).
4. **SHRINCS (C).** The current SHRINCS draft's stateless path is plain SLH-DSA (no FORS+C/PORS+FP),
   and its WOTS+C uses a 16-bit counter over a 32-byte digest (~1/64 success). FORS+C results inform
   optimised-variant debate, not SHRINCS-as-drafted.
5. **Timeline facts to recheck (C).** Doc says Google "≤1,200" logical qubits; a bitcoindev message
   quotes the same paper as "at least 1200". IonQ estimate not found on bitcoindev/Delving.
6. **2^−30 worst case (B).** The paper's "worst case" sums per-component bounds; it is not a single
   joint bound.
7. **GPU-signer points use z = 1 (B).** One WOTS+C chain forced to zero per layer. Not modelled in the
   repo; security impact unanalysed. Equivalent to 8 trailing zero bits of d at w = 256, which the
   kernel's zero mask already implements.

## Agent reports blocked by tooling (summarised here)

**B — parameters.** `ref/costs.py` ports costs.sage; `tests/test_costs.py` (56 tests) reproduces all
30 Table 1–2 rows exactly on size, verification cost, expected grind and 2^−30 worst case, plus the
repo's golden values. 3,128 B is not the smallest 2^20 point (a 2,856 B row exists). Fluhrer–Dang
2024/018 2^20 sets match sizes exactly and signing hashes within 5; their verification counts are
18–27 hashes higher; grinding buys ~300 B at equal signing budget. gpu-max points' signing cost is
dominated by tree building (~5–8e8 compressions), not grinding.

**D — hardware (cited, typical compressions/s).** Class 0: ATECC608 ~1.5e2, Cortex-M4 software
~4.0e4, MCU HASH peripheral ~1.2e5. Class 1: Pi 4 ~8.3e6, Pi 5 ~7.4e7. Class 2: i5-13420H class
~1.8e8 (estimate). Class 3: RTX 4060 ~4.0e9. Class 4: 8× RTX 4090 ~1.72e11. pqm4 cross-check:
~3,000 cycles/compression on Cortex-M4. Hashcat overstates full-compression rates by 5–15%.
Conflict logged: OpenBenchmarking RTX 4090 ~50 GH/s vs hashcat (claim D-C036), not used.

**E — fees.** 1 signature byte = 0.25 vB. P2MR witness overhead at depth 1 ≈ signature + 73 B.
A 3–4 KB signature is invalid in tapscript today (520-byte element limit, BIP-342); a new
OP_SUCCESSx-based opcode would lift it. Weight code reproduces two mainnet txs exactly.

## Our measurements so far (preliminary, short runs; E0/E5 supersede)

| What | Value |
|---|---|
| GPU raw single-block compressions/s (10 s) | 2.2e9 |
| CPU SHA-NI, 1 thread / 12 threads | 2.9e7 / 2.65e8 |
| GPU WOTS+C useful compressions/s | 1.25e9 (w=16,S=304) – 1.67e9 (w=256,S=2840) |
| GPU FORS+C R-grind / ctr-grind attempts/s | 3.8e8 / 7.9e8 |
| GPU PORS+FP attempts/s (k=11,a=14,m_max=118) | 1.58e8 |
