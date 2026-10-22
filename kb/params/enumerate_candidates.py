"""
Enumerate the GRINDSTONE candidate parameter space -> params_candidates.parquet.

Model: grindstone/ref/costs.py (port of SPHINCS-Parameters costs.sage @ ceee8ed),
profile = repo HEAD (R = 16 B, "cached" hash convention). The paper-profile
size (R = 32 B, as in ePrint 2025/2203 Tables 1-2) is sig_bytes + 16, stored
as sig_bytes_paper_r32.

Grid (extends the repo's 2^40-only canonical grid, export_site_data.sage:62-66):
  sig_limit_log2 in {20, 30, 40}
  h in [L-4, L+12], d | h with 4 <= h/d <= 16 (h' > 16: keygen/sign > 2^16 leaves)
  k in [6, 24]; a = smallest a in [8, 20] passing >= 128-bit security for
      (L, h, k) under the variant's security model (larger a is dominated:
      bigger and slower; same for FORS+C grinding cost 2^a)
  WOTS+C: (w, S, z) with w in {16, 256}, S = mean sum of the l = len1 - z
      signed chains + offset (w=16: 0..96 step 16; w=256: 0..1000 step 200),
      z in {0,1,2} (w=16) / {0,1} (w=256); kept if E[tries/layer] <= 2^24
  Variants: wots_c+fors (W+C), wots_c+fors_c (W+C_F+C), wots_c+pors_fp (W+C_P+FP)
      PORS+FP m_max: repo rule (compute_mmax) plus a sweep of every m_max
      with 2^4 <= E[tries] <= 2^24.
Size cap: < 7856 B (SLH-DSA-128s), as in the repo sweeps.

Run:  python -I enumerate_candidates.py   (from this directory or anywhere)
"""
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "ref"))
import costs as c  # noqa: E402

import pandas as pd  # noqa: E402

LIMITS = (20, 30, 40)
K_RANGE = range(6, 25)
A_RANGE = range(8, 21)
MAX_TRIES = 2.0 ** 24
MIN_PFP_TRIES = 2.0 ** 4
SIZE_CAP = 7856
# S = floor(l*(w-1)/2) + offset, l = len1 - z (the mean sum of the l signed
# chains minimises tries; the offsets reproduce the paper's S=240/304, 2040/2840)
WOTS_GRID = {16: ([0, 16, 32, 48, 64, 80, 96], [0, 1, 2]),
             256: ([0, 200, 400, 600, 800, 1000], [0, 1])}
REF_KEYS = {(VS, q, h, d, a, k, w, S) for (VS, q, h, d, a, k, w, _l, S, _b) in c.PARAMETER_SETS
            if VS != "SPX"}
VARIANT = {"W+C": "wots_c+fors", "W+C_F+C": "wots_c+fors_c", "W+C_P+FP": "wots_c+pors_fp"}
TAG = {"W+C": "WC", "W+C_F+C": "WCFC", "W+C_P+FP": "WCPFP"}
CONV = "cached"


def wots_options():
    out = []
    for w, (offs, zs) in WOTS_GRID.items():
        len1 = c.compute_wots_len1(w)
        for off in offs:
            for z in zs:
                S = c.wots_c_mean_sum(w, len1 - z) + off
                if S > (len1 - z) * (w - 1):
                    continue
                t = c.wots_c_expected_tries(w, len1, S, z)
                if t <= MAX_TRIES:
                    out.append((w, S, z, t))
    return out


_sec = {}


def security(L, h, k, a, model):
    key = (L, h, k, a, model)
    if key not in _sec:
        _sec[key] = c.compute_security(2 ** L, h, k, a, model)
    return _sec[key]


def a_min(L, h, k, model):
    for a in A_RANGE:
        s = security(L, h, k, a, model)
        if s >= 128.0:
            return a, s
    return None, None


def pfp_mmax_values(t, k, rule_mmax):
    table = dict(c.interleave_cost_table(t, k)) if (t, k) not in c._interleave_table_cache \
        else c._interleave_table_cache[(t, k)]
    c._interleave_table_cache[(t, k)] = table
    vals = {rule_mmax}
    for m, lg in table.items():
        if MIN_PFP_TRIES <= 2.0 ** lg <= MAX_TRIES:
            vals.add(m)
    return sorted(vals)


def row(L, scheme, h, d, a, k, w, S, z, mmax, sec, rule):
    sign = c.compute_signing_time(h, d, a, k, w, S, scheme, z=z, mmax=mmax, convention=CONV)
    m = sign["mmax"]
    ver = c.compute_verification_time(h, d, a, k, w, S, scheme, m, z=z, convention=CONV)
    size = c.compute_size(h, d, a, k, w, scheme, m, z=z)
    pid = f"L{L}-{TAG[scheme]}-h{h}d{d}-k{k}a{a}-w{w}S{S}z{z}" + (f"-m{m}" if scheme == "W+C_P+FP" else "")
    fts = sign["fts_tries_exact"]
    return {
        "param_id": pid, "variant": VARIANT[scheme], "scheme_costs_sage": scheme,
        "sig_limit_log2": L, "h": h, "d": d, "h_prime": h // d, "a": a, "k": k, "w": w,
        "len1": c.compute_wots_len1(w), "l": c.compute_wots_l(scheme, w, z), "S": S, "z": z,
        "m_max": m if scheme == "W+C_P+FP" else None, "m_max_rule": rule,
        "sig_bytes": size, "sig_bytes_paper_r32": size + 16,
        "sign_hashes": int(sign["hashes"]), "sign_compressions": int(sign["compressions"]),
        "verify_hashes": int(ver["hashes"]), "verify_compressions": int(ver["compressions"]),
        "keygen_compressions": int(c.compute_keygen_time(h, d, w, scheme, z, CONV)),
        "wots_c_tries_per_layer": sign["wots_c_tries_per_layer"],
        "wots_c_tries_total_exp": sign["wots_c_tries_per_layer"] * d,
        "wots_c_worst_2m30_tries": int(sign["wots_c_worst_tries"]),
        "fors_c_tries": float(fts) if scheme == "W+C_F+C" else 0.0,
        "pors_fp_tries": float(fts) if scheme == "W+C_P+FP" else 0.0,
        "fts_worst_2m30_tries": int(sign["fts_worst_tries"]),
        "exp_search_hashes": int(sign["exp_search"]),
        "grind_worst_case_2m30": int(sign["worst_search"]),
        "max_single_instance_tries": max(sign["wots_c_tries_per_layer"], float(fts)),
        "security_bits": sec,
        "is_blockstream_ref": bool(z == 0 and rule in ("repo", "n/a")
                                   and (scheme, L, h, d, a, k, w, S) in REF_KEYS),
    }


def main():
    t0 = time.time()
    wopts = wots_options()
    print(f"{len(wopts)} WOTS+C (w,S,z) options", flush=True)
    rows = []
    for L in LIMITS:
        for h in range(max(L - 4, 8), L + 13):
            ds = [d for d in range(1, h + 1) if h % d == 0 and 4 <= h // d <= 16]
            for k in K_RANGE:
                for scheme in ("W+C", "W+C_F+C", "W+C_P+FP"):
                    model = "PORS+FP" if scheme == "W+C_P+FP" else "FORS"
                    a, sec = a_min(L, h, k, model)
                    if a is None:
                        continue
                    if scheme == "W+C_F+C" and 2.0 ** a > MAX_TRIES:
                        continue
                    for d in ds:
                        for (w, S, z, _t) in wopts:
                            if scheme == "W+C_P+FP":
                                r0 = row(L, scheme, h, d, a, k, w, S, z, None, sec, "repo")
                                if r0["sig_bytes"] < SIZE_CAP and r0["pors_fp_tries"] <= MAX_TRIES:
                                    rows.append(r0)
                                t, _, _ = c.compute_pors_tree_geometry(k, a)
                                for m in pfp_mmax_values(t, k, r0["m_max"]):
                                    if m == r0["m_max"]:
                                        continue
                                    r = row(L, scheme, h, d, a, k, w, S, z, m, sec, "sweep")
                                    if r["sig_bytes"] < SIZE_CAP:
                                        rows.append(r)
                            else:
                                r = row(L, scheme, h, d, a, k, w, S, z, None, sec, "n/a")
                                if r["sig_bytes"] < SIZE_CAP:
                                    rows.append(r)
            print(f"  L={L} h={h}: {len(rows)} rows, {time.time()-t0:.0f}s", flush=True)
    df = pd.DataFrame(rows)
    df = df.drop_duplicates("param_id").sort_values(["sig_limit_log2", "sig_bytes", "sign_hashes"])
    out = os.path.join(HERE, "params_candidates.parquet")
    df.to_parquet(out, index=False, compression="zstd")
    print(f"wrote {len(df)} rows -> {out} in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
