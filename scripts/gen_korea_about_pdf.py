"""Render the "About the model" methodology — English then Korean — as one PDF for the
diplomats: docs/research/korea-slides-pack/about-the-model.pdf.

    .venv/bin/python scripts/gen_korea_about_pdf.py

The text is exactly what the site's About dialog shows (copy.json / copy.ko.json →
korea.about + korea.disclosures + the central run's conventions line), rendered through
the same markdown subset as web/src/content/md.tsx, printed by headless Chrome (the only
renderer on the machine with Korean fonts and no LaTeX). Regenerate whenever that copy
changes; the PDF is committed so the pack is complete without a build.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COPY = ROOT / "web" / "src" / "content"
OUT = ROOT / "docs" / "research" / "korea-slides-pack" / "about-the-model.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4; margin: 22mm 20mm 24mm 20mm; }
body { font-family: Georgia, "Noto Serif KR", "Apple SD Gothic Neo", serif; color: #2b2822;
       font-size: 10.5pt; line-height: 1.5; }
:lang(ko) { font-family: "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic", sans-serif;
            word-break: keep-all; }
section:lang(ko) { font-size: 10.2pt; line-height: 1.65; }   /* not :lang(ko) — that
                                                                outranks the h1/h2 sizes */
h1 { font-size: 20pt; margin: 0 0 2pt; font-weight: 600; }
h2 { font-size: 13pt; margin: 18pt 0 6pt; font-weight: 600; }
.sub { color: #6b6760; margin: 0 0 14pt; font-size: 9.5pt; }
p { margin: 0 0 8pt; }
ul, ol { margin: 0 0 8pt; padding-left: 18pt; }
li { margin: 0 0 3pt; }
table { border-collapse: collapse; margin: 6pt 0 10pt; font-size: 9.5pt; }
th, td { text-align: left; vertical-align: top; padding: 3pt 10pt 3pt 0; border-bottom: 1px solid #d8d4cc; }
.caption { color: #6b6760; font-size: 9.2pt; }
.break { page-break-before: always; }
a { color: inherit; }
"""


def inline(text: str) -> str:
    """The md.tsx inline rules: links, **bold**, *italic*; everything else escaped."""
    out = []
    for p in re.split(r"(\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|\*[^*]+\*)", text):
        if not p:
            continue
        m = re.match(r"^\[([^\]]+)\]\(([^)]+)\)$", p)
        if m:
            out.append(f'<a href="{html.escape(m.group(2))}">{html.escape(m.group(1))}</a>')
        elif p.startswith("**") and p.endswith("**"):
            out.append(f"<strong>{html.escape(p[2:-2])}</strong>")
        elif p.startswith("*") and p.endswith("*") and len(p) > 2:
            out.append(f"<em>{html.escape(p[1:-1])}</em>")
        else:
            out.append(html.escape(p))
    return "".join(out)


def markdown(text: str) -> str:
    parts = []
    for block in re.split(r"\n\s*\n", text):
        b = block.strip()
        if not b:
            continue
        if b.startswith("####"):
            parts.append(f"<h2>{inline(re.sub(r'^#+\s*', '', b))}</h2>")
            continue
        lines = b.split("\n")
        if all(l.strip().startswith("|") for l in lines):
            rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines]
            rows = [r for r in rows if not all(re.match(r"^:?-+:?$", c) for c in r)]
            head, rest = rows[0], rows[1:]
            parts.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head)
                         + "</tr></thead><tbody>"
                         + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
                                   for r in rest) + "</tbody></table>")
            continue
        if all(re.match(r"^\s*(-|\d+\.)\s", l) for l in lines):
            tag = "ol" if re.match(r"^\s*\d+\.", lines[0]) else "ul"
            items = "".join(f"<li>{inline(re.sub(r'^\s*(-|\d+\.)\s*', '', l))}</li>" for l in lines)
            parts.append(f"<{tag}>{items}</{tag}>")
            continue
        parts.append(f"<p>{inline(b.replace(chr(10), ' '))}</p>")
    return "\n".join(parts)


def section(pack: dict, lang: str, site_title: str, first: bool) -> str:
    about, disc = pack["korea"]["about"], pack["korea"]["disclosures"]
    conventions = pack["korea"]["templates"]["conventions_medium"]
    cls = "" if first else ' class="break"'
    return f"""
<section lang="{lang}"{cls}>
  <h1>{html.escape(about["title"])}</h1>
  <p class="sub">{html.escape(site_title)}</p>
  {markdown(about["body"])}
  <h2>{html.escape(about["scope_title"])}</h2>
  <ul class="caption">{"".join(f"<li>{html.escape(d)}</li>" for d in disc)}</ul>
  <p class="caption">{html.escape(conventions)}</p>
</section>"""


def main() -> None:
    en = json.loads((COPY / "copy.json").read_text(encoding="utf-8"))
    ko = json.loads((COPY / "copy.ko.json").read_text(encoding="utf-8"))
    doc = ("<!doctype html><html><head><meta charset='utf-8'>"
           f"<title>{html.escape(en['korea']['about']['title'])}</title><style>{CSS}</style></head><body>"
           + section(en, "en", en["korea"]["title"], True)
           + section(ko, "ko", ko["korea"]["title"], False)
           + "</body></html>")
    src = OUT.with_suffix(".html")
    src.write_text(doc, encoding="utf-8")
    OUT.unlink(missing_ok=True)
    # Chrome under --headless=new does not reliably self-terminate: fire, poll, kill
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--user-data-dir={OUT.parent / '.chrome-profile'}",
         f"--print-to-pdf={OUT}", src.as_uri()],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while time.time() - t0 < 60 and not OUT.exists():
        time.sleep(0.5)
    time.sleep(1.0)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    src.unlink(missing_ok=True)
    if not OUT.exists():
        sys.exit("Chrome never wrote the PDF")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
