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

### NPS pension headline (2026-08-10; corrected same day by the test pass)

**Correction:** the first run was misdescribed — the presets lacked `adoption_reach_year`, so
the 40-year run ramped linearly to 2065 instead of the documented "ramp to 2035 then flat".
Fixed (`adoption_reach_year=9`; a regression test pins the path shape) and recomputed. The
10-year NHI/EI results were identical under both shapes and stand unchanged.

40-year horizon, ramp to 2035 then flat, NPS share band edges: **automation gives back
0.34–1.64 of the reform's eight bought years** (central preset: **0.67–0.84**). Zero-erosion
anchor reproduces 표 25 exactly; NABO's own post-reform depletion is **2065** (quote NABO's
2065, not the ministry-attributed ~2064).

## Addendum 2026-09-08 — the diffusion family's labour-market anchor

The three diffusion presets (slow / central / fast) were defined with empty overrides and
so inherited the engine's shipped `reabsorption_rate = 0.0`: no displaced worker was ever
re-employed in the headline case — an inherited default, never a calibrated choice (every
other Korea preset and every US preset sets a rate). Korean anchor now applied via
`KOREA_DIFFUSION_LABOUR` in `fiscal_model/korea_scenarios.py`:

| Field | Value | Evidence |
|---|---|---|
| `reabsorption_rate` | **0.25/yr** | 고용노동부 구직급여 수급 중 재취업률 30.6% (2024; 26.9% 2021 → 30.3% 2023), ~120 days to re-employment — annualizes to ~0.35–0.45/yr for ALL recipients. AI displacement is structural (re-entry into the finite service floor), so the all-recipient rate is an upper anchor; discounted to 0.25 (Alex's judgment; DvW slack band 0.15–0.35). |
| `reemployment_haircut` | 0.13 | Farber 2015 central — no Korean primary on re-employment wages yet (KLI ask outstanding). |

Effect on the central headlines (zero re-employment → 0.25): NHI 0.50 → 0.43 yrs earlier;
EI ₩5.5 → 5.2tn short (outlays dominate, robust); NPS 1.14 → 0.19 of 8 bought years; jobs
0.91M → 0.40M; Δu +2.7 → +1.1pp. The recapture finding flips for the pension only: 100%
corporate recapture (₩7.6tn/yr) now makes the pension whole, recovers 0.26 of NHI's 0.43
years, and refunds under a fifth of the EI shortfall.

## Addendum 2026-09-09 — the trio's remaining inherited defaults, and the channel conventions

The 2026-09-09 review found the diffusion trio still inheriting US engine defaults it had
never chosen (`ui_weeks`, the disposition triple, five more) and three US-only channels
running in every Korea preset. Resolution (Alex's decisions):

| Field | Value | Evidence / decision |
|---|---|---|
| `ui_weeks` | **26** (kept) | 26 weeks = 182 days, mid-band of Korea's statutory 구직급여 소정급여일수 120–270 days (by age and insured period). Kept at the engine value by decision; now an explicit, provenanced override. |
| disposition (retained / price / survivor), `attrition_rate`, `survivor_elasticity`, `auto_cost`, `demand_multiplier`, `price_passthrough`, `productivity_passthrough`, `lfp_exit_rate` | shipped values, now explicit | Behavioural conventions shared with every preset on both sites — carried, listed in `KOREA_DIFFUSION_LABOUR` with provenance, and covered by the porting-discipline test. Numbers unchanged. |
| `compute_effective_rate` | **0.0**, every Korea preset | The US gross-receipts rate on compute-pool spend has no Korean counterpart: compute spend flows overwhelmingly to foreign vendors. Was inheriting 0.10 (~7% of the corporate-recapture transfer) and sat on the rail; delisted and pinned. |
| `shareholder_eff_rate` | **0.0**, every Korea preset | The capital-gains tax on the shareholder windfall is parameterised on US holder structure and realization rates; Korea taxes listed-share gains only for major shareholders, so the tax leg is off. The undistributed-earnings level keeps accruing at the engine's convention because the NPS mandate lever is a share of it. Disclosed. |
| `ssdi_annual` | **0.0**, every Korea preset | A USD benefit the engine was spending as won (a ₩1bn no-op). Off, disclosed. |

`KOREA_CHANNEL_CONVENTIONS` in `fiscal_model/korea_scenarios.py` applies the three channel
switches beneath every preset's overrides (in `korea_preset_params`).

Effect: fund headlines unchanged (NHI 0.43 / EI ₩5.2tn / NPS 0.19). The 2035 general-account
result moves from ₩1.57tn better off to **₩0.47tn better off** — still no widening for VAT
to cover, but no longer resting on US channels. The corporate-recapture transfer is
**₩7.0tn/yr** (was 7.6); at 100% it still makes the pension whole, recovers 0.24 of NHI's
0.43 years, and refunds ₩0.7tn of the ₩5.2tn EI shortfall.
