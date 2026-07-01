"""Accuracy-overhaul gate — pins the six fixes that corrected the model's mechanics.

Fix 1 adoption = cumulative diffusion ceiling; Fix 2 UBI = a real federal outlay; Fix 3 strong
output-weighted productivity dividend; Fix 4 automation/robot tax; Fix 5 unified reabsorption (haircut =
wage cut, floored); Fix 6a mode-dependent state close; Fix 6b offshore-off default + natural attrition.
The C8 anchor + conservation battery live in test_v2_phase*; here we pin the NEW behaviors.
"""
from dataclasses import replace
import time

import numpy as np
import pandas as pd
import pytest

from fiscal_model import levers_v2, macro, reabsorption
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


# ----------------------------------------------------------------- Fix 1: adoption ceiling
def test_adoption_is_a_cumulative_ceiling(data, deltas):
    # CONSTANT adoption → one displacement to the ceiling at t=0, then flat (not compounding erosion).
    flat = DynamicModelV2(data, deltas, replace(R, cognitive_feasibility=1.0, physical_feasibility=0.0,
                                                adoption_path=[0.3] * 10)).run()
    assert np.allclose(flat["employed_M"].iloc[1:].to_numpy(), flat["employed_M"].iloc[1], atol=1e-6)
    # the automated stock reaches g_cell·adoption_final·emp0 (per-cell), so the aggregate loss matches
    m = DynamicModelV2(data, deltas, replace(R, cognitive_feasibility=1.0, physical_feasibility=0.0,
                                             adoption_path=[0.3] * 10))
    g, emp0 = m._v1.g_cell, m._v1.emp0
    expected_drop = (g * 0.3 * emp0).sum() / emp0.sum() * 100
    assert abs(m.run()["employment_drop_pct"].iloc[-1] - expected_drop) < 1e-6


def test_adoption_monotone_and_bounded(data, deltas):
    r = DynamicModelV2(data, deltas, replace(R, **SCEN)).run()
    assert r["employed_M"].is_monotonic_decreasing                      # cumulative → never recovers
    assert (r["employment_drop_pct"] <= 100.0 + 1e-9).all()


# ----------------------------------------------------------------- Fix 2: UBI outlay
def test_ubi_is_a_federal_outlay(data, deltas):
    base = DynamicModelV2(data, deltas, replace(R, **SCEN)).run()
    ubi = DynamicModelV2(data, deltas, replace(R, **SCEN, ubi_annual=12_000)).run()
    workforce = deltas["employed"].sum()
    assert np.allclose(ubi["ubi_outlay_B"].to_numpy(), 12_000 * workforce / 1e9)
    assert np.allclose((ubi["fed_deficit_B"] - base["fed_deficit_B"]).to_numpy(),
                       12_000 * workforce / 1e9)                        # deficit rises by exactly the outlay


# ----------------------------------------------------------------- Fix 3: productivity dividend
def test_productivity_output_weighted(data, deltas):
    pt = 0.3
    r = DynamicModelV2(data, deltas, replace(R, **SCEN, **DISP, productivity_passthrough=pt)).run()
    assert np.allclose(r["productivity_index"].to_numpy(),
                       1.0 + pt * (r["saved_bill_B"] * 1e9 / macro.COMP_TOTAL_USD).to_numpy())
    assert (r["productivity_index"].iloc[-1] > 1.10)                    # a MATERIAL dividend (was ~1.007)


# ----------------------------------------------------------------- Fix 4: automation tax
def test_automation_tax_recovers_revenue(data, deltas):
    r = DynamicModelV2(data, deltas, replace(R, **SCEN, **DISP, automation_tax_rate=0.1)).run()
    assert np.allclose(r["automation_tax_B"].to_numpy(), 0.1 * r["saved_bill_B"].to_numpy())
    base = DynamicModelV2(data, deltas, replace(R, **SCEN, **DISP)).run()
    assert (r["fed_deficit_B"] < base["fed_deficit_B"]).all()           # the robot tax lowers the deficit


# ----------------------------------------------------------------- Fix 5: unified reabsorption
@pytest.fixture(scope="module")
def rung1_ready():
    if not reabsorption.engine_artifacts_exist():
        pytest.skip("benefit-lookup / NOC artifacts absent")
    return True


def test_haircut_zero_is_whole_reabsorption(data, deltas, rung1_ready):
    # the user's key intuition: reabsorption + haircut=0 shouldn't grow the deficit (reabsorbed are whole)
    common = dict(**SCEN, reabsorption_rung=1, reabsorption_rate=0.5)
    h0 = DynamicModelV2(data, deltas, replace(R, **common, reemployment_haircut=0.0)).run()
    h5 = DynamicModelV2(data, deltas, replace(R, **common, reemployment_haircut=0.5)).run()
    h9 = DynamicModelV2(data, deltas, replace(R, **common, reemployment_haircut=0.9)).run()
    # a deeper haircut monotonically worsens the deficit; haircut=0 is the mildest
    assert h0["fed_debt_B"].iloc[-1] < h5["fed_debt_B"].iloc[-1] < h9["fed_debt_B"].iloc[-1]
    # at haircut=0 the reabsorbed carry ~no loss → debt is far below the deep-cut case
    assert h0["fed_debt_B"].iloc[-1] < 0.5 * h9["fed_debt_B"].iloc[-1]
    # a deep haircut fires the means-tested channel (more transfers than the whole case)
    assert h9["transfers_added_B"].iloc[-1] > h0["transfers_added_B"].iloc[-1] + 1.0


def test_reabsorption_engine_is_fast(data, deltas, rung1_ready):
    v2p = replace(R, **SCEN, **DISP, reabsorption_rung=1, reabsorption_rate=0.4, reemployment_haircut=0.4,
                  demand_multiplier=0.5, n_periods=10)
    t0 = time.perf_counter()
    DynamicModelV2(data, deltas, v2p).run()                            # construction (live engine) + run
    assert (time.perf_counter() - t0) / 10 < 1.0                       # < 1s/period amortized (the budget)


# ----------------------------------------------------------------- Fix 6a: mode-dependent close
def test_rate_cap_moves_deficit_only_when_demand_on(data, deltas):
    on = dict(**SCEN, **DISP, demand_multiplier=0.5, state_response="raise_rates")
    hi = DynamicModelV2(data, deltas, replace(R, **on, state_rate_hike_cap=2.0)).run()
    lo = DynamicModelV2(data, deltas, replace(R, **on, state_rate_hike_cap=0.05)).run()
    assert lo["fed_debt_B"].iloc[-1] != hi["fed_debt_B"].iloc[-1]       # the cap now bites (was invariant)
    off = dict(**SCEN, **DISP, demand_multiplier=0.0, state_response="raise_rates")
    hi0 = DynamicModelV2(data, deltas, replace(R, **off, state_rate_hike_cap=2.0)).run()
    lo0 = DynamicModelV2(data, deltas, replace(R, **off, state_rate_hike_cap=0.05)).run()
    assert np.allclose(hi0["fed_deficit_B"].to_numpy(), lo0["fed_deficit_B"].to_numpy())   # C8-safe at 0


# ----------------------------------------------------------------- Fix 6b: attrition + offshore
def test_attrition_conserves_population_and_is_delta_neutral(data, deltas):
    # coherence semantics: attrition retires the long-term unemployed into the DELTA-NEUTRAL `retired`
    # bucket (the baseline twin retired too) — population conserved, the standing loss cancels, and the
    # deficit strictly FALLS (the perpetual-work counterfactual is gone).
    base = DynamicModelV2(data, deltas, replace(R, **SCEN)).run()
    att = DynamicModelV2(data, deltas, replace(R, **SCEN, attrition_rate=0.1)).run()
    baseline_M = deltas["employed"].sum() / 1e6
    assert np.allclose(att["population_M"].to_numpy(), baseline_M, atol=1e-6)   # C1 holds (retired counted)
    assert att["retired_M"].iloc[-1] > 0                                        # drains the long-term unemployed
    assert att["fed_deficit_B"].iloc[-1] < base["fed_deficit_B"].iloc[-1]       # and the loss decays with them
    # the firm side is untouched by retirement (the job stays automated)
    assert np.allclose(att["saved_bill_B"].to_numpy(), base["saved_bill_B"].to_numpy(), rtol=1e-12)


def test_offshore_off_by_default(data, deltas):
    r = DynamicModelV2(data, deltas, replace(levers_v2.DEFAULTS_SHIPPED, **SCEN))
    assert r.v2p.offshore_share == 0.0                                 # shipped default: full inflow taxable
    res = r.run()
    assert np.allclose(res["offshore_leak_B"].to_numpy(), 0.0)


# ----------------------------------------------------------------- guard: new levers gate C8
def test_new_levers_in_reduction_guard():
    assert not levers_v2.is_v1_reduction(replace(R, automation_tax_rate=0.1))
    assert not levers_v2.is_v1_reduction(replace(R, attrition_rate=0.05))
