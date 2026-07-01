"""Phase 4 gate — survivor wage + tax (A, G, J.1) and reabsorption Rung 1 (D).

C5c (router survivor_gains ≡ mechanical labour inflow — the leak detector), C6 (federal revenue
reconciliation, no residual), C-headcount (the taxed-population partition; the in-motion cohort priced
once — G), the sign-flip (survivor elasticity ±), J.1 order-independence (ΔW_market on t−1 slack, 0 at
t=0), the reabsorbed-cross-threshold (Rung 1 fires means-tested outlays Rung 0 silently misses), and the
v1-reduction anchor (survivor off + Rung 0 → exact v1).
"""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from fiscal_model import levers_v2, reabsorption
from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.levers_v2 import DEFAULTS_V1REDUCTION, DEFAULTS_SHIPPED

SCEN = dict(cognitive_feasibility=0.85, physical_feasibility=0.25,
            adoption_path=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9])
# disposition with a live survivor-gains share (the mechanical raise)
DISP = dict(retained_profit_share=0.6, price_reduction_share=0.2, survivor_gains_share=0.2)
C8 = ["fed_deficit_B", "fed_debt_B", "state_gap_B", "employment_drop_pct", "revenue_lost_B",
      "transfers_added_B", "corp_offset_B", "ubi_required_rate"]


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built — run `python -m fiscal_model.dynamics`")
    return pd.read_parquet(DELTA_CACHE)


@pytest.fixture(scope="module")
def rung1_ready():
    if not reabsorption.engine_artifacts_exist():
        pytest.skip("benefit-lookup / NOC artifacts absent — build them (README Setup)")
    return True


# ----------------------------------------------------------------- v1-reduction (C8)
def test_c8_holds_with_survivor_off(data, deltas, c8_compare):
    # survivor_gains_share=0 ∧ survivor_elasticity=0 ∧ rung 0 → survivor channel identically 0 → exact v1
    v2p = replace(DEFAULTS_V1REDUCTION, **SCEN)
    _, r2 = c8_compare(data, deltas, v2p, C8)
    assert (r2["W_survivor"] == 1.0).all()
    assert r2["survivor_gain_fed_B"].abs().max() == 0.0


# ----------------------------------------------------------------- C5c (the conserved partition)
def test_c5c_conserved_partition(data, deltas):
    # the capacity-checked mechanical raise conserves survivor_gains every period:
    # absorbed wage inflow + profit overflow + price overflow == survivor_gains (exact).
    res = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN, **DISP,
                                               survivor_raise_ceiling=1.5)).run()
    lhs = (res["survivor_mech_inflow_B"] + res["survivor_overflow_profit_B"]
           + res["survivor_overflow_price_B"])
    assert np.allclose(lhs.to_numpy(), res["survivor_gains_B"].to_numpy(), rtol=1e-12, atol=0)
    assert (res["survivor_gains_B"] > 0).any()                  # the channel is exercised
    assert (res["survivor_mech_inflow_B"] > 0).any()            # some is absorbed as wage
    assert (res["survivor_overflow_profit_B"] + res["survivor_overflow_price_B"] > 0).any()  # cap binds
    assert res["W_survivor"].max() <= 1.5 + 1e-9               # the ceiling bounds total W


def test_unbounded_ceiling_absorbs_all_gains(data, deltas):
    # the unbounded lever (ceiling=inf) recovers the faithful-C5c behavior: every gains dollar lands on
    # survivor wages, no overflow — and W is free to inflate (the regime the cap was introduced to tame).
    res = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN, **DISP,
                                               survivor_raise_ceiling=float("inf"))).run()
    assert np.allclose(res["survivor_mech_inflow_B"].to_numpy(), res["survivor_gains_B"].to_numpy(),
                       rtol=1e-12, atol=0)
    assert np.allclose((res["survivor_overflow_profit_B"] + res["survivor_overflow_price_B"]).to_numpy(),
                       0.0, atol=1e-12)
    assert res["W_survivor"].max() > 1.5                       # unbounded → inflates past any cap


def test_sticky_rate_semantics_in_binding_cap(data, deltas):
    # DOCUMENTS the chosen semantics (see the known-limitation note in dynamics_v2 step 5): once the cap
    # binds, this period's routed wage inflow goes to 0 (all survivor_gains overflow to profit/price) yet
    # the survivor tax stays positive — it is levied on the STANDING accumulated wage level W_mech, pinned
    # at the ceiling. A maintainer who "fixes" this into a per-period-funded tax base trips this test.
    res = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN, **DISP,
                                               survivor_raise_ceiling=1.5)).run()
    tail = res[np.isclose(res["survivor_mech_inflow_B"], 0.0) & (res["period"] > 0)]
    assert len(tail) > 0                                        # the cap binds (no new inflow) in the tail
    assert np.allclose(tail["W_survivor_mech"].to_numpy(), 1.5)   # W stays pinned at the ceiling
    assert (tail["survivor_gain_fed_B"] > 0).all()             # yet the standing raise is still taxed


def test_spillover_split_routes_overflow(data, deltas):
    # when the cap binds, survivor_spillover_to_profit shifts the overflow between corporate recovery
    # (federal, lowers the deficit) and price deflation (no nominal-fed effect) — the fed/state lever.
    common = dict(**SCEN, **DISP, survivor_raise_ceiling=1.1)   # low ceiling → large overflow
    to_profit = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **common,
                                                     survivor_spillover_to_profit=1.0)).run()
    to_price = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **common,
                                                    survivor_spillover_to_profit=0.0)).run()
    assert (to_profit["survivor_overflow_corp_tax_B"] > 0).any()
    assert np.allclose(to_price["survivor_overflow_corp_tax_B"].to_numpy(), 0.0)
    assert to_profit["fed_deficit_B"].iloc[-1] < to_price["fed_deficit_B"].iloc[-1]


def test_c5_market_is_exempt_from_conservation(data, deltas):
    # ΔW_market (unconserved) must NOT enter the C5c partition: with gains_share=0 the partition is all
    # zero, yet the market wage effect still moves the survivor tax (ceiling raised so it isn't truncated).
    res = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN,
                                               survivor_elasticity=-0.2, survivor_raise_ceiling=1.5)).run()
    assert np.allclose(res["survivor_mech_inflow_B"].to_numpy(), 0.0)
    assert np.allclose(res["survivor_gains_B"].to_numpy(), 0.0)
    assert (res["survivor_market_frac"] != 0).any()             # market effect is live
    assert (res["survivor_gain_fed_B"] != 0).any()              # and it moves the survivor tax


# ----------------------------------------------------------------- C6 (federal reconciliation)
def test_c6_federal_reconciles_no_residual(data, deltas):
    # ceiling=1.2 so the overflow→corp-tax recovery is live and must appear in the reconciliation.
    res = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN, **DISP,
                                               survivor_elasticity=-0.1, auto_cost=0.1,
                                               offshore_share=0.25, survivor_raise_ceiling=1.2)).run()
    recon = (res["inc_fed_loss_B"] + res["payroll_fed_loss_B"] + res["transfer_fed_B"]
             + res["ui_outlay_fed_B"] - res["ui_tax_fed_B"] - res["corp_offset_B"]
             - res["survivor_gain_fed_B"] - res["compute_pool_tax_B"]
             - res["survivor_overflow_corp_tax_B"] + res["survivor_netting_B"]  # Phase-5 netting term
             + res["ubi_outlay_B"] - res["ubi_recapture_B"] - res["automation_tax_B"])
    assert np.allclose(recon.to_numpy(), res["fed_deficit_B"].to_numpy(), rtol=0, atol=1e-9)


# ----------------------------------------------------------------- C-headcount (G)
def test_c_headcount_partition_prices_in_motion_cohort_once(data, deltas):
    # survivors + new-displaced + carried-displaced + reabsorbed + exited == baseline, every period;
    # survivors (employed_M) exclude the in-motion on-UI cohort, so it is never both survivor and displaced.
    v2p = replace(DEFAULTS_V1REDUCTION, **SCEN, **DISP, reabsorption_rate=0.3, lfp_exit_rate=0.05)
    res = DynamicModelV2(data, deltas, v2p).run()
    buckets = (res["employed_M"] + res["on_ui_M"] + res["exhausted_M"]
               + res["reabsorbed_M"] + res["exited_M"])
    baseline_M = deltas["employed"].sum() / 1e6
    assert np.allclose(buckets.to_numpy(), baseline_M, atol=1e-6)
    # the survivor base (employed_M) shrinks as displacement proceeds (rides the post-transition stock)
    assert res["employed_M"].is_monotonic_decreasing
    # at a period with fresh displacement, survivors are strictly fewer than survivors+new-displaced
    assert (res["on_ui_M"] > 0).any()


# ----------------------------------------------------------------- sign-flip
def test_sign_flip_on_elasticity(data, deltas):
    def gain(el):
        # ceiling 1.5 so the positive (complementarity) market raise isn't truncated at baseline
        return DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN, survivor_elasticity=el,
                                                    survivor_raise_ceiling=1.5)).run()["survivor_gain_fed_B"]
    pos, neg = gain(+0.2), gain(-0.2)
    t = 5                                                        # a period with slack_prev > 0
    assert pos.iloc[t] > 0 and neg.iloc[t] < 0                  # complementarity gains, substitution loses
    # mechanical-only (no market, cap high enough to absorb) is a pure revenue gain
    mech = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN, **DISP,
                                                survivor_raise_ceiling=1.5)).run()
    assert (mech["survivor_gain_fed_B"] > 0).all()


# ----------------------------------------------------------------- J.1 order-independence
def test_j1_market_keys_off_lagged_slack(data, deltas):
    res = DynamicModelV2(data, deltas,
                         replace(DEFAULTS_V1REDUCTION, **SCEN, survivor_elasticity=-0.2)).run()
    # zero at t=0 (no prior slack); thereafter slack_prev is exactly the PRIOR period's cumulative drop
    assert res["survivor_market_frac"].iloc[0] == 0.0 and res["survivor_slack_prev"].iloc[0] == 0.0
    prior_drop = (res["employment_drop_pct"] / 100.0).shift(1).fillna(0.0)
    assert np.allclose(res["survivor_slack_prev"].to_numpy(), prior_drop.to_numpy(), atol=1e-12)


# ----------------------------------------------------------------- reabsorbed-cross-threshold (Rung 1)
def test_rung1_engine_fires_means_tested_outlays(data, rung1_ready):
    # at the engine level: a low-wage cell re-employed at the service floor trips transfers (gained
    # outlays > 0) — the channel Rung 0's flat haircut (tax-only) silently keeps at zero.
    from fiscal_model.integrate import CellIntegrator
    from fiscal_model.transfers import TransferLookup
    from fiscal_model.kernel import KernelParams
    floors, nat = reabsorption.service_floor_by_state(data, 0.30)
    ci = CellIntegrator(data, TransferLookup(), KernelParams())
    # a low-wage service occupation in an expansion state (Medicaid/SNAP/EITC live)
    fd = ci.integrate_reemployment("35-3023", "California", floors.get("California", nat))
    assert (fd.gained_outlays_fed + fd.gained_outlays_state) > 0


def test_rung1_vs_rung0_transfers_higher(data, deltas, rung1_ready):
    # run level: Rung 1 routes reabsorbed through the full service-floor delta (incl. transfers), so its
    # transfers exceed Rung 0's tax-only haircut for the same scenario, driven by the reabsorbed stock.
    common = dict(**SCEN, reabsorption_rate=0.4)
    r0 = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, reabsorption_rung=0, **common)).run()
    r1 = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, reabsorption_rung=1, **common)).run()
    assert (r1["reabsorbed_M"] > 0).any()
    assert r1["transfers_added_B"].iloc[-1] > r0["transfers_added_B"].iloc[-1]


def test_shipped_default_runs_end_to_end(data, deltas, rung1_ready):
    # DEFAULTS_SHIPPED has reabsorption_rung=1 + survivor levers on — it must run (no NotImplementedError)
    res = DynamicModelV2(data, deltas, replace(DEFAULTS_SHIPPED, **SCEN)).run()
    assert len(res) == 10 and np.isfinite(res["fed_deficit_B"]).all()


# ----------------------------------------------------------------- XOR guard still holds with rung 1
def test_corp_xor_guard_unaffected(data, deltas):
    with pytest.raises(AssertionError):
        DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, corp_offset_scale=0.5))
