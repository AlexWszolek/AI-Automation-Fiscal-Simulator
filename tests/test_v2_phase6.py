"""Phase 6 gate — full-system regression. Every conservation identity (C1–C8, C-gate, C-headcount,
C6-state, C7) must hold simultaneously across a SWEEP of lever combinations, not just the single
scenarios each phase pinned. This is the integration capstone: the multi-actor system stays internally
consistent under arbitrary settings. Plus the C8 anchor across a sweep of reduction-compatible scenarios,
and a performance budget.

Reconciliation identities use RELATIVE tolerance (bincount summation-order roundoff is ~1e-15 relative).
"""
from dataclasses import replace

import time

import numpy as np
import pandas as pd
import pytest

from fiscal_model import government, levers_v2, reabsorption
from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.levers_v2 import DEFAULTS_V1REDUCTION, DEFAULTS_SHIPPED

MILD = dict(cognitive_feasibility=0.4, physical_feasibility=0.1,
            adoption_path=[0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5])
STRONG = dict(cognitive_feasibility=0.85, physical_feasibility=0.25,
              adoption_path=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9])
DISP = dict(retained_profit_share=0.6, price_reduction_share=0.2, survivor_gains_share=0.2)


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built — run `python -m fiscal_model.dynamics`")
    return pd.read_parquet(DELTA_CACHE)


# The conservation battery lives in fiscal_model/invariants.py (one source of truth — the Monte Carlo
# runner spot-checks draws with the SAME identities this suite gates on).
from fiscal_model.invariants import _rel, assert_all_invariants  # noqa: E402  (re-exported for the sweep)


# --------------------------------------------------------------- the lever sweep
def _sweep():
    """Curated combinations stressing each channel + a few kitchen-sink runs. (id, overrides)."""
    base = []
    for scen_name, scen in (("mild", MILD), ("strong", STRONG)):
        base += [
            (f"{scen_name}-bare", dict(**scen)),
            (f"{scen_name}-disp", dict(**scen, **DISP, auto_cost=0.1, offshore_share=0.25)),
            (f"{scen_name}-survivor-cap", dict(**scen, **DISP, survivor_raise_ceiling=1.5,
                                               survivor_elasticity=-0.15)),
            (f"{scen_name}-survivor-unbounded", dict(**scen, **DISP,
                                                     survivor_raise_ceiling=float("inf"))),
            (f"{scen_name}-survivor-complement", dict(**scen, **DISP, survivor_raise_ceiling=1.5,
                                                      survivor_elasticity=0.25)),
            (f"{scen_name}-spillover-price", dict(**scen, **DISP, survivor_raise_ceiling=1.1,
                                                  survivor_spillover_to_profit=0.0)),
            (f"{scen_name}-macro", dict(**scen, **DISP, price_passthrough=0.3,
                                        productivity_passthrough=0.02)),
            (f"{scen_name}-exit-reab0", dict(**scen, lfp_exit_rate=0.05, reabsorption_rate=0.3)),
            (f"{scen_name}-demand", dict(**scen, **DISP, demand_multiplier=0.8)),
            (f"{scen_name}-state-cut", dict(**scen, **DISP, state_response="cut_spending",
                                            demand_multiplier=0.5)),
            (f"{scen_name}-state-mix", dict(**scen, **DISP, state_response="mix", state_cut_share=0.5,
                                            demand_multiplier=0.5)),
            (f"{scen_name}-rate-cap", dict(**scen, **DISP, state_rate_hike_cap=0.01,
                                           demand_multiplier=0.5)),
            (f"{scen_name}-ui0", dict(**scen, **DISP, ui_weeks=0)),
            (f"{scen_name}-ui52", dict(**scen, **DISP, ui_weeks=52)),
            (f"{scen_name}-pct-gdp", dict(**scen, **DISP, denominator="pct_gdp", price_passthrough=0.3)),
            # live mpc / stickiness scale the lagged-demand impulse (not frozen in the cache)
            (f"{scen_name}-mpc-stick", dict(**scen, **DISP, demand_multiplier=0.6, mpc=0.7,
                                            consumption_stickiness=0.5)),
            # post-hoc consumption scale + a non-default reabsorption haircut (Rung 0)
            (f"{scen_name}-cons-haircut", dict(**scen, **DISP, consumption_scale=0.6,
                                               reabsorption_rate=0.3, reemployment_haircut=0.6)),
            # a second compute-pool effective rate (live pool)
            (f"{scen_name}-compute-rate", dict(**scen, **DISP, auto_cost=0.15, offshore_share=0.3,
                                               compute_effective_rate=0.20)),
            (f"{scen_name}-kitchensink", dict(**scen, **DISP, auto_cost=0.1, offshore_share=0.25,
                                              survivor_raise_ceiling=1.5, survivor_elasticity=-0.15,
                                              price_passthrough=0.3, productivity_passthrough=0.02,
                                              lfp_exit_rate=0.05, reabsorption_rate=0.3,
                                              demand_multiplier=0.6, state_response="mix",
                                              state_cut_share=0.4, ubi_annual=12_000)),
        ]
    # scenario-independent branches the per-scenario grid never hits
    base += [
        ("logistic", dict(**STRONG, **DISP, exposure_mapping="logistic", logistic_steepness=0.8,
                          logistic_midpoint=0.1)),                         # the logistic diffusion branch
        ("scalar-adoption", dict(cognitive_feasibility=0.7, physical_feasibility=0.2, adoption=0.5,
                                 **DISP)),                                 # no adoption_path → constant branch
        ("market-exempt", dict(**STRONG, retained_profit_share=0.8, price_reduction_share=0.2,
                               survivor_gains_share=0.0, survivor_elasticity=-0.2,
                               survivor_raise_ceiling=1.5)),               # C5-market-exempt (gains=0)
    ]
    return base


SWEEP = _sweep()


@pytest.mark.parametrize("cfg_id,overrides", SWEEP, ids=[c[0] for c in SWEEP])
def test_full_battery_over_sweep(data, deltas, cfg_id, overrides):
    v2p = replace(DEFAULTS_V1REDUCTION, **overrides)
    res = DynamicModelV2(data, deltas, v2p).run()
    assert_all_invariants(res, v2p, deltas["employed"].sum() / 1e6)


def test_full_battery_rung1(data, deltas):
    # Rung 1 needs its disk cache; skip cleanly if absent (a fresh clone).
    if not reabsorption.engine_artifacts_exist():
        pytest.skip("benefit-lookup / NOC artifacts absent — build them (README Setup)")
    for scen in (MILD, STRONG):
        v2p = replace(DEFAULTS_V1REDUCTION, **scen, **DISP, reabsorption_rung=1,
                      reabsorption_rate=0.3, demand_multiplier=0.5, survivor_raise_ceiling=1.5)
        res = DynamicModelV2(data, deltas, v2p).run()
        assert_all_invariants(res, v2p, deltas["employed"].sum() / 1e6)


def test_shipped_default_full_battery(data, deltas):
    if not reabsorption.engine_artifacts_exist():
        pytest.skip("benefit-lookup / NOC artifacts absent — build them (README Setup)")
    res = DynamicModelV2(data, deltas, replace(DEFAULTS_SHIPPED, **STRONG)).run()
    assert_all_invariants(res, DEFAULTS_SHIPPED, deltas["employed"].sum() / 1e6)


# --------------------------------------------------------------- C8 across a sweep
C8_COLS = ["fed_deficit_B", "fed_debt_B", "state_gap_B", "employment_drop_pct", "revenue_lost_B",
           "transfers_added_B", "corp_offset_B", "ubi_required_rate"]
C8_SWEEP = [
    dict(**MILD), dict(**STRONG),
    dict(**STRONG, reabsorption_rate=0.5), dict(**STRONG, ui_weeks=0), dict(**STRONG, ui_weeks=52),
    dict(**STRONG, ubi_annual=15_000), dict(**STRONG, interest_rate=0.05),
    dict(**STRONG, reabsorption_rate=0.4, state_response="cut_spending"),
    # the logistic diffusion branch must ALSO reduce to v1 bit-for-bit
    dict(**STRONG, exposure_mapping="logistic", logistic_steepness=0.8, logistic_midpoint=0.1),
]


@pytest.mark.parametrize("overrides", C8_SWEEP, ids=[f"c8-{i}" for i in range(len(C8_SWEEP))])
def test_c8_reduction_across_sweep(data, deltas, c8_compare, overrides):
    # every behavioral lever off → v2 reproduces v1 bit-for-bit, across reduction-compatible scenarios
    c8_compare(data, deltas, replace(DEFAULTS_V1REDUCTION, **overrides), C8_COLS)


# NOTE — build-time kernel levers (dividend_tax_rate, passthrough_individual_rate,
# marginal_taxable_multiplier) are NOT swept here: they are baked into the worker-delta cache at build
# time (like surplus_capture), so on a V2Params with a pre-built cache they affect only the LIVE paths
# (mpc/consumption_stickiness reach the lagged-demand impulse — covered by `*-mpc-stick`). The cached
# corporate/consumption channels at other kernel points are exercised by test_kernel.py, and the V2
# conservation identities hold by construction regardless of the kernel values (the C8 anchor proves the
# propagation). A perturbed-kernel battery run would need a force-rebuild of the shared cache.


# --------------------------------------------------------------- price double-application (A2, generalized)
def test_price_double_application_all_nominal(data, deltas):
    # A2 generalized beyond the frozen phase-3 list: price_passthrough must move ONLY the real / %-GDP
    # columns; EVERY nominal column (incl. the phase-4/5 survivor + ledger + state columns) is bit-invariant.
    cfg = dict(**STRONG, **DISP, survivor_raise_ceiling=1.5, survivor_elasticity=-0.15,
               demand_multiplier=0.5, productivity_passthrough=0.0)
    r0 = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **cfg, price_passthrough=0.0)).run()
    r1 = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **cfg, price_passthrough=0.6)).run()
    assert (r1["price_level"] < 1.0).any()                     # ΔP is actually live
    driven = lambda c: ("real" in c or "pct_gdp" in c or c == "price_level")
    nominal = [c for c in r0.columns if r0[c].dtype.kind == "f" and not driven(c)]
    for c in nominal:
        assert np.allclose(r0[c].to_numpy(), r1[c].to_numpy(), rtol=0, atol=1e-9), f"nominal {c} moved with ΔP"


# --------------------------------------------------------------- fail-loud input guards
def test_offsum_and_out_of_domain_levers_raise(data, deltas):
    # off-sum disposition shares silently break C2/C5b; out-of-[0,1] inputs silently break C-gate/C3/P —
    # the model must reject them at construction, not run green to a wrong answer.
    with pytest.raises(ValueError):
        DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, retained_profit_share=0.5,
                                             price_reduction_share=0.5, survivor_gains_share=0.5))
    for bad in (dict(auto_cost=1.5), dict(offshore_share=1.2), dict(price_passthrough=2.0)):
        with pytest.raises(ValueError):
            DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **bad))


# --------------------------------------------------------------- the demand one-period-lag carrier
def test_demand_lag_carrier(data, deltas):
    res = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **STRONG, demand_multiplier=0.6)).run()
    assert res["standing_withdrawal_B"].iloc[0] > 0             # the withdrawal level exists at t=0
    assert res["induced_M"].iloc[0] == 0.0                      # but lands a period later (0 at t=0)
    # the induced stock change at t equals the SIGNED controller flow queued at t−1 — the strict
    # one-period lag — over the interior periods (no transitions drain induced in this config).
    d_induced = np.diff(res["induced_M"].to_numpy(), prepend=0.0)
    k = 8
    assert np.allclose(d_induced[1:k], res["induced_pending_M"].to_numpy()[:k - 1], atol=1e-9)


# --------------------------------------------------------------- performance budget
def test_performance_budget(data, deltas):
    # the per-period recompute target is < 1s over the 33k cells (the plan's tractability bar)
    v2p = replace(DEFAULTS_V1REDUCTION, **STRONG, **DISP, demand_multiplier=0.5, n_periods=10)
    m = DynamicModelV2(data, deltas, v2p)            # construction (engine builds) excluded from the budget
    t0 = time.perf_counter()
    m.run()
    per_period = (time.perf_counter() - t0) / 10
    assert per_period < 1.0, f"per-period recompute {per_period:.3f}s exceeds the 1s budget"
