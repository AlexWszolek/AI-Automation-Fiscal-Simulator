"""The Korea ScenarioPayload: sanitizer hostility, static ≡ live discipline, the prefix
property the one-run design rests on, and agreement with the bundle's pinned numbers."""
import numpy as np
import pytest

from fiscal_model.korea_cells import PAYM39_CSV

pytestmark = pytest.mark.skipif(
    not PAYM39_CSV.exists(),
    reason="Korea tidy CSV not built — scripts/fetch_korea_tables.py --parse-only")


@pytest.fixture(scope="module")
def pools():
    from fiscal_model.korea_assembly import build_korea_deltas
    return {"data_pool": {}, "deltas": build_korea_deltas(), "ctx_pool": {}}


@pytest.fixture(scope="module")
def central(pools):
    from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                               sanitize_korea_config)
    return build_korea_scenario_payload(sanitize_korea_config({}), **pools)


def test_sanitizer_survives_hostile_bodies():
    from fiscal_model.korea_webpayload import sanitize_korea_config
    cfg = sanitize_korea_config({
        "preset": "agi-5y",                       # US preset key: not a Korea preset → central
        "levers": {"ui_weeks": 400, "mpc": "NaN", "bogus": 9, "adoption_end": -3,
                   "exposure_delta": 0.31, "nhi_share": 2.0,
                   "cognitive_feasibility": 0.0,  # a PINNED convention: must be dropped
                   "demography_path": [1]}})      # structural: must be dropped
    assert cfg["preset"] == "korea-central"
    assert cfg["levers"]["ui_weeks"] == 52                      # clamped, int
    assert cfg["levers"]["adoption_end"] == 0.005               # clamped to floor
    assert cfg["levers"]["exposure_delta"] == 0.5               # snapped to the read grid
    assert cfg["levers"]["nhi_share"] == 0.97                   # clamped to the band
    for k in ("mpc", "bogus", "cognitive_feasibility", "demography_path"):
        assert k not in cfg["levers"]


def test_default_payload_matches_the_bundle_pins(central):
    f = central["final"]
    assert f["nhi_years_forward"] == pytest.approx(0.50, abs=0.01)
    assert f["nps_given_back"] == pytest.approx(1.14, abs=0.01)
    assert f["ei_shortfall_tn"] == pytest.approx(5.5, abs=0.1)
    assert f["employment_drop_pct"] == pytest.approx(8.95, abs=0.1)
    assert central["config"]["modified_fields"] == []
    assert len(central["rows"]) == 10                           # display horizon, not 40
    assert len(central["funds"]["nps"]["years"]) == 40          # funds get the full window


def test_envelope_contains_central_and_respects_publication(central):
    for key, f in central["funds"].items():
        lo, c, hi = map(np.asarray, (f["eroded_lo"], f["eroded"], f["eroded_hi"]))
        assert (lo <= c + 1e-9).all() and (c <= hi + 1e-9).all(), key
        assert (hi <= np.asarray(f["published"]) + 1e-9).all(), key
    assert central["funds"]["ei"]["years_pulled_forward"] is None   # shortfall story


def test_levers_actually_move_the_payload(pools):
    from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                               sanitize_korea_config)
    p = build_korea_scenario_payload(
        sanitize_korea_config({"levers": {"ui_weeks": 39, "adoption_end": 0.30}}), **pools)
    assert p["config"]["modified_fields"] == ["adoption_end", "ui_weeks"]
    assert p["final"]["ei_shortfall_tn"] > 8.0        # longer window + more adoption
    assert p["final"]["nhi_years_forward"] > 0.60


def test_prefix_property_pins_the_one_run_design(pools):
    """rows sliced from the 40-year run must equal a native 10-year run — if a future
    mechanism reads the horizon (terminal condition, backward pass), this catches it."""
    from fiscal_model.korea_assembly import run_korea_preset
    r10 = run_korea_preset("korea-central", n_periods=10,
                           data=pools["data_pool"][0.0], deltas=pools["deltas"])["res"]
    r40 = run_korea_preset("korea-central", n_periods=40,
                           data=pools["data_pool"][0.0], deltas=pools["deltas"])["res"]
    num = r10.select_dtypes(include=[float, int]).columns
    head = r40.iloc[:10].reset_index(drop=True)
    for c in num:
        assert float((r10[c] - head[c]).abs().max()) < 1e-9, c


def test_agi_preset_payload_matches_its_bundle_row(pools):
    from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                               sanitize_korea_config)
    p = build_korea_scenario_payload(sanitize_korea_config({"preset": "korea-agi-5y"}),
                                     **pools)
    assert p["final"]["nhi_years_forward"] == pytest.approx(2.14, abs=0.02)
    assert p["final"]["ei_shortfall_tn"] == pytest.approx(59.2, abs=0.5)
    assert p["final"]["nps_given_back"] == pytest.approx(6.59, abs=0.05)
    assert p["config"]["display_periods"] == 10


def test_committed_scenario_bundles_match_fresh_generation(pools):
    """Anti-drift: every committed korea/scenarios/<preset>.json must equal what the
    payload function generates today — regenerate with scripts/gen_korea_scenarios.py."""
    import json
    from pathlib import Path

    from fiscal_model.korea_scenarios import KOREA_PRESETS
    from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                               sanitize_korea_config)
    root = Path(__file__).resolve().parent.parent
    for key in KOREA_PRESETS:
        path = root / "web" / "public" / "data" / "korea" / "scenarios" / f"{key}.json"
        assert path.exists(), f"missing bundle for {key} — scripts/gen_korea_scenarios.py"
        committed = json.loads(path.read_text(encoding="utf-8"))
        fresh = json.loads(json.dumps(
            build_korea_scenario_payload(sanitize_korea_config({"preset": key}), **pools)))
        assert fresh == committed, f"stale bundle for {key} — scripts/gen_korea_scenarios.py"
