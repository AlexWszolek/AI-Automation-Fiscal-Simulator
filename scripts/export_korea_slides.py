"""Export the Korea slide deck as 1920×1080 PNGs — the artifact the diplomat's deck is
assembled from. Builds the site, serves the dist with `vite preview` (no HMR socket, so
headless Chrome exits cleanly), shoots every slide's ?slide=N export view, and writes
docs/research/korea-slides-pack/slides/NN-<key>.png.

    .venv/bin/python scripts/export_korea_slides.py [--skip-build]

The deck reads the committed static bundles, so the PNGs carry exactly the site's numbers.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
OUT = ROOT / "docs" / "research" / "korea-slides-pack" / "slides"
PORT = 5197
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SLIDES = ["headline", "nps", "nhi", "ei", "scenarios", "composition", "map", "sensitivity", "scope"]


def wait_for(url: str, timeout: float = 30.0) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"server at {url} never came up")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-build", action="store_true")
    a = ap.parse_args()

    if not a.skip_build:
        print("building…")
        subprocess.run(["npx", "vite", "build"], cwd=WEB, check=True,
                       capture_output=True, text=True)
    OUT.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen(["npx", "vite", "preview", "--port", str(PORT)], cwd=WEB,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for(f"http://localhost:{PORT}/korea-slides.html")
        for i, key in enumerate(SLIDES, start=1):
            png = OUT / f"{i:02d}-{key}.png"
            png.unlink(missing_ok=True)
            # Chrome under --headless=new does not reliably self-terminate after the
            # screenshot lands (observed with both --timeout and --virtual-time-budget),
            # so: fire, poll for the file, kill. The PNG is complete when it appears —
            # Chrome writes it atomically.
            proc = subprocess.Popen(
                [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                 f"--user-data-dir={OUT / '.chrome-profile'}",
                 "--window-size=1920,1080", "--timeout=15000",
                 f"--screenshot={png}",
                 f"http://localhost:{PORT}/korea-slides.html?slide={i}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            t0 = time.time()
            while time.time() - t0 < 45 and not png.exists():
                time.sleep(0.5)
            time.sleep(1.0)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            if not png.exists():
                raise RuntimeError(f"slide {i} ({key}) never rendered")
            print(f"wrote {png} ({png.stat().st_size // 1024} KB)")
    finally:
        server.terminate()
        server.wait(timeout=10)
        chrome_profile = OUT / ".chrome-profile"
        if chrome_profile.exists():
            subprocess.run(["rm", "-rf", str(chrome_profile)], check=False)


if __name__ == "__main__":
    main()
