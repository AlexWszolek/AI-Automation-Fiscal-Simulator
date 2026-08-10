"""Generate web/public/data/korea.json — the single data file behind the Korea page.

Everything the page shows comes from here, and everything here comes from the tested model
chain (same functions the integration tests pin), so the site cannot disagree with the code.
Regenerate after any Korea model change:

    .venv/bin/python scripts/gen_korea_bundle.py

Conventions, documented once and carried in the bundle's `config` block:
- central line   = korea-central preset × central exposure read × band-midpoint shares
                   (NHI 0.81, NPS 0.85 — midpoints of the documented bands, disclosed);
- band envelope  = pointwise min/max of eroded reserves across the full run grid
                   (3 presets × NHI-share edges × NPS-share edges × exposure ±0.5pp);
- adoption ramps 2026→2035 then holds (the preset semantics, test-pinned);
- the chain is the direct displacement CEILING, gross of re-employment — the page must
  display that disclosure, not footnote it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_model.korea_exposure import FIG9_SHARES
from fiscal_model.korea_funds import (EI_BASELINE, NHI_REFORM, NPS_REFORM,
                                      first_negative_year)
from fiscal_model.korea_scenarios import (KOREA_PRESETS, WAGE_LINKED_SHARE,
                                          korea_erosion_paths, korea_fund_headlines)
from fiscal_model.presets import build_adoption_path

OUT = Path(__file__).resolve().parent.parent / "web" / "public" / "data" / "korea.json"

NHI_MID = round((WAGE_LINKED_SHARE["nhi"].low + WAGE_LINKED_SHARE["nhi"].high) / 2, 2)
NPS_MID = round((WAGE_LINKED_SHARE["nps"].low + WAGE_LINKED_SHARE["nps"].high) / 2, 2)


def _exposure_variant(delta_pp: float) -> dict:
    out = {}
    for g, (le, hehc, helc) in FIG9_SHARES.items():
        total = le + hehc + helc
        helc_v = min(max(helc + delta_pp if helc > 0 else helc, 0.0), total)
        out[g] = helc_v / total if total else 0.0
    return out


def run_grid():
    """Every run in the band grid, with its eroded reserve paths per fund."""
    horizon = len(NPS_REFORM.revenue)
    for pkey, preset in KOREA_PRESETS.items():
        adoption = build_adoption_path(preset, horizon)
        for nhi_s in (WAGE_LINKED_SHARE["nhi"].low, WAGE_LINKED_SHARE["nhi"].high):
            for nps_s in (WAGE_LINKED_SHARE["nps"].low, WAGE_LINKED_SHARE["nps"].high):
                for delta in (-0.5, 0.0, 0.5):
                    r = korea_fund_headlines(
                        adoption, nhi_wage_linked_share=nhi_s,
                        nps_wage_linked_share=nps_s,
                        exposure=_exposure_variant(delta))
                    yield pkey, r


def central_run():
    horizon = len(NPS_REFORM.revenue)
    adoption = build_adoption_path(KOREA_PRESETS["korea-central"], horizon)
    return korea_fund_headlines(adoption, nhi_wage_linked_share=NHI_MID,
                                nps_wage_linked_share=NPS_MID)


def fund_block(fund, key: str, central, runs) -> dict:
    eroded = np.stack([r[key]["eroded_reserves"] for _, r in runs])
    return {
        "years": list(fund.years),
        "published": list(fund.reserves),
        "eroded_central": [round(float(v), 2) for v in central[key]["eroded_reserves"]],
        "eroded_lo": [round(float(v), 2) for v in eroded.min(axis=0)],
        "eroded_hi": [round(float(v), 2) for v in eroded.max(axis=0)],
        "published_depletion": first_negative_year(fund.reserves, fund.base_year),
        "source": fund.source,
    }


def main() -> None:
    runs = list(run_grid())
    central = central_run()

    nhi_years = [r["nhi"]["years_pulled_forward"] for _, r in runs]
    nps_years = [r["nps"]["years_pulled_forward"] for _, r in runs]
    nps_central = [r["nps"]["years_pulled_forward"] for p, r in runs if p == "korea-central"]
    ei_short = [EI_BASELINE.reserves[-1] - r["ei"]["eroded_reserves"][-1] for _, r in runs]

    # composition: central-2035 erosion by institution + the two decomposition what-ifs
    adoption10 = build_adoption_path(KOREA_PRESETS["korea-central"], 10)
    comp_central = {k: round(float(v[-1]), 4)
                    for k, v in korea_erosion_paths(adoption10).items()
                    if not k.startswith("memo:")}
    white_collar = {g: (0.6 if g in (1, 2) else 0.0) for g in range(1, 10)}
    elementary = {g: (0.6 if g == 9 else 0.0) for g in range(1, 10)}
    comp_wc = {k: round(float(v[0]), 4)
               for k, v in korea_erosion_paths([0.5], exposure=white_collar).items()
               if not k.startswith("memo:")}
    comp_el = {k: round(float(v[0]), 4)
               for k, v in korea_erosion_paths([0.5], exposure=elementary).items()
               if not k.startswith("memo:")}

    bundle = {
        "config": {
            "chain": "direct exposure × adoption (displacement CEILING, gross of re-employment)",
            "central": f"korea-central preset × central exposure read × band-midpoint "
                       f"shares (NHI {NHI_MID}, NPS {NPS_MID})",
            "band": "pointwise min/max over 3 presets × NHI share edges "
                    f"[{WAGE_LINKED_SHARE['nhi'].low}, {WAGE_LINKED_SHARE['nhi'].high}] × "
                    f"NPS share edges [{WAGE_LINKED_SHARE['nps'].low}, "
                    f"{WAGE_LINKED_SHARE['nps'].high}] × exposure read ±0.5pp "
                    f"({len(runs)} runs)",
            "adoption": "ramp 2026→2035 then flat (per preset), anchored in "
                        "docs/KOREA_PRESET_EVIDENCE.md",
        },
        "headlines": {
            "nhi": {
                "published_depletion": 2029,
                "years_forward_central": round(central["nhi"]["years_pulled_forward"], 2),
                "years_forward_lo": round(min(nhi_years), 2),
                "years_forward_hi": round(max(nhi_years), 2),
            },
            "nps": {
                "published_depletion": 2065,
                "pre_reform_depletion": 2057,
                "bought_years": 8,
                "given_back_central": round(central["nps"]["years_pulled_forward"], 2),
                "given_back_central_lo": round(min(nps_central), 2),
                "given_back_central_hi": round(max(nps_central), 2),
                "given_back_lo": round(min(nps_years), 2),
                "given_back_hi": round(max(nps_years), 2),
            },
            "ei": {
                "planned_2029_tn": EI_BASELINE.reserves[-1],
                "shortfall_central_tn": round(
                    EI_BASELINE.reserves[-1] - central["ei"]["eroded_reserves"][-1], 1),
                "shortfall_lo_tn": round(min(ei_short), 1),
                "shortfall_hi_tn": round(max(ei_short), 1),
            },
        },
        "funds": {
            "nhi": fund_block(NHI_REFORM, "nhi", central, runs),
            "nps": fund_block(NPS_REFORM, "nps", central, runs),
            "ei": fund_block(EI_BASELINE, "ei", central, runs),
        },
        "composition": {
            "central_2035": comp_central,
            "white_collar_only": comp_wc,
            "elementary_only": comp_el,
        },
        "sources": [
            {"name": "NHI path", "cite": NHI_REFORM.source},
            {"name": "NPS path", "cite": NPS_REFORM.source},
            {"name": "EI path", "cite": EI_BASELINE.source},
            {"name": "Exposure", "cite": "BOK 이슈노트 2025-2 「AI와 한국경제」 <그림 9> "
             "(figure-read, reconciled to published aggregates; IMF SIP 2025/013 Fig. 7 "
             "confirms)"},
            {"name": "Demography", "cite": "Statistics Korea 장래인구추계 2022~2072, medium "
             "variant (press-release tables)"},
        ],
    }
    OUT.write_text(json.dumps(bundle, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB, {len(runs)} band runs)")


if __name__ == "__main__":
    main()
