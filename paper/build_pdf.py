"""Print the website's /paper/ page to paper/grindstone-paper.pdf (and site/public/ for the download link).

    cd site && npm run build && cd ..      # the PDF is printed from site/out/
    python paper/build_pdf.py

Uses headless Microsoft Edge or Chrome, so the PDF is rendered by the same Markdown renderer and styles as
the web page (print stylesheet in site/app/globals.css). No LaTeX needed.
"""
import functools
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "site" / "out"
PDF = ROOT / "paper" / "grindstone-paper.pdf"
PUBLIC = ROOT / "site" / "public" / "grindstone-paper.pdf"

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google-chrome", "chromium", "microsoft-edge",
]


def browser():
    for b in BROWSERS:
        if Path(b).exists() or shutil.which(b):
            return b
    sys.exit("no Edge/Chrome found")


def main():
    if not (OUT_DIR / "paper" / "index.html").exists():
        sys.exit("site/out/paper/index.html missing: run `npm run build` in site/ first")

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(OUT_DIR)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/paper/"

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "paper.pdf"
        subprocess.run([
            browser(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
            "--force-prefers-reduced-motion", "--virtual-time-budget=10000",
            f"--user-data-dir={tmp}", f"--print-to-pdf={raw}", url,
        ], check=True, capture_output=True, timeout=180)
        server.shutdown()

        writer = PdfWriter(clone_from=PdfReader(raw))
        writer.add_metadata({
            "/Title": "Grinding at the Edge: Empirical Signer-Cost Distributions for Bitcoin-Tuned Hash-Based Signatures",
            "/Author": "Georgios Nanos",
            "/Subject": "GRINDSTONE: measured grinding costs of WOTS+C, FORS+C and PORS+FP (draft 2026-10-24)",
            "/Keywords": "post-quantum, Bitcoin, SPHINCS+, WOTS+C, FORS+C, PORS+FP, grinding, GPU",
        })
        with open(PDF, "wb") as f:
            writer.write(f)

    shutil.copy(PDF, PUBLIC)
    print(f"wrote {PDF.relative_to(ROOT)} ({len(PdfReader(PDF).pages)} pages) and {PUBLIC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
