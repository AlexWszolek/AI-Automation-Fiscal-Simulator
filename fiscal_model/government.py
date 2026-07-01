"""Phase 5 — government closure (decision H, gates C6-state / C7) + the absolute revenue ledger.

Two pieces:

1. `RevenueLedger` — anchors the model's per-period DELTAS to the real 2024 base-linkage absolutes
   (`receipts`), so the headline rides a real base instead of the synthetic VA one. Federal: absolute
   revenue = R_fed0 + Δrevenue and absolute deficit = baseline_fed_deficit + net_fed. State-local:
   absolute revenue = R_state0 − loss + close-recovery (states balance, so there is no standing state
   deficit). The federal OUTLAY baseline is not in the receipts file, so `BASELINE_FED_DEFICIT_BUSD` is a
   documented CBO FY2024 anchor (≈ $1.83T) rather than derived.

2. `close_state_gaps` — the balanced-budget close (the asymmetric-amplifier thesis). Each state must
   erase its net loss within-year; the federal government need not. A state closes by raising rates
   (recover revenue from the remaining labour-income base) and/or cutting spending. CRITICAL (design
   review): a rate hike is bounded — a gap needing more than `state_rate_hike_cap × base` is INFEASIBLE
   and the unclosable remainder is forced into a spending cut, with a `capped` flag surfaced (else the
   model silently encodes impossible >100% tax rates and reports them 'balanced'). Both rate hikes and
   spending cuts are contractionary by ≈ the gap — that austerity is the impulse fed to the lagged-demand
   channel (decision I). Reported `state_gap_B` stays the PRE-close magnitude (= v1), so the close is
   inert for the C8 anchor; its only feedback is the contraction, gated by `demand_multiplier`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import loaders

# CBO FY2024 federal unified deficit (~$1.83T). Documented anchor: the receipts file carries revenue but
# not total outlays, so the absolute federal deficit level rides this constant + the modeled net_fed delta.
BASELINE_FED_DEFICIT_BUSD = 1833.0

# Marginal propensity to consume out of a government spending cut (≈1: purchases are demand 1:1), vs the
# household MPC (v2p.mpc, ≈0.95) out of a rate-hike-driven disposable-income cut. Drives the close-mode
# demand asymmetry (fix 6a).
MPC_GOV = 1.0


class RevenueLedger:
    """Absolute baseline revenue from `receipts`, and the per-period absolute fed/state figures."""

    def __init__(self, data: loaders.FiscalData):
        r = data.receipts
        self.fed_revenue0 = float(r.loc[r["level"] == "Federal", "amount_busd"].sum())          # ≈ 4982.8
        self.state_revenue0 = float(r.loc[r["level"] == "State & local", "amount_busd"].sum())   # ≈ 3514.9
        self.fed_deficit0 = BASELINE_FED_DEFICIT_BUSD

    def federal(self, net_fed_busd: float, fed_revenue_delta_busd: float, ngdp_usd: float) -> dict:
        """net_fed_busd = the modeled deficit INCREASE ($B); fed_revenue_delta_busd = the revenue-side
        change ($B, negative = revenue lost). Returns absolute revenue, deficit, and deficit/GDP."""
        deficit = self.fed_deficit0 + net_fed_busd
        return {"fed_revenue_B": self.fed_revenue0 + fed_revenue_delta_busd,
                "fed_deficit_abs_B": deficit,
                "fed_deficit_abs_pct_gdp": 100.0 * (deficit * 1e9) / ngdp_usd if ngdp_usd > 0 else 0.0}

    def state(self, state_loss_busd: float, close_recovery_busd: float) -> dict:
        """Post-close state-local net fiscal POSITION (deliberately NOT 'revenue'): baseline revenue minus
        the net loss the close absorbed — which nets in added transfer OUTLAYS, not only lost revenue —
        plus the rate-hike recovery. Named a 'position' precisely because the gap mixes a spending term."""
        return {"state_fiscal_position_B": self.state_revenue0 - state_loss_busd + close_recovery_busd}


@dataclass
class StateCloseResult:
    recovered: np.ndarray          # per-state revenue raised via rate hikes ($)
    spending_cut: np.ndarray       # per-state spending cut ($) — incl. the infeasible rate-hike spillover
    capped: np.ndarray             # per-state bool: the rate hike hit its feasibility cap
    residual: np.ndarray           # per-state |gap − (recovered + spending_cut)| — must be ~0 (C7)
    gap: np.ndarray                # per-state pre-close net loss closed (max(0, state_net))
    contraction: float             # total austerity ($) = Σ gap — the impulse fed to lagged demand (I)


def close_state_gaps(state_net: np.ndarray, taxable_base: np.ndarray, v2p) -> StateCloseResult:
    """Close each state's gap = max(0, state_net) within-year (C7), per the `state_response` mode.

    `taxable_base[s]` = the remaining labour-income base a rate hike is levied on. raise_rates recovers
    min(target, cap·base); the unclosable remainder spills to a forced spending cut (the infeasibility
    fallback). recovered + spending_cut == gap exactly → C7 residual ≈ 0. Vectorized over the 51 states.
    """
    gap = np.maximum(state_net, 0.0)
    if v2p.state_response == "raise_rates":
        cut_share = 0.0
    elif v2p.state_response == "cut_spending":
        cut_share = 1.0
    else:                                     # 'mix'
        cut_share = float(v2p.state_cut_share)

    planned_cut = gap * cut_share
    rate_target = gap - planned_cut                          # what the state tries to recover via rates
    rate_max = v2p.state_rate_hike_cap * np.maximum(taxable_base, 0.0)
    recovered = np.minimum(rate_target, rate_max)
    spilled = rate_target - recovered                        # infeasible rate hike → forced spending cut
    spending_cut = planned_cut + spilled
    capped = spilled > 0
    residual = np.abs(gap - (recovered + spending_cut))
    # Mode-dependent contraction (the fix that makes the rate cap bite): a spending cut removes government
    # demand ~1:1 (MPC_gov≈1), a rate hike removes household disposable income × the household MPC. So a
    # lower rate cap → more forced spending cuts → a LARGER contraction → deeper lagged-demand feedback.
    contraction = float((spending_cut * MPC_GOV + recovered * v2p.mpc).sum())
    return StateCloseResult(recovered=recovered, spending_cut=spending_cut, capped=capped,
                            residual=residual, gap=gap, contraction=contraction)
