"""The web ScenarioPayload builder — ONE resolution + assembly path for the site.

`resolve_config` reimplements the Streamlit app's widget semantics exactly once (defaults →
lever diffs → the kinked-adoption branch → `ui_from_defaults`'s clamps → `build_v2_params` →
`apply_overlays`), and `build_scenario_payload` runs the model and assembles everything the
front end renders. The static bundle generator (scripts/gen_web_bundle.py) and the API
(api/scenario.py) both call THIS module, so a committed bundle and a live response for the same
config cannot drift — the byte-equality is pinned in tests/test_api.py.

Inputs arrive in `parse_query_config` shape: {"preset": key|None, "overlays": [..],
"levers": {ui-key: value}} — already clamped/snapped when they came through the codec (URL or
API sanitizer). Pure module: no streamlit, no fastapi.
"""
from __future__ import annotations

import math

import numpy as np

from . import grounding
from . import mc as mc_mod
from . import presets as presets_mod
from . import summary as summary_mod
from .app_params import (CUSTOM_DEFAULTS, build_v2_params, canon, cfg_key,
                         preset_widget_defaults, ui_from_defaults)
from .charts import US_STATE_FIPS
from .dynamics_v2 import DynamicModelV2
from .government import RevenueLedger

# ---------------------------------------------------------------------------- config resolution
KINK_TOL = 0.004      # the app's isclose abs_tol for "adoption sliders untouched" (JS doubles)


def slug(cfg: dict) -> str:
    """Static-bundle filename for a pristine config: '<preset|custom>' or '<...>~ov1+ov2'
    (overlays in canonical OVERLAYS order)."""
    base = cfg.get("preset") or "custom"
    ovs = [k for k in presets_mod.OVERLAYS if k in (cfg.get("overlays") or [])]
    return base + ("~" + "+".join(ovs) if ovs else "")


def resolve_config(cfg: dict) -> dict:
    """cfg → {"ui": .., "v2p": .., "preset": .., "overlays": .., "notes": .., "kink_replaced": ..}.

    Mirrors app/streamlit_app.py: widget defaults come from the preset (or CUSTOM_DEFAULTS),
    lever diffs overwrite them, and a kinked preset keeps its parametric path only while the
    adoption sliders sit on the preset values (else linspace + a warning)."""
    preset = presets_mod.PRESETS.get(cfg.get("preset") or "")
    overlays = [k for k in (cfg.get("overlays") or []) if k in presets_mod.OVERLAYS]
    if {"cw-robot-tax", "grt-robot-tax"} <= set(overlays):
        overlays.remove("grt-robot-tax")                    # the app's exclusivity rule

    d = dict(preset_widget_defaults(preset)) if preset is not None else dict(CUSTOM_DEFAULTS)
    d.update({k: v for k, v in (cfg.get("levers") or {}).items() if k in d})

    kink_replaced = False
    kink_preset = preset
    if preset is not None and preset.adoption_reach_year is not None:
        untouched = (math.isclose(d["adopt0"], preset.adoption_start, abs_tol=KINK_TOL)
                     and math.isclose(d["adopt1"], preset.adoption_end, abs_tol=KINK_TOL))
        if not untouched:
            kink_preset, kink_replaced = None, True         # sliders moved → linear ramp

    ui = ui_from_defaults(d, rung=1, preset=kink_preset)
    v2p, notes = presets_mod.apply_overlays(build_v2_params(ui), overlays)
    return {"ui": ui, "v2p": v2p, "preset": preset, "overlays": overlays,
            "notes": notes, "kink_replaced": kink_replaced}


def cfg_repr_for(cfg: dict) -> str:
    """The repr-exact cache key of a config's canonical params (no model run needed)."""
    return cfg_key(resolve_config(cfg)["v2p"])


# ---------------------------------------------------------------------------- payload assembly
def _differs(a, b) -> bool:                                  # the app's deviation check, verbatim
    if isinstance(a, list) or isinstance(b, list):
        return not np.allclose(np.asarray(a, float), np.asarray(b, float), atol=1e-9)
    if isinstance(a, float) or isinstance(b, float):
        return not math.isclose(float(a), float(b), abs_tol=1e-6)
    return a != b


def _summary_json(res, ledger, grouping: str, units: str, start_year: int, cbo) -> dict:
    df = summary_mod.build_fiscal_summary(res, ledger, grouping=grouping, units=units,
                                          start_year=start_year, cbo=cbo)
    year_cols = [c for c in df.columns if str(c)[:2] == "20" and str(c).isdigit()]
    rows = [{"group": r["group"], "label": r["label"], "kind": r["kind"],
             "values": [None if (isinstance(r[c], float) and math.isnan(r[c])) else round(float(r[c]), 4)
                        for c in year_cols],
             "total": None if (isinstance(r["Total"], float) and math.isnan(r["Total"]))
             else round(float(r["Total"]), 4)}
            for _, r in df.iterrows()]
    return {"years": [int(c) for c in year_cols], "rows": rows}


def build_scenario_payload(data, deltas, cfg: dict, ctx_cache: dict | None = None) -> dict:
    """Run the model for a resolved config and assemble the full ScenarioPayload (see module
    doc + the plan's schema). `ctx_cache` (cfg_key → mc.ScenarioContext) is shared across calls
    so overlay readouts reuse one context per base, exactly like the app's cache_resource."""
    r = resolve_config(cfg)
    ui, v2p, preset, overlays = r["ui"], r["v2p"], r["preset"], r["overlays"]
    start_year = preset.start_year if preset is not None else 2026

    m = DynamicModelV2(data, deltas, v2p)                    # keep the object: state_table
    res = m.run()
    res = res.assign(state_gap_cum_B=res["state_gap_B"].cumsum())
    final = res.iloc[-1]

    jobs_lost_M = float(final["population_M"] - final["employed_M"] - final["reabsorbed_M"]
                        - final["retired_M"])
    inc_tax_lost_cum_B = float(res["inc_fed_loss_B"].sum())

    # overlay readouts: base WITHOUT overlays vs each overlay alone (one shared context)
    overlay_readouts, combined = [], None
    if overlays:
        if ctx_cache is None:
            ctx_cache = {}
        base_no = canon(build_v2_params(ui))
        bkey = cfg_key(base_no)
        ctx = ctx_cache.get(bkey)
        if ctx is None:
            ctx = ctx_cache[bkey] = mc_mod.ScenarioContext(data, deltas, base_no)
        gap = float(ctx.run(base_no).iloc[-1]["fed_deficit_B"])
        for k in overlays:
            ovp = canon(presets_mod.apply_overlays(base_no, [k])[0])
            rec = gap - float(ctx.run(ovp).iloc[-1]["fed_deficit_B"])
            overlay_readouts.append({
                "key": k, "name": presets_mod.OVERLAYS[k].name, "no_gap": gap <= 1.0,
                "recovered_B": round(rec, 4), "gap_B": round(gap, 4),
                "pct": round(100 * rec / gap, 4) if gap > 1.0 else None})
        if len(overlays) > 1 and gap > 1.0:
            rec_all = gap - float(ctx.run(canon(v2p)).iloc[-1]["fed_deficit_B"])
            combined = {"recovered_B": round(rec_all, 4), "gap_B": round(gap, 4),
                        "pct": round(100 * rec_all / gap, 4)}

    modified_fields = []
    if preset is not None:
        pp = presets_mod.to_params(preset, n_periods=ui["n_periods"])
        uip = build_v2_params(ui)
        modified_fields = [f for f in sorted(set(preset.overrides) | {"adoption_path"})
                           if _differs(getattr(uip, f), getattr(pp, f))]

    stbl = m.state_table.assign(fips=lambda t: t["state"].map(US_STATE_FIPS))
    tax_base_B = float(stbl["taxable_base_B"].sum())
    gap_B = float(final["state_gap_B"])

    cbo = grounding.load_cbo_baseline()
    ledger = RevenueLedger(data)
    final_year = start_year + int(final["period"])
    cbo_def = abs(cbo.deficit(final_year))

    payload = {
        "config": {
            "preset": preset.key if preset is not None else None,
            "overlays": overlays,
            "levers": {k: v for k, v in (cfg.get("levers") or {}).items()},
            "start_year": start_year, "n_periods": int(ui["n_periods"]),
            "cfg_repr": cfg_key(v2p),
            "modified_fields": modified_fields,
            "overlay_notes": r["notes"],
        },
        "rows": res.round(4).to_dict("records"),
        "final": {
            "jobs_lost_M": round(jobs_lost_M, 4),
            "employment_drop_pct": round(float(final["employment_drop_pct"]), 4),
            "inc_tax_lost_cum_B": round(inc_tax_lost_cum_B, 4),
            "fed_deficit_abs_B": round(float(final["fed_deficit_abs_B"]), 4),
            "fed_deficit_abs_pct_gdp": round(float(final["fed_deficit_abs_pct_gdp"]), 4),
            "fed_debt_B": round(float(final["fed_debt_B"]), 4),
            "fed_deficit_B": round(float(final["fed_deficit_B"]), 4),
            "state_gap_B": round(gap_B, 4),
            "productivity_index": round(float(final["productivity_index"]), 6),
            "ubi_required_rate": round(float(final["ubi_required_rate"]), 6),
            "n_states_capped": int(final["n_states_capped"]),
        },
        "grounding": {
            "jobs": grounding.ground(jobs_lost_M, "jobs"),
            "revenue_flow": grounding.ground(inc_tax_lost_cum_B, "revenue_flow"),
            "debt_stock": grounding.ground(float(final["fed_debt_B"]), "debt_stock"),
            "fed_deficit_flow": grounding.ground(float(final["fed_deficit_B"]), "fed_deficit_flow"),
            "state_flow": grounding.ground(gap_B, "state_flow"),
        },
        "states": stbl.round(4).to_dict("records"),
        "state_calc": {
            "tax_base_B": round(tax_base_B, 4),
            "implied_pct": round(100.0 * gap_B / tax_base_B, 4) if tax_base_B > 0 else 0.0,
        },
        "summary": {
            "tax_busd": _summary_json(res, ledger, "tax", "busd", start_year, cbo),
            "tax_pct": _summary_json(res, ledger, "tax", "pct_cbo_revenue", start_year, cbo),
            "channel_busd": _summary_json(res, ledger, "channel", "busd", start_year, cbo),
            "channel_pct": _summary_json(res, ledger, "channel", "pct_cbo_revenue", start_year, cbo),
        },
        "scale_check": {
            "final_year": final_year,
            "cbo_deficit_B": round(float(cbo_def), 4),
            "add_pct": round(100.0 * float(final["fed_deficit_B"]) / cbo_def, 4),
            "cbo_max_year": cbo.max_year,
            "extrapolated": final_year > cbo.max_year,
        },
        "overlay_readouts": overlay_readouts,
        "warnings": {
            "kink_replaced": r["kink_replaced"],
        },
    }
    if combined is not None:
        payload["overlay_readouts_combined"] = combined
    if v2p.ubi_annual > 0 and float(final["ubi_required_rate"]) > 1.0:
        payload["warnings"]["ubi_unfunded"] = {
            "ubi_annual": v2p.ubi_annual,
            "required_rate": round(float(final["ubi_required_rate"]), 4),
        }
    return payload
