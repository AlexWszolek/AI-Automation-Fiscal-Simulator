"""Phase 2 — the sector disposition router (plan module `firms/disposition.py`).

Routes each automated job's saved fully-loaded COMPENSATION. Automation cost nets FIRST (note C):

    automation_spend = auto_cost × saved_bill            → compute pool
    net_saving       = saved_bill − automation_spend     (≥ 0 by construction — the C-gate / F)
    net_saving split (shares sum to 1, C2) → { retained_profit → corporate tax,
                                               price_reduction → ΔP (Phase 3),
                                               survivor_gains  → ΔW_mechanical (Phase 4) }

Corporate XOR (note C): corporate tax is computed ONCE here, on `retained_profit`. The per-worker
corporate offset is LINEAR in the surplus base, so the offset = base_offset · (retained_profit / comp)
= base_offset · retained_profit_share · (1 − auto_cost). At the reduction defaults
(retained_profit_share = 1, auto_cost = 0) it equals v1's full-comp offset **exactly** — the C8
anchor. v1's `surplus_capture` path is superseded; it survives only as the alias
(1 − auto_cost)·retained_profit_share.

Phase 2 uses GLOBAL disposition shares (per-sector shares are an advanced lever). At global shares the
sector aggregation equals the economy total, so the router works on aggregates here; the corporate
offset is kept as a per-cell array so the federal loop subtracts it exactly as v1 did.

NOTE — cost-of-automation GATE deferred: only the METER (`automation_spend = auto_cost × saved_bill`) is
implemented. The GATE (note C: `auto_cost` modulating the displacement *fraction* by wage, making
high-wage-first endogenous) is a deferred diffusion refinement — `auto_cost` does not yet affect
displacement counts, only the split of the saved bill.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class DispositionResult:
    saved_bill: float            # annual saved fully-loaded compensation of the automated stock
    automation_spend: float      # → compute pool (the meter)
    net_saving: float            # saved_bill − automation_spend (≥ 0)
    retained_profit: float       # → corporate tax (taxed via corporate_offset_cell)
    price_reduction: float       # → ΔP (consumed in Phase 3)
    survivor_gains: float        # → ΔW_mechanical (consumed in Phase 4)
    corporate_offset_cell: np.ndarray  # per-cell federal corporate recovery on retained_profit


def route(automated_stock: np.ndarray, comp_per_worker: np.ndarray,
          base_corp_offset_pw: np.ndarray, v2p) -> DispositionResult:
    """Disposition of one period's saved bill (the automated STOCK × comp), per the V2 levers.

    `automated_stock`, `comp_per_worker`, `base_corp_offset_pw` are per-cell arrays; `base_corp_offset_pw`
    is v1's full-comp corporate offset per worker (surplus_capture=1 base).
    """
    saved_bill = float((automated_stock * comp_per_worker).sum())
    automation_spend = v2p.auto_cost * saved_bill
    net_saving = saved_bill - automation_spend
    retained_profit = v2p.retained_profit_share * net_saving
    price_reduction = v2p.price_reduction_share * net_saving
    survivor_gains = v2p.survivor_gains_share * net_saving

    disp_factor = v2p.retained_profit_share * (1.0 - v2p.auto_cost)   # = 1 at reduction
    corporate_offset_cell = automated_stock * base_corp_offset_pw * disp_factor
    return DispositionResult(saved_bill, automation_spend, net_saving, retained_profit,
                             price_reduction, survivor_gains, corporate_offset_cell)


def shares_sum(v2p) -> float:
    """The disposition partition over net_saving (C2): must equal 1."""
    return v2p.retained_profit_share + v2p.price_reduction_share + v2p.survivor_gains_share
