"""Generate web/public/data/korea.json — the single data file behind the Korea page.

Everything the page shows comes from here, and everything here comes from the tested model
chain (same functions the integration tests pin), so the site cannot disagree with the code.
Regenerate after any Korea model change:

    .venv/bin/python scripts/gen_korea_bundle.py

Conventions, documented once and carried in the bundle's `config` block:
- chain          = the ASSEMBLED V2 run (net displacement: re-employment, survivor raises,
                   demand destruction) via run_korea_preset + the funds bridge, with the EI
                   OUTLAY side included — this replaced the direct gross-ceiling chain;
- central line   = korea-central preset × central exposure read × band-midpoint shares
                   (NHI 0.81, NPS 0.85 — midpoints of the documented bands, disclosed);
- band envelope  = pointwise min/max over 9 assembled runs (3 diffusion presets × exposure
                   read ±0.5pp) × 4 share-edge combos applied in the projector;
- AGI scenarios  = korea-agi-20y / korea-agi-5y at central exposure × mid shares. Separate
                   rows, NEVER band edges. Cognitive channel only (no Korean robot-exposure
                   vector) — an understatement the page must disclose;
- the two composition what-ifs stay on the direct chain: they are structural decompositions
  of a hypothetical displacement pattern, not forecasts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_model.korea_assembly import (build_korea_data, build_korea_deltas,
                                         korea_assembled_band, korea_project_funds,
                                         run_korea_preset)
from fiscal_model.korea_funds import (EI_BASELINE, NHI_REFORM, NPS_REFORM,
                                      first_negative_year)
from fiscal_model.korea_region import region_exposure
from fiscal_model.korea_scenarios import WAGE_LINKED_SHARE, korea_erosion_paths

OUT = Path(__file__).resolve().parent.parent / "web" / "public" / "data" / "korea.json"

NHI_MID = round((WAGE_LINKED_SHARE["nhi"].low + WAGE_LINKED_SHARE["nhi"].high) / 2, 2)
NPS_MID = round((WAGE_LINKED_SHARE["nps"].low + WAGE_LINKED_SHARE["nps"].high) / 2, 2)
AGI_KEYS = ("korea-agi-20y", "korea-agi-5y")


def band_projections(band: dict) -> list:
    """(preset_key, projection) per grid run × share-edge combo — the band population."""
    out = []
    for (pkey, _delta), bridge in band.items():
        for nhi_s in (WAGE_LINKED_SHARE["nhi"].low, WAGE_LINKED_SHARE["nhi"].high):
            for nps_s in (WAGE_LINKED_SHARE["nps"].low, WAGE_LINKED_SHARE["nps"].high):
                out.append((pkey, korea_project_funds(bridge, nhi_s, nps_s)))
    return out


def fund_block(fund, key: str, central, runs, agi: dict) -> dict:
    eroded = np.stack([r[key]["eroded_reserves"] for _, r in runs])
    return {
        "years": list(fund.years),
        "published": list(fund.reserves),
        "eroded_central": [round(float(v), 2) for v in central[key]["eroded_reserves"]],
        "eroded_lo": [round(float(v), 2) for v in eroded.min(axis=0)],
        "eroded_hi": [round(float(v), 2) for v in eroded.max(axis=0)],
        "published_depletion": first_negative_year(fund.reserves, fund.base_year),
        "source": fund.source,
        # AGI worlds as separate overlay paths (mid shares), never folded into the band
        "scenarios": {k: [round(float(v), 2) for v in agi[k][key]["eroded_reserves"]]
                      for k in AGI_KEYS},
    }


def main() -> None:
    band = korea_assembled_band()
    runs = band_projections(band)
    central_bridge = band[("korea-central", 0.0)]
    central = korea_project_funds(central_bridge, NHI_MID, NPS_MID)

    data = build_korea_data()
    deltas = build_korea_deltas()
    horizon = len(NPS_REFORM.revenue)
    agi_bridges = {k: run_korea_preset(k, n_periods=horizon, data=data, deltas=deltas)["bridge"]
                   for k in AGI_KEYS}
    agi = {k: korea_project_funds(b, NHI_MID, NPS_MID) for k, b in agi_bridges.items()}

    nhi_years = [r["nhi"]["years_pulled_forward"] for _, r in runs]
    nps_years = [r["nps"]["years_pulled_forward"] for _, r in runs]
    nps_central = [r["nps"]["years_pulled_forward"] for p, r in runs if p == "korea-central"]
    ei_short = [EI_BASELINE.reserves[-1] - r["ei"]["eroded_reserves"][-1] for _, r in runs]

    # composition: the assembled central run's 2035 erosion by institution (consistent with
    # the fund charts on the same page) + the two structural what-ifs (direct chain)
    comp_central = {k: round(float(v[9]), 4)
                    for k, v in central_bridge["erosion"].items()}
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
            "chain": "the assembled model, which nets out re-employment, survivor raises "
                     "and demand destruction, and includes EI benefit outlays",
            "central": f"the central preset with the central exposure reading and "
                       f"band-midpoint revenue shares (NHI {NHI_MID}, NPS {NPS_MID})",
            "band": "the pointwise range over the three diffusion presets, the exposure "
                    f"reading, and the revenue-share bands ({len(runs)} projections)",
            "agi": "korea-agi-20y / korea-agi-5y (Korinek-Suh translations) at central "
                   "exposure × mid shares — separate scenario rows, never band edges; "
                   "cognitive channel only (no Korean robot-exposure vector wired), which "
                   "understates displacement in manual occupations",
            "adoption": "diffusion presets ramp from 2026 to 2035 and then hold, while "
                        "the AGI presets reach full automation of exposed work at year 5 "
                        "or year 20 and then hold",
            "whatifs": "composition what-ifs are the direct structural chain (hypothetical "
                       "displacement pattern), not forecasts",
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
            "agi": {
                k: {
                    "nhi_years_forward": round(agi[k]["nhi"]["years_pulled_forward"], 2),
                    "nps_given_back": round(agi[k]["nps"]["years_pulled_forward"], 2),
                    "ei_shortfall_tn": round(
                        EI_BASELINE.reserves[-1] - agi[k]["ei"]["eroded_reserves"][-1], 1),
                } for k in AGI_KEYS
            },
        },
        "funds": {
            "nhi": fund_block(NHI_REFORM, "nhi", central, runs, agi),
            "nps": fund_block(NPS_REFORM, "nps", central, runs, agi),
            "ei": fund_block(EI_BASELINE, "ei", central, runs, agi),
        },
        "composition": {
            "central_2035": comp_central,
            "white_collar_only": comp_wc,
            "elementary_only": comp_el,
        },
        # workstream D: descriptive — the geography of exposure, no provincial fiscal
        # claims. All-employed occupation mix (LAFS) × national within-occupation HELC.
        "regions": [
            {"key": r.key, "short": r.short, "region": r.region,
             "col": int(r.col), "row": int(r.row),
             "emp_k": round(float(r.emp_k), 1),
             "helc_share": round(float(r.helc_share), 4)}
            for r in region_exposure().itertuples()],
        "sources": [
            {"name": "NHI path", "cite": NHI_REFORM.source},
            {"name": "NPS path", "cite": NPS_REFORM.source},
            {"name": "EI path", "cite": EI_BASELINE.source},
            {"name": "Exposure", "cite": "BOK 이슈노트 2025-2 「AI와 한국경제」 <그림 9> "
             "(figure-read, reconciled to published aggregates; IMF SIP 2025/013 Fig. 7 "
             "confirms)"},
            {"name": "Demography", "cite": "Statistics Korea 장래인구추계 2022~2072, medium "
             "variant (press-release tables)"},
            {"name": "Regional mix", "cite": "국가데이터처 「2025년 상반기 지역별고용조사」 "
             "취업자의 산업 및 직업별 특성, 통계표 4 (시도 직업별 취업자, 2025.1/2) — "
             "all-employed occupation mix × BOK within-occupation HELC shares; "
             "descriptive, no provincial fiscal claims"},
            {"name": "AGI scenarios", "cite": "Korinek & Suh — translated presets "
             "(docs/PRESET_EVIDENCE §1); cognitive channel only for Korea"},
        ],
    }
    OUT.write_text(json.dumps(bundle, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB, "
          f"{len(band)} assembled runs, {len(runs)} projections)")


if __name__ == "__main__":
    main()
