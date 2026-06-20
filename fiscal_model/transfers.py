"""Transfer channel — reads the PolicyEngine-baked static lookup and provides the
marginal transfer delta for the kernel's seam (`Kernel.set_transfer_lookup`).

The bake (scripts/bake_benefits.py, run offline in .venv) produces
`data/interim/benefit_lookup.parquet`: net means-tested benefits as a function of
household income, keyed by (state, filing, n_children). This module interpolates that
function and differences it across residual-income phases — never importing PolicyEngine.

Marginal object (per worker): transfers(without the worker's earnings) − transfers(with).
The kernel passes `residual_income` (UI during the window, 0 after exhaustion); we evaluate
net benefits at income_before = household_income and income_after = (household_income −
worker_wage) + residual_income, difference per program, and split fed/state by funding share.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pandas as pd

INTERIM = Path(__file__).resolve().parent.parent / "data" / "interim"

PROGRAMS = ["eitc", "ctc_refundable", "snap", "medicaid_value", "aca_ptc", "tanf", "ssi"]

# Federal funding share per program (v1). Medicaid 65/35 per briefing §3.4 (FMAP);
# SNAP/EITC/CTC/ACA federal; TANF block-grant ~50/50; SSI federal + small state supplement.
DEFAULT_FED_SHARE = {
    "eitc": 1.0, "ctc_refundable": 1.0, "snap": 1.0, "medicaid_value": 0.65,
    "aca_ptc": 1.0, "tanf": 0.5, "ssi": 0.95,
}

_FILINGS = ("Single", "Head of household", "Married filing jointly")


def _load(path_parquet: Path, path_csv: Path) -> pd.DataFrame:
    if path_parquet.exists():
        try:
            return pd.read_parquet(path_parquet)
        except Exception:
            pass
    if path_csv.exists():
        return pd.read_csv(path_csv)
    raise FileNotFoundError(
        f"benefit lookup not found ({path_parquet.name}/{path_csv.name}); "
        f"run `.venv/bin/python scripts/bake_benefits.py` first")


class TransferLookup:
    """Interpolable net-benefit function from the baked grid."""

    def __init__(self, interim_dir: Path = INTERIM, fed_share: Optional[dict] = None):
        self.fed_share = dict(fed_share or DEFAULT_FED_SHARE)
        lk = _load(interim_dir / "benefit_lookup.parquet", interim_dir / "benefit_lookup.csv")
        # Per (state, filing, n_children): sorted income axis + per-program arrays.
        self._grid: dict = {}
        for (state, filing, nc), g in lk.groupby(["state", "filing", "n_children"]):
            g = g.sort_values("household_income")
            self._grid[(state, filing, int(nc))] = (
                g["household_income"].to_numpy(dtype=float),
                {p: g[p].to_numpy(dtype=float) for p in PROGRAMS if p in g.columns},
            )
        try:
            ui = _load(interim_dir / "ui_params.parquet", interim_dir / "ui_params.csv")
            self._ui = ui.set_index("state")
        except FileNotFoundError:
            self._ui = None

    def _resolve_children(self, state, filing, n_children) -> int:
        nc = min(max(int(n_children), 0), 3)
        # 'Single' is baked only at 0 children (nonfamily households have no own children).
        if (state, filing, nc) in self._grid:
            return nc
        for fallback in (nc, 0):
            if (state, filing, fallback) in self._grid:
                return fallback
        raise KeyError(f"no baked benefits for {(state, filing, n_children)}")

    def net_benefits_by_program(self, state: str, filing: str, n_children: int,
                                income: float) -> dict:
        nc = self._resolve_children(state, filing, n_children)
        xs, progs = self._grid[(state, filing, nc)]
        # np.interp does flat extrapolation beyond the grid ends (benefits ~0 above the top).
        return {p: float(np.interp(income, xs, ys)) for p, ys in progs.items()}

    def program_arrays(self, state: str, filing: str, n_children: int):
        """Raw (income_axis, {program: values}) for vectorized interpolation (Part C)."""
        nc = self._resolve_children(state, filing, n_children)
        return self._grid[(state, filing, nc)]

    def ui_benefit(self, wage: float, state: str) -> float:
        """Annual UI benefit ≈ replacement_rate × prior wage, capped (v1 params)."""
        if self._ui is None or state not in self._ui.index:
            rep, cap = 0.45, 20_000.0
        else:
            row = self._ui.loc[state]
            rep, cap = float(row["replacement_rate"]), float(row["annual_cap_usd"])
        return min(rep * max(0.0, wage), cap)

    def marginal_transfer(self, state: str, filing: str, n_children: int,
                          income_before: float, income_after: float) -> dict:
        """transfers(income_after) − transfers(income_before), split fed/state.
        Positive = added outlay (benefits rise as income falls)."""
        nb0 = self.net_benefits_by_program(state, filing, n_children, income_before)
        nb1 = self.net_benefits_by_program(state, filing, n_children, income_after)
        fed = state_amt = 0.0
        by_program = {}
        for p in nb0:
            d = nb1[p] - nb0[p]
            by_program[p] = d
            fs = self.fed_share.get(p, 1.0)
            fed += d * fs
            state_amt += d * (1.0 - fs)
        return {"fed": fed, "state": state_amt, "by_program": by_program}


def make_transfer_fn(lookup: TransferLookup) -> Callable:
    """Build the kernel-seam function fn(worker, residual_income) -> {'fed','state'}.

    residual_income = the worker's remaining income post-displacement (UI benefit during
    the window, 0 after exhaustion). The dynamics choose which phase; on-UI callers pass
    `lookup.ui_benefit(worker.worker_wage, worker.state)`."""
    def fn(worker, residual_income: float = 0.0) -> dict:
        income_before = worker.household_income
        income_after = max(0.0, worker.household_income - worker.worker_wage) + residual_income
        d = lookup.marginal_transfer(worker.state, worker.filing, worker.n_children,
                                     income_before, income_after)
        return {"fed": d["fed"], "state": d["state"]}
    return fn
