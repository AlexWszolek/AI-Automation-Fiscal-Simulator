"""Korean transfer programmes as national formulas — no archetype bake needed.

Korea has no subnational benefit variation, so the three programmes the Korea port models
are statute-level formulas (all ✓-verified 2026-08-07, docs/research/korea-fiscal-system.md
§3 Channel 5 / §2.3):

- **구직급여 (EI unemployment benefit)** — the UI-window analogue the kernel's residual
  income uses. 60% of the base daily wage, but the 2026 floor (80% of the 8-hour minimum
  wage, ₩66,048/day) and cap (₩68,100/day, 시행령 §68) nearly touch: the benefit is
  effectively FLAT ≈ ₩2.0–2.07m/month for almost every wage level. Duration 120–270 days by
  age and insured years (고용보험법 §50, post-2019.10 schedule).
- **근로장려금 (Korean EITC)** — the statutory trapezoids of 조세특례제한법 §100조의5
  (amended 2024-12-31), household-type keyed. Requires earned income: displacement zeroes it.
- **기초연금 (Basic Pension)** — ₩349,700/month (2026), bottom 70% of the 65+ population by
  income recognition. The finite-refuge landing zone: an outlay-side, 65+ mechanism, kept as
  constants here for the projector/outlay side rather than the working-age marginal delta.

Alignment with the US seam: the US kernel consumes (a) UI as residual income during the
displacement window and (b) a marginal means-tested transfer delta. Korea's (a) is
`ei_spell_benefit` (daily benefit × entitlement days — NOT monthly × days); Korea's (b) is,
in v1, the EITC alone via `kr_eitc_delta_on_displacement`, which returns
credit(after) − credit(before): NEGATIVE for a worker who loses the in-work credit, exactly
the sign the seam's marginal object carries. Use the functions, not a re-derivation. NBLSS
(생계급여 etc.) is deliberately deferred: its components are still ⚠ in the research doc.
"""
from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------- 구직급여 (EI benefit), 2026
EI_REPLACEMENT = 0.60                    # 고용보험법 §46: 60% of the base daily wage
EI_DAILY_CAP = 68_100.0                  # 시행령 §68 (2026: raised 66,000 → 68,100)
MIN_WAGE_HOURLY = 10_320.0               # 2026 minimum wage (₩82,560/day at 8h)
EI_DAILY_FLOOR = 0.80 * MIN_WAGE_HOURLY * 8.0        # 최저구직급여일액 = ₩66,048
_DAYS_PER_YEAR = 365.0                   # 기초일액 is calendar-day average pay
_DAYS_PER_MONTH = _DAYS_PER_YEAR / 12.0

# 소정급여일수 (benefit duration, days) by insured years; 고용보험법 §50 schedule, 2019.10–
_EI_TENURE_KNOTS = np.array([0.0, 1.0, 3.0, 5.0, 10.0])          # insured years (lower bounds)
_EI_DAYS_UNDER_50 = np.array([120.0, 150.0, 180.0, 210.0, 240.0])
_EI_DAYS_50_PLUS = np.array([120.0, 180.0, 210.0, 240.0, 270.0])


def ei_daily_benefit(wage_year_won: np.ndarray) -> np.ndarray:
    """60% of the calendar-day wage, clipped to the statutory floor and cap. The floor
    assumes 8 contracted hours/day (part-time floors scale with hours; not modelled)."""
    base_daily = np.asarray(wage_year_won, dtype=float) / _DAYS_PER_YEAR
    return np.clip(EI_REPLACEMENT * base_daily, EI_DAILY_FLOOR, EI_DAILY_CAP)


def ei_monthly_benefit(wage_year_won: np.ndarray) -> np.ndarray:
    return ei_daily_benefit(wage_year_won) * _DAYS_PER_MONTH


def ei_duration_days(insured_years: np.ndarray, age_50_plus=False) -> np.ndarray:
    yrs = np.asarray(insured_years, dtype=float)
    # negative or NaN input would silently index-wrap to the MAXIMUM entitlement
    assert np.isfinite(yrs).all() and (yrs >= 0.0).all(), "insured_years must be finite ≥ 0"
    i = np.searchsorted(_EI_TENURE_KNOTS, yrs, side="right") - 1
    table = _EI_DAYS_50_PLUS if age_50_plus else _EI_DAYS_UNDER_50
    return table[i]


def ei_spell_benefit(wage_year_won, insured_years, age_50_plus=False) -> np.ndarray:
    """Total benefit over one displacement spell (₩): daily benefit × entitlement days."""
    return ei_daily_benefit(wage_year_won) * ei_duration_days(insured_years, age_50_plus)


# ------------------------------------------------- 근로장려금 (EITC), 조특법 §100조의5, 2026
# household type -> (phase-in end, plateau end, ceiling, maximum credit), all ₩/year
EITC_SCHEDULE = {
    "single": (4_000_000.0, 9_000_000.0, 22_000_000.0, 1_650_000.0),
    "single_earner": (7_000_000.0, 14_000_000.0, 32_000_000.0, 2_850_000.0),
    "dual_earner": (8_000_000.0, 17_000_000.0, 44_000_000.0, 3_300_000.0),
}
EITC_ASSET_HALVING = 170_000_000.0       # assets ≥ ₩170m -> 50% payment (§100조의5 ④)
EITC_ASSET_CEILING = 240_000_000.0       # assets ≥ ₩240m -> ineligible (§100조의3)


def kr_eitc(annual_income: np.ndarray, household: str = "single",
            asset_halved: bool = False) -> np.ndarray:
    """The statutory trapezoid: income × (max/phase-in-end), plateau at max, then linear to
    zero at the ceiling. Zero outside — including at zero income: the credit requires
    earned income, which is what makes displacement zero it."""
    lo, mid, hi, mx = EITC_SCHEDULE[household]
    y = np.asarray(annual_income, dtype=float)
    credit = np.select(
        [y < lo, y < mid, y < hi],
        [y * (mx / lo), np.full_like(y, mx), mx - (y - mid) * (mx / (hi - mid))],
        default=0.0)
    # the phase-in branch fires for y < 0 too (business losses, data errors) — the credit
    # requires positive earned income, never a negative payment
    credit = np.maximum(credit, 0.0)
    return credit * (0.5 if asset_halved else 1.0)


def kr_eitc_delta_on_displacement(wage_year_won, residual_income=0.0,
                                  household: str = "single") -> np.ndarray:
    """Marginal EITC object, US-seam semantics: credit(after) − credit(before). Negative
    for a phase-in/plateau worker who loses the in-work credit entirely."""
    w = np.asarray(wage_year_won, dtype=float)
    return kr_eitc(np.full_like(w, residual_income), household) - kr_eitc(w, household)


# ---------------------------------------------------------------- 기초연금 (Basic Pension), 2026
BASIC_PENSION_MONTH = 349_700.0          # standard payment, CPI-indexed
BASIC_PENSION_COVERAGE = 0.70            # bottom 70% of the 65+ population
BASIC_PENSION_THRESHOLD_SINGLE = 2_470_000.0    # 소득인정액/month, 2026 selection
BASIC_PENSION_THRESHOLD_COUPLE = 3_952_000.0


def basic_pension_year() -> float:
    """Annual outlay per eligible 65+ recipient (₩). An upper bound per recipient: the
    statutory reductions (couple reduction, National-Pension-linked reduction) are not
    modelled — outlay-side scenarios should treat this as the standard-rate ceiling."""
    return BASIC_PENSION_MONTH * 12.0
