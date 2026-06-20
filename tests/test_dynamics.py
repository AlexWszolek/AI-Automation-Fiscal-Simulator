"""Tests for the §7 dynamic model — stock-flow accounting, the levers, and the two
headline theses (revenue falls faster than employment; states bear an unfinanceable gap)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fiscal_model import levers
from fiscal_model.dynamics import DynamicModel, DynamicsParams, DELTA_CACHE
from fiscal_model.kernel import KernelParams


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built — run `python -m fiscal_model.dynamics`")
    return pd.read_parquet(DELTA_CACHE)


def _model(data, deltas, **dp):
    lp = levers.LeverParams(cognitive_feasibility=0.85, physical_feasibility=0.25, adoption=1.0)
    path = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9]
    return DynamicModel(data, deltas, lp, DynamicsParams(n_periods=10, adoption_path=path, **dp))


def test_run_shape(data, deltas):
    res = _model(data, deltas).run()
    assert len(res) == 10
    assert {"fed_deficit_B", "fed_debt_B", "state_gap_B", "employment_drop_pct"} <= set(res.columns)


def test_employment_falls_debt_rises(data, deltas):
    res = _model(data, deltas).run()
    assert res["employed_M"].is_monotonic_decreasing
    assert res["fed_debt_B"].is_monotonic_increasing
    assert res["fed_debt_B"].iloc[-1] > 0


def test_revenue_falls_faster_than_employment(data, deltas):
    # base-migration thesis: the most-exposed work is the highest-paid
    res = _model(data, deltas).run()
    assert (res["revenue_lost_pct"] >= res["employment_drop_pct"] - 1e-6).all()
    assert res["revenue_lost_pct"].iloc[3] > res["employment_drop_pct"].iloc[3]


def test_states_bear_unfinanceable_gap(data, deltas):
    res = _model(data, deltas).run()
    assert (res["state_gap_B"] > 0).all()


def test_corporate_offset_cushions_federal(data, deltas):
    res = _model(data, deltas).run()
    # the federal deficit is well below gross revenue lost + transfers, thanks to the offset
    assert (res["corp_offset_B"] > 0).all()
    assert (res["fed_deficit_B"] < res["revenue_lost_B"] + res["transfers_added_B"]).all()


def test_reabsorption_reduces_debt(data, deltas):
    base = _model(data, deltas, reabsorption_rate=0.0).run()
    reab = _model(data, deltas, reabsorption_rate=0.5).run()
    assert reab["fed_debt_B"].iloc[-1] < base["fed_debt_B"].iloc[-1]


def test_demand_multiplier_increases_deficit(data, deltas):
    base = _model(data, deltas, demand_multiplier=0.0).run()
    mult = _model(data, deltas, demand_multiplier=0.5).run()
    assert mult["fed_deficit_B"].iloc[-1] > base["fed_deficit_B"].iloc[-1]


def test_ubi_required_rate_rises_as_base_erodes(data, deltas):
    res = _model(data, deltas, ubi_annual=12_000).run()
    assert res["ubi_required_rate"].iloc[-1] > res["ubi_required_rate"].iloc[0] > 0
