"""Korea's working-age population path — the numbers behind `V2Params.demography_path`.

Source (✓ primary): Statistics Korea, 장래인구추계 2022~2072 (2023-12 release), statistical
table 7 「생산연령인구(15-64세) 및 구성비」, **medium variant (중위추계)** — the standard
reference projection NABO's long-term outlook also uses. Local copy:
`docs/research/sources/kostat-population-projection-2022-2072-press.pdf` (table at p. 60).

The published table is annual through 2040 and 5-yearly to 2072; between the 5-year knots we
interpolate linearly (disclosed; the model's default 10-period horizon never needs it).
Anchors that reconcile with the research doc: 36,743k is 71.1% of the 51,673k 2022 total;
the press headline "332만 decline in ten years" is 36,743 − 33,426 (2022→2032); the 2030
value 34,166k matches the quoted 3,417만.

`korea_demography_path` returns scale factors relative to the model's year 0 (2026), shaped
for `V2Params.demography_path` (index t, year 0 = 1.0). This is data for KOREA scenarios —
it changes no default: `demography_path=None` remains the US behaviour, so no artifact
regeneration is owed.
"""
from __future__ import annotations

# 15-64 population, both sexes, thousands — medium variant, exactly as published
WORKING_AGE_K = {
    2022: 36_743, 2023: 36_572, 2024: 36_328, 2025: 35_912, 2026: 35_488,
    2027: 35_184, 2028: 34_804, 2029: 34_518, 2030: 34_166, 2031: 33_812,
    2032: 33_426, 2033: 32_979, 2034: 32_418, 2035: 31_878, 2036: 31_284,
    2037: 30_712, 2038: 30_130, 2039: 29_552, 2040: 29_029,
    2045: 26_654, 2050: 24_448, 2055: 22_795, 2060: 20_687, 2065: 18_640,
    2070: 17_111, 2072: 16_575,
}

MODEL_BASE_YEAR = 2026


def working_age_k(year: int) -> float:
    """Published value, or linear interpolation between the 5-year knots after 2040."""
    if year in WORKING_AGE_K:
        return float(WORKING_AGE_K[year])
    years = sorted(WORKING_AGE_K)
    if not years[0] <= year <= years[-1]:
        raise ValueError(f"{year} outside the published projection ({years[0]}–{years[-1]})")
    lo = max(y for y in years if y < year)
    hi = min(y for y in years if y > year)
    frac = (year - lo) / (hi - lo)
    return WORKING_AGE_K[lo] + frac * (WORKING_AGE_K[hi] - WORKING_AGE_K[lo])


def korea_demography_path(n_periods: int = 10, base_year: int = MODEL_BASE_YEAR) -> tuple:
    """Scale factors for `V2Params.demography_path`: period t is (base_year + t) relative to
    base_year, so path[0] == 1.0 by construction."""
    base = working_age_k(base_year)
    return tuple(working_age_k(base_year + t) / base for t in range(n_periods))
