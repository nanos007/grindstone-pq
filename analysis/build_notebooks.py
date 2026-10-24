"""Build and execute the analysis notebooks from their cell modules (nb_*.py).

    python analysis/build_notebooks.py            # all
    python analysis/build_notebooks.py 01 03      # some

The nb_*.py files are the source of truth (reviewable diffs); the .ipynb files are generated with
outputs. Figures and tables land in analysis/out/<notebook>/. CPU only; no GPU needed.
Set GRINDSTONE_RUN=<run_id> to analyse another run; everything then goes to analysis/out_<run_id>/.
"""
import importlib
import os
import sys
from pathlib import Path

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

HERE = Path(__file__).resolve().parent
NOTEBOOKS = {
    "01": ("nb_01_validate", "01_validate_vs_analytic.ipynb"),
    "02": ("nb_02_tails", "02_tails.ipynb"),
    "03": ("nb_03_pareto", "03_pareto.ipynb"),
    "04": ("nb_04_fees_energy", "04_fees_energy.ipynb"),
    "05": ("nb_05_oq3", "05_oq3_overgrinding.ipynb"),
}


def build(key):
    mod_name, nb_name = NOTEBOOKS[key]
    sys.path.insert(0, str(HERE))
    cells = importlib.import_module(mod_name).CELLS
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.cells = [nbformat.v4.new_markdown_cell(src) if kind == "md" else nbformat.v4.new_code_cell(src)
                for kind, src in cells]
    ExecutePreprocessor(timeout=1800, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(HERE)}})
    run = os.environ.get("GRINDSTONE_RUN")
    run = None if run == importlib.import_module("common").PUBLISHED_RUN else run
    dest = HERE / f"out_{run}" if run else HERE  # executed copies for other runs stay out of the published set
    dest.mkdir(exist_ok=True)
    nbformat.write(nb, dest / nb_name)
    print(f"{dest.name}/{nb_name}: ok" if run else f"{nb_name}: ok")


if __name__ == "__main__":
    for k in sys.argv[1:] or NOTEBOOKS:
        build(k)
