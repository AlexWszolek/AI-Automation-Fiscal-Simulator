"""Generate web/src/gen/korea_grid.json — the Korea rail's lever specs, per-preset
defaults, and group layout, from the SAME Python sources the API sanitizes against
(KOREA_LEVER_SPECS bounds, korea_preset_params defaults), so a slider can never emit a
value the server clamps differently.

    .venv/bin/python scripts/gen_korea_grid.py

`copy` names reference existing keys in copy.json's US lever block where the lever is the
same lever (label REUSE, not new copy); Korea-only axes use keys under copy.json
korea.levers, which are [copy: Alex] placeholders until the copy pass.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_model.korea_assembly import korea_preset_params
from fiscal_model.korea_scenarios import KOREA_PRESETS
from fiscal_model.korea_webpayload import (KOREA_LEVER_SPECS, NHI_MID, NPS_MID)

OUT = Path(__file__).resolve().parent.parent / "web" / "src" / "gen" / "korea_grid.json"

# lever -> (copy key: "us:<key>" reuses copy.levers, "kr:<key>" reads copy.korea.levers,
#           group title, step, kind)
UI = [
    ("adoption_start",        "us:adopt0",     "Automation & adoption", 0.005, "float"),
    ("adoption_end",          "us:adopt1",     "Automation & adoption", 0.01,  "float"),
    ("reabsorption_rate",     "us:reab",       "Labor market",          0.01,  "float"),
    ("reemployment_haircut",  "us:haircut",    "Labor market",          0.01,  "float"),
    ("ui_weeks",              "us:ui_weeks",   "Labor market",          1,     "int"),
    ("reab_wage_baumol",      "us:reab_baumol", "Labor market",         0.05,  "float"),
    ("reab_wage_crowding",    "us:reab_crowd", "Labor market",          0.05,  "float"),
    ("lfp_exit_rate",         "us:lfp",        "Labor market",          0.005, "float"),
    ("attrition_rate",        "us:attrition",  "Labor market",          0.005, "float"),
    ("retained_profit_share", "us:retained",   "Firms",                 0.01,  "float"),
    ("price_reduction_share", "us:price",      "Firms",                 0.01,  "float"),
    ("auto_cost",             "us:auto_cost",  "Firms",                 0.01,  "float"),
    ("compute_effective_rate", "us:compute_rate", "Firms",               0.01,  "float"),
    ("survivor_elasticity",   "us:elasticity", "Survivor wages",        0.05,  "float"),
    ("survivor_raise_ceiling", "us:ceiling",    "Survivor wages",        0.05,  "float"),
    ("survivor_spillover_to_profit", "us:spillover", "Survivor wages",   0.05,  "float"),
    ("price_passthrough",     "us:price_pt",   "Macro & demand",        0.05,  "float"),
    ("productivity_passthrough", "us:prod_pt", "Macro & demand",        0.05,  "float"),
    ("baseline_growth_rate",  "us:growth",     "Macro & demand",        0.005, "float"),
    ("demand_multiplier",     "us:demand",     "Macro & demand",        0.05,  "float"),
    ("interest_rate",         "us:interest",   "Macro & demand",        0.005, "float"),
    ("automation_tax_rate",   "us:atax",       "Government policy",     0.01,  "float"),
    ("income_tax_mult",       "us:income_mult", "Government policy",    0.05,  "float"),
    ("corp_tax_mult",         "us:corp_mult",  "Government policy",     0.05,  "float"),
    ("cons_tax_mult",         "us:cons_mult",  "Government policy",     0.05,  "float"),
    ("nhi_share",             "kr:nhi_share",  "KOREA_AXES",            0.01,  "float"),
    ("nps_share",             "kr:nps_share",  "KOREA_AXES",            0.01,  "float"),
    ("exposure_delta",        "kr:exposure_delta", "KOREA_AXES",        None,  "select"),
    ("demography_variant",    "kr:demography_variant", "KOREA_AXES",    None,  "select"),
]
AXIS_DEFAULTS = {"nhi_share": NHI_MID, "nps_share": NPS_MID, "exposure_delta": 0.0,
                 "demography_variant": 0.0}


def main() -> None:
    levers = {}
    for name, copy_key, group, step, kind in UI:
        lo, hi = KOREA_LEVER_SPECS[name]
        spec = {"lo": float(lo), "hi": float(hi), "copy": copy_key,
                "group": group, "kind": kind}
        if kind == "select":
            spec["values"] = ([-1, 0, 1] if name == "demography_variant"
                              else [-0.5, 0.0, 0.5])
        else:
            spec["step"] = step
        levers[name] = spec

    presets = []
    for key, p in KOREA_PRESETS.items():
        v2p = korea_preset_params(key)
        defaults = {}
        for name, *_ in UI:
            if name == "adoption_end":
                defaults[name] = round(float(v2p.adoption_path[-1]), 4)
            elif name == "adoption_start":
                defaults[name] = round(float(v2p.adoption_path[0]), 4)
            else:
                defaults[name] = AXIS_DEFAULTS.get(name, getattr(v2p, name, None))
        defaults["ui_weeks"] = int(defaults["ui_weeks"])
        presets.append({"key": key, "name": p.name, "blurb": p.blurb,
                        "display_periods": p.n_periods, "defaults": defaults})

    groups = []
    for _, _, g, _, _ in UI:
        if g not in groups:
            groups.append(g)
    grid = {"levers": levers, "presets": presets, "groups": groups}
    OUT.write_text(json.dumps(grid, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ({len(levers)} levers, {len(presets)} presets)")


if __name__ == "__main__":
    main()
