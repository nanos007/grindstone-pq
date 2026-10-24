"""GRINDSTONE campaign: E0 calibration, E1 correctness gate, E2/E3 grind distributions, E5 CPU
baseline, with E6 power logging throughout (doc §4.3).

    python -m runner.run_campaign --smoke            # ~5 min end-to-end check, tiny sample counts
    python -m runner.run_campaign                    # full campaign
    python -m runner.run_campaign --resume <run_id>  # continue an interrupted run
    python -m runner.run_campaign --extra oq3        # add-on config set (runner.configs.EXTRA)
    python -m runner.run_campaign --only pors-k9-a13-h48-m77 --n 100000   # rerun configs at a new n

Everything lands in data/raw/<run_id>/: one Parquet per config (append-only; a finished config is
skipped on resume), summary.jsonl, gate.json, e0/e5 results, launch traces and power logs.
The run stops if E1 fails or any GPU counter is rejected by the reference.
"""
import argparse
import ctypes
import json
import os
import subprocess
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from grind import gpu
from runner import instances as inst
from runner.configs import COMPRESSIONS, EXTRA, GATE, ROOT, from_shortlist, shortlist_sha256
from runner.power_logger import PowerLogger

DATA = ROOT / "data"
MANIFEST = DATA / "manifest.jsonl"

# samples per config (doc §1.6: ≥ 1e5); PORS+FP points with E[tries] > 1e6 get fewer to fit a night
N_WOTS, N_FORS, N_PORS, N_PORS_HEAVY = 1_000_000, 200_000, 100_000, 20_000
N_GATE = 10_000
FULL_CHECK_N, FULL_CHECK_MAX_E = 32, 20_000  # re-grind a prefix of instances with the reference
E0_SECONDS = 600
CPU_N = 10_000
# rough useful compressions/s at 45 W, for the ETA only
RATE = {"wots": 1.4e9, "R": 2.2e9, "ctr": 2.3e9, "pors": 1.1e9}


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Log:
    def __init__(self, path):
        self.path = path

    def __call__(self, msg):
        line = f"[{datetime.now():%H:%M:%S}] {msg}"
        print(line, flush=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def keep_awake():
    if os.name == "nt":  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED: no sleep while the campaign runs
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)


def manifest(kind, run_id, **extra):
    from env import check_env
    rec = {"kind": kind, "run_id": run_id, "utc": utc(), **extra}
    if kind == "campaign_start":
        rec.update(check_env.gpu_info())
        rec.update(check_env.cpu_info())
        rec.update(check_env.os_info())
        git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        rec["git_sha"] = git("rev-parse", "HEAD")
        rec["git_dirty"] = bool(git("status", "--porcelain"))
        rec["shortlist_sha256"] = shortlist_sha256()
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def eta_s(cfg):
    return cfg.n * cfg.expected_tries() * COMPRESSIONS[cfg.kind] / RATE[cfg.kind]


def plan(smoke, extra=None, only=None, n=None):
    if extra:
        cfgs = EXTRA[extra]()  # sample counts set by the add-on itself
    else:
        cfgs = from_shortlist()
        for c in cfgs:
            if c.kind == "wots":
                c.n = N_WOTS
            elif c.kind in ("R", "ctr"):
                c.n = N_FORS
            else:
                c.n = N_PORS_HEAVY if c.expected_tries() > 1e6 else N_PORS
    if only:
        missing = set(only) - {c.id for c in cfgs}
        if missing:
            raise SystemExit(f"unknown config ids: {sorted(missing)}")
        cfgs = [c for c in cfgs if c.id in only]
    for c in cfgs:
        if n:
            c.n = n
        if smoke:
            c.n = max(c.n // 1000, 20)
    return sorted(cfgs, key=eta_s)


# ---------------------------------------------------------------- instances

def build(run_id, cfg, n):
    """(materials, GPU records) for instances 0..n-1 of cfg."""
    if cfg.kind == "wots":
        mat = inst.wots_materials(run_id, cfg.id, 0, n)
        return mat, inst.wots_records(mat)
    msgs = inst.fors_msgs(run_id, cfg.id, 0, n)
    return msgs, inst.fors_records(run_id, cfg, msgs)


def grinder(cfg, group=None):
    group = group or cfg.group
    if cfg.kind == "wots":
        return gpu.wots_grinder(cfg.wots_params, inst.CTR_OFF, group=group)
    return gpu.fors_grinder(cfg.kind, cfg.k, cfg.a, cfg.h, cfg.m_max, group=group)


def check(pool, run_id, cfg, mat, counters, idx, full):
    """Indices whose GPU counter the reference rejects (or, if full, that are not minimal)."""
    idx = list(idx)
    chunk = max(1, min(2000, len(idx) // (4 * (os.cpu_count() or 1)) + 1))
    if cfg.kind == "wots":
        p = cfg.wots_params
        jobs = ((inst.wots_rows(mat, counters, idx[i:i + chunk]), p, full) for i in range(0, len(idx), chunk))
        fn = inst.wots_check
    else:
        key = inst.fors_key(run_id, cfg.id)
        jobs = (([(j, mat[j], int(counters[j])) for j in idx[i:i + chunk]], cfg, key, full)
                for i in range(0, len(idx), chunk))
        fn = inst.fors_check
    bad = []
    window = []
    for job in jobs:  # bounded submission window keeps 1e6-row checks out of memory
        window.append(pool.submit(fn, job))
        if len(window) >= 64:
            bad += window.pop(0).result()
    for f in window:
        bad += f.result()
    return bad


# ---------------------------------------------------------------- experiments

def e0(out, log, seconds):
    log(f"E0: raw single-block SHA-256 for {seconds} s")
    r = gpu.bench_raw(seconds)
    df = pd.DataFrame(r, columns=["t_s", "comp_per_s"])
    df.to_parquet(out / "e0.parquet", index=False)
    tail = df[df.t_s > seconds / 3]
    res = {"median": float(df.comp_per_s.median()), "median_last_2_3": float(tail.comp_per_s.median()),
           "min": float(df.comp_per_s.min()), "max": float(df.comp_per_s.max()), "launches": len(df)}
    (out / "e0.json").write_text(json.dumps(res, indent=2))
    log(f"E0: median {res['median']/1e9:.3f} Gcomp/s, sustained (last 2/3) {res['median_last_2_3']/1e9:.3f}")


def e1(out, log, pool, run_id, n):
    log(f"E1: correctness gate, {n} instances per config, warp and block drivers vs reference")
    results, ok = [], True
    for cfg in GATE:
        cfg.n = n
        t0 = time.time()
        mat, recs = build(run_id, cfg, n)
        counters = {}
        for group in ("w32", "blk"):
            counters[group] = grinder(cfg, group).run(lambda i0, k: recs[i0:i0 + k], n)
        same = bool(np.array_equal(counters["w32"], counters["blk"]))
        bad = check(pool, run_id, cfg, mat, counters["w32"], range(n), full=True)
        tries = counters["w32"].astype(np.float64) + 1
        r = {"config_id": cfg.id, "n": n, "w32_eq_blk": same, "ref_mismatches": len(bad),
             "first_bad": bad[:5], "mean_tries": float(tries.mean()), "expected_tries": cfg.expected_tries(),
             "seconds": round(time.time() - t0, 1)}
        results.append(r)
        ok &= same and not bad
        log(f"  {cfg.id:<28} {'PASS' if same and not bad else 'FAIL'}  mean {r['mean_tries']:.1f} "
            f"(analytic {r['expected_tries']:.1f})  {r['seconds']} s")
    (out / "gate.json").write_text(json.dumps({"passed": ok, "utc": utc(), "configs": results}, indent=2))
    return ok


def summarize(cfg, tries, kernel_s):
    e = cfg.expected_tries()
    n = len(tries)
    mean = float(tries.mean())
    q = np.quantile(tries, [0.5, 0.9, 0.99, 0.999])
    p = 1 / e
    geo = lambda qq: float(np.ceil(np.log1p(-qq) / np.log1p(-p)))  # geometric quantile
    return {"config_id": cfg.id, "n": n, "expected_tries": e, "mean_tries": mean, "ratio": mean / e,
            "ci95_rel": float(1.96 * tries.std(ddof=1) / mean / np.sqrt(n)) if n > 1 else None,
            "p50": float(q[0]), "p90": float(q[1]), "p99": float(q[2]), "p999": float(q[3]),
            "geo_p50": geo(0.5), "geo_p90": geo(0.9), "geo_p99": geo(0.99), "geo_p999": geo(0.999),
            "kernel_s": kernel_s, "attempts_per_s": float(tries.sum() / kernel_s),
            "comp_per_s": float(tries.sum() * COMPRESSIONS[cfg.kind] / kernel_s)}


def run_config(out, log, pool, run_id, cfg):
    t_build = time.time()
    mat, recs = build(run_id, cfg, cfg.n)
    g = grinder(cfg)
    trace = []
    last = [time.time()]
    started = {"utc": utc(), "local": datetime.now().isoformat()}
    log(f"{cfg.id}: n={cfg.n:,} group={cfg.group} E[tries]={cfg.expected_tries():,.0f} "
        f"(inputs built in {time.time() - t_build:.1f} s, est. {eta_s(cfg)/60:.1f} min)")

    def progress(done, total):
        now = time.time()
        trace.append((now, g.kernel_ms, g.launches, g.budget, done))
        if now - last[0] > 60:
            last[0] = now
            log(f"  {cfg.id}: {done:,}/{total:,} ({100 * done / total:.1f}%)")

    counters = g.run(lambda i0, k: recs[i0:i0 + k], cfg.n, on_progress=progress)
    ended = {"utc": utc(), "local": datetime.now().isoformat()}

    failed = int((counters == gpu.FAILED).sum())
    bad = check(pool, run_id, cfg, mat, counters, range(cfg.n), full=False)
    full_n = FULL_CHECK_N if cfg.expected_tries() <= FULL_CHECK_MAX_E else 0
    bad += check(pool, run_id, cfg, mat, counters, range(min(full_n, cfg.n)), full=True)
    if failed or bad:
        raise RuntimeError(f"{cfg.id}: {failed} FAILED, {len(bad)} rejected by reference: {sorted(set(bad))[:10]}")

    tries = counters.astype(np.uint64) + 1
    kernel_ns = g.kernel_ms * 1e6
    df = pd.DataFrame({
        "run_id": run_id, "config_id": cfg.id, "component": cfg.component, "layout": cfg.kind,
        "instance_seed": np.arange(cfg.n, dtype=np.uint64), "tries": tries,
        "counter": counters.astype(np.uint64),
        "gpu_ns": (kernel_ns * tries / tries.sum()).astype(np.uint64),  # batch-amortized
    })
    (out / "trace").mkdir(exist_ok=True)
    pd.DataFrame(trace, columns=["wall_t", "kernel_ms_cum", "launch", "budget", "done"]) \
        .to_parquet(out / "trace" / f"{cfg.id}.parquet", index=False)
    s = summarize(cfg, tries.astype(np.float64), g.kernel_ms / 1e3)
    s.update(group=cfg.group, launches=g.launches, start=started, end=ended,
             verified_all=True, full_ref_checked=min(full_n, cfg.n))
    with (out / "summary.jsonl").open("a") as f:
        f.write(json.dumps(s) + "\n")
    df.to_parquet(out / f"{cfg.id}.parquet", index=False)  # written last: marks the config done
    log(f"  {cfg.id}: mean {s['mean_tries']:,.1f} / analytic {s['expected_tries']:,.1f} = {s['ratio']:.4f} "
        f"(+/-{100 * s['ci95_rel']:.2f}%), p99.9 {s['p999']:,.0f} vs geo {s['geo_p999']:,.0f}, "
        f"{s['comp_per_s']/1e9:.2f} Gcomp/s, {s['kernel_s']:.0f} s")


def e5(out, log, run_id, cfgs, n, bench_s):
    from grind import cpu
    log("E5: CPU SHA-NI baseline (GPU idle)")
    res = {"bench": []}
    for threads, secs in ((1, bench_s[0]), (12, bench_s[1]), (12, bench_s[2])):
        r = cpu.bench(threads, secs)
        res["bench"].append(r)
        log(f"  bench {threads:>2} threads {secs:>4} s: {r['rate']/1e6:.1f} Mcomp/s")
    res["bench"][1]["warmup"] = True  # PL2 burst: the second 12-thread run is the sustained figure
    res["grind"] = []
    for cfg in (c for c in cfgs if c.kind == "wots"):
        k = min(n, cfg.n)
        mat, recs = build(run_id, cfg, k)
        c, secs, wall = cpu.grind_wots_c(recs[:, :8], recs[:, 8:], inst.CTR_OFF, cfg.wots_params, threads=12)
        gpu_c = pd.read_parquet(out / f"{cfg.id}.parquet", columns=["counter"]).counter.to_numpy()[:k]
        match = bool(np.array_equal(c.astype(np.uint64), gpu_c))
        tries = c.astype(np.float64) + 1
        r = {"config_id": cfg.id, "n": k, "threads": 12, "wall_s": wall, "mean_tries": float(tries.mean()),
             "attempts_per_s": float(tries.sum() / wall), "matches_gpu": match,
             "sec_p50": float(np.median(secs)), "sec_p99": float(np.quantile(secs, 0.99)),
             "sec_p999": float(np.quantile(secs, 0.999))}
        res["grind"].append(r)
        (out / "e5").mkdir(exist_ok=True)
        pd.DataFrame({"config_id": cfg.id, "instance_seed": np.arange(k, dtype=np.uint64),
                      "counter": c.astype(np.uint64), "seconds": secs}) \
            .to_parquet(out / "e5" / f"{cfg.id}.parquet", index=False)
        log(f"  {cfg.id}: {r['attempts_per_s']/1e6:.0f} Mattempts/s, matches GPU: {match}")
        if not match:
            raise RuntimeError(f"E5 {cfg.id}: CPU counters differ from GPU")
    (out / "e5.json").write_text(json.dumps(res, indent=2))


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--smoke", action="store_true", help="tiny sample counts, short E0/E5")
    ap.add_argument("--resume", metavar="RUN_ID", help="continue data/raw/<RUN_ID>, skipping finished parts")
    ap.add_argument("--skip", default="", help="comma list of E0,E1,E2,E3,E5 to skip")
    ap.add_argument("--extra", choices=sorted(EXTRA), help="run an add-on config set instead of the shortlist")
    ap.add_argument("--only", default="", help="comma list of config ids to run (others are left out)")
    ap.add_argument("--n", type=int, help="override samples per config")
    args = ap.parse_args()
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    skip = {s.strip().upper() for s in args.skip.split(",") if s.strip()}

    prefix = ("smoke-" if args.smoke else "") + (f"{args.extra}-" if args.extra else "") + ("rerun-" if only else "")
    run_id = args.resume or (prefix + uuid.uuid4().hex[:12])
    out = DATA / "raw" / run_id
    if args.resume and not out.exists():
        raise SystemExit(f"no such run: {out}")
    out.mkdir(parents=True, exist_ok=True)
    log = Log(out / "log.txt")
    smoke = args.smoke or run_id.startswith("smoke-")

    extra = args.extra or next((e for e in EXTRA if run_id.removeprefix("smoke-").startswith(e + "-")), None)
    cfgs = plan(smoke, extra, only, args.n)
    cfg_path = out / "configs.json"
    if cfg_path.exists():  # resume: same configs and sample counts the run started with
        stored = {d["config_id"]: d["n"] for d in json.loads(cfg_path.read_text())}
        if args.resume:
            cfgs = [c for c in plan(smoke, extra) if c.id in stored]
        for c in cfgs:
            c.n = stored.get(c.id, c.n)
    else:
        cfg_path.write_text(json.dumps([c.as_dict() for c in cfgs], indent=2))

    todo = [c for c in cfgs if not (out / f"{c.id}.parquet").exists()
            and not ({"E2"} if c.kind == "wots" else {"E3"}) & skip]
    log(f"run {run_id} ({'smoke' if smoke else 'full'}): {len(cfgs)} configs, {len(todo)} to do, "
        f"est. GPU time {sum(map(eta_s, todo)) / 3600:.2f} h (+E0/E1/E5)")
    manifest("campaign_start", run_id, smoke=smoke, resumed=bool(args.resume), skip=sorted(skip),
             extra=args.extra, only=sorted(only), n_override=args.n)
    keep_awake()

    t0 = time.time()
    with PowerLogger(out / f"power-{datetime.now():%Y%m%d-%H%M%S}.parquet"), \
            ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
        if "E0" not in skip and not (out / "e0.json").exists():
            e0(out, log, 10 if smoke else E0_SECONDS)
        if "E1" not in skip:
            gate = out / "gate.json"
            if not (gate.exists() and json.loads(gate.read_text())["passed"]):
                if not e1(out, log, pool, run_id, 300 if smoke else N_GATE):
                    manifest("campaign_abort", run_id, reason="E1 gate failed")
                    raise SystemExit("E1 correctness gate FAILED: see gate.json. Campaign not started.")
        for i, cfg in enumerate(todo, 1):
            log(f"[{i}/{len(todo)}] {cfg.component} {cfg.id}  serves {len(cfg.param_ids)} param sets")
            run_config(out, log, pool, run_id, cfg)
        if "E5" not in skip and not (out / "e5.json").exists():
            e5(out, log, run_id, cfgs, 500 if smoke else CPU_N, (5, 5, 10) if smoke else (60, 30, 120))
    manifest("campaign_end", run_id, hours=round((time.time() - t0) / 3600, 3))
    log(f"done in {(time.time() - t0) / 3600:.2f} h -> {out}")


if __name__ == "__main__":
    main()
