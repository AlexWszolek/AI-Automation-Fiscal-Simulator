"""The static fiscal kernel — net fiscal delta of displacing one worker.

Five separate, additive channels (per docs/PROJECT_BRIEFING_v2.md §6), each an
independently inspectable lever. Three are built here; two plug in later:

    income tax     T(HH) - T(HH - wage), fed+state        -> rates.IncomeTax   [DONE]
    payroll FICA   FICA(wage), capped                     -> rates.PayrollFICA [DONE]
    consumption    eff-rate(state) x spending cut         -> _consumption()    [DONE here]
    corporate      lost comp -> surplus -> corp/div/PT tax -> _corporate()     [DONE here]
    transfers      transfers(without) - transfers(with)   -> set_transfer_lookup() [SEAM]

Sign convention: revenue LOSSES and outlay GAINS are POSITIVE (worse for government);
recovered capital taxes are an OFFSET. `net = cost - offset`. Federal and state-local
are tracked separately throughout.

The kernel is pure and deterministic. The corporate channel is data-driven by the
per-sector effective rates in the capital file; the consumption channel by the per-state
effective rate in the consumption file. All behavioural assumptions are KernelParams levers.

NOT YET WIRED (await NOC + PolicyEngine bake): the transfer channel and the within-cell
income-distribution integration (scale OEWS percentiles to the household mean, §3.7).
`fiscal_delta()` here evaluates a single (wage, household_income) point; the distribution
integration will wrap it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd

from . import loaders, rates


# --------------------------------------------------------------------- levers
@dataclass(frozen=True)   # frozen: instances are shared as defaults/templates — mutation must fail loud
class KernelParams:
    # --- corporate channel ---
    surplus_capture: float = 1.0
    """Fraction of the displaced worker's lost COMPENSATION that becomes taxable operating
    surplus. 1.0 = the full saved labour cost shows up as profit (the most generous offset,
    steelmanning the optimistic case); lower if automation's own cost absorbs some."""
    dividend_tax_rate: float = 0.188
    """Effective federal tax on distributed dividends (qualified-dividend top rate 20% +
    3.8% NIIT ~= 18.8% for the high earners who own most corporate equity)."""
    passthrough_individual_rate: float = 0.25
    """Effective individual rate on pass-through (proprietor) income routed to the owner.
    v1 federal approximation; the state share is a later refinement."""

    # --- consumption channel ---
    mpc: float = 0.95
    """Marginal propensity to consume out of the lost disposable income."""
    consumption_stickiness: float = 1.0
    """Fraction of the consumption decline realized in-period (1.0 = no stickiness;
    < 1.0 mutes/delays the short-run hit — the briefing's v1 stickiness lever)."""
    marginal_taxable_multiplier: float = 1.0
    """Marginal taxable basket share / average. Displaced workers protect exempt
    necessities and cut taxable discretionary goods, so this can exceed 1.0."""


@dataclass
class Worker:
    """A displaced worker (or n identical workers). Wage/household_income in dollars."""
    worker_wage: float          # OEWS annual wage ($)
    household_income: float     # mean HOUSEHOLD income (HINCP, $), the AGI proxy
    filing: str                 # 'Single' | 'Head of household' | 'Married filing jointly'
    state: str                  # full state name ('District of Columbia' for DC)
    sector: str                 # one of the 20 BEA sectors (for the corporate channel)
    compensation: Optional[float] = None  # labour cost saved; defaults to worker_wage
    n: float = 1.0              # number of such workers displaced
    n_children: int = 0         # children in the household (for the transfer channel; 0..3 = 3+)


# --------------------------------------------------------------------- output
@dataclass
class FiscalDelta:
    # losses (positive = lost revenue)
    lost_income_tax_fed: float = 0.0
    lost_income_tax_state: float = 0.0
    lost_payroll_fed: float = 0.0
    lost_consumption_tax_state: float = 0.0
    # recovered capital taxes (the offset; stored positive, subtracted in net)
    recovered_corp_tax_fed: float = 0.0
    recovered_dividend_tax_fed: float = 0.0
    recovered_passthrough_tax_fed: float = 0.0
    # outlays (positive = added spending) — transfer channel, wired later
    gained_outlays_fed: float = 0.0
    gained_outlays_state: float = 0.0

    @property
    def offset(self) -> float:
        return (self.recovered_corp_tax_fed + self.recovered_dividend_tax_fed
                + self.recovered_passthrough_tax_fed)

    @property
    def cost(self) -> float:
        """Gross fiscal cost before the capital-tax offset."""
        return (self.lost_income_tax_fed + self.lost_income_tax_state
                + self.lost_payroll_fed + self.lost_consumption_tax_state
                + self.gained_outlays_fed + self.gained_outlays_state)

    @property
    def net_fed(self) -> float:
        return (self.lost_income_tax_fed + self.lost_payroll_fed + self.gained_outlays_fed
                - self.offset)

    @property
    def net_state(self) -> float:
        return (self.lost_income_tax_state + self.lost_consumption_tax_state
                + self.gained_outlays_state)

    @property
    def net_total(self) -> float:
        return self.net_fed + self.net_state

    def __add__(self, other: "FiscalDelta") -> "FiscalDelta":
        return FiscalDelta(**{f: getattr(self, f) + getattr(other, f)
                              for f in self.__dataclass_fields__})

    def breakdown(self) -> dict:
        return {
            "lost_income_tax_fed": self.lost_income_tax_fed,
            "lost_income_tax_state": self.lost_income_tax_state,
            "lost_payroll_fed": self.lost_payroll_fed,
            "lost_consumption_tax_state": self.lost_consumption_tax_state,
            "recovered_corp_tax_fed": -self.recovered_corp_tax_fed,
            "recovered_dividend_tax_fed": -self.recovered_dividend_tax_fed,
            "recovered_passthrough_tax_fed": -self.recovered_passthrough_tax_fed,
            "gained_outlays_fed": self.gained_outlays_fed,
            "gained_outlays_state": self.gained_outlays_state,
            "cost": self.cost, "offset": self.offset,
            "net_fed": self.net_fed, "net_state": self.net_state, "net_total": self.net_total,
        }


# --------------------------------------------------------------------- kernel
class Kernel:
    def __init__(self, data: loaders.FiscalData, params: Optional[KernelParams] = None):
        self.data = data
        self.params = params if params is not None else KernelParams()
        self.income, self.fica = rates.build_engines(data)
        self._cap = data.capital.set_index("industry")
        self._cons = data.consumption.set_index("state")["eff_tax_rate_frac"]
        self._transfer_lookup: Optional[Callable[[Worker, float], dict]] = None

    # -- transfer seam: PolicyEngine-baked lookup plugs in here later --
    def set_transfer_lookup(self, fn: Callable[[Worker, float], dict]) -> None:
        """Register the marginal-transfer function: fn(worker, residual_income) ->
        {'fed': float, 'state': float} = transfers(without) - transfers(with), per worker."""
        self._transfer_lookup = fn

    # -- corporate channel ---------------------------------------------------
    def _corporate(self, sector: str, lost_comp: float) -> tuple[float, float, float]:
        """Lost compensation -> operating surplus -> (corp tax, dividend tax, pass-through tax).
        Government (and any sector with no taxable capital income) returns zeros."""
        if sector not in self._cap.index:
            raise KeyError(f"unknown sector for corporate channel: {sector!r}")
        row = self._cap.loc[sector]
        corp_share = row["corp_share_taxable_capital_income"]
        if pd.isna(corp_share):                          # Government: capital share is depreciation
            return 0.0, 0.0, 0.0
        surplus = self.params.surplus_capture * lost_comp
        corp_portion = corp_share * surplus
        pass_portion = (1.0 - corp_share) * surplus

        eff_corp = row["eff_corp_tax_rate"]
        corp_tax = (0.0 if pd.isna(eff_corp) else eff_corp) * corp_portion
        after_tax = corp_portion - corp_tax
        payout = row["dividend_payout_ratio"]
        dividends = (0.0 if pd.isna(payout) else payout) * after_tax
        div_tax = self.params.dividend_tax_rate * dividends
        pass_tax = self.params.passthrough_individual_rate * pass_portion
        return corp_tax, div_tax, pass_tax

    # -- consumption channel -------------------------------------------------
    def _consumption_tax(self, state: str, disposable_income_loss: float) -> float:
        rate = float(self._cons.get(state, 0.0))
        spending_cut = (self.params.mpc * self.params.consumption_stickiness
                        * max(0.0, disposable_income_loss))
        return rate * self.params.marginal_taxable_multiplier * spending_cut

    # -- assembly ------------------------------------------------------------
    def fiscal_delta(self, w: Worker, residual_income: float = 0.0) -> FiscalDelta:
        """Net fiscal delta of displacing worker `w`. `residual_income` is the worker's
        remaining income after displacement (e.g. UI during the window, 0 post-exhaustion) —
        it reduces the consumption hit and will feed the transfer lookup."""
        inc = self.income.marginal_income_tax_lost(w.household_income, w.worker_wage,
                                                    w.state, w.filing)
        inc_fed, inc_state = float(np.asarray(inc["federal"])), float(np.asarray(inc["state"]))
        payroll = float(self.fica.fica(w.worker_wage, w.filing))
        emp_fica = float(self.fica.employee_fica(w.worker_wage, w.filing))

        disposable_loss = max(0.0, w.worker_wage - inc["total"] - emp_fica - residual_income)
        cons = self._consumption_tax(w.state, disposable_loss)

        lost_comp = w.worker_wage if w.compensation is None else w.compensation
        corp_tax, div_tax, pass_tax = self._corporate(w.sector, lost_comp)

        fd = FiscalDelta(
            lost_income_tax_fed=inc_fed,
            lost_income_tax_state=inc_state,
            lost_payroll_fed=payroll,
            lost_consumption_tax_state=cons,
            recovered_corp_tax_fed=corp_tax,
            recovered_dividend_tax_fed=div_tax,
            recovered_passthrough_tax_fed=pass_tax,
        )
        if self._transfer_lookup is not None:
            tr = self._transfer_lookup(w, residual_income)
            fd.gained_outlays_fed = tr.get("fed", 0.0)
            fd.gained_outlays_state = tr.get("state", 0.0)

        if w.n != 1.0:
            fd = FiscalDelta(**{f: getattr(fd, f) * w.n for f in fd.__dataclass_fields__})
        return fd


if __name__ == "__main__":
    data = loaders.load_all()
    k = Kernel(data)

    examples = [
        Worker(worker_wage=180_000, household_income=250_000, filing="Married filing jointly",
               state="California", sector="Professional, scientific, and technical services",
               compensation=220_000),
        Worker(worker_wage=35_000, household_income=55_000, filing="Single",
               state="Texas", sector="Accommodation and food services", compensation=40_000),
    ]
    labels = ["High-wage cognitive (SW dev, CA, MFJ)", "Low-wage service (food svc, TX, single)"]

    for lab, w in zip(labels, examples):
        fd = k.fiscal_delta(w)
        b = fd.breakdown()
        print(f"\n=== {lab}  wage ${w.worker_wage:,} / HH ${w.household_income:,} / {w.sector}")
        for key in ("lost_income_tax_fed", "lost_income_tax_state", "lost_payroll_fed",
                    "lost_consumption_tax_state", "recovered_corp_tax_fed",
                    "recovered_dividend_tax_fed", "recovered_passthrough_tax_fed"):
            print(f"   {key:32s} {b[key]:>12,.0f}")
        print(f"   {'-- gross cost':32s} {b['cost']:>12,.0f}")
        print(f"   {'-- capital-tax offset':32s} {b['offset']:>12,.0f}")
        print(f"   {'== NET (fed / state / total)':32s} "
              f"{b['net_fed']:>10,.0f} / {b['net_state']:>9,.0f} / {b['net_total']:>10,.0f}")
        # base-migration read: revenue lost as a share of wage, before offset
        print(f"   revenue lost / wage = "
              f"{(b['lost_income_tax_fed']+b['lost_income_tax_state']+b['lost_payroll_fed']):,.0f}"
              f" / {w.worker_wage:,} = "
              f"{(b['lost_income_tax_fed']+b['lost_income_tax_state']+b['lost_payroll_fed'])/w.worker_wage:.1%}")

    print("\n[transfer channel + within-cell distribution NOT yet wired — awaiting NOC/PolicyEngine]")
