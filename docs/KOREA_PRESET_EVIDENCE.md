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
| NPS fund path | — | **absent by design** | post-reform path = top document ask |
| `wage_linked_share` (EI) | 0.9297 (= ₩18.92tn / ₩20.35tn, FY2025) | ✓ | annual [표 146]/[표 149] |
| `wage_linked_share` (NHI) | band **0.65–0.97**, no central | ⚠ workplace share of contributions pending (NHIS statistics); contributions/revenue 84.9% ✓ and subsidy-tracks-contributions rule ✓ | annual [표 202]/[표 203] |
| **Exposure vector** | — | **BLOCKED — refuses to run** (`korea_scenarios.require_exposure`) | one of OECD StatLink / BOK 이슈노트 2023-30 / IMF SIP — top ask in `research/korea-primary-docs-request.md` |

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
