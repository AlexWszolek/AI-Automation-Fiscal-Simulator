"""Tax-regime multiplier gate — static-scoring levers that rescale the shock's fiscal flows.

income_tax_mult / corp_tax_mult / cons_tax_mult: 1.0 = current law = the C8 off value. The battery
pins (a) the conservation identities under mult ≠ 1, (b) the directional economics, (c) exact
proportionality of the channels each lever claims, and (d) that the levers never touch what they
must not (payroll, the demand basis, the compute/robot taxes)."""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from fiscal_model import levers_v2, reabsorption
from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.invariants import assert_all_invariants
from fiscal_model.levers_v2 import DEFAULTS_V1REDUCTION as R

SCEN = dict(cognitive_feasibility=0.7, physical_feasibility=0.2,
            adoption_path=list(np.linspace(0.1, 0.6, 10)))
LIVE = dict(**SCEN, retained_profit_share=0.6, price_reduction_share=0.2, survivor_gains_share=0.2,
            survivor_raise_ceiling=1.5, survivor_elasticity=-0.15, demand_multiplier=0.5,
            auto_cost=0.10, reabsorption_rate=0.3, lfp_exit_rate=0.03, attrition_rate=0.025,
            price_passthrough=0.3, productivity_passthrough=0.3, baseline_growth_rate=0.04,
            robotics_lag=4.0, ubi_annual=12_000, ubi_recapture_rate=0.25)


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built")
    return pd.read_parquet(DELTA_CACHE)


@pytest.fixture(scope="module")
def rung(deltas):
    return 1 if reabsorption.engine_artifacts_exist() else 0


@pytest.fixture(scope="module")
def runs(data, deltas, rung):
    """LIVE runs (demand feedback ON) for direction/invariants; dm=0 twins for the EXACT
    proportionality pins — with feedback, scaled state gaps change induced layoffs from t≥1, so
    channel columns are proportional only at t=0 (correct economics, wrong test target)."""
    base = replace(R, **LIVE, reabsorption_rung=rung)
    base0 = replace(base, demand_multiplier=0.0)
    out = {"base": DynamicModelV2(data, deltas, base).run(),
           "base0": DynamicModelV2(data, deltas, base0).run()}
    for key, ov in (("im", dict(income_tax_mult=1.2)), ("cm", dict(corp_tax_mult=1.2)),
                    ("km", dict(cons_tax_mult=0.8)),
                    ("all", dict(income_tax_mult=1.3, corp_tax_mult=0.7, cons_tax_mult=1.5))):
        out[key] = DynamicModelV2(data, deltas, replace(base, **ov)).run()
        out[key + "0"] = DynamicModelV2(data, deltas, replace(base0, **ov)).run()
    return out, base


def test_guard_listing():
    assert levers_v2.is_v1_reduction(R)
    for f in ("income_tax_mult", "corp_tax_mult", "cons_tax_mult"):
        assert not levers_v2.is_v1_reduction(replace(R, **{f: 1.1})), f


def test_domain_guard(data, deltas):
    with pytest.raises(AssertionError):
        DynamicModelV2(data, deltas, replace(R, **SCEN, income_tax_mult=-0.1))
    with pytest.raises(AssertionError):
        DynamicModelV2(data, deltas, replace(R, **SCEN, corp_tax_mult=float("inf")))


def test_invariants_green_under_mults(runs, deltas):
    out, base = runs
    v2p = replace(base, income_tax_mult=1.3, corp_tax_mult=0.7, cons_tax_mult=1.5)
    assert_all_invariants(out["all"], v2p, deltas["employed"].sum() / 1e6)


def test_income_mult_exact_proportionality_and_direction(runs):
    r, _ = runs
    base0, im0 = r["base0"], r["im0"]                 # dm=0: pure static scoring, exact ratios
    for col in ("inc_fed_loss_B", "inc_state_loss_B", "ui_tax_fed_B"):
        assert np.allclose(im0[col], 1.2 * base0[col], rtol=1e-12), col
    # payroll, compute, robot tax untouched
    for col in ("payroll_fed_loss_B", "compute_pool_tax_B", "automation_tax_B", "ubi_recapture_B"):
        assert np.allclose(im0[col], base0[col], rtol=1e-12), col
    # with feedback ON: a higher-income-tax regime loses MORE from displacement
    assert r["im"]["fed_deficit_B"].iloc[-1] > r["base"]["fed_deficit_B"].iloc[-1]
    # revenue_lost_pct stays rate-consistent (numerator and denominator both scaled)
    assert np.allclose(im0["revenue_lost_pct"], base0["revenue_lost_pct"], rtol=5e-2)


def test_corp_mult_exact_proportionality_and_direction(runs):
    r, _ = runs
    base0, cm0 = r["base0"], r["cm0"]
    for col in ("corp_offset_B", "survivor_overflow_corp_tax_B"):
        assert np.allclose(cm0[col], 1.2 * base0[col], rtol=1e-12), col
    # the router partition legs are untouched (C2/C5b semantics preserved)
    for col in ("retained_profit_B", "price_reduction_B", "survivor_gains_B", "saved_bill_B",
                "compute_pool_tax_B", "inc_fed_loss_B"):
        assert np.allclose(cm0[col], base0[col], rtol=1e-12), col
    assert r["cm"]["fed_deficit_B"].iloc[-1] < r["base"]["fed_deficit_B"].iloc[-1]  # more recapture


def test_cons_mult_state_side_only(runs):
    r, _ = runs
    base0, km0 = r["base0"], r["km0"]
    assert np.allclose(km0["cons_state_loss_B"], 0.8 * base0["cons_state_loss_B"], rtol=1e-12)
    # federal columns untouched at dm=0 (no state-close feedback path back to the federal side)
    for col in ("inc_fed_loss_B", "corp_offset_B", "fed_deficit_B"):
        assert np.allclose(km0[col], base0[col], rtol=1e-12), col
    # the state gap shrinks with a smaller consumption loss (feedback ON)
    assert r["km"]["state_gap_B"].sum() < r["base"]["state_gap_B"].sum()


def test_feedback_coupling_is_real(runs):
    # documents WHY proportionality needs dm=0: with feedback, the scaled state gap changes
    # induced layoffs, so inc losses diverge from the pure ratio at t>=1 (and only then)
    r, _ = runs
    ratio = (r["im"]["inc_fed_loss_B"] / r["base"]["inc_fed_loss_B"]).to_numpy()
    assert np.isclose(ratio[0], 1.2, rtol=1e-9)
    assert not np.allclose(ratio[1:], 1.2, rtol=1e-6)


def test_state_table(data, deltas, rung):
    m = DynamicModelV2(data, deltas, replace(R, **LIVE, reabsorption_rung=rung))
    res = m.run()
    tbl = m.state_table
    assert len(tbl) == 51 and list(tbl.columns) == [
        "state", "net_B", "shortfall_B", "rate_hike_B", "spending_cut_B",
        "implied_rate_hike_pct", "at_cap"]
    # the table's shortfall total is the final-year state_gap_B column (same close object)
    assert np.isclose(tbl["shortfall_B"].sum(), res["state_gap_B"].iloc[-1], rtol=1e-9)
    assert (tbl["shortfall_B"] >= 0).all()
    assert np.allclose(np.maximum(tbl["net_B"], 0.0), tbl["shortfall_B"], rtol=1e-9)
