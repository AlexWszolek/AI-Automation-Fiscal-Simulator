# Canonical data files (`data/raw/`)

Copied from `~/Downloads` and renamed to clean snake_case. Units are **not** normalized
on disk — they are normalized in `loaders.py`. See `docs/PROJECT_BRIEFING_v2.md` §3.

| Canonical name | Original (Downloads) | Units | Key sheets |
|---|---|---|---|
| `occ_industry_matrices_v2_aligned.xlsx` | `occ_industry_matrices_v2_aligned.xlsx` | emp = 000s; comp = $m | Detail/Sector employment (000s), Detail/Sector compensation ($m) |
| `occupation_ai_exposure.xlsx` | `Occupation AI Exposure(Claude).xlsx` | PCA score (standardized) | Occupation AI exposure; Industry exposure (sector)/(detail) |
| `capital_income_by_sector.xlsx` | `Capital Income by Sector(Claude).xlsx` | $m | Capital income & tax by sector |
| `government_fiscal_accounts.xlsx` | `Government Fiscal Accounts(Claude).xlsx` | $billions | Receipts; Transfers & stabilizers; Base linkage & eff. rates |
| `state_occupation_numbers_oews.xlsx` | `State Occupation Numbers(Claude).xlsx` | wages = $/yr & $/hr; emp = persons | State OEWS (all groups); Coverage; Areas |
| `taxable_consumption_base_by_state.xlsx` | `Taxable_Consumption_Base_by_State(Claude).xlsx` | $m; rates = fraction | Effective consumption tax; PCE taxability classification |
| `household_archetypes_by_state.xlsx` | `household_archetypes_by_state.xlsx` | income = $ (dollars) | Household archetypes by SOC-state |
| `tax_side_schedule.xlsx` | `tax_side_schedule.xlsx` | tax = $; rates = fraction | Federal/State/Payroll params; baked income & FICA schedules |
| `robot_exposure_by_soc.xlsx` | `robot_exposure_by_soc.xlsx` | pct_robot = 0–100 | Robot exposure by SOC (Webb 2020) — physical-automation channel for `levers.py` |

**Not copied into the repo** (too large; external inputs handled later):
- ACS PUMS 1-year 2024 extracts (`~/Downloads/ACSPUMS1Y2024_*.xlsx`) — source for the NOC
  (number-of-children) cross-tab used by the PolicyEngine transfer bake.

## Korea (`data/raw/korea/`)

Fetched 2026-08-07 from the MOEL statHtml mirror of KOSIS (`stathtml.moel.go.kr`, orgId 118,
고용형태별근로실태조사 — Survey on Labour Conditions by Employment Type, an **establishment
survey**: ~12.4m of ~22m wage workers, skewed to larger firms; no section O public
administration). `scripts/fetch_korea_tables.py` automates the site's bulk export; the
`.xml.gz` files are the raw SpreadsheetML byte-for-byte as served (canonical), `.meta.json`
records the dimension code→label maps, and the `.tidy.csv` files are regenerable offline
(`--parse-only`, gitignored). The fetch validates 2025 anchors against
`docs/research/korea-fiscal-system.md` §9.0 before writing.

| File | Content | Units | Vintage |
|---|---|---|---|
| `DT_118N_PAYM39.xml.gz` | occupation (KSCO 6th major, 9+total) × sex × wage bracket (24+total) × age (10+total): worker count, hours | persons; hours/month; brackets in ₩1,000/month | 2020–2025 |
| `DT_118N_PAYN42.xml.gz` | industry (18 KSIC sections+total) × education (4+total) × sex × age: 14 items incl. 월임금총액 (total monthly wage), 정액/초과/특별급여 split, tenure, hours, worker count | ₩1,000/month; persons | 2020–2025 |
