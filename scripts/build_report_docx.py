"""Report assembler: docs/report/src/*.md + artifacts/manifest.json -> docs/report/report.docx.

Two-stage split (the docx skill recommends docx-js for document generation):
  1. THIS script (python, no fiscal_model imports, <5s): parses the markdown sources in name
     order, resolves every placeholder against manifest.json / the artifact CSVs (FAIL LOUD on
     anything unresolved — the no-drift guarantee), and emits a fully-resolved docspec.json.
  2. scripts/docx_render/render.mjs (node + docx-js): a dumb renderer mapping docspec blocks to
     Word constructs. No content logic lives in JS.

Markdown subset (anything else fails loud): #..#### headings; paragraphs; **bold** *italic*
`code` inline; single-level - and 1. lists; fenced ``` blocks -> Equation style; | pipe tables;
> blockquote paragraphs. Placeholders:
  {{n:presets.windfall-medium.final.fed_deficit_abs_pct_gdp|.1f}}   number (dotted manifest path;
      optional format spec; modifiers: "abs," prefix, "+" sign via format spec)
  {{fig:presets.acemoglu-modest.fan_deficit|Caption text}}          figure (auto "Figure N")
  {{tbl:summary_tax:acemoglu-modest|condensed|Caption}}             per-preset fiscal summary
  {{tbl:summary_tax:acemoglu-modest|full|Caption}}                  all year columns (landscape)
  {{tbl:windfall_grid|Caption}}  {{tbl:overlay_recovery|Caption}}   built from manifest/CSVs
  {{tbl:cross_preset|Caption}}                                      cross-preset comparison
  {{toc}}  {{pagebreak}}  {{section:landscape}}  {{section:portrait}}

Usage:  .venv/bin/python scripts/build_report_docx.py [--src docs/report/src] [--check-only]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "report" / "src"
ART = ROOT / "docs" / "report" / "artifacts"
OUT = ROOT / "docs" / "report" / "report.docx"
RENDERER = ROOT / "scripts" / "docx_render" / "render.mjs"

_N = re.compile(r"\{\{n:([^}|]+)(?:\|([^}]+))?\}\}")
_INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`)")


def manifest_get(manifest: dict, dotted: str):
    cur = manifest
    for part in dotted.split("."):
        if isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(f"unresolved manifest path: {dotted!r} (failed at {part!r})")
    if cur is None:
        raise KeyError(f"manifest path {dotted!r} is null — the text must not cite it")
    return cur


def resolve_numbers(text: str, manifest: dict) -> str:
    def sub(m: re.Match) -> str:
        val = manifest_get(manifest, m.group(1).strip())
        fmt = (m.group(2) or "").strip()
        if fmt.startswith("abs,"):
            val, fmt = abs(val), fmt[4:]
        return format(val, fmt) if fmt else str(val)
    return _N.sub(sub, text)


def parse_inline(text: str) -> list:
    """-> [{t: 'plain'|'bold'|'italic'|'code', s: str}]"""
    runs = []
    for piece in _INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**"):
            runs.append({"t": "bold", "s": piece[2:-2]})
        elif piece.startswith("`") and piece.endswith("`"):
            runs.append({"t": "code", "s": piece[1:-1]})
        elif piece.startswith("*") and piece.endswith("*"):
            runs.append({"t": "italic", "s": piece[1:-1]})
        else:
            runs.append({"t": "plain", "s": piece})
    return runs


# ------------------------------------------------------------------------------ table builders
def read_csv_rows(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def fmt_b(v: str) -> str:
    try:
        return f"{float(v):,.1f}"
    except ValueError:
        return v


def summary_table(preset_key: str, mode: str, grouping: str = "tax") -> dict:
    rows = read_csv_rows(ART / "presets" / preset_key / f"summary_{grouping}.csv")
    year_cols = [c for c in rows[0] if c.startswith("Year ")]
    if mode == "condensed":
        picks = sorted({0, 1, 3, 5, len(year_cols) - 1} & set(range(len(year_cols))))
        year_cols = [year_cols[i] for i in picks]
    cols = ["Line", *year_cols, "Total"]
    out_rows, emph = [], []
    for r in rows:
        if r["kind"] == "memo" and mode == "condensed":
            continue                                     # keep the body table tight
        out_rows.append([r["label"], *[fmt_b(r[c]) for c in year_cols], fmt_b(r["Total"])])
        emph.append(r["kind"] in ("subtotal", "net"))
    first = 0.30 if mode == "condensed" else 0.22
    fracs = [first] + [(1 - first) / (len(cols) - 1)] * (len(cols) - 1)
    return {"kind": "table", "header": cols, "rows": out_rows, "emph": emph,
            "col_fracs": fracs, "font_size": 8 if mode == "full" else 9}


def windfall_table(manifest: dict) -> dict:
    grid = manifest["validation"]["windfall"]["grid"]
    order = {"low": 0, "medium": 1, "high": 2}
    rows = [[g["scenario"].capitalize(), g["capture"].capitalize(),
             f"{g['model_pct']:+.2f}%", f"{g['target_pct']:+.1f}%"]
            for g in sorted(grid, key=lambda g: (order[g["scenario"]], g["capture"] == "low"))]
    return {"kind": "table", "header": ["Scenario", "Value capture", "This model", "Windfall Trust"],
            "rows": rows, "emph": [False] * len(rows),
            "col_fracs": [0.25, 0.25, 0.25, 0.25], "font_size": 10}


def overlay_table(manifest: dict) -> dict:
    from collections import OrderedDict
    names = {"cw-robot-tax": "Robot tax (CW optimal)", "grt-robot-tax": "Robot tax (GRT trans.)",
             "ubi": "UBI $12k + 30% recapture", "compute-parity": "Compute parity 0.27"}
    header = ["Preset", *names.values()]
    rows, emph = [], []
    for pk, per in manifest["overlays"].items():
        cells = [manifest["presets"][pk]["name"]]
        for ok in names:
            d = per[ok]
            pct = f" ({d['pct_of_cum_gap']:.0f}%)" if d.get("pct_of_cum_gap") is not None else ""
            cells.append(f"{d['cum_recovery_B']:+,.0f}{pct}")
        rows.append(cells)
        emph.append(False)
    return {"kind": "table", "header": header, "rows": rows, "emph": emph,
            "col_fracs": [0.28] + [0.18] * 4, "font_size": 9}


def cross_preset_table(manifest: dict) -> dict:
    header = ["Preset", "Horizon", "Employment", "Net fiscal (final yr)", "Deficit %GDP",
              "Debt Δ", "State gap", "Final deficit P10–P90"]
    rows = []
    for v in manifest["presets"].values():
        f, m = v["final"], v["mc"]["final_fed_deficit_B"]
        rows.append([v["name"], f"{v['n_periods']}y", f"−{f['employment_drop_pct']:.0f}%",
                     f"{f['net_fiscal_impact_B']:+,.0f}", f"{f['fed_deficit_abs_pct_gdp']:.1f}%",
                     f"{f['fed_debt_B']:,.0f}", f"{f['state_gap_B']:,.0f}",
                     f"{m['p10']:,.0f} … {m['p90']:,.0f}"])
    return {"kind": "table", "header": header, "rows": rows, "emph": [False] * len(rows),
            "col_fracs": [0.22, 0.07, 0.11, 0.14, 0.10, 0.10, 0.10, 0.16], "font_size": 9}


TABLES = {"windfall_grid": windfall_table, "overlay_recovery": overlay_table,
          "cross_preset": cross_preset_table}


def static_table(lines: list[str]) -> dict:
    split = lambda ln: [c.strip() for c in ln.strip().strip("|").split("|")]
    header = split(lines[0])
    rows = [split(ln) for ln in lines[2:]]
    return {"kind": "table", "header": header, "rows": rows, "emph": [False] * len(rows),
            "col_fracs": [1 / len(header)] * len(header), "font_size": 9}


# ------------------------------------------------------------------------------ block parser
def parse_md(text: str, manifest: dict, counters: dict) -> list[dict]:
    blocks, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1
            continue
        if "{{n:" in s:                       # resolve numbers FIRST so directives may nest them
            s = resolve_numbers(s, manifest)  # in fig/tbl captions without breaking the regexes

        if s.startswith("```"):
            eq, i = [], i + 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                eq.append(resolve_numbers(lines[i], manifest))
                i += 1
            blocks.append({"kind": "equation", "lines": eq})
            i += 1
            continue
        if s.startswith("|"):
            tbl, start = [], i
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl.append(resolve_numbers(lines[i], manifest))
                i += 1
            blocks.append(static_table(tbl))
            continue
        if m := re.fullmatch(r"(#{1,4})\s+(.*)", s):
            blocks.append({"kind": "heading", "level": len(m.group(1)),
                           "text": resolve_numbers(m.group(2), manifest)})
            i += 1
            continue
        if s in ("{{toc}}", "{{pagebreak}}", "{{section:landscape}}", "{{section:portrait}}"):
            blocks.append({"kind": s[2:-2].split(":")[0],
                           **({"orientation": s[2:-2].split(":")[1]} if ":" in s else {})})
            i += 1
            continue
        if m := re.fullmatch(r"\{\{fig:([^}|]+)\|([^}]+)\}\}", s):
            path = manifest_get(manifest, m.group(1).strip() if "figures" in m.group(1)
                                else _fig_path(m.group(1).strip()))
            f = ART / path
            if not f.exists():
                raise FileNotFoundError(f"figure missing: {f}")
            counters["fig"] += 1
            blocks.append({"kind": "figure", "path": str(f),
                           "caption": f"Figure {counters['fig']} — "
                                      f"{resolve_numbers(m.group(2).strip(), manifest)}"})
            i += 1
            continue
        if m := re.fullmatch(r"\{\{tbl:([^}|]+)(?:\|([^}|]+))?\|([^}]+)\}\}", s):
            spec, mode, caption = m.group(1).strip(), (m.group(2) or "").strip(), m.group(3).strip()
            if spec.startswith(("summary_tax:", "summary_channel:")):
                grouping, key = spec.split(":", 1)
                t = summary_table(key, mode or "condensed", grouping.split("_")[1])
            elif spec in TABLES:
                t = TABLES[spec](manifest)
            else:
                raise KeyError(f"unknown table spec: {spec!r}")
            counters["tbl"] += 1
            t["caption"] = f"Table {counters['tbl']} — {resolve_numbers(caption, manifest)}"
            blocks.append(t)
            i += 1
            continue
        if s.startswith("- ") or re.match(r"\d+\.\s", s):
            ordered = not s.startswith("- ")
            items = []
            while i < len(lines) and (lines[i].strip().startswith("- ")
                                      or re.match(r"\d+\.\s", lines[i].strip())):
                item = re.sub(r"^(-|\d+\.)\s+", "", lines[i].strip())
                items.append(parse_inline(resolve_numbers(item, manifest)))
                i += 1
            blocks.append({"kind": "list", "ordered": ordered, "items": items})
            continue
        if s.startswith("{{"):
            raise ValueError(f"unrecognized directive: {s}")
        # paragraph: greedy join of consecutive plain lines (blockquote > kept as a styled para).
        # Each continuation line is number-resolved BEFORE the block-boundary test — a hard-wrapped
        # line beginning with an inline {{n:...}} must read as prose, not as a directive (an
        # unresolved "{{" prefix here would neither match a branch nor advance i: infinite loop).
        quote = s.startswith("> ")
        para = []
        while i < len(lines) and lines[i].strip():
            nxt = lines[i].strip()
            if "{{n:" in nxt:
                nxt = resolve_numbers(nxt, manifest)
            if nxt.startswith(("#", "|", "```", "- ", "{{")) or re.match(r"\d+\.\s", nxt):
                break
            para.append(nxt.lstrip("> ") if quote else nxt)
            i += 1
        assert para, f"parser stalled on line {i}: {lines[i]!r}"     # fail loud, never spin
        blocks.append({"kind": "quote" if quote else "para",
                       "runs": parse_inline(" ".join(para))})
    return blocks


def _fig_path(short: str) -> str:
    """`presets.<key>.<figname>` or `comparison.<figname>` -> manifest figures registry path."""
    parts = short.split(".")
    if parts[0] == "presets":
        return f"presets.{parts[1]}.figures.{parts[2]}"
    if parts[0] == "comparison":
        return f"comparison.figures.{parts[1]}"
    raise KeyError(f"unknown figure shorthand: {short!r}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--check-only", action="store_true",
                    help="resolve everything but skip the node render")
    args = ap.parse_args()

    manifest = json.loads((ART / "manifest.json").read_text())
    counters = {"fig": 0, "tbl": 0}
    blocks = []
    files = sorted(args.src.glob("*.md"))
    if not files:
        sys.exit(f"no markdown sources in {args.src}")
    for f in files:
        blocks.extend(parse_md(f.read_text(), manifest, counters))

    docspec = {
        "title": "The Fiscal Consequences of AI Automation",
        "footer": f"AI Automation Fiscal Model — technical report · {manifest['git_sha']} · "
                  f"{manifest['generated']} · seed {manifest['config']['seed']}, "
                  f"N={manifest['config']['n']}",
        "blocks": blocks,
    }
    spec_path = ART / "docspec.json"
    spec_path.write_text(json.dumps(docspec, indent=1))
    print(f"docspec: {len(blocks)} blocks, {counters['fig']} figures, {counters['tbl']} tables")
    if args.check_only:
        return
    r = subprocess.run(["node", str(RENDERER), str(spec_path), str(args.out)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"render failed:\n{r.stdout}\n{r.stderr}")
    print(r.stdout.strip())
    print(f"report → {args.out}")


if __name__ == "__main__":
    main()
