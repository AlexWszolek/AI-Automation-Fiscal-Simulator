"""Phase 4 — the survivor channel (plan decision A).

The still-employed majority is the term the plan flags as *likely the largest* — and the one that can
flip the headline's sign. When a sector's survivor wage index W moves (firms passing automation savings
to remaining workers, and/or labour-market slack pushing wages), the income + payroll tax on those wages
moves with it. `SurvivorEngine.delta(W_cell)` returns the **per-worker** income-tax (fed/state) and
payroll increment for a per-cell wage multiplier, as a GAIN (positive) when W > 1.

Decision A — application & grain:
- W scales the **worker wage only**: household income = hh_baseline + wage·(W−1); payroll on wage·W
  (capped, filing-dependent Additional-Medicare threshold). Household income is NOT scaled by W (that
  would inflate the base by spouse earnings).
- **Exact bracket math, not a linearization**: the increment is the actual bracket function differenced
  at two real income points (T(hh+Δw) − T(hh)), never a marginal-rate × Δw approximation.
- Evaluated at the per-filing household **MEAN**. The within-cell income-distribution integration (the
  lognormal nodes the displacement delta uses) is a documented deferral here: g(h) = T(h+Δw) − T(h) is
  piecewise-CONSTANT in h with jumps at bracket edges, so the at-mean Jensen gap is bounded (~≤4% only
  when the cell mean straddles a bracket boundary) and second-order versus the transfer cliffs the
  distribution was built for — and the survivor increment carries no transfer interp, so it stays cheap.
  The exact distribution integration is a near-free future refinement (reuse the integrator's nodes).
- **Scope = income + payroll** (the channels rates.py owns). Survivor consumption (more spending) and
  transfer effects (survivors sit above means-tested thresholds) are deferred, per decision A.

At W = 1 every bracket and FICA difference is identically zero → the channel contributes nothing at
`DEFAULTS_V1REDUCTION` (the C8 anchor).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import loaders
from .rates import build_engines

# (filing label, filing-share column, household-mean column) — order fixes the W/M column layout.
_FILINGS = [("Married filing jointly", "p_mfj", "inc_married_usd"),
            ("Head of household", "p_hoh", "inc_hoh_usd"),
            ("Single", "p_single", "inc_single_usd")]


class SurvivorEngine:
    """Vectorized exact income+payroll re-eval of the surviving employed at a scaled wage."""

    def __init__(self, data: loaders.FiscalData, deltas: pd.DataFrame):
        self.income, self.fica = build_engines(data)
        d = deltas.reset_index(drop=True)[["soc_code", "state", "worker_wage"]].copy()
        self.worker_wage = d["worker_wage"].to_numpy(float)
        self.state = d["state"].to_numpy()
        n = len(d)

        hh = data.household[["soc_code", "state", "p_mfj", "p_hoh", "p_single",
                             "inc_married_usd", "inc_hoh_usd", "inc_single_usd"]]
        m = d.merge(hh, on=["soc_code", "state"], how="left")   # left join preserves delta-row order
        assert len(m) == n, "household merge changed row count — duplicate (soc,state)?"

        P = m[["p_mfj", "p_hoh", "p_single"]].to_numpy(float)
        allnan = np.isnan(P).all(axis=1)
        Psafe = np.where(np.isnan(P), 0.0, P)
        tot = Psafe.sum(axis=1)
        weights = Psafe / np.where(tot > 0, tot, 1.0)[:, None]
        weights[allnan] = 1.0 / 3.0                              # no household data → equal filing weights

        M = m[["inc_married_usd", "inc_hoh_usd", "inc_single_usd"]].to_numpy(float)
        M = np.where(np.isnan(M) | (M <= 0), self.worker_wage[:, None], M)   # fallback mean = wage

        self.weight = {f: weights[:, j] for j, (f, _, _) in enumerate(_FILINGS)}
        self.hh_mean = {f: M[:, j] for j, (f, _, _) in enumerate(_FILINGS)}
        self._states = sorted(set(self.state))
        self._state_mask = {s: (self.state == s) for s in self._states}

    def delta(self, W_cell) -> dict:
        """Per-WORKER income+payroll tax increment for a per-cell wage multiplier W_cell (GAINS +).
        Returns {'inc_fed', 'inc_state', 'payroll'} per-cell arrays. W_cell == 1 → all zeros."""
        W = np.asarray(W_cell, float)
        dw = self.worker_wage * (W - 1.0)                        # per-cell wage change ($)
        n = len(self.worker_wage)
        inc_fed = np.zeros(n); inc_state = np.zeros(n); payroll = np.zeros(n)
        for f, _, _ in _FILINGS:
            wt, mean = self.weight[f], self.hh_mean[f]
            # federal income tax increment (filing-only → one vectorized pair over all cells)
            ff = np.asarray(self.income.federal_tax(mean + dw, f), float) \
                - np.asarray(self.income.federal_tax(mean, f), float)
            inc_fed += wt * ff
            # payroll on the scaled wage (capped OASDI, filing-dependent Additional Medicare)
            pf = np.asarray(self.fica.fica(self.worker_wage * W, f), float) \
                - np.asarray(self.fica.fica(self.worker_wage, f), float)
            payroll += wt * pf
            # state income tax increment (state-dependent brackets → per-state vectorized)
            for s in self._states:
                mask = self._state_mask[s]
                si = np.asarray(self.income.state_tax(mean[mask] + dw[mask], s, f), float) \
                    - np.asarray(self.income.state_tax(mean[mask], s, f), float)
                inc_state[mask] += wt[mask] * si
        return {"inc_fed": inc_fed, "inc_state": inc_state, "payroll": payroll}


def funded_w_update(survivor_gains: float, W_mech_old: float, wage_bill: float,
                    comp_loading: float, ceiling: float) -> tuple:
    """The FUNDED W* update (coherence fix): the recurring `survivor_gains` flow must pay the standing
    raise's recurring cost (`maintenance`, in comp-$ — raises cost the firm fully-loaded compensation,
    `comp_loading` ≈ 1.4× wages) BEFORE any increment; only the surplus raises W further (converging
    W* = 1 + gains/(ℓ·wage_bill), still capped by the ceiling). If gains cannot fund the standing raise,
    W snaps DOWN to the fundable level instantly — the snap keeps the C5c identity exact in every branch:

        ℓ·wage_bill·(W_mech_new − 1)  +  overflow  ==  survivor_gains        (wage_cost + overflow)

    This replaces the old unfunded ratchet + `survivor_profit_netting` (which deducted corporate tax that
    was never booked — up to 81× the booked amount). The raise is now self-financing from the routed flow;
    it is taxed exactly once, as labour income (sd), never as phantom profit.

    Returns (W_mech_new, wage_cost, increment, overflow). Pure — unit-testable (the snap branch is a rare
    corner end-to-end: gains are monotone under the cumulative-automation base, so it fires mainly when a
    demand release rebounds the wage bill)."""
    if wage_bill <= 0:                                   # no survivors: nothing absorbable, all spills
        return W_mech_old, 0.0, 0.0, max(0.0, survivor_gains)
    lw = comp_loading * wage_bill
    maintenance = lw * (W_mech_old - 1.0)
    available = survivor_gains - maintenance
    if available >= 0.0:
        room = float("inf") if not np.isfinite(ceiling) else max(0.0, lw * (ceiling - W_mech_old))
        increment = min(available, room)
        overflow = available - increment
        W_new = W_mech_old + increment / lw
    else:                                                # unfundable → instant snap to the funded level
        W_new = 1.0 + max(0.0, survivor_gains) / lw
        increment, overflow = 0.0, 0.0
    wage_cost = lw * (W_new - 1.0)                       # = maintenance+increment (funded) | = gains (snap)
    return W_new, wage_cost, increment, overflow
