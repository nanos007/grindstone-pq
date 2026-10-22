"""Grind configurations for E1–E3, derived from the parameter shortlist.

A grind's distribution depends only on a few parameters (WOTS+C: w, S, z; FORS+C: k, a and the
layout; PORS+FP: k, a, h, m_max), so shortlist points that share them share one config. Each
config lists the param_ids it serves; samples are i.i.d. per-instance (per-layer for WOTS+C).
"""
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ref import costs, fors_c, wots_c

ROOT = Path(__file__).resolve().parents[1]
SHORTLIST = ROOT / "kb" / "params" / "shortlist_draft.yaml"
N_BITS = 128

# per-attempt compressions (README finding 1); WOTS+C = 1
COMPRESSIONS = {"wots": 1, "R": 6, "ctr": 3, "pors": 7}
COMPONENT = {"wots": "wots_c", "R": "fors_c", "ctr": "fors_c", "pors": "pors_fp"}


@dataclass
class Config:
    kind: str                   # wots | R | ctr | pors
    w: int = 0
    S: int = 0
    z: int = 0
    k: int = 0
    a: int = 0
    h: int = 0
    m_max: int = 0
    param_ids: list = field(default_factory=list)
    n: int = 0                  # samples to collect (set by the plan)

    @property
    def id(self):
        if self.kind == "wots":
            return f"wots-w{self.w}-S{self.S}-z{self.z}"
        if self.kind == "pors":
            return f"pors-k{self.k}-a{self.a}-h{self.h}-m{self.m_max}"
        return f"fors_{self.kind}-k{self.k}-a{self.a}"

    @property
    def component(self):
        return COMPONENT[self.kind]

    @property
    def wots_params(self):
        logw = self.w.bit_length() - 1
        # last z chains forced to zero == last z·log2(w) bits of d zero (log2 w | 128 for w ∈ {16, 256})
        return wots_c.WotsParams(w=self.w, len1=N_BITS // logw, S=self.S, z_bits=self.z * logw)

    def expected_tries(self):
        """Analytic E[tries] = 1/p, with the PORS+FP P_enough correction (README finding 3)."""
        if self.kind == "wots":
            return costs.wots_c_expected_tries(self.w, N_BITS // (self.w.bit_length() - 1), self.S, self.z)
        if self.kind in ("R", "ctr"):
            return float(1 << self.a)
        t = self.k << self.a
        return costs.exp_work_from_mmax(t, self.k, self.m_max) / fors_c.p_enough(t, self.k, self.h)

    @property
    def group(self):
        # measured 2026-10-22: block-per-instance wins from E[tries] ~ 500 up, warp below
        return "blk" if self.expected_tries() >= 256 else "w32"

    def as_dict(self):
        return {"config_id": self.id, "kind": self.kind, "component": self.component,
                "w": self.w, "S": self.S, "z": self.z, "k": self.k, "a": self.a, "h": self.h,
                "m_max": self.m_max, "n": self.n, "group": self.group,
                "expected_tries": self.expected_tries(),
                "compressions_per_attempt": COMPRESSIONS[self.kind], "param_ids": self.param_ids}


def from_shortlist(path=SHORTLIST):
    pts = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["points"]
    out = {}

    def add(cfg, pid):
        out.setdefault(cfg.id, cfg).param_ids.append(pid)

    for p in pts:
        pid = p["param_id"]
        add(Config("wots", w=p["w"], S=p["S"], z=p["z"]), pid)
        if p["variant"] == "wots_c+fors_c":
            for lay in ("R", "ctr"):
                add(Config(lay, k=p["k"], a=p["a"]), pid)
        elif p["variant"] == "wots_c+pors_fp":
            add(Config("pors", k=p["k"], a=p["a"], h=p["h"], m_max=p["m_max"]), pid)
    return list(out.values())


def shortlist_sha256(path=SHORTLIST):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# E1: same kernels at reduced difficulty so the Python reference can check every counter.
# Covers each acceptance path: WOTS+C w=16/256 and the zero mask, FORS+C masks inside one word
# and straddling words 3/4 (k=19, a=7: bits 126..132), PORS+FP with non-power-of-two t.
GATE = [
    Config("wots", w=16, S=240),
    Config("wots", w=256, S=2040),
    Config("wots", w=16, S=240, z=1),
    Config("R", k=11, a=7), Config("R", k=19, a=7),
    Config("ctr", k=11, a=7), Config("ctr", k=19, a=7),
    Config("pors", k=10, a=6, h=20, m_max=40),
    Config("pors", k=11, a=5, h=40, m_max=36),
    Config("pors", k=9, a=7, h=33, m_max=44),
]
