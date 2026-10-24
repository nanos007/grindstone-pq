# GRINDSTONE analysis (doc §4.5)

Analysis of campaign run `196e7e91e907` (37 grind configs, 11.16 M reference-verified samples, RTX 4050
Laptop @ 45 W, plus E5 CPU baseline on i5-13420H). CPU only; nothing here needs the GPU.

```
python analysis/build_notebooks.py          # rebuild + execute all four notebooks (~1 min)
python analysis/build_notebooks.py 03       # just one
```

`nb_*.py` hold the cells (source of truth, clean diffs); the `.ipynb` files are generated with outputs.
Shared loaders and conversions are in `common.py`. Every figure and table is written to `out/<notebook>/`
(PNG + SVG figures, Markdown + CSV tables).

| Notebook | Answers | Key outputs |
|---|---|---|
| `01_validate_vs_analytic` | RQ1, H1, H1b | `validation.md`, `forest_mean_ratio.png`, `layout_costs.md`, `power_windows.md` |
| `02_tails` | RQ2 | `quantiles.md`, `ccdf_normalized.png`, `signature_grind.md`, `grind_p999_seconds_by_class.md`, `e5_crosscheck.md` |
| `03_pareto` | E4, RQ3, H2, H3, OQ-2 | `e4_sign_cost.md`, `pareto_p99.png`, `smallest_per_budget.md`, `h3_pairs.md` |
| `04_fees_energy` | RQ4, RQ5 | `fee_deltas.md`, `gpu_energy_by_kind.md`, `joules_per_signature.md` |

## Headline results (2026-10-24)

**RQ1 — the analytic model holds.** All 37 means within 2 % of 1/p (max deviation −1.66 %,
`pors-k9-a13-h48-m77`, n = 2·10⁴). Σz² = 39.6 on 37 dof (p = 0.36); 2 configs outside their 95 % CI
(1.9 expected). KS on the randomized PIT against the *analytic* p: 0 rejections after Holm. Variance
ratios ≈ 1.

**H1 — tails are geometric.** p99/mean = 4.56–4.65 (theory 4.61), p99.9/mean = 6.73–7.05 (theory 6.91);
p99.9 within −2.2 % … +1.9 % of the geometric quantile. All configs collapse onto e^(−x) (`ccdf_normalized.png`).

**H1b — the cost model mis-prices FTS attempts.** costs.sage charges 4 compressions per FORS+C/PORS+FP
attempt. FIPS 205 SHA-2 instantiation: R-grind 6, ctr-grind 3, PORS+FP 7. On the GPU, ctr-grind runs
2.08× more attempts/s than R-grind (but stores a 4-byte counter). Re-priced full signing cost differs from
the model by −1 % … +8 %.

**E4 — grinding is a minor share of signing.** ≤ 18 % of mean signing work at every point; tree building
dominates. For the `gpu_signer_*` points, the base cost (~5·10⁸ compressions) is the larger part.

**RQ2/RQ3 — p99 full signing time (compressions ÷ class rate):**

| limit | profile | bytes | Cortex-M4 (cited) | MCU+SHA (cited) | Pi 5 (cited) | i5 SHA-NI (meas.) | RTX 4050 (meas.) |
|---|---|---|---|---|---|---|---|
| 2²⁰ | hw_wallet_safe | 2876 | 2.7 min | 54 s | 88 ms | 28 ms | 3.0 ms |
| 2²⁰ | gpu_signer_moderate | 2504 | 24 min | 8.0 min | 0.78 s | 0.25 s | 27 ms |
| 2²⁰ | gpu_signer_max | 2280 | 6.1 h | 2.0 h | 12 s | 3.8 s | 0.41 s |
| 2³⁰ | hw_wallet_safe | 3456 | 2.2 min | 43 s | 70 ms | 22 ms | 2.4 ms |
| 2³⁰ | gpu_signer_max | 2664 | 6.3 h | 2.1 h | 12 s | 3.9 s | 0.42 s |
| 2⁴⁰ | hw_wallet_safe | 3944 | 2.8 min | 56 s | 90 ms | 29 ms | 3.1 ms |
| 2⁴⁰ | gpu_signer_moderate | 3216 | 35 min | 12 min | 1.1 s | 0.36 s | 39 ms |
| 2⁴⁰ | gpu_signer_max | 2892 | 8.0 h | 2.7 h | 16 s | 5.0 s | 0.54 s |

A 10 s p99 budget on the measured laptop CPU already reaches the smallest shortlisted point at every
limit. The shortlist cap (grinds ≤ 2²⁴, signing ≤ 2³⁰) binds for GPU-class signers, so their real
frontier lies further left; measured savings are a lower bound there.

**H3 — verification never worse.** In all 15 (plain FORS → FORS+C/PORS+FP) pairs with otherwise equal
parameters, verification compressions go down.

**RQ4 — fees, per input vs. hw_wallet_safe (P2MR, 1-in/2-out):** 2²⁰: −596 B = −149 vB = −1,490 sat @10
sat/vB (−17 % of the tx); 2³⁰: −792 B = −198 vB (−19 %); 2⁴⁰ gpu_signer_max: −1,052 B = −263 vB =
−2,630 sat @10 sat/vB (−23 %); 2⁴⁰ gpu_signer_moderate: −728 B (−16 %).

**RQ5 — energy.** GPU measured: 20.8 nJ per raw compression; per attempt WOTS+C 27 nJ, ctr-grind 59 nJ,
R-grind 124 nJ, PORS+FP 241 nJ. Largest GPU-signer point ≈ 18 J per signature on the RTX 4050.

## Caveats to carry into threats_to_validity.md

- Classes 0a/0b/1b/4 use cited/derived rates from `kb/hardware.yaml`; only classes 2 and 3 are measured.
- Seconds assume the whole signature (trees + grinding) parallelizes across the class's cores/GPUs at the
  raw rate. Batch throughput ≠ single-signature latency for small grinds (GPU kernel-launch overhead, tens of µs, not measured).
  CPU per-instance p99.9 for the tiniest WOTS+C grind is 2× the prediction (OS jitter at µs scale).
- Base signing cost is the cost model's (minus its grind term), not measured.
- CPU energy uses 45 W PL1, not a power measurement.
- Three heavy PORS+FP configs have n = 2·10⁴ (< 10⁵ DoD target); their CI is ±1.4 %.
- Clock-event flags: 0x20 (SW thermal) only appears in idle P-states between launches; under load the
  GPU sits at the 45 W power cap (0x4) with 0.014 % of busy samples flagged.
