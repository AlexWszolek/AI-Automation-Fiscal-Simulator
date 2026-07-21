"""Generate the site's document pages — web/public/report.html + evidence.html.

The REPORT page renders from docs/report/artifacts/docspec.json — the fully-RESOLVED block
stream stage 1 of build_report_docx.py emits (every {{n:}}/{{fig:}}/{{tbl:}} already substituted
against the manifest), so the web edition inherits the no-drift guarantee and can never disagree
with the docx or the model. It is the condensed edition: intro, findings, validation,
simplifications, conclusion, and the appendices; the construction sections (data → calibration)
live in the full docx. Referenced figures are copied to web/public/report-figures/.

The EVIDENCE page renders docs/PRESET_EVIDENCE.md through a small tolerant markdown converter
(headings, lists with hanging indents, pipe tables, bold/italic/code/links, hr).

Self-contained HTML (embedded CSS from the design tokens) — served as static files, no React.
tests/test_web_gen.py holds the freshness gate. Run:  .venv/bin/python scripts/gen_web_pages.py
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DOCSPEC = ROOT / "docs" / "report" / "artifacts" / "docspec.json"
EVIDENCE_MD = ROOT / "docs" / "PRESET_EVIDENCE.md"
OUT_DIR = ROOT / "web" / "public"
FIG_DIR = OUT_DIR / "report-figures"
GH = "https://github.com/AlexWszolek/AI-Automation-Fiscal-Simulator/blob/main"

# the condensed web edition: front matter + these numbered/appendix h1 sections
KEEP_H1 = ("1.", "7.", "9.", "10.", "11.", "Appendix")

PAGE_CSS = """
@font-face { font-family:'Charis SIL'; font-weight:400; font-display:swap;
             src:url('/fonts/charis-400.woff2') format('woff2'); }
@font-face { font-family:'Charis SIL'; font-weight:700; font-display:swap;
             src:url('/fonts/charis-700.woff2') format('woff2'); }
:root {
  --bg-page:#fcfbf8; --bg-panel:#fefdfb; --bg-well:#f4f2ec; --ink:#1a1a18; --ink-2:#3d3d3a;
  --ink-3:#6e6e68; --line:#e2dfd7; --bad:#8c2f28; --good:#5b7c99; --accent:#2c5f8a;
  --serif:Charter, 'Bitstream Charter', 'Charis SIL', 'XCharter', serif;
  --mono:ui-monospace,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace;
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg-page); color:var(--ink); font-family:var(--serif);
       font-size:17px; line-height:1.55; }
.page { max-width: 860px; margin: 0 auto; padding: 1.4rem 1.6rem 5rem; }
.topnav { border-bottom:1px solid var(--line); padding-bottom:0.7rem; margin-bottom:2rem;
          display:flex; justify-content:space-between; align-items:baseline; gap:1rem;
          flex-wrap:wrap; }
.topnav a { color:var(--accent); }
.topnav .site { font-weight:700; font-size:1.05rem; color:var(--ink); text-decoration:none; }
h1 { font-size:1.9rem; line-height:1.15; margin:2.4rem 0 0.5rem; }
h2 { font-size:1.4rem; margin:2rem 0 0.4rem; }
h3 { font-size:1.12rem; margin:1.5rem 0 0.3rem; color:var(--ink-2); }
h4 { margin:1.2rem 0 0.3rem; }
a { color:var(--accent); text-underline-offset:2px; }
.caption, figcaption { color:var(--ink-3); font-size:0.88rem; line-height:1.4; }
blockquote { border-left:3px solid var(--line); margin:1rem 0; padding:0.2rem 0 0.2rem 1rem;
             color:var(--ink-2); }
pre { background:var(--bg-well); border:1px solid var(--line); border-radius:4px;
      padding:0.7rem 0.9rem; overflow-x:auto; font-family:var(--mono); font-size:0.82rem;
      line-height:1.45; }
code { font-family:var(--mono); font-size:0.86em; background:var(--bg-well);
       padding:0.05em 0.3em; border-radius:3px; }
pre code { background:none; padding:0; }
.tbl { overflow-x:auto; margin:0.8rem 0; }
table { border-collapse:collapse; width:100%; font-size:0.85rem; }
th { background:var(--bg-well); color:var(--ink-2); text-align:left; padding:0.4rem 0.6rem;
     border-bottom:1px solid var(--line); }
td { padding:0.3rem 0.6rem; border-bottom:1px solid var(--line); vertical-align:top; }
td.num, th.num { text-align:right; font-family:var(--mono); font-variant-numeric:tabular-nums;
                 white-space:nowrap; }
figure { margin:1.4rem 0; }
figure img { max-width:100%; height:auto; border:1px solid var(--line); border-radius:4px;
             background:white; }
hr { border:0; border-top:1px solid var(--line); margin:2rem 0; }
.toc { background:var(--bg-panel); border:1px solid var(--line); border-radius:4px;
       padding:0.9rem 1.2rem; margin:1.2rem 0 2rem; }
.toc a { display:block; padding:0.12rem 0; text-decoration:none; }
.note { background:var(--bg-panel); border:1px solid var(--line); border-radius:4px;
        padding:0.7rem 1rem; }
ul, ol { padding-left:1.5rem; }
li { margin:0.25rem 0; }
"""

_NUMRE = re.compile(r"^[\s$€]*[−\-+]?[\d,.]+[%×xB TM]*$")


def esc(s: str) -> str:
    return html.escape(str(s), quote=False)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def shell(title: str, nav_extra: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{esc(title)}</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<div class="page">
<nav class="topnav">
  <a class="site" href="/">Fiscal Consequences of AI Automation</a>
  <span>{nav_extra}</span>
</nav>
{body}
</div>
</body>
</html>
"""


# ------------------------------------------------------------------ report (from docspec)
def runs_html(runs: list[dict]) -> str:
    out = []
    for r in runs:
        s = esc(r["s"])
        t = r.get("t", "plain")
        if t == "bold":
            out.append(f"<strong>{s}</strong>")
        elif t == "italic":
            out.append(f"<em>{s}</em>")
        elif t == "code":
            out.append(f"<code>{s}</code>")
        else:
            out.append(s)
    return "".join(out)


def table_html(b: dict) -> str:
    head = "".join(
        f"<th{' class=num' if i > 0 else ''}>{esc(h)}</th>" for i, h in enumerate(b["header"]))
    rows = []
    for row in b["rows"]:
        tds = []
        for i, cell in enumerate(row):
            numeric = i > 0 and _NUMRE.match(str(cell).strip() or "x") is not None
            tds.append(f"<td{' class=num' if numeric else ''}>{esc(cell)}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return (f"<div class='tbl'><table><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def build_report() -> str:
    spec = json.loads(DOCSPEC.read_text())
    blocks = spec["blocks"]

    kept: list[dict] = []
    keeping = True                       # front matter (title + abstract) is kept
    for b in blocks:
        if b["kind"] in ("pagebreak", "toc", "section"):
            continue
        if b["kind"] == "heading" and b["level"] == 1:
            t = b["text"]
            numbered = t[:1].isdigit() or t.startswith("Appendix")
            keeping = (not numbered) or t.startswith(KEEP_H1)
        if keeping:
            kept.append(b)

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    parts: list[str] = []
    toc: list[tuple[str, str]] = []
    for b in kept:
        k = b["kind"]
        if k == "heading":
            text = b["text"]
            if b["level"] == 1 and (text.startswith(KEEP_H1)):
                anchor = slugify(text)
                toc.append((text, anchor))
                parts.append(f"<h1 id='{anchor}'>{esc(text)}</h1>")
            else:
                parts.append(f"<h{min(b['level'], 4)}>{esc(text)}</h{min(b['level'], 4)}>")
        elif k == "para":
            parts.append(f"<p>{runs_html(b['runs'])}</p>")
        elif k == "quote":
            parts.append(f"<blockquote>{runs_html(b['runs'])}</blockquote>")
        elif k == "list":
            tag = "ol" if b.get("ordered") else "ul"
            items = "".join(f"<li>{runs_html(item)}</li>" for item in b["items"])
            parts.append(f"<{tag}>{items}</{tag}>")
        elif k == "equation":
            parts.append("<pre>" + esc("\n".join(b["lines"])) + "</pre>")
        elif k == "table":
            parts.append(table_html(b))
        elif k == "figure":
            src = Path(b["path"])
            if src.exists():
                # per-preset figures share basenames (fan_deficit.png etc.) — qualify with the
                # parent directory so they don't overwrite each other
                name = f"{src.parent.name}-{src.name}" if src.parent.name != "artifacts" else src.name
                shutil.copyfile(src, FIG_DIR / name)
                parts.append(f"<figure><img src='/report-figures/{name}' loading='lazy' "
                             f"alt='{esc(b.get('caption', ''))}' />"
                             f"<figcaption>{esc(b.get('caption', ''))}</figcaption></figure>")

    toc_html = "<div class='toc'>" + "".join(
        f"<a href='#{a}'>{esc(t)}</a>" for t, a in toc) + "</div>"
    note = ("<p class='note caption'>This is the condensed web edition. The construction "
            "sections — data, the static kernel, the dynamic model, correctness discipline, and "
            "calibration — are in the "
            f"<a href='{GH}/docs/report/report.docx'>full report (.docx)</a>; a plain-language "
            "summary is in the tool's <em>Learn more</em>. Every number here is resolved from "
            "the same generated manifest as the document and the site.</p>")

    body_parts = parts[:1] + [note, toc_html] + parts[1:] if parts else parts
    return shell("Technical report — Fiscal Consequences of AI Automation",
                 f"<a href='/evidence.html'>Preset evidence</a> · "
                 f"<a href='{GH}/docs/report/report.docx'>full .docx</a>",
                 "\n".join(body_parts))


# ------------------------------------------------------------------ evidence (markdown)
_INLINE = re.compile(r"(\[[^\]]+\]\([^)]+\)|`[^`]+`|\*\*[^*]+\*\*|\*[^*\s][^*]*\*)")


def inline_html(text: str) -> str:
    out = []
    pos = 0
    for m in _INLINE.finditer(text):
        out.append(esc(text[pos:m.start()]))
        tok = m.group(0)
        if tok.startswith("["):
            lm = re.match(r"\[([^\]]+)\]\(([^)]+)\)", tok)
            href = lm.group(2)
            if not href.startswith(("http", "#", "/")):
                href = f"{GH}/docs/{href}"          # repo-relative doc links -> GitHub
            out.append(f"<a href='{esc(href)}'>{inline_html(lm.group(1))}</a>")
        elif tok.startswith("`"):
            out.append(f"<code>{esc(tok[1:-1])}</code>")
        elif tok.startswith("**"):
            out.append(f"<strong>{inline_html(tok[2:-2])}</strong>")
        else:
            out.append(f"<em>{inline_html(tok[1:-1])}</em>")
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def md_blocks(text: str) -> list[str]:
    """Tolerant converter for PRESET_EVIDENCE.md's markdown subset."""
    parts: list[str] = []
    toc: list[tuple[str, str]] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            t = line.lstrip("# ").strip()
            if level == 2:
                anchor = slugify(t)
                toc.append((t, anchor))
                parts.append(f"<h2 id='{anchor}'>{inline_html(t)}</h2>")
            else:
                parts.append(f"<h{min(level, 4)}>{inline_html(t)}</h{min(level, 4)}>")
            i += 1
        elif line.strip() == "---":
            parts.append("<hr />")
            i += 1
        elif line.lstrip().startswith("|"):
            tbl = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                tbl.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            body = [r for r in tbl if not all(re.fullmatch(r":?-+:?", c or "-") for c in r)]
            head, rest = body[0], body[1:]
            h = "".join(f"<th>{inline_html(c)}</th>" for c in head)
            rows = "".join("<tr>" + "".join(f"<td>{inline_html(c)}</td>" for c in r) + "</tr>"
                           for r in rest)
            parts.append(f"<div class='tbl'><table><thead><tr>{h}</tr></thead>"
                         f"<tbody>{rows}</tbody></table></div>")
        elif re.match(r"^\s*(-|\d+\.)\s", line):
            ordered = bool(re.match(r"^\s*\d+\.", line))
            items = []
            while i < len(lines) and lines[i].strip():
                if re.match(r"^\s*(-|\d+\.)\s", lines[i]):
                    items.append(re.sub(r"^\s*(-|\d+\.)\s*", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()      # hanging-indent continuation
                i += 1
            tag = "ol" if ordered else "ul"
            parts.append(f"<{tag}>" + "".join(f"<li>{inline_html(it)}</li>" for it in items)
                         + f"</{tag}>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|")) \
                    and lines[i].strip() != "---" and not re.match(r"^\s*(-|\d+\.)\s", lines[i]):
                para.append(lines[i].strip())
                i += 1
            parts.append(f"<p>{inline_html(' '.join(para))}</p>")
    if toc:
        toc_html = "<div class='toc'>" + "".join(
            f"<a href='#{a}'>{esc(t)}</a>" for t, a in toc) + "</div>"
        # insert after the first h1 + lead paragraph
        for j, p in enumerate(parts):
            if p.startswith("<p>"):
                parts.insert(j + 1, toc_html)
                break
    return parts


def build_evidence() -> str:
    parts = md_blocks(EVIDENCE_MD.read_text())
    return shell("Preset evidence — Fiscal Consequences of AI Automation",
                 "<a href='/report.html'>Technical report</a>",
                 "\n".join(parts))


def main() -> None:
    (OUT_DIR / "report.html").write_text(build_report())
    print("wrote web/public/report.html")
    (OUT_DIR / "evidence.html").write_text(build_evidence())
    print("wrote web/public/evidence.html")


if __name__ == "__main__":
    main()
