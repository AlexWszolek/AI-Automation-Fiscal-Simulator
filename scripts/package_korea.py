"""Assemble the Korea package — everything the diplomats' organisation needs to host the
Korea site on their own infrastructure, and nothing of the US site.

    .venv/bin/python scripts/package_korea.py
    # -> build/korea-package/                      the assembled tree
    #    build/korea-package-<sha>.tar.gz          MAIL-SAFE: no web/dist (Gmail rejects any archive
    #                                              holding .js files, whatever the format)
    #    build/korea-package-<sha>.zip             the full tree incl. web/dist, for Drive/USB

The package mirrors this repository's layout (api/, fiscal_model/, scripts/, tests/,
data/raw/korea/, web/, deploy/, docs/) so every regeneration script runs unchanged, plus:

- web/dist/         the site prebuilt (Korea entries only) — deployable with no toolchain;
- data/raw/korea/*.tidy.csv   the parsed tables the compute service reads (gitignored here,
                    shipped there so the service starts without the parse step);
- VERSION           the source commit, reported by /api/health;
- README.md         the deploy guide (deploy/KOREA_PACKAGE_README.md).

Excluded: the US app's HTML entry, public data, report pages and figures; the US model's
raw data and interim artifacts; the US-only tests, Streamlit app, notebooks, report
pipeline. The web/src tree keeps the US app's modules because the Korea pages import the
chart, component and copy modules they share — only the Korea entries are built (the
Vite config drops the US entry when index.html is absent).
"""
from __future__ import annotations

import fnmatch
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "korea-package"

# (source, glob patterns to include — every file under the dir when None, excludes below)
DIRS: list[tuple[str, list[str] | None]] = [
    ("api", None),
    ("fiscal_model", None),
    ("data/raw/korea", None),
    ("data/raw/crosswalks", None),
    ("tests", ["conftest.py", "test_korea_*.py"]),
    ("scripts", ["gen_korea_*.py", "fetch_korea_*.py", "export_korea_slides.py",
                 "korea_monte_carlo.py", "package_korea.py"]),
    ("deploy", ["nginx.conf.example", "Caddyfile.example", "fiscal-api.service.example"]),
    ("web/src", None),
    ("web/public/fonts", None),
    ("web/public/data/korea", None),
    ("docs/research/korea-slides-pack", None),
]
FILES = [
    "requirements.txt", "api/requirements.txt", "LICENSE",
    "web/korea.html", "web/korea-app.html", "web/korea-dash.html", "web/korea-slides.html",
    "web/package.json", "web/package-lock.json", "web/tsconfig.json", "web/vite.config.ts",
    "web/.gitignore",
    "web/public/data/korea.json", "web/public/data/korea-sido-topo.json",
    "docs/KOREA_PRESET_EVIDENCE.md", "docs/research/korea-fiscal-system.md",
    # the US exposure sources the Korea robot/cognitive vectors are mapped from
    # (scripts/gen_korea_exposure_map.py and its pin test read them)
    "data/raw/occupation_ai_exposure.xlsx", "data/raw/robot_exposure_by_soc.xlsx",
]
EXCLUDE = ["__pycache__", "*.pyc", ".DS_Store", ".chrome-profile", "*.tsbuildinfo",
           "node_modules", "dist"]


def _excluded(path: Path) -> bool:
    return any(fnmatch.fnmatch(part, pat) for part in path.parts for pat in EXCLUDE)


def copy_tree(src: Path, dst: Path, patterns: list[str] | None) -> int:
    n = 0
    for f in sorted(src.rglob("*")):
        if not f.is_file() or _excluded(f.relative_to(src)):
            continue
        if patterns and not any(fnmatch.fnmatch(f.name, p) for p in patterns):
            continue
        target = dst / f.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
        n += 1
    return n


def git_sha() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True, check=True).stdout.strip()


def build_site(dist: Path) -> None:
    """The Korea entries only, into the package's web/dist (the copied web/ has no
    index.html, so a rebuild there yields the same set)."""
    env = {**os.environ, "KOREA_ONLY": "1"}
    subprocess.run(["npx", "vite", "build", "--outDir", str(dist), "--emptyOutDir"],
                   cwd=ROOT / "web", env=env, check=True, capture_output=True, text=True)
    # vite copies all of public/: drop the US data and pages it brought along
    for rel in ("data/us-10m.json", "data/scenarios", "data/tornado.json",
                "data/column-guide.csv", "report-figures", "report.html", "evidence.html"):
        p = dist / rel
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
    # a landing page so the site root is not a 404: the four entries by their own titles
    import re
    links = []
    for name in ("korea.html", "korea-app.html", "korea-dash.html", "korea-slides.html"):
        title = re.search(r"<title>(.*?)</title>", (dist / name).read_text(encoding="utf-8"))
        links.append(f'<li><a href="/{name}">{title.group(1) if title else name}</a></li>')
    (dist / "index.html").write_text(
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='robots' content='noindex, nofollow'>"
        "<title>Fiscal Consequences of AI Automation — Korea</title>"
        "<style>body{font-family:Georgia,serif;max-width:40rem;margin:4rem auto;padding:0 1rem;"
        "color:#2b2822}li{margin:.5rem 0}</style></head><body>"
        "<h1>Fiscal Consequences of AI Automation — Korea</h1><ul>" + "".join(links)
        + "</ul></body></html>\n", encoding="utf-8")


def main() -> None:
    sha = git_sha()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    total = 0
    for rel, patterns in DIRS:
        total += copy_tree(ROOT / rel, OUT / rel, patterns)
    for rel in FILES:
        (OUT / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, OUT / rel)
        total += 1
    # the Korea tidy tables are gitignored in the repo (regenerable from the committed raw
    # exports) but shipped in the package so the service starts without the parse step
    missing = [f for f in ("DT_118N_PAYM39.tidy.csv", "region_occupation.tidy.csv",
                           "region_labour_force.tidy.csv")
               if not (OUT / "data/raw/korea" / f).exists()]
    if missing:
        sys.exit(f"Korea tidy tables missing — run scripts/bootstrap.sh step 7 first: {missing}")
    # the model's requirements minus what only the Streamlit app and the report build use
    # (nothing on the Korea path imports them); the pinned native trio stays exactly as is
    drop = ("streamlit", "altair", "vl-convert-python", "python-docx")
    req = [l for l in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
           if not l.strip().startswith(drop)]
    (OUT / "requirements.txt").write_text("\n".join(req) + "\n", encoding="utf-8")
    shutil.copy2(ROOT / "deploy" / "KOREA_PACKAGE_README.md", OUT / "README.md")
    (OUT / "VERSION").write_text(sha + "\n", encoding="utf-8")
    # the package's systemd unit runs the service in Korea-only mode under its own paths
    unit = OUT / "deploy" / "fiscal-api.service.example"
    text = unit.read_text(encoding="utf-8").replace("/srv/fiscal-simulator", "/srv/korea-fiscal")
    text = text.replace("Environment=FISCAL_TORNADO_WORKERS=6\n",
                        "Environment=FISCAL_TORNADO_WORKERS=6\nEnvironment=FISCAL_KOREA_ONLY=1\n")
    unit.write_text(text, encoding="utf-8")
    for name in ("nginx.conf.example", "Caddyfile.example"):
        p = OUT / "deploy" / name
        p.write_text(p.read_text(encoding="utf-8").replace("/srv/fiscal-simulator", "/srv/korea-fiscal"),
                     encoding="utf-8")
    print(f"copied {total} files")
    build_site(OUT / "web" / "dist")
    print("built web/dist (Korea entries)")

    for old in (ROOT / "build").glob("korea-package-*.*"):
        old.unlink()
    files = [f for f in sorted(OUT.rglob("*")) if f.is_file()]
    # the mail-safe archive: Gmail blocks archives (zip, tgz, gz, ...) that contain .js
    # files, and the built site is eight of them — so it ships the source and the README's
    # one-command build instead. Nothing else in the tree is a blocked type.
    tar_path = ROOT / "build" / f"korea-package-{sha}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as t:
        for f in files:
            rel = f.relative_to(OUT)
            if rel.parts[:2] != ("web", "dist"):
                t.add(f, arcname=str(Path("korea-package") / rel))
    print(f"wrote {tar_path} ({tar_path.stat().st_size // 1024 // 1024} MB, mail-safe, no web/dist)")
    zip_path = ROOT / "build" / f"korea-package-{sha}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, Path("korea-package") / f.relative_to(OUT))
    print(f"wrote {zip_path} ({zip_path.stat().st_size // 1024 // 1024} MB, full tree incl. web/dist)")


if __name__ == "__main__":
    main()
