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
    with pytest.raises(ValueError):
        DynamicModelV2(data, deltas, replace(R, **SCEN, income_tax_mult=-0.1))
    with pytest.raises(ValueError):
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
    # the DELTA side alone loses more per displaced worker, but the baseline surcharge dominates:
    # net, a higher-income-tax regime IMPROVES the balance (total = mult·(baseline − losses))
    assert r["im"]["fed_deficit_B"].iloc[-1] < r["base"]["fed_deficit_B"].iloc[-1]
    extra_losses = (im0["inc_fed_loss_B"] - base0["inc_fed_loss_B"]).iloc[-1]
    assert 0 < extra_losses < im0["income_surcharge_fed_B"].iloc[-1]   # both effects real; surcharge wins
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


def test_cons_mult_channels(runs):
    r, _ = runs
    base0, km0 = r["base0"], r["km0"]                  # km = 0.8: a consumption-tax CUT
    assert np.allclose(km0["cons_state_loss_B"], 0.8 * base0["cons_state_loss_B"], rtol=1e-12)
    # the displaced-channel federal columns are untouched; the FEDERAL effect is exactly the
    # excise surcharge (negative here — a cut loses baseline revenue)
    for col in ("inc_fed_loss_B", "corp_offset_B"):
        assert np.allclose(km0[col], base0[col], rtol=1e-12), col
    assert np.allclose(km0["excise_surcharge_fed_B"], -0.2 * 101.6, rtol=1e-9)
    assert np.allclose(km0["fed_deficit_B"] - base0["fed_deficit_B"], 0.2 * 101.6, rtol=1e-6)
    # state side: the cut REDUCES the shock loss (smaller cons deltas) but FORFEITS baseline
    # revenue (negative surcharge) — the baseline dominates, so gaps grow with a cut
    assert np.allclose(km0["cons_surcharge_state_B"], -0.2 * 873.7, rtol=1e-9)
    assert r["km"]["state_gap_B"].sum() > r["base"]["state_gap_B"].sum()


def test_feedback_coupling_is_real(runs):
    # documents WHY proportionality needs dm=0: with feedback, the scaled state gap changes
    # induced layoffs, so inc losses diverge from the pure ratio at t>=1 (and only then)
    r, _ = runs
    ratio = (r["im"]["inc_fed_loss_B"] / r["base"]["inc_fed_loss_B"]).to_numpy()
    assert np.isclose(ratio[0], 1.2, rtol=1e-9)
    assert not np.allclose(ratio[1:], 1.2, rtol=1e-6)


def test_no_automation_tax_hike_reduces_debt(data, deltas):
    """THE user requirement: with no automation, raising a tax mult must REDUCE the deficit/debt
    (net fiscal impact positive) via the baseline surcharge — total = mult·(baseline − losses)."""
    none = dict(cognitive_feasibility=0.0, physical_feasibility=0.0,
                adoption_path=[0.0] * 10)
    base = DynamicModelV2(data, deltas, replace(R, **none)).run()
    hike = DynamicModelV2(data, deltas, replace(R, **none, income_tax_mult=1.1)).run()
    assert np.allclose(base["fed_deficit_B"], 0.0, atol=1e-6)          # nothing happens at baseline
    # a 10% income surcharge collects 10% of the $2,403.2B baseline line, every year
    assert np.allclose(hike["income_surcharge_fed_B"], 0.1 * 2403.2, rtol=1e-9)
    assert np.allclose(-hike["fed_deficit_B"], 0.1 * 2403.2, rtol=1e-6)  # net fiscal impact POSITIVE
    assert hike["fed_debt_B"].iloc[-1] < base["fed_debt_B"].iloc[-1] - 2000   # debt falls, a lot
    # state side: the surcharge shrinks (here: zeroes) state gaps
    assert np.allclose(hike["income_surcharge_state_B"], 0.1 * 536.2, rtol=1e-9)
    assert (hike["state_gap_B"] <= base["state_gap_B"] + 1e-9).all()


def test_surcharge_columns_and_reconciliation(runs, data, deltas):
    r, base = runs
    res = r["all"]                                     # im=1.3, cm=0.7, km=1.5
    assert np.allclose(res["income_surcharge_fed_B"], 0.3 * 2403.2, rtol=1e-9)
    assert np.allclose(res["corp_surcharge_fed_B"], -0.3 * 491.7, rtol=1e-9)   # a CUT loses revenue
    assert np.allclose(res["excise_surcharge_fed_B"], 0.5 * 101.6, rtol=1e-9)
    assert np.allclose(res["cons_surcharge_state_B"], 0.5 * 873.7, rtol=1e-9)
    # summary must reconcile with the new rows (it asserts internally)
    from fiscal_model import summary
    from fiscal_model.government import RevenueLedger
    for grouping in ("tax", "channel"):
        summary.build_fiscal_summary(res, RevenueLedger(data), grouping, "busd")


def test_extreme_scenario_no_employment_oscillation(data, deltas, rung):
    """Regression for the audit-verified limit cycle: with the active-pool allocation key,
    employment declines monotonically at near-total automation (no release-re-displace whipsaw)."""
    from fiscal_model import presets
    if rung == 0:
        pytest.skip("presets are calibrated to rung 1")
    res = DynamicModelV2(data, deltas, presets.to_params(presets.PRESETS["agi-20y"])).run()
    emp = res["employed_M"].to_numpy()
    d = np.diff(emp)
    d = d[np.abs(d) > 0.01]
    assert (d <= 0).all(), f"employment must decline monotonically; diffs {np.round(d, 2)}"


def test_state_table(data, deltas, rung):
    m = DynamicModelV2(data, deltas, replace(R, **LIVE, reabsorption_rung=rung))
    res = m.run()
    tbl = m.state_table
    assert len(tbl) == 51 and list(tbl.columns) == [
        "state", "net_B", "shortfall_B", "rate_hike_B", "spending_cut_B",
        "implied_rate_hike_pct", "taxable_base_B", "at_cap"]
    assert (tbl["taxable_base_B"] > 0).all()
    # the table's shortfall total is the final-year state_gap_B column (same close object)
    assert np.isclose(tbl["shortfall_B"].sum(), res["state_gap_B"].iloc[-1], rtol=1e-9)
    assert (tbl["shortfall_B"] >= 0).all()
    assert np.allclose(np.maximum(tbl["net_B"], 0.0), tbl["shortfall_B"], rtol=1e-9)
