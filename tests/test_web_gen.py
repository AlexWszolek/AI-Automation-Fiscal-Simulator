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


def test_copy_json_fresh():
    """The mechanically-ported copy must track the app — editing app copy without re-running
    scripts/extract_web_copy.py goes red here."""
    spec = importlib.util.spec_from_file_location("extract_web_copy",
                                                  ROOT / "scripts" / "extract_web_copy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    committed = json.loads((ROOT / "web" / "src" / "content" / "copy.json").read_text())
    assert json.loads(json.dumps(mod.extract(), sort_keys=True, ensure_ascii=False)) == committed, \
        "web/src/content/copy.json is stale — re-run scripts/extract_web_copy.py"
