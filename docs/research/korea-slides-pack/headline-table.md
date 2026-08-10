# Korea headline table — generated from the model, do not hand-edit

Regenerate with `scripts/gen_korea_evidence_tables.py`. Config: BOK-published exposure
(HELC within-group shares) × anchored adoption presets (ramp 2026→2035, flat after) ×
documented wage-linked-share band edges. Direct chain: displacement CEILING, gross of
re-employment — disclosed wherever these numbers appear. Test-pinned in
`tests/test_korea_integration.py`.

Published baselines the shifts move against: NHI (reform variant) depletes **2029** (NABO Focus 162); EI planned reserves reach
**₩21.8tn** by 2029 ([표 151]); NPS (post-reform) depletes
**2065** (NABO [표 25]; pre-reform 2057 — the reform bought eight years).

| Preset | NHI share | NPS share | NHI yrs earlier | NHI depletion | EI 2029 shortfall (₩tn) | NPS yrs given back | NPS depletion |
|---|---|---|---|---|---|---|---|
| korea-slow | 0.65 | 0.75 | 0.25 | 2029.62 | 0.7 | 0.34 | 2065.25 |
| korea-slow | 0.65 | 0.95 | 0.25 | 2029.62 | 0.7 | 0.43 | 2065.16 |
| korea-slow | 0.97 | 0.75 | 0.35 | 2029.52 | 0.7 | 0.34 | 2065.25 |
| korea-slow | 0.97 | 0.95 | 0.35 | 2029.52 | 0.7 | 0.43 | 2065.16 |
| korea-central | 0.65 | 0.75 | 0.44 | 2029.43 | 1.5 | 0.67 | 2064.92 |
| korea-central | 0.65 | 0.95 | 0.44 | 2029.43 | 1.5 | 0.84 | 2064.75 |
| korea-central | 0.97 | 0.75 | 0.60 | 2029.28 | 1.5 | 0.67 | 2064.92 |
| korea-central | 0.97 | 0.95 | 0.60 | 2029.28 | 1.5 | 0.84 | 2064.75 |
| korea-fast | 0.65 | 0.75 | 0.73 | 2029.14 | 3.0 | 1.31 | 2064.28 |
| korea-fast | 0.65 | 0.95 | 0.73 | 2029.14 | 3.0 | 1.64 | 2063.95 |
| korea-fast | 0.97 | 0.75 | 0.93 | 2028.94 | 3.0 | 1.31 | 2064.28 |
| korea-fast | 0.97 | 0.95 | 0.93 | 2028.94 | 3.0 | 1.64 | 2063.95 |

## Band summary (the numbers for the slide)

- **NHI depletion pulled forward: 0.25–0.93 years**
- **EI 2029 planned-rebuild shortfall: ₩0.7–3.0tn**
- **NPS: 0.34–1.64 of the reform's eight bought years
  given back** (central preset: 0.67–0.84)
