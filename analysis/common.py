"""Shared loaders and conversions for the GRINDSTONE analysis notebooks (doc §4.5).

Everything reads a finished campaign directory, data/raw/<run_id>/, and the frozen inputs it
was run against (kb/params/shortlist_draft.yaml, kb/hardware.yaml). Nothing here touches the GPU.

Conventions
- "tries" is the primary, hardware-independent metric: attempts until the grind condition holds.
- "compressions" = tries x compressions per attempt for that grind layout (runner.configs.COMPRESSIONS:
  WOTS+C 1, FORS+C R-grind 6, FORS+C ctr-grind 3, PORS+FP 7).
- Seconds on a hardware class = compressions / that class's compressions per second. Our own two
  classes (RTX 4050 Laptop @ 45 W, i5-13420H SHA-NI) are measured; all others are cited (Agent D)
  and always labelled as such.
"""
import json
import os
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kb import fees  # noqa: E402
from runner.configs import COMPRESSIONS  # noqa: E402

PUBLISHED_RUN = "196e7e91e907"
# GRINDSTONE_RUN points the notebooks at another run (e.g. a `reproduce` smoke run); its outputs then go to
# analysis/out_<run>/ so the published figures stay untouched.
RUN_ID = os.environ.get("GRINDSTONE_RUN", PUBLISHED_RUN)
RAW = ROOT / "data" / "raw"
OUT = ROOT / "analysis" / ("out" if RUN_ID == PUBLISHED_RUN else f"out_{RUN_ID}")
SHORTLIST = ROOT / "kb" / "params" / "shortlist_draft.yaml"
HARDWARE = ROOT / "kb" / "hardware.yaml"

KIND_LABEL = {"wots": "WOTS+C", "R": "FORS+C (R-grind)", "ctr": "FORS+C (ctr-grind)", "pors": "PORS+FP"}
MODEL_COMPRESSIONS_PER_FTS_ATTEMPT = 4  # costs.sage: C_Hmsg + C_PRFmsg


def run_dir(run_id=RUN_ID):
    return RAW / run_id


def out_dir(name):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- campaign data

@lru_cache(None)
def configs(run_id=RUN_ID):
    """One row per grind config, as planned (configs.json)."""
    df = pd.DataFrame(json.loads((run_dir(run_id) / "configs.json").read_text()))
    return df.set_index("config_id")


@lru_cache(None)
def summary(run_id=RUN_ID):
    """Per-config summary written by the runner, joined with the plan."""
    rows = [json.loads(l) for l in (run_dir(run_id) / "summary.jsonl").read_text().splitlines() if l]
    s = pd.DataFrame(rows).set_index("config_id")
    for col in ("start", "end"):
        s[col] = pd.to_datetime(s[col].map(lambda d: d["local"]))
    c = configs(run_id)
    s = s.join(c[["kind", "component", "w", "S", "z", "k", "a", "h", "m_max", "compressions_per_attempt"]])
    s["z_score"] = (s.ratio - 1) / (s.ci95_rel / 1.96)
    return s


def tries(config_id, run_id=RUN_ID):
    return pd.read_parquet(run_dir(run_id) / f"{config_id}.parquet", columns=["tries"]).tries.to_numpy(np.int64)


@lru_cache(None)
def e0(run_id=RUN_ID):
    return json.loads((run_dir(run_id) / "e0.json").read_text())


@lru_cache(None)
def e5(run_id=RUN_ID):
    return json.loads((run_dir(run_id) / "e5.json").read_text())


@lru_cache(None)
def power(run_id=RUN_ID):
    files = sorted(run_dir(run_id).glob("power-*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True).sort_values("timestamp")


def window(df, t0, t1):
    return df[(df.timestamp >= t0) & (df.timestamp <= t1)]


def energy_joules(p):
    dt = p.timestamp.diff().dt.total_seconds().fillna(0).clip(upper=1.0)  # don't bridge log gaps
    return float((p.power_w * dt).sum())


# ---------------------------------------------------------------- statistics

def geometric_pit(t, p, rng):
    """Randomized probability integral transform: uniform on (0,1) iff t ~ Geometric(p) on {1,2,...}."""
    t = np.asarray(t, np.float64)
    lo = -np.expm1((t - 1) * np.log1p(-p))  # F(t-1)
    hi = -np.expm1(t * np.log1p(-p))        # F(t)
    return lo + rng.random(len(t)) * (hi - lo)


def geometric_tests(t, expected, seed=0):
    """KS and Anderson-Darling on the randomized PIT against the *analytic* p = 1/E (no fitting)."""
    rng = np.random.default_rng(seed)
    u = geometric_pit(t, 1.0 / expected, rng)
    ks = stats.kstest(u, "uniform")
    return {"ks_stat": float(ks.statistic), "ks_p": float(ks.pvalue), "ad_stat": anderson_darling_uniform(u)}


# fully specified null (no estimated parameters): 5% and 1% critical values of A^2
AD_CRIT_5PCT, AD_CRIT_1PCT = 2.492, 3.857


def anderson_darling_uniform(u):
    """A^2 against U(0,1); weights the tails more than KS, which is where wallet timeouts live."""
    u = np.clip(np.sort(u), 1e-300, 1 - 1e-16)
    n = len(u)
    i = np.arange(1, n + 1)
    return float(-n - np.mean((2 * i - 1) * (np.log(u) + np.log1p(-u[::-1]))))


def holm(pvals):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(p) - rank) * p[i]))
        adj[i] = running
    return adj


def geometric_quantile(e, q):
    p = 1.0 / e
    return float(np.ceil(np.log1p(-q) / np.log1p(-p)))


# ---------------------------------------------------------------- parameter points

@lru_cache(None)
def shortlist():
    d = yaml.safe_load(SHORTLIST.read_text(encoding="utf-8"))
    pts = pd.DataFrame(d["points"]).set_index("param_id")
    t = pd.json_normalize(pts.pop("tries").tolist()).set_index(pts.index)
    return pts.join(t.add_prefix("model_"))


def point_configs(run_id=RUN_ID):
    """param_id -> {'wots': config_id, 'fts': [config_ids]} (FORS+C points get both layouts)."""
    out = {}
    for cid, row in configs(run_id).iterrows():
        for pid in row.param_ids:
            e = out.setdefault(pid, {"wots": None, "fts": []})
            if row.kind == "wots":
                e["wots"] = cid
            else:
                e["fts"].append(cid)
    return out


def base_compressions(pt):
    """Signing compressions excluding grinding: the model total minus the model's grind term
    (WOTS+C: d * ceil(1/p) x 1; FORS+C / PORS+FP: tries x 4)."""
    wots = pt.d * np.ceil(pt.model_wots_c_per_layer)
    if pt.variant == "wots_c+fors_c":
        fts = pt.model_fors_c * MODEL_COMPRESSIONS_PER_FTS_ATTEMPT
    elif pt.variant == "wots_c+pors_fp":
        fts = np.ceil(pt.model_pors_fp) * MODEL_COMPRESSIONS_PER_FTS_ATTEMPT
    else:
        fts = 0
    return float(pt.sign_compressions_cached - wots - fts)


def signature_grind_samples(pid, fts_cid=None, n=200_000, seed=1, run_id=RUN_ID):
    """Empirical per-signature grind work, by resampling the measured per-instance samples:
    d independent WOTS+C layers + one FORS+C/PORS+FP grind (layers and messages are independent).
    Returns (WOTS+C tries summed over the d layers, FORS+C/PORS+FP tries or zeros), int64 arrays."""
    pt = shortlist().loc[pid]
    pc = point_configs(run_id)[pid]
    rng = np.random.default_rng(seed)
    w = tries(pc["wots"], run_id)
    wots = rng.choice(w, size=(n, int(pt.d))).sum(axis=1)
    fts = rng.choice(tries(fts_cid, run_id), size=n) if fts_cid else np.zeros(n, np.int64)
    return wots, fts


def point_layouts(run_id=RUN_ID):
    """(param_id, fts config_id or None, layout kind or None) for every shortlist point × grind layout."""
    c = configs(run_id)
    out = []
    for pid, pc in point_configs(run_id).items():
        for cid in pc["fts"] or [None]:
            out.append((pid, cid, c.loc[cid, "kind"] if cid else None))
    return sorted(out, key=lambda r: (shortlist().loc[r[0], "sig_limit_log2"], r[0], str(r[2])))


# ---------------------------------------------------------------- hardware ladder

@lru_cache(None)
def hardware():
    return yaml.safe_load(HARDWARE.read_text(encoding="utf-8"))


def measured_rates(run_id=RUN_ID):
    """Our two measured classes, in raw compressions/s, plus per-layout effective GPU rates."""
    s = summary(run_id)
    bench = {(b["threads"], b.get("warmup", False)): b["rate"] for b in e5(run_id)["bench"]}
    gpu_eff = s.groupby("kind").comp_per_s.median().to_dict()
    return {
        "gpu_raw_sustained": e0(run_id)["median_last_2_3"],
        "gpu_effective": gpu_eff,  # useful compressions/s inside each grind kernel
        "cpu_1t": bench[(1, False)],
        "cpu_12t_sustained": bench[(12, False)],
        "cpu_12t_burst": bench[(12, True)],
    }


def ladder(run_id=RUN_ID):
    """Signer classes for time conversion: id, label, compressions/s (typical), kind (measured/cited/derived)."""
    m = measured_rates(run_id)
    hw = {c["id"]: c for c in hardware()["classes"]}
    rows = [
        ("class0a", "HW wallet MCU, software SHA (Cortex-M4)", hw["class0a"]["compressions_per_sec"]["typical"], hw["class0a"]["kind"]),
        ("class0b", "HW wallet MCU + SHA peripheral", hw["class0b"]["compressions_per_sec"]["typical"], hw["class0b"]["kind"]),
        ("class1b", "Raspberry Pi 5 (ARMv8 SHA2)", hw["class1b"]["compressions_per_sec"]["typical"], hw["class1b"]["kind"]),
        ("class2", "i5-13420H SHA-NI, 12 threads", m["cpu_12t_sustained"], "measured"),
        ("class3", "RTX 4050 Laptop @ 45 W", m["gpu_raw_sustained"], "measured"),
        ("class4", "8x RTX 4090 server", hw["class4"]["compressions_per_sec"]["typical"], hw["class4"]["kind"]),
    ]
    return pd.DataFrame(rows, columns=["class_id", "label", "comp_per_s", "kind"]).set_index("class_id")


# ---------------------------------------------------------------- formatting

def fmt_seconds(s):
    if not np.isfinite(s):
        return "-"
    for unit, k in (("d", 86400), ("h", 3600), ("min", 60), ("s", 1), ("ms", 1e-3), ("µs", 1e-6)):
        if s >= k:
            return f"{s / k:.3g} {unit}"
    return f"{s * 1e9:.3g} ns"


def to_markdown(df, path=None, floatfmt=".4g"):
    """GitHub table without the tabulate dependency."""
    df = df.reset_index() if df.index.name or not isinstance(df.index, pd.RangeIndex) else df
    cell = lambda v: format(v, floatfmt) if isinstance(v, (float, np.floating)) else str(v)
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in df.itertuples(index=False)]
    md = "\n".join(lines)
    if path:
        Path(path).write_text(md + "\n", encoding="utf-8")
    return md
