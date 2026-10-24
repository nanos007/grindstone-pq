# Spot-check: C-* quotes and D-* hardware figures (threats §8.2, Must-fix 4)

Generated 2026-10-24 from `kb/claims/all_claims.yaml`. These claims were compiled by LLM agents. Only claims
whose number or quote appears downstream are listed. They were found by text matching against the paper,
executive summary, mailing-list post and `kb/hardware.yaml`, so a few matches may be coincidental; tick
"not used" for those. The other 39 C/D claims are background only and nothing quantitative depends on them.

For each claim: open the source, find the location, and confirm that the statement and the value match.
Mark a wrong claim ✗, fix it in `all_claims.yaml`, and tell Claude which downstream number to recompute.

## Pre-check of Tier 1 (Claude, 2026-10-24; sources fetched, not a substitute for the sign-off below)

All 14 checkable Tier-1 claims match their sources. C-C006's public-key size (48 B) was not found; the original
SHRINCS post says 16 B. No downstream number uses it. Re-checking usage showed that only the four D-* claims
feed results (signer rates in `kb/hardware.yaml`). The C-* matches were coincidental numbers (16, 40, 548, ...),
so a C-* error would change wording at most, not a computed result.

| Claim | Says | Source says | Verdict |
|---|---|---|---|
| C-C006 | SHRINCS: 5777 B stateless, 548 B stateful min, 48 B pk | SHRINCS.md: `SHRINCS_SL_SIGNATURE_SIZE` 5777, `SHRINCS_SF_SIGNATURE_SIZE_MIN` 548; pk 48 B not found (Dec 2025 post: "public key is 16 bytes") | 2/3 ✓, pk ?; not used |
| C-C007 | OTS 292 B, min(292+q·16, s_l)+16 | "OTS signature is 292 bytes … min(292 + q·16, s_l) + 16" (jonasnick, 2025-12-11) | ✓ |
| C-C011 | 4480 B at 2⁴⁰, verify ratio "almost 9 times better" | "4480 bytes signatures (under the 2^40 signatures limit) … ratio being almost 9 times better" (Kudinov, bitcoindev 2025-12-08) | ✓ |
| C-C012 | WOTS+C+PORS+FP 16–18 % smaller at 2⁴⁰ | "16% to 18% smaller than vanilla, size-optimized SPHINCS+ (for 2^40 signatures max)" (same thread; author per Google Groups render: Kudinov) | ✓ (author: check) |
| C-C013 | ~2⁷⁸ Toffoli depth, limited parallelism | "approximately 2^78 Toffoli depth operations in practice, with limited parallelization benefits" (Kudinov, 2025-12-08) | ✓ |
| C-C021 | 11 ms sign, 2 ms keygen (1 ms batched); PQClean 94/12 ms; MB of RAM | verbatim (conduition, bitcoindev 2025-11-24) | ✓ |
| C-C028 | SHRINCS stateless n16 lg_w4 d5 h'9 a13 k10, 2⁴⁰, −26 %/−23 %/−28 % | SHRINCS.md parameter table + rationale, all values | ✓ |
| C-C029 | H_grind layout, u16 counter, 2¹⁶ tries, 2¹²² of 2¹²⁸, fail < 2⁻¹⁴⁵⁰ | SHRINCS.md `H_grind` code and grind docs, all values | ✓ |
| C-C031 | SHRIMPS 2564 B @ 2¹⁰, (8,17,12,1), 6.8M; SLH-DSA 7856 B @ 2.3M; 0.30 vs ~0.19 C/B | SHRIMPS post table and text, all values | ✓ |
| C-C042 | h40 d4 a13 k12 w4 → 7696 B, ~1000 compressions, ~64× cheaper/byte | conduition, Delving #2749, all values | ✓ |
| C-C043 | 338,000 comp/s, ~482 sig/s, ~20 s per 10k-sig block | conduition, Delving #2875, all values | ✓ |
| D-C004 | pqm4 cycles at 24 MHz (no wait states) | "obtained at 24MHz to avoid wait cycles due to the speed of the memory controller" | ✓ (wording: memory, not flash) |
| D-C009 | STM32L4A6Z sw SHA-256 847.458 KiB/s @ 80 MHz | "SHA-256 … 847.458 KiB/s", "Cortex-M4 at 80 MHz"; derived 13.6k comp/s, 92.2 c/B recomputed ✓ | ✓ |
| D-C023 | Pi 5 SHA-256 wolfCrypt 1464, MbedTLS 205 MiB/s | "SHA-256 1464 MiB/s 205 MiB/s" (Cortex-A76 @ 2.4 GHz); derived 24.0M comp/s ✓ | ✓ |
| D-C029 | SHA-NI 64-B block ≈ 80 ns (Xeon Gold 5318Y) | "On SHA-NI hardware, one 64-byte SHA-256 block compresses in roughly 80 ns" | ✓ (claim says "one-shot API"; source derives it from the incremental-API floor) |

## Tier 1: appears in the paper, summary or post (15)

- [ ] **C-C006** (H; used in paper.md)
  - Claim: The SHRINCS draft states: stateless signatures are 5777 bytes, stateful signatures are 548 bytes at minimum, and public keys are 48 bytes.
  - Value: `{pk_bytes: 48, stateful_sig_min_bytes: 548, stateless_sig_bytes: 5777}`
  - Source: https://gnusha.org/pi/bitcoindev/-w8D4WbD7zY2bfYQIES40iBZQWbZx6ab-S6EW8tWsMEFaHO9NEOLUkte_MZZgNQDd0pljCM2wD1Ccnk3BfjwLPgCiVz-NfTwjHJ4aZHUqUw=@proton.me/T/ (Root message, 'Features' list)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **C-C007** (H; used in hardware.yaml, paper.md)
  - Claim: Original SHRINCS (Dec 2025): with intact state, signature size is min(292 + q*16, s_l) + 16 bytes at NIST L1, i.e. 324 B for q = 1; the WOTS+C OTS is 292 B.
  - Value: `{auth_path_bytes_per_q: 16, ots_bytes: 292, sig_bytes_q1: 324}`
  - Source: https://delvingbitcoin.org/t/shrincs-324-byte-stateful-post-quantum-signatures-with-static-backups/2158 (Post #1 (jonasnick, 2025-12-11))
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **C-C011** (H; used in mailing_list_post.md, paper.md)
  - Claim: A 4480-byte signature at the 2^40 limit (Table 1 of the report) has a verification-cost-to-size ratio 'almost 9 times better' than Schnorr.
  - Value: `{sig_bytes: 4480, sig_limit_log2: 40, verify_ratio_vs_schnorr: almost 9x better}`
  - Source: https://gnusha.org/pi/bitcoindev/CAPcK4uQBvfWpNsOdOwW++L_LgUxFH-9CvY7YFKb1b5OzJgJ_1A@mail.gmail.com/ (Section 'On verification costs')
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **C-C012** (H; used in hardware.yaml, mailing_list_post.md, paper.md)
  - Claim: The WOTS+C + PORS+FP variant is 16% to 18% smaller than vanilla, size-optimized SPHINCS+ for 2^40 signatures max (per costs.sage).
  - Value: `{sig_limit_log2: 40, size_reduction_pct: [16, 18]}`
  - Source: https://gnusha.org/pi/bitcoindev/27070789-50f0-4d2d-a107-c90be445db14@gmail.com/ (Paragraph 1)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **C-C013** (M; used in paper.md)
  - Claim: Quantum attacks on 128-bit hash security require approximately 2^78 Toffoli depth in practice, with limited parallelization benefits.
  - Value: `{toffoli_depth_log2: 78}`
  - Source: https://gnusha.org/pi/bitcoindev/3e815d03-5e21-41ed-ba1a-4f9b2120a986n@googlegroups.com/T/ (Root message, security-targets paragraph)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **C-C021** (M; used in executive_summary.md, hardware.yaml, mailing_list_post.md, paper.md)
  - Claim: conduition's optimized SLH-DSA-SHA2-128s signs in 11 ms and generates keys in 2 ms (1 ms batched) on his desktop CPU, versus PQClean's 94 ms and 12 ms. It needs several MB of RAM and does not help hardware wallets.
  - Value: `{keygen_batched_ms: 1, keygen_ms: 2, pqclean_keygen_ms: 12, pqclean_sign_ms: 94, ram: several megabytes, sign_ms: 11}`
  - Source: https://groups.google.com/g/bitcoindev/c/LAll07BHwjw (Root message (Google Groups render))
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **C-C028** (H; used in executive_summary.md, hardware.yaml, mailing_list_post.md, paper.md)
  - Claim: SHRINCS stateless parameters: SLH-DSA (FIPS-205 algorithms) with n=16, lg_w=4, d=5, h'=9, a=13, k=10; 2^40 budget; 26% smaller than SLH-DSA-SHA2-128s; 23% fewer compressions for average signing and 28% fewer for worst-case verification. No FORS+C or PORS+FP is used.
  - Value: `{a: 13, budget_log2: 40, d: 5, h_prime: 9, k: 10, lg_w: 4, n: 16, sign_reduction_pct: 23, size_reduction_pct: 26, verify_reduction_pct: 28}`
  - Source: https://github.com/SHRINCS/shrincs-bip/blob/main/SHRINCS.md (Sections 'Stateless Parameters' and 'Why not use a standardized SLH-DSA parameter set?')
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **C-C029** (H; used in hardware.yaml, paper.md)
  - Claim: SHRINCS WOTS+C grind: H_grind = sha256(pk_seed || zeros(48) || ADRS[:10] || digest(32 B) || zeros(4) || counter(u16))[:16]. At most 2^16 attempts. With w=16 and 32 chains, about 2^122 of 2^128 index sets hit the constant sum 240, so P(success) ≈ 2^-6 (derived). Failure probability < 2^-1450.
  - Value: `{chain_bits: 4, chains: 32, compressions_per_attempt_derived: 1, constant_sum: 240, counter_bits: 16, fail_prob_log2: -1450, frac_valid_log2: -6, max_attempts: 65536}`
  - Source: https://github.com/SHRINCS/shrincs-bip/blob/main/SHRINCS.md (Sections 'H_grind(...)', 'wots_c_grind_to_constant_sum(...)', 'Stateful Parameters/Constants')
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **C-C031** (H; used in executive_summary.md, hardware.yaml, mailing_list_post.md, paper.md)
  - Claim: SHRIMPS compact path: 2564 B at q_s = 2^10 with (k,a,h,d) = (8,17,12,1), w=16, S_wn=240, costing 6.8M compressions to sign. SLH-DSA (q_s = 2^64) is 7856 B at 2.3M compressions. Verification is 0.30 C/B for SLH-DSA vs ~0.19 for d=1 sets.
  - Value: `{q_s_log2: 10, sig_bytes: 2564, sign_compressions: 6.8e6, slh_dsa_bytes: 7856, slh_dsa_sign_compressions: 2.3e6}`
  - Source: https://delvingbitcoin.org/t/shrimps-2-5-kb-post-quantum-signatures-across-multiple-stateful-devices/2355 (Post #1 (jonasnick, 2026-03-27), parameter table)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **C-C042** (M; used in hardware.yaml, mailing_list_post.md, paper.md)
  - Claim: SLH-DSA with h=40 d=4 a=13 k=12 w=4 gives 7696-byte signatures costing about 1000 SHA-256 compressions to verify, about 64x cheaper per byte than Schnorr with hardware acceleration.
  - Value: `{a: 13, d: 4, h: 40, k: 12, sig_bytes: 7696, verify_compressions: 1000, w: 4}`
  - Source: https://delvingbitcoin.org/t/pqc-output-type-discussion/2749 (Post #9 (conduition, 2026-08-22))
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **C-C043** (L; used in hardware.yaml, mailing_list_post.md, paper.md)
  - Claim: A 10-thread CPU prover (naive extension of Flock benchmarks) proves ~338000 SHA-256 compressions/s, ~482 signature verifications/s for h=36 d=4 a=13 k=15 w=4, ~20 s per block of ~10,000 signatures.
  - Value: `{block_prove_s: 20, compressions_per_s: 338000, sigs_per_s: 482}`
  - Source: https://delvingbitcoin.org/t/block-wide-signature-aggregation-via-snarks/2875 (Post #10 (conduition, 2026-09-16))
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C004** (H; used in executive_summary.md, hardware.yaml, paper.md)
  - Claim: pqm4 cycle counts are obtained at 24 MHz to avoid flash wait states.
  - Value: `{clock_MHz: 24}`
  - Source: https://github.com/mupq/pqm4 (README, benchmarking section)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C009** (H; used in hardware.yaml, paper.md)
  - Claim: wolfSSL measures software SHA-256 at 847.458 KiB/s on STM32L4A6Z (Cortex-M4 @80 MHz, no asm).
  - Value: `{bytes_per_s: 867797, clock_MHz: 80, compressions_per_s: 13600.0, cycles_per_byte: 92.2}`
  - Source: https://github.com/wolfSSL/wolfssl/blob/master/IDE/STM32Cube/STM32_Benchmarks.md (STM32L4A6Z (No HW Crypto, SP Math All NO ASM), SHA-256 line)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C023** (H; used in executive_summary.md, hardware.yaml, mailing_list_post.md, paper.md)
  - Claim: wolfCrypt SHA-256 runs at 1464 MiB/s and MbedTLS at 205 MiB/s on Raspberry Pi 5 (Cortex-A76 @2.4 GHz).
  - Value: `{cps_wolf_per_core: 24000000.0, mbedtls_MiBps: 205, wolfcrypt_MiBps: 1464}`
  - Source: https://www.wolfssl.com/wordpress/wp-content/uploads/2026/07/wolfSSL-vs-MbedTLS.docx.pdf (Section 'ARM Raspberry Pi 5', results table, SHA-256 row)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C029** (M; used in hardware.yaml, paper.md)
  - Claim: On SHA-NI hardware (Xeon Gold 5318Y), one 64-byte SHA-256 block via OpenSSL one-shot APIs takes roughly 80 ns.
  - Value: `{cps_per_core: 12500000.0, ns_per_block: 80}`
  - Source: https://github.com/hsw/openssl-sha256-bench (README, dispatch section)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____


## Tier 2: feeds `kb/hardware.yaml` only (15)

- [ ] **C-C004** (H; used in hardware.yaml)
  - Claim: A P2MR depth-1 witness (Schnorr leaf) is 135 bytes, 69 bytes larger than a P2TR key-path witness (66 B), and 32 bytes smaller than an equivalent P2TR script-path witness (34 bytes at m = 7).
  - Value: `{delta_vs_keypath: 69, delta_vs_p2tr_scriptpath: -32, p2mr_depth1_witness_bytes: 135, p2tr_keypath_witness_bytes: 66}`
  - Source: https://github.com/bitcoin/bips/blob/master/bip-0360.mediawiki (Section on witness size comparison (P2MR witness for a depth-1 tree; general case 103 + 32*m bytes))
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **C-C010** (H; used in hardware.yaml)
  - Claim: With WOTS+C/FORS+C/PORS+FP optimizations, SPHINCS+ signatures are 4036 B at a 2^40 signature bound, 3440 B at 2^30 and 3128 B at 2^20; standard SPHINCS+ is 'almost 8KB'.
  - Value: `{sig_bytes: {q2_20: 3128, q2_30: 3440, q2_40: 4036}, standard_sphincs: almost 8KB}`
  - Source: https://gnusha.org/pi/bitcoindev/3e815d03-5e21-41ed-ba1a-4f9b2120a986n@googlegroups.com/T/ (Root message (Kudinov & Nick, 2025-12-08), paragraph 3)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **C-C024** (M; used in hardware.yaml)
  - Claim: On the same HW wallets, UXMSS (SHRINCS-L, 1092 B) signing with WOTS+C target sum S_wn=96 takes 3.01–8.04 s (mean). With 'overgrinding' to S_wn=140 it takes 225.63–572.78 s (Jade 225.63, Trezor 264.74, Ledger 572.78, BitBox02 334.6).
  - Value: `{chains: 64, swn_140_s: {bitbox02_nova: 334.6, jade_plus: 225.63, ledger: 572.78, trezor: 264.74}, swn_96_s: {bitbox02_nova: 5.5, jade_plus: 3.31, ledger: 8.04, trezor: 3.01}, w: 4}`
  - Source: https://blog.blockstream.com/hardware-wallets-post-quantum-signatures/ (SigGen table rows 'SHRINCS-L (swn=96, 1092 B)' and 'UXMSS (SHRINCS-L) (swn=140, 1092 B)'; text 'Due to overgrinding...')
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C001** (H; used in hardware.yaml)
  - Claim: pqm4 sphincs-sha2-128f-simple (clean) signing takes 368,575,228 cycles on Cortex-M4 (avg of 10).
  - Value: `{clock_note: measured at 24 MHz, keygen_cycles: 15742990, sign_cycles: 368575228, verify_cycles: 21923628}`
  - Source: https://raw.githubusercontent.com/mupq/pqm4/master/benchmarks.md (Speed Evaluation > Signature Schemes table, row sphincs-sha2-128f-simple clean)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C002** (H; used in hardware.yaml)
  - Claim: pqm4 sphincs-sha2-128s-simple (clean) signing takes 7,657,558,168 cycles on Cortex-M4 (avg of 10).
  - Value: `{keygen_cycles: 1007731522, sign_cycles: 7657558168, verify_cycles: 7471794}`
  - Source: https://raw.githubusercontent.com/mupq/pqm4/master/benchmarks.md (Speed Evaluation > Signature Schemes table, row sphincs-sha2-128s-simple clean)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C005** (M; used in hardware.yaml)
  - Claim: Back-calculated from D-C001..3, one SHA-256 compression (incl. per-call overhead) costs ~2,950 (128f) to ~3,130 (128s) Cortex-M4 cycles in pqm4 clean SPHINCS+.
  - Value: `{cycles_per_compression_128f: 2950, cycles_per_compression_128s: 3128}`
  - Source: derived (kb/raw/D report section 7) (compressions per signature: 128f ~113.3k, 128s ~2.22M (1 comp per F/H/PRF with seeded midstate; T_len = 10 blocks))
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C008** (H; used in hardware.yaml)
  - Claim: wolfSSL measures software SHA-256 at 2.602 MB/s on STM32F437 (Cortex-M4 @160 MHz, -Os, no HW crypto).
  - Value: `{bytes_per_s: 2602000.0, clock_MHz: 160, compressions_per_s: 40700.0, cycles_per_byte: 61.5}`
  - Source: https://github.com/wolfSSL/wolfssl/blob/master/IDE/STM32Cube/STM32_Benchmarks.md (STM32F437 (No HW Crypto, -Os, FastMath), SHA-256 line)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C010** (H; used in hardware.yaml)
  - Claim: wolfSSL measures SHA-256 at 985 KB/s on STM32WB55 (Cortex-M4 @64 MHz), identical with and without HW hash enabled.
  - Value: `{bytes_per_s: 985222, clock_MHz: 64, compressions_per_s: 15400.0}`
  - Source: https://github.com/wolfSSL/wolfssl/blob/master/IDE/STM32Cube/STM32_Benchmarks.md (STM32WB55 sections, SHA-256 lines)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C011** (H; used in hardware.yaml)
  - Claim: wolfCrypt Thumb2-asm SHA-256 runs at 5488 KiB/s and MbedTLS at 3849 KiB/s on STM32H563 (Cortex-M33 @250 MHz, no HW crypto).
  - Value: `{compressions_per_s_wolf: 87800.0, cycles_per_byte_mbed: 63.4, cycles_per_byte_wolf: 44.5, mbedtls_KiBps: 3849, wolfcrypt_KiBps: 5488}`
  - Source: https://www.wolfssl.com/wordpress/wp-content/uploads/2026/07/wolfSSL-vs-MbedTLS.docx.pdf (Section 'STM32H563 (Cortex-M33 @ 250 MHz, bare metal)', results table, SHA-256 row)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C013** (M; used in hardware.yaml)
  - Claim: STM32U5 HASH peripheral is claimed to process one 512-bit SHA-256 block in 66 clock cycles (RM0456 ch. 51); Trezor had not used it as of the issue.
  - Value: `{cycles_per_block: 66, theoretical_cps_at_160MHz: 2420000.0}`
  - Source: https://github.com/trezor/trezor-firmware/issues/3638 (Issue #3638 description)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C020** (H; used in hardware.yaml)
  - Claim: SUPERCOP measures sha256 at 11.34 cycles/byte (long messages, median) on Raspberry Pi 4 (Cortex-A72).
  - Value: `{cps_per_core_1500MHz: 2070000.0, cycles_per_byte: 11.34, cycles_per_compression: 726}`
  - Source: https://bench.cr.yp.to/results-nistlwc-hash/aarch64-pi4b.html (Cycles/byte for long messages, row sha256 (supercop-20251114))
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C021** (H; used in hardware.yaml)
  - Claim: SUPERCOP measures sha256 at 27.31 cycles/byte for 64-byte messages on Raspberry Pi 4.
  - Value: `{cycles_per_byte_64B: 27.31}`
  - Source: http://bench.cr.yp.to/results-hash/aarch64-pi4b.html (Cycles/byte for 64 bytes, row sha256 (supercop-20260330))
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C026** (H; used in hardware.yaml)
  - Claim: SUPERCOP measures sha256 at 2.05 cycles/byte (long) and 4.69 cycles/byte (64-byte msg) on Intel Core i7-13700H P cores (Raptor Cove).
  - Value: `{cps_per_core_4600MHz: 35100000.0, cycles_per_byte_64B: 4.69, cycles_per_byte_long: 2.05, cycles_per_compression: 131}`
  - Source: http://bench.cr.yp.to/results-hash/amd64-raptor.html (Cycles/byte for long messages / for 64 bytes, rows sha256 (supercop-20231107))
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C028** (H; used in hardware.yaml)
  - Claim: wolfCrypt SHA-256 (SHA extensions) runs at 1703 MiB/s on Intel i9-11950H; MbedTLS at 340 MiB/s.
  - Value: `{cps_per_core: 27900000.0, wolfcrypt_MiBps: 1703}`
  - Source: https://www.wolfssl.com/wordpress/wp-content/uploads/2026/07/wolfSSL-vs-MbedTLS.docx.pdf (Section 'Intel i9-11950H (x86_64)', results table, SHA-256 row)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____

- [ ] **D-C035** (M; used in hardware.yaml)
  - Claim: On an 8x RTX 4090 rig (hashcat 6.2.6 -O -w 4) SHA2-256 runs at 21.5 GH/s per card; 4x H100 SXM total 65,963.4 MH/s (~16.5 GH/s each); 4x H100 PCIe total 50,179.6 MH/s (~12.5 GH/s each).
  - Value: `{h100_pcie_total_4: 50179600000.0, h100_sxm_total_4: 65963400000.0, rtx4090_per_card: 21500000000.0}`
  - Source: https://www.onlinehashcrack.com/tools-benchmark-hashcat-nvidia-rtx-4090.php (RTX 4090 page summary; H100-SXM and H100-PCIE pages Hash-Mode 1400 Speed.#*)
  - Check: [ ] source says this  [ ] number/quote matches  Note: ____


## Sign-off

Checked by: ____  Date: ____  Claims wrong: ____
