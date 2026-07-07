"""Monte Carlo — local uncertainty around a chosen lever configuration.

Once the user sets the levers, `sample_draws` produces N slightly-perturbed configs (seeded, constraint-
aware) and `run_mc` runs them through a `ScenarioContext` — a build-once/run-many fast path over
`DynamicModelV2` (~0.15–0.25s/draw vs ~4s cold) — returning percentile FAN paths and a Spearman TORNADO
(which levers drive the final-year headline).

The fast path's validity condition (the repo's C8 discipline applied here): `ScenarioContext.run(v2p)`
must equal `DynamicModelV2(data, deltas, v2p).run()` BIT-FOR-BIT for any whitelisted draw — pinned by
tests/test_mc.py. It holds because the per-draw formulas live only in `DynamicModelV2._bind_params`
(the context just shallow-copies the built template and re-binds).

Sampling rules (see PERTURBED below):
- relative truncated-normal jitter x' = clip(x·(1 + spread·z), lo, hi), z rejection-truncated to ±2σ
  (clipping z would put point mass at the edges and distort the Spearman ranks);
- OFF-STAYS-OFF: a lever at its off value is never perturbed — "slightly different settings" must not
  switch mechanisms on (0 self-preserves under relative jitter; ceiling==1/inf and lag==0 are explicit);
- the three disposition shares are jittered then RENORMALIZED to the simplex; auto_cost is drawn next;
  automation_tax_rate is then clipped to the drawn bound retained'·(1−auto_cost') (0 when the bound
  collapses — e.g. auto_cost→1);
- survivor_elasticity: relative jitter of |x|, sign preserved; survivor_raise_ceiling: jitter the EXCESS
  above 1; ui_weeks: rounded int in [0, 52]; the adoption path is scaled by end'/end (shape preserved),
  capped so max ≤ 1.

CAVEAT (documented, accepted repo-wide): mpc / consumption_stickiness are LIVE in the demand gain, the
state-close contraction, and the rung-1 reabsorption consumption channel, but FROZEN in the cached
displaced-worker consumption channel — their tornado bars reflect only the live paths.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, fields, replace

import numpy as np
import pandas as pd

from . import loaders
from .dynamics_v2 import DynamicModelV2
from .invariants import assert_all_invariants
from .levers_v2 import V2Params

# ---- the perturbation whitelist: lever -> (lo, hi) clip bounds. Everything else is FROZEN. ----------
PERTURBED = {
    "cognitive_feasibility": (0.0, 1.0), "physical_feasibility": (0.0, 1.0),
    "robotics_lag": (0.0, np.inf),
    "ui_weeks": (0, 52),                        # int rule
    "reabsorption_rate": (0.0, 1.0), "reemployment_haircut": (0.0, 1.0),
    "lfp_exit_rate": (0.0, 1.0), "attrition_rate": (0.0, 1.0),
    "survivor_elasticity": (-1.0, 1.0),         # signed rule
    "survivor_raise_ceiling": (1.0, np.inf),    # excess rule; off at 1.0 or inf
    "survivor_spillover_to_profit": (0.0, 1.0),
    "retained_profit_share": (0.0, 1.0), "price_reduction_share": (0.0, 1.0),
    "survivor_gains_share": (0.0, 1.0),         # simplex rule (the three together)
    "auto_cost": (0.0, 1.0), "offshore_share": (0.0, 1.0), "compute_effective_rate": (0.0, 1.0),
    "automation_tax_rate": (0.0, 1.0),          # bound rule (after shares + auto_cost)
    "ubi_recapture_rate": (0.0, 1.0), "baseline_growth_rate": (0.0, 0.10),
    # dm bound tracks the UI slider max (2.0): a (0,1) bound would clip every draw around a preset
    # base of 1.2–1.5 to exactly 1.0 — point mass at the edge, degenerate tornado row. ρ ≈ 0.22·dm
    # stays < 1 even for ±2σ draws around 2.0 (the model's fail-loud guard is the backstop).
    "demand_multiplier": (0.0, 2.0), "price_passthrough": (0.0, 1.0),
    "productivity_passthrough": (0.0, 1.0),
    "mpc": (0.01, 1.0), "consumption_stickiness": (0.01, 1.0),
    "interest_rate": (0.0, 0.10), "ubi_annual": (0.0, np.inf), "ssdi_annual": (0.0, np.inf),
    "state_cut_share": (0.0, 1.0), "state_rate_hike_cap": (0.01, np.inf),
}
_SIMPLEX = ("retained_profit_share", "price_reduction_share", "survivor_gains_share")

# Structural / categorical / frozen fields — a draw must NOT differ from the template on any of these.
# Reasons: categorical (response/rung/mapping/denominator/periods), baked into the shared template
# (consumption_scale in v1.arr; mapping shape in the channel cells; floor pctile + kernel fields in the
# reabsorption engine; dividend/passthrough/marginal_taxable in the worker-delta cache), asserted ==1
# (corporate XOR), or declared-but-inert placeholders (perturbing them adds pure-noise tornado rows).
FROZEN = tuple(f.name for f in fields(V2Params)
               if f.name not in PERTURBED and f.name not in ("adoption_path", "adoption"))


def _truncated_z(rng: np.random.Generator) -> float:
    """Standard normal rejection-truncated to ±2σ (no edge point-mass)."""
    while True:
        z = rng.standard_normal()
        if abs(z) <= 2.0:
            return z


def sample_draws(base: V2Params, n: int, spread: float, seed: int = 0) -> list:
    """N constraint-aware local perturbations of `base` (see the module docstring for the rules)."""
    if spread == 0:
        return [base] * n
    rng = np.random.default_rng(seed)
    j = lambda x: x * (1.0 + spread * _truncated_z(rng))
    draws = []
    for _ in range(n):
        d = {}
        # 1) the disposition simplex (skip degenerate corners like (1,0,0): zeros self-preserve there,
        #    and renormalizing a single jittered survivor returns exactly 1.0)
        shares = np.array([getattr(base, s) for s in _SIMPLEX], float)
        jittered = np.array([j(x) if x > 0 else 0.0 for x in shares])
        tot = jittered.sum()
        if tot > 0:
            for name, val in zip(_SIMPLEX, jittered / tot):
                d[name] = float(val)
        # 2) everything else on the whitelist
        for name, (lo, hi) in PERTURBED.items():
            if name in _SIMPLEX or name == "automation_tax_rate":
                continue
            x = getattr(base, name)
            if name == "survivor_raise_ceiling":
                if x == 1.0 or not np.isfinite(x):
                    continue                                     # off (no raise) or unbounded — keep
                d[name] = max(1.0, 1.0 + (x - 1.0) * (1.0 + spread * _truncated_z(rng)))
            elif name == "survivor_elasticity":
                if x != 0.0:
                    d[name] = float(np.sign(x) * np.clip(j(abs(x)), 0.0, 1.0))
            elif name == "ui_weeks":
                if x != 0:
                    d[name] = int(np.clip(round(j(float(x))), lo, hi))
            elif x != 0.0:                                       # off-stays-off: exact zeros are kept
                d[name] = float(np.clip(j(x), lo, hi))
        # 3) the robot tax, clipped to the DRAWN capacity bound (0 when the bound collapses, e.g.
        #    auto_cost→1 — the fail-loud model assert must be unreachable from the sampler)
        if base.automation_tax_rate > 0:
            bound = (d.get("retained_profit_share", base.retained_profit_share)
                     * (1.0 - d.get("auto_cost", base.auto_cost)))
            d["automation_tax_rate"] = float(np.clip(j(base.automation_tax_rate), 0.0, max(0.0, bound)))
        # 4) the adoption ceiling: scale the whole path (shape preserved), capped so max(path') ≤ 1
        if base.adoption_path is not None:
            path = np.asarray(base.adoption_path, float)
            end = path[-1] if len(path) else 0.0
            if end > 0:
                factor = np.clip(j(end), 1e-6, 1.0) / end
                factor = min(factor, 1.0 / max(path.max(), 1e-9))
                d["adoption_path"] = list(path * factor)
        elif base.adoption > 0:
            d["adoption"] = float(np.clip(j(base.adoption), 1e-6, 1.0))
        draws.append(replace(base, **d))
    return draws


class ScenarioContext:
    """Build-once/run-many wrapper: a template `DynamicModelV2` whose lever-dependent members are
    re-bound per draw. Refuses draws that differ on FROZEN fields (they are baked into the template)."""

    def __init__(self, data: loaders.FiscalData, deltas: pd.DataFrame, base: V2Params):
        self.base = base
        self._template = DynamicModelV2(data, deltas, base)

    def run(self, v2p: V2Params) -> pd.DataFrame:
        for name in FROZEN:
            assert getattr(v2p, name) == getattr(self.base, name), \
                f"'{name}' is structural/frozen in this context — rebuild the context to change it"
        m = copy.copy(self._template)            # shallow: shared arrays are re-bound, never mutated
        m._v1 = copy.copy(self._template._v1)    # v1 gets per-draw p/lp/ui_share/g_cell rebinds
        m._bind_params(v2p)
        return m.run()


# ---- the runner --------------------------------------------------------------------------------------
PATH_COLS = ["fed_deficit_B", "fed_debt_B", "fed_deficit_abs_pct_gdp", "employment_drop_pct",
             "state_gap_B", "induced_M"]
PCTS = (10, 25, 50, 75, 90)


@dataclass
class MCResult:
    draws: pd.DataFrame          # one row per draw: sampled lever values + final-year headlines
    paths: pd.DataFrame          # long: draw × period × PATH_COLS
    percentiles: pd.DataFrame    # long: metric × period × P10/25/50/75/90
    tornado: pd.DataFrame        # lever × spearman ρ vs final deficit / final employment (|ρ|-sorted)
    base_run: pd.DataFrame       # the unperturbed run (the dashed reference line)


def _draw_scalars(v2p: V2Params) -> dict:
    out = {name: float(getattr(v2p, name)) for name in PERTURBED}
    out["adoption_end"] = float(v2p.adoption_path[-1]) if v2p.adoption_path is not None else float(v2p.adoption)
    return out


def run_mc(context: ScenarioContext, n: int = 300, spread: float = 0.15, seed: int = 0,
           progress=None, invariant_every: int = 20) -> MCResult:
    """Run N perturbed draws through the fast path. `progress(i, n)` is called every few draws.
    Every `invariant_every`-th draw (plus draw 0) is checked against the FULL conservation battery."""
    base = context.base
    base_run = context.run(base)
    baseline_M = float(base_run["population_M"].iloc[0])
    draws = sample_draws(base, n, spread, seed)

    rows, path_frames = [], []
    for i, v2p in enumerate(draws):
        try:
            res = context.run(v2p)
            if invariant_every and i % invariant_every == 0:
                assert_all_invariants(res, v2p, baseline_M)
        except AssertionError as e:              # fail loud, with the draw pinned for reproduction
            raise AssertionError(f"MC draw {i} failed: {e}\nlevers: {_draw_scalars(v2p)}") from e
        scal = _draw_scalars(v2p)
        scal.update({"draw": i,
                     "final_fed_deficit_B": float(res["fed_deficit_B"].iloc[-1]),
                     "final_employment_drop_pct": float(res["employment_drop_pct"].iloc[-1])})
        rows.append(scal)
        pf = res[["period"] + PATH_COLS].copy()
        pf["draw"] = i
        path_frames.append(pf)
        if progress and (i % 5 == 0 or i == n - 1):
            progress(i + 1, n)

    draws_df = pd.DataFrame(rows)
    paths = pd.concat(path_frames, ignore_index=True)

    pct_rows = []
    for col in PATH_COLS:
        g = paths.groupby("period")[col]
        for p in PCTS:
            q = g.quantile(p / 100.0)
            pct_rows.append(pd.DataFrame({"metric": col, "period": q.index, "pct": p, "value": q.values}))
    percentiles = pd.concat(pct_rows, ignore_index=True)

    varied = [c for c in PERTURBED if draws_df[c].nunique() > 1]
    if draws_df["adoption_end"].nunique() > 1:
        varied.append("adoption_end")
    tornado_rows = []
    for target in ("final_fed_deficit_B", "final_employment_drop_pct"):
        corr = draws_df[varied + [target]].corr(method="spearman")[target].drop(target)
        tornado_rows.append(pd.DataFrame({"lever": corr.index, "target": target, "spearman": corr.values}))
    tornado = (pd.concat(tornado_rows, ignore_index=True)
               .assign(abs_rho=lambda t: t["spearman"].abs())
               .sort_values(["target", "abs_rho"], ascending=[True, False])
               .drop(columns="abs_rho").reset_index(drop=True))

    return MCResult(draws=draws_df, paths=paths, percentiles=percentiles, tornado=tornado,
                    base_run=base_run)
