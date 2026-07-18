"""Extract the app's user-facing copy into web/src/content/copy.json — the mechanical port.

The site's copy is the USER'S (hand-edited via the website_copy.xlsx round); it migrates
byte-for-byte from app/streamlit_app.py, never retyped. This walks the app AST and emits, per
sidebar lever (keyed by the ui/grid key), its label + help text, plus section headings, chart
captions, metric labels/helps, the intro, warnings, and the About/Learn-more bodies.

Widget → ui-key mapping: the app assigns each widget to a variable (cog = st.slider(...));
the VARMAP below pins variable name → grid key and is asserted complete against UI_GRID.

Run:  .venv/bin/python scripts/extract_web_copy.py   (tests/test_web_gen.py gates freshness)
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fiscal_model.app_params import UI_GRID                      # noqa: E402

APP = ROOT / "app" / "streamlit_app.py"
OUT = ROOT / "web" / "src" / "content" / "copy.json"

# widget variable name -> ui/grid key (asserted complete against UI_GRID below)
VARMAP = {
    "cog": "cog", "phys": "phys", "robotics_lag": "robotics_lag", "rob_base": "rob_base",
    "adopt0": "adopt0", "adopt1": "adopt1", "n_periods": "n_periods",
    "reab": "reab", "haircut": "haircut", "reab_baumol": "reab_baumol",
    "reab_crowd": "reab_crowd", "ui_weeks": "ui_weeks", "lfp_exit": "lfp",
    "attrition": "attrition",
    "retained": "retained", "price": "price", "auto_cost": "auto_cost",
    "compute_rate": "compute_rate",
    "survivor_unbounded": "unbounded", "ceiling": "ceiling", "elasticity": "elasticity",
    "spillover": "spillover",
    "price_pt": "price_pt", "prod_pt": "prod_pt", "growth": "growth", "demand": "demand",
    "income_mult": "income_mult", "corp_mult": "corp_mult", "cons_mult": "cons_mult",
    "automation_tax": "atax", "ubi": "ubi", "ubi_recapture": "ubi_recapture",
    "interest": "interest",
    "state_resp": "state_resp", "state_cut_share": "state_cut", "rate_cap": "rate_cap",
}


def const_str(node) -> str | None:
    """A plain or implicitly-concatenated constant string (help texts are adjacent literals)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def extract() -> dict:
    tree = ast.parse(APP.read_text())
    levers: dict[str, dict] = {}
    groups: list[dict] = []           # sidebar expander order: {title, expanded, keys[]}
    metrics: list[dict] = []          # metric label + help in render order
    subheaders: list[str] = []
    captions: list[str] = []          # chart captions via show_chart(..., "caption")

    current_group = None
    for node in ast.walk(tree):
        # sidebar groups: `with sb.expander("title", expanded=..)` — record order + membership
        if isinstance(node, ast.With):
            for item in node.items:
                c = item.context_expr
                if (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                        and c.func.attr == "expander" and c.args
                        and isinstance(c.func.value, ast.Name) and c.func.value.id == "sb"):
                    title = const_str(c.args[0])
                    expanded = any(kw.arg == "expanded" and getattr(kw.value, "value", False)
                                   for kw in c.keywords)
                    if title and title not in ("Share this configuration", "About this model"):
                        current_group = {"title": title, "expanded": expanded, "keys": []}
                        groups.append(current_group)
                        # source order + dedupe: branch-duplicated widgets (price/atax clamps)
                        # appear once, and ast.walk's breadth-first order is repaired by lineno
                        found = []
                        for sub in ast.walk(node):
                            if isinstance(sub, ast.Assign) and len(sub.targets) == 1 \
                                    and isinstance(sub.targets[0], ast.Name):
                                var = sub.targets[0].id
                                if var in VARMAP:
                                    found.append((sub.lineno, VARMAP[var]))
                        seen = set()
                        for _ln, k in sorted(found):
                            if k not in seen:
                                seen.add(k)
                                current_group["keys"].append(k)

        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                # subheaders + chart captions + metrics on st/columns
                if node.func.attr == "subheader" and node.args:
                    t = const_str(node.args[0])
                    if t:
                        subheaders.append(t)
                if node.func.attr == "metric" and node.args:
                    label = const_str(node.args[0])
                    hlp = next((const_str(kw.value) for kw in node.keywords if kw.arg == "help"),
                               None)
                    if label:
                        metrics.append({"label": label, "help": hlp})
            continue

        call = node.value
        if not (isinstance(call.func, ast.Attribute)
                and call.func.attr in ("slider", "selectbox", "checkbox")):
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in VARMAP:
            continue
        label = const_str(call.args[0]) if call.args else None
        hlp = next((const_str(kw.value) for kw in call.keywords if kw.arg == "help"), None)
        levers[VARMAP[target.id]] = {"label": label, "help": hlp,
                                     "widget": call.func.attr}

    # chart captions ride show_chart(chart, "...") calls
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "show_chart" and len(node.args) >= 2):
            t = const_str(node.args[1])
            if t:
                captions.append(t)

    # module-level prose constants: intro markdown, About body, Learn-more markdown
    intro = about = learn_more = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id == "_LEARN_MORE_MD":
            learn_more = const_str(node.value)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "markdown" and node.args):
            t = const_str(node.args[0])
            if t and t.startswith("How to use this:"):
                intro = t
            if t and t.startswith("A bottom-up accounting model"):
                about = t

    missing = set(UI_GRID) - set(levers)
    # widgets rendered in the main area (state response trio) are still in VARMAP; anything
    # truly missing means the app changed shape — fail loud
    assert not missing, f"levers missing from the extraction: {sorted(missing)}"
    return {"levers": levers, "groups": groups, "metrics": metrics,
            "subheaders": subheaders, "captions": captions,
            "intro": intro, "about": about, "learn_more": learn_more}


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(extract(), indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
