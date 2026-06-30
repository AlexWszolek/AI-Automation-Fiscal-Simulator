"""Phase 2 gate — disposition router + compute pool. C2 (partition + meter), C3 (compute-pool
flow), C-gate (net_saving ≥ 0), C5b (destinations partition the saved bill), the corporate
reduction anchor, and the base-migration effect."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fiscal_model import compute_pool
from fiscal_model.dynamics import DynamicModel, DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.firms import disposition
from fiscal_model.levers_v2 import DEFAULTS_V1REDUCTION

SCEN = dict(cognitive_feasibility=0.85, physical_feasibility=0.25,
            adoption_path=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9])
DISP = dict(retained_profit_share=0.6, price_reduction_share=0.2, survivor_gains_share=0.2,
            auto_cost=0.1, offshore_share=0.25, compute_effective_rate=0.10)


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built — run `python -m fiscal_model.dynamics`")
    return pd.read_parquet(DELTA_CACHE)


def _route(v2p):
    stock = np.full(100, 1000.0)
    comp = np.full(100, 100_000.0)
    base = np.full(100, 30_000.0)
    return disposition.route(stock, comp, base, v2p)


def test_c2_partition_and_meter():
    v2p = replace(DEFAULTS_V1REDUCTION, **DISP)
    assert np.isclose(disposition.shares_sum(v2p), 1.0)               # partition sums to 1
    d = _route(v2p)
    assert np.isclose(d.automation_spend + d.net_saving, d.saved_bill)  # meter identity
    assert np.isclose(d.retained_profit + d.price_reduction + d.survivor_gains, d.net_saving)


def test_c5b_destinations_partition_saved_bill():
    d = _route(replace(DEFAULTS_V1REDUCTION, **DISP))
    assert np.isclose(d.automation_spend + d.retained_profit + d.price_reduction
                      + d.survivor_gains, d.saved_bill)


@pytest.mark.parametrize("auto_cost", [0.0, 0.1, 0.5, 1.0])
def test_c_gate_net_saving_nonneg(auto_cost):
    v2p = replace(DEFAULTS_V1REDUCTION, auto_cost=auto_cost,
                  retained_profit_share=1.0, price_reduction_share=0.0, survivor_gains_share=0.0)
    assert _route(v2p).net_saving >= -1e-9


def test_c3_compute_pool_flow():
    v2p = replace(DEFAULTS_V1REDUCTION, **DISP)
    cp = compute_pool.route_to_compute_pool(1000.0, v2p)
    assert np.isclose(cp.inflow, 1000.0)
    assert np.isclose(cp.domestic + cp.offshore_leak, cp.inflow)
    assert np.isclose(cp.tax_fed, cp.domestic * v2p.compute_effective_rate)


def test_corporate_reduction_equals_v1(data, deltas, c8_compare):
    v2p = replace(DEFAULTS_V1REDUCTION, **SCEN)         # disposition off
    _, r2 = c8_compare(data, deltas, v2p, ["corp_offset_B"])
    assert (r2["compute_pool_tax_B"] == 0).all()


def test_conservation_in_live_run(data, deltas):
    # C2 / C-gate / C5b asserted on the disp produced INSIDE a real run (not just a synthetic _route)
    res = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN, **DISP)).run()
    assert np.allclose(res["automation_spend_B"] + res["net_saving_B"], res["saved_bill_B"])   # C2 meter
    assert np.allclose(res["retained_profit_B"] + res["price_reduction_B"]                     # C2 partition
                       + res["survivor_gains_B"], res["net_saving_B"])
    assert (res["net_saving_B"] >= -1e-9).all()                                                # C-gate
    assert np.allclose(res["automation_spend_B"] + res["retained_profit_B"]                    # C5b
                       + res["price_reduction_B"] + res["survivor_gains_B"], res["saved_bill_B"])


def test_corporate_xor_guard(data, deltas):
    # corp_offset_scale / surplus_capture are superseded by the router — V2 must reject ≠ 1.0
    with pytest.raises(AssertionError):
        DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, corp_offset_scale=0.5))
    with pytest.raises(AssertionError):
        DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, surplus_capture=0.5))


def test_base_migration_shrinks_recovery_and_grows_deficit(data, deltas):
    r0 = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN)).run()
    r1 = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN, **DISP)).run()
    rec0 = r0["corp_offset_B"].iloc[-1] + r0["compute_pool_tax_B"].iloc[-1]
    rec1 = r1["corp_offset_B"].iloc[-1] + r1["compute_pool_tax_B"].iloc[-1]
    assert rec1 < rec0                                          # capital recovery shrinks
    assert r1["fed_debt_B"].iloc[-1] > r0["fed_debt_B"].iloc[-1]   # deficit grows
    # comp migrated to a lightly-taxed pool: its tax is far below the corporate tax it replaced
    assert r1["compute_pool_tax_B"].iloc[-1] < 0.25 * r0["corp_offset_B"].iloc[-1]
    assert r1["offshore_leak_B"].iloc[-1] > 0                   # part leaks out of the US base
