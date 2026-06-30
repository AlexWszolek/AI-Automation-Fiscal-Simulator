"""Phase 0 gate — the anchor harness. C8 (v2 reproduces v1), C1 (population conservation,
5-state collapsed), and the t=0 base-rate gate (J.2)."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fiscal_model import levers_v2
from fiscal_model.dynamics import DynamicModel, DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.levers_v2 import DEFAULTS_V1REDUCTION

SCENARIO = dict(cognitive_feasibility=0.85, physical_feasibility=0.25,
                adoption_path=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9])
_C8_COLS = ["fed_deficit_B", "fed_debt_B", "state_gap_B", "employment_drop_pct",
            "revenue_lost_B", "transfers_added_B", "corp_offset_B", "ubi_required_rate"]


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built — run `python -m fiscal_model.dynamics`")
    return pd.read_parquet(DELTA_CACHE)


def test_two_default_sets_differ(data):
    # E: the reduction set and the shipped set must be distinct objects
    assert levers_v2.is_v1_reduction(replace(DEFAULTS_V1REDUCTION, **SCENARIO))
    assert not levers_v2.is_v1_reduction(levers_v2.DEFAULTS_SHIPPED)
    diffs = {f for f in ("reabsorption_rung", "auto_cost", "offshore_share", "price_passthrough")
             if getattr(DEFAULTS_V1REDUCTION, f) != getattr(levers_v2.DEFAULTS_SHIPPED, f)}
    assert {"reabsorption_rung", "auto_cost"} <= diffs


@pytest.mark.parametrize("reab", [0.0, 0.4, 0.8])
def test_c8_v2_reproduces_v1(data, deltas, c8_compare, reab):
    v2p = replace(DEFAULTS_V1REDUCTION, reabsorption_rate=reab, ubi_annual=12_000, **SCENARIO)
    c8_compare(data, deltas, v2p, _C8_COLS)   # asserts is_v1_reduction then v2 == v1


def test_c1_population_conservation(data, deltas):
    res = DynamicModelV2(data, deltas,
                         replace(DEFAULTS_V1REDUCTION, reabsorption_rate=0.4, **SCENARIO)).run()
    baseline_M = deltas["employed"].sum() / 1e6
    assert np.allclose(res["population_M"].to_numpy(), baseline_M, atol=1e-6)
    assert (res["exited_M"] == 0).all()   # no LFP exit at v1-reduction


def test_t0_baseline_rate_gate(data, deltas):
    r = DynamicModelV2(data, deltas, DEFAULTS_V1REDUCTION).baseline_rates()
    assert abs(r["income"] - 0.195) < 0.01
    assert abs(r["payroll"] - 0.128) < 0.01
    assert abs(r["corporate"] - 0.178) < 0.01
