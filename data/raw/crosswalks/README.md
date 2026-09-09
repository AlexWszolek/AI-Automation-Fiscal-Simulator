# Occupation crosswalks (SOC → ISCO-08 → KSCO major)

- `soc10_isco08.dta` — SOC 2010 (6-digit) → ISCO-08 (4-digit), one-to-many. The BLS/SOC Policy
  Committee crosswalk as distributed in the CWS-IBS `onetsoc_to_isco` Stata bundle, mirrored by
  github.com/eworx-org/iscoCrosswalks (`data-raw/stata_dset/onetsoc_to_isco_cws_ibs/`). The BLS
  page itself is bot-walled to scripts. 1,131 pairs. Retrieved 2026-09-09.
- `soc_2010_to_2018.xlsx` — O*NET-SOC 2010 → 2018 SOC, O*NET Resource Center occupation listings
  (same mirror, `data-raw/onet_classification/OccupationalListings/Crosswalks/`). Retrieved 2026-09-09.

Consumed by `scripts/gen_korea_exposure_map.py`, which maps the US per-SOC exposure measures
(Yale Budget Lab PCA → percentile share; Webb 2020 robot-patent exposure) onto KSCO 6th major
groups, US-employment-weighted, and emits the literals in `fiscal_model/korea_exposure.py`.
