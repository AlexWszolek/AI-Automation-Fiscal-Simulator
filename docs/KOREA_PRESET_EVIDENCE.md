# Korea preset evidence — provenance scaffold

Companion to [PRESET_EVIDENCE.md](PRESET_EVIDENCE.md) (US presets) for the Korea port. Same
contract: every number a Korea scenario uses must trace to a row here, and every row to a primary
source (✓) — ⚠ rows cannot feed anything external. Verified facts live in
[research/korea-fiscal-system.md](research/korea-fiscal-system.md); primary documents in
[research/sources/](research/sources/). This file exists from Phase 6 scaffolding onward so the
provenance discipline is structural, not retrofitted.

## Field status

| Field / input | Value(s) | Status | Source |
|---|---|---|---|
| Cell structure | 209 occupation × wage-bracket cells; 12,413,858 covered workers (2025) | ✓ | MOEL `PAYM39`/`PAYN42`, validated in `scripts/fetch_korea_tables.py` |
| Payroll components | 20.9048% of payroll over five schemes; pension capped ₩79.08m/yr | ✓ | 보건복지부/NPS notices; 「2026 대한민국 사회보험」 |
| Income-tax chain | deduction → 6–45% brackets → wage-earner credit → +10% local | ✓ | NTS schedule; KOTRA 2025 (local copy) |
| Transfers | EI benefit (cap ₩68,100 / floor ₩66,048 / 120–270 days); EITC trapezoids; Basic Pension ₩349,700 | ✓ | 고용보험법/시행령 via the annual; 조특법 §100조의5 |
| Demography path | 2026=1.0 → 2035=0.898 → 2050=0.689 (medium variant) | ✓ | Statistics Korea 장래인구추계 (press-release tables, local) |
| NHI fund path | 2026–35 both variants; depletion 2031 / 2029 | ✓ | NABO Focus 162 |
| EI fund path | 2026–29 whole-fund baseline (embeds planned PCMF borrowing) | ✓ | 「2026 대한민국 사회보험」 [표 151] |
| NPS fund path | 표 25 knots 2025–2065, annual-interpolated; deficit 2047, **depletion 2065** (pre-reform 2057 → 8 bought years) | ✓ | NABO 현안보고서 2025-06 (`nabo-pension-reform-analysis-2025.pdf`), fetched via the KDI-aggregator link |
| `wage_linked_share` (EI) | 0.9297 (= ₩18.92tn / ₩20.35tn, FY2025) | ✓ | annual [표 146]/[표 149] |
| `wage_linked_share` (NPS) | band **0.75–0.95**, no central (revenue column is already contributions-only) | ⚠ workplace share of contribution revenue pending (NPS yearbook) | NABO 표 25 |
| `wage_linked_share` (NHI) | band **0.65–0.97**, no central | ⚠ workplace share of contributions pending (NHIS statistics); contributions/revenue 84.9% ✓ and subsidy-tracks-contributions rule ✓ | annual [표 202]/[표 203] |
| **Exposure vector** | within-group HELC shares: clerical 1.00, sales 0.356, professionals 0.218, service 0.107, managers/manual 0 (AI-cognitive channel) | ✓ **figure-read, reconciled** — read from BOK 이슈노트 2025-2 <그림 9> (±0.5pp/segment), accepted because it reconciles with the note's published 24/27/~49 aggregates; IMF SIP Fig. 7 confirms every segment | `fiscal_model/korea_exposure.py`; sources: `bok-issue-note-2025-2-ai-korean-economy.pdf`, `imf-sip-2025-013-ai-korea.pdf` |

## Adoption calibration anchors (for the eventual Korea presets)

Adoption reuses `presets.Preset` + `build_adoption_path` — no new dynamics. What the Korean
evidence pins:

- ✓ **Korea sits EARLIER on the adoption curve than peers**: AI adoption 31% of SMEs vs >50% in
  Germany (OECD, *AI and the Labour Market in Korea*, 2025 — via research doc §6). Korean preset
  `adoption_start` should sit at or below the US presets' starting points.
- ✓ **The technical ceiling is high and near-term**: 38.8% of jobs have >70% of tasks automatable
  at 2023 technology; ~99% at the 2030 expert forecast (KDI monograph 2023-03, first-hand). This
  anchors `cognitive_feasibility`-type ceilings, NOT adoption — KDI's own framing is that
  realization is gated by adoption. The wide feasible-minus-realized gap is the Korean signature.
- ✓ **First-wave composition evidence**: 42.9% of convenience stores/supermarkets and 40.0% of
  coffee/retail considering unmanned automation; kiosks in 1-of-2-to-3 major fast-food outlets
  (research doc §7.2) — service/sales cells lead the cognitive channel in Korea's realized wave.
- Pending: Metaculus/forecast-market anchors for Korean-specific timing (the US evidence file's
  pattern); realized-adoption canaries from Korean firm surveys (KDI ch. 4 firm survey has
  adoption-by-industry rates usable here — extraction TODO).

## Standing constraints

- Preset lever values must sit on the widget grid (`test_ui_grid_representability`) once Korea
  presets reach the app layer.
- The direct exposure × adoption chain in `korea_scenarios.korea_erosion_paths` is a displacement
  **ceiling** (gross of reabsorption); headline scenarios must either disclose that or feed net
  displacement from an assembled V2 run.
- NHI headline sensitivity must show the `wage_linked_share` band edges until the NHIS split
  lands.

## First sourced run (2026-08-10) — model output, direct chain

Config: BOK HELC exposure × `KOREA_PRESETS` adoption (slow/central/fast, linear 10y) ×
NHI wage-linked band edges × exposure read-error ±0.5pp — 18 runs, `korea_headline_band()`.
**Gross-of-reabsorption ceiling, disclosed.**

- **NHI (reform variant, published-equivalent depletion 2029.87):** pulled forward
  **0.24–0.95 years** (central preset: 0.44–0.60 depending on the NHI share edge).
- **EI:** the planned rebuild to ₩21.8tn by 2029 falls **₩0.7–3.1tn short** (central ₩1.5tn).
- **Composition (central, 2035):** erosion ≈ 8% across institutions — income tax 8.57%,
  flat schemes 8.05%, pension 7.93%. The clerical epicentre (mid-wage, 17.4% of employment)
  spreads damage EVENLY with a slight general-account tilt; the sharp institutional splits
  live in the what-if decompositions (white-collar-only vs elementary-only), not the central.
- Still absent from headlines: NPS (no post-reform published path) — the fund where the
  "years pulled forward" framing has decades to work with.

### NPS pension headline added (2026-08-10, same session)

40-year horizon, adoption ramp to 2035 then flat (conservative on a 2065 horizon, disclosed),
NPS share band edges: **automation gives back 0.20–0.98 of the reform's eight bought years**
(central preset: 0.40–0.50). Zero-erosion anchor reproduces 표 25 exactly; NABO's own
post-reform depletion is **2065** (quote NABO's 2065, not the ministry-attributed ~2064).
