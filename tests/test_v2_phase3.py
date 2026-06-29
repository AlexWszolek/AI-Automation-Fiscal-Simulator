"""Phase 3 gate — macro state + price/transfer correctness. C4: a price-passthrough change moves
REAL / %-GDP aggregates but leaves every NOMINAL column unchanged (the A2 double-application trap);
productivity cushions %-GDP; macro inert at reduction."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.levers_v2 import DEFAULTS_V1REDUCTION

SCEN = dict(cognitive_feasibility=0.85, physical_feasibility=0.25,
            adoption_path=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9])
DISPP = dict(retained_profit_share=0.8, price_reduction_share=0.2, survivor_gains_share=0.0)
NOMINAL = ["fed_deficit_B", "fed_debt_B", "corp_offset_B", "transfers_added_B", "compute_pool_tax_B",
           "automation_spend_B", "price_reduction_B", "state_gap_B", "employment_drop_pct"]


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built — run `python -m fiscal_model.dynamics`")
    return pd.read_parquet(DELTA_CACHE)


def test_c4_price_is_deflation_only(data, deltas):
    base = replace(DEFAULTS_V1REDUCTION, **SCEN, **DISPP, price_passthrough=0.0)
    defl = replace(DEFAULTS_V1REDUCTION, **SCEN, **DISPP, price_passthrough=0.6)
    r0 = DynamicModelV2(data, deltas, base).run()
    r1 = DynamicModelV2(data, deltas, defl).run()
    # A2: every NOMINAL column is invariant to price_passthrough (ΔP never touches nominal fiscal)
    for c in NOMINAL:
        assert np.allclose(r0[c].to_numpy(), r1[c].to_numpy(), atol=1e-9), f"nominal {c} moved with ΔP"
    # P falls with deflation; real = nominal / P; deficit/GDP rises (smaller nominal GDP)
    assert (r0["price_level"] == 1.0).all()
    assert (r1["price_level"] < 1.0).any()
    assert np.allclose(r1["fed_deficit_real_B"].to_numpy(),
                       (r1["fed_deficit_B"] / r1["price_level"]).to_numpy())
    assert r1["fed_deficit_pct_gdp"].iloc[-1] > r0["fed_deficit_pct_gdp"].iloc[-1]


def test_macro_inert_at_reduction(data, deltas):
    r = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN)).run()
    assert (r["price_level"] == 1.0).all() and (r["productivity_index"] == 1.0).all()
    assert np.allclose(r["fed_deficit_real_B"].to_numpy(), r["fed_deficit_B"].to_numpy())


def test_productivity_cushions_pct_gdp(data, deltas):
    r0 = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN,
                                              productivity_passthrough=0.0)).run()
    r1 = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN,
                                              productivity_passthrough=0.3)).run()
    assert (r1["productivity_index"] > 1.0).any()
    assert np.allclose(r0["fed_deficit_B"].to_numpy(), r1["fed_deficit_B"].to_numpy(), atol=1e-9)
    assert r1["fed_deficit_pct_gdp"].iloc[-1] < r0["fed_deficit_pct_gdp"].iloc[-1]
