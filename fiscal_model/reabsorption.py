"""Phase 4 — reabsorption Rung 1 (plan decision D): the permanent service-floor scar.

Rung 0 (the Phase-1 anchor) re-employs a displaced worker at a flat haircut of the ORIGIN wage and only
recovers a fraction of the tax channels — it can never trip a means-tested program, silently zeroing a
thesis-central channel. Rung 1 re-employs at a **service-floor wage w_d DECOUPLED from the origin wage**:
a low percentile of still-hiring low-exposure work. Earning w_d instead of w_o, the household re-query
hh_baseline − w_o + w_d can fall below the EITC / SNAP / Medicaid thresholds, turning those outlays ON.
The scar (w_o − w_d) is permanent.

`w_d[state]` = employment-weighted P(`reabsorption_floor_pctile`, default p30) of the per-occupation
annual-mean wage over the **low-exposure** occupations {soc : ai_pca_score ≤ national EXPOSURE_PCTILE}.
OEWS ships no p30 wage column, so the floor is a weighted percentile of the occupational mean-wage
distribution (not a column read). The AI-exposure file is national and continuous (a PCA score, no state
dimension, no low/high flag), so the low-exposure cut is a **fixed internal constant** — `EXPOSURE_PCTILE`
— not a scenario lever; it is folded into the destination wage, and the cache key carries only the floor
percentile. A state with no low-exposure OEWS rows falls back to the national floor (does not occur in the
2025 data — every state has ≥1 — but kept for safety). Because w_d is decoupled it may sit ABOVE w_o for
some cells; the integrator's signed wage_removed handles that as a uniform net fiscal gain.

The per-cell reabsorbed-at-w_d delta is scenario-invariant given (`reabsorption_floor_pctile`,
`EXPOSURE_PCTILE`), so — like the worker-delta cache — it is built once over all occ×state cells and
persisted to disk (an in-process memo would not survive across pytest processes / app launches, and the
shipped default runs Rung 1).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import loaders
from .integrate import INTERIM, CellIntegrator
from .kernel import KernelParams
from .rates import build_engines
from .transfers import TransferLookup

REAB_CHANNELS = ["inc_fed", "inc_state", "payroll_fed", "cons_state", "transfer_fed", "transfer_state"]
_FILINGS = [("Married filing jointly", "p_mfj", "inc_married_usd"),
            ("Head of household", "p_hoh", "inc_hoh_usd"),
            ("Single", "p_single", "inc_single_usd")]

# Low-exposure work = occupations at/below this national AI-PCA-score percentile. Fixed & non-tunable
# (it defines the service floor, not a scenario knob) — so it is NOT a V2Params lever and the on-disk
# cache key carries only the floor percentile.
EXPOSURE_PCTILE = 0.30


def _weighted_percentile(values, weights, q: float) -> float:
    """Employment-weighted q-quantile (linear interpolation on the weighted CDF midpoints)."""
    v = np.asarray(values, float); w = np.asarray(weights, float)
    keep = np.isfinite(v) & np.isfinite(w) & (w > 0) & (v > 0)
    v, w = v[keep], w[keep]
    if v.size == 0:
        return float("nan")
    order = np.argsort(v)
    v, w = v[order], w[order]
    cum = (np.cumsum(w) - 0.5 * w) / w.sum()
    return float(np.interp(q, cum, v))


def service_floor_by_state(data: loaders.FiscalData, pctile: float = 0.30):
    """Return ({state: w_d}, national_w_d) — the Rung-1 destination wage per state (see module doc)."""
    exp = data.exposure_occ[["soc_code", "ai_pca_score"]].dropna()
    cut = exp["ai_pca_score"].quantile(EXPOSURE_PCTILE)
    low = set(exp.loc[exp["ai_pca_score"] <= cut, "soc_code"])

    o = data.oews.copy()
    wage = o["annual_mean_usd"].where(o["annual_mean_usd"].notna(), o["hourly_mean_usd"] * 2080)
    o = o.assign(wage=wage)
    o = o[o["soc_code"].isin(low) & o["wage"].notna() & (o["employment_persons"] > 0)]

    national = _weighted_percentile(o["wage"], o["employment_persons"], pctile)
    floors = {}
    for state, g in o.groupby("state"):
        wd = _weighted_percentile(g["wage"], g["employment_persons"], pctile)
        floors[state] = wd if np.isfinite(wd) else national
    return floors, national


class ReabsorptionEngine:
    """Live per-run reabsorbed fiscal delta (all 6 channels) at a haircut-driven destination wage
    `w_d = max(origin·(1−haircut), service_floor)`. Unifies the old Rung-0/Rung-1 split into ONE dial:
    haircut=0 → w_d=origin → zero delta (reabsorbed fiscally WHOLE, so full reabsorption doesn't grow the
    deficit); a bigger haircut → deeper cut → income/payroll tax lost AND the means-tested cross-threshold
    fire. Evaluated AT-MEAN per cell (like `survivor.SurvivorEngine` — fast enough to recompute live for
    the UI, no 83s disk cache); the within-cell lognormal integration of the transfer cliffs
    (`integrate_reemployment`) is the higher-fidelity offline path, traded here for interactivity. The
    delta depends only on the haircut, so `delta()` is called ONCE per run and scaled by the reabsorbed
    stock each period."""

    def __init__(self, data, deltas, lookup: TransferLookup, kp: KernelParams, floor_pctile: float = 0.30):
        self.income, self.fica = build_engines(data)
        self._ci = CellIntegrator(data, lookup, kp)      # reuse noc / lookup / consumption / band machinery
        self.mult = kp.marginal_taxable_multiplier
        d = deltas.reset_index(drop=True)
        self.worker_wage = d["worker_wage"].to_numpy(float)
        self.state = d["state"].to_numpy()
        n = len(d)

        hh = data.household[["soc_code", "state", "p_mfj", "p_hoh", "p_single",
                             "inc_married_usd", "inc_hoh_usd", "inc_single_usd"]]
        m = d[["soc_code", "state", "worker_wage"]].merge(hh, on=["soc_code", "state"], how="left")
        assert len(m) == n, "household merge changed row count"
        P = m[["p_mfj", "p_hoh", "p_single"]].to_numpy(float)
        allnan = np.isnan(P).all(axis=1)
        Ps = np.where(np.isnan(P), 0.0, P); tot = Ps.sum(axis=1)
        Wt = Ps / np.where(tot > 0, tot, 1.0)[:, None]; Wt[allnan] = 1.0 / 3.0
        M = m[["inc_married_usd", "inc_hoh_usd", "inc_single_usd"]].to_numpy(float)
        M = np.where(np.isnan(M) | (M <= 0), self.worker_wage[:, None], M)
        self.weight = {f: Wt[:, j] for j, (f, _, _) in enumerate(_FILINGS)}
        self.hh_mean = {f: M[:, j] for j, (f, _, _) in enumerate(_FILINGS)}

        cons = data.consumption.set_index("state")["eff_tax_rate_frac"]
        self.cons_rate = np.array([float(cons.get(s, 0.0)) for s in self.state])
        floors, national = service_floor_by_state(data, floor_pctile)
        self.service_floor = np.array([floors.get(s, national) for s in self.state])
        self._states = sorted(set(self.state))
        self._state_mask = {s: (self.state == s) for s in self._states}
        # children-probability weights per cell per filing, at the (fixed) mean-income band
        self._pk = {}
        for f, _, _ in _FILINGS:
            band = self._ci._band_index(self.hh_mean[f])
            self._pk[f] = np.array([self._ci._noc.get((f, self.state[i], int(band[i])), np.full(4, 0.25))
                                    for i in range(n)])

    def delta(self, haircut: float, mpc: float, stickiness: float) -> dict:
        """Per-worker reabsorbed fiscal loss (6 channels), losses POSITIVE. haircut=0 → all zero."""
        w_d = np.maximum(self.worker_wage * (1.0 - haircut), self.service_floor)
        wage_removed = self.worker_wage - w_d                        # SIGNED (w_d>origin ⇒ a small gain)
        n = len(self.worker_wage)
        inc_fed = np.zeros(n); inc_state = np.zeros(n); payroll = np.zeros(n); emp_fica = np.zeros(n)
        tr_fed = np.zeros(n); tr_state = np.zeros(n)
        for f, _, _ in _FILINGS:
            wt, mean = self.weight[f], self.hh_mean[f]
            lo = np.maximum(mean - wage_removed, 0.0)                # income after removing wage_removed
            inc_fed += wt * (np.asarray(self.income.federal_tax(mean, f), float)
                             - np.asarray(self.income.federal_tax(lo, f), float))
            payroll += wt * (np.asarray(self.fica.fica(self.worker_wage, f), float)
                             - np.asarray(self.fica.fica(w_d, f), float))
            emp_fica += wt * (np.asarray(self.fica.employee_fica(self.worker_wage, f), float)
                              - np.asarray(self.fica.employee_fica(w_d, f), float))
            ks = [0] if f == "Single" else [0, 1, 2, 3]
            for s in self._states:
                idx = np.where(self._state_mask[s])[0]
                if idx.size == 0:
                    continue
                h = mean[idx]; h_after = np.maximum(h - wage_removed[idx], 0.0)
                inc_state[idx] += wt[idx] * (np.asarray(self.income.state_tax(h, s, f), float)
                                             - np.asarray(self.income.state_tax(h_after, s, f), float))
                for k in ks:
                    xs, progs = self._ci.lookup.program_arrays(s, f, k)
                    dfed = np.zeros(idx.size); dstate = np.zeros(idx.size)
                    for prog, ys in progs.items():
                        dprog = np.interp(h_after, xs, ys) - np.interp(h, xs, ys)
                        fs = self._ci.lookup.fed_share.get(prog, 1.0)
                        dfed += dprog * fs; dstate += dprog * (1.0 - fs)
                    pkk = self._pk[f][idx, k]
                    tr_fed[idx] += wt[idx] * pkk * dfed
                    tr_state[idx] += wt[idx] * pkk * dstate
        disp_loss = wage_removed - (inc_fed + inc_state) - emp_fica
        cons = self.cons_rate * self.mult * mpc * stickiness * disp_loss
        return {"inc_fed": inc_fed, "inc_state": inc_state, "payroll_fed": payroll,
                "cons_state": cons, "transfer_fed": tr_fed, "transfer_state": tr_state}


def engine_artifacts_exist() -> bool:
    """True if the artifacts the live `ReabsorptionEngine` needs — the baked benefit lookup and the NOC
    children distribution (both consumed via `CellIntegrator`) — are present. The 83s disk cache is gone
    (the live engine recomputes the reabsorbed delta once per run), so Rung 1 no longer needs a prebuild."""
    return (INTERIM / "benefit_lookup.parquet").exists() and (INTERIM / "noc_distribution.csv").exists()
