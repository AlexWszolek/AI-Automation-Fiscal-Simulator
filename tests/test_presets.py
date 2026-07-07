"""Preset gate — every literature-anchored preset must be UI-representable, provenance-complete,
overlay-composable, and pass the full conservation battery.

Two halves: the PURE tests run on a fresh clone (no artifacts); the battery tests skip loudly when
the delta cache / reabsorption artifacts are absent (same guards as test_v2_phase4/6)."""
import math
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from fiscal_model import mc, presets, reabsorption
from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model.invariants import assert_all_invariants
from fiscal_model.levers_v2 import DEFAULTS_SHIPPED, is_v1_reduction

ALL = list(presets.PRESETS.values())


# ------------------------------------------------------------------------------- pure: validity
def test_to_params_valid():
    for p in ALL:
        v2p = presets.to_params(p)
        assert not is_v1_reduction(v2p), p.key
        s = v2p.retained_profit_share + v2p.price_reduction_share + v2p.survivor_gains_share
        assert abs(s - 1.0) < 1e-9, (p.key, s)                       # the simplex assert's tolerance
        # the derived remainder IS the app's expression (bit-for-bit round-trip guarantee)
        assert v2p.survivor_gains_share == max(
            0.0, 1.0 - v2p.retained_profit_share - v2p.price_reduction_share)
        assert len(v2p.adoption_path) == v2p.n_periods
        assert all(0.0 <= a <= 1.0 for a in v2p.adoption_path)
        assert v2p.automation_tax_rate == 0.0, "presets ship tax-free; taxation lives in OVERLAYS"
        # demand loop gain stays well under the model's fail-loud ρ<1 guard (ρ ≈ 0.22·dm)
        assert v2p.demand_multiplier <= 2.0
        assert 0.0 <= v2p.baseline_growth_rate <= 0.10


def test_shipped_robot_tax_moved_to_overlays():
    assert DEFAULTS_SHIPPED.automation_tax_rate == 0.0


# --------------------------------------------------------------------- pure: UI representability
# Sidebar widget grids (app/streamlit_app.py). A preset value off its widget grid would load as a
# different number than documented — this test makes future preset edits fail loudly instead.
_GRID = {
    "cognitive_feasibility": (0.0, 1.0, 0.05), "physical_feasibility": (0.0, 1.0, 0.05),
    "robotics_lag": (0, 15, 1),
    "reabsorption_rate": (0.0, 1.0, 0.025), "reemployment_haircut": (0.0, 1.0, 0.01),
    "lfp_exit_rate": (0.0, 0.2, 0.01), "attrition_rate": (0.0, 0.1, 0.005),
    "retained_profit_share": (0.0, 1.0, 0.05), "price_reduction_share": (0.0, 1.0, 0.05),
    "auto_cost": (0.0, 1.0, 0.05), "compute_effective_rate": (0.0, 0.4, 0.01),
    "survivor_elasticity": (-0.5, 0.5, 0.05), "productivity_passthrough": (0.0, 1.0, 0.05),
    "price_passthrough": (0.0, 1.0, 0.05), "demand_multiplier": (0.0, 2.0, 0.05),
    "baseline_growth_rate": (0.0, 0.08, 0.005), "interest_rate": (0.0, 0.10, 0.005),
    "state_cut_share": (0.0, 1.0, 0.05), "state_rate_hike_cap": (0.1, 3.0, 0.1),
    "ubi_recapture_rate": (0.0, 0.6, 0.05),
}


def _on_grid(v, lo, hi, step):
    if not (lo - 1e-9 <= v <= hi + 1e-9):
        return False
    k = (v - lo) / step
    return abs(k - round(k)) < 1e-6


def test_ui_grid_representability():
    for p in ALL:
        v2p = presets.to_params(p)
        for f, (lo, hi, step) in _GRID.items():
            v = getattr(v2p, f)
            assert _on_grid(v, lo, hi, step), f"{p.key}.{f}={v} is off the widget grid {lo}..{hi}/{step}"
        assert _on_grid(p.adoption_start, 0.0, 1.0, 0.01), p.key
        assert _on_grid(p.adoption_end, 0.0, 1.0, 0.01), p.key
        assert 3 <= p.n_periods <= 30
        # the price slider's max is 1 − retained
        assert p.overrides["price_reduction_share"] <= 1.0 - p.overrides["retained_profit_share"] + 1e-9
        # the robot-tax slider survives every preset (bound ≥ 0.01 so it never collapses to 0)
        assert v2p.retained_profit_share * (1.0 - v2p.auto_cost) >= 0.01, p.key


def test_provenance_completeness():
    for p in ALL:
        assert p.name and p.blurb
        missing = set(p.overrides) - set(p.provenance)
        assert not missing, f"{p.key}: overrides without provenance: {missing}"
        assert "adoption" in p.provenance, p.key


# ------------------------------------------------------------------------------- pure: the kink
def test_kinked_path_is_parametric():
    p = presets.PRESETS["agi-5y"]
    for n in (10, 20):
        path = presets.build_adoption_path(p, n)
        assert len(path) == n
        assert math.isclose(path[0], 0.20)
        assert math.isclose(path[5], 1.0), "full automation at year 5 (Korinek-Suh aggressive)"
        assert all(math.isclose(x, 1.0) for x in path[5:]), "flat after the transition"
    short = presets.build_adoption_path(p, 4)                    # horizon inside the transition
    assert len(short) == 4 and short[-1] < 1.0
    # to_params at a stretched horizon keeps the kink (the whole point of the parametric form)
    assert presets.to_params(p, n_periods=20).adoption_path[5] == 1.0


# ------------------------------------------------------------------------------- pure: overlays
def test_overlay_robot_tax_formula_and_bound():
    for p in ALL:
        base = presets.to_params(p)
        cw, _ = presets.apply_overlays(base, ["cw-robot-tax"])
        assert math.isclose(cw.automation_tax_rate,
                            min(0.027 * base.auto_cost,
                                base.retained_profit_share * (1.0 - base.auto_cost)))
        grt, notes = presets.apply_overlays(base, ["grt-robot-tax"])
        assert math.isclose(grt.automation_tax_rate,
                            min(0.051 * base.auto_cost,
                                base.retained_profit_share * (1.0 - base.auto_cost)))
        if base.n_periods > 10:
            assert "overstates" in notes[0], "GRT decade-1 approximation must be flagged beyond 10y"
    # adversarial corner: the bound clip engages (and never goes negative)
    tight = replace(DEFAULTS_SHIPPED, retained_profit_share=0.05, price_reduction_share=0.05,
                    survivor_gains_share=0.90, auto_cost=0.90)
    clipped, _ = presets.apply_overlays(tight, ["grt-robot-tax"])
    assert clipped.automation_tax_rate == pytest.approx(0.05 * 0.10)   # bound < 0.051·auto_cost
    assert clipped.automation_tax_rate <= tight.retained_profit_share * (1 - tight.auto_cost) + 1e-12


def test_overlay_ubi_parity_and_composition():
    base = presets.to_params(presets.PRESETS["windfall-medium"])
    both, notes = presets.apply_overlays(base, ["ubi", "compute-parity"])
    assert both.ubi_annual == 12_000.0 and both.ubi_recapture_rate == 0.30
    assert both.compute_effective_rate == 0.27
    assert len(notes) == 2
    with pytest.raises(ValueError):
        presets.apply_overlays(base, ["cw-robot-tax", "grt-robot-tax"])
    with pytest.raises(KeyError):
        presets.apply_overlays(base, ["not-a-real-overlay"])


# ------------------------------------------------------------------- pure: MC sampler at preset dm
def test_sampler_dm_domain_at_preset_base():
    # the (0,1) bound would have clipped every draw around dm=1.5 to exactly 1.0 (point mass)
    base = presets.to_params(presets.PRESETS["china-shock"])
    dms = np.array([d.demand_multiplier for d in mc.sample_draws(base, 200, 0.15, seed=1)])
    assert dms.max() <= 2.0 and dms.min() >= 0.0
    assert (dms > 1.0).mean() > 0.5, "draws around a 1.5 base must live above the old (0,1) bound"
    assert np.unique(dms).size > 150, "no point mass at a clip edge"


# ------------------------------------------------------------------------ battery (needs artifacts)
@pytest.fixture(scope="module")
def preset_runs(data):
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built — run scripts/bootstrap.sh (precompute)")
    if not reabsorption.engine_artifacts_exist():
        pytest.skip("benefit-lookup / NOC artifacts absent — presets are calibrated to rung 1")
    deltas = pd.read_parquet(DELTA_CACHE)
    runs = {}
    by_horizon: dict = {}
    for p in ALL:                                    # group same-horizon presets on one context —
        by_horizon.setdefault(p.n_periods, []).append(p)   # ctx.run is bit-identical to fresh build
    for group in by_horizon.values():
        ctx = mc.ScenarioContext(data, deltas, presets.to_params(group[0]))
        for p in group:
            runs[p.key] = (ctx.run(presets.to_params(p)), presets.to_params(p), ctx)
    return runs, deltas["employed"].sum() / 1e6


@pytest.mark.parametrize("key", list(presets.PRESETS))
def test_preset_full_battery(preset_runs, key):
    runs, baseline_M = preset_runs
    res, v2p, _ = runs[key]
    assert_all_invariants(res, v2p, baseline_M)
    assert (res["fed_deficit_B"] > 0).any(), f"{key}: a displacement scenario must move the deficit"


def test_overlays_run_clean_on_a_preset(preset_runs):
    runs, baseline_M = preset_runs
    _, base, ctx = runs["windfall-medium"]
    v2p, _ = presets.apply_overlays(base, ["cw-robot-tax", "ubi", "compute-parity"])
    res = ctx.run(v2p)                               # overlay fields are all PERTURBED → same context
    assert_all_invariants(res, v2p, baseline_M)
    assert (res["automation_tax_B"] > 0).any()
    assert (res["ubi_outlay_B"] > 0).any() and (res["ubi_recapture_B"] > 0).any()
