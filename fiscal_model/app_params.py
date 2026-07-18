"""The pure UI↔params bridge — single source of truth for the app, the MC precompute, and tests.

Everything here is streamlit-free:
- `build_v2_params(ui)`: the sidebar dict → V2Params (the app's only construction path);
- `CUSTOM_DEFAULTS` / `preset_widget_defaults(preset)`: the widget-default dicts the keyless
  value-swap mechanism feeds (presets.py stays the single source of preset truth);
- `ui_from_defaults(d, ...)`: reproduce the ui dict EXACTLY as untouched widgets would return it
  (incl. the price/robot-tax clamps and the kinked-adoption branch) — this is what lets the
  precompute script and tests generate configs bit-identical to the live app's;
- `canon(v2p)` / `cfg_key(v2p)`: the canonical repr key for MC caches and precomputed artifacts
  (`denominator` is display-only and normalized out so flipping the %-GDP radio never invalidates
  a 60-second tornado);
- `UI_GRID` + `parse_query_config`/`encode_query_config`: the shareable-URL codec — values are
  clamped to widget ranges and snapped to widget grids so a hand-edited URL can never crash a
  slider (StreamlitValueAboveMaxError) or plant an off-grid default.

The per-preset guarantee (tests/test_app_params.py): `build_v2_params(ui_from_defaults(
preset_widget_defaults(p), rung=1, preset=p))` equals `presets.to_params(p)` BOTH as a dataclass
and as repr() — repr equality is what makes precomputed-artifact matching exact.
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Optional

import numpy as np

from . import presets as presets_mod
from .levers_v2 import V2Params

# ---------------------------------------------------------------------------- defaults
CUSTOM_DEFAULTS = dict(cog=0.70, phys=0.20, robotics_lag=4, rob_base=1.0, adopt0=0.10,
                       adopt1=0.60, n_periods=10,
                       reab=0.0, haircut=0.30, reab_baumol=0.0, reab_crowd=0.0,
                       ui_weeks=26, interest=0.03, ubi=0,
                       retained=0.6, price=0.2, auto_cost=0.10, compute_rate=0.10,
                       unbounded=False, ceiling=1.5, elasticity=-0.15, spillover=0.5,
                       price_pt=0.3, prod_pt=0.30, growth=0.04, lfp=0.03, attrition=0.025,
                       atax=0.0, ubi_recapture=0.25, demand=0.5,
                       income_mult=1.0, corp_mult=1.0, cons_mult=1.0,
                       state_resp="mix", state_cut=0.0, rate_cap=1.0)


def preset_widget_defaults(preset) -> dict:
    """Widget defaults derived from to_params(preset) — presets.py stays the single source of truth."""
    p = presets_mod.to_params(preset)
    return dict(cog=p.cognitive_feasibility, phys=p.physical_feasibility,
                robotics_lag=int(p.robotics_lag), rob_base=p.robotics_base,
                adopt0=preset.adoption_start,
                adopt1=preset.adoption_end, n_periods=p.n_periods,
                reab=p.reabsorption_rate, haircut=p.reemployment_haircut,
                reab_baumol=p.reab_wage_baumol, reab_crowd=p.reab_wage_crowding, ui_weeks=p.ui_weeks,
                interest=p.interest_rate, ubi=int(p.ubi_annual),
                retained=p.retained_profit_share, price=p.price_reduction_share,
                auto_cost=p.auto_cost, compute_rate=p.compute_effective_rate,
                unbounded=math.isinf(p.survivor_raise_ceiling),
                ceiling=p.survivor_raise_ceiling if math.isfinite(p.survivor_raise_ceiling) else 1.5,
                elasticity=p.survivor_elasticity, spillover=p.survivor_spillover_to_profit,
                price_pt=p.price_passthrough, prod_pt=p.productivity_passthrough,
                growth=p.baseline_growth_rate, lfp=p.lfp_exit_rate, attrition=p.attrition_rate,
                atax=p.automation_tax_rate, ubi_recapture=p.ubi_recapture_rate,
                demand=p.demand_multiplier, state_resp=p.state_response,
                income_mult=p.income_tax_mult, corp_mult=p.corp_tax_mult, cons_mult=p.cons_tax_mult,
                state_cut=p.state_cut_share, rate_cap=p.state_rate_hike_cap)


# ---------------------------------------------------------------------------- params construction
def build_v2_params(ui: dict) -> V2Params:
    """Map the sidebar dict to a V2Params. Disposition survivor share is the remainder of
    profit+price (clamped ≥0). float(ui["ubi"]) matters: the UBI slider returns an int, and repr
    equality with to_params(preset) — the precomputed-artifact key — needs the float."""
    survivor_share = max(0.0, 1.0 - ui["retained_profit_share"] - ui["price_reduction_share"])
    ceiling = float("inf") if ui["survivor_unbounded"] else ui["survivor_raise_ceiling"]
    return V2Params(
        exposure_mapping=ui["mapping"], cognitive_feasibility=ui["cog"], physical_feasibility=ui["phys"],
        robotics_lag=ui["robotics_lag"], robotics_base=ui["robotics_base"],
        adoption=1.0, adoption_path=ui["adoption_path"], n_periods=ui["n_periods"],
        retained_profit_share=ui["retained_profit_share"], price_reduction_share=ui["price_reduction_share"],
        survivor_gains_share=survivor_share, auto_cost=ui["auto_cost"], offshore_share=ui["offshore_share"],
        compute_effective_rate=ui["compute_effective_rate"],
        survivor_raise_ceiling=ceiling, survivor_elasticity=ui["survivor_elasticity"],
        survivor_spillover_to_profit=ui["survivor_spillover_to_profit"],
        reabsorption_rung=ui["reabsorption_rung"], reabsorption_rate=ui["reab"],
        reemployment_haircut=ui["haircut"],
        reab_wage_baumol=ui["reab_wage_baumol"], reab_wage_crowding=ui["reab_wage_crowding"],
        lfp_exit_rate=ui["lfp_exit_rate"],
        attrition_rate=ui["attrition_rate"], ui_weeks=ui["ui_weeks"],
        price_passthrough=ui["price_passthrough"], productivity_passthrough=ui["productivity_passthrough"],
        demand_multiplier=ui["demand"], state_response=ui["state_resp"], state_cut_share=ui["state_cut_share"],
        state_rate_hike_cap=ui["state_rate_hike_cap"], automation_tax_rate=ui["automation_tax_rate"],
        interest_rate=ui["interest"], ubi_annual=float(ui["ubi"]), ubi_recapture_rate=ui["ubi_recapture_rate"],
        baseline_growth_rate=ui["baseline_growth_rate"], denominator=ui["denominator"],
        income_tax_mult=ui["income_tax_mult"], corp_tax_mult=ui["corp_tax_mult"],
        cons_tax_mult=ui["cons_tax_mult"])


def ui_from_defaults(d: dict, *, rung: int, preset=None, mapping: str = "percentile",
                     denominator: str = "absolute") -> dict:
    """The ui dict EXACTLY as the app's untouched widgets would return it from defaults `d` —
    including the price-slider clamp, the robot-tax bound clamp, and the kinked-path branch."""
    retained, price = d["retained"], d["price"]
    price_max = round(1.0 - retained, 2)
    price = min(price, price_max) if price_max > 0 else 0.0
    atx_bound = round(min(0.30, retained * (1.0 - d["auto_cost"])), 2)
    atax = 0.0 if atx_bound < 0.01 else min(d["atax"], atx_bound)
    n = d["n_periods"]
    if preset is not None and preset.adoption_reach_year is not None:
        adoption_path = presets_mod.build_adoption_path(preset, n)
    else:
        adoption_path = list(np.linspace(d["adopt0"], d["adopt1"], n))
    return dict(mapping=mapping, cog=d["cog"], phys=d["phys"], robotics_lag=float(d["robotics_lag"]),
                robotics_base=float(d["rob_base"]),
                adoption_path=adoption_path, n_periods=n,
                retained_profit_share=retained, price_reduction_share=price, auto_cost=d["auto_cost"],
                offshore_share=0.0, compute_effective_rate=d["compute_rate"],
                survivor_unbounded=d["unbounded"], survivor_raise_ceiling=d["ceiling"],
                survivor_elasticity=d["elasticity"], survivor_spillover_to_profit=d["spillover"],
                reabsorption_rung=rung, reab=d["reab"], haircut=d["haircut"],
                reab_wage_baumol=float(d["reab_baumol"]), reab_wage_crowding=float(d["reab_crowd"]),
                lfp_exit_rate=d["lfp"], attrition_rate=d["attrition"], ui_weeks=d["ui_weeks"],
                price_passthrough=d["price_pt"], productivity_passthrough=d["prod_pt"],
                demand=d["demand"], state_resp=d["state_resp"], state_cut_share=d["state_cut"],
                state_rate_hike_cap=d["rate_cap"], automation_tax_rate=atax,
                interest=d["interest"], ubi=d["ubi"], ubi_recapture_rate=d["ubi_recapture"],
                baseline_growth_rate=d["growth"], denominator=denominator,
                income_tax_mult=d["income_mult"], corp_tax_mult=d["corp_mult"],
                cons_tax_mult=d["cons_mult"])


def canon(v2p: V2Params) -> V2Params:
    """Normalize display-only fields out of a config so cache keys ignore them."""
    return replace(v2p, denominator="absolute")


def cfg_key(v2p: V2Params) -> str:
    """The canonical cache/artifact key. repr of a frozen dataclass is deterministic, and the
    ui_from_defaults round-trip is repr-exact against to_params(preset) (pinned in tests)."""
    return repr(canon(v2p))


# ---------------------------------------------------------------------------- shareable URLs
# One entry per URL-encodable widget: ui/defaults key -> (lo, hi, step, type). Enum/bool entries
# carry their legal values instead of a numeric grid. Grid values mirror the app's sliders and
# tests/test_presets.py::_GRID (cross-pinned in tests/test_app_params.py).
UI_GRID: dict[str, tuple] = {
    "cog": (0.0, 1.0, 0.05, float), "phys": (0.0, 1.0, 0.05, float),
    "robotics_lag": (0, 15, 1, int), "rob_base": (1.0, 2.0, 0.05, float),
    "adopt0": (0.0, 1.0, 0.01, float), "adopt1": (0.0, 1.0, 0.01, float),
    "n_periods": (3, 30, 1, int),
    "reab": (0.0, 1.0, 0.025, float), "haircut": (0.0, 1.0, 0.01, float),
    "reab_baumol": (0.0, 1.0, 0.05, float), "reab_crowd": (0.0, 1.0, 0.05, float),
    "ui_weeks": (0, 52, 1, int),
    "lfp": (0.0, 0.2, 0.01, float), "attrition": (0.0, 0.1, 0.005, float),
    "retained": (0.0, 1.0, 0.05, float), "price": (0.0, 1.0, 0.05, float),
    "auto_cost": (0.0, 1.0, 0.05, float), "compute_rate": (0.0, 0.4, 0.01, float),
    "unbounded": (None, None, None, bool),
    "ceiling": (1.0, 3.0, 0.1, float),
    "elasticity": (-0.5, 0.5, 0.05, float), "spillover": (0.0, 1.0, 0.05, float),
    "price_pt": (0.0, 1.0, 0.05, float), "prod_pt": (0.0, 1.0, 0.05, float),
    "growth": (0.0, 0.08, 0.005, float), "demand": (0.0, 2.0, 0.05, float),
    "state_resp": (("mix", "raise_rates", "cut_spending"), None, None, str),
    "state_cut": (0.0, 1.0, 0.05, float), "rate_cap": (0.1, 3.0, 0.1, float),
    "atax": (0.0, 0.30, 0.01, float),
    "ubi": (0, 30_000, 1_000, int), "ubi_recapture": (0.0, 0.6, 0.05, float),
    "interest": (0.0, 0.10, 0.005, float),
    "income_mult": (0.5, 1.5, 0.05, float), "corp_mult": (0.5, 1.5, 0.05, float),
    "cons_mult": (0.5, 1.5, 0.05, float),
}


def _snap(raw: str, spec: tuple):
    """Parse + clamp to [lo, hi] + snap to the widget grid; None if unparseable."""
    lo, hi, step, typ = spec
    if typ is bool:
        return raw in ("1", "true", "True")
    if typ is str:
        return raw if raw in lo else None
    try:
        v = float(raw)
    except ValueError:
        return None
    v = min(max(v, lo), hi)
    k = round((v - lo) / step)
    v = round(lo + k * step, 10)
    v = min(max(v, lo), hi)                      # snap can land one step past hi on odd grids
    return typ(round(v)) if typ is int else float(v)


def parse_query_config(qp: dict) -> dict:
    """Query params → {preset: key|None, overlays: [..], levers: {ui-key: value}}. Unknown keys,
    unknown presets/overlays, and unparseable values are silently dropped (a shared URL must
    never crash the app)."""
    preset = qp.get("preset")
    if preset not in presets_mod.PRESETS:
        preset = None
    overlays = [k for k in str(qp.get("ov", "")).split(",") if k in presets_mod.OVERLAYS]
    if all(k in overlays for k in ("cw-robot-tax", "grt-robot-tax")):
        overlays.remove("grt-robot-tax")
    levers = {}
    for key, spec in UI_GRID.items():
        if key in qp:
            v = _snap(str(qp[key]), spec)
            if v is not None:
                levers[key] = v
    return {"preset": preset, "overlays": overlays, "levers": levers}


def encode_query_config(preset_key: Optional[str], overlays: list, current: dict,
                        pristine: dict) -> dict:
    """The write-back dict: preset + overlays + only the levers that differ from the pristine
    preset defaults (grid-tolerant compare absorbs JS-double slider echoes)."""
    out: dict[str, str] = {}
    if preset_key:
        out["preset"] = preset_key
    if overlays:
        out["ov"] = ",".join(overlays)
    for key, spec in UI_GRID.items():
        if key not in current or key not in pristine:
            continue
        cur, pri = current[key], pristine[key]
        _lo, _hi, step, typ = spec
        if typ in (bool, str):
            if cur != pri:
                out[key] = ("1" if cur else "0") if typ is bool else str(cur)
        elif not math.isclose(float(cur), float(pri), abs_tol=(step or 1) / 2.001):
            out[key] = f"{typ(cur):g}" if typ is float else str(int(cur))
    return out
