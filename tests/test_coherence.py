"""Coherence-overhaul gate — pins the economic-logic fixes from the model review.

C1 (commit 1): the firm side rides the CUMULATIVE automated stock — reabsorption/attrition can no longer
retroactively un-automate jobs (the $4,233B→$650B saved_bill collapse that flipped the federal balance).
Later commits append their pins here (funded W*, retired state, level-targeting demand, robotics lag).
"""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.levers_v2 import DEFAULTS_V1REDUCTION as R

SCEN = dict(cognitive_feasibility=0.85, physical_feasibility=0.25, adoption_path=list(np.linspace(0.1, 0.9, 10)))
DISP = dict(retained_profit_share=0.6, price_reduction_share=0.2, survivor_gains_share=0.2)


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built")
    return pd.read_parquet(DELTA_CACHE)


# ----------------------------------------------------- fix: firm side keyed to cumulative auto_disp
def test_firm_side_invariant_to_reabsorption(data, deltas):
    # a job stays automated after its worker finds other work: the whole firm side (saved bill, corp
    # offset, robot-tax base, survivor gains, productivity) must be IDENTICAL across reabsorption rates.
    r0 = DynamicModelV2(data, deltas, replace(R, **SCEN, **DISP)).run()
    r3 = DynamicModelV2(data, deltas, replace(R, **SCEN, **DISP, reabsorption_rate=0.3)).run()
    for c in ("saved_bill_B", "corp_offset_B", "survivor_gains_B", "retained_profit_B",
              "automation_spend_B", "productivity_index"):
        assert np.allclose(r0[c].to_numpy(), r3[c].to_numpy(), rtol=1e-12), c


def test_firm_side_invariant_to_attrition_and_exit(data, deltas):
    r0 = DynamicModelV2(data, deltas, replace(R, **SCEN, **DISP)).run()
    ra = DynamicModelV2(data, deltas, replace(R, **SCEN, **DISP, attrition_rate=0.1,
                                              lfp_exit_rate=0.1)).run()
    for c in ("saved_bill_B", "corp_offset_B", "survivor_gains_B"):
        assert np.allclose(r0[c].to_numpy(), ra[c].to_numpy(), rtol=1e-12), c


def test_reabsorption_no_longer_flips_federal_balance(data, deltas):
    # the review's probe: reabsorption 0→0.3 used to collapse saved_bill and FLIP the yr-10 federal
    # balance (re-employment worsening the deficit). Now re-employment strictly HELPS the ledger.
    common = dict(**SCEN, **DISP, reabsorption_rung=1, reemployment_haircut=0.3)
    r0 = DynamicModelV2(data, deltas, replace(R, **common)).run()
    r3 = DynamicModelV2(data, deltas, replace(R, **common, reabsorption_rate=0.3)).run()
    assert r3["fed_deficit_B"].iloc[-1] < r0["fed_deficit_B"].iloc[-1]
    assert r3["fed_debt_B"].iloc[-1] < r0["fed_debt_B"].iloc[-1]


# ----------------------------------------------------- fix: the robot tax has a PAYER
def test_robot_tax_is_paid_from_retained_profit(data, deltas):
    # the tax is corp-deductible: the corporate offset shrinks by corp_rate·tax, so net federal recovery
    # is tax·(1−corp_rate) — revenue no longer appears ex nihilo (firms used to disburse 107% of the bill).
    base = DynamicModelV2(data, deltas, replace(R, **SCEN, **DISP)).run()
    taxed = DynamicModelV2(data, deltas, replace(R, **SCEN, **DISP, automation_tax_rate=0.1)).run()
    assert (taxed["corp_offset_B"] < base["corp_offset_B"] - 1e-9).all()      # the payer's books shrink
    assert (taxed["fed_deficit_B"] < base["fed_deficit_B"]).all()             # net recovery still positive
    # deficit falls by LESS than the tax (the deduction claws part back)
    recovery = base["fed_deficit_B"].iloc[-1] - taxed["fed_deficit_B"].iloc[-1]
    assert recovery < taxed["automation_tax_B"].iloc[-1]


def test_robot_tax_capacity_bound_raises(data, deltas):
    # a rate above retained_profit_share·(1−auto_cost) has no profit to pay it — fail loud
    with pytest.raises(AssertionError):
        DynamicModelV2(data, deltas, replace(R, retained_profit_share=0.1, price_reduction_share=0.4,
                                             survivor_gains_share=0.5, automation_tax_rate=0.2))


# ----------------------------------------------------- fix: funded W* (the snap branch, unit-level)
def test_funded_w_update_identity_all_branches():
    # C5c must hold exactly in EVERY branch of the pure update: ℓ·wb·(W_new−1) + overflow == gains
    from fiscal_model.survivor import funded_w_update
    cases = [
        dict(gains=100.0, W=1.0, wb=1000.0, l=1.4, ceil=1.5),     # funded, under the ceiling
        dict(gains=900.0, W=1.2, wb=1000.0, l=1.4, ceil=1.3),     # funded, cap binds → overflow
        dict(gains=50.0, W=1.4, wb=1000.0, l=1.4, ceil=1.5),      # UNFUNDABLE → snap down
        dict(gains=100.0, W=1.1, wb=1000.0, l=1.4, ceil=float("inf")),  # unbounded
        dict(gains=100.0, W=1.2, wb=0.0, l=1.4, ceil=1.5),        # no survivors → all overflow
    ]
    for c in cases:
        W_new, cost, inc, ov = funded_w_update(c["gains"], c["W"], c["wb"], c["l"], c["ceil"])
        assert abs(cost + ov - c["gains"]) < 1e-9, c              # the conserved identity
        assert cost >= -1e-12 and ov >= -1e-12 and W_new >= 1.0 - 1e-12
        if np.isfinite(c["ceil"]):
            assert W_new <= c["ceil"] + 1e-12
    # the snap case specifically: W falls to the fundable level
    W_new, cost, inc, ov = funded_w_update(50.0, 1.4, 1000.0, 1.4, 1.5)
    assert W_new < 1.4 and abs(W_new - (1 + 50.0 / 1400.0)) < 1e-12 and inc == 0.0 and ov == 0.0


# ----------------------------------------------------- fix: worker machine & baseline frame
def test_ssdi_outlay_on_exited(data, deltas):
    res = DynamicModelV2(data, deltas, replace(R, **SCEN, lfp_exit_rate=0.1)).run()
    assert (res["ssdi_outlay_B"].iloc[1:] > 0).all()            # exited draw SSDI once they exist
    expected = res["exited_M"] * 1e6 * 18_000 / 1e9
    assert np.allclose(res["ssdi_outlay_B"].to_numpy(), expected.to_numpy())


def test_induced_can_be_reabsorbed(data, deltas):
    # demand-displaced workers join the same reabsorption channel as automation-displaced (they used to
    # be locked in an absorbing trap while an automation-displaced coder could wait tables)
    v2p = replace(R, **SCEN, demand_multiplier=0.8, reabsorption_rate=0.5)
    res = DynamicModelV2(data, deltas, v2p).run()
    no_reab = DynamicModelV2(data, deltas, replace(R, **SCEN, demand_multiplier=0.8)).run()
    assert res["induced_M"].iloc[-1] < no_reab["induced_M"].iloc[-1]   # the pool drains into service jobs
    baseline_M = deltas["employed"].sum() / 1e6
    assert np.allclose(res["population_M"].to_numpy(), baseline_M, atol=1e-6)


def test_growth_moves_only_pct_gdp_columns(data, deltas):
    g0 = DynamicModelV2(data, deltas, replace(R, **SCEN, **DISP)).run()
    g4 = DynamicModelV2(data, deltas, replace(R, **SCEN, **DISP, baseline_growth_rate=0.04)).run()
    for c in ("fed_deficit_B", "fed_debt_B", "state_gap_B", "saved_bill_B"):   # nominal $ unchanged
        assert np.allclose(g0[c].to_numpy(), g4[c].to_numpy(), rtol=0, atol=1e-9), c
    # the %-GDP columns shrink as the denominator grows (r>g inversion fixed)
    assert g4["fed_debt_pct_gdp"].iloc[-1] < g0["fed_debt_pct_gdp"].iloc[-1]
    assert g4["fed_deficit_pct_gdp"].iloc[-1] < g0["fed_deficit_pct_gdp"].iloc[-1]


def test_slack_excludes_reabsorbed_and_retired(data, deltas):
    # reabsorbed are EMPLOYED — they must not suppress survivor wages as phantom slack
    v2p = replace(R, **SCEN, reabsorption_rate=0.5, survivor_elasticity=-0.2, survivor_raise_ceiling=1.5)
    with_reab = DynamicModelV2(data, deltas, v2p).run()
    no_reab = DynamicModelV2(data, deltas, replace(v2p, reabsorption_rate=0.0)).run()
    # more reabsorption → less slack → a smaller market wage cut (less negative market_frac)
    assert with_reab["survivor_market_frac"].iloc[-1] > no_reab["survivor_market_frac"].iloc[-1]


# ----------------------------------------------------- fix: UBI recapture (recipient-side economics)
def test_ubi_recapture_lowers_net_cost(data, deltas):
    gross = DynamicModelV2(data, deltas, replace(R, **SCEN, ubi_annual=12_000)).run()
    net = DynamicModelV2(data, deltas, replace(R, **SCEN, ubi_annual=12_000,
                                               ubi_recapture_rate=0.25)).run()
    assert np.allclose(net["ubi_recapture_B"].to_numpy(), 0.25 * net["ubi_outlay_B"].to_numpy())
    assert np.allclose((gross["fed_deficit_B"] - net["fed_deficit_B"]).to_numpy(),
                       net["ubi_recapture_B"].to_numpy())      # deficit falls by exactly the recapture
    # the financing metric reports the NET burden
    assert (net["ubi_required_rate"] < gross["ubi_required_rate"]).all()
