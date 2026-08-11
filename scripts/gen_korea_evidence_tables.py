"""Generate the slides-pack headline table FROM the model, so slide numbers cannot drift
from the code. Regenerate after any Korea change:

    .venv/bin/python scripts/gen_korea_evidence_tables.py

Writes docs/research/korea-slides-pack/headline-table.md. The same numbers are pinned by
tests/test_korea_integration.py — if those tests are green, this table matches the model.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_model.korea_funds import (EI_BASELINE, NHI_REFORM, NPS_REFORM,
                                      first_negative_year)
from fiscal_model.korea_scenarios import (KOREA_BAND_KEYS, KOREA_PRESETS, WAGE_LINKED_SHARE,
                                          korea_fund_headlines)
from fiscal_model.presets import build_adoption_path

OUT = Path(__file__).resolve().parent.parent / "docs" / "research" / "korea-slides-pack"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    nhi_lo, nhi_hi = WAGE_LINKED_SHARE["nhi"].low, WAGE_LINKED_SHARE["nhi"].high
    nps_lo, nps_hi = WAGE_LINKED_SHARE["nps"].low, WAGE_LINKED_SHARE["nps"].high

    rows = []
    agg = {"nhi": [], "ei": [], "nps": []}
    for pkey in KOREA_BAND_KEYS:
        a = build_adoption_path(KOREA_PRESETS[pkey], len(NPS_REFORM.revenue))
        for nhi_s in (nhi_lo, nhi_hi):
            for nps_s in (nps_lo, nps_hi):
                r = korea_fund_headlines(a, nhi_wage_linked_share=nhi_s,
                                         nps_wage_linked_share=nps_s)
                nhi_y = r["nhi"]["years_pulled_forward"]
                nps_y = r["nps"]["years_pulled_forward"]
                ei_short = EI_BASELINE.reserves[-1] - r["ei"]["eroded_reserves"][-1]
                agg["nhi"].append(nhi_y)
                agg["nps"].append(nps_y)
                agg["ei"].append(ei_short)
                rows.append(
                    f"| {pkey} | {nhi_s:.2f} | {nps_s:.2f} | {nhi_y:.2f} "
                    f"| {r['nhi']['eroded_date']:.2f} | {ei_short:.1f} "
                    f"| {nps_y:.2f} | {r['nps']['eroded_date']:.2f} |")

    md = f"""# Korea headline table — generated from the model, do not hand-edit

Regenerate with `scripts/gen_korea_evidence_tables.py`. Config: BOK-published exposure
(HELC within-group shares) × anchored adoption presets (ramp 2026→2035, flat after) ×
documented wage-linked-share band edges. Direct chain: displacement CEILING, gross of
re-employment — disclosed wherever these numbers appear. Test-pinned in
`tests/test_korea_integration.py`.

Published baselines the shifts move against: NHI (reform variant) depletes **{
first_negative_year(NHI_REFORM.reserves, NHI_REFORM.base_year)}** (NABO Focus 162); EI planned reserves reach
**₩{EI_BASELINE.reserves[-1]:.1f}tn** by 2029 ([표 151]); NPS (post-reform) depletes
**2065** (NABO [표 25]; pre-reform 2057 — the reform bought eight years).

| Preset | NHI share | NPS share | NHI yrs earlier | NHI depletion | EI 2029 shortfall (₩tn) | NPS yrs given back | NPS depletion |
|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Band summary (the numbers for the slide)

- **NHI depletion pulled forward: {min(agg['nhi']):.2f}–{max(agg['nhi']):.2f} years**
- **EI 2029 planned-rebuild shortfall: ₩{min(agg['ei']):.1f}–{max(agg['ei']):.1f}tn**
- **NPS: {min(agg['nps']):.2f}–{max(agg['nps']):.2f} of the reform's eight bought years
  given back** (central preset: {
    min(x for x, r_ in zip(agg['nps'], rows) if 'central' in r_):.2f}–{
    max(x for x, r_ in zip(agg['nps'], rows) if 'central' in r_):.2f})
"""
    (OUT / "headline-table.md").write_text(md, encoding="utf-8")
    print(f"wrote {OUT / 'headline-table.md'} ({len(rows)} scenario rows)")


if __name__ == "__main__":
    main()
