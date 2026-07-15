"""Freshness gate for the app's precomputed tornado artifact — editing a preset (or
CUSTOM_DEFAULTS, or any V2Params field) without re-running scripts/precompute_app_mc.py must turn
the suite red, not silently degrade every preset to a 60-second live recompute."""
import json
from pathlib import Path

import pytest

from fiscal_model import app_params as ap
from fiscal_model import presets

ARTIFACT = Path(__file__).resolve().parent.parent / "data" / "app_precomputed" / "mc_tornado.json"


@pytest.fixture(scope="module")
def payload():
    if not ARTIFACT.exists():
        pytest.fail(f"{ARTIFACT} missing — run scripts/precompute_app_mc.py (it is a committed "
                    "artifact; presets must render their tornado instantly)")
    return json.loads(ARTIFACT.read_text())


def test_every_config_present(payload):
    keys = {e["key"] for e in payload["entries"]}
    assert keys == set(presets.PRESETS) | {"custom"}


def test_cfg_reprs_match_source(payload):
    """The stored keys must equal cfg_key() recomputed from today's source — the app matches on
    exact repr, so any drift means stale artifacts."""
    stored = {e["key"]: e["cfg_repr"] for e in payload["entries"]}
    assert stored["custom"] == ap.cfg_key(ap.build_v2_params(
        ap.ui_from_defaults(dict(ap.CUSTOM_DEFAULTS), rung=1)))
    for key, p in presets.PRESETS.items():
        ui = ap.ui_from_defaults(ap.preset_widget_defaults(p), rung=1, preset=p)
        assert stored[key] == ap.cfg_key(ap.build_v2_params(ui)), \
            f"{key}: precomputed artifact is stale — re-run scripts/precompute_app_mc.py"


def test_entries_are_renderable(payload):
    for e in payload["entries"]:
        assert e["tornado"] and all({"lever", "spearman"} <= set(t) for t in e["tornado"])
        assert e["p10"] <= e["p50"] <= e["p90"]
    assert payload["n"] == 200 and payload["seed"] == 0
