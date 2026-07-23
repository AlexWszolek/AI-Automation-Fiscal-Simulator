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
from .rates import build_engines, state_slot_matrices, state_slot_tax
from .transfers import TransferLookup

REAB_CHANNELS = ["inc_fed", "inc_state", "payroll_fed", "cons_state", "transfer_fed", "transfer_state"]
_FILINGS = [("Married filing jointly", "p_mfj", "inc_married_usd"),
            ("Head of household", "p_hoh", "inc_hoh_usd"),
            ("Single", "p_single", "inc_single_usd")]

# Low-exposure work = occupations at/below this national AI-PCA-score percentile. Fixed & non-tunable
# (it defines the service floor, not a scenario knob) — so it is NOT a V2Params lever and the on-disk
# cache key carries only the floor percentile.
EXPOSURE_PCTILE = 0.30


def _interp_rows(xs: np.ndarray, Y: np.ndarray, q: np.ndarray,
                 S: np.ndarray | None = None) -> np.ndarray:
    """np.interp of EVERY row of Y over the shared grid xs at query q — one binary search shared
    by all rows instead of one np.interp call per program. Same formula and edge rules as numpy's
    C loop: slope = (y1−y0)/(x1−x0) then slope·(q−x0)+y0, left edge q<xs[0] → ys[0], right edge
    q≥xs[-1] → ys[-1] (numpy special-cases q==xs[-1] to ys[-1]; the general formula would give
    (ys[-1]−ys[-2])+ys[-2], not bitwise ys[-1]).

    NOT guaranteed bit-identical to np.interp: numpy's compiled kernel may fuse the final
    multiply-add into one rounding (it does on macOS arm64 — verified empirically), which no
    composition of numpy ufuncs can reproduce; the absolute deviation is bounded by ~1 ulp of
    the program's benefit scale, ~1e-12 dollars (pinned in tests/test_reemployment — near
    cancellation points the RELATIVE error can look large while the absolute error stays there).
    It is therefore used ONLY on the wage-dynamics path
    (delta(wage_index≠1) — the per-period Baumol/crowding re-evaluation, which post-dates every
    bit-frozen artifact); the wage_index==1 path keeps calling real np.interp so the legacy
    bit-parity anchors (delta ≡ _delta_loop exact, C8, golden pins, non-Baumol bundles) are
    untouched."""
    nx = xs.size
    if nx == 1:                                    # single-knot grid: np.interp is the constant ys[0]
        return np.repeat(Y[:, :1], q.size, axis=1)
    j = xs.searchsorted(q, side="right") - 1       # xs[j] ≤ q < xs[j+1] for interior q; j ∈ [−1, nx−1]
    np.minimum(j, nx - 2, out=j)                   # integer clamp (np.clip's wrapper is ~6µs/call —
    np.maximum(j, 0, out=j)                        # measurable at ~460 calls per period)
    x0 = xs[j]
    if S is None:
        vals = (Y[:, j + 1] - Y[:, j]) / (xs[j + 1] - x0) * (q - x0) + Y[:, j]
    else:
        # S = the precomputed per-segment slope matrix (Y[:,1:]−Y[:,:-1])/(xs[1:]−xs[:-1]);
        # divide-then-gather ≡ gather-then-divide elementwise, so identical bits, fewer temporaries
        # (np.interp itself precomputes slopes when len(q) ≥ len(xs))
        vals = S[:, j] * (q - x0) + Y[:, j]
    left = q < xs[0]
    if left.any():
        vals[:, left] = Y[:, :1]
    right = q >= xs[-1]
    if right.any():
        vals[:, right] = Y[:, -1:]
    return vals


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


def low_exposure_socs(data: loaders.FiscalData) -> set:
    """The refuge occupations: SOC codes at/below the national EXPOSURE_PCTILE AI-PCA cut. This is
    the work the service floor prices AND the destination the reabsorbed implicitly move into, so
    it is also the base for the finite-refuge capacity check in dynamics_v2."""
    exp = data.exposure_occ[["soc_code", "ai_pca_score"]].dropna()
    cut = exp["ai_pca_score"].quantile(EXPOSURE_PCTILE)
    return set(exp.loc[exp["ai_pca_score"] <= cut, "soc_code"])


def service_floor_by_state(data: loaders.FiscalData, pctile: float = 0.30):
    """Return ({state: w_d}, national_w_d) — the Rung-1 destination wage per state (see module doc)."""
    low = low_exposure_socs(data)

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
    haircut=0 → w_d=origin → zero delta (reabsorbed fiscally WHOLE, so full reabsorption doesn't grow
    the deficit) — EXCEPT cells whose origin wage sits below the service floor, which re-employ AT the
    floor (a small gain: the floor is the going wage for the service work they move into);
    a bigger haircut → deeper cut → income/payroll tax lost AND the means-tested cross-threshold
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

        # ---- vectorized fast path: the draw-INDEPENDENT sides, computed once ----------------
        # Every "before" term in delta()'s pairs is a constant of the engine (household mean,
        # origin wage): federal/state income tax at the mean, FICA at the origin wage, and the
        # transfer interp AT the mean. Hoisting them is bit-safe (same calls, same inputs); the
        # state side additionally moves to the shared padded slot matrices (bit-parity argument
        # in rates.state_slot_matrices). _delta_loop below is the retained reference.
        self._idx = {s: np.where(self._state_mask[s])[0] for s in self._states}
        self._state_slots = state_slot_matrices(self.income, self.state, self._state_mask)
        self._fed_at_mean = {f: np.asarray(self.income.federal_tax(self.hh_mean[f], f), float)
                             for f, _, _ in _FILINGS}
        self._fica_at_wage = {f: np.asarray(self.fica.fica(self.worker_wage, f), float)
                              for f, _, _ in _FILINGS}
        self._efica_at_wage = {f: np.asarray(self.fica.employee_fica(self.worker_wage, f), float)
                               for f, _, _ in _FILINGS}
        self._state_at_mean = {f: state_slot_tax(self._state_slots, self.hh_mean[f], f)
                               for f, _, _ in _FILINGS}
        # per-(filing, state) hoists for the transfer loop: masked weights and the (idx, 4)
        # children-probability block (views per k are then free); value-identical to the
        # reference's per-call fancy indexing
        self._wt_by_state = {(f, s): self.weight[f][self._idx[s]]
                             for f, _, _ in _FILINGS for s in self._states}
        self._pk_by_state = {(f, s): self._pk[f][self._idx[s]]
                             for f, _, _ in _FILINGS for s in self._states}
        # (filing, state, k) -> (xs, Y row-matrix of all program ys, [(fed_share, interp@mean)],
        # fed-share vector, stacked at-mean matrix A). Y/A rows follow the dict's insertion order,
        # so row p ↔ the p-th program exactly as the reference iterates them. The at-mean side
        # stays a real np.interp (hoisted, bit-safe). The legacy wage_index==1 path in delta()
        # consumes (xs, Y, progs) per program — bit-frozen; the wage-dynamics path consumes
        # (xs, Y, fs_vec, A) through _interp_rows + matvec accumulation.
        self._tr = {}
        for f, _, _ in _FILINGS:
            for s in self._states:
                idx = self._idx[s]
                if idx.size == 0:
                    continue
                h = self.hh_mean[f][idx]
                for k in ([0] if f == "Single" else [0, 1, 2, 3]):
                    xs, progs = self._ci.lookup.program_arrays(s, f, k)
                    Y = (np.array([ys for ys in progs.values()], dtype=float)
                         if progs else np.zeros((0, xs.size)))
                    plist = [(self._ci.lookup.fed_share.get(prog, 1.0),
                              np.interp(h, xs, ys)) for prog, ys in progs.items()]
                    fs_vec = np.array([fs for fs, _ in plist])
                    A = (np.vstack([am for _, am in plist])
                         if plist else np.zeros((0, idx.size)))
                    S = ((Y[:, 1:] - Y[:, :-1]) / (xs[1:] - xs[:-1])
                         if xs.size > 1 else np.zeros((Y.shape[0], 0)))
                    self._tr[(f, s, k)] = (xs, Y, plist, fs_vec, A, S)

    def delta(self, haircut: float, mpc: float, stickiness: float,
              wage_index: float = 1.0) -> dict:
        """Per-worker reabsorbed fiscal loss (6 channels), losses POSITIVE. haircut=0 → all zero.

        `wage_index` scales the destination wage (the reabsorbed wage dynamics: Baumol pull /
        crowding pressure, computed per period in dynamics_v2). 1.0 is the exact legacy path;
        an index > 1 can push w_d above the origin wage — the signed wage_removed handles that
        as a fiscal gain, and the transfer interp re-fires the means-tested cliffs at the new
        household income either way.

        Vectorized fast path (bind-time hot spot: ~98ms → ~30ms/draw): all "before" sides come
        from the constants hoisted at construction, state income tax runs on the shared slot
        matrices, and only the after-side transfer interp remains per call. At wage_index==1
        (bind time, every non-Baumol scenario) it calls real np.interp per program and is
        bit-identical to `_delta_loop` (the retained reference), pinned in tests/test_reemployment.
        At wage_index≠1 — the per-period Baumol/crowding re-evaluation, fired ~n_periods times per
        run — the programs of each (filing, state, kids) group share one `_interp_rows` blend
        (one binary search for all rows; ≤1 ulp vs np.interp, see its docstring), pinned with a
        tight-tolerance variant of the same anchor."""
        w_d = np.maximum(self.worker_wage * (1.0 - haircut), self.service_floor)
        if wage_index != 1.0:
            w_d = w_d * wage_index
        wage_removed = self.worker_wage - w_d                        # SIGNED (w_d>origin ⇒ a small gain)
        n = len(self.worker_wage)
        inc_fed = np.zeros(n); inc_state = np.zeros(n); payroll = np.zeros(n); emp_fica = np.zeros(n)
        tr_fed = np.zeros(n); tr_state = np.zeros(n)
        for f, _, _ in _FILINGS:
            wt, mean = self.weight[f], self.hh_mean[f]
            lo = np.maximum(mean - wage_removed, 0.0)                # income after removing wage_removed
            inc_fed += wt * (self._fed_at_mean[f]
                             - np.asarray(self.income.federal_tax(lo, f), float))
            payroll += wt * (self._fica_at_wage[f]
                             - np.asarray(self.fica.fica(w_d, f), float))
            emp_fica += wt * (self._efica_at_wage[f]
                              - np.asarray(self.fica.employee_fica(w_d, f), float))
            inc_state += wt * (self._state_at_mean[f] - state_slot_tax(self._state_slots, lo, f))
            ks = [0] if f == "Single" else [0, 1, 2, 3]
            for s in self._states:
                idx = self._idx[s]
                if idx.size == 0:
                    continue
                h_after = lo[idx]                                    # == max(mean[idx]−wr[idx], 0)
                wt_s, pk_s = self._wt_by_state[(f, s)], self._pk_by_state[(f, s)]
                for k in ks:
                    xs, Y, progs, fs_vec, A, S = self._tr[(f, s, k)]
                    if not progs:
                        # keep the reference's += of exact zeros (skipping could launder a −0.0)
                        dfed = np.zeros(idx.size); dstate = np.zeros(idx.size)
                    elif wage_index != 1.0:
                        # wage-dynamics path: one shared search for all programs, then a matvec
                        # over the P≈7 program rows. The matvec reorders a tiny sum (~1e-15
                        # relative) — inside the wi≠1 tolerance anchor, like _interp_rows itself.
                        D = _interp_rows(xs, Y, h_after, S) - A  # (P, m)
                        dfed = fs_vec @ D
                        dstate = (1.0 - fs_vec) @ D
                    else:                                        # legacy path: bit-frozen np.interp
                        dfed = np.zeros(idx.size); dstate = np.zeros(idx.size)
                        for p, (fs, at_mean) in enumerate(progs):
                            dprog = np.interp(h_after, xs, Y[p]) - at_mean
                            dfed += dprog * fs; dstate += dprog * (1.0 - fs)
                    pkk = pk_s[:, k]
                    tr_fed[idx] += wt_s * pkk * dfed
                    tr_state[idx] += wt_s * pkk * dstate
        disp_loss = wage_removed - (inc_fed + inc_state) - emp_fica
        cons = self.cons_rate * self.mult * mpc * stickiness * disp_loss
        return {"inc_fed": inc_fed, "inc_state": inc_state, "payroll_fed": payroll,
                "cons_state": cons, "transfer_fed": tr_fed, "transfer_state": tr_state,
                "net_takehome_loss": disp_loss - (tr_fed + tr_state)}

    def _delta_loop(self, haircut: float, mpc: float, stickiness: float,
                    wage_index: float = 1.0) -> dict:
        """The original per-state/per-program reference — kept as the parity anchor for delta()
        (the same role mc.run_mc and survivor._delta_loop play). Tests compare bit-for-bit."""
        w_d = np.maximum(self.worker_wage * (1.0 - haircut), self.service_floor)
        if wage_index != 1.0:
            w_d = w_d * wage_index
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
                "cons_state": cons, "transfer_fed": tr_fed, "transfer_state": tr_state,
                # the SIGNED per-worker take-home scar net of the transfers that replace it — the
                # reabsorbed's standing DEMAND withdrawal (consumed by the level-targeting controller;
                # extra key is safe: the fiscal loop iterates the v1 channel names, not this dict)
                "net_takehome_loss": disp_loss - (tr_fed + tr_state)}


def engine_artifacts_exist() -> bool:
    """True if the artifacts the live `ReabsorptionEngine` needs — the baked benefit lookup and the NOC
    children distribution (both consumed via `CellIntegrator`) — are present. The 83s disk cache is gone
    (the live engine recomputes the reabsorbed delta once per run), so Rung 1 no longer needs a prebuild."""
    return (INTERIM / "benefit_lookup.parquet").exists() and (INTERIM / "noc_distribution.csv").exists()
