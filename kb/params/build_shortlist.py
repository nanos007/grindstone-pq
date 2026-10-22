"""
Build shortlist_draft.yaml from params_candidates.parquet (deterministic).

Profiles (all: security >= 128 bits at the limit, verify_hashes <= 10,500
[~ the heaviest Kudinov-Nick row], every single grind instance <= 2^24 tries):

  blockstream_ref     all 29 non-SPX rows of costs.sage PARAMETER_SETS
                      (= ePrint 2025/2203 Tables 1-2), m_max by repo rule.
  hw_wallet_safe      smallest size with E[tries] <= 2^12 per instance,
                      2^-30 grind worst case <= 2^20 hashes and expected
                      sign <= 2^23 compressions (~8.4e6).
  gpu_signer_moderate smallest size with E[tries] <= 2^20 per instance and
                      sign <= 2^26 compressions.
  gpu_signer_max      smallest size with E[tries] <= 2^24 per instance and
                      sign <= 2^30 compressions.
  fors_c_stress       (2^30 only) FORS+C with a >= 18 (2^18..2^20 tries), smallest size.
  wots_c_stress       (2^30 only) WOTS+C with 2^19 <= E[tries/layer] <= 2^21, smallest size.
"""
import math
import os

import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
VERIFY_CAP = 10_500
MAX_TRIES = 2 ** 24


def lg(x):
    return round(math.log2(x), 2) if x and x > 0 else None


def entry(r, profile, rationale):
    return {
        "param_id": r.param_id,
        "profile": profile,
        "variant": r.variant,
        "sig_limit_log2": int(r.sig_limit_log2),
        "h": int(r.h), "d": int(r.d), "a": int(r.a), "k": int(r.k), "w": int(r.w),
        "S": int(r.S), "z": int(r.z),
        "m_max": None if pd.isna(r.m_max) else int(r.m_max),
        "counter_size_bytes": 4, "randomness_bytes": 16, "n_bytes": 16,
        "sig_bytes": int(r.sig_bytes),
        "sig_bytes_paper_r32": int(r.sig_bytes_paper_r32),
        "sign_hashes": int(r.sign_hashes),
        "sign_compressions_cached": int(r.sign_compressions),
        "verify_hashes": int(r.verify_hashes),
        "verify_compressions_cached": int(r.verify_compressions),
        "security_bits": round(float(r.security_bits), 2),
        "tries": {
            "wots_c_per_layer": round(float(r.wots_c_tries_per_layer), 2),
            "wots_c_per_layer_log2": lg(r.wots_c_tries_per_layer),
            "wots_c_layers": int(r.d),
            "fors_c": round(float(r.fors_c_tries), 2),
            "fors_c_log2": lg(r.fors_c_tries),
            "pors_fp": round(float(r.pors_fp_tries), 2),
            "pors_fp_log2": lg(r.pors_fp_tries),
            "wots_c_worst_2m30_all_layers": int(r.wots_c_worst_2m30_tries),
            "fts_worst_2m30": int(r.fts_worst_2m30_tries),
        },
        "grind_worst_case_2m30_hashes": int(r.grind_worst_case_2m30),
        "rationale": rationale,
    }


def main():
    df = pd.read_parquet(os.path.join(HERE, "params_candidates.parquet"))
    out = []
    ref = df[df.is_blockstream_ref].sort_values(["sig_limit_log2", "variant", "sig_bytes"],
                                                ascending=[False, True, True])
    for r in ref.itertuples():
        out.append(entry(r, "blockstream_ref",
                         f"Kudinov-Nick ePrint 2025/2203 Table {'1' if r.sig_limit_log2 >= 30 else '2'} "
                         f"row ({r.sig_bytes_paper_r32} B in paper with R=32 B); anchor for RQ1 validation."))

    ok = df[(df.verify_hashes <= VERIFY_CAP) & (df.max_single_instance_tries <= MAX_TRIES)
            & (df.security_bits >= 128.0)]

    def pick(sub):
        return sub.sort_values(["sig_bytes", "sign_compressions", "verify_hashes"]).iloc[0]

    for L in (20, 30, 40):
        x = ok[ok.sig_limit_log2 == L]
        hw = pick(x[(x.max_single_instance_tries <= 2 ** 12) & (x.grind_worst_case_2m30 <= 2 ** 20)
                    & (x.sign_compressions <= 2 ** 23)])
        out.append(entry(hw, "hw_wallet_safe",
                         f"Smallest 2^{L} point with every grind <= 2^12 expected tries, 2^-30 worst case "
                         f"<= 2^20 hashes and <= 2^23 sign compressions (Cortex-M class signer)."))
        gm = pick(x[(x.max_single_instance_tries <= 2 ** 20) & (x.sign_compressions <= 2 ** 26)])
        out.append(entry(gm, "gpu_signer_moderate",
                         f"Smallest 2^{L} point with grinds <= 2^20 tries and <= 2^26 sign compressions "
                         f"(desktop GPU, well under 1 s)."))
        gx = pick(x[x.sign_compressions <= 2 ** 30])
        out.append(entry(gx, "gpu_signer_max",
                         f"Smallest 2^{L} point with grinds <= 2^24 tries and <= 2^30 sign compressions "
                         f"(GPU / co-signing server; size floor of the campaign)."))
        if L == 30:
            fc = pick(x[(x.variant == "wots_c+fors_c") & (x.a >= 18)])
            out.append(entry(fc, "fors_c_stress",
                             "FORS+C with a >= 18 (2^18-2^20 R-regrinding tries, 4 compressions each): "
                             "stresses the no-midstate FTS grind path (H1b)."))
            wc = x[(x.wots_c_tries_per_layer >= 2 ** 19) & (x.wots_c_tries_per_layer <= 2 ** 21)]
            out.append(entry(pick(wc), "wots_c_stress",
                             "WOTS+C at ~2^20 tries/layer (midstate-cached 1-compression attempts, d layers): "
                             "stresses the WOTS+C kernel and the negative-binomial tail."))
    # de-duplicate (a profile may coincide with a reference row)
    seen, final = set(), []
    for e in out:
        if e["param_id"] in seen:
            continue
        seen.add(e["param_id"])
        final.append(e)
    doc = {
        "generated_by": "grindstone/kb/params/build_shortlist.py",
        "model": "grindstone/ref/costs.py (port of SPHINCS-Parameters costs.sage @ ceee8ed), "
                 "profile R=16 B, cached convention; sig_bytes_paper_r32 = +16 B (paper tables)",
        "date": "2026-10-22",
        "status": "DRAFT - for review by Agent F / owner",
        "constraints": {"security_bits_min": 128, "verify_hashes_max": VERIFY_CAP,
                        "max_expected_tries_per_grind_instance": MAX_TRIES},
        "count": len(final),
        "points": final,
    }
    with open(os.path.join(HERE, "shortlist_draft.yaml"), "w", encoding="utf8") as f:
        yaml.safe_dump(doc, f, sort_keys=False, width=120)
    for e in final:
        t = e["tries"]
        print(f"{e['profile']:20s} {e['param_id']:42s} {e['sig_bytes']:5d} "
              f"wots={t['wots_c_per_layer_log2']} fc={t['fors_c_log2']} pfp={t['pors_fp_log2']} "
              f"sign={e['sign_compressions_cached']:.2e} ver={e['verify_hashes']}")
    print(len(final))


if __name__ == "__main__":
    main()
