"""The Korea ScenarioPayload — one function behind both the static Korea bundles and the
live /api/korea/run path, so static ≡ live by construction (the US webpayload discipline).

Shape notes against the US payload:
- `rows` carries the SAME engine result columns (same engine), so the US timeSeries chart
  battery reads Korea rows unchanged — units are ₩bn where the US has $bn, labeled by copy;
- `funds` sits where `states` sits for the US: per-fund published vs eroded reserve paths
  WITH an uncertainty envelope, plus the depletion headlines — recomputed live per config
  (the envelope is 3 exposure-variant runs × 4 share-edge projections, ~100ms warm);
- one 40-year run serves everything: `rows` is sliced to the preset's display horizon and
  the funds always project the full NPS window (the prefix property — a 40-year run's first
  N periods equal the N-year run bit-for-bit — is pinned in tests);
- the Korea axes (wage-linked shares, exposure read) are first-class levers here even
  though they are not V2Params fields: shares act at the projector, exposure at the data.

Levers are sanitized against KOREA_LEVER_SPECS (clamp, drop junk) — a hand-crafted request
can never 500 the model. The Korea conventions (cognitive-only, frozen demography, no
closure) are baked by korea_preset_params and are NOT reachable from levers.
"""
from __future__ import annotations

import numpy as np

from . import mc as mc_mod
from .korea_assembly import (build_korea_data, build_korea_deltas,
                             korea_erosion_from_run, korea_preset_params,
                             korea_project_funds)
from .korea_exposure import exposure_variant
from .korea_funds import EI_BASELINE, NHI_REFORM, NPS_REFORM, first_negative_year
from .korea_scenarios import KOREA_PRESETS, WAGE_LINKED_SHARE

HORIZON = len(NPS_REFORM.revenue)                    # 40 — the NPS projection window
EXPOSURE_DELTAS = (-0.5, 0.0, 0.5)
NHI_MID = round((WAGE_LINKED_SHARE["nhi"].low + WAGE_LINKED_SHARE["nhi"].high) / 2, 2)
NPS_MID = round((WAGE_LINKED_SHARE["nps"].low + WAGE_LINKED_SHARE["nps"].high) / 2, 2)

# The rail's whitelist: lever -> (lo, hi) clamp bounds. Model levers reuse mc.PERTURBED's
# bounds (single source); the Korea-pinned conventions and US-only levers are NOT here, so
# they are unreachable. adoption_end scales the preset path shape-preserved (the MC rule).
_MODEL_LEVERS = ("reabsorption_rate", "reemployment_haircut", "lfp_exit_rate",
                 "attrition_rate", "survivor_elasticity", "retained_profit_share",
                 "price_reduction_share", "productivity_passthrough", "price_passthrough",
                 "demand_multiplier", "mpc", "consumption_stickiness", "ui_weeks",
                 "auto_cost", "interest_rate", "baseline_growth_rate")
KOREA_LEVER_SPECS: dict[str, tuple] = {
    **{k: mc_mod.PERTURBED[k] for k in _MODEL_LEVERS},
    "adoption_end": (0.005, 1.0),
    "nhi_share": (WAGE_LINKED_SHARE["nhi"].low, WAGE_LINKED_SHARE["nhi"].high),
    "nps_share": (WAGE_LINKED_SHARE["nps"].low, WAGE_LINKED_SHARE["nps"].high),
    "exposure_delta": (-0.5, 0.5),
}
_INT_LEVERS = {"ui_weeks"}


def sanitize_korea_config(body: dict) -> dict:
    """{"preset", "levers"} → resolved config. Unknown levers and junk values are DROPPED,
    known values clamped to spec bounds; exposure_delta snaps to the read-error grid."""
    preset = body.get("preset")
    if preset not in KOREA_PRESETS:
        preset = "korea-central"
    levers: dict[str, float] = {}
    raw = body.get("levers") or {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            spec = KOREA_LEVER_SPECS.get(str(k))
            if spec is None:
                continue
            try:
                x = float(v)
            except (TypeError, ValueError):
                continue
            if not np.isfinite(x):
                continue
            x = float(np.clip(x, spec[0], spec[1]))
            if k == "exposure_delta":
                x = min(EXPOSURE_DELTAS, key=lambda d: abs(d - x))
            if k in _INT_LEVERS:
                x = int(round(x))
            levers[str(k)] = x
    return {"preset": preset, "levers": levers}


def _korea_v2p(preset: str, levers: dict):
    """Preset params + sanitized model levers, with the two derived rules the sampler also
    follows: the disposition simplex remainder and shape-preserved adoption-path scaling."""
    model_levers = {k: v for k, v in levers.items() if k in _MODEL_LEVERS}
    v2p = korea_preset_params(preset, HORIZON, **model_levers)
    if "adoption_end" in levers:
        path = np.asarray(v2p.adoption_path, float)
        end = float(path[-1])
        if end > 0:
            factor = min(levers["adoption_end"] / end, 1.0 / max(float(path.max()), 1e-9))
            from dataclasses import replace
            v2p = replace(v2p, adoption_path=list(path * factor),
                          adoption=float(path[-1] * factor))
    return v2p


def _fund_json(fund, proj, lo: np.ndarray, hi: np.ndarray) -> dict:
    return {
        "years": list(fund.years),
        "published": [round(float(v), 2) for v in fund.reserves],
        "eroded": [round(float(v), 2) for v in proj["eroded_reserves"]],
        "eroded_lo": [round(float(v), 2) for v in lo],
        "eroded_hi": [round(float(v), 2) for v in hi],
        "published_depletion": first_negative_year(fund.reserves, fund.base_year),
        # EI is a shortfall story, not a depletion story: its path never crosses zero on
        # the published window, so both shift fields are honestly null there
        "years_pulled_forward": round(float(proj["years_pulled_forward"]), 2)
        if proj.get("years_pulled_forward") is not None else None,
        "eroded_date": round(float(proj["eroded_date"]), 2)
        if proj.get("eroded_date") is not None else None,
        "source": fund.source,
    }


def build_korea_scenario_payload(cfg: dict, data_pool: dict | None = None,
                                 deltas=None, ctx_pool: dict | None = None) -> dict:
    """cfg comes from sanitize_korea_config. `data_pool` ({exposure_delta: KoreaFiscalData})
    and `ctx_pool` ({exposure_delta: ScenarioContext}) amortize construction across requests
    — pass module-level dicts from the API; None rebuilds everything (scripts, tests)."""
    preset_key, levers = cfg["preset"], cfg["levers"]
    preset = KOREA_PRESETS[preset_key]
    display_n = preset.n_periods
    nhi_s = levers.get("nhi_share", NHI_MID)
    nps_s = levers.get("nps_share", NPS_MID)
    user_delta = levers.get("exposure_delta", 0.0)

    deltas = deltas if deltas is not None else build_korea_deltas()
    if data_pool is None:
        data_pool = {}
    if ctx_pool is None:
        ctx_pool = {}
    base = korea_preset_params("korea-central", HORIZON)   # one structural shape for all runs
    v2p = _korea_v2p(preset_key, levers)
    bridges = {}
    for d in EXPOSURE_DELTAS:
        if d not in data_pool:
            data_pool[d] = build_korea_data(exposure=exposure_variant(d) if d else None)
        if d not in ctx_pool:
            ctx_pool[d] = mc_mod.ScenarioContext(data_pool[d], deltas, base)
        model, res = ctx_pool[d].run_model(v2p)
        bridges[d] = korea_erosion_from_run(model, res, deltas)
        if d == user_delta:
            user_res = res

    central = korea_project_funds(bridges[user_delta], nhi_s, nps_s)
    grid = [korea_project_funds(b, ns, ps)
            for b in bridges.values()
            for ns in (WAGE_LINKED_SHARE["nhi"].low, WAGE_LINKED_SHARE["nhi"].high)
            for ps in (WAGE_LINKED_SHARE["nps"].low, WAGE_LINKED_SHARE["nps"].high)]
    envelope = {
        k: (np.min([g[k]["eroded_reserves"] for g in grid], axis=0),
            np.max([g[k]["eroded_reserves"] for g in grid], axis=0))
        for k in ("nhi", "nps", "ei")}

    rows = user_res.iloc[:display_n].round(4).to_dict("records")
    final = user_res.iloc[display_n - 1]
    bridge = bridges[user_delta]
    jobs_lost_M = float(final["population_M"] - final["employed_M"]
                        - final["reabsorbed_M"] - final["retired_M"])

    default_axes = {"nhi_share": NHI_MID, "nps_share": NPS_MID, "exposure_delta": 0.0}
    pp = korea_preset_params(preset_key, HORIZON)
    modified = sorted(
        [k for k, v in levers.items()
         if k in _MODEL_LEVERS and v != getattr(pp, k)]
        + [k for k, v in levers.items()
           if k in default_axes and v != default_axes[k]]
        + (["adoption_end"] if "adoption_end" in levers
           and levers["adoption_end"] != float(pp.adoption_path[-1]) else []))

    return {
        "config": {
            "country": "kr", "preset": preset_key, "levers": levers,
            "start_year": 2026, "display_periods": display_n, "horizon": HORIZON,
            "modified_fields": modified,
            "conventions": "cognitive channel only; demography frozen (published medium "
                           "variant); fiscal gap reported, never closed",
        },
        "rows": rows,
        "final": {
            "jobs_lost_M": round(jobs_lost_M, 4),
            "employment_drop_pct": round(float(final["employment_drop_pct"]), 4),
            "fed_deficit_B": round(float(final["fed_deficit_B"]), 4),      # ₩bn
            "W_survivor": round(float(final["W_survivor"]), 6),
            "nhi_years_forward": round(float(central["nhi"]["years_pulled_forward"]), 2),
            "nps_given_back": round(float(central["nps"]["years_pulled_forward"]), 2),
            "ei_shortfall_tn": round(float(EI_BASELINE.reserves[-1]
                                           - central["ei"]["eroded_reserves"][-1]), 1),
        },
        "funds": {
            "nhi": _fund_json(NHI_REFORM, central["nhi"], *envelope["nhi"]),
            "nps": _fund_json(NPS_REFORM, central["nps"], *envelope["nps"]),
            "ei": _fund_json(EI_BASELINE, central["ei"], *envelope["ei"]),
        },
        "composition_2035": {k: round(float(v[9]), 4)
                             for k, v in bridge["erosion"].items()},
        "ei_outlay_tn": [round(float(v) / 1000.0, 3)
                         for v in bridge["ei_outlay_bn"][:len(EI_BASELINE.years)]],
        "band_note": "envelope = exposure read ±0.5pp × wage-linked share band edges at "
                     "the CURRENT lever settings (12 projections over 3 runs); preset "
                     "spread lives in the preset picker, not this envelope",
    }


def korea_mc_tornado(cfg: dict, n: int = 150, seed: int = 0,
                     data_pool: dict | None = None, deltas=None,
                     ctx_pool: dict | None = None) -> dict:
    """The tornado behind the site's sensitivity section: Spearman rank correlations from a
    Korea MC sampled around THIS config (the US site's form, served synchronously — the
    Korea engine is fast enough to skip the job queue). The axes always sweep their full
    documented bands; the base row reflects the user's own settings."""
    from .korea_mc import HEADLINES, run_korea_mc

    preset_key, levers = cfg["preset"], cfg["levers"]
    base_axes = {k: levers[k] for k in ("exposure_delta", "nhi_share", "nps_share")
                 if k in levers}
    r = run_korea_mc(n=n, spread=0.15, seed=seed, preset=preset_key,
                     base_params=_korea_v2p(preset_key, levers), base_axes=base_axes,
                     deltas=deltas, data_pool=data_pool, ctx_pool=ctx_pool,
                     invariant_every=0)
    return {
        "config": {"preset": preset_key, "levers": levers, "n": n, "seed": seed,
                   "spread": 0.15},
        "base": {k: round(float(v), 4) for k, v in r.base.items()},
        "targets": {
            h: [{"lever": row.input, "spearman": round(float(row.spearman), 4)}
                for row in r.tornado[r.tornado.headline == h].itertuples()]
            for h in HEADLINES},
    }
