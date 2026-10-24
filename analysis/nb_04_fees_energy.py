"""Cells for 04_fees_energy.ipynb (RQ4, RQ5). Built by build_notebooks.py."""

CELLS = [
("md", """# 04 — Fees (RQ4) and energy per signature (RQ5)

**Fees:** per signature limit, every shortlisted point against the `hw_wallet_safe` point as baseline:
Δbytes → ΔWU → ΔvB → Δsats per input at 2 / 10 / 50 sat/vB (`kb/fees.py`, BIP-360 P2MR script-path spend,
depth 1, 32-byte PQ pubkey). Signature bytes use R = 16 B.

**Energy:** GPU joules per attempt measured by integrating the 10 Hz board-power log over each config's kernel
window (includes launch gaps, so it is the real cost of a batch). Other classes: rate × typical power from
`kb/hardware.yaml` (estimates, labelled)."""),
("code", """import sys; sys.path.insert(0, '.')
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import common as C
from common import fees
from runner.configs import COMPRESSIONS
OUT = C.out_dir('04_fees_energy')
sl = C.shortlist()
e4 = pd.read_csv(C.OUT / '03_pareto' / 'e4_sign_cost.csv').set_index(['param_id', 'layout'])"""),
("md", "## Fee deltas vs. the hardware-wallet-safe point"),
("code", """rows = []
for L, g in sl.groupby('sig_limit_log2'):
    base_pid = g.index[g.profile == 'hw_wallet_safe'][0]
    base = int(g.loc[base_pid, 'sig_bytes'])
    for pid, pt in g.sort_values('sig_bytes').iterrows():
        r = fees.delta_table([int(pt.sig_bytes)], base)[0]
        rows.append({'sig_limit': f'2^{L}', 'param_id': pid, 'profile': pt.profile, 'sig_bytes': int(pt.sig_bytes),
                     'vs_hw_wallet_safe_B': base, 'd_bytes': r['d_bytes'], 'd_vB': r['d_vb'],
                     'd_sats@2': r['d_sats@2'], 'd_sats@10': r['d_sats@10'], 'd_sats@50': r['d_sats@50'],
                     'tx_vB_1in2out': r['tx_vsize_1in2out'], 'pct_of_tx': -r['d_vb'] / fees.tx_vbytes(1, 2, base) * 100})
fz = pd.DataFrame(rows)
C.to_markdown(fz, OUT / 'fee_deltas.md'); fz.to_csv(OUT / 'fee_deltas.csv', index=False)
key = fz[fz.profile.isin(['hw_wallet_safe', 'gpu_signer_moderate', 'gpu_signer_max'])]
key[['sig_limit', 'profile', 'sig_bytes', 'd_bytes', 'd_vB', 'd_sats@10', 'tx_vB_1in2out', 'pct_of_tx']]"""),
("md", """Negative Δ = saving per input versus the hardware-wallet-safe set. `pct_of_tx` is the saving as a share of a
1-input / 2-output P2MR spend with the baseline signature. Reference: the Kudinov–Nick 2²⁰ point (3,128 B with
R = 32, 3,112 B here) costs `fees.tx_vbytes(1, 2, 3112)` vB."""),
("code", """print('1-in/2-out P2MR spend, vB:', {b: fees.tx_vbytes(1, 2, b) for b in (2280, 2892, 3112, 3456, 3944, 64)})
fig, ax = plt.subplots(figsize=(6.5, 3.4))
cols = {'2^20': '#2a6fdb', '2^30': '#d9822b', '2^40': '#2f9e44'}
for L, g in fz.groupby('sig_limit'):
    ax.scatter(g.sig_bytes, g['d_sats@10'], color=cols[L], s=18, label=L)
ax.axhline(0, color='k', lw=0.7); ax.set_xlabel('signature bytes'); ax.set_ylabel('Δ sats per input @ 10 sat/vB\\n(vs hw_wallet_safe)')
ax.legend(fontsize=8); ax.grid(alpha=0.25); fig.tight_layout(); fig.savefig(OUT / 'fee_deltas.png', dpi=160)"""),
("md", "## GPU energy per attempt, measured"),
("code", """s = C.summary(); pw = C.power()
rows = []
for cid, r in s.iterrows():
    w = C.window(pw, r.start, r.end)
    if len(w) < 20: continue  # < 2 s of telemetry: too short to integrate
    J = C.energy_joules(w)
    tr = r.mean_tries * r.n
    rows.append({'config_id': cid, 'kind': r.kind, 'window_s': (r.end - r.start).total_seconds(), 'joules': J,
                 'mean_W': J / (r.end - r.start).total_seconds(), 'J_per_instance': J / r.n,
                 'nJ_per_attempt': J / tr * 1e9, 'nJ_per_compression': J / (tr * COMPRESSIONS[r.kind]) * 1e9})
cols_en = ['config_id', 'kind', 'window_s', 'joules', 'mean_W', 'J_per_instance', 'nJ_per_attempt', 'nJ_per_compression']
en = pd.DataFrame(rows, columns=cols_en).set_index('config_id')
by = en.groupby('kind')[['nJ_per_attempt', 'nJ_per_compression', 'mean_W']].median()
busy = pw[pw.power_w > 30].power_w.mean()
raw_nJ = busy / C.e0()['median_last_2_3'] * 1e9
print(f"configs with ≥ 2 s telemetry: {len(en)};  raw-SHA energy (busy power / E0 rate): {raw_nJ:.1f} nJ per compression")
C.to_markdown(en.round(3), OUT / 'gpu_energy_configs.md'); C.to_markdown(by.round(3), OUT / 'gpu_energy_by_kind.md')
# layouts without a long enough window (short runs) fall back to the raw-SHA figure x compressions per attempt
nj_attempt = lambda k: by.loc[k, 'nJ_per_attempt'] if k in by.index else raw_nJ * COMPRESSIONS[k]
by"""),
("md", """## Energy per signature, by signer class (mean signing work from notebook 03)

GPU grinding uses the measured nJ/attempt per layout; GPU tree building uses the raw-SHA figure. CPU uses the
45 W PL1 package power over the measured sustained rate (not a power measurement). Other classes from
`kb/hardware.yaml` (typical watts ÷ typical rate)."""),
("code", """hw = {c['id']: c for c in C.hardware()['classes']}
lad = C.ladder()
jpc = {}
for cid, r in lad.iterrows():
    if cid == 'class3':
        jpc[cid] = raw_nJ * 1e-9
    elif cid == 'class2':
        jpc[cid] = 45.0 / r.comp_per_s
    else:
        jpc[cid] = hw[cid]['watts']['typical'] / r.comp_per_s
rows = []
for (pid, lay), r in e4.iterrows():
    row = {'param_id': pid, 'layout': lay, 'profile': r.profile, 'sig_bytes': r.sig_bytes}
    for cid, lr in lad.iterrows():
        if cid == 'class3':
            g = r.grind_mean
            # split grind into WOTS+C and FTS parts priced at their measured per-attempt energy
            pt = sl.loc[pid]
            wots_part = pt.d * pt.model_wots_c_per_layer
            fts_part = max(g - wots_part, 0)
            J = r.base_comp * jpc[cid] + wots_part * nj_attempt('wots') * 1e-9
            if lay in COMPRESSIONS: J += fts_part / COMPRESSIONS[lay] * nj_attempt(lay) * 1e-9
        else:
            J = r.total_mean * jpc[cid]
        row[lr.label] = J
    rows.append(row)
ej = pd.DataFrame(rows).set_index(['param_id', 'layout'])
ej.to_csv(OUT / 'joules_per_signature.csv')
C.to_markdown(ej.round(4), OUT / 'joules_per_signature.md')
print(pd.Series(jpc, name='J per compression').map(lambda v: f'{v:.3g}'))
ej[ej.profile.isin(['hw_wallet_safe', 'gpu_signer_moderate', 'gpu_signer_max'])].round(3)"""),
("md", """At these magnitudes energy is not a constraint for any desktop/GPU signer (≲ 20 J for the largest GPU-signer
point, roughly a laptop running for half a second at 45 W). For MCU wallets the cost shows up as time, not as
battery: a few hundred joules at most for the hardware-wallet-safe points."""),
]
