"""The declining baseline — `V2Params.demography_path`.

Why it exists: the model held the no-AI counterfactual at a fixed year-0 workforce. Where the
working-age population is projected to fall (Korea: roughly −35% by 2050), a flat baseline makes
the counterfactual a world that cannot happen, and every delta measured against it is mis-scaled.
The path is structural, taken from a national statistics office, and adds no free parameter.

Three things must hold, and they are the whole contract:
  1. OFF is exactly off — `None` and an all-ones path are bit-identical to today's behaviour.
  2. Conservation survives — the outflow routes employed → the delta-neutral `retired` bucket,
     both inside `WorkerStocks.total()`, so C1 (aggregate AND per-cell) is untouched.
  3. The counterfactual is fixed — under pure demographic decline with ZERO automation the
     headline `employment_drop_pct` reads ~0, i.e. it measures AI rather than demographics.
"""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.invariants import assert_all_invariants
from fiscal_model.levers_v2 import DEFAULTS_V1REDUCTION


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built")
    return pd.read_parquet(DELTA_CACHE)


def _run(data, deltas, **over):
    p = replace(DEFAULTS_V1REDUCTION, **over)
    return p, DynamicModelV2(data, deltas, p).run()


def _float_cols(df):
    return [c for c in df.columns if df[c].dtype.kind == "f"]


def test_flat_path_is_bit_identical_to_none(data, deltas):
    """OFF-stays-OFF, the C8-anchor discipline every new field here follows: an all-ones path must
    reproduce the None path BIT-FOR-BIT, not merely closely. `emp0 * (1 - 1.0)` is exactly 0.0 and
    `baseline_emp * 1.0` is exactly `baseline_emp`, so there is no excuse for drift."""
    n = DEFAULTS_V1REDUCTION.n_periods
    _, ref = _run(data, deltas)
    _, flat = _run(data, deltas, demography_path=[1.0] * n)
    for c in _float_cols(ref):
        assert np.array_equal(ref[c].to_numpy(), flat[c].to_numpy(), equal_nan=True), c


def test_pure_demographic_decline_is_not_reported_as_automation(data, deltas):
    """THE property the change exists for. Zero automation, a shrinking population: the workforce
    falls, but `employment_drop_pct` — the headline — must stay at zero, because nobody was
    displaced by AI. Against a flat baseline this column would report the entire demographic
    decline as if automation had caused it."""
    n = DEFAULTS_V1REDUCTION.n_periods
    decline = [1.0 - 0.03 * t for t in range(n)]
    _, res = _run(data, deltas, adoption=0.0, adoption_path=[0.0] * n, demography_path=decline)
    assert np.abs(res["employment_drop_pct"]).max() < 1e-9
    # the workforce really did shrink — the test is not vacuous
    assert res["employed_M"].iloc[-1] < res["employed_M"].iloc[0] * 0.9
    assert res["retired_M"].iloc[-1] > 0


def test_conservation_holds_under_decline(data, deltas):
    """C1 aggregate and per-cell, plus the whole invariant battery, with population falling AND
    automation running — the outflow must not leak mass out of the seven states."""
    n = DEFAULTS_V1REDUCTION.n_periods
    decline = [1.0 - 0.025 * t for t in range(n)]
    p, res = _run(data, deltas, demography_path=decline, adoption=0.6,
                  cognitive_feasibility=0.5)
    baseline_M = float(res["population_M"].iloc[0])
    assert_all_invariants(res, p, baseline_M)
    assert (res["max_cell_resid_M"] < 1e-6).all()


def test_outflow_is_capped_and_monotone(data, deltas):
    """A path steeper than the workforce can supply must not drive employment negative, and the
    retired stock must never fall (demographic outflow is one-way)."""
    n = DEFAULTS_V1REDUCTION.n_periods
    brutal = [max(0.02, 1.0 - 0.30 * t) for t in range(n)]
    _, res = _run(data, deltas, demography_path=brutal)
    assert (res["employed_M"] >= -1e-9).all()
    assert (np.diff(res["retired_M"].to_numpy()) >= -1e-9).all()


@pytest.mark.parametrize("bad", [[], [1.0, 0.0], [1.0, -0.1], [1.0, float("nan")]])
def test_degenerate_paths_are_rejected(data, deltas, bad):
    """A zero (or negative, or NaN) scale factor makes the period's counterfactual workforce zero
    and every per-capita ratio undefined. Fail loudly at bind rather than emit silent NaNs — the
    same house style as the robotics_base / ssdi_annual guards beside it."""
    with pytest.raises(ValueError, match="demography_path"):
        _run(data, deltas, demography_path=bad)


def test_demography_path_is_structural_not_perturbed(data, deltas):
    """It fixes the counterfactual rather than tuning a mechanism, so it must be FROZEN — a Monte
    Carlo draw perturbing the population projection would be nonsense, and a frozen field is part
    of the context key so changing it rebuilds the context rather than silently reusing one."""
    from fiscal_model import mc
    assert "demography_path" in mc.FROZEN
    assert "demography_path" not in mc.PERTURBED


def test_context_rejects_a_changed_path(data, deltas):
    """The frozen-field guard must actually fire: a context built flat cannot serve a declining
    run, because the template baked the flat baseline in."""
    from fiscal_model import mc
    n = DEFAULTS_V1REDUCTION.n_periods
    base = replace(DEFAULTS_V1REDUCTION, demography_path=[1.0] * n)
    ctx = mc.ScenarioContext(data, deltas, base)
    with pytest.raises(AssertionError, match="demography_path"):
        ctx.run(replace(base, demography_path=[1.0 - 0.02 * t for t in range(n)]))
