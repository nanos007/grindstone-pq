"""Cells for 05_oq3_overgrinding.ipynb (OQ-3). Built by build_notebooks.py.

Uses the newest data/raw/oq3-* run if one exists (`python -m runner.run_campaign --extra oq3`); otherwise it
shows the analytic side only and says so."""

CELLS = [
("md", """# 05 — Overgrinding: signer work vs. verifier work at fixed size (OQ-3)

Kudinov asked (bitcoindev, 2025-12-09): *"would it be reasonable to choose larger signatures if they offer
lower verification costs?"* WOTS+C has a knob that trades signer work for verifier work **at the same size**:
the target digit sum S. The verifier walks (w−1)·len1 − S chain steps per layer, so raising S saves
verification and costs more grinding. Blockstream's HW-wallet benchmark moves S from 96 to 140 at w = 4.

Per layer, for w = 4 (len1 = 64) and w = 16 (len1 = 32): expected and measured tries, p99, verifier chain
steps, and signer p99 seconds on each class."""),
("code", """import sys; sys.path.insert(0, '.')
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import common as C
from runner.configs import EXTRA
OUT = C.out_dir('05_oq3')
runs = sorted(C.RAW.glob('oq3-*'), key=lambda p: p.stat().st_mtime)
RUN = runs[-1].name if runs and (runs[-1] / 'summary.jsonl').exists() else None
print('measured run:', RUN or 'none yet — analytic only (run: python -m runner.run_campaign --extra oq3)')
meas = C.summary(RUN) if RUN else None
# the shortlist's w=16 S=240/304 points from the main run complete the w=16 sweep
main = C.summary()"""),
("code", """rows = []
cfgs = EXTRA['oq3']()
extra_main = [c for c in ('wots-w16-S240-z0', 'wots-w16-S304-z0') if c in main.index]
for c in cfgs + [None] * len(extra_main):
    if c is None:
        cid = extra_main.pop(0); r = main.loc[cid]; w, S, E = int(r.w), int(r.S), r.expected_tries; src = C.RUN_ID
    else:
        cid, w, S, E = c.id, c.w, c.S, c.expected_tries()
        r = meas.loc[cid] if meas is not None and cid in meas.index else None; src = RUN if r is not None else None
    len1 = 128 // (w.bit_length() - 1)
    rows.append({'config_id': cid, 'w': w, 'S': S, 'E_tries': E, 'geo_p99': C.geometric_quantile(E, 0.99),
                 'measured_ratio': r.ratio if r is not None else np.nan,
                 'measured_p99': r.p99 if r is not None else np.nan, 'n': int(r.n) if r is not None else 0,
                 'verify_chain_steps': (w - 1) * len1 - S, 'run': src})
oq = pd.DataFrame(rows).sort_values(['w', 'S']).set_index('config_id')
for w, g in oq.groupby('w'):
    base = g.verify_chain_steps.iloc[0]
    oq.loc[g.index, 'verify_saved_vs_mean_S'] = 1 - g.verify_chain_steps / base
lad = C.ladder()
for cid in ('class0a', 'class0b', 'class2'):
    oq[f"p99_s {lad.loc[cid, 'label']}"] = oq.geo_p99 / lad.loc[cid, 'comp_per_s']
C.to_markdown(oq.round(4), OUT / 'oq3_sweep.md'); oq.to_csv(OUT / 'oq3_sweep.csv')
oq"""),
("code", """fig, ax = plt.subplots(figsize=(6.5, 3.8))
for w, g in oq.groupby('w'):
    ax.plot(g.verify_chain_steps, g.geo_p99, 'o-', label=f'w = {w} (analytic p99)')
    m = g.dropna(subset=['measured_p99'])
    if len(m): ax.plot(m.verify_chain_steps, m.measured_p99, 'kx', ms=6)
    for _, r in g.iterrows(): ax.annotate(f"S={r.S}", (r.verify_chain_steps, r.geo_p99), fontsize=6, xytext=(3, 3), textcoords='offset points')
ax.plot([], [], 'kx', label='measured p99')
ax.set_yscale('log'); ax.set_xlabel('verifier chain steps per WOTS+C layer'); ax.set_ylabel('signer p99 tries per layer')
ax.invert_xaxis(); ax.grid(alpha=0.25, which='both'); ax.legend(fontsize=8); fig.tight_layout()
fig.savefig(OUT / 'oq3_tradeoff.png', dpi=160)"""),
("md", """Reading (left to right = less verifier work): at w = 4, S 96 → 128 cuts per-layer verification by a third
for ≈ 650× more grinding (≈ 1.7 s p99 per layer on a Cortex-M4 at the cited 4·10⁴ comp/s). The last steps
(S ≥ 136) cost orders of magnitude more for little extra saving. Size is identical along each curve."""),
]
