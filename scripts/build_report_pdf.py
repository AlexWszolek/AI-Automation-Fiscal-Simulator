"""Report PDF: docs/report/artifacts/docspec.json -> docs/report/report.pdf (via headless Chrome).

Third output of the SAME pipeline, so all three editions inherit the no-drift guarantee and can
never disagree with each other or the model:

    docs/report/src/*.md ─┬─> build_report_docx.py stage 1 -> docspec.json (fully resolved)
                          ├─> docx_render/render.mjs        -> report.docx   (full, Word)
                          ├─> gen_web_pages.py              -> report.html   (condensed, web)
                          └─> THIS SCRIPT                   -> report.pdf    (full, print)

The block -> HTML converters are imported from gen_web_pages rather than reimplemented; only the
layout policy differs (this edition keeps every section, honours {{pagebreak}}/{{toc}}, and styles
for paper instead of a screen).

Chrome does not implement CSS Paged Media margin boxes, so per-page numbering has to come from
Chrome's own header/footer templates (--header-footer). Default is off: cleaner for a document
whose canonical paginated edition is the .docx.

Usage:
  .venv/bin/python scripts/build_report_pdf.py                 # -> docs/report/report.pdf
  .venv/bin/python scripts/build_report_pdf.py --header-footer # page numbers, Chrome's template
  .venv/bin/python scripts/build_report_pdf.py --html-only     # emit the print HTML, skip Chrome
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from gen_web_pages import esc, runs_html, slugify, table_html  # noqa: E402

DOCSPEC = ROOT / "docs" / "report" / "artifacts" / "docspec.json"
OUT_PDF = ROOT / "docs" / "report" / "report.pdf"
OUT_HTML = ROOT / "docs" / "report" / "report_print.html"

CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome", "chromium", "chromium-browser",
)

PRINT_CSS = """
@page { size: Letter; margin: 19mm 17mm 17mm 17mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.5;
  color: #16191d; margin: 0;
}
h1, h2, h3, h4 { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #0f1216;
  line-height: 1.25; margin: 0 0 .4em; break-after: avoid; page-break-after: avoid; }
h1 { font-size: 17pt; margin-top: 0; padding-bottom: .25em; border-bottom: 2px solid #2c3540; }
h2 { font-size: 13pt; margin-top: 1.5em; }
h3 { font-size: 11pt; margin-top: 1.2em; }
h4 { font-size: 10.5pt; margin-top: 1em; font-style: italic; font-weight: 600; }
p { margin: 0 0 .65em; orphans: 3; widows: 3; text-align: justify; hyphens: auto; }
ul, ol { margin: 0 0 .7em; padding-left: 1.35em; }
li { margin-bottom: .3em; orphans: 2; widows: 2; }
code { font-family: 'SF Mono', Menlo, Consolas, monospace; font-size: .87em;
  background: #f2f4f6; padding: .06em .3em; border-radius: 3px; }
pre { font-family: 'SF Mono', Menlo, Consolas, monospace; font-size: 8.6pt; line-height: 1.42;
  background: #f6f8fa; border-left: 3px solid #c3ccd6; padding: .55em .8em; margin: 0 0 .8em;
  white-space: pre-wrap; break-inside: avoid; page-break-inside: avoid; }
blockquote { margin: 0 0 .8em; padding: .5em .9em; background: #f6f8fa;
  border-left: 3px solid #7d8c9c; font-size: .95em; break-inside: avoid; }

/* Figures and tables are the things that paginate badly — keep each intact on one page. */
figure { margin: 1em 0; break-inside: avoid; page-break-inside: avoid; text-align: center; }
figure img { max-width: 100%; max-height: 21cm; height: auto; }
figcaption { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 8.4pt;
  color: #4a5560; margin-top: .45em; text-align: left; line-height: 1.4; }
.tbl { margin: 1em 0; break-inside: avoid; page-break-inside: avoid; overflow: visible; }
table { border-collapse: collapse; width: 100%; font-family: 'Helvetica Neue', Helvetica, Arial,
  sans-serif; font-size: 8.2pt; }
th, td { border-bottom: .6pt solid #d3dae1; padding: .32em .45em; text-align: left;
  vertical-align: top; }
thead th { border-bottom: 1pt solid #2c3540; background: #eef1f4; font-weight: 600; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
tbody tr:nth-child(even) { background: #fafbfc; }

.pagebreak { break-before: page; page-break-before: always; height: 0; }
.landscape { break-before: page; page-break-before: always; }

.titleblock { text-align: center; margin: 2.2cm 0 1.6cm; }
.titleblock h1 { border: 0; font-size: 24pt; margin-bottom: .5em; }
.titleblock .stamp { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  font-size: 8.6pt; color: #5a6672; }
.toc { break-after: page; page-break-after: always; }
.toc h2 { margin-top: 0; }
.toc ol { list-style: none; padding-left: 0; font-family: 'Helvetica Neue', Helvetica, Arial,
  sans-serif; font-size: 9.5pt; }
.toc li { margin-bottom: .35em; }
.toc .l2 { padding-left: 1.2em; font-size: 9pt; color: #47525d; }
"""


def find_chrome(explicit: str | None) -> str:
    for c in ([explicit] if explicit else []) + list(CHROME_CANDIDATES):
        if c and (Path(c).exists() or shutil.which(c)):
            return c
    sys.exit("no Chrome/Chromium found — pass --chrome /path/to/binary")


def build_html(spec: dict) -> str:
    blocks = spec["blocks"]
    title, footer = spec.get("title", "Report"), spec.get("footer", "")

    # Headings first: the {{toc}} block needs them before it is emitted.
    toc_entries = [(b["level"], b["text"], slugify(b["text"]))
                   for b in blocks if b["kind"] == "heading" and 1 <= b["level"] <= 2
                   and b["text"] != title]

    parts: list[str] = []
    seen_title = False
    for b in blocks:
        k = b["kind"]
        if k == "heading":
            lvl, text = b["level"], b["text"]
            if not seen_title and text == title:
                seen_title = True
                parts.append(f"<div class='titleblock'><h1>{esc(text)}</h1>"
                             f"<div class='stamp'>{esc(footer)}</div></div>")
                continue
            tag = f"h{min(lvl, 4)}"
            anchor = f" id='{slugify(text)}'" if lvl <= 2 else ""
            parts.append(f"<{tag}{anchor}>{esc(text)}</{tag}>")
        elif k == "para":
            parts.append(f"<p>{runs_html(b['runs'])}</p>")
        elif k == "quote":
            parts.append(f"<blockquote>{runs_html(b['runs'])}</blockquote>")
        elif k == "list":
            tag = "ol" if b.get("ordered") else "ul"
            parts.append(f"<{tag}>" + "".join(f"<li>{runs_html(i)}</li>" for i in b["items"])
                         + f"</{tag}>")
        elif k == "equation":
            parts.append("<pre>" + esc("\n".join(b["lines"])) + "</pre>")
        elif k == "table":
            parts.append(table_html(b))
        elif k == "figure":
            src = Path(b["path"])
            if src.exists():                     # file:// URL — no copying, no staging directory
                parts.append(f"<figure><img src='{src.as_uri()}' alt='{esc(b.get('caption',''))}'/>"
                             f"<figcaption>{esc(b.get('caption',''))}</figcaption></figure>")
            else:
                sys.exit(f"figure missing: {src} — re-run scripts/report_artifacts.py --stage render")
        elif k == "pagebreak":
            parts.append("<div class='pagebreak'></div>")
        elif k == "section":
            # The docx uses real landscape sections for wide tables; HTML has no equivalent, so
            # start a fresh page and let the table scale to the portrait width instead.
            parts.append("<div class='landscape'></div>")
        elif k == "toc":
            items = "".join(
                f"<li class='l{lvl}'><a href='#{a}'>{esc(t)}</a></li>" for lvl, t, a in toc_entries)
            parts.append(f"<nav class='toc'><h2>Contents</h2><ol>{items}</ol></nav>")
        else:
            sys.exit(f"unknown docspec block kind {k!r} — teach build_report_pdf.py about it")

    return (f"<!doctype html>\n<html lang='en'>\n<head>\n<meta charset='utf-8'/>\n"
            f"<title>{esc(title)}</title>\n<style>{PRINT_CSS}</style>\n</head>\n<body>\n"
            + "\n".join(parts) + "\n</body>\n</html>\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_PDF)
    ap.add_argument("--chrome", default=None)
    ap.add_argument("--header-footer", action="store_true",
                    help="Chrome's own header/footer — adds page numbers, also a date and the URL")
    ap.add_argument("--html-only", action="store_true")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    if not DOCSPEC.exists():
        sys.exit(f"{DOCSPEC} absent — run scripts/build_report_docx.py first")
    spec = json.loads(DOCSPEC.read_text())
    err = None
    OUT_HTML.write_text(build_html(spec))
    print(f"print HTML → {OUT_HTML}  ({len(spec['blocks'])} blocks)")
    if args.html_only:
        return

    chrome = find_chrome(args.chrome)
    args.out.unlink(missing_ok=True)
    with __import__("tempfile").TemporaryDirectory() as profile:
        cmd = [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
               "--no-default-browser-check", f"--user-data-dir={profile}",
               # the figures are file:// URIs outside the HTML's own directory
               "--allow-file-access-from-files",
               "--virtual-time-budget=20000", f"--print-to-pdf={args.out}"]
        if not args.header_footer:
            cmd.append("--print-to-pdf-no-header")
        cmd.append(OUT_HTML.as_uri())
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
            err = f"exit {p.returncode}\n{p.stderr[-1200:]}" if not args.out.exists() else None
        except subprocess.TimeoutExpired:
            err = f"timed out after {args.timeout}s"
    if err:
        sys.exit(
            f"\nHeadless Chrome could not render the PDF ({err})\n\n"
            f"The print HTML is written and complete — it is only the browser step that failed.\n"
            f"Chrome's own headless mode is a full browser and is unreliable for batch printing\n"
            f"(it can wedge when a normal Chrome session is already running). Three ways round it:\n\n"
            f"  1. Open {OUT_HTML.name} in any browser and print to PDF (Cmd-P). Zero setup;\n"
            f"     the stylesheet is already print-targeted, so the output is the same.\n"
            f"  2. A dedicated headless binary, which does not collide with your Chrome session:\n"
            f"       npx @puppeteer/browsers install chrome-headless-shell@stable\n"
            f"       .venv/bin/python scripts/build_report_pdf.py --chrome <printed path>\n"
            f"  3. LibreOffice, converting the .docx instead — highest fidelity to the canonical\n"
            f"     paginated edition (keeps its TOC, footers and landscape sections):\n"
            f"       brew install --cask libreoffice\n"
            f"       soffice --headless --convert-to pdf docs/report/report.docx\n")
    print(f"report → {args.out}  ({args.out.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
