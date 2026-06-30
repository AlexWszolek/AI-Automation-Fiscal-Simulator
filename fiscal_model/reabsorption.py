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
from .transfers import TransferLookup

REAB_CHANNELS = ["inc_fed", "inc_state", "payroll_fed", "cons_state", "transfer_fed", "transfer_state"]

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


def cache_path(pctile: float):
    return INTERIM / f"reab_rung1_deltas_p{int(round(pctile * 100))}.parquet"


def load_or_build_rung1_deltas(data: loaders.FiscalData, lookup: TransferLookup, kp: KernelParams,
                               pctile: float = 0.30, force: bool = False) -> pd.DataFrame:
    """Per (soc, state) permanent reabsorbed-at-w_d fiscal delta — all six channels, Rung 1.
    Scenario-invariant given (pctile, EXPOSURE_PCTILE) → cached on disk (mirrors the worker-delta cache)."""
    path = cache_path(pctile)
    if path.exists() and not force:
        return pd.read_parquet(path)

    floors, national = service_floor_by_state(data, pctile)
    ci = CellIntegrator(data, lookup, kp)
    emp = data.oews.groupby(["soc_code", "state"])["employment_persons"].sum()
    rows = []
    for (soc, state), employed in emp.items():
        if pd.isna(employed) or employed <= 0:
            continue
        w_d = floors.get(state, national)
        fd = ci.integrate_reemployment(soc, state, w_d)
        if fd is None:
            continue
        rows.append({"soc_code": soc, "state": state, "dest_wage": float(w_d),
                     "inc_fed": fd.lost_income_tax_fed, "inc_state": fd.lost_income_tax_state,
                     "payroll_fed": fd.lost_payroll_fed, "cons_state": fd.lost_consumption_tax_state,
                     "transfer_fed": fd.gained_outlays_fed, "transfer_state": fd.gained_outlays_state})
    df = pd.DataFrame(rows)
    INTERIM.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return df


if __name__ == "__main__":
    data = loaders.load_all()
    print("building reabsorption Rung-1 per-cell deltas (cached after first run)...")
    df = load_or_build_rung1_deltas(data, TransferLookup(), KernelParams(), pctile=0.30, force=True)
    floors, national = service_floor_by_state(data, 0.30)
    print(f"  {len(df):,} cells; national service floor w_d ≈ ${national:,.0f}")
    print(f"  cache → {cache_path(0.30)}")
