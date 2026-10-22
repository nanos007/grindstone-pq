"""Build and drive the SHA-NI CPU grinder (E5)."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
EXE = ".exe" if os.name == "nt" else ""


def build(name):
    out = BUILD / f"{name}{EXE}"
    src = ROOT / "cpu" / f"{name}.c"
    deps = list((ROOT / "cpu").glob("*.h")) + [src]
    if out.exists() and out.stat().st_mtime > max(d.stat().st_mtime for d in deps):
        return out
    BUILD.mkdir(exist_ok=True)
    subprocess.run([sys.executable, "-m", "ziglang", "cc", "-O3", "-msha", "-msse4.1", "-mssse3",
                    "-o", str(out), str(src)], check=True)
    return out


def bench(threads, seconds):
    r = subprocess.run([str(build("bench_cpu")), str(threads), str(seconds)],
                       check=True, capture_output=True, text=True)
    return json.loads(r.stdout)


def _cap(max_tries, ctr_bytes):
    return min(max_tries, 1 << (8 * ctr_bytes)) if ctr_bytes < 4 else max_tries


def grind_wots_c(mids, tmpls, ctr_off, params, ctr_le=False, max_tries=1 << 30, threads=12, ctr_bytes=4):
    """Same contract as grind.gpu.grind_wots_c; returns (counters, per-instance seconds, wall_s)."""
    from ref.wots_c import zmask_words
    praw = np.array([params.len1, params.logw, params.S, *zmask_words(params),
                     ctr_off, int(ctr_le), _cap(max_tries, ctr_bytes), ctr_bytes], dtype="<u4")
    inst = np.concatenate([np.asarray(mids, dtype="<u4"), np.asarray(tmpls, dtype="<u4")], axis=1)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        praw.tofile(td / "p.bin")
        inst.tofile(td / "i.bin")
        r = subprocess.run([str(build("grind_cpu")), "wots", str(threads), str(td / "p.bin"),
                            str(td / "i.bin"), str(td / "o.bin")],
                           check=True, capture_output=True, text=True)
        out = np.fromfile(td / "o.bin", dtype=[("counter", "<u4"), ("pad", "<u4"), ("seconds", "<f8")])
    return out["counter"], out["seconds"], json.loads(r.stdout)["wall_s"]
