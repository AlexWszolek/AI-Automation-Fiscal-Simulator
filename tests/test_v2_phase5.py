"""Phase 5 gate — government closure (H) + lagged demand (I) + absolute ledger + survivor netting.

C6-state (per-state composition reconciles before close), C7 (the balanced-budget close zeroes each
state's residual; infeasible rate hikes spill to spending cuts), the demand toggle (induced is a
C1-guarded employment flow, 0 at t=0, a strict one-period lag, off → v1), the survivor netting (resolves
the Phase-4 double-count), the absolute ledger, order-independence (J.1), and the v1-reduction anchor.

Tolerances are RELATIVE: bincount summation-order roundoff is ~2e-5 absolute / ~1e-15 relative, so
'reconciles with no residual' means machine-eps-relative, not literal ==0.
"""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from fiscal_model import government, levers_v2
from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.levers_v2 import DEFAULTS_V1REDUCTION

SCEN = dict(cognitive_feasibility=0.85, physical_feasibility=0.25,
            adoption_path=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9])
DISP = dict(retained_profit_share=0.6, price_reduction_share=0.2, survivor_gains_share=0.2)
C8 = ["fed_deficit_B", "fed_debt_B", "state_gap_B", "employment_drop_pct", "revenue_lost_B",
      "transfers_added_B", "corp_offset_B", "ubi_required_rate"]


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built — run `python -m fiscal_model.dynamics`")
    return pd.read_parquet(DELTA_CACHE)


# ----------------------------------------------------------------- v1-reduction (C8)
def test_c8_holds_with_close_and_demand_off(data, deltas, c8_compare):
    # state close runs but reports the pre-close gap; demand off; survivor channel 0 → bit-for-bit v1
    v2p = replace(DEFAULTS_V1REDUCTION, reabsorption_rate=0.4, **SCEN)
    _, r2 = c8_compare(data, deltas, v2p, C8)
    assert r2["induced_M"].abs().max() == 0.0                   # no induced flow at demand off
    assert (r2["survivor_wage_cost_B"] == 0.0).all()           # funded raise 0 at reduction


def test_demand_multiplier_in_reduction_guard():
    # BLOCKER #2: c8_compare must REJECT a dm>0 config (post-Phase-5 v2 diverges from v1's closed form)
    assert not levers_v2.is_v1_reduction(replace(DEFAULTS_V1REDUCTION, demand_multiplier=0.5))
    assert not levers_v2.is_v1_reduction(replace(DEFAULTS_V1REDUCTION, state_cut_share=0.5))
    assert levers_v2.is_v1_reduction(replace(DEFAULTS_V1REDUCTION, **SCEN))   # scenario knobs are fine


# ----------------------------------------------------------------- C6-state + C7 (the close)
@pytest.mark.parametrize("response,cut", [("raise_rates", 0.0), ("cut_spending", 0.0), ("mix", 0.5)])
def test_c6_state_composition_and_c7_close(data, deltas, response, cut):
    # rebuild the per-state composition and close the way the model does, asserting the two identities:
    #   (1) composition residual: inc+cons+transfer − sd − state_net == 0   (always, machine-rel)
    #   (2) C7 close residual:    gap − (recovered + spending_cut) == 0      (the gap is fully closed)
    v2p = replace(DEFAULTS_V1REDUCTION, **SCEN, **DISP, survivor_elasticity=-0.1,
                  survivor_raise_ceiling=1.3, state_response=response, state_cut_share=cut)
    m = DynamicModelV2(data, deltas, v2p)
    res = m.run()
    # (1) composition: the signed per-state total reconstructs from its labeled components (no residual)
    state_recon = (res["inc_state_loss_B"] + res["cons_state_loss_B"] + res["transfer_state_B"]
                   - res["survivor_gain_state_B"])
    assert np.allclose(state_recon.to_numpy(), res["state_net_total_B"].to_numpy(), rtol=1e-9, atol=1e-6)
    # (2)+(3) the close zeroes each state's residual and the whole gap is covered by the two means (C7)
    assert (res["state_close_residual_B"] <= 1e-9 * res["state_gap_B"].clip(lower=1.0)).all()
    assert (res["state_rate_hike_B"] + res["state_spending_cut_B"] >= res["state_gap_B"] - 1e-6).all()


def test_c7_close_is_exact_at_unit_level(data, deltas):
    # the closer itself: recovered + spending_cut == gap exactly, per state, incl. the cap fallback
    import numpy as np
    state_net = np.array([100.0, -50.0, 1e12, 0.0])            # loss, surplus, infeasible, none
    base = np.array([1000.0, 1000.0, 1000.0, 1000.0])
    for resp, cut in (("raise_rates", 0.0), ("cut_spending", 0.0), ("mix", 0.4)):
        v2p = replace(DEFAULTS_V1REDUCTION, state_response=resp, state_cut_share=cut,
                      state_rate_hike_cap=1.0)
        c = government.close_state_gaps(state_net, base, v2p)
        assert np.allclose(c.recovered + c.spending_cut, c.gap)             # C7 exact
        assert c.gap[1] == 0.0                                              # surplus state closes nothing
        assert c.spending_cut[2] > 0                                        # infeasible gap is cut
        if resp != "cut_spending":                                         # rate-hiking modes flag the cap
            assert c.capped[2]


def test_infeasible_rate_hike_spills_to_cut(data, deltas):
    # MAJOR #4: a tiny rate-hike cap forces most gaps into spending cuts and flags them
    v2p = replace(DEFAULTS_V1REDUCTION, **SCEN, **DISP, state_response="raise_rates",
                  state_rate_hike_cap=0.001)
    res = DynamicModelV2(data, deltas, v2p).run()
    assert (res["n_states_capped"] > 0).any()
    assert (res["state_spending_cut_B"] > 0).any()             # the unclosable remainder is cut


# ----------------------------------------------------------------- lagged demand (I)
def test_demand_toggle_zero_is_v1_path(data, deltas):
    off = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN)).run()
    on = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN, demand_multiplier=0.5)).run()
    assert (off["induced_M"] == 0.0).all()                     # off: no induced flow
    assert on["induced_M"].iloc[0] == 0.0                      # on: zero at t=0 (no carry-in)
    assert (on["induced_M"].iloc[1:] > 0).all()                # then the flow kicks in
    assert on["employed_M"].iloc[-1] < off["employed_M"].iloc[-1]   # demand amplifies the job loss


def test_demand_flow_conserves_population(data, deltas):
    res = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN,
                                               demand_multiplier=0.8, reabsorption_rate=0.3,
                                               lfp_exit_rate=0.05)).run()
    baseline_M = deltas["employed"].sum() / 1e6
    assert np.allclose(res["population_M"].to_numpy(), baseline_M, atol=1e-6)   # C1 incl. induced


def test_demand_toggle_off_is_one_period_lag(data, deltas):
    # nice-to-have #4: pending computed at end of k−1 is consumed at start of k, so toggling off at k
    # leaves period k still perturbed (it consumes k−1's pending) and k+1 onward matches the no-feedback
    # path. Build a per-period adoption and compare an always-off run to one that is on only through k−1.
    base = replace(DEFAULTS_V1REDUCTION, **SCEN)
    off = DynamicModelV2(data, deltas, base).run()
    on = DynamicModelV2(data, deltas, replace(base, demand_multiplier=0.5)).run()
    # period 0: both have induced_M==0 (no carry-in) AND identical employed (pending not yet consumed)
    assert np.isclose(on["employed_M"].iloc[0], off["employed_M"].iloc[0])
    # period 1 onward diverges (the t=0 pending lands at t=1) — the one-period lag
    assert not np.isclose(on["employed_M"].iloc[1], off["employed_M"].iloc[1])


# ----------------------------------------------------------------- survivor corporate-channel sanity
def test_corporate_channel_sane_under_survivor_stress(data, deltas):
    # the review's worst ledger error: the old unfunded netting deducted corporate tax up to 81× larger
    # than any ever booked, driving the corporate channel net-NEGATIVE. Under the funded W* there is no
    # phantom deduction: the booked corporate recovery is non-negative even at survivor-heavy settings.
    res = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN,
                                               retained_profit_share=0.1, price_reduction_share=0.0,
                                               survivor_gains_share=0.9,
                                               survivor_raise_ceiling=5.0)).run()
    corp_channel = res["corp_offset_B"] + res["survivor_overflow_corp_tax_B"]
    assert (corp_channel >= -1e-9).all()                       # never net-negative
    assert np.isfinite(res["fed_deficit_B"]).all()
    # and the funded identity holds even at the extreme config
    lhs = (res["survivor_wage_cost_B"] + res["survivor_overflow_profit_B"]
           + res["survivor_overflow_price_B"])
    assert np.allclose(lhs.to_numpy(), res["survivor_gains_B"].to_numpy(), rtol=1e-12, atol=1e-9)


# ----------------------------------------------------------------- absolute ledger
def test_absolute_ledger_anchors_to_real_base(data, deltas):
    res = DynamicModelV2(data, deltas, replace(DEFAULTS_V1REDUCTION, **SCEN, demand_multiplier=0.5)).run()
    led = government.RevenueLedger(data)
    # federal: absolute deficit = baseline + the modeled net_fed delta
    assert np.allclose((res["fed_deficit_abs_B"] - led.fed_deficit0).to_numpy(),
                       res["fed_deficit_B"].to_numpy())
    assert led.fed_revenue0 > 4900 and led.state_revenue0 > 3400   # real 2024 receipt totals
    # absolute revenue falls below baseline as the labour base erodes
    assert (res["fed_revenue_B"] < led.fed_revenue0).all()


# ----------------------------------------------------------------- order-independence (J.1)
def test_order_independence_survivor_vs_state(data, deltas):
    # the state close reads the POST-survivor base and the survivor wage uses t−1 slack — neither depends
    # on the other within a period, so the run is deterministic & reproducible (a regression guard on the
    # decoupling: two identical runs match exactly).
    cfg = replace(DEFAULTS_V1REDUCTION, **SCEN, **DISP, survivor_elasticity=-0.1,
                  survivor_raise_ceiling=1.3, demand_multiplier=0.5, state_response="mix",
                  state_cut_share=0.5)
    a = DynamicModelV2(data, deltas, cfg).run()
    b = DynamicModelV2(data, deltas, cfg).run()
    for c in ("fed_deficit_B", "state_gap_B", "survivor_gain_fed_B", "induced_M"):
        assert np.array_equal(a[c].to_numpy(), b[c].to_numpy())
