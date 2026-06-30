"""Phase 1 gate — the 5-state worker machine. The UI-blend reduction test, C1 with exit +
reabsorption, the lfp_exit physics, and the no-exit reduction anchor."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fiscal_model.dynamics import DynamicModel, DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.levers_v2 import DEFAULTS_V1REDUCTION, DEFAULTS_SHIPPED

SCEN = dict(cognitive_feasibility=0.85, physical_feasibility=0.25,
            adoption_path=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9])
C8 = ["fed_deficit_B", "fed_debt_B", "state_gap_B", "employment_drop_pct", "revenue_lost_B",
      "transfers_added_B", "corp_offset_B", "ubi_required_rate"]


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built — run `python -m fiscal_model.dynamics`")
    return pd.read_parquet(DELTA_CACHE)


@pytest.mark.parametrize("ui_weeks", [0, 13, 26, 39, 52])
def test_ui_blend_reduction(data, deltas, c8_compare, ui_weeks):
    # the 5-state on-UI cohort must reproduce v1's ui_share during/after blend across UI durations
    v2p = replace(DEFAULTS_V1REDUCTION, ui_weeks=ui_weeks, reabsorption_rate=0.3, **SCEN)
    c8_compare(data, deltas, v2p, C8)


def test_c1_with_exit_and_reabsorption(data, deltas):
    v2p = replace(DEFAULTS_V1REDUCTION, reabsorption_rate=0.3, lfp_exit_rate=0.1, **SCEN)
    res = DynamicModelV2(data, deltas, v2p).run()
    baseline_M = deltas["employed"].sum() / 1e6
    assert np.allclose(res["population_M"].to_numpy(), baseline_M, atol=1e-6)


def test_lfp_exit_grows_absorbing_exited_stock(data, deltas):
    v2p = replace(DEFAULTS_V1REDUCTION, reabsorption_rate=0.3, lfp_exit_rate=0.1, **SCEN)
    res = DynamicModelV2(data, deltas, v2p).run()
    assert res["exited_M"].iloc[-1] > 0
    assert res["exited_M"].is_monotonic_increasing       # exited is absorbing


def test_lfp_exit_increases_long_run_loss(data, deltas):
    base = replace(DEFAULTS_V1REDUCTION, reabsorption_rate=0.4, lfp_exit_rate=0.0, **SCEN)
    exit_ = replace(DEFAULTS_V1REDUCTION, reabsorption_rate=0.4, lfp_exit_rate=0.1, **SCEN)
    d0 = DynamicModelV2(data, deltas, base).run()["fed_debt_B"].iloc[-1]
    d1 = DynamicModelV2(data, deltas, exit_).run()["fed_debt_B"].iloc[-1]
    assert d1 > d0   # exit siphons reabsorbable workers into permanent loss


def test_reduction_holds_at_no_exit(data, deltas, c8_compare):
    v2p = replace(DEFAULTS_V1REDUCTION, reabsorption_rate=0.5, lfp_exit_rate=0.0, **SCEN)
    _, r2 = c8_compare(data, deltas, v2p, C8)
    assert (r2["exited_M"] == 0).all()


def test_rung1_now_implemented_rung2_still_boundary(data, deltas):
    # Phase 4 wired Rung 1 (service floor) — it must construct without NotImplementedError (skip if its
    # disk cache is absent, since construction loads it). Rung 2 (cross-cell routing) stays a boundary.
    from fiscal_model import reabsorption
    if not reabsorption.cache_path(DEFAULTS_SHIPPED.reabsorption_floor_pctile).exists():
        pytest.skip("Rung-1 reabsorption cache not built — run `python -m fiscal_model.reabsorption`")
    DynamicModelV2(data, deltas, replace(DEFAULTS_SHIPPED, **SCEN))            # no raise
    with pytest.raises(NotImplementedError):
        DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, reabsorption_rung=2, **SCEN))
