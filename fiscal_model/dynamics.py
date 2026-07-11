"""Dynamic model (briefing §7) — wraps the kernel in a stock-flow loop.

Each period a user-set displacement flow (levers.py = exposure-gated × feasibility × adoption)
moves workers employed→unemployed; the kernel's per-worker delta (precomputed per occupation×state)
is applied to the stock; the federal deficit accumulates into a debt stock with interest, while
**states must balance within-year** (the contractionary amplifier the federal government escapes).

Stocks per (occupation × state) cell:
  employed → (displacement) → unemployed → (reabsorption) → reemployed (at a wage haircut)

UI is time-limited: a newly-displaced cohort is on UI for `ui_weeks/52` of its first period
(phase 'during', + a UI outlay), then exhausted (phase 'after') — the Medicaid/SNAP step-up lands
at exhaustion, not displacement. The corporate offset (recovered capital tax) is attached to the
displaced worker in v1 (see note).

Per-worker deltas are SCENARIO-INVARIANT (they depend on wages/households/states/sectors, not on
the levers), so they are precomputed once over all occupation×state cells and cached; the loop just
scales them by the scenario's flows. Everything else is an explicit lever in DynamicsParams.

v1 simplifications (documented): demand multiplier and UBI financing are simple closed-forms;
reemployed workers carry a haircut residual loss only. (The corporate offset rides the CUMULATIVE
automated stock — a job stays automated after its worker is reabsorbed — matching v2.)
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from . import loaders, levers, workers
from .integrate import CellIntegrator
from .kernel import Kernel, KernelParams
from .transfers import TransferLookup

INTERIM = Path(__file__).resolve().parent.parent / "data" / "interim"
DELTA_CACHE = INTERIM / "worker_deltas_by_occ_state.parquet"
# UI benefits are federally taxable income; ~10% is a rough average effective rate on them
# (no source-grade estimate wired — a sensitivity candidate). ONE definition, both engines.
UI_FED_TAX_RATE = 0.10

_CHANNELS = ["inc_fed", "inc_state", "payroll_fed", "cons_state", "transfer_fed", "transfer_state"]


@dataclass
class DynamicsParams:
    n_periods: int = 10
    ui_weeks: int = 26
    reabsorption_rate: float = 0.0       # per-period share of unemployed re-employed (default 0 = thesis)
    reemployment_haircut: float = 0.30   # wage cut on re-employment -> residual loss
    demand_multiplier: float = 0.0       # 2nd-round: induced fiscal loss per $ of net loss (0 = off)
    state_response: str = "mix"          # 'cut_spending' | 'raise_rates' | 'mix' (recorded)
    interest_rate: float = 0.03          # on federal debt
    adoption_path: Optional[list] = None # adoption per period; None -> constant LeverParams.adoption
    ubi_annual: float = 0.0              # per-capita UBI ($); 0 = off
    corp_offset_scale: float = 1.0       # scales the (linear) corporate recapture without recompute
    consumption_scale: float = 1.0       # scales the (linear) consumption channel without recompute
    kernel_params: KernelParams = field(default_factory=KernelParams)


# ----------------------------------------------------------------- precompute
def corporate_per_worker(data: loaders.FiscalData, kp: KernelParams) -> pd.Series:
    """Federal corporate-tax offset per displaced worker, by occupation (employment-weighted
    over the sectors the occupation works in)."""
    k = Kernel(data, kp)
    m = data.matrices_sector.copy()
    m = m[m["emp_thousands"] > 0]
    m["comp_per_worker"] = m["comp_musd"] / m["emp_thousands"] * 1_000.0   # $m/$k *1000 = $
    vals = []
    for r in m.itertuples():
        corp, div, pt = k._corporate(r.industry, r.comp_per_worker)
        vals.append(corp + div + pt)
    m["corp_offset_pw"] = vals
    # employment-weighted average over sectors for each occupation
    g = m.groupby("soc_code").apply(
        lambda d: np.average(d["corp_offset_pw"], weights=d["emp_thousands"]))
    g.name = "corp_per_worker_fed"
    return g


def precompute_worker_deltas(data: loaders.FiscalData, lookup: TransferLookup,
                             kp: KernelParams, force: bool = False) -> pd.DataFrame:
    """Per (occupation × state): employed, worker_wage, ui_benefit, and the during/after
    per-worker fiscal delta by channel. Cached (scenario-invariant)."""
    if DELTA_CACHE.exists() and not force:
        return pd.read_parquet(DELTA_CACHE)

    ci = CellIntegrator(data, lookup, kp)
    emp = data.oews.groupby(["soc_code", "state"])["employment_persons"].sum()
    rows = []
    for (soc, state), employed in emp.items():
        if pd.isna(employed) or employed <= 0:
            continue
        r = ci.integrate(soc, state)
        if r is None:
            continue
        rec = {"soc_code": soc, "state": state, "employed": float(employed),
               "worker_wage": r.worker_wage, "ui_benefit": r.ui_benefit}
        for phase in ("during", "after"):
            fd = getattr(r, phase)
            rec[f"{phase}_inc_fed"] = fd.lost_income_tax_fed
            rec[f"{phase}_inc_state"] = fd.lost_income_tax_state
            rec[f"{phase}_payroll_fed"] = fd.lost_payroll_fed
            rec[f"{phase}_cons_state"] = fd.lost_consumption_tax_state
            rec[f"{phase}_transfer_fed"] = fd.gained_outlays_fed
            rec[f"{phase}_transfer_state"] = fd.gained_outlays_state
        rows.append(rec)
    df = pd.DataFrame(rows)
    corp = corporate_per_worker(data, kp)
    df = df.merge(corp.rename("corp_per_worker_fed"), left_on="soc_code", right_index=True, how="left")
    df["corp_per_worker_fed"] = df["corp_per_worker_fed"].fillna(0.0)
    INTERIM.mkdir(parents=True, exist_ok=True)
    df.to_parquet(DELTA_CACHE, index=False)
    return df


# -------------------------------------------------------------------- model
class DynamicModel:
    def __init__(self, data: loaders.FiscalData, deltas: pd.DataFrame,
                 lever_params: levers.LeverParams, params: DynamicsParams = DynamicsParams()):
        self.data = data
        self.p = params
        self.lp = lever_params
        d = deltas.reset_index(drop=True).copy()
        self.d = d
        # per-occupation displacement at adoption=1 (cognitive + robot channels); scaled by
        # adoption each period. replace() copies all lever fields (incl. the robot channel).
        g = levers.displacement_fraction(data.exposure_occ, replace(lever_params, adoption=1.0))
        self.g_cell = d["soc_code"].map(g).fillna(0.0).to_numpy()
        self.ui_share = min(1.0, params.ui_weeks / 52.0)
        self.states = d["state"].to_numpy()
        self.uniq_states = sorted(pd.unique(self.states))
        self._state_idx = {s: i for i, s in enumerate(self.uniq_states)}
        self.state_of_cell = np.array([self._state_idx[s] for s in self.states])
        # channel arrays
        self.arr = {ph: {c: d[f"{ph}_{c}"].to_numpy() for c in _CHANNELS} for ph in ("during", "after")}
        for ph in ("during", "after"):                       # linear post-hoc scales (no recompute)
            self.arr[ph]["cons_state"] = self.arr[ph]["cons_state"] * params.consumption_scale
        self.ui = d["ui_benefit"].to_numpy()
        self.corp = d["corp_per_worker_fed"].to_numpy() * params.corp_offset_scale
        self.emp0 = d["employed"].to_numpy()
        # rough avg compensation per worker for the UBI tax base (wage proxy)
        self.wage = d["worker_wage"].to_numpy()

    def _adoption(self, t):
        if self.p.adoption_path is not None:
            return self.p.adoption_path[min(t, len(self.p.adoption_path) - 1)]
        return self.lp.adoption

    def run(self) -> pd.DataFrame:
        p, n = self.p, self.d.shape[0]
        employed = self.emp0.copy()
        U = np.zeros(n)        # unemployed, 'after' phase (carried)
        R = np.zeros(n)        # reemployed (haircut residual)
        debt = 0.0
        baseline_emp = employed.sum()
        baseline_pop = baseline_emp                    # UBI per-capita base = workforce (v1)
        baseline_rev = None
        auto_disp = np.zeros(n)                        # cumulative automation-displaced stock (fix 1)
        out = []

        for t in range(p.n_periods):
            adopt = self._adoption(t)
            # cumulative diffusion ceiling (fix 1) — identical to v2 so the C8 anchor holds
            new = workers.displacement_flow(self.g_cell, adopt, self.emp0, auto_disp, employed)
            auto_disp = auto_disp + new
            employed = employed - new

            # ---- per-cell fiscal flows ($) ----
            ch = {c: np.zeros(n) for c in _CHANNELS}
            for c in _CHANNELS:
                # new cohort: UI-window blend; carried U: fully 'after'; reemployed R: haircut residual
                blend = self.ui_share * self.arr["during"][c] + (1 - self.ui_share) * self.arr["after"][c]
                ch[c] += new * blend + U * self.arr["after"][c]
                if c in ("inc_fed", "inc_state", "payroll_fed", "cons_state"):   # residual: no transfers
                    ch[c] += R * p.reemployment_haircut * self.arr["after"][c]

            ui_outlay_fed = (new * self.ui * self.ui_share)
            ui_tax_fed = UI_FED_TAX_RATE * ui_outlay_fed
            # corporate recovery on the CUMULATIVE automated stock (coherence fix, matches v2): a job stays
            # automated after its worker is reabsorbed — the saved labour cost keeps flowing to capital.
            corp_offset_fed = auto_disp * self.corp

            # ---- aggregate federal ----
            fed = (ch["inc_fed"] + ch["payroll_fed"] + ch["transfer_fed"]
                   + ui_outlay_fed - ui_tax_fed - corp_offset_fed)
            net_fed = fed.sum()
            # ---- aggregate state (per state, then total gap that must be closed) ----
            state_cell = ch["inc_state"] + ch["cons_state"] + ch["transfer_state"]
            state_net = np.bincount(self.state_of_cell, weights=state_cell, minlength=len(self.uniq_states))
            state_gap_total = state_net[state_net > 0].sum()                     # states close positive gaps

            # ---- second-round demand multiplier (toggle) ----
            induced = p.demand_multiplier * (net_fed + state_gap_total)
            net_fed += induced

            # ---- UBI is a real federal outlay (fix 2; identical to v2 so C8 holds) ----
            net_fed += p.ubi_annual * baseline_pop

            # ---- federal debt with interest ----
            debt = debt * (1 + p.interest_rate) + net_fed

            # ---- UBI required tax rate (base erodes with employment) ----
            base = (employed * self.wage).sum()                                  # remaining labor income
            ubi_rate = (p.ubi_annual * baseline_pop / base) if (p.ubi_annual > 0 and base > 0) else 0.0

            tot_emp = employed.sum()
            tot_unemp = (U + new).sum()
            rev_lost = ch["inc_fed"].sum() + ch["inc_state"].sum() + ch["payroll_fed"].sum()
            if baseline_rev is None:
                # max-scenario labor revenue (all workers displaced) — the denominator for
                # revenue_lost_pct. income tax & payroll are phase-invariant, so using 'after'
                # here is consistent with rev_lost (which uses the during/after blend).
                baseline_rev = (self.emp0 * (self.arr["after"]["inc_fed"] + self.arr["after"]["inc_state"]
                                             + self.arr["after"]["payroll_fed"])).sum()

            out.append({
                "period": t, "adoption": adopt,
                "employed_M": tot_emp / 1e6, "unemployed_M": tot_unemp / 1e6,
                "reemployed_M": R.sum() / 1e6,   # start-of-period reemployed stock
                "employment_drop_pct": 100 * (1 - tot_emp / baseline_emp),
                "revenue_lost_B": rev_lost / 1e9,
                "revenue_lost_pct": 100 * rev_lost / baseline_rev if baseline_rev else 0.0,
                "transfers_added_B": (ch["transfer_fed"].sum() + ch["transfer_state"].sum()
                                      + ui_outlay_fed.sum()) / 1e9,
                "corp_offset_B": corp_offset_fed.sum() / 1e9,
                "fed_deficit_B": net_fed / 1e9, "fed_debt_B": debt / 1e9,
                "state_gap_B": state_gap_total / 1e9,
                "ubi_required_rate": ubi_rate,
            })

            # ---- end of period: reabsorption ----
            pool = U + new
            reabsorbed = pool * p.reabsorption_rate
            U = pool - reabsorbed
            R = R + reabsorbed
        return pd.DataFrame(out)


if __name__ == "__main__":
    data = loaders.load_all()
    lookup = TransferLookup()
    print("precomputing per-worker deltas over occupation×state cells (cached after first run)...")
    deltas = precompute_worker_deltas(data, lookup, KernelParams())
    print(f"  {len(deltas):,} cells.\n")

    lp = levers.LeverParams(cognitive_feasibility=0.85, physical_feasibility=0.25, adoption=1.0)
    dp = DynamicsParams(n_periods=10, reabsorption_rate=0.0,
                        adoption_path=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9])
    res = DynamicModel(data, deltas, lp, dp).run()
    pd.set_option("display.width", 200, "display.max_columns", 20)
    cols = ["period", "adoption", "employment_drop_pct", "revenue_lost_pct", "revenue_lost_B",
            "transfers_added_B", "corp_offset_B", "fed_deficit_B", "fed_debt_B", "state_gap_B"]
    print(res[cols].to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    e = res.iloc[2]   # an early period, where high-wage cognitive work goes first
    print(f"\nBase-migration (period {int(e['period'])}): employment −{e['employment_drop_pct']:.1f}% "
          f"but labor revenue −{e['revenue_lost_pct']:.1f}% — revenue falls FASTER than employment "
          f"(the most-exposed work is the highest-paid).")
    f = res.iloc[-1]
    print(f"Federal vs state asymmetry (final): the corporate-tax recapture (${f['corp_offset_B']:,.0f}B) "
          f"cushions the federal deficit to ${f['fed_deficit_B']:,.0f}B/yr, but states have no such "
          f"recapture and must close ${f['state_gap_B']:,.0f}B/yr within-year. Federal debt ${f['fed_debt_B']:,.0f}B.")
