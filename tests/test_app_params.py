"""The UI↔params bridge gate — the repr-exact round-trip that precomputed-artifact matching rides
on, the URL codec's clamp/snap guarantees, and cross-pins against the preset widget grid."""
import math
from dataclasses import replace

import pytest

from fiscal_model import app_params as ap
from fiscal_model import presets

ALL = list(presets.PRESETS.values())


# --------------------------------------------------------------- the round-trip (repr-exact)
@pytest.mark.parametrize("preset", ALL, ids=[p.key for p in ALL])
def test_roundtrip_repr_exact(preset):
    """build_v2_params(untouched widgets) must equal to_params(preset) BOTH as a dataclass and as
    repr — repr equality is the precomputed-tornado cache key."""
    ui = ap.ui_from_defaults(ap.preset_widget_defaults(preset), rung=1, preset=preset)
    built = ap.build_v2_params(ui)
    target = presets.to_params(preset)
    assert built == target, preset.key
    assert repr(built) == repr(target), f"{preset.key}: repr drift breaks artifact matching"
    assert ap.cfg_key(built) == ap.cfg_key(target)


def test_custom_defaults_construct():
    ui = ap.ui_from_defaults(dict(ap.CUSTOM_DEFAULTS), rung=1)
    v2p = ap.build_v2_params(ui)
    assert v2p.n_periods == 10 and v2p.ubi_annual == 0.0
    assert isinstance(v2p.ubi_annual, float)                     # the int-slider cast


def test_cfg_key_ignores_denominator():
    ui = ap.ui_from_defaults(dict(ap.CUSTOM_DEFAULTS), rung=1)
    a = ap.build_v2_params(ui)
    b = replace(a, denominator="pct_gdp")
    assert repr(a) != repr(b) and ap.cfg_key(a) == ap.cfg_key(b)


# --------------------------------------------------------------- UI_GRID cross-pins
def test_ui_grid_agrees_with_preset_grid():
    """The URL codec's grid must match the widget grid test_presets pins on V2Params fields."""
    from tests.test_presets import _GRID
    mapping = {  # V2Params field -> ui key
        "cognitive_feasibility": "cog", "physical_feasibility": "phys",
        "robotics_lag": "robotics_lag", "reabsorption_rate": "reab",
        "reemployment_haircut": "haircut", "lfp_exit_rate": "lfp", "attrition_rate": "attrition",
        "retained_profit_share": "retained", "price_reduction_share": "price",
        "auto_cost": "auto_cost", "compute_effective_rate": "compute_rate",
        "survivor_elasticity": "elasticity", "productivity_passthrough": "prod_pt",
        "price_passthrough": "price_pt", "demand_multiplier": "demand",
        "baseline_growth_rate": "growth", "interest_rate": "interest",
        "state_cut_share": "state_cut", "state_rate_hike_cap": "rate_cap",
        "ubi_recapture_rate": "ubi_recapture",
    }
    for field, (lo, hi, step) in _GRID.items():
        ui_key = mapping[field]
        glo, ghi, gstep, _typ = ap.UI_GRID[ui_key]
        assert (glo, ghi, gstep) == (lo, hi, step), f"{field}/{ui_key}"


# --------------------------------------------------------------- URL codec
def test_url_roundtrip_identity_on_grid():
    preset = presets.PRESETS["agi-5y"]
    pristine = ap.preset_widget_defaults(preset)
    current = dict(pristine, cog=0.9, demand=1.0, ubi=12_000, unbounded=True)
    qp = ap.encode_query_config("agi-5y", ["ubi"], current, pristine)
    assert qp["preset"] == "agi-5y" and qp["ov"] == "ubi"
    assert set(qp) == {"preset", "ov", "cog", "demand", "ubi", "unbounded"}   # only the diffs
    parsed = ap.parse_query_config(qp)
    assert parsed["preset"] == "agi-5y" and parsed["overlays"] == ["ubi"]
    assert parsed["levers"] == {"cog": 0.9, "demand": 1.0, "ubi": 12_000, "unbounded": True}


def test_url_snap_and_clamp():
    parsed = ap.parse_query_config({"cog": "0.837", "demand": "99", "ubi": "-5",
                                    "rate_cap": "0.1499", "state_resp": "raise_rates"})
    lv = parsed["levers"]
    assert math.isclose(lv["cog"], 0.85)                          # snapped to the 0.05 grid
    assert lv["demand"] == 2.0 and lv["ubi"] == 0                 # clamped to widget range
    assert math.isclose(lv["rate_cap"], 0.1)                      # snapped down within [0.1, 3]
    assert lv["state_resp"] == "raise_rates"


def test_url_garbage_is_dropped():
    parsed = ap.parse_query_config({"preset": "nope", "ov": "ubi,bogus,cw-robot-tax,grt-robot-tax",
                                    "cog": "banana", "state_resp": "coup", "unknown_key": "1"})
    assert parsed["preset"] is None
    assert parsed["overlays"] == ["ubi", "cw-robot-tax"]          # bogus dropped, GRT loses the tie
    assert parsed["levers"] == {}


def test_encode_ignores_slider_echo():
    """JS doubles echo back min+k*step with float error — must not create spurious URL params."""
    preset = presets.PRESETS["windfall-medium"]
    pristine = ap.preset_widget_defaults(preset)
    echoed = dict(pristine, cog=pristine["cog"] + 1e-12)
    assert ap.encode_query_config("windfall-medium", [], echoed, pristine) == {"preset": "windfall-medium"}
