# GRINDSTONE

**Measured grinding costs of Bitcoin-tuned hash-based signatures (WOTS+C, FORS+C, PORS+FP) on a consumer
GPU and a laptop CPU.**

**Website:** https://grindstone-pq.vercel.app · **Paper (PDF):** [`paper/grindstone-paper.pdf`](paper/grindstone-paper.pdf) ·
**Dataset:** GitHub release `data-196e7e91e907`

Hash-based post-quantum signatures for Bitcoin can be made smaller by *grinding*: the signer retries a
hash until it meets a condition, which removes checksum chains or whole FORS trees from the signature.
Published analyses give the expected cost of this search. GRINDSTONE measures the full distribution,
tails included, for the parameter sets of Kudinov–Nick (ePrint 2025/2203) and a set of smaller
"heavy-signer" points. It maps the results onto signer hardware from hardware wallets to GPUs.

- Plan and research questions: `btc-pq-grinding-project.md` (kept outside this repository)
- Results: [`analysis/README.md`](analysis/README.md) (headline numbers) and `analysis/*.ipynb`
- Threats to validity: [`kb/threats_to_validity.md`](kb/threats_to_validity.md)
- Paper draft: [`paper/paper.md`](paper/paper.md), PDF [`paper/grindstone-paper.pdf`](paper/grindstone-paper.pdf) (`python paper/build_pdf.py` after `npm run build` in `site/`)

## Headline results (run `196e7e91e907`, RTX 4050 Laptop @ 45 W)

- **The analytic model holds.** 11.16 M reference-verified grinds across 37 configs; every mean is within
  2 % of 1/p (max −1.66 %), with no detectable deviation in distribution shape.
- **Tails are geometric.** The slowest grind in 1,000 takes 6.73–7.05× the mean (theory 6.91×). Wallets
  should design for about 7× the mean grind, not the mean.
- **The published cost model mis-prices FTS grinding.** Each FORS+C/PORS+FP attempt costs 6 (R-grind),
  3 (ctr-grind) or 7 (PORS+FP) SHA-256 compressions under FIPS 205, not the modelled 4.
- **Grinding is ≤ 18 % of signing work.** Tree building dominates at every point.
- **Signer budget buys bytes.** At 2⁴⁰ signatures, 2,892 B (GPU-signer) vs. 3,944 B (hardware-wallet-safe)
  = −263 vB per input, −23 % of a 1-in/2-out spend. A laptop CPU with SHA-NI reaches the smallest
  shortlisted point at every limit within a 10 s p99 budget.
- **Verification never gets worse** when FORS+C/PORS+FP compression is added.

## Layout

```
ref/        pure-Python reference (obviously correct, slow): WOTS+C, FORS+C, PORS+FP, cost model port
cuda/       NVRTC kernels: SHA-256 midstate, grind_wots_c, grind_fors_c (R / ctr / PORS+FP), raw bench
cpu/        SHA-NI C grinder and bench (built with `ziglang`), the Class 2 baseline
grind/      Python drivers for the GPU (CuPy) and CPU grinders
runner/     campaign runner (E0–E6), instance derivation, power logger, reproduce
kb/         knowledge base: sources, claims, constructions, parameters, hardware ladder, fees, threats
data/       manifest.jsonl (committed); raw/<run_id>/ Parquet per config (not in git; published separately)
analysis/   notebooks 01–05 (cell sources nb_*.py → executed .ipynb), figures and tables in out/
tests/      pytest: reference vs. spec, cost model vs. paper tables, fees vs. mainnet, GPU vs. reference
paper/      paper draft, executive summary, mailing-list post
```

## Setup

Windows 11 or Linux, Python 3.12, an NVIDIA GPU with a recent driver. No CUDA toolkit or compiler is
needed: kernels compile at run time through NVRTC (CuPy), and the CPU grinder is built with the `ziglang`
pip package.

```
pip install -r env/requirements.txt
python -m env.check_env          # compiles a test kernel, records GPU/CPU/OS in data/manifest.jsonl
python -m pytest -q              # 112 tests; -k "not gpu" for the CPU-only subset
```

## Running

```
python -m runner.run_campaign --smoke                 # ~5 min end-to-end check
python -m runner.run_campaign                         # full campaign (~2.3 h GPU + E0/E1/E5)
python -m runner.run_campaign --resume <run_id>       # continue an interrupted run
python -m runner.run_campaign --extra oq3             # OQ-3 overgrinding sweep (~15 min GPU)
python -m runner.run_campaign --only pors-k9-a13-h48-m77 --n 100000   # rerun one config at n = 1e5 (~2.2 h)

python analysis/build_notebooks.py                    # rebuild + execute all notebooks (CPU only, ~1 min)
python -m runner.reproduce                            # smoke campaign + all notebooks on it
python -m runner.reproduce --analysis-only            # notebooks on the published run
python -m runner.reproduce --hash 196e7e91e907        # dataset hash
```

Each campaign refuses to start unless the E1 correctness gate passes: GPU counters must equal the Python
reference bit for bit, with full minimality checks. Every counter of every campaign is re-checked against
the reference before it is written.

Run campaigns on mains power with nothing else using the GPU. Other GPU load (games included) slows the
grind and invalidates its timing data. Tries counts stay correct, but throughput and energy do not.

## Data

`data/raw/196e7e91e907/` contains:
- one Parquet per config (`instance_seed, tries, counter, gpu_ns`);
- `summary.jsonl`, `configs.json` and `gate.json`;
- E0/E5 results;
- 10 Hz GPU power/clock logs and per-launch traces.

Instance inputs derive from SHA-256("grindstone" ‖ run_id ‖ i), so every sample can be regenerated.

Dataset SHA-256 (`runner.reproduce --hash`): `01e9fd2ca78f89e5c2525072705e8f32f42863054ffcbc7301341905bfe98d80`

## Website

`site/` is a static Next.js site: results, an interactive signer-budget explorer, method, the paper and
reproduction steps, styled after nanos.work. It reads only `site/content/` (committed), so it builds
without Python or the raw dataset.

```
python site/scripts/export_data.py    # refresh site/content/ after re-running the notebooks
cd site && npm install
npm run dev                           # http://localhost:3000
npm run check                         # explorer rule vs. analysis/out/03_pareto (112 checks)
npm run build                         # static export to site/out/
```

Vercel: import the repository with Root Directory `site`. GitHub Pages: build with
`NEXT_PUBLIC_BASE_PATH=/grindstone-pq` and publish `site/out/`.

## License

Code: MIT (`LICENSE`). Data and figures: CC-BY-4.0.
