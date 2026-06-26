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
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class WorkerStocks:
    employed: np.ndarray
    on_ui: np.ndarray
    exhausted: np.ndarray
    reabsorbed: np.ndarray
    exited: np.ndarray

    @classmethod
    def initial(cls, employed0: np.ndarray) -> "WorkerStocks":
        z = np.zeros_like(employed0, dtype=float)
        return cls(employed0.astype(float).copy(), z.copy(), z.copy(), z.copy(), z.copy())

    def total(self) -> np.ndarray:
        return self.employed + self.on_ui + self.exhausted + self.reabsorbed + self.exited

    # -- step 1-2 (mid-period): displace `frac` of employed into the fresh on-UI cohort --
    def displace(self, frac: np.ndarray) -> np.ndarray:
        new = frac * self.employed
        self.employed = self.employed - new
        self.on_ui = new                       # on_ui was emptied by the prior period-end aging
        return new

    # -- period end: age on-UI into exhausted, then split the exhausted pool --
    def age_and_transition(self, reabsorption_rate: float, lfp_exit_rate: float) -> None:
        assert reabsorption_rate + lfp_exit_rate <= 1.0 + 1e-9, "reabsorption + exit must be ≤ 1"
        pool = self.exhausted + self.on_ui     # == v1's `U + new`
        self.on_ui = np.zeros_like(self.on_ui)
        exit_flow = pool * lfp_exit_rate
        reab_flow = pool * reabsorption_rate
        self.exited = self.exited + exit_flow
        self.reabsorbed = self.reabsorbed + reab_flow
        self.exhausted = pool - exit_flow - reab_flow


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
