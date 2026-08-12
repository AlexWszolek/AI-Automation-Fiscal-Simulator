"""Korea's working-age population path — the numbers behind `V2Params.demography_path`.

Source (✓ primary): Statistics Korea, 장래인구추계 2022~2072 (2023-12 release), statistical
table 7 「생산연령인구(15-64세) 및 구성비」, **medium variant (중위추계)** — the standard
reference projection NABO's long-term outlook also uses. Local copy:
`docs/research/sources/kostat-population-projection-2022-2072-press.pdf` (table at p. 60).

The published table is annual through 2040, then 5-yearly knots to 2070 plus a final 2072
value; between knots we interpolate linearly (disclosed; the model's default 10-period
horizon never needs it).
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

# The 저위/고위 (low/high) scenario working-age series from the SAME press-release annex
# table as the medium knots above ([표 7] 생산연령인구(15-64세), 저위추계/고위추계 blocks) —
# extracted 2026-08-11, medium block re-verified against WORKING_AGE_K 26/26. These are the
# published alternative scenarios, exposed as a SELECTOR (never a continuous slider: paths
# are published objects, not lever space). By 2072: low 13.3m / medium 16.6m / high 20.1m.
WORKING_AGE_BY_VARIANT = {
    "medium": None,        # filled below — WORKING_AGE_K stays the canonical medium dict
    "low": {
    2022: 36743.0,
    2023: 36571.0,
    2024: 36260.0,
    2025: 35785.0,
    2026: 35302.0,
    2027: 34941.0,
    2028: 34506.0,
    2029: 34164.0,
    2030: 33758.0,
    2031: 33352.0,
    2032: 32914.0,
    2033: 32417.0,
    2034: 31808.0,
    2035: 31219.0,
    2036: 30580.0,
    2037: 29963.0,
    2038: 29336.0,
    2039: 28710.0,
    2040: 28139.0,
    2045: 25403.0,
    2050: 22765.0,
    2055: 20645.0,
    2060: 18128.0,
    2065: 15753.0,
    2070: 13974.0,
    2072: 13344.0,
},
    "high": {
    2022: 36743.0,
    2023: 36572.0,
    2024: 36395.0,
    2025: 36039.0,
    2026: 35672.0,
    2027: 35424.0,
    2028: 35099.0,
    2029: 34867.0,
    2030: 34568.0,
    2031: 34267.0,
    2032: 33933.0,
    2033: 33536.0,
    2034: 33024.0,
    2035: 32532.0,
    2036: 31985.0,
    2037: 31459.0,
    2038: 30923.0,
    2039: 30394.0,
    2040: 29935.0,
    2045: 27975.0,
    2050: 26227.0,
    2055: 25060.0,
    2060: 23385.0,
    2065: 21702.0,
    2070: 20479.0,
    2072: 20070.0,
},
}

MODEL_BASE_YEAR = 2026
WORKING_AGE_BY_VARIANT["medium"] = WORKING_AGE_K


def working_age_k(year: int, variant: str = "medium") -> float:
    """Published value, or linear interpolation between the 5-year knots after 2040."""
    table = WORKING_AGE_BY_VARIANT[variant]
    if year in table:
        return float(table[year])
    years = sorted(table)
    if not years[0] <= year <= years[-1]:
        raise ValueError(f"{year} outside the published projection ({years[0]}–{years[-1]})")
    lo = max(y for y in years if y < year)
    hi = min(y for y in years if y > year)
    frac = (year - lo) / (hi - lo)
    return table[lo] + frac * (table[hi] - table[lo])


def korea_demography_path(n_periods: int = 10, base_year: int = MODEL_BASE_YEAR,
                          variant: str = "medium") -> tuple:
    """Scale factors for `V2Params.demography_path`: period t is (base_year + t) relative to
    base_year, so path[0] == 1.0 by construction. `variant` selects among the PUBLISHED
    KOSIS scenarios (low/medium/high) — the demographic risk axis, as published paths only."""
    if n_periods < 1:
        raise ValueError("n_periods must be ≥ 1")
    base = working_age_k(base_year, variant)
    return tuple(working_age_k(base_year + t, variant) / base for t in range(n_periods))
