"""Freshness gate for the web front end's generated artifacts — editing app_params / presets
without re-running scripts/gen_web_bundle.py must turn the suite red, not silently hand the TS
side a stale grid or stale golden vectors (the test_app_precomputed pattern)."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "web" / "src" / "gen"


@pytest.fixture(scope="module")
def genmod():
    spec = importlib.util.spec_from_file_location("gen_web_bundle",
                                                  ROOT / "scripts" / "gen_web_bundle.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _committed(name: str) -> dict:
    p = GEN / name
    if not p.exists():
        pytest.fail(f"{p} missing — run scripts/gen_web_bundle.py --grid-only")
    return json.loads(p.read_text())


def test_grid_json_fresh(genmod):
    assert json.loads(json.dumps(genmod.build_grid(), sort_keys=True, allow_nan=False)) \
        == _committed("grid.json"), \
        "web/src/gen/grid.json is stale — re-run scripts/gen_web_bundle.py --grid-only"


def test_codec_vectors_fresh(genmod):
    assert json.loads(json.dumps(genmod.build_codec_vectors(), sort_keys=True, allow_nan=False)) \
        == _committed("codec_vectors.json"), \
        "web/src/gen/codec_vectors.json is stale — re-run scripts/gen_web_bundle.py --grid-only"


def test_grid_covers_every_ui_key(genmod):
    from fiscal_model.app_params import UI_GRID
    grid = _committed("grid.json")["grid"]
    assert set(grid) == set(UI_GRID)


def test_copy_json_wellformed():
    """copy.json is HAND-MAINTAINED since copy round 2 (the Streamlit extractor is retired —
    Decisions tab of docs/website_copy_round2.xlsx). This guards structure, not provenance:
    the keys the components import must exist and be non-empty."""
    committed = json.loads((ROOT / "web" / "src" / "content" / "copy.json").read_text())
    for key in ("about", "captions", "groups", "intro", "learn_more", "levers",
                "metrics", "prose", "subheaders"):
        assert committed.get(key), f"copy.json missing/empty top-level key {key!r}"
    for k, lever in committed["levers"].items():
        assert lever.get("label"), f"levers.{k} has no label"


def test_web_pages_fresh():
    """report.html / evidence.html must track the docspec + evidence markdown — regenerate via
    scripts/gen_web_pages.py after report or evidence changes."""
    spec = importlib.util.spec_from_file_location("gen_web_pages",
                                                  ROOT / "scripts" / "gen_web_pages.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.build_report() == (ROOT / "web" / "public" / "report.html").read_text(), \
        "web/public/report.html is stale — re-run scripts/gen_web_pages.py"
    assert mod.build_evidence() == (ROOT / "web" / "public" / "evidence.html").read_text(), \
        "web/public/evidence.html is stale — re-run scripts/gen_web_pages.py"


def test_print_edition_covers_every_block_kind():
    """The PDF/print edition renders the FULL docspec, so a new block kind must not be silently
    dropped (the web edition filters sections; this one must not). build_report_pdf.build_html
    exits on an unknown kind — this asserts it survives today's docspec and keeps every section."""
    spec = importlib.util.spec_from_file_location("build_report_pdf",
                                                  ROOT / "scripts" / "build_report_pdf.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not mod.DOCSPEC.exists():
        pytest.skip("docspec.json absent — run scripts/build_report_docx.py")
    docspec = json.loads(mod.DOCSPEC.read_text())
    html = mod.build_html(docspec)

    n_h1 = sum(1 for b in docspec["blocks"] if b["kind"] == "heading" and b["level"] == 1)
    assert html.count("<h1") + html.count("<div class='titleblock'>") >= n_h1, \
        "print edition dropped a top-level section"
    for b in docspec["blocks"]:
        if b["kind"] == "figure":
            assert Path(b["path"]).as_uri() in html, f"figure missing from print edition: {b['path']}"
