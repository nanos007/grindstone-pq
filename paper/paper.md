# Grinding at the Edge: Empirical Signer-Cost Distributions for Bitcoin-Tuned Hash-Based Signatures

*George Nanos* · DRAFT 2026-10-24 · not for distribution before the must-fix items in §7 are closed

> **Draft status.** Every number in this draft comes from `analysis/out/` (run `196e7e91e907`) or from
> `kb/claims/all_claims.yaml`. Sections marked **[TODO]** need the owner's input or the optional GPU runs.
> Signature sizes use R = 16 B (FIPS 205, SPHINCS-Parameters HEAD); Kudinov–Nick's tables use R = 32 B and
> are 16 B larger.

## Abstract

Hash-based signatures are the conservative post-quantum option for Bitcoin. Their size can be cut by
*grinding*: the signer retries a hash until a condition holds, so checksum chains (WOTS+C) or FORS tree
paths (FORS+C, PORS+FP) can be dropped from the signature. Prior work tabulates the expected search cost and
an analytic 2⁻³⁰ worst case in abstract hash calls.

We measure the cost. On a 45 W laptop GPU we ran 11.16 million reference-verified grinds across 37 grind
configurations, which serve 40 parameter sets at 2²⁰, 2³⁰ and 2⁴⁰ signature limits. We cross-checked them
on a SHA-NI laptop CPU. Results:
- Every measured mean is within 2 % of the analytic expectation, and the distributions are geometric down
  to the 10⁻⁴…10⁻⁶ tail.
- The widely used cost model under-prices FORS+C and PORS+FP attempts by 1.5–1.75× under FIPS 205's SHA-2
  instantiation, and over-prices the counter-in-H_msg variant by 1.33×.
- Grinding is at most 18 % of total signing work; tree building dominates.
- A signer budget of 10 s at p99 on a laptop CPU, or under one second on a laptop GPU, buys 596–1,052 bytes
  per signature over a hardware-wallet-safe set: 17–23 % of a 1-input/2-output transaction.
- Verification cost never increases.

We release the CUDA/NVRTC grinder, the dataset and a one-command reproduction.

## 1. Introduction

BIP-360 (P2MR) was merged on 2026-02-11 and leaves the post-quantum signature opcode to a future BIP. Kudinov
and Nick's Bitcoin-tuned SPHINCS+ variants (ePrint 2025/2203) show that two levers shrink hash-based
signatures:
- **fewer signatures per key:** 2²⁰–2⁴⁰ instead of 2⁶⁴;
- **grinding:** a pure work-for-bytes trade made at signing time.

How much work a signer can afford is a free parameter of the design, and the community disagrees about it.
Positions range from "seconds per input on low-power devices is fine" (Maxwell, RQ-02) to "a couple of
minutes is not a big deal" (Blockstream, RQ-05). SHRINCS fixes a single parameter set (RQ-41).

Kudinov and Nick opened the bitcoindev thread with the question **"What are the concrete performance
requirements across various hardware, including low-power devices?"** (OQ-1). Maxwell's answer to whether
several parameter sets should be standardized was **"it would depend on their relative performance"** (OQ-2).

This paper supplies that relative performance, measured. Contributions:
1. **Validation (RQ1).** The analytic expected cost holds to 2 % for WOTS+C, FORS+C (two layouts) and PORS+FP,
   and the full distribution is geometric.
2. **Per-attempt pricing (H1b).** Counted under FIPS 205 SHA-2, grinding attempts cost 1 / 6 / 3 / 7 SHA-256
   compressions (WOTS+C / FORS+C R-grind / FORS+C ctr-grind / PORS+FP), not 1 / 4 / 4 / 4.
3. **Latency per signer class (RQ2, OQ-1).** p50 / p99 / p99.9 signing time from hardware wallets to GPUs,
   measured on two classes and scaled from cited rates for four.
4. **Frontier and fees (RQ3/RQ4, OQ-2).** The smallest signature per time budget and per class, and its fee
   effect.
5. **Open artifacts:** kernels, data, notebooks, reproduction.

## 2. Background

**SPHINCS+ / SLH-DSA.** A hypertree of d layers of XMSS trees, each signing the root below with WOTS, over a
few-time signature (FORS) on the message digest. FIPS 205 fixes the SHA-2 instantiation:
- H_msg = MGF1-SHA-256(R ‖ PK.seed ‖ SHA-256(R ‖ PK.seed ‖ PK.root ‖ M), m);
- PRF_msg = HMAC-SHA-256.

**WOTS+C.** The signer grinds a counter until the base-w digits of d = Th(PK.seed, ADRS, m ‖ count) sum to a
fixed target S. This removes the checksum chains. Success probability p = ν / w^len1. The signature carries
the counter.

**FORS+C.** The signer grinds until the last FORS tree opens leaf 0, which happens with p = 2⁻ᵃ, so that tree's
path is dropped. Kudinov–Nick put the counter into PRF_msg ("R-grind": fresh R per attempt, nothing extra
stored). The original SPHINCS+C appends a counter to H_msg ("ctr-grind": R fixed, 4-byte counter stored).

**PORS+FP.** PORS with forced pruning. The signer grinds R until the k distinct indices derived from H_msg
have an Octopus authentication set of size ≤ m_max. Expected work comes from Abri–Katz's exact PMF. With a
512-bit H_msg, an attempt can also fail to yield k distinct indices; we include that probability (P_enough,
0.987–1.000 for the reference rows).

**Tail model.** Independent attempts make the number of tries T geometric: P(T > t) = (1 − p)^t. So
p99 ≈ 4.61/p, p99.9 ≈ 6.91/p and the 2⁻³⁰ quantile ≈ 20.8/p.

## 3. Methodology

**Parameter points.** We use 40 shortlisted points:
- the 29 Kudinov–Nick table rows (reproduced exactly by our port of `costs.sage`: size, verification cost,
  expected search and 2⁻³⁰ worst case);
- per signature limit, a **hw_wallet_safe** point (every grind ≤ 2¹² tries), a **gpu_signer_moderate** point
  and a **gpu_signer_max** point;
- two stress points.

The search space was capped at grinds ≤ 2²⁴ expected tries and signing ≤ 2³⁰ compressions. The grind
distribution depends only on (w, S, z), on (k, a) and the layout, or on (k, a, h, m_max), so the 40 points
need 37 grind configurations.

**Byte layouts.** The authors give no byte-level SHA-256 spec for FORS+C or PORS+FP, so we fixed FIPS
205-faithful layouts (`kb/constructions/`):
- WOTS+C: ADRSc (type 7) ‖ m ‖ count₃₂ in one block after the PK.seed midstate;
- FORS+C: last a-bit chunk of md is zero;
- R-grind: HMAC message opt_rand ‖ M ‖ i₃₂.

Tries do not depend on these choices; per-attempt cost and test vectors do.

**Kernels.** NVRTC-compiled CUDA (no toolkit needed), one kernel per layout. Each thread strides counters,
and the lowest successful counter wins (atomicMin), so the result is deterministic and equals a sequential
search. Many independent instances are batched per launch, and each instance is one sample.

**Correctness.**
- **Gate.** A campaign starts only after the E1 gate passes: 10 configurations at reduced difficulty (all
  acceptance paths, including FORS masks straddling 32-bit words and non-power-of-two PORS t), 10⁴
  instances each. Every counter matches the pure-Python reference with a full minimality check.
- **Campaign.** All 11.16 M campaign counters were re-checked by the reference.
- **CPU cross-check.** A separate SHA-NI CPU grinder reproduced all WOTS+C counters bit for bit.

**Samples.** 10⁶ per WOTS+C config, 2·10⁵ per FORS+C config, 10⁵ per PORS+FP config. The three PORS+FP
configs with E[tries] ≈ 1.2·10⁷ got 2·10⁴.

**Hardware.** MSI Thin 15 B13VE:
- RTX 4050 Laptop GPU at its 45 W TGP floor (20 SMs, sm_89). E0 sustained single-block SHA-256:
  2.15·10⁹ compressions/s.
- i5-13420H (4P+4E, SHA-NI). E5 sustained, 12 threads: 2.33·10⁸ compressions/s; 1 thread: 2.93·10⁷.

Board power, clocks and clock-event reasons were logged at 10 Hz. The GPU sat at its power cap; 0.014 % of busy
samples were flagged by any slowdown reason.

**Signer classes.** For the other classes we use cited typical rates (`kb/hardware.yaml`), labelled as
cited/derived:
- Cortex-M4 software SHA: 4·10⁴/s;
- MCU with SHA peripheral: 1.2·10⁵/s;
- Raspberry Pi 5: 7.4·10⁷/s;
- 8× RTX 4090: 1.72·10¹¹/s.

**Full signing cost (E4)** = the model's non-grinding work (tree building) + the measured per-signature grind
distribution (d WOTS+C layers + one FTS grind, resampled), priced at the counted per-attempt cost.

**Statistics.** Mean ratio with 95 % CI. A randomized probability integral transform against the *analytic*
p (nothing fitted), tested with KS (Holm-corrected) and Anderson–Darling. Σz² across configs.

## 4. Results

### 4.1 Validation (RQ1, H1)

| | value |
|---|---|
| configs / samples | 37 / 11.16 M, all reference-verified |
| max \|mean/analytic − 1\| | 1.66 % (`pors-k9-a13-h48-m77`, n = 2·10⁴, z = −2.36) |
| Σz² (37 dof) | 39.6, p = 0.36; 2 configs outside their 95 % CI (1.9 expected) |
| KS on PIT, Holm 5 % | 0 rejections |
| AD on PIT, 5 % | 2 rejections (1.9 expected) |
| variance / geometric variance | 0.963–1.026 (median 1.000) |
| p99 / mean | 4.56–4.65 (theory 4.61) |
| p99.9 / mean | 6.73–7.05 (theory 6.91) |

All configs collapse onto e^(−x) when tries are divided by E[tries] (Fig. 1, `ccdf_normalized.png`). The
analytic model, including the P_enough correction for PORS+FP, is accurate for the mean and the shape.

### 4.2 What an attempt really costs (H1b)

| grind | model (costs.sage) | counted (FIPS 205 SHA-2) | GPU attempts/s | useful comp/s ÷ E0 |
|---|---|---|---|---|
| WOTS+C | 1 | 1 | 1.35·10⁹ | 0.63 |
| FORS+C R-grind | 4 | **6** | 3.49·10⁸ | 0.97 |
| FORS+C ctr-grind | 4 | **3** | 7.25·10⁸ | 1.01 |
| PORS+FP | 4 | **7** | 1.81·10⁸ | 0.59 |

The model assumes a single-SHA-256 H_msg. FIPS 205's H_msg is nested (inner hash + MGF1) and PRF_msg is HMAC.
Two consequences:
- **Layout choice.** On the GPU, ctr-grind runs 2.08× more attempts per second than R-grind but stores a
  4-byte counter. This is a measurable design choice, not just a 4-byte question.
- **Kernel efficiency.** WOTS+C and PORS+FP kernels run at about 60 % of raw SHA throughput because of
  per-attempt digit and Octopus work. FORS+C runs at raw speed.

Re-priced full signing cost differs from the model by −1 % … +8 %.

### 4.3 Grinding is a minor part of signing

Mean grinding is 0–18 % of total signing work across all 49 point × layout rows; tree building dominates.
Even for the gpu_signer_max points (≈ 5–8·10⁸ compressions), the base cost is 86–90 % of the total. Two
consequences:
- the grind tail moves the full-signing p99 only slightly;
- the cost of the small "GPU-signer" sets is mainly larger hypertree layers (h/d = 16), not grinding.

Per signature, p99.9/mean of the grind ranges from 2.96 (several comparable WOTS+C layers, which concentrate)
to 7.1 (one dominant FTS grind). Kudinov–Nick's 2⁻³⁰ worst case is 6.3–20.9× the mean.

### 4.4 Latency per signer class (RQ2, OQ-1)

p99 full signing time = model base + measured grind, divided by the class rate:

| limit | profile | bytes | Cortex-M4 ᶜ | MCU+SHA ᶜ | Pi 5 ᶜ | i5 SHA-NI ᵐ | RTX 4050 ᵐ |
|---|---|---|---|---|---|---|---|
| 2²⁰ | hw_wallet_safe | 2876 | 2.7 min | 54 s | 88 ms | 28 ms | 3.0 ms |
| 2²⁰ | gpu_signer_moderate | 2504 | 24 min | 8.0 min | 0.78 s | 0.25 s | 27 ms |
| 2²⁰ | gpu_signer_max | 2280 | 6.1 h | 2.0 h | 12 s | 3.8 s | 0.41 s |
| 2³⁰ | hw_wallet_safe | 3456 | 2.2 min | 43 s | 70 ms | 22 ms | 2.4 ms |
| 2³⁰ | gpu_signer_moderate | 2908 | 20 min | 6.7 min | 0.65 s | 0.21 s | 22 ms |
| 2³⁰ | gpu_signer_max | 2664 | 6.3 h | 2.1 h | 12 s | 3.9 s | 0.42 s |
| 2⁴⁰ | hw_wallet_safe | 3944 | 2.8 min | 56 s | 90 ms | 29 ms | 3.1 ms |
| 2⁴⁰ | gpu_signer_moderate | 3216 | 35 min | 12 min | 1.1 s | 0.36 s | 39 ms |
| 2⁴⁰ | gpu_signer_max | 2892 | 8.0 h | 2.7 h | 16 s | 5.0 s | 0.54 s |

ᶜ cited/derived rate · ᵐ measured on the test laptop. Times assume perfect parallelism within a class (§7).

### 4.5 Frontier (RQ3, H2, OQ-2)

Fig. 2 (`pareto_p99.png`) plots bytes against p99 signing work per limit. Smallest shortlisted signature
within a p99 budget:

| limit | Cortex-M4, 120 s | MCU+SHA, 120 s | laptop CPU, 1 s | laptop CPU, 10 s | laptop GPU, 1 s |
|---|---|---|---|---|---|
| 2²⁰ | none ≤ 120 s | 2876 | 2504 | 2280 | 2280 |
| 2³⁰ | 3968 | 3424 | 2908 | 2664 | 2664 |
| 2⁴⁰ | none ≤ 120 s | 3944 | 3216 | 2892 | 2892 |

The GPU reaches the smallest shortlisted point at every budget. Because the shortlist caps signing at 2³⁰
compressions, the true GPU frontier lies further left, and the GPU savings are lower bounds.

### 4.6 Fees (RQ4)

Per input, against the hw_wallet_safe point of the same limit (BIP-360 P2MR, depth 1, 32-byte PQ key):

| limit | profile | Δbytes | ΔvB | Δsat @ 2 / 10 / 50 sat/vB | share of a 1-in/2-out tx |
|---|---|---|---|---|---|
| 2²⁰ | gpu_signer_moderate | −372 | −93 | −186 / −930 / −4,650 | −10.6 % |
| 2²⁰ | gpu_signer_max | −596 | −149 | −298 / −1,490 / −7,450 | −17.0 % |
| 2³⁰ | gpu_signer_moderate | −548 | −137 | −274 / −1,370 / −6,850 | −13.4 % |
| 2³⁰ | gpu_signer_max | −792 | −198 | −396 / −1,980 / −9,900 | −19.4 % |
| 2⁴⁰ | gpu_signer_moderate | −728 | −182 | −364 / −1,820 / −9,100 | −15.9 % |
| 2⁴⁰ | gpu_signer_max | −1,052 | −263 | −526 / −2,630 / −13,150 | −23.0 % |

### 4.7 Verification (H3) and energy (RQ5)

- **Verification.** In all 15 pairs that differ only in FTS compression, verification compressions fall by
  15–40. The gpu_signer points verify cheaper than the hw_wallet_safe points of the same limit (e.g. 2⁴⁰:
  5,893 vs. 10,026 compressions) because they have fewer, taller layers.
- **Energy.** Measured GPU energy is 20.8 nJ per raw compression. Per attempt: WOTS+C 27 nJ, ctr-grind 59 nJ,
  R-grind 124 nJ, PORS+FP 241 nJ. The largest GPU-signer signature costs about 18 J on the RTX 4050. Energy
  is not a constraint for desktop or GPU signers.

## 5. Discussion

**Design for 7× the mean, not the mean.** The tails are textbook geometric. A wallet UI should budget about
7× the mean grind (p99.9) and expose progress, not a fixed timeout at the mean. Because tree building
dominates, full signing time is much tighter than the grind tail; per-signature p99.9/mean of grinding alone
is 3–7.

**Two signer profiles are a real choice.** Between a hardware-wallet-safe and a GPU-signer set the gap is
596–1,052 B (17–23 % of a simple spend) at the limits studied. Even a laptop CPU at a 1 s budget gets
372–728 B of it. Maxwell's condition for more than one parameter set ("relative performance") is therefore
met with a large margin. Free configuration hurts privacy (RQ-40), which argues for exactly two named
profiles rather than a menu.

**Price attempts at FIPS 205 cost.** Cost tables that feed parameter selection should use 6 (R-grind) or 7
(PORS+FP) compressions per attempt, or state the non-FIPS H_msg they assume. For signers that store a
counter anyway, ctr-grind halves FORS+C grinding.

**Overgrinding (OQ-3).** Raising the WOTS+C target S trades signer work for verifier work at fixed size. At
w = 4, S = 96 → 128 removes a third of per-layer chain steps for about 650× more grinding (analytic).
**[TODO: measured sweep, `--extra oq3`, notebook 05.]**

## 6. Related work

- Kudinov–Nick 2025 (ePrint 2025/2203): parameters, analytic expected and 2⁻³⁰ costs; our baseline.
- Hülsing–Kudinov–Ronen–Yogev, SPHINCS+C: WOTS+C, FORS+C.
- Abri–Katz: PORS+FP.
- Fluhrer–Dang 2024/018: smaller SPHINCS+ without grinding; grinding buys ≈ 300 B at equal signing budget.
- The SHRINCS BIP draft: stateful + plain-SLH-DSA stateless path.
- Blockstream's 2026 hardware-wallet benchmarks: means on real devices; our tails complement them.

## 7. Threats to validity

Summarized from `kb/threats_to_validity.md`:
- **z = 1 security (open).** The z = 1 (forced zero chain) gpu_signer points have no analysed security impact
  in our model. They are reported as measured, not endorsed.
- **Our byte layouts.** Tries transfer to any author layout; per-attempt cost is reported for both readings
  of H_msg.
- **Modelled tree-building cost.** The base cost is modelled, not measured.
- **Cited ladder.** Four of six signer classes use cited rates; tries remain the primary, hardware-independent
  metric.
- **Parallelism assumption.** Throughput is assumed to equal latency within a class.
- **Small n.** Three configs have n = 2·10⁴.
- **Tail extrapolation.** The 2⁻³⁰ tail is extrapolated from the geometric form.
- **Hardware.** One laptop, one run.
- **Shortlist cap.** The cap makes GPU savings a lower bound.

## 8. Conclusion and artifacts

Grinding behaves exactly as modelled in tries, costs more per attempt than modelled under FIPS 205, and is a
minor part of signing. The signer's hardware budget is a first-order size lever: hundreds of bytes per input.
The PQ-signature BIP should state its signer assumption explicitly and consider two named parameter profiles.

**Artifacts.** `github.com/[TODO]/grindstone`: NVRTC kernels, SHA-NI grinder, Python reference, campaign
runner, notebooks, `python -m runner.reproduce`. Data under CC-BY-4.0, dataset SHA-256
`01e9fd2ca78f89e5c2525072705e8f32f42863054ffcbc7301341905bfe98d80`.

## References

[KN25] M. Kudinov, J. Nick. Hash-based Signature Schemes for Bitcoin. IACR ePrint 2025/2203.
[SPXC] A. Hülsing, M. Kudinov, E. Ronen, E. Yogev. SPHINCS+C: Compressing SPHINCS+ With (Almost) No Cost. ePrint 2022/778.
[FD24] S. Fluhrer, Q. Dang. Smaller SPHINCS+. ePrint 2024/018.
[FIPS205] NIST FIPS 205, Stateless Hash-Based Digital Signature Standard, 2024.
[BIP360] BIP-360 (P2MR), bitcoin/bips, merged 2026-02-11.
[SHRINCS] SHRINCS BIP draft, github.com/SHRINCS/shrincs-bip, commit 2d1679b.
[REPO] BlockstreamResearch/SPHINCS-Parameters, commit ceee8ed.
[AK] M. Abri, J. Katz. PORS+FP tooling, github.com/MehdiAbri/PORS-FP. **[TODO: paper citation]**
