"""Reemployment-overhaul gate — the finite refuge and the reabsorbed wage dynamics.

FINITE REFUGE (rung-1 semantics, no lever): the reabsorbed move into low-exposure service work,
so the effective reabsorption rate scales by the un-automated share of that refuge employment.
Under AGI-grade configs the refuge shrinks and reabsorption chokes off; under mild configs
capacity stays ≈ 1 and behavior is (near-)unchanged. Rung 0 — the C8 anchor — is untouched.

WAGE DYNAMICS (rung 1, gated levers, off = 0): W_reab = 1 + baumol·(Y_{t−1}−1) − crowding·slack_{t−1}.
Baumol can dominate crowding: re-employed wages RISE amid mass displacement when the productivity
dividend outruns the supply shock — the user-required scenario, pinned below.
"""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from fiscal_model import reabsorption
from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.levers_v2 import DEFAULTS_V1REDUCTION as R
from fiscal_model.levers_v2 import DEFAULTS_SHIPPED, is_v1_reduction

DISP = dict(retained_profit_share=0.6, price_reduction_share=0.2, survivor_gains_share=0.2)


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built")
    return pd.read_parquet(DELTA_CACHE)


def _rung1(data):
    if not reabsorption.engine_artifacts_exist():
        pytest.skip("benefit-lookup / NOC artifacts not built")


def _agi(**kw):
    """Full-feasibility fast automation — the refuge-killing corner."""
    base = dict(cognitive_feasibility=1.0, physical_feasibility=1.0,
                robotics_lag=0.0, adoption_path=[1.0] * 8, n_periods=8,
                reabsorption_rate=0.4, reabsorption_rung=1, demand_multiplier=0.0, **DISP)
    base.update(kw)
    return replace(DEFAULTS_SHIPPED, **base)


def _mild(**kw):
    """Acemoglu-grade automation — the refuge barely touched."""
    base = dict(cognitive_feasibility=0.2, physical_feasibility=0.05,
                robotics_lag=0.0, adoption_path=list(np.linspace(0.02, 0.23, 8)), n_periods=8,
                reabsorption_rate=0.4, reabsorption_rung=1, demand_multiplier=0.0, **DISP)
    base.update(kw)
    return replace(DEFAULTS_SHIPPED, **base)


# ------------------------------------------------------------------ finite refuge capacity
def test_refuge_capacity_chokes_reabsorption_under_agi(data, deltas):
    _rung1(data)
    agi = DynamicModelV2(data, deltas, _agi()).run()
    mild = DynamicModelV2(data, deltas, _mild()).run()
    # AGI: capacity collapses immediately (everything feasible automates at t=0) and stays put
    assert agi["refuge_capacity"].iloc[0] < 0.5
    assert (agi["refuge_capacity"].diff().dropna() <= 1e-12).all()      # monotone non-increasing
    # mild: the refuge is barely touched — near-full capacity throughout
    assert mild["refuge_capacity"].iloc[-1] > 0.9
    # the choke identity, exactly: Δreabsorbed_{t→t+1} = (exhausted+on_ui+induced)_t × rate × cap_t
    # (rows are pre-transition stocks; demand is off so induced ≡ 0)
    for t in range(len(agi) - 1):
        pool = (agi["exhausted_M"] + agi["on_ui_M"] + agi["induced_M"]).iloc[t]
        d_reab = agi["reabsorbed_M"].iloc[t + 1] - agi["reabsorbed_M"].iloc[t]
        expect = pool * 0.4 * agi["refuge_capacity"].iloc[t]
        assert abs(d_reab - expect) < 1e-9 * max(pool, 1.0), f"period {t}: {d_reab} != {expect}"


def test_refuge_capacity_off_at_rung0(data, deltas):
    """Rung 0 is the C8 anchor: the capacity column reports 1.0 and the rate is unscaled."""
    r = DynamicModelV2(data, deltas, replace(
        R, cognitive_feasibility=1.0, adoption_path=[1.0] * 5, reabsorption_rate=0.3)).run()
    assert (r["refuge_capacity"] == 1.0).all()
    # unscaled-rate arithmetic: reabsorbed grows by rate × (exhausted + on_ui) each period —
    # if capacity leaked into rung 0 this pin would move
    assert r["reabsorbed_M"].iloc[1] > 0


# ------------------------------------------------------------------ reabsorbed wage dynamics
def test_baumol_beats_crowding_wages_rise_amid_mass_displacement(data, deltas):
    """THE requirement: it must be possible for re-employed wages to RISE even under massive
    displacement, when the Baumol pull (productivity → service wages) outruns crowding."""
    _rung1(data)
    p = _agi(productivity_passthrough=0.9, reab_wage_baumol=0.8, reab_wage_crowding=0.2)
    r = DynamicModelV2(data, deltas, p).run()
    assert r["employment_drop_pct"].iloc[-1] > 30           # massive displacement…
    assert r["W_reab"].iloc[-1] > 1.02                      # …and rising re-employed wages
    assert (r["W_reab"].diff().dropna() > -1e-9).all()      # monotone under a monotone Y


def test_crowding_alone_pushes_wages_down_and_worsens_the_deficit(data, deltas):
    _rung1(data)
    base = DynamicModelV2(data, deltas, _agi()).run()
    crowd = DynamicModelV2(data, deltas, _agi(reab_wage_crowding=0.8)).run()
    assert crowd["W_reab"].iloc[-1] < 0.9                   # deep slack → deep wage cut
    assert crowd["fed_deficit_B"].iloc[-1] > base["fed_deficit_B"].iloc[-1], \
        "lower re-employed wages must mean less tax and a worse deficit"


def test_baumol_alone_improves_the_deficit(data, deltas):
    _rung1(data)
    base = DynamicModelV2(data, deltas, _agi(productivity_passthrough=0.9)).run()
    bau = DynamicModelV2(data, deltas, _agi(productivity_passthrough=0.9,
                                            reab_wage_baumol=1.0)).run()
    assert bau["W_reab"].iloc[-1] > base["W_reab"].iloc[-1] == 1.0
    assert bau["fed_deficit_B"].iloc[-1] < base["fed_deficit_B"].iloc[-1]


def test_off_is_bitwise_fast_path(data, deltas):
    """Levers at 0 must reuse the bind-time delta verbatim — W_reab ≡ 1 and the engine is never
    re-called (the run twice pattern: identical outputs at identical configs)."""
    _rung1(data)
    p = _mild()
    a = DynamicModelV2(data, deltas, p).run()
    assert (a["W_reab"] == 1.0).all()


def test_domain_guards_and_reduction_listing(data, deltas):
    with pytest.raises(ValueError):
        DynamicModelV2(data, deltas, replace(R, reab_wage_baumol=1.5))
    with pytest.raises(ValueError):
        DynamicModelV2(data, deltas, replace(R, reab_wage_crowding=-0.1))
    assert not is_v1_reduction(replace(R, reab_wage_baumol=0.3))
    assert not is_v1_reduction(replace(R, reab_wage_crowding=0.3))


def test_invariants_battery_with_everything_on(data, deltas):
    """Kitchen sink: capacity active + both wage levers + demand feedback — the full C-battery."""
    _rung1(data)
    from fiscal_model.invariants import assert_all_invariants
    p = _agi(productivity_passthrough=0.9, reab_wage_baumol=0.7, reab_wage_crowding=0.4,
             demand_multiplier=0.8, lfp_exit_rate=0.05, attrition_rate=0.025)
    res = DynamicModelV2(data, deltas, p).run()
    assert_all_invariants(res, p, deltas["employed"].sum() / 1e6)


def test_reab_delta_vectorized_parity(data, deltas):
    """The vectorized ReabsorptionEngine.delta (hoisted before-sides + shared slot matrices +
    hoisted at-mean transfer interp) against the per-state/per-program reference _delta_loop
    (always pure np.interp) — the anchor that lets the fast paths exist (the
    survivor._delta_loop / mc_pool discipline).

    wage_index==1 (bind time, every non-Baumol scenario): BIT-FOR-BIT on all 7 outputs.
    wage_index≠1 (the per-period Baumol/crowding path): delta uses the _interp_rows shared-search
    blend, which agrees with np.interp only to 1 ulp (numpy's kernel fuses the final multiply-add
    on some platforms) — so the anchor there is a tight relative tolerance, still far below any
    real logic bug."""
    from fiscal_model.kernel import KernelParams
    from fiscal_model.transfers import TransferLookup
    eng = reabsorption.ReabsorptionEngine(data, deltas, TransferLookup(), KernelParams())
    keys = ("inc_fed", "inc_state", "payroll_fed", "cons_state",
            "transfer_fed", "transfer_state", "net_takehome_loss")
    for hc, wi in ((0.0, 1.0), (0.05, 1.0), (0.25, 0.7), (0.6, 1.3), (1.0, 1.0)):
        new = eng.delta(hc, 0.6, 0.5, wage_index=wi)
        ref = eng._delta_loop(hc, 0.6, 0.5, wage_index=wi)
        for k in keys:
            if wi == 1.0:
                assert np.array_equal(new[k], ref[k], equal_nan=True), (hc, wi, k)
            else:
                np.testing.assert_allclose(new[k], ref[k], rtol=1e-12, atol=1e-9,
                                           err_msg=str((hc, wi, k)))


def test_interp_rows_matches_np_interp_rounding_only(data, deltas):
    """_interp_rows (the shared-search multi-program blend on the wage-dynamics path) vs per-row
    np.interp over every real transfer grid: identical binary-search bracket and edge rules, so
    the ONLY permitted difference is the final multiply-add rounding (numpy's kernel may fuse it;
    ufunc composition rounds twice). That bounds the ABSOLUTE error at ~1 ulp of the program's
    benefit scale (~1e-12 dollars) — near cancellation points the relative-to-result error can
    look huge while the absolute error stays there. Any bracket/edge bug would differ at the
    benefit scale itself, 12 orders above this bound. Queries cover knots exactly, knots±1ulp,
    midpoints, and beyond-grid overshoot both sides."""
    from fiscal_model.kernel import KernelParams
    from fiscal_model.transfers import TransferLookup
    eng = reabsorption.ReabsorptionEngine(data, deltas, TransferLookup(), KernelParams())
    n_groups = 0
    for (f, s, k), tr in eng._tr.items():
        xs, Y, progs, S = tr[0], tr[1], tr[2], tr[5]
        if not progs:
            continue
        eps = np.spacing(np.abs(xs) + 1.0)
        q = np.concatenate([xs, xs - eps, xs + eps,
                            (xs[:-1] + xs[1:]) / 2 if xs.size > 1 else xs,
                            np.linspace(-1.0, 1.5 * abs(float(xs[-1])) + 1.0, 401)])
        got = reabsorption._interp_rows(xs, Y, q, S)             # the production (slope-matrix) path
        # divide-then-gather ≡ gather-then-divide: the S fast path must be BIT-identical to the
        # direct formula (same elementwise operands and ops, just batched at bind time)
        assert np.array_equal(got, reabsorption._interp_rows(xs, Y, q)), (f, s, k)
        want = np.vstack([np.interp(q, xs, Y[p]) for p in range(Y.shape[0])])
        scale = np.abs(Y).max(axis=1, keepdims=True)             # per-program benefit scale
        bound = 2.0 * np.spacing(np.maximum(np.abs(want), scale))
        assert (np.abs(got - want) <= bound).all(), (f, s, k)
        n_groups += 1
    assert n_groups > 300              # the sweep really covered the (filing, state, kids) grids
