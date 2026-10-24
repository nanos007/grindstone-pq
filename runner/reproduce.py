"""One-command reproduction (doc §4.6).

    python -m runner.reproduce                    # smoke campaign on this GPU (~5 min) + all notebooks on it
    python -m runner.reproduce --analysis-only    # rebuild the published figures from data/raw/<published run>
    python -m runner.reproduce --hash <run_id>    # print the dataset hash of a run directory

The smoke campaign runs E0/E1/E2/E3/E5 at 1/1000 of the published sample counts (same kernels, same
correctness gate), so it checks that the pipeline works on your machine; its statistics are not
publication-grade. Outputs of a non-published run go to analysis/out_<run_id>/.
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PUBLISHED_RUN = "196e7e91e907"


def dataset_hash(run_dir):
    """SHA-256 over (relative path, file SHA-256) of every Parquet/JSON/JSONL file, sorted by path.
    Logs and the console trace are excluded; they are not data."""
    h = hashlib.sha256()
    for p in sorted(run_dir.rglob("*")):
        if p.is_file() and p.suffix in (".parquet", ".json", ".jsonl"):
            rel = p.relative_to(run_dir).as_posix()
            h.update(f"{rel}\0{hashlib.sha256(p.read_bytes()).hexdigest()}\n".encode())
    return h.hexdigest()


def notebooks(run_id):
    env = dict(os.environ, GRINDSTONE_RUN=run_id)
    subprocess.run([sys.executable, str(ROOT / "analysis" / "build_notebooks.py")], cwd=ROOT, env=env, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--analysis-only", action="store_true", help="skip the GPU smoke campaign")
    ap.add_argument("--run", help="analyse this run instead of a fresh smoke run (with --analysis-only)")
    ap.add_argument("--hash", metavar="RUN_ID", help="print the dataset hash of data/raw/RUN_ID and exit")
    args = ap.parse_args()

    if args.hash:
        print(dataset_hash(RAW / args.hash))
        return
    if args.analysis_only:
        run_id = args.run or PUBLISHED_RUN
    else:
        out = subprocess.run([sys.executable, "-m", "runner.run_campaign", "--smoke"], cwd=ROOT, check=True,
                             capture_output=True, text=True)
        print(out.stdout, end="")
        run_id = re.search(r"run (smoke-[0-9a-f]+)", out.stdout).group(1)
    notebooks(run_id)
    print(f"run {run_id}: dataset sha256 {dataset_hash(RAW / run_id)}")


if __name__ == "__main__":
    main()
