"""Freshness gate for the app's precomputed tornado artifact — editing a preset, an overlay,
CUSTOM_DEFAULTS, or any V2Params field without re-running scripts/precompute_app_mc.py must turn
the suite red, not silently degrade a preset+response cart to a 60-second live recompute."""
import json
from itertools import combinations
from pathlib import Path

import pytest

from fiscal_model import app_params as ap
from fiscal_model import presets, webpayload

ARTIFACT = Path(__file__).resolve().parent.parent / "data" / "app_precomputed" / "mc_tornado.json"


def pristine_configs() -> list[dict]:
    """Every preset/custom × valid overlay subset — the same enumeration the precompute script
    and scripts/gen_web_bundle.py use (both robot taxes together is invalid)."""
    ov_keys = list(presets.OVERLAYS)
    subsets = [list(c) for r in range(len(ov_keys) + 1) for c in combinations(ov_keys, r)
               if not {"cw-robot-tax", "grt-robot-tax"} <= set(c)]
    return [{"preset": p, "overlays": ovs, "levers": {}}
            for p in [None] + list(presets.PRESETS) for ovs in subsets]


@pytest.fixture(scope="module")
def payload():
    if not ARTIFACT.exists():
        pytest.fail(f"{ARTIFACT} missing — run scripts/precompute_app_mc.py (it is a committed "
                    "artifact; presets must render their tornado instantly)")
    return json.loads(ARTIFACT.read_text())


def test_every_config_present(payload):
    keys = {e["key"] for e in payload["entries"]}
    expected = {webpayload.slug(cfg) for cfg in pristine_configs()}
    assert len(expected) == 120
    assert keys == expected


def test_cfg_reprs_match_source(payload):
    """The stored keys must equal cfg_key() recomputed from today's source — the app matches on
    exact repr, so any drift means stale artifacts."""
    stored = {e["key"]: e["cfg_repr"] for e in payload["entries"]}
    for cfg in pristine_configs():
        slug = webpayload.slug(cfg)
        assert stored[slug] == webpayload.cfg_repr_for(cfg), \
            f"{slug}: precomputed artifact is stale — re-run scripts/precompute_app_mc.py"


def test_entries_are_renderable(payload):
    for e in payload["entries"]:
        assert e["tornado"] and all({"lever", "spearman"} <= set(t) for t in e["tornado"])
        assert e["p10"] <= e["p50"] <= e["p90"]
    assert payload["n"] == 200 and payload["seed"] == 0
