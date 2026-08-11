"""Generate the slides-pack headline table FROM the model, so slide numbers cannot drift
from the code. Regenerate after any Korea change:

    .venv/bin/python scripts/gen_korea_evidence_tables.py

Writes docs/research/korea-slides-pack/headline-table.md. The numbers are the ASSEMBLED
chain — the same korea_assembled_band / korea_project_funds calls behind korea.json, whose
parity test regenerates the bundle on every suite run — so if the suite is green, this
table matches the site and the model.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_model.korea_assembly import (build_korea_data, build_korea_deltas,
                                         korea_assembled_band, korea_project_funds,
                                         run_korea_preset)
from fiscal_model.korea_funds import (EI_BASELINE, NHI_REFORM, NPS_REFORM,
                                      first_negative_year)
from fiscal_model.korea_scenarios import WAGE_LINKED_SHARE

OUT = Path(__file__).resolve().parent.parent / "docs" / "research" / "korea-slides-pack"

NHI_MID = round((WAGE_LINKED_SHARE["nhi"].low + WAGE_LINKED_SHARE["nhi"].high) / 2, 2)
NPS_MID = round((WAGE_LINKED_SHARE["nps"].low + WAGE_LINKED_SHARE["nps"].high) / 2, 2)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    nhi_edges = (WAGE_LINKED_SHARE["nhi"].low, WAGE_LINKED_SHARE["nhi"].high)
    nps_edges = (WAGE_LINKED_SHARE["nps"].low, WAGE_LINKED_SHARE["nps"].high)

    band = korea_assembled_band()
    horizon = len(NPS_REFORM.revenue)

    # display rows: central exposure read only (12 = 3 presets × 2×2 share edges);
    # the band summary sweeps the full grid including the exposure ±0.5pp runs
    rows = []
    agg = {"nhi": [], "ei": [], "nps": []}
    nps_central = []
    for (pkey, delta), bridge in band.items():
        for nhi_s in nhi_edges:
            for nps_s in nps_edges:
                r = korea_project_funds(bridge, nhi_s, nps_s)
                nhi_y = r["nhi"]["years_pulled_forward"]
                nps_y = r["nps"]["years_pulled_forward"]
                ei_short = EI_BASELINE.reserves[-1] - r["ei"]["eroded_reserves"][-1]
                agg["nhi"].append(nhi_y)
                agg["nps"].append(nps_y)
                agg["ei"].append(ei_short)
                if pkey == "korea-central":
                    nps_central.append(nps_y)
                if delta == 0.0:
                    rows.append(
                        f"| {pkey} | {nhi_s:.2f} | {nps_s:.2f} | {nhi_y:.2f} "
                        f"| {r['nhi']['eroded_date']:.2f} | {ei_short:.1f} "
                        f"| {nps_y:.2f} | {r['nps']['eroded_date']:.2f} |")

    data, deltas = build_korea_data(), build_korea_deltas()
    agi_rows = []
    for key in ("korea-agi-20y", "korea-agi-5y"):
        b = run_korea_preset(key, n_periods=horizon, data=data, deltas=deltas)["bridge"]
        r = korea_project_funds(b, NHI_MID, NPS_MID)
        ei_short = EI_BASELINE.reserves[-1] - r["ei"]["eroded_reserves"][-1]
        agi_rows.append(
            f"| {key} | {NHI_MID:.2f} | {NPS_MID:.2f} "
            f"| {r['nhi']['years_pulled_forward']:.2f} | {r['nhi']['eroded_date']:.2f} "
            f"| {ei_short:.1f} | {r['nps']['years_pulled_forward']:.2f} "
            f"| {r['nps']['eroded_date']:.2f} |")

    md = f"""# Korea headline table — generated from the model, do not hand-edit

Regenerate with `scripts/gen_korea_evidence_tables.py`. Chain: the ASSEMBLED V2 run (net
displacement — re-employment, survivor raises, demand destruction — with EI benefit
outlays included), BOK-published exposure × anchored adoption presets × documented
wage-linked-share band edges. Matches `web/public/data/korea.json` (parity-tested in
`tests/test_korea_bundle.py`; the bridge is pinned in `tests/test_korea_assembly.py`).

Published baselines the shifts move against: NHI (reform variant) depletes **{
first_negative_year(NHI_REFORM.reserves, NHI_REFORM.base_year)}** (NABO Focus 162); EI planned reserves reach
**₩{EI_BASELINE.reserves[-1]:.1f}tn** by 2029 ([표 151]); NPS (post-reform) depletes
**2065** (NABO [표 25]; pre-reform 2057 — the reform bought eight years).

Rows below are the central exposure read; the band summary additionally sweeps the
figure-read error axis (±0.5pp), 36 projections total.

| Preset | NHI share | NPS share | NHI yrs earlier | NHI depletion | EI 2029 shortfall (₩tn) | NPS yrs given back | NPS depletion |
|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Fast worlds — Korinek-Suh translations (mid shares, separate rows, never band edges)

Cognitive channel only: Korea has no published robot-exposure vector wired, so these
UNDERSTATE displacement in manual occupations.

| Scenario | NHI share | NPS share | NHI yrs earlier | NHI depletion | EI 2029 shortfall (₩tn) | NPS yrs given back | NPS depletion |
|---|---|---|---|---|---|---|---|
{chr(10).join(agi_rows)}

## Band summary (the numbers for the slide)

- **NHI depletion pulled forward: {min(agg['nhi']):.2f}–{max(agg['nhi']):.2f} years**
- **EI 2029 planned-rebuild shortfall: ₩{min(agg['ei']):.1f}–{max(agg['ei']):.1f}tn**
  (of ₩{EI_BASELINE.reserves[-1]:.1f}tn planned — benefit outlays included)
- **NPS: {min(agg['nps']):.2f}–{max(agg['nps']):.2f} of the reform's eight bought years
  given back** (central preset: {min(nps_central):.2f}–{max(nps_central):.2f})
"""
    (OUT / "headline-table.md").write_text(md, encoding="utf-8")
    print(f"wrote {OUT / 'headline-table.md'} "
          f"({len(rows)} band rows + {len(agi_rows)} AGI rows)")


if __name__ == "__main__":
    main()
