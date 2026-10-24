"""Cells for 02_tails.ipynb (RQ2, H1 tail form). Built by build_notebooks.py."""

CELLS = [
("md", """# 02 — Tail latency of grinding (RQ2)

1. Per grind config: empirical p50 / p90 / p99 / p99.9 tries vs. the geometric quantiles, and the
   tail-to-mean ratios a wallet must design for.
2. All configs on one scale: the CCDF of tries ÷ E[tries] collapses onto e^(−x) if H1 holds.
3. Per *signature*: d WOTS+C layers + one FORS+C / PORS+FP grind, by resampling the measured samples,
   converted to seconds on each signer class. Grinding only; full signing cost is in notebook 03."""),
("code", """import sys; sys.path.insert(0, '.')
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import common as C
OUT = C.out_dir('02_tails')
s = C.summary()
Q = [0.5, 0.9, 0.99, 0.999]"""),
("md", "## Per-config quantiles"),
("code", """rows = []
for cid, r in s.iterrows():
    e = r.expected_tries
    row = {'config_id': cid, 'grind': C.KIND_LABEL[r.kind], 'n': int(r.n), 'E': e, 'mean': r.mean_tries}
    for q, col in zip(Q, ['p50', 'p90', 'p99', 'p999']):
        row[col] = r[col]; row[col + '_vs_geo'] = r[col] / r['geo_' + col]
    row['p99_over_mean'] = r.p99 / r.mean_tries
    row['p999_over_mean'] = r.p999 / r.mean_tries
    row['max_over_mean'] = C.tries(cid).max() / r.mean_tries
    rows.append(row)
t = pd.DataFrame(rows).set_index('config_id')
print("geometric: p99/mean = ln(100) = 4.61, p99.9/mean = ln(1000) = 6.91")
print(t[['p99_over_mean', 'p999_over_mean']].describe().loc[['mean', 'min', 'max']].round(3))
print(f"p99.9 vs geometric quantile: {t.p999_vs_geo.min():.3f} .. {t.p999_vs_geo.max():.3f}")
C.to_markdown(t.round(4), OUT / 'quantiles.md'); t.to_csv(OUT / 'quantiles.csv')
t[['grind', 'n', 'E', 'p50_vs_geo', 'p90_vs_geo', 'p99_vs_geo', 'p999_vs_geo', 'p99_over_mean', 'p999_over_mean', 'max_over_mean']]"""),
("md", """The p99.9 sampling error is ≈ ±(1/√(n·0.001))/ln 1000 ≈ ±2 % at n = 10⁵ and ±5 % at n = 2·10⁴,
which covers the observed spread of `p999_vs_geo`."""),
("md", "## Normalized CCDF: one curve for every config"),
("code", """fig, ax = plt.subplots(figsize=(6.5, 4))
x = np.linspace(0, 14, 300)
for cid, r in s.iterrows():
    v = np.sort(C.tries(cid) / r.expected_tries)
    ccdf = 1 - np.arange(1, len(v) + 1) / len(v)
    k = slice(None, None, max(1, len(v) // 4000))
    ax.semilogy(v[k], ccdf[k], lw=0.7, alpha=0.5, color={'wots': '#2a6fdb', 'R': '#d9822b', 'ctr': '#7a5195', 'pors': '#2f9e44'}[r.kind])
ax.semilogy(x, np.exp(-x), 'k--', lw=1.2, label='geometric limit e^(−x)')
for q in (0.99, 0.999):
    ax.axhline(1 - q, color='0.6', lw=0.6); ax.text(13.8, (1 - q) * 1.15, f'p{100*q:g}', ha='right', fontsize=7)
for k, c in {'WOTS+C': '#2a6fdb', 'FORS+C R': '#d9822b', 'FORS+C ctr': '#7a5195', 'PORS+FP': '#2f9e44'}.items():
    ax.plot([], [], color=c, label=k)
ax.set_xlim(0, 14); ax.set_ylim(1e-6, 1); ax.set_xlabel('tries / analytic E[tries]'); ax.set_ylabel('P(T > t)')
ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(OUT / 'ccdf_normalized.png', dpi=160); fig.savefig(OUT / 'ccdf_normalized.svg')"""),
("md", """## Per-signature grind work

Resampled from the measured per-instance tries: n = 2·10⁵ synthetic signatures per point and layout.
Compressions use the counted per-attempt cost (WOTS+C 1, R-grind 6, ctr-grind 3, PORS+FP 7).
`model_worst_2^-30` is the Kudinov–Nick analytic worst case (sum of per-component bounds at q = 2⁻³⁰),
re-priced with the same per-attempt costs. Plain-FORS points (`wots_c+fors`) only grind WOTS+C."""),
("code", """from runner.configs import COMPRESSIONS
sl = C.shortlist()
rows, samples = [], {}
for pid, fcid, kind in C.point_layouts():
    pt = sl.loc[pid]
    w, f = C.signature_grind_samples(pid, fcid)
    comp = w + f * (COMPRESSIONS[kind] if kind else 0)
    samples[(pid, kind)] = (w, f, comp)
    worst = pt.model_wots_c_worst_2m30_all_layers + (pt.model_fts_worst_2m30 * COMPRESSIONS[kind] if kind else 0)
    q = np.quantile(comp, Q)
    rows.append({'param_id': pid, 'profile': pt.profile, 'layout': kind or '-', 'sig_limit': int(pt.sig_limit_log2),
                 'sig_bytes': int(pt.sig_bytes), 'grind_mean': comp.mean(), 'grind_p50': q[0], 'grind_p99': q[2],
                 'grind_p999': q[3], 'p999_over_mean': q[3] / comp.mean(), 'model_worst_2^-30': worst,
                 'worst_over_mean': worst / comp.mean(), 'wots_share_mean': w.mean() / comp.mean()})
sg = pd.DataFrame(rows).set_index(['param_id', 'layout'])
sg.to_csv(OUT / 'signature_grind.csv'); C.to_markdown(sg.round(3), OUT / 'signature_grind.md')
sg[['profile', 'sig_bytes', 'grind_mean', 'grind_p99', 'grind_p999', 'p999_over_mean', 'worst_over_mean', 'wots_share_mean']]"""),
("md", """`p999_over_mean` is below 6.9 for points where the grind is a *sum* of several comparable geometric
components (d WOTS+C layers + FTS): sums concentrate. It approaches 6.9 when one component dominates."""),
("md", "## Grinding time per signer class (p50 / p99 / p99.9)"),
("code", """lad = C.ladder()
m = C.measured_rates()
print(lad)
tt = {}
for (pid, kind), (w, f, comp) in samples.items():
    row = {}
    for cls, r in lad.iterrows():
        for q, lbl in ((0.5, 'p50'), (0.99, 'p99'), (0.999, 'p99.9')):
            row[(r.label, lbl)] = np.quantile(comp, q) / r.comp_per_s
    # GPU as actually measured: per-kernel attempt rates, not the raw E0 rate
    sec = w / m['gpu_effective']['wots'] + (f * COMPRESSIONS[kind] / m['gpu_effective'][kind] if kind else 0)
    for q, lbl in ((0.5, 'p50'), (0.99, 'p99'), (0.999, 'p99.9')):
        row[('RTX 4050 measured kernels', lbl)] = np.quantile(sec, q)
    tt[(pid, kind or '-')] = row
tt = pd.DataFrame(tt).T
tt.columns = pd.MultiIndex.from_tuples(tt.columns)
tt.index.names = ['param_id', 'layout']
tt.to_csv(OUT / 'grind_seconds_by_class.csv')
pretty = tt.xs('p99.9', axis=1, level=1).map(C.fmt_seconds)
pretty.insert(0, 'sig_bytes', sl.loc[pretty.index.get_level_values(0), 'sig_bytes'].to_numpy())
pretty.insert(1, 'profile', sl.loc[pretty.index.get_level_values(0), 'profile'].to_numpy())
C.to_markdown(pretty, OUT / 'grind_p999_seconds_by_class.md')
pretty"""),
("md", """Classes 0a/0b/1b/4 are *cited* rates (Agent D, `kb/hardware.yaml`), classes 2/3 are measured on the test
laptop (E5 sustained 12-thread, E0 sustained). Single-signature GPU latency equals batch throughput only
when one grind fills the GPU (E[tries] ≳ 10⁵); small grinds are bounded below by kernel-launch overhead (tens of µs, not measured here)."""),
("md", "## E5 cross-check: CPU per-instance seconds vs. tries ÷ rate"),
("code", """rows = []
for g in C.e5()['grind']:
    cid = g['config_id']
    d = pd.read_parquet(C.run_dir() / 'e5' / f'{cid}.parquet')
    tr = d.counter.to_numpy(np.float64) + 1
    rate1 = (tr.sum() / d.seconds.sum())  # attempts per second per thread
    rows.append({'config_id': cid, 'n': len(d), 'attempts_per_s_per_thread': rate1,
                 'attempts_per_s_12t': g['attempts_per_s'], 'sec_p99': g['sec_p99'], 'sec_p999': g['sec_p999'],
                 'pred_p99': np.quantile(tr, 0.99) / rate1, 'pred_p999': np.quantile(tr, 0.999) / rate1,
                 'gpu_over_cpu_attempts': s.loc[cid, 'attempts_per_s'] / g['attempts_per_s']})
e5t = pd.DataFrame(rows).set_index('config_id')
C.to_markdown(e5t, OUT / 'e5_crosscheck.md'); e5t"""),
("md", """Per-instance CPU times track tries ÷ per-thread rate, so the tries tables convert to time linearly.
For the small WOTS+C grinds the 12-thread attempt rate is below the raw SHA-NI rate (per-instance setup
dominates); for E[tries] ≳ 10³ it approaches it."""),
]
