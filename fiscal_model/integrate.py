"""Part C — within-cell integration wrapper.

Turns the point `fiscal_delta` into a CELL-level expectation. For each (occupation × state)
cell the fiscal delta is an expectation over three distributions (transfer_side_build_plan.md §0):
  1. within-cell household income — OEWS wage percentiles scaled multiplicatively to the
     cell's mean household income for each filing (§3.7 / C.1);
  2. number of children — P(children | filing, state, income band) from noc_distribution (Part A);
  3. residual phase — on-UI (during the ~26-wk window) vs $0 (after exhaustion) — NOT integrated;
     returned as two results so the dynamics apply the right one per cohort age (C.4).

Why integrate rather than evaluate at the mean: the transfer delta is a step function of income
(Medicaid cliff, SNAP phase-out, EITC hump). A cell whose mean sits just above a Medicaid
threshold reads as "nobody eligible" when the sub-mean part of the cell is the entire fiscal event.

Channels integrated here: income tax (fed/state), payroll (fed), consumption (state), transfers
(fed/state). The CORPORATE channel is industry-level (not occupation×state×filing×income) and is
layered on by the dynamics per (occupation × industry) — it is intentionally absent here.

Quadrature: rather than 7-11 hand-placed nodes, we use a fine income grid ($500 below $100k where
every kink lives, $5k above) with lognormal-CDF masses. The transfer evaluation is a cheap np.interp
on the $500-resolution baked lookup, so this resolves every kink for every children count robustly,
without having to locate them. ~p0.5..p99.9 of the within-cell lognormal.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from . import loaders
from .kernel import FiscalDelta, KernelParams
from .rates import IncomeTax, PayrollFICA, build_engines
from .transfers import TransferLookup, DEFAULT_FED_SHARE, PROGRAMS

INTERIM = Path(__file__).resolve().parent.parent / "data" / "interim"
NOC_BAND_EDGES = [-np.inf, 25_000, 55_000, np.inf]   # must match noc.DEFAULT_BAND_EDGES
_Z = {0.005: -2.5758293, 0.999: 3.0902323}
_erf = np.vectorize(math.erf)


def _norm_cdf(z):
    return 0.5 * (1.0 + _erf(np.asarray(z, dtype=float) / math.sqrt(2.0)))


@dataclass
class CellResult:
    soc_code: str
    state: str
    worker_wage: float
    ui_benefit: float
    during: FiscalDelta          # expected delta, cohort still on UI
    after: FiscalDelta           # expected delta, UI exhausted
    net_std_during: float        # dispersion of net_total across the within-cell distribution
    net_std_after: float
    coverage: str                # 'full' | partial-fallback note


class CellIntegrator:
    """Integrates fiscal_delta over a cell's income × children distribution, per phase."""

    def __init__(self, data: loaders.FiscalData, transfer_lookup: TransferLookup,
                 params: KernelParams = KernelParams(),
                 noc_csv: Path = INTERIM / "noc_distribution.csv"):
        self.params = params
        self.income, self.fica = build_engines(data)
        self.lookup = transfer_lookup
        self._oews = data.oews.set_index(["soc_code", "state"]).sort_index()
        self._hh = data.household.set_index(["soc_code", "state"]).sort_index()
        self._cons = data.consumption.set_index("state")["eff_tax_rate_frac"]
        self._noc = self._load_noc(noc_csv)
        self._filings = [
            ("Married filing jointly", "p_mfj", "inc_married_usd"),
            ("Head of household", "p_hoh", "inc_hoh_usd"),
            ("Single", "p_single", "inc_single_usd"),
        ]
        # NOC must cover every (filing, state, band) the integrator looks up — a missing cell
        # would silently default to "0 children" and bias transfers downward. Fail loud instead.
        _states = {s for (_, s, _) in self._noc}
        _missing = [(f, s, b) for f, _, _ in self._filings for s in _states for b in (0, 1, 2)
                    if (f, s, b) not in self._noc]
        assert not _missing, (f"noc_distribution missing {len(_missing)} (filing,state,band) cells; "
                              "rebuild via `python -m fiscal_model.noc`")

    @staticmethod
    def _load_noc(path: Path) -> dict:
        df = pd.read_csv(path)
        # band index from lower edge: NaN -> 0 (<25k), 25000 -> 1, 55000 -> 2
        lo = df["income_band_lo"]
        df["band"] = np.where(lo.isna(), 0, np.where(lo == 25_000, 1, 2))
        kmap = {"0": 0, "1": 1, "2": 2, "3+": 3, 0: 0, 1: 1, 2: 2}
        df["k"] = df["n_children"].map(kmap)
        out = {}
        for (filing, state, band), g in df.groupby(["filing_status", "state", "band"]):
            probs = np.zeros(4)
            for _, r in g.iterrows():
                probs[int(r["k"])] = r["prob"]
            out[(filing, state, int(band))] = probs
        return out

    # -- within-cell income distribution (C.1) -------------------------------
    def _wage_percentiles(self, soc, state):
        try:
            r = self._oews.loc[(soc, state)]
        except KeyError:
            return None
        if isinstance(r, pd.DataFrame):
            r = r.iloc[0]
        mean = r["annual_mean_usd"]
        if pd.isna(mean) and not pd.isna(r["hourly_mean_usd"]):
            mean = r["hourly_mean_usd"] * 2080
        p = {q: r[f"annual_p{q}_usd"] for q in (10, 25, 50, 75, 90)}
        for q in p:
            if pd.isna(p[q]) and not pd.isna(r[f"hourly_p{q}_usd"]):
                p[q] = r[f"hourly_p{q}_usd"] * 2080
        return mean, p

    def _nodes_and_masses(self, shape_p10, shape_p50, shape_p90, target_mean):
        """Lognormal scaled to target_mean (shape from the worker's wage percentiles).
        Returns (nodes, masses). Falls back to a point mass at target_mean if degenerate."""
        if (target_mean is None or target_mean <= 0 or any(pd.isna(x) or x <= 0 for x in
                (shape_p10, shape_p50, shape_p90)) or shape_p90 <= shape_p10):
            return np.array([max(target_mean or 0.0, 0.0)]), np.array([1.0])
        sigma = (math.log(shape_p90) - math.log(shape_p10)) / (2 * 1.2815515594508)
        mu0 = math.log(shape_p50)
        mean0 = math.exp(mu0 + sigma * sigma / 2)
        mu = mu0 + math.log(target_mean / mean0)            # multiplicative scaling to target mean
        lo = math.exp(mu + sigma * _Z[0.005])
        hi = math.exp(mu + sigma * _Z[0.999])
        fine = np.arange(max(250.0, math.floor(lo / 500) * 500), min(hi, 100_000) + 1, 500)
        sparse = np.arange(100_000, hi + 1, 5_000) if hi > 100_000 else np.array([])
        nodes = np.unique(np.concatenate([fine, sparse]))
        if nodes.size < 2:
            return np.array([target_mean]), np.array([1.0])
        mids = np.sqrt(nodes[:-1] * nodes[1:])              # geometric midpoints (lognormal-natural)
        edges = np.concatenate([[0.0], mids, [np.inf]])
        cdf = np.where(edges <= 0, 0.0, np.where(np.isinf(edges), 1.0,
                       _norm_cdf((np.log(np.clip(edges, 1e-9, None)) - mu) / sigma)))
        masses = np.diff(cdf)
        masses = masses / masses.sum()
        return nodes, masses

    @staticmethod
    def _band_index(income):
        return np.digitize(income, [25_000, 55_000]).astype(int)  # 0/1/2

    # -- per-filing, per-phase integration -----------------------------------
    def _integrate_filing(self, soc, state, filing, hh_mean, worker_wage, ui, p,
                          collapse_to_mean=False):
        if collapse_to_mean:
            nodes, masses = np.array([hh_mean if hh_mean and hh_mean > 0 else worker_wage]), np.array([1.0])
        else:
            nodes, masses = self._nodes_and_masses(p[10], p[50], p[90],
                                                   hh_mean if hh_mean and hh_mean > 0 else worker_wage)
        h = nodes
        # income tax delta (fed/state), vectorized over income nodes
        inc = self.income.marginal_income_tax_lost(h, worker_wage, state, filing)
        inc_fed, inc_state, inc_tot = (np.asarray(inc["federal"], float),
                                       np.asarray(inc["state"], float),
                                       np.asarray(inc["total"], float))
        payroll = float(self.fica.fica(worker_wage, filing))          # constant across nodes
        emp_fica = float(self.fica.employee_fica(worker_wage, filing))
        rate = float(self._cons.get(state, 0.0))

        out = {}
        for phase, residual in (("during", ui), ("after", 0.0)):
            disp_loss = np.maximum(worker_wage - inc_tot - emp_fica - residual, 0.0)
            cons = rate * self.params.marginal_taxable_multiplier * \
                self.params.mpc * self.params.consumption_stickiness * disp_loss
            h_after = np.maximum(h - worker_wage, 0.0) + residual

            # transfer delta over children, weighted by P(k | filing, state, band(h))
            tr_fed = np.zeros_like(h); tr_state = np.zeros_like(h)
            bands = self._band_index(h)
            ks = [0] if filing == "Single" else [0, 1, 2, 3]
            for k in ks:
                xs, progs = self.lookup.program_arrays(state, filing, k)
                d_fed = np.zeros_like(h); d_state = np.zeros_like(h)
                for prog, ys in progs.items():
                    delta = np.interp(h_after, xs, ys) - np.interp(h, xs, ys)
                    fs = self.lookup.fed_share.get(prog, 1.0)
                    d_fed += delta * fs
                    d_state += delta * (1.0 - fs)
                pk = np.array([self._noc.get((filing, state, b), np.full(4, 0.25))[k] for b in bands])
                tr_fed += pk * d_fed
                tr_state += pk * d_state

            # expected channel values (mass-weighted over income nodes)
            fd = FiscalDelta(
                lost_income_tax_fed=float((masses * inc_fed).sum()),
                lost_income_tax_state=float((masses * inc_state).sum()),
                lost_payroll_fed=payroll,
                lost_consumption_tax_state=float((masses * cons).sum()),
                gained_outlays_fed=float((masses * tr_fed).sum()),
                gained_outlays_state=float((masses * tr_state).sum()),
            )
            # net_total per node, for dispersion
            net_node = (inc_fed + inc_state + payroll + cons + tr_fed + tr_state)
            mean_net = float((masses * net_node).sum())
            var = float((masses * (net_node - mean_net) ** 2).sum())
            out[phase] = (fd, var)
        return out

    def integrate(self, soc_code: str, state: str, collapse_to_mean: bool = False) -> Optional[CellResult]:
        wp = self._wage_percentiles(soc_code, state)
        if wp is None:
            return None
        worker_wage, p = wp
        if worker_wage is None or pd.isna(worker_wage):
            return None
        try:
            hh = self._hh.loc[(soc_code, state)]
            if isinstance(hh, pd.DataFrame):
                hh = hh.iloc[0]
        except KeyError:
            hh = None
        ui = self.lookup.ui_benefit(worker_wage, state)

        # filing weights & household means (fallback: equal-ish / wage-based if suppressed)
        filings = []
        for label, pcol, icol in self._filings:
            pf = float(hh[pcol]) if hh is not None and not pd.isna(hh[pcol]) else None
            mean = float(hh[icol]) if hh is not None and not pd.isna(hh[icol]) else None
            filings.append((label, pf, mean))
        if all(pf is None for _, pf, _ in filings):
            filings = [(lbl, 1 / 3, None) for lbl, _, _ in filings]
            coverage = "no household data; equal filing weights"
        else:
            tot = sum(pf for _, pf, _ in filings if pf) or 1.0
            filings = [(lbl, (pf or 0.0) / tot, mean) for lbl, pf, mean in filings]
            coverage = "full"

        agg = {"during": FiscalDelta(), "after": FiscalDelta()}
        var = {"during": 0.0, "after": 0.0}
        for label, pf, mean in filings:
            if pf <= 0:
                continue
            res = self._integrate_filing(soc_code, state, label, mean, worker_wage, ui, p,
                                         collapse_to_mean)
            for phase in ("during", "after"):
                fd, v = res[phase]
                agg[phase] = agg[phase] + FiscalDelta(
                    **{f: getattr(fd, f) * pf for f in fd.__dataclass_fields__})
                var[phase] += pf * v   # approx: pool within-filing variance by filing weight

        return CellResult(soc_code, state, worker_wage, ui, agg["during"], agg["after"],
                          math.sqrt(max(var["during"], 0.0)), math.sqrt(max(var["after"], 0.0)),
                          coverage)


if __name__ == "__main__":
    data = loaders.load_all()
    lk = TransferLookup()
    ci = CellIntegrator(data, lk)

    # Pick a low-wage occupation in an expansion vs non-expansion state to show the cliff.
    examples = [("35-3023", "Texas"), ("35-3023", "California"), ("15-1252", "California")]
    names = {"35-3023": "Fast food / counter workers", "15-1252": "Software developers"}
    for soc, st in examples:
        r = ci.integrate(soc, st)
        rm = ci.integrate(soc, st, collapse_to_mean=True)
        if r is None:
            print(f"\n{soc}/{st}: no data"); continue
        print(f"\n=== {names.get(soc, soc)} ({soc}) in {st}  | worker wage ${r.worker_wage:,.0f}  UI ${r.ui_benefit:,.0f}")
        for phase in ("during", "after"):
            fd = getattr(r, phase)
            print(f"  [{phase:6s}] net ${fd.net_total:,.0f}  (income ${fd.lost_income_tax_fed+fd.lost_income_tax_state:,.0f}"
                  f"  payroll ${fd.lost_payroll_fed:,.0f}  consumption ${fd.lost_consumption_tax_state:,.0f}"
                  f"  transfers ${fd.gained_outlays_fed+fd.gained_outlays_state:,.0f})")
        # integrated vs at-the-mean (after phase) — the kink test
        diff = r.after.gained_outlays_fed + r.after.gained_outlays_state \
            - (rm.after.gained_outlays_fed + rm.after.gained_outlays_state)
        print(f"  transfer (after): integrated ${r.after.gained_outlays_fed+r.after.gained_outlays_state:,.0f}"
              f"  vs at-mean ${rm.after.gained_outlays_fed+rm.after.gained_outlays_state:,.0f}"
              f"  -> diff ${diff:,.0f}")
