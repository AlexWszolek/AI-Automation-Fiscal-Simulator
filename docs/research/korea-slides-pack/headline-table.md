# Korea headline table — generated from the model, do not hand-edit

Regenerate with `scripts/gen_korea_evidence_tables.py`. Chain: the ASSEMBLED V2 run (net
displacement — re-employment, survivor raises, demand destruction — with EI benefit
outlays included), BOK-published exposure × anchored adoption presets × documented
wage-linked-share band edges. Matches `web/public/data/korea.json` (parity-tested in
`tests/test_korea_bundle.py`; the bridge is pinned in `tests/test_korea_assembly.py`).

Published baselines the shifts move against: NHI (reform variant) depletes **2029** (NABO Focus 162); EI planned reserves reach
**₩21.8tn** by 2029 ([표 151]); NPS (post-reform) depletes
**2065** (NABO [표 25]; pre-reform 2057 — the reform bought eight years).

Rows below are the central exposure read; the band summary additionally sweeps the
figure-read error axis (±0.5pp), 36 projections total.

| Preset | NHI share | NPS share | NHI yrs earlier | NHI depletion | EI 2029 shortfall (₩tn) | NPS yrs given back | NPS depletion |
|---|---|---|---|---|---|---|---|
| korea-slow | 0.65 | 0.75 | 0.20 | 2029.68 | 2.6 | 0.09 | 2065.50 |
| korea-slow | 0.65 | 0.95 | 0.20 | 2029.68 | 2.6 | 0.11 | 2065.48 |
| korea-slow | 0.97 | 0.75 | 0.28 | 2029.59 | 2.6 | 0.09 | 2065.50 |
| korea-slow | 0.97 | 0.95 | 0.28 | 2029.59 | 2.6 | 0.11 | 2065.48 |
| korea-central | 0.65 | 0.75 | 0.36 | 2029.51 | 5.2 | 0.17 | 2065.42 |
| korea-central | 0.65 | 0.95 | 0.36 | 2029.51 | 5.2 | 0.21 | 2065.37 |
| korea-central | 0.97 | 0.75 | 0.50 | 2029.38 | 5.2 | 0.17 | 2065.42 |
| korea-central | 0.97 | 0.95 | 0.50 | 2029.38 | 5.2 | 0.21 | 2065.37 |
| korea-fast | 0.65 | 0.75 | 0.62 | 2029.26 | 10.4 | 0.33 | 2065.26 |
| korea-fast | 0.65 | 0.95 | 0.62 | 2029.26 | 10.4 | 0.42 | 2065.17 |
| korea-fast | 0.97 | 0.75 | 0.81 | 2029.07 | 10.4 | 0.33 | 2065.26 |
| korea-fast | 0.97 | 0.95 | 0.81 | 2029.07 | 10.4 | 0.42 | 2065.17 |

## Fast worlds — Korinek-Suh translations (mid shares, separate rows, never band edges)

Cognitive channel only: Korea has no published robot-exposure vector wired, so these
UNDERSTATE displacement in manual occupations.

| Scenario | NHI share | NPS share | NHI yrs earlier | NHI depletion | EI 2029 shortfall (₩tn) | NPS yrs given back | NPS depletion |
|---|---|---|---|---|---|---|---|
| korea-agi-20y | 0.81 | 0.85 | 1.26 | 2028.62 | 17.2 | 4.18 | 2061.40 |
| korea-agi-5y | 0.81 | 0.85 | 2.14 | 2027.73 | 59.5 | 7.46 | 2058.13 |

## Band summary (the numbers for the slide)

- **NHI depletion pulled forward: 0.19–0.82 years**
- **EI 2029 planned-rebuild shortfall: ₩2.5–10.8tn**
  (of ₩21.8tn planned — benefit outlays included)
- **NPS: 0.08–0.43 of the reform's eight bought years
  given back** (central preset: 0.16–0.22)
