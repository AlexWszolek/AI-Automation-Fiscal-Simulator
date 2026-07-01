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
