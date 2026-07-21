"""Monte Carlo gate — the fast-path ANCHOR (ScenarioContext.run == fresh construction, bit-for-bit),
the constraint-aware sampler properties, invariants across draws, and the per-draw timing budget."""
import time
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from fiscal_model import mc, reabsorption
from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.levers_v2 import DEFAULTS_SHIPPED, DEFAULTS_V1REDUCTION as R

SCEN = dict(cognitive_feasibility=0.85, physical_feasibility=0.25,
            adoption_path=list(np.linspace(0.1, 0.9, 10)))
BASE0 = replace(R, **SCEN, retained_profit_share=0.6, price_reduction_share=0.2,
                survivor_gains_share=0.2, survivor_raise_ceiling=1.5, survivor_elasticity=-0.15,
                demand_multiplier=0.5, auto_cost=0.10, automation_tax_rate=0.05, ubi_annual=12_000,
                ubi_recapture_rate=0.25, lfp_exit_rate=0.03, attrition_rate=0.025,
                reabsorption_rate=0.3, price_passthrough=0.3, productivity_passthrough=0.3,
                baseline_growth_rate=0.04, robotics_lag=4.0)          # rung 0, everything live


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built")
    return pd.read_parquet(DELTA_CACHE)


def _assert_bit_equal(a: pd.DataFrame, b: pd.DataFrame):
    assert list(a.columns) == list(b.columns)
    for c in a.columns:
        av, bv = a[c].to_numpy(), b[c].to_numpy()
        if av.dtype.kind == "f":
            assert np.array_equal(av, bv, equal_nan=True), f"column {c} differs (bitwise)"
        else:
            assert (av == bv).all(), f"column {c} differs"


# --------------------------------------------------------------- THE anchor: fast path == slow path
@pytest.mark.parametrize("rung", [0, 1])
def test_fast_path_bit_equivalence(data, deltas, rung):
    if rung == 1 and not reabsorption.engine_artifacts_exist():
        pytest.skip("benefit-lookup / NOC artifacts absent")
    base = replace(BASE0, reabsorption_rung=rung, reemployment_haircut=0.3)
    ctx = mc.ScenarioContext(data, deltas, base)
    cases = mc.sample_draws(base, 4, spread=0.15, seed=7)
    # the lag==0 branch is the one that exercises the g_cell rebind — force one such draw explicitly
    cases.append(replace(cases[0], robotics_lag=0.0))
    for i, d in enumerate(cases):
        fast = ctx.run(d)
        slow = DynamicModelV2(data, deltas, d).run()
        _assert_bit_equal(fast, slow)
    # and the template itself is uncorrupted after the sequence (shared-state mutation would show here)
    _assert_bit_equal(ctx.run(base), DynamicModelV2(data, deltas, base).run())


def test_context_rejects_structural_drift(data, deltas):
    ctx = mc.ScenarioContext(data, deltas, BASE0)
    with pytest.raises(AssertionError):
        ctx.run(replace(BASE0, reabsorption_rung=1))
    with pytest.raises(AssertionError):
        ctx.run(replace(BASE0, exposure_mapping="logistic"))


# --------------------------------------------------------------- sampler properties (pure)
def test_sampler_deterministic_and_spread_zero_exact():
    a = mc.sample_draws(BASE0, 10, 0.2, seed=3)
    b = mc.sample_draws(BASE0, 10, 0.2, seed=3)
    assert a == b                                               # dataclass equality, same seed
    assert all(d == BASE0 for d in mc.sample_draws(BASE0, 5, 0.0, seed=3))   # spread=0 ⇒ exact base


def test_sampler_domain_battery():
    for d in mc.sample_draws(BASE0, 500, spread=0.30, seed=1):
        s = d.retained_profit_share + d.price_reduction_share + d.survivor_gains_share
        assert abs(s - 1.0) < 1e-12                             # simplex
        assert d.automation_tax_rate <= d.retained_profit_share * (1 - d.auto_cost) + 1e-12
        assert 0 <= d.auto_cost <= 1 and 0 <= d.offshore_share <= 1
        assert 0 <= d.baseline_growth_rate <= 0.10 and 0 <= d.interest_rate <= 0.10
        assert isinstance(d.ui_weeks, int) and 0 <= d.ui_weeks <= 52
        assert max(d.adoption_path) <= 1.0 + 1e-12
        assert d.survivor_raise_ceiling >= 1.0
        assert np.sign(d.survivor_elasticity) == np.sign(BASE0.survivor_elasticity)   # sign preserved


def test_sampler_off_stays_off():
    off = replace(BASE0, ubi_annual=0.0, physical_feasibility=0.0, robotics_lag=0.0,
                  demand_multiplier=0.0, survivor_raise_ceiling=1.0,
                  retained_profit_share=1.0, price_reduction_share=0.0, survivor_gains_share=0.0,
                  automation_tax_rate=0.0, auto_cost=0.0)
    for d in mc.sample_draws(off, 200, spread=0.30, seed=2):
        assert d.ubi_annual == 0.0 and d.physical_feasibility == 0.0 and d.robotics_lag == 0.0
        assert d.demand_multiplier == 0.0 and d.survivor_raise_ceiling == 1.0
        assert (d.retained_profit_share, d.price_reduction_share, d.survivor_gains_share) == (1.0, 0.0, 0.0)
        assert d.automation_tax_rate == 0.0 and d.auto_cost == 0.0


def test_sampler_zero_bound_corner():
    # the user-reported crash class: auto_cost near 1 collapses the robot-tax bound — the sampler must
    # clip the tax toward 0, never producing a config the fail-loud model assert rejects
    hot = replace(BASE0, auto_cost=0.98, automation_tax_rate=0.01)
    for d in mc.sample_draws(hot, 200, spread=0.30, seed=4):
        assert d.automation_tax_rate <= d.retained_profit_share * (1 - d.auto_cost) + 1e-12


# --------------------------------------------------------------- runner: invariants + shapes + timing
def test_run_mc_invariants_and_shapes(data, deltas):
    ctx = mc.ScenarioContext(data, deltas, BASE0)
    res = mc.run_mc(ctx, n=20, spread=0.15, seed=5, invariant_every=1)   # FULL battery on every draw
    assert len(res.draws) == 20
    assert len(res.paths) == 20 * BASE0.n_periods
    assert not res.paths[mc.PATH_COLS].isna().any().any()
    assert set(res.percentiles["pct"].unique()) == set(mc.PCTS)
    varied = set(res.tornado["lever"].unique())
    assert "productivity_passthrough" in varied and "n_periods" not in varied
    # the base path sits inside the P10-P90 band (sane fans)
    p10 = res.percentiles.query("metric == 'fed_deficit_B' and pct == 10").set_index("period")["value"]
    p90 = res.percentiles.query("metric == 'fed_deficit_B' and pct == 90").set_index("period")["value"]
    base_path = res.base_run.set_index("period")["fed_deficit_B"]
    assert ((base_path >= p10 - 1e-9) & (base_path <= p90 + 1e-9)).mean() > 0.7


def test_per_draw_timing_budget(data, deltas):
    ctx = mc.ScenarioContext(data, deltas, BASE0)
    d = mc.sample_draws(BASE0, 1, 0.15, seed=9)[0]
    ctx.run(d)                                                   # warm
    t0 = time.perf_counter()
    for _ in range(3):
        ctx.run(d)
    assert (time.perf_counter() - t0) / 3 < 0.5                 # loose CI bound (measured ~0.15-0.24s)


def test_pooled_equals_serial_bitwise(data, deltas):
    """mc_pool determinism gate: chunked multi-process run ≡ the serial reference, bit-for-bit
    (workers regenerate the same seeded draw list and rows reassemble in global order). Spawn
    workers load their own data (~5s each) — the one deliberately slow test in this file."""
    if not reabsorption.engine_artifacts_exist():
        pytest.skip("rung-1 artifacts not built")
    from fiscal_model import mc_pool
    ctx = mc.ScenarioContext(data, deltas, BASE0)
    serial = mc.run_mc(ctx, n=8, spread=0.15, seed=0)
    ticks = []
    pooled = mc_pool.run_mc_pooled(ctx, n=8, spread=0.15, seed=0, workers=2, chunk=3,
                                   progress=lambda d, t: ticks.append((d, t)))
    for name in ("draws", "paths", "percentiles", "tornado", "base_run"):
        _assert_bit_equal(getattr(pooled, name), getattr(serial, name))
    assert ticks[-1] == (8, 8) and [t for _, t in ticks] == [8] * len(ticks)


def test_partial_callbacks_do_not_change_final(data, deltas):
    """Progressive display: partial MCResults fire mid-run with increasing n, and the FINAL
    result is bit-identical to a plain run (same rows in the same order, same finalize)."""
    if not reabsorption.engine_artifacts_exist():
        pytest.skip("rung-1 artifacts not built")
    ctx = mc.ScenarioContext(data, deltas, BASE0)
    plain = mc.run_mc(ctx, n=8, spread=0.15, seed=0)
    partials = []
    with_p = mc.run_mc(ctx, n=8, spread=0.15, seed=0,
                       on_partial=lambda r, d: partials.append((d, r)), partial_every=3)
    for name in ("draws", "paths", "percentiles", "tornado", "base_run"):
        _assert_bit_equal(getattr(with_p, name), getattr(plain, name))
    assert [d for d, _ in partials] == [3, 6]                 # fires mid-run only, never at n
    assert all(len(r.draws) == d for d, r in partials)        # each partial covers d draws
