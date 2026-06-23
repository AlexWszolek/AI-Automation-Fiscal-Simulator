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
