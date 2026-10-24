"""Export campaign results for the website: site/content/data.json + copies of the paper drafts.

    python site/scripts/export_data.py        # from the grindstone repo root

Reads data/raw/<run>/ and analysis/out/ (run the notebooks first). The site never computes statistics
itself; every number it shows comes from this file.
"""
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
sys.path.insert(0, str(ROOT / "analysis"))
import common as C  # noqa: E402

RUN, OQ3, RERUN = C.RUN_ID, "oq3-eb65c6cd81a0", "rerun-ef62ccd1b407"
OUT = ROOT / "analysis" / "out"
RAW = ROOT / "data" / "raw"


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def jsonl(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return x
    return int(v) if v.is_integer() and abs(v) < 2**53 else v


summary = {r["config_id"]: r for r in jsonl(RAW / RUN / "summary.jsonl")}
validation = []
for r in rows(OUT / "01_validate" / "validation.csv"):
    s = summary[r["config_id"]]
    validation.append({
        "id": r["config_id"], "grind": r["grind"], "n": num(r["n"]), "expected": num(r["E_analytic"]),
        "ratio": num(r["ratio"]), "ci95": num(r["ci95_rel"]), "z": num(r["z"]), "ks_p_holm": num(r["ks_p_holm"]),
        "p99": s["p99"], "geo_p99": s["geo_p99"], "p999": s["p999"], "geo_p999": s["geo_p999"],
        "comp_per_s": s["comp_per_s"], "verified": s["verified_all"],
    })

rerun = jsonl(RAW / RERUN / "summary.jsonl")[0]
z_rerun = (rerun["ratio"] - 1) / (rerun["ci95_rel"] / 1.96)

oq3 = [{
    "id": r["config_id"], "w": num(r["w"]), "S": num(r["S"]), "expected": num(r["E_tries"]),
    "ratio": num(r["measured_ratio"]), "n": num(r["n"]), "chain_steps": num(r["verify_chain_steps"]),
    "saved": num(r["verify_saved_vs_mean_S"]), "run": r["run"],
    "p99_mcu": num(r["p99_s HW wallet MCU, software SHA (Cortex-M4)"]),
    "p99_cpu": num(r["p99_s i5-13420H SHA-NI, 12 threads"]),
} for r in rows(OUT / "05_oq3" / "oq3_sweep.csv")]

params = [{
    "id": r["param_id"], "layout": r["layout"], "profile": r["profile"], "variant": r["variant"],
    "limit": num(r["sig_limit"]), "bytes": num(r["sig_bytes"]), "total_p99": num(r["total_p99"]),
    "total_mean": num(r["total_mean"]), "grind_share": num(r["grind_share_mean"]),
    "verify_comp": num(r["verify_comp"]), "z1": "z1" in r["param_id"],
} for r in rows(OUT / "03_pareto" / "e4_sign_cost.csv")]

ladder = [{"id": cid, "label": r.label, "rate": float(r.comp_per_s), "kind": r.kind}
          for cid, r in C.ladder().iterrows()]

threats = []
for line in (ROOT / "kb" / "threats_to_validity.md").read_text(encoding="utf-8").split("## Summary", 1)[1].split("\n---")[0].splitlines():
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) == 4 and cells[0][:1].isdigit():
        threats.append(dict(zip(("id", "threat", "severity", "status"), cells)))

e5 = json.load(open(RAW / RUN / "e5.json", encoding="utf-8"))
e0 = json.load(open(RAW / RUN / "e0.json", encoding="utf-8"))
z2 = sum(v["z"] ** 2 for v in validation)

data = {
    "run": RUN, "oq3_run": OQ3, "rerun_run": RERUN,
    "headline": {
        "configs": len(validation), "samples": sum(v["n"] for v in validation),
        "sum_z2": z2, "dof": len(validation),
        "outside_ci": sum(abs(v["z"]) > 1.96 for v in validation),
        "gpu_raw": e0["median_last_2_3"],
        "cpu_12t": next(b["rate"] for b in e5["bench"] if b["threads"] == 12 and not b.get("warmup")),
        "cpu_1t": next(b["rate"] for b in e5["bench"] if b["threads"] == 1),
    },
    "rerun": {"id": rerun["config_id"], "n": rerun["n"], "ratio": rerun["ratio"], "ci95": rerun["ci95_rel"],
              "z": z_rerun, "verified": rerun["verified_all"]},
    "validation": validation, "oq3": oq3, "params": params, "ladder": ladder, "threats": threats,
    "fees": [{k: num(v) for k, v in r.items()} for r in rows(OUT / "04_fees_energy" / "fee_deltas.csv")],
}

(SITE / "content").mkdir(parents=True, exist_ok=True)
json.dump(data, open(SITE / "content" / "data.json", "w", encoding="utf-8"), indent=1)
for name in ("paper.md", "executive_summary.md"):
    shutil.copy(ROOT / "paper" / name, SITE / "content" / name)
shutil.copytree(ROOT / "paper" / "figures", SITE / "public" / "figures", dirs_exist_ok=True)
print(f"wrote site/content/data.json: {len(validation)} configs, {len(oq3)} oq3, {len(params)} params, "
      f"{len(ladder)} classes; sum z^2 = {z2:.1f}")
