# Threats to validity (Agent F, "Red Team")

Written 2026-10-24, after campaign run `196e7e91e907` and the analysis in `analysis/` (notebooks 01–04).
This file becomes paper §7. Each threat gets a **severity** for the paper's conclusions (High / Medium /
Low), the **evidence** we have, and its **status** (mitigated / disclosed / open).

The brief (plan §2, Agent F) asked three questions: is any grind condition security-relevant; are the
analytic models right and does the kernel implement the spec; are the hardware numbers cherry-picked. They
are §1, §2–3 and §5 below. The rest covers what a hostile reviewer would raise next.

## Summary

| # | Threat | Severity | Status |
|---|---|---|---|
| 1.1 | Grinding time leaks information about SK.prf (R-grind) | Low | disclosed; standard PRF argument |
| 1.2 | z = 1 (forced zero chain) at the GPU-signer points has no analysed security impact in our model | Medium | **open**; disclosed |
| 1.3 | Counter exhaustion makes signing fail | Low | mitigated (4-byte counter) |
| 2.1 | Our byte layouts are our own choices, not an author spec | Medium | disclosed; email to authors drafted, unsent |
| 2.2 | Cost model mis-prices FTS attempts (4 vs 6/3/7 compressions) | Medium | measured and reported (H1b) |
| 2.3 | Base (tree-building) signing cost is modelled, not measured | Medium | disclosed |
| 2.4 | R = 16 B (repo, FIPS 205) vs 32 B (paper tables) | Low | disclosed; both sizes in shortlist |
| 3.1 | GPU kernel bug produces "too good" numbers | Low | mitigated (E1 gate, full reference check, CPU match, means) |
| 3.2 | Minimal-counter property only spot-checked | Low | mitigated by means; disclosed |
| 4.1 | Three heavy PORS+FP configs have n = 2·10⁴ < 10⁵ | Low | disclosed; optional rerun |
| 4.2 | Multiple testing across 37 configs | Low | mitigated (Σz², Holm) |
| 4.3 | The 2⁻³⁰ worst case cannot be observed | Medium | disclosed; tail form tested to ~10⁻⁴ |
| 4.4 | Per-signature distributions are resampled, not measured end to end | Low | disclosed; independence holds by construction |
| 5.1 | Hardware ladder: 4 of 6 classes are cited/derived, not measured | Medium | disclosed; tries are the primary metric |
| 5.2 | Throughput ≠ single-signature latency | Medium | disclosed |
| 5.3 | One laptop, one run, 45 W power cap | Low | disclosed; conservative by design |
| 5.4 | Thermal / clock state during measurement | Low | mitigated (10 Hz telemetry) |
| 6.1 | Shortlist built by us; its caps truncate the GPU frontier | Medium | disclosed; savings are a lower bound |
| 6.2 | "hw_wallet_safe" / "gpu_signer" labels are our definitions | Low | disclosed |
| 7.1 | Fee model assumes a future opcode and P2MR depth 1 | Low | disclosed |
| 7.2 | Energy for non-GPU classes is estimated | Low | disclosed |
| 8.1 | Analysis designed after seeing the data | Low | thresholds pre-registered in plan §1.6 |
| 8.2 | Research inputs were compiled by LLM agents | Medium | claims carry sources; `verified_by_us` flags |

---

## 1. Is any grind condition security-relevant?

**1.1 Timing leaks the number of tries (Low).** Signing time is proportional to the number of tries, and an
observer can time a signer.
- **WOTS+C and FORS+C ctr-grind:** the winning counter is part of the signature anyway, so timing reveals nothing new.
- **R-grind (FORS+C, PORS+FP):** the index i of the winning R_i = PRF_msg(SK.prf, opt, M, i) is not in the
  signature. Timing reveals roughly how many PRF outputs failed the condition. Each failure is a fact about one
  PRF output, which is computationally independent of SK.prf as long as PRF_msg is a PRF.
- With hedged signing (fresh opt_rand), even that fact concerns a one-time input.

We consider the leak harmless but did not prove anything. We state it as an assumption and do not claim it as
a result. It is also not specific to our study: every grinding signer has it.

**1.2 z = 1 at the GPU-signer points (Medium, open).** The `gpu_signer_moderate` and `gpu_signer_max` points
(and both stress points) force one WOTS+C chain per layer to zero (z = 1, S = 1912), which saves 16 B per
layer. Sources:
- SPHINCS+C (Hülsing–Kudinov–Ronen–Yogev) defines forced-zero chains; we have not checked that its security argument covers this exact parameterization.
- Kudinov–Nick list them, but the SPHINCS-Parameters repo does not model z (claim B-022).
- The security bits in our shortlist come from the repo's FORS/PORS forgery model and do not include z.
- The two sources disagree on *which* chains (first vs. last z; ambiguity 2).

**Impact on conclusions:** the largest byte savings we report (H2, RQ4) rely partly on z = 1. The z = 0
`gpu_signer` alternatives are larger. Before the paper claims these sets as recommendations, the z = 1 security
argument needs a cryptographer's sign-off. Until then the paper must label them "measured, not endorsed".

**1.3 Counter exhaustion (Low).** We use a 4-byte counter, and the per-instance probability of exhausting it is
negligible: (1 − p)^(2³²) < e^(−340) even for the hardest grind (E[tries] = 1.26·10⁷).

SHRINCS's 16-bit WOTS+C counter would fail about 11 % of the time per layer at w = 256, S = 2840 (claim A-012).
Any profile with large S needs a wider counter, and the paper should say so.

## 2. Are the analytic models correct?

**2.1 Our byte layouts are our choices (Medium).** No public SHA-256 byte-level spec of FORS+C or PORS+FP
from the authors exists (ambiguity decisions 1–5, `kb/constructions/ambiguity_decisions.md`).
- Every choice was made to match FIPS 205 where it applies, and is marked [OUR CHOICE] there.
- **What depends on the choice:** test vectors and compressions per attempt. The number of tries does not,
  because a SHA-256 output behaves as random and the acceptance probability depends only on (w, S, z) or on
  (k, a, h, m_max).
- The measured tries match the analytic p in all 37 configs (RQ1). Tries therefore transfer to any author
  layout, and only the per-attempt pricing (§2.2) is layout-specific.
- The email to Kudinov and Nick (`kb/raw/A/email_draft.md`) asks exactly these questions. It has not been sent.

**2.2 Per-attempt cost (Medium, now a result).** `costs.sage` charges 4 compressions per FORS+C/PORS+FP
attempt. Under FIPS 205's SHA-2 H_msg (nested SHA-256 plus MGF1), the real counts are 6 for R-grind, 3 for
ctr-grind and 7 for PORS+FP with a 512-bit output.
- These were counted through the reference implementation (`tests/test_fors_c.py::test_compressions_per_attempt`)
  and are consistent with the measured GPU attempt rates (notebook 01, `layout_costs.md`).
- If the authors intended a single-SHA-256 H_msg, the repo's 4 is right for that variant. We report both.
- Re-priced full signing cost differs from the model by −1 % … +8 %.

**2.3 Base signing cost is modelled (Medium).** E4 adds the measured grind distribution to the cost model's
non-grinding work (tree building, leaves), i.e. `sign_compressions_cached` minus the model's grind term. We
did not implement full signing, so:
- the base cost, which is 82–100 % of total signing work, is not measured;
- the seconds per class assume tree building runs at the class's raw compression rate.

Tree building is embarrassingly parallel SHA-256 work, so this is plausible, but it is an assumption. The
paper must present full-signing seconds as "model + measured grind", not as measured end to end.

**2.4 R size (Low).** Paper Tables 1–2 use R = 32 B, while the repo HEAD and FIPS 205 use 16 B. The shortlist
stores both (`sig_bytes`, `sig_bytes_paper_r32`), and every size in our analysis is the R = 16 figure. Δ-bytes
between points are unaffected. Absolute sizes are 16 B below the paper's.

Also: the FORS+C ctr-grind layout stores a 4-byte counter. The analysis adds +4 B to those rows, and the
shortlist's `sig_bytes` do not include it.

## 3. Does the GPU kernel implement the spec?

**3.1 "Too good" numbers (Low, mitigated).** Four independent checks:
- **E1 correctness gate.** 10 configs at reduced difficulty, 10⁴ instances each. Every counter was re-ground by
  the pure-Python reference with a full minimality check, and the warp and block drivers agree bit for bit
  (`gate.json`: passed). The gate covers both WOTS+C digit widths, the zero mask, FORS+C masks inside one word
  and straddling words 3/4, and PORS+FP with non-power-of-two t.
- **Full reference check in the campaign.** Every one of the 11.16 M campaign counters was accepted by the
  reference (`verified_all`), and the first 32 instances per config were checked for minimality where
  E[tries] ≤ 2·10⁴.
- **Independent CPU implementation.** The CPU grinder (SHA-NI, separate code) reproduces the GPU counters
  bit for bit for all 7 WOTS+C configs (E5, 10⁴ instances each).
- **Statistics.** A kernel that skipped valid counters would inflate tries, and one that accepted invalid
  counters would be caught by the reference. The means match 1/p (max |Δ| = 1.66 %).

**3.2 Minimality spot-checked only (Low).** Full minimality was checked on the E1 gate and on 32-instance
prefixes. A kernel that sometimes returns a valid but non-minimal counter would bias tries upward, and §4
shows no such bias (Σz² = 39.6 on 37 dof). For FORS+C/PORS+FP, E5 has no independent CPU implementation; the
reference check covers acceptance.

## 4. Statistics

**4.1 n = 2·10⁴ for three heavy PORS+FP configs (Low).** These are `pors-k11-a10-h32-m68`,
`pors-k7-a19-h32-m96` and `pors-k9-a13-h48-m77`, below the plan's 10⁵ target (DoD §1.6).
- Their 95 % CIs are ±1.4 %, inside the 2 % DoD band.
- `pors-k9-a13-h48-m77` is the largest deviation (−1.66 %, z = −2.36).
- A rerun of that one config at 10⁵ (≈2.2 h GPU) would settle whether it is chance. It is optional, and the
  command is in the project README.

**4.2 Multiple testing (Low).** 37 configs × 3 tests. We report Σz² (p = 0.36), the count outside the 95 % CI
(2 vs. 1.9 expected), Holm-adjusted KS (0 rejections) and AD at 5 % (2 vs. 1.9 expected). No config is
singled out post hoc.

**4.3 The 2⁻³⁰ worst case is unobservable (Medium).**
- With ≤ 10⁶ samples per config, the empirical tail reaches P ≈ 10⁻⁶ for WOTS+C and ≈ 10⁻⁴…10⁻⁵ for FTS
  grinds. Beyond that the geometric form is an assumption.
- It is a strong one: independent trials of a hash that behaves as random are memoryless, and the data show no
  deviation in shape (KS, AD, normalized CCDF).
- Kudinov–Nick's "worst case" sums per-component 2⁻³⁰ bounds; it is not a joint bound (claim B-025). We quote
  it as the authors define it.

**4.4 Per-signature distributions are resampled (Low).** A signature's grind = d WOTS+C layers + one FTS
grind. We combine independently measured per-instance samples (bootstrap, 2·10⁵ draws). Independence holds by
construction: distinct ADRS per layer, distinct messages per instance, and instances derived from
SHA-256("grindstone" ‖ run_id ‖ i).

## 5. Hardware and measurement

**5.1 The ladder is mostly cited (Medium).**
- **Measured:** only class 2 (i5-13420H SHA-NI, E5 sustained 2.33·10⁸ comp/s) and class 3 (RTX 4050 Laptop
  @ 45 W, E0 sustained 2.15·10⁹ comp/s).
- **Derived or cited:** classes 0a/0b/0c/1a/1b/4, from `kb/hardware.yaml` with sources, low/typical/high
  ranges and confidence (several L).
- **Against cherry-picking:**
  - we use the *typical* value everywhere;
  - we keep the conflicting OpenBenchmarking RTX 4090 figure out (claim D-C036, 2× all hashcat runs);
  - we note that hashcat overstates full-compression rates by 5–15 % and that MCU figures exclude 10–30 %
    per-try overhead;
  - our own pre-measurement estimates were close: D-C038 predicted 1.3–2.0·10⁹ for the GPU (measured 2.15·10⁹,
    slightly above), and D-C039 predicted 1.0–2.3·10⁸ for the CPU (measured 2.33·10⁸).
- Because time = compressions ÷ rate, every table rescales linearly, and tries/compressions stay the primary,
  hardware-independent metric.

**5.2 Throughput ≠ latency (Medium).** Seconds per class assume one signature's work spreads across all cores
or GPUs at the batch rate. That holds for tree building and large grinds (E[tries] ≳ 10⁵ fills the GPU). It
breaks down in three places:
- small grinds on the GPU, where kernel-launch overhead (tens of µs; not measured here) dominates;
- the 8×4090 class, where splitting one signature across GPUs is assumed, not shown;
- the CPU at µs scale: E5 per-instance p99.9 for the 65-try grind is 2× the prediction (OS scheduling jitter).

Hardware-wallet conclusions are unaffected: MCUs are single-core and the work is minutes long.

**5.3 One machine, one run (Low).** All measurements come from one MSI Thin 15 at the 45 W TGP floor. This is
deliberately conservative for "heavy signer" claims: any desktop GPU is faster. Driver, CUDA, NVRTC and CuPy
versions are in `data/manifest.jsonl`. The campaign was interrupted once and resumed (2026-10-22 → 10-24).
Resumed configs are self-contained, so this affects only wall-clock bookkeeping.

**5.4 Thermals (Low, mitigated).** The 10 Hz telemetry shows the GPU at its 45 W software power cap (reason
0x4) for 99.98 % of busy samples. "SW thermal" (0x20) appears only in idle P-states between launches. E0
dipped to 1.73·10⁹ at its minimum, but its median over the last two-thirds of the run (2.15·10⁹) is what we
use.

## 6. Choice of parameter points

**6.1 Shortlist caps (Medium).** The 40-point shortlist (Agent B) caps grinds at ≤ 2²⁴ expected tries and
signing at ≤ 2³⁰ compressions so the campaign fits a night.
- For GPU-class signers every time budget reaches the smallest shortlisted point, so the true GPU frontier
  lies further left.
- The byte savings for heavy signers (H2, RQ4) are therefore a lower bound. Hardware-wallet conclusions are
  not affected by the cap.
- The shortlist header still says DRAFT; the freeze is recorded in `kb/params/FROZEN.md` (hash-pinned by
  the run manifest) and awaits owner sign-off.

**6.2 Profile labels are ours (Low).** "hw_wallet_safe" (every grind ≤ 2¹² tries), "gpu_signer_moderate" and
"gpu_signer_max" are our definitions. The community positions differ:
- Greg Maxwell: seconds per input on low-power devices is fine (RQ-02);
- Blockstream: a couple of minutes is fine for custody (RQ-05);
- SHRINCS: one parameter set only (RQ-41).

The paper presents budgets (1 / 10 / 120 / 600 s) rather than a single verdict.

## 7. Fees and energy

**7.1 Fee model (Low).** Our weight accounting assumes:
- BIP-360 P2MR depth 1, a 32-byte PQ pubkey, and a future OP_SUCCESSx-based opcode. Today's 520-byte element
  limit makes 2–5 kB signatures invalid in tapscript (E-006/E-007).
- No PQ witness discount (RQ-25, E-015).

Δ-vbytes between points are robust to all of these: 0.25 vB per signature byte.

**7.2 Energy (Low).** GPU energy integrates nvidia-smi board power, which excludes the rest of the laptop.
CPU energy is 45 W PL1 ÷ the measured rate, not a measurement. MCU and Pi energy come from cited typical
watts (confidence L). No conclusion in the paper depends on energy beyond "it is not a constraint for
desktop or GPU signers".

## 8. Process

**8.1 Analysis after data (Low).** The analysis code was written after the campaign finished. The acceptance
criteria were fixed earlier in plan §1.6 and the notebooks report them unchanged: mean within 2 % of analytic,
≥ 10⁵ samples, Blockstream rows reproduced to ±1 B. The tests (randomized PIT + KS/AD against the analytic p,
nothing fitted) are standard and have no tuning knobs.

**8.2 LLM-compiled research inputs (Medium).** Phase 2 inputs (agents A–E) were compiled by LLM research
agents. Mitigations:
- every claim carries a source URL, location, date and confidence (`kb/claims/all_claims.yaml`);
- numbers that feed the analysis were reproduced in code where possible: B-007 (all 30 table rows, 56 tests)
  and E-011/E-012 (mainnet tx weights);
- claims the campaign reproduced are flagged `verified_by_us: true`, and all others stay false.

Before publication, a human should spot-check the cited hardware figures (D-*) and the developer quotes (C-*),
which are not machine-verifiable.

## Must-fix before publishing

1. Get a security sign-off on z = 1, or demote the z = 1 points to "measured, not endorsed" (1.2).
2. Send the author email, or state the layout choices prominently (2.1).
3. Owner sign-off on the shortlist freeze record `kb/params/FROZEN.md` (6.1); the yaml itself stays byte-identical because the manifest pins its hash.
4. Human spot-check of the C-* quotes and D-* hardware figures (8.2).

Optional: rerun `pors-k9-a13-h48-m77` at n = 10⁵ (4.1).
