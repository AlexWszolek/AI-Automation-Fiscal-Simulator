"""The full conservation battery over one DynamicModelV2 run — extracted from the Phase-6 regression
suite so the Monte Carlo runner can spot-check draws with the SAME identities the tests gate on
(C1/C-headcount incl. per-cell, C2/C-gate/C5b, C5c funded partition, C3, C4 + macro positivity,
C6 federal + C6-state composition, C7 close, the absolute-ledger anchor).

`tests/test_v2_phase6.py` imports these back — one source of truth for the identity algebra.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import government


def _rel(a, b, rtol=1e-9, atol=1e-6):
    return np.allclose(np.asarray(a, float), np.asarray(b, float), rtol=rtol, atol=atol)


def assert_all_invariants(res: pd.DataFrame, v2p, baseline_M: float):
    """The full conservation battery on one run. Each identity is read off the output columns."""
    # C1 / C-headcount: the seven worker states partition the baseline population, every period —
    # at the AGGREGATE and PER-CELL (a per-cell leak that nets to zero in aggregate would slip past).
    buckets = (res["employed_M"] + res["on_ui_M"] + res["exhausted_M"] + res["reabsorbed_M"]
               + res["exited_M"] + res["induced_M"] + res["retired_M"])
    assert _rel(buckets, res["population_M"]) and _rel(res["population_M"], baseline_M), "C1/C-headcount"
    assert (res["max_cell_resid_M"] < 1e-6).all(), "C1 per-cell"

    # C2: disposition meter + partition over net_saving.
    assert _rel(res["automation_spend_B"] + res["net_saving_B"], res["saved_bill_B"]), "C2 meter"
    assert _rel(res["retained_profit_B"] + res["price_reduction_B"] + res["survivor_gains_B"],
                res["net_saving_B"]), "C2 partition"
    # C-gate: net_saving never negative.
    assert (res["net_saving_B"] >= -1e-9).all(), "C-gate"
    # C5b: the four destinations partition the saved bill.
    assert _rel(res["automation_spend_B"] + res["retained_profit_B"] + res["price_reduction_B"]
                + res["survivor_gains_B"], res["saved_bill_B"]), "C5b"
    # C5c: the funded survivor routing conserves survivor_gains.
    assert _rel(res["survivor_wage_cost_B"] + res["survivor_overflow_profit_B"]
                + res["survivor_overflow_price_B"], res["survivor_gains_B"]), "C5c"

    # C3: compute pool — tax = (inflow − offshore leak) × effective rate.
    domestic = res["automation_spend_B"] - res["offshore_leak_B"]
    assert _rel(res["compute_pool_tax_B"], domestic * v2p.compute_effective_rate), "C3"

    # C4: real = nominal / price level (deficit AND debt) — the A2 price double-application trap. The
    # price level itself must stay positive (a negative P would sign-flip every real/%GDP column while
    # the ratio identity stayed a passing tautology).
    assert (res["price_level"] > 0).all() and (res["productivity_index"] > 0).all(), "macro positivity"
    assert _rel(res["fed_deficit_real_B"], res["fed_deficit_B"] / res["price_level"]), "C4 deficit"
    assert _rel(res["fed_debt_real_B"], res["fed_debt_B"] / res["price_level"]), "C4 debt"

    # C6: federal reconciliation — net_fed is exactly the sum of its labeled components.
    recon = (res["inc_fed_loss_B"] + res["payroll_fed_loss_B"] + res["transfer_fed_B"]
             + res["ui_outlay_fed_B"] - res["ui_tax_fed_B"] - res["corp_offset_B"]
             - res["survivor_gain_fed_B"] - res["compute_pool_tax_B"]
             - res["survivor_overflow_corp_tax_B"]
             + res["ubi_outlay_B"] - res["ubi_recapture_B"] - res["automation_tax_B"]
             + res["ssdi_outlay_B"]
             - res["income_surcharge_fed_B"] - res["corp_surcharge_fed_B"]   # baseline tax-regime
             - res["excise_surcharge_fed_B"])                                # surcharges (revenue)
    assert _rel(recon, res["fed_deficit_B"]), "C6 federal reconciliation"

    # C6-state: the signed per-state total reconstructs from its labeled components (pins sd_state's sign
    # and the bincount — a state-side sign error would otherwise flow silently into the gap).
    state_recon = (res["inc_state_loss_B"] + res["cons_state_loss_B"] + res["transfer_state_B"]
                   - res["survivor_gain_state_B"]
                   - res["income_surcharge_state_B"] - res["corp_surcharge_state_B"]
                   - res["cons_surcharge_state_B"])
    assert _rel(state_recon, res["state_net_total_B"]), "C6-state composition"
    # C7: the close is exact — recovered + spending_cut covers the gap, residual ~0, every state balances.
    assert (res["state_rate_hike_B"] + res["state_spending_cut_B"]
            >= res["state_gap_B"] - 1e-6).all(), "C7 gap covered"
    assert (res["state_close_residual_B"] <= 1e-9 * res["state_gap_B"].clip(lower=1.0)).all(), "C7 residual"
    assert res["state_balanced"].all(), "C7 balanced flag"

    # absolute ledger: the absolute federal deficit is exactly the baseline anchor + the modeled delta.
    assert _rel(res["fed_deficit_abs_B"] - res["fed_deficit_B"], government.BASELINE_FED_DEFICIT_BUSD), \
        "absolute ledger anchor"
