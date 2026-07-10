"""Global-screening gate — the LHS sampler's statistical guarantees (stratification, cross-dim
independence, the exactly-uniform simplex, fraction-of-bound tax), the analysis indices (η² on a
synthetic non-monotone response, the alternation metric), and an artifact-gated mini-battery that
runs real points through one ScenarioContext with the full invariant + spot-check machinery."""
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fiscal_model import mc, reabsorption
from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model.levers_v2 import DEFAULTS_SHIPPED

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import global_screening as gs  # noqa: E402  (scripts/ is not a package)

BASE = replace(DEFAULTS_SHIPPED, n_periods=10, adoption_path=list(np.linspace(0.05, 0.5, 10)))


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built")
    return pd.read_parquet(DELTA_CACHE)


@pytest.fixture(scope="module")
def sampled():
    draws, samples = mc.lhs_draws(BASE, 500, seed=0)
    return draws, samples


# --------------------------------------------------------------- sampler statistics (pure)
def test_marginal_stratification(sampled):
    """Latin property: every dim's u-column hits each of the n strata exactly once."""
    _, s = sampled
    n = len(s)
    for dim in mc.GLOBAL_RANGES:
        strata = np.floor(s[f"u_{dim}"].to_numpy() * n).astype(int)
        assert sorted(strata) == list(range(n)), dim


def test_cross_dim_rank_independence(sampled):
    """One permutation PER dim — a shared permutation (the classic hand-rolled-LHS bug) would
    show |ρ| ≈ 1 between every pair; independent permutations give |ρ| ~ 1/√n."""
    _, s = sampled
    u = s[[f"u_{d}" for d in mc.GLOBAL_RANGES]]
    c = u.corr(method="spearman").abs().to_numpy().copy()
    np.fill_diagonal(c, 0.0)
    assert c.max() < 0.2, f"cross-dim rank correlation {c.max():.3f} — shared-permutation bug?"


def test_constraint_battery(sampled):
    """Every sampled config satisfies the model's domain asserts by construction."""
    _, s = sampled
    assert ((s.retained_profit_share + s.price_reduction_share + s.survivor_gains_share - 1.0)
            .abs() < 1e-12).all(), "disposition simplex must sum to 1 exactly"
    assert ((s[["retained_profit_share", "price_reduction_share", "survivor_gains_share"]] >= 0)
            .all().all())
    assert ((s.reabsorption_rate + s.lfp_exit_rate) <= 1.0).all(), \
        "workers.age_and_transition asserts reab+lfp ≤ 1"
    assert (s.automation_tax_rate
            <= s.retained_profit_share * (1 - s.auto_cost) + 1e-12).all(), "robot-tax bound"
    assert s.ui_weeks.between(0, 52).all() and s.ui_weeks.dtype.kind == "i"
    for dim, (lo, hi, _tag) in mc.GLOBAL_RANGES.items():
        if dim in ("retained_profit_share", "price_reduction_share"):   # stick-breaking, [0,1]
            lo, hi = 0.0, 1.0
        assert s[dim].between(lo, hi).all(), dim


def test_simplex_uniformity(sampled):
    """Stick-breaking gives the exact uniform-simplex marginals: retained ~ Beta(1,2) (mean 1/3),
    and by symmetry price/survivor also mean 1/3 (normalized-uniforms would over-weight the
    centroid and put retained's mean near 0.39)."""
    _, s = sampled
    assert abs(s.retained_profit_share.mean() - 1 / 3) < 0.02
    assert abs(s.price_reduction_share.mean() - 1 / 3) < 0.03
    assert abs(s.survivor_gains_share.mean() - 1 / 3) < 0.03


def test_determinism_and_seed_variation():
    d1, s1 = mc.lhs_draws(BASE, 50, seed=9)
    d2, s2 = mc.lhs_draws(BASE, 50, seed=9)
    d3, s3 = mc.lhs_draws(BASE, 50, seed=10)
    assert s1.equals(s2) and d1[13] == d2[13]
    assert not s1.equals(s3)


def test_fraction_of_bound_tax_semantics(sampled):
    """The tornado ranks the independent fraction; the realized rate = frac·retained·(1−auto_cost)
    exactly (no clip mass — the model's fail-loud bound is unreachable from the sampler)."""
    draws, s = sampled
    expect = s.automation_tax_frac * s.retained_profit_share * (1 - s.auto_cost)
    assert np.allclose(s.automation_tax_rate, expect, rtol=0, atol=1e-15)
    assert all(d.automation_tax_rate == s.automation_tax_rate.iloc[i]
               for i, d in enumerate(draws[:20]))


def test_range_overrides():
    _, s = mc.lhs_draws(BASE, 100, seed=1, range_overrides=gs.CYCLE_OVERRIDES)
    assert s.adoption_end.min() >= 0.7 and s.demand_multiplier.min() >= 1.0
    assert s.reabsorption_rate.max() <= 0.2


def test_draws_are_template_derivatives(sampled):
    """replace(base, …) derivatives only — a fresh V2Params would trip the context frozen-field
    guard (== over every non-whitelisted field)."""
    draws, _ = sampled
    for d in draws[:20]:
        for name in mc.FROZEN:
            assert getattr(d, name) == getattr(BASE, name), name
        assert len(d.adoption_path) == BASE.n_periods and d.adoption_path[0] == 0.05


# --------------------------------------------------------------- analysis indices (pure)
def test_eta2_catches_nonmonotone():
    """A pure V-shape has Spearman ≈ 0 but strong η² — the disagreement is the non-monotone flag."""
    rng = np.random.default_rng(0)
    x = pd.Series(rng.random(2000))
    y = (x - 0.5) ** 2 + pd.Series(rng.normal(0, 0.01, 2000))
    rho = float(x.rank().corr(y.rank()))
    _e2, e2_adj = gs.eta_squared(x, y)
    assert abs(rho) < 0.1 and e2_adj > 0.5


def test_eta2_debias():
    """Pure noise: raw η² sits at its null bias (k−1)/(n−1); the debiased value collapses to ~0."""
    rng = np.random.default_rng(1)
    x, y = pd.Series(rng.random(400)), pd.Series(rng.normal(size=400))
    e2, e2_adj = gs.eta_squared(x, y)
    assert e2 > 0.01 and e2_adj < 0.04


def test_alternation_count():
    monotone = np.array([-3.0, -2.5, -2.0, -1.0, -0.5])
    trough_recovery = np.array([-3.0, -2.0, -1.0, 1.0, 2.0])
    cycle = np.array([5.0, -5.0, 5.0, -5.0, 5.0])
    tiny_flips = np.array([-3.0, 0.01, -0.02, 0.01, -3.0])   # sub-threshold wiggle
    assert gs.alternation_count(monotone, 0.1) == 0
    assert gs.alternation_count(trough_recovery, 0.1) == 1
    assert gs.alternation_count(cycle, 0.1) == 4
    assert gs.alternation_count(tiny_flips, 0.1) == 0


def test_regime_classification():
    df = pd.DataFrame({"fed_deficit_pct_gdp": [-0.5, 0.0, 0.4, 1.0, 2.9, 3.01]})
    assert list(gs.classify(df)) == [gs.REGIME_ORDER[0], gs.REGIME_ORDER[0], gs.REGIME_ORDER[1],
                                     gs.REGIME_ORDER[1], gs.REGIME_ORDER[2], gs.REGIME_ORDER[3]]


# --------------------------------------------------------------- mini-battery (artifact-gated)
def test_screening_battery(data, deltas):
    """~25 real global points through the actual runner: full invariants on every point, the
    3-draw fresh-vs-context bit-equality spot check, and the per-draw timing budget."""
    if not reabsorption.engine_artifacts_exist():
        pytest.skip("benefit-lookup / NOC artifacts absent — screening template needs rung 1")
    t0 = time.time()
    results = gs.run_sweep(data, deltas, BASE, 25, seed=123, label="test")
    per_draw = (time.time() - t0) / 25
    assert per_draw < 1.0, f"{per_draw:.2f}s/draw — screening budget blown"
    assert len(results) == 25 and results["fed_deficit_B"].notna().all()
    for col in ("cum_net_fiscal_B", "max_states_capped", "alternations", "pending_alternations",
                "regime" if "regime" in results else "fed_deficit_pct_gdp"):
        assert col in results.columns
    # the tornado builder runs on the mini-batch (values are noisy at n=25 — shape only)
    tor = gs.build_tornado(results)
    assert set(tor.columns) >= {"lever", "tag", "spearman", "eta2", "eta2_debiased"}
    assert len(tor) == len(mc.GLOBAL_RANGES)
