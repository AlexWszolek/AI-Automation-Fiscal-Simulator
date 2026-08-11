"""Korea Monte Carlo — joint uncertainty for the fund headlines, reusing mc.py's machinery.

Three uncertainty families, drawn JOINTLY per draw (the direct band varies them one grid
axis at a time; MC answers "and if everything is uncertain at once?"):

- model levers: `mc.sample_draws` around the Korea preset params (same ±spread truncated-z
  rules, disposition simplex, off-stays-off, adoption-path scaling as the US MC);
- wage-linked revenue shares: uniform within their DOCUMENTED bands (korea_scenarios) —
  a projector input, not a model lever, so it perturbs the projection not the run;
- the exposure figure-read: the ±0.5pp grid (korea_exposure.exposure_variant), one
  prebuilt ScenarioContext per variant — exposure lives in the data, not V2Params.

DEMOGRAPHY IS FROZEN at the published medium variant: `demography_path` is structural in
mc.FROZEN, and the fund erosion is defined against the demography-scaled baseline (the
inertness test), so demographic uncertainty is deliberately NOT in the band — the message
is "on the government's own population path", not "and maybe the population is different".

Korea conventions and Korea-inert levers are PINNED back after sampling (KOREA_PINNED):
cognitive/physical feasibility carry the BOK exposure convention (the read error is its own
axis — jittering cf would double-count it, one-sided), robotics_lag has no Korean robot
vector to act on, and the state-closure levers are unused (the gap is reported, never
closed). Pinned fields never reach the tornado — they are constant across draws.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from . import mc
from .invariants import assert_all_invariants
from .korea_assembly import (build_korea_data, build_korea_deltas,
                             korea_erosion_from_run, korea_preset_params,
                             korea_project_funds)
from .korea_exposure import exposure_variant
from .korea_funds import EI_BASELINE, NPS_REFORM
from .korea_scenarios import WAGE_LINKED_SHARE

KOREA_PINNED = ("cognitive_feasibility", "physical_feasibility", "robotics_lag",
                "state_cut_share", "state_rate_hike_cap",
                # US transfer/shareholder levers: they reach only the US-ledger deficit
                # lines, never the fund headlines this MC targets — sampling them adds
                # pure-noise tornado rows (SSDI/UBI-recapture/equity bars at |ρ|≈n^-1/2)
                "ubi_annual", "ubi_recapture_rate", "ssdi_annual",
                "equity_pe_multiple", "equity_taxable_share", "cg_realization_rate",
                "shareholder_eff_rate", "swf_profit_share", "fed_vat_rate")
EXPOSURE_DELTAS = (-0.5, 0.0, 0.5)
HEADLINES = ("nhi_years_forward", "nps_given_back", "ei_shortfall_tn",
             "employment_drop_pct", "nhi_erosion_2035")
PCTS = (10, 25, 50, 75, 90)


@dataclass
class KoreaMCResult:
    draws: pd.DataFrame          # one row per draw: sampled inputs + fund headlines
    percentiles: pd.DataFrame    # headline × P10/25/50/75/90
    tornado: pd.DataFrame        # input × headline Spearman ρ, |ρ|-sorted per headline
    base: dict                   # the unperturbed central headlines (reference row)


def _headline_row(model, res, deltas, nhi_s: float, nps_s: float) -> dict:
    bridge = korea_erosion_from_run(model, res, deltas)
    pr = korea_project_funds(bridge, nhi_s, nps_s)
    return {
        "nhi_years_forward": float(pr["nhi"]["years_pulled_forward"]),
        "nps_given_back": float(pr["nps"]["years_pulled_forward"]),
        "ei_shortfall_tn": float(EI_BASELINE.reserves[-1]
                                 - pr["ei"]["eroded_reserves"][-1]),
        "employment_drop_pct": float(res["employment_drop_pct"].iloc[-1]),
        "nhi_erosion_2035": float(bridge["erosion"]["NHI health"][9]),
    }


def run_korea_mc(n: int = 400, spread: float = 0.15, seed: int = 0,
                 preset: str = "korea-central", invariant_every: int = 20,
                 progress=None, base_params=None, base_axes: dict | None = None,
                 deltas=None, data_pool: dict | None = None,
                 ctx_pool: dict | None = None) -> KoreaMCResult:
    """Serial and deterministic: one lever-draw stream (mc.sample_draws, `seed`), one
    Korea-axes stream (`seed`+1 — separate so adding a lever never reshuffles the share
    draws), fixed draw order. Every `invariant_every`-th draw runs the full conservation
    battery (country="kr").

    `base_params` overrides the preset's V2Params as the sampling centre (the live-tornado
    path: sample around the user's modified config). Sampling of the Korea AXES is always
    the full documented band/grid — a user's point choice doesn't shrink the uncertainty —
    but the reference `base` row uses `base_axes` (exposure_delta/nhi_share/nps_share) so
    it reflects the user's own configuration. `deltas`/`data_pool`/`ctx_pool` amortize
    construction across calls (shared with the webpayload pools — same structural shape)."""
    horizon = len(NPS_REFORM.revenue)
    base = base_params if base_params is not None else korea_preset_params(preset, horizon)
    deltas = deltas if deltas is not None else build_korea_deltas()
    if data_pool is None:
        data_pool = {}
    if ctx_pool is None:
        ctx_pool = {}
    for d in EXPOSURE_DELTAS:
        if d not in data_pool:
            data_pool[d] = build_korea_data(exposure=exposure_variant(d) if d else None)
        if d not in ctx_pool:
            ctx_pool[d] = mc.ScenarioContext(
                data_pool[d], deltas, korea_preset_params("korea-central", horizon))
    contexts = ctx_pool

    lever_draws = mc.sample_draws(base, n, spread, seed)
    pin = {k: getattr(base, k) for k in KOREA_PINNED}
    rng = np.random.default_rng(seed + 1)
    axes = [{"exposure_delta": float(EXPOSURE_DELTAS[rng.integers(0, 3)]),
             "nhi_share": float(rng.uniform(WAGE_LINKED_SHARE["nhi"].low,
                                            WAGE_LINKED_SHARE["nhi"].high)),
             "nps_share": float(rng.uniform(WAGE_LINKED_SHARE["nps"].low,
                                            WAGE_LINKED_SHARE["nps"].high))}
            for _ in range(n)]

    nhi_mid = round((WAGE_LINKED_SHARE["nhi"].low + WAGE_LINKED_SHARE["nhi"].high) / 2, 2)
    nps_mid = round((WAGE_LINKED_SHARE["nps"].low + WAGE_LINKED_SHARE["nps"].high) / 2, 2)
    b_axes = {"exposure_delta": 0.0, "nhi_share": nhi_mid, "nps_share": nps_mid,
              **(base_axes or {})}
    base_model, base_res = contexts[b_axes["exposure_delta"]].run_model(base)
    base_row = _headline_row(base_model, base_res, deltas,
                             b_axes["nhi_share"], b_axes["nps_share"])

    rows = []
    for i, d in enumerate(lever_draws):
        v2p = replace(d, **pin)
        ax = axes[i]
        try:
            model, res = contexts[ax["exposure_delta"]].run_model(v2p)
            if invariant_every and i % invariant_every == 0:
                assert_all_invariants(res, v2p, float(res["population_M"].iloc[0]),
                                      country="kr")
        except (AssertionError, ValueError) as e:
            raise AssertionError(
                f"Korea MC draw {i} failed: {e}\naxes: {ax}") from e
        scal = {name: float(getattr(v2p, name)) for name in mc.PERTURBED
                if name not in KOREA_PINNED}
        scal["adoption_end"] = float(v2p.adoption_path[-1])
        scal.update(ax)
        scal["draw"] = i
        scal.update(_headline_row(model, res, deltas, ax["nhi_share"], ax["nps_share"]))
        rows.append(scal)
        if progress and (i % 5 == 0 or i == n - 1):
            progress(i + 1, n)

    draws_df = pd.DataFrame(rows)
    pct = pd.DataFrame(
        [{"headline": h, "pct": p, "value": float(np.percentile(draws_df[h], p))}
         for h in HEADLINES for p in PCTS])
    inputs = [c for c in draws_df.columns
              if c not in HEADLINES and c != "draw" and draws_df[c].nunique() > 1]
    trows = []
    for h in HEADLINES:
        corr = draws_df[inputs + [h]].corr(method="spearman")[h].drop(h)
        trows.append(pd.DataFrame({"input": corr.index, "headline": h,
                                   "spearman": corr.values}))
    tornado = (pd.concat(trows, ignore_index=True)
               .assign(abs_rho=lambda t: t["spearman"].abs())
               .sort_values(["headline", "abs_rho"], ascending=[True, False])
               .drop(columns="abs_rho").reset_index(drop=True))
    return KoreaMCResult(draws=draws_df, percentiles=pct, tornado=tornado, base=base_row)
