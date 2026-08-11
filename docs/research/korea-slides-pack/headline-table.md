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
| korea-slow | 0.65 | 0.75 | 0.24 | 2029.64 | 2.8 | 0.52 | 2065.07 |
| korea-slow | 0.65 | 0.95 | 0.24 | 2029.64 | 2.8 | 0.65 | 2064.94 |
| korea-slow | 0.97 | 0.75 | 0.33 | 2029.54 | 2.8 | 0.52 | 2065.07 |
| korea-slow | 0.97 | 0.95 | 0.33 | 2029.54 | 2.8 | 0.65 | 2064.94 |
| korea-central | 0.65 | 0.75 | 0.42 | 2029.45 | 5.5 | 1.01 | 2064.58 |
| korea-central | 0.65 | 0.95 | 0.42 | 2029.45 | 5.5 | 1.26 | 2064.33 |
| korea-central | 0.97 | 0.75 | 0.57 | 2029.30 | 5.5 | 1.01 | 2064.58 |
| korea-central | 0.97 | 0.95 | 0.57 | 2029.30 | 5.5 | 1.26 | 2064.33 |
| korea-fast | 0.65 | 0.75 | 0.70 | 2029.18 | 11.0 | 1.92 | 2063.67 |
| korea-fast | 0.65 | 0.95 | 0.70 | 2029.18 | 11.0 | 2.38 | 2063.21 |
| korea-fast | 0.97 | 0.75 | 0.88 | 2028.99 | 11.0 | 1.92 | 2063.67 |
| korea-fast | 0.97 | 0.95 | 0.88 | 2028.99 | 11.0 | 2.38 | 2063.21 |

## Fast worlds — Korinek-Suh translations (mid shares, separate rows, never band edges)

Cognitive channel only: Korea has no published robot-exposure vector wired, so these
UNDERSTATE displacement in manual occupations.

| Scenario | NHI share | NPS share | NHI yrs earlier | NHI depletion | EI 2029 shortfall (₩tn) | NPS yrs given back | NPS depletion |
|---|---|---|---|---|---|---|---|
| korea-agi-20y | 0.81 | 0.85 | 1.25 | 2028.62 | 17.1 | 3.82 | 2061.77 |
| korea-agi-5y | 0.81 | 0.85 | 2.14 | 2027.74 | 59.2 | 6.59 | 2059.00 |

## Band summary (the numbers for the slide)

- **NHI depletion pulled forward: 0.23–0.90 years**
- **EI 2029 planned-rebuild shortfall: ₩2.6–11.4tn**
  (of ₩21.8tn planned — benefit outlays included)
- **NPS: 0.49–2.44 of the reform's eight bought years
  given back** (central preset: 0.96–1.30)
