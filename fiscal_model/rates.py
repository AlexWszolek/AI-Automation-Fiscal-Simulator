"""Tax engine — federal + state income tax and federal payroll FICA.

Implements `T(income)` and `FICA(wage)` directly from the params in
`tax_side_schedule.xlsx` (the source of truth), so the kernel can evaluate tax at any
income and **difference it for an exact marginal delta**. The file also ships precomputed
"baked" schedules; `verify_against_baked()` proves this engine reproduces them.

Channels owned here (per docs/PROJECT_BRIEFING_v2.md): income tax (federal channel =
federal; state channel = state-and-local) and payroll FICA (federal). Transfers,
corporate, and consumption live elsewhere.

Conventions:
- Income tax `T(gross)` subtracts the filing's standard deduction, then applies brackets.
- State has only Single & MFJ brackets; **Head of household maps to Single** (matches the
  baked sheet); the 9 no-wage-tax states return 0.
- FICA combines employer + employee for OASDI (12.4%, capped) and Medicare (2.9%, uncapped),
  plus employee-only Additional Medicare (0.9% above the filing threshold).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import loaders


def _bracket_tax(taxable, floors: np.ndarray, rates: np.ndarray) -> np.ndarray:
    """Progressive-bracket tax on an array of taxable-income values."""
    t = np.asarray(taxable, dtype=float)
    uppers = np.append(floors[1:], np.inf)
    tax = np.zeros(t.shape, dtype=float)
    for lo, hi, r in zip(floors, uppers, rates):
        tax += r * np.clip(t, lo, hi)  # income within band [lo, hi]
        tax -= r * lo                  # ... minus the floor -> band width above lo
    # The two lines above compute sum_i r_i * (clip(t,lo,hi) - lo); clip>=lo so >=0.
    return tax


@dataclass
class _Schedule:
    floors: np.ndarray
    rates: np.ndarray
    std_deduction: float


class IncomeTax:
    """Federal + state income tax from bracket params."""

    def __init__(self, fed_brackets: pd.DataFrame, state_brackets: pd.DataFrame,
                 no_wage_tax: frozenset):
        self.no_wage_tax = frozenset(no_wage_tax)
        self._fed = {f: self._sched(g) for f, g in fed_brackets.groupby("filing")}
        self._state = {
            (s, f): self._sched(g)
            for (s, f), g in state_brackets.groupby(["state", "filing"])
        }

    @staticmethod
    def _sched(g: pd.DataFrame) -> _Schedule:
        g = g.sort_values("bracket_floor_usd")
        std = float(g["std_deduction_usd"].iloc[0])
        return _Schedule(
            floors=g["bracket_floor_usd"].to_numpy(dtype=float),
            rates=g["marginal_rate"].to_numpy(dtype=float),
            std_deduction=0.0 if np.isnan(std) else std,
        )

    @staticmethod
    def _scalar(out, like):
        return float(out) if np.isscalar(like) or np.ndim(like) == 0 else out

    def federal_tax(self, gross, filing: str):
        sch = self._fed[filing]
        taxable = np.maximum(np.asarray(gross, dtype=float) - sch.std_deduction, 0.0)
        return self._scalar(_bracket_tax(taxable, sch.floors, sch.rates), gross)

    def state_tax(self, gross, state: str, filing: str):
        zero = np.zeros_like(np.asarray(gross, dtype=float))
        if state in self.no_wage_tax:
            return self._scalar(zero, gross)
        eff_filing = "Single" if filing == "Head of household" else filing
        sch = self._state.get((state, eff_filing))
        if sch is None:                                  # taxing state w/o this filing block
            return self._scalar(zero, gross)
        taxable = np.maximum(np.asarray(gross, dtype=float) - sch.std_deduction, 0.0)
        return self._scalar(_bracket_tax(taxable, sch.floors, sch.rates), gross)

    def total_income_tax(self, gross, state: str, filing: str):
        return (np.asarray(self.federal_tax(gross, filing))
                + np.asarray(self.state_tax(gross, state, filing)))

    def marginal_income_tax_lost(self, household_income, worker_wage, state: str, filing: str):
        """Income tax LOST when the worker's wage is removed from the household:
        T(household_income) - T(household_income - worker_wage), fed+state."""
        hi = np.asarray(household_income, dtype=float)
        lo = np.maximum(hi - np.asarray(worker_wage, dtype=float), 0.0)
        fed = self.federal_tax(hi, filing) - self.federal_tax(lo, filing)
        st = (self.state_tax(hi, state, filing) - self.state_tax(lo, state, filing))
        return {"federal": np.asarray(fed), "state": np.asarray(st),
                "total": np.asarray(fed) + np.asarray(st)}


class PayrollFICA:
    """Federal payroll FICA (employer + employee for OASDI/Medicare; employee-only Addl)."""

    def __init__(self, payroll_params: pd.DataFrame):
        p = payroll_params
        oasdi = p[p["component"].str.contains("OASDI")].iloc[0]
        med = p[p["component"].str.fullmatch(r"Medicare")].iloc[0]
        addl_s = p[p["component"].str.contains("single", case=False)].iloc[0]
        addl_m = p[p["component"].str.contains("MFJ")].iloc[0]
        self.oasdi_rate = float(oasdi["rate"])
        self.oasdi_cap = float(oasdi["cap_threshold_usd"])
        self.medicare_rate = float(med["rate"])
        self.addl_rate = float(addl_s["rate"])
        self.addl_thresh_single = float(addl_s["cap_threshold_usd"])
        self.addl_thresh_mfj = float(addl_m["cap_threshold_usd"])

    def fica(self, wage, filing: str):
        """Total FICA (employer + employee for OASDI/Medicare; employee-only Addl Medicare)
        — all federal revenue that disappears with the job."""
        w = np.asarray(wage, dtype=float)
        oasdi = self.oasdi_rate * np.minimum(w, self.oasdi_cap)
        medicare = self.medicare_rate * w
        thresh = self.addl_thresh_mfj if filing == "Married filing jointly" else self.addl_thresh_single
        addl = self.addl_rate * np.maximum(w - thresh, 0.0)
        out = oasdi + medicare + addl
        return float(out) if np.isscalar(wage) or np.ndim(wage) == 0 else out

    def employee_fica(self, wage, filing: str):
        """Employee-side FICA only (half of OASDI + half of Medicare + all Addl Medicare).
        This is what reduces the worker's take-home pay (used for the consumption channel)."""
        w = np.asarray(wage, dtype=float)
        oasdi = (self.oasdi_rate / 2) * np.minimum(w, self.oasdi_cap)
        medicare = (self.medicare_rate / 2) * w
        thresh = self.addl_thresh_mfj if filing == "Married filing jointly" else self.addl_thresh_single
        addl = self.addl_rate * np.maximum(w - thresh, 0.0)
        out = oasdi + medicare + addl
        return float(out) if np.isscalar(wage) or np.ndim(wage) == 0 else out


def build_engines(data: loaders.FiscalData):
    return (IncomeTax(data.fed_brackets, data.state_brackets, data.state_no_wage_tax),
            PayrollFICA(data.payroll_params))


def state_slot_matrices(income: IncomeTax, state_arr: np.ndarray, state_masks: dict) -> dict:
    """Per-cell padded state-bracket matrices for vectorized state_tax over ALL cells at once.

    Each cell's (state, effective-filing) schedule expands into K fixed slots of (lo, hi, rate)
    plus a std-deduction column; no-wage-tax states / missing filing blocks are all-zero rows and
    short schedules get zero-rate padding — a zero-rate slot contributes an exact ±0.0, so the
    slot-ordered accumulation in `state_slot_tax` reproduces `_bracket_tax` BIT-FOR-BIT (the
    parity anchors in tests/test_v2_phase4 and tests/test_reemployment pin it). HoH maps to
    Single (this module's convention) → callers index the result by effective filing.
    Returns {eff_filing: (lo, hi, rate, rate*lo, std)}; rate*lo is the per-slot constant the
    reference recomputes each call (same operands → same bits)."""
    n = len(state_arr)
    K = max((len(sch.floors) for sch in income._state.values()), default=1)
    out = {}
    for eff in ("Married filing jointly", "Single"):
        lo = np.zeros((n, K)); hi = np.zeros((n, K)); rt = np.zeros((n, K))
        std = np.zeros(n)
        for s, mask in state_masks.items():
            if s in income.no_wage_tax:
                continue                                    # all-zero row → tax ≡ 0.0 exactly
            sch = income._state.get((s, eff))
            if sch is None:
                continue
            b = len(sch.floors)
            lo[mask, :b] = sch.floors
            hi[mask, :b] = np.append(sch.floors[1:], np.inf)
            rt[mask, :b] = sch.rates
            std[mask] = sch.std_deduction
        out[eff] = (lo, hi, rt, rt * lo, std)
    return out


def state_slot_tax(slots: dict, gross, filing: str) -> np.ndarray:
    """State income tax for every cell at once via `state_slot_matrices` — bit-identical to
    per-state `IncomeTax.state_tax` calls (identical slot-ordered accumulation; the out=
    buffers change allocation, never values)."""
    eff = "Single" if filing == "Head of household" else filing
    lo, hi, rt, rlo, std = slots[eff]
    t = np.maximum(np.asarray(gross, float) - std, 0.0)     # the same taxable transform
    tax = np.zeros(t.shape, dtype=float)
    tmp = np.empty_like(tax)
    for k in range(lo.shape[1]):                            # the _bracket_tax loop, per slot
        np.clip(t, lo[:, k], hi[:, k], out=tmp)
        np.multiply(tmp, rt[:, k], out=tmp)
        tax += tmp
        tax -= rlo[:, k]
    return tax


def verify_against_baked(data: loaders.FiscalData, tol: float = 1.0) -> dict:
    """Reproduce the file's baked income & FICA schedules from params. Returns max abs
    diffs (USD). Raises if any cell differs by more than `tol` dollars (rounding)."""
    inc, fica = build_engines(data)

    bi = data.baked_income
    fed = np.array([inc.federal_tax(r.household_income_usd, r.filing) for r in bi.itertuples()])
    st = np.array([inc.state_tax(r.household_income_usd, r.state, r.filing) for r in bi.itertuples()])
    fed_diff = np.abs(fed - bi["federal_tax_usd"].to_numpy())
    st_diff = np.abs(st - bi["state_tax_usd"].to_numpy())

    bf = data.baked_fica
    fic = np.array([fica.fica(r.wage_usd, r.filing) for r in bf.itertuples()])
    fica_diff = np.abs(fic - bf["total_fica_usd"].to_numpy())

    res = {"federal_max_diff": float(fed_diff.max()),
           "state_max_diff": float(st_diff.max()),
           "fica_max_diff": float(fica_diff.max())}
    for k, v in res.items():
        if v > tol:
            raise AssertionError(f"engine disagrees with baked schedule: {k}={v:.2f} > {tol}")
    return res


if __name__ == "__main__":
    data = loaders.load_all()
    inc, fica = build_engines(data)

    # Headline checks (from the Validation sheet)
    print("Federal single $100k  :", round(inc.federal_tax(100_000, "Single"), 0), "(expect 13614)")
    print("Federal MFJ   $200k   :", round(inc.federal_tax(200_000, "Married filing jointly"), 0),
          "(expect 27228)")
    print("FICA single $176,100  :", round(fica.fica(176_100, "Single"), 0), "(OASDI at cap)")
    print("FICA single $1,000,000:", round(fica.fica(1_000_000, "Single"), 0))

    res = verify_against_baked(data)
    print("\nReproduced baked schedules (max abs diff, USD):")
    for k, v in res.items():
        print(f"  {k:18s} {v:.4f}")
    print("\nTax engine matches the file's baked schedules.")
