"""Phase 1 — the 5-state worker population machine (plan module `workers.py`).

Per (occupation × state) cell, the workforce is a population vector across five states:
    employed → on-UI → exhausted → {reabsorbed, exited}
Owns population conservation (C1): the five states always sum to the cell's baseline.

Reduction to v1 (the C8 anchor): a freshly-displaced cohort is `on_ui` for its first period
(getting v1's `ui_share·during + (1−ui_share)·after` fiscal blend); at period end it **ages into
`exhausted` before** the exhausted pool splits, so the pool that reabsorbs/exits is exactly v1's
`U + new`. With `lfp_exit_rate = 0` the `exited` bucket stays empty and the dynamics are bit-for-bit
v1's {employed, U(=exhausted), R(=reabsorbed)} stock flow.

`exited` is absorbing (left the labor force / SSDI): like `exhausted` it carries the full "after"
fiscal loss, but it can never be reabsorbed — so `lfp_exit` permanently erodes the labor-tax base
(SSDI outlays are a later-phase refinement; for now exited == exhausted fiscally, minus the recovery
option).

`induced` (Phase 5, decision I) is the SIXTH state: workers laid off by the second-round DEMAND
contraction, not by automation. They carry the full "after" fiscal loss like `exhausted` (no first-period
UI blend — a documented simplification; the demand-side withdrawal basis nets taxes/transfers properly),
and are kept in their own bucket because a demand layoff produces no saved compensation to dispose —
`induced` is EXCLUDED from the automated base the disposition router prices. Coherence fix: induced now
JOIN the transition pool (reabsorption / lfp-exit / attrition apply as a parallel split), so
demand-displaced workers can find service jobs like automation-displaced ones.

`retired` (coherence fix) is the SEVENTH state and it is fiscally DELTA-NEUTRAL: baseline attrition
(retirement / mortality / discouragement) moves the long-term unemployed here, and their baseline twin
retired too — so they carry NO after-loss and NO demand withdrawal. This fixes the perpetual-work
counterfactual (losses used to accrue forever against a baseline that never retires). `exited` (SSDI via
lfp_exit) keeps the after-loss and gains an SSDI outlay in the dynamics; it does not itself retire
(a documented residual perpetuity).

At `demand_multiplier = attrition = lfp_exit = 0` the extra states stay empty → the v1 anchor.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def displacement_flow(g_cell: np.ndarray, adoption_t: float, emp0: np.ndarray,
                      auto_disp: np.ndarray, employed: np.ndarray) -> np.ndarray:
    """Cumulative diffusion ceiling (the accuracy fix): `adoption(t)` is the CUMULATIVE share of each
    cell's feasibly-automatable jobs automated BY year t, so the automated STOCK target =
    g_cell·adoption(t)·emp0 (on the BASELINE emp0 → a ceiling, not a per-period rate on the shrinking
    pool). The period's displacement is the increment above what's already automated (`auto_disp`),
    capped at the remaining `employed` (the induced/demand flow draws from the same pool). Monotone
    adoption ⇒ flow ≥ 0. Pure — the caller accumulates `auto_disp += flow`."""
    target = np.clip(g_cell * adoption_t, 0.0, 1.0) * emp0
    return np.clip(target - auto_disp, 0.0, employed)


@dataclass
class WorkerStocks:
    employed: np.ndarray
    on_ui: np.ndarray
    exhausted: np.ndarray
    reabsorbed: np.ndarray
    exited: np.ndarray
    induced: np.ndarray
    retired: np.ndarray

    @classmethod
    def initial(cls, employed0: np.ndarray) -> "WorkerStocks":
        z = np.zeros_like(employed0, dtype=float)
        return cls(employed0.astype(float).copy(), z.copy(), z.copy(), z.copy(), z.copy(),
                   z.copy(), z.copy())

    def total(self) -> np.ndarray:
        return (self.employed + self.on_ui + self.exhausted + self.reabsorbed
                + self.exited + self.induced + self.retired)

    # -- step 1-2 (mid-period): move the period's automation displacement `new` (absolute jobs, from
    #    `displacement_flow`) into the fresh on-UI cohort --
    def displace(self, new: np.ndarray) -> np.ndarray:
        self.employed = self.employed - new
        self.on_ui = new                       # on_ui was emptied by the prior period-end aging
        return new

    # -- decision I: the lagged demand contraction lands here as a per-cell employment movement.
    #    employed -> induced (C1-conserved); a separate bucket so these are NOT priced as automation. --
    def displace_extra(self, jobs: np.ndarray) -> np.ndarray:
        jobs = np.minimum(jobs, self.employed)   # cannot lay off more than remain employed
        self.employed = self.employed - jobs
        self.induced = self.induced + jobs
        return jobs

    # -- period end: age on-UI into exhausted, split the pool, then apply baseline attrition --
    def age_and_transition(self, reabsorption_rate: float, lfp_exit_rate: float,
                           attrition_rate: float = 0.0) -> None:
        assert reabsorption_rate + lfp_exit_rate <= 1.0 + 1e-9, "reabsorption + exit must be ≤ 1"
        assert 0.0 <= attrition_rate <= 1.0, "attrition_rate must be in [0, 1]"
        pool = self.exhausted + self.on_ui     # == v1's `U + new` (bit-identical anchor arithmetic)
        self.on_ui = np.zeros_like(self.on_ui)
        exit_flow = pool * lfp_exit_rate
        reab_flow = pool * reabsorption_rate
        self.exited = self.exited + exit_flow
        self.reabsorbed = self.reabsorbed + reab_flow
        self.exhausted = pool - exit_flow - reab_flow
        # induced (demand-displaced) join the SAME transitions as a parallel split (coherence fix —
        # a demand-displaced waiter can find a service job too). induced ≡ 0 at reduction → C8-safe.
        ind_exit = self.induced * lfp_exit_rate
        ind_reab = self.induced * reabsorption_rate
        self.exited = self.exited + ind_exit
        self.reabsorbed = self.reabsorbed + ind_reab
        self.induced = self.induced - ind_exit - ind_reab
        # baseline natural attrition (retirement / mortality) of the LONG-TERM unemployed into the
        # DELTA-NEUTRAL `retired` bucket (coherence fix): the baseline twin retired too, so retiring a
        # displaced worker cancels their standing fiscal loss — the perpetual-work counterfactual is gone.
        # C1-preserving (both buckets in total()); 0 at reduction.
        for bucket in ("exhausted", "induced"):
            flow = getattr(self, bucket) * attrition_rate
            self.retired = self.retired + flow
            setattr(self, bucket, getattr(self, bucket) - flow)


def reabsorbed_loss_factor(v2p) -> float:
    """Per-worker residual fiscal loss of a reabsorbed worker, as a fraction of the 'after' delta.

    Rung 0 (Phase-1 anchor): the worker re-emerges at w_d = (1−haircut)·w_o, recovering (1−haircut)
    of their tax contribution, so the residual loss ≈ `haircut × after-delta` — exactly v1's linear
    haircut. Rungs 1 (service floor) and 2 (cross-cell routing) recompute the *exact* tax at a
    destination wage decoupled from w_o; they land in Phase 4 (where they also gate the means-tested
    channel for reabsorbed households). Until then they raise rather than silently approximate.
    """
    if v2p.reabsorption_rung == 0:
        return v2p.reemployment_haircut
    raise NotImplementedError("reabsorption Rung 1/2 (service-floor / routed w_d) land in Phase 4")
