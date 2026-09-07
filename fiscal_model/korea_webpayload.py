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
from .korea_region import national_labour_force
from .korea_overlays import NPS_MANDATE_PROFIT_SHARE
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
                 "auto_cost", "baseline_growth_rate",
                 "reab_wage_baumol", "reab_wage_crowding", "compute_effective_rate",
                 "survivor_raise_ceiling",
                 "automation_tax_rate",
                 "income_tax_mult", "corp_tax_mult", "cons_tax_mult")
# Delisted from the rail (diplomat review, 2026-08): interest_rate moves only the debt
# columns, which no Korea chart plots, and survivor_spillover_to_profit acts only when
# the survivor-raise ceiling binds, which no rail-reachable config makes it do. Both stay
# engine params (presets and the tornado's sampler still see them); they are simply not
# accepted from the web. reemployment_haircut stays: inert in the diffusion family
# because re-employment wages already sit at the service floor there, live elsewhere.
_MULTS = ("income_tax_mult", "corp_tax_mult", "cons_tax_mult")
KOREA_LEVER_SPECS: dict[str, tuple] = {
    **{k: mc_mod.PERTURBED[k] for k in _MODEL_LEVERS if k not in _MULTS},
    **{k: (0.5, 1.5) for k in _MULTS},           # the US rail's bounds; FROZEN in MC, so
                                                 # not in PERTURBED — contexts key on them
    "survivor_raise_ceiling": (1.0, 3.0),        # PERTURBED's hi is inf; the slider needs one
    "adoption_start": (0.0, 0.5),
    "adoption_end": (0.005, 1.0),
    "demography_variant": (-1.0, 1.0),           # select: -1 low / 0 medium / +1 high
    # policy levers (all default 0 = off; pristine numbers never move):
    "vat_pp": (0.0, 5.0),                        # statutory VAT points, engine-calibrated
    "nps_mandate_share": (0.0, 0.5),             # NPS share of after-tax automation profit
    "corp_to_funds": (0.0, 1.0),                 # automation corp recapture → the funds
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
            if k == "demography_variant":
                x = float(round(x))                       # snap to the published scenarios
            if k in _INT_LEVERS:
                x = int(round(x))
            levers[str(k)] = x
    # legacy: the overlay checkboxes became levers — old shared links keep their meaning
    raw_ov = body.get("overlays") or []
    if isinstance(raw_ov, list):
        if "kr-vat" in raw_ov and "vat_pp" not in levers:
            levers["vat_pp"] = 1.0
        if "kr-nps-mandate" in raw_ov and "nps_mandate_share" not in levers:
            levers["nps_mandate_share"] = NPS_MANDATE_PROFIT_SHARE
    return {"preset": preset, "levers": levers}


_DEMO_VARIANTS = {-1.0: "low", 0.0: "medium", 1.0: "high"}


def _korea_v2p(preset: str, levers: dict):
    """Preset params + sanitized model levers, with the two derived rules the sampler also
    follows: the disposition simplex remainder and shape-preserved adoption-path scaling.
    The vat_pp policy lever maps through the receipts-calibrated statutory→engine rate;
    the other policy levers act at the projector, not here."""
    from .levers_v2 import DEFAULTS_SHIPPED

    model_levers = {k: v for k, v in levers.items() if k in _MODEL_LEVERS}
    # The disposition simplex is a JOINT constraint the per-lever clamps can't see: a user
    # retained/price pair summing past 1 makes the derived survivor remainder 0 and the
    # engine's simplex guard raise (a 500 an adversarial pass reproduced). Apply the US
    # rail's rule — retained wins, price clamps to the remainder — against the preset's
    # own effective values, so a single-lever request can never oversubscribe the simplex.
    ov = KOREA_PRESETS[preset].overrides
    ret = model_levers.get("retained_profit_share",
                           ov.get("retained_profit_share",
                                  DEFAULTS_SHIPPED.retained_profit_share))
    pri = model_levers.get("price_reduction_share",
                           ov.get("price_reduction_share",
                                  DEFAULTS_SHIPPED.price_reduction_share))
    if ret + pri > 1.0:
        model_levers["price_reduction_share"] = max(0.0, 1.0 - ret)
    # reabsorption + LFP-exit is the second joint constraint the per-lever clamps can't
    # see (workers.py asserts the pair sums ≤ 1). Same shape as the simplex rule above:
    # the rate the user pushed wins, the exit rate clamps to the remainder.
    reab = model_levers.get("reabsorption_rate",
                            ov.get("reabsorption_rate", DEFAULTS_SHIPPED.reabsorption_rate))
    lfe = model_levers.get("lfp_exit_rate",
                           ov.get("lfp_exit_rate", DEFAULTS_SHIPPED.lfp_exit_rate))
    if reab + lfe > 1.0:
        model_levers["lfp_exit_rate"] = max(0.0, 1.0 - reab)
    # the robot tax's capacity bound (the sampler's rule): it is paid out of retained
    # profit net of compute costs, so clamp to retained × (1 − auto_cost)
    if "automation_tax_rate" in model_levers:
        ac = model_levers.get("auto_cost", ov.get("auto_cost", DEFAULTS_SHIPPED.auto_cost))
        model_levers["automation_tax_rate"] = min(
            model_levers["automation_tax_rate"], max(0.0, ret * (1.0 - ac)))
    if levers.get("vat_pp", 0.0) > 0:
        from .korea_overlays import kr_vat_engine_rate
        model_levers["fed_vat_rate"] = kr_vat_engine_rate(levers["vat_pp"] / 100.0)
    variant = _DEMO_VARIANTS[levers.get("demography_variant", 0.0)]
    v2p = korea_preset_params(preset, HORIZON, demography_variant=variant, **model_levers)
    if "adoption_start" in levers or "adoption_end" in levers:
        # rebuild the path parametrically with the preset's own reach semantics (linear to
        # the reach year, flat after) — same shape family as build_adoption_path
        from dataclasses import replace
        path = np.asarray(v2p.adoption_path, float)
        start = float(levers.get("adoption_start", path[0]))
        end = max(float(levers.get("adoption_end", path[-1])), start)
        pre = KOREA_PRESETS[preset]
        reach = pre.adoption_reach_year if pre.adoption_reach_year is not None else HORIZON - 1
        ramp = np.linspace(start, end, reach + 1)
        path2 = np.clip(np.concatenate(
            [ramp, np.full(max(0, HORIZON - reach - 1), end)])[:HORIZON], 0.0, 1.0)
        v2p = replace(v2p, adoption_path=list(path2), adoption=float(path2[-1]))
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
    assert user_delta in EXPOSURE_DELTAS, \
        f"exposure_delta {user_delta} off the read grid — cfg must come from sanitize"

    deltas = deltas if deltas is not None else build_korea_deltas()
    if data_pool is None:
        data_pool = {}
    if ctx_pool is None:
        ctx_pool = {}
    # demography_path is FROZEN into a context template, so contexts key on
    # (exposure variant, demography variant) — built lazily, ≤9 ever
    demo_variant = _DEMO_VARIANTS[levers.get("demography_variant", 0.0)]
    mults = {k: levers[k] for k in _MULTS if k in levers}
    mandate_share = levers.get("nps_mandate_share", 0.0)
    corp_share = levers.get("corp_to_funds", 0.0)
    v2p = _korea_v2p(preset_key, levers)
    runs = {}
    for d in EXPOSURE_DELTAS:
        if d not in data_pool:
            data_pool[d] = build_korea_data(exposure=exposure_variant(d) if d else None)
        # the tax mults are FROZEN template fields (the US pool keys on them too) — a
        # mult-modified config gets its own context, keyed alongside exposure and variant
        ckey = (d, demo_variant, tuple(sorted(mults.items())))
        if ckey not in ctx_pool:
            ctx_pool[ckey] = mc_mod.ScenarioContext(
                data_pool[d], deltas,
                korea_preset_params("korea-central", HORIZON,
                                    demography_variant=demo_variant, **mults))
        model, res = ctx_pool[ckey].run_model(v2p)
        # the two projector-level policy flows, from THIS run's own engine outputs:
        # the mandate is share × after-tax undistributed automation profit (never through
        # the treasury); the transfer is share × automation-attributable corporate
        # recapture (corp offset + compute-pool tax + overflow corp tax), FROM the treasury
        mandate_tn = (mandate_share * res["shareholder_undist_B"].to_numpy(float) / 1000.0
                      if mandate_share > 0 else None)
        transfer_tn = (corp_share * (res["corp_offset_B"].to_numpy(float)
                                     + res["compute_pool_tax_B"].to_numpy(float)
                                     + res["survivor_overflow_corp_tax_B"].to_numpy(float))
                       / 1000.0 if corp_share > 0 else None)
        runs[d] = {"bridge": korea_erosion_from_run(model, res, deltas),
                   "mandate_tn": mandate_tn, "transfer_tn": transfer_tn}
        if d == user_delta:
            user_res = res

    bridges = {d: r["bridge"] for d, r in runs.items()}
    ur = runs[user_delta]
    central = korea_project_funds(ur["bridge"], nhi_s, nps_s,
                                  nps_inflows_tn=ur["mandate_tn"],
                                  fund_transfer_tn=ur["transfer_tn"])
    grid = [korea_project_funds(r["bridge"], ns, ps,
                                nps_inflows_tn=r["mandate_tn"],
                                fund_transfer_tn=r["transfer_tn"])
            for r in runs.values()
            for ns in (WAGE_LINKED_SHARE["nhi"].low, WAGE_LINKED_SHARE["nhi"].high)
            for ps in (WAGE_LINKED_SHARE["nps"].low, WAGE_LINKED_SHARE["nps"].high)]
    envelope = {
        k: (np.min([g[k]["eroded_reserves"] for g in grid], axis=0),
            np.max([g[k]["eroded_reserves"] for g in grid], axis=0))
        for k in ("nhi", "nps", "ei")}

    rows = user_res.iloc[:display_n].round(4).to_dict("records")
    final = user_res.iloc[display_n - 1]
    # the corporate-recapture transfer comes FROM the treasury: the reported deficit
    # worsens by exactly the transferred amount while the funds gain it (conservation is
    # test-pinned). Applied to the payload's display copies, never the engine output.
    deficit_raw_final = float(final["fed_deficit_B"])
    if ur["transfer_tn"] is not None:
        tr_bn = ur["transfer_tn"] * 1000.0
        for i, r in enumerate(rows):
            r["fed_deficit_B"] = round(r["fed_deficit_B"] + tr_bn[i], 4)
            r["fed_deficit_abs_B"] = round(r["fed_deficit_abs_B"] + tr_bn[i], 4)
    disp = user_res.iloc[:display_n]
    lf = national_labour_force()
    # displaced still IN the labour force: the UI window + exhausted + demand-shortfall
    # layoffs; exited/retired left it. Mechanical translation against the same survey
    # frame as the map (지역별고용조사 sheet 1), disclosed as such.
    u_uplift_pp = (100.0 * (float(final["on_ui_M"]) + float(final["exhausted_M"])
                            + float(final["induced_M"])) * 1e6
                   / (lf["labour_force_k"] * 1e3))
    bridge = bridges[user_delta]
    jobs_lost_M = float(final["population_M"] - final["employed_M"]
                        - final["reabsorbed_M"] - final["retired_M"])

    default_axes = {"nhi_share": NHI_MID, "nps_share": NPS_MID, "exposure_delta": 0.0,
                    "demography_variant": 0.0, "vat_pp": 0.0,
                    "nps_mandate_share": 0.0, "corp_to_funds": 0.0}
    pp = korea_preset_params(preset_key, HORIZON)
    modified = sorted(
        [k for k, v in levers.items()
         if k in _MODEL_LEVERS and v != getattr(pp, k)]
        + [k for k, v in levers.items()
           if k in default_axes and v != default_axes[k]]
        + (["adoption_end"] if "adoption_end" in levers
           and levers["adoption_end"] != float(pp.adoption_path[-1]) else []))

    # policy readouts. The charts and heroes already REFLECT the policy levers (they run
    # through the projector); the readouts state each lever's own ledger, including the
    # no-policy comparison, computed with one extra projector call (never an engine run).
    policy_readouts = []
    any_policy = (levers.get("vat_pp", 0) > 0 or mandate_share > 0 or corp_share > 0)
    nopolicy = (korea_project_funds(ur["bridge"], nhi_s, nps_s) if any_policy else central)
    if levers.get("vat_pp", 0) > 0:
        vat_final = float(final["fed_vat_B"]) / 1000.0
        # the widening WITHOUT the vat: fed_vat enters net_fed linearly as revenue,
        # so adding it back recovers the no-vat deficit exactly — no second run
        gap_final = deficit_raw_final / 1000.0 + vat_final
        policy_readouts.append({
            "key": "vat_pp", "pp": levers["vat_pp"],
            "revenue_final_tn": round(vat_final, 2),
            "deficit_widening_final_tn": round(gap_final, 2),
            "coverage_pct": round(100.0 * vat_final / gap_final, 1)
            if gap_final > 0.05 else None,
        })
    if mandate_share > 0:
        policy_readouts.append({
            "key": "nps_mandate_share", "share": mandate_share,
            "flow_final_tn": round(float(ur["mandate_tn"][-1]), 2),
            "given_back_nopolicy": round(float(nopolicy["nps"]["years_pulled_forward"]), 2),
            "years_bought_back": round(
                float(nopolicy["nps"]["years_pulled_forward"]
                      - central["nps"]["years_pulled_forward"]), 2),
        })
    if corp_share > 0:
        tr = ur["transfer_tn"]
        policy_readouts.append({
            "key": "corp_to_funds", "share": corp_share,
            "transfer_final_tn": round(float(tr[display_n - 1]), 2),
            "transfer_cum_tn": round(float(tr[:display_n].sum()), 2),
            "nps_years_recovered": round(
                float(nopolicy["nps"]["years_pulled_forward"]
                      - central["nps"]["years_pulled_forward"]), 2),
            "nhi_years_recovered": round(
                float(nopolicy["nhi"]["years_pulled_forward"]
                      - central["nhi"]["years_pulled_forward"]), 2),
            "ei_shortfall_recovered_tn": round(
                float(central["ei"]["eroded_reserves"][-1]
                      - nopolicy["ei"]["eroded_reserves"][-1]), 2),
            "deficit_cost_final_tn": round(float(tr[display_n - 1]), 2),
        })

    return {
        "config": {
            "country": "kr", "preset": preset_key, "levers": levers,
            "start_year": 2026, "display_periods": display_n, "horizon": HORIZON,
            "modified_fields": modified,
            "conventions": ("The model covers cognitive work only. Demography follows "
                            f"the published KOSIS {demo_variant} scenario"
                            + (", which varies the model's workforce path only, since the "
                               "published fund baselines embed NABO's own demographic "
                               "assumptions" if demo_variant != "medium" else "")
                            + ". The fiscal gap is reported and never closed."),
        },
        "rows": rows,
        "final": {
            "jobs_lost_M": round(jobs_lost_M, 4),
            "employment_drop_pct": round(float(final["employment_drop_pct"]), 4),
            "fed_deficit_B": round(deficit_raw_final
                                   + (float(ur["transfer_tn"][display_n - 1]) * 1000.0
                                      if ur["transfer_tn"] is not None else 0.0), 4),  # ₩bn
            "W_survivor": round(float(final["W_survivor"]), 6),
            "nhi_years_forward": round(float(central["nhi"]["years_pulled_forward"]), 2),
            "nps_given_back": round(float(central["nps"]["years_pulled_forward"]), 2),
            "ei_shortfall_tn": round(float(EI_BASELINE.reserves[-1]
                                           - central["ei"]["eroded_reserves"][-1]), 1),
            "inc_tax_lost_cum_tn": round(float(disp["inc_fed_loss_B"].sum()
                                               + disp["inc_state_loss_B"].sum()) / 1000.0, 2),
            "contrib_lost_cum_tn": round(float(disp["payroll_fed_loss_B"].sum()) / 1000.0, 2),
            "ei_outlay_cum_tn": round(float(bridge["ei_outlay_bn"][:display_n].sum())
                                      / 1000.0, 2),
            "u_uplift_pp": round(u_uplift_pp, 2),
            "u_base_pct": round(lf["u_rate_pct"], 1),
            # the demographic decomposition: what the population path removes by itself vs
            # what automation removes on top (the drop is measured AGAINST that baseline)
            "demo_decline_pct": round(
                100.0 * (1.0 - v2p.demography_path[display_n - 1]), 2),
            "demo_variant": demo_variant,
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
        "policy_readouts": policy_readouts,
        "band_note": "The envelope combines the exposure reading and the wage-linked "
                     "share bands at the current lever settings. Spread across scenarios "
                     "lives in the preset picker, not in this envelope.",
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
    # the tax mults are static LEDGER scoring (they cannot move the five targets) and the
    # policy levers (vat_pp / nps_mandate_share / corp_to_funds) are policy CHOICES, not
    # model uncertainty — the tornado deliberately samples the PRE-POLICY model, so all
    # are stripped from the sampling base (documented in the caption's framing)
    _POLICY = ("vat_pp", "nps_mandate_share", "corp_to_funds")
    levers = {k: v for k, v in levers.items() if k not in _MULTS and k not in _POLICY}
    variant = _DEMO_VARIANTS[levers.get("demography_variant", 0.0)]
    base_axes = {k: levers[k] for k in ("exposure_delta", "nhi_share", "nps_share")
                 if k in levers}
    r = run_korea_mc(n=n, spread=0.15, seed=seed, preset=preset_key,
                     base_params=_korea_v2p(preset_key, levers), base_axes=base_axes,
                     deltas=deltas, data_pool=data_pool, ctx_pool=ctx_pool,
                     invariant_every=0, demography_variant=variant)
    return {
        "config": {"preset": preset_key, "levers": levers, "n": n, "seed": seed,
                   "spread": 0.15},
        "base": {k: round(float(v), 4) for k, v in r.base.items()},
        "targets": {
            h: [{"lever": row.input, "spearman": round(float(row.spearman), 4)}
                for row in r.tornado[r.tornado.headline == h].itertuples()]
            for h in HEADLINES},
    }
