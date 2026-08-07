"""Korean wage-earner income tax — the verified four-stage chain, on annual wages.

Sources (all ✓, docs/research/korea-fiscal-system.md §3 Channel 1): the NTS bracket schedule
(2023–2025 tax years, current law) and KOTRA *Taxation in Korea 2025*
(`docs/research/sources/kotra-taxation-in-korea-2025.pdf`) for the wage & salary income
deduction, the basic deduction, the pension/insurance premium deductions, the wage-earner tax
credit, and the +10% local income surtax.

Korea taxes individuals, not households — there is no filing-status dimension (a genuine
simplification over the US engine). The baseline models a taxpayer with no dependents and the
mechanical deductions every wage earner gets: wage & salary deduction, basic deduction
(₩1.5m), and the employee's own social-insurance contributions (fully deductible). Personal
circumstances beyond that (child credits, card/medical/housing deductions) shift individual
liabilities but are second-order for cell-level means; the simplification is disclosed in the
research doc.
"""
from __future__ import annotations

import numpy as np

# -- stage 1: wage & salary income deduction (근로소득공제), ceiling ₩20m ---------------------
# breakpoints (annual gross, ₩) with (base deduction at breakpoint, marginal rate above it)
_WSD_KNOTS = np.array([0.0, 5_000_000.0, 15_000_000.0, 45_000_000.0, 100_000_000.0])
_WSD_BASE = np.array([0.0, 3_500_000.0, 7_500_000.0, 12_000_000.0, 14_750_000.0])
_WSD_RATE = np.array([0.70, 0.40, 0.15, 0.05, 0.02])
_WSD_CEILING = 20_000_000.0

BASIC_DEDUCTION = 1_500_000.0          # taxpayer; +₩1.5m per dependent (not modelled)

# -- stage 3: bracket schedule, 2023–2025 tax years (tax = base·rate − 누진공제) --------------
_BRACKET_LO = np.array([0.0, 14e6, 50e6, 88e6, 150e6, 300e6, 500e6, 1_000e6])
_BRACKET_RATE = np.array([0.06, 0.15, 0.24, 0.35, 0.38, 0.40, 0.42, 0.45])
_PROG_DEDUCTION = np.array([0.0, 1.26e6, 5.76e6, 15.44e6, 19.94e6, 25.94e6, 35.94e6, 65.94e6])

LOCAL_SURTAX = 0.10                    # 지방소득세: 10% of the national liability


def _wage_salary_deduction(gross: np.ndarray) -> np.ndarray:
    i = np.searchsorted(_WSD_KNOTS, gross, side="right") - 1
    ded = _WSD_BASE[i] + _WSD_RATE[i] * (gross - _WSD_KNOTS[i])
    return np.minimum(ded, _WSD_CEILING)


def _bracket_tax(base: np.ndarray) -> np.ndarray:
    i = np.searchsorted(_BRACKET_LO, base, side="right") - 1
    return base * _BRACKET_RATE[i] - _PROG_DEDUCTION[i]


def _wage_earner_credit(computed_tax: np.ndarray, gross: np.ndarray) -> np.ndarray:
    """근로소득세액공제: 55% of the first ₩1.3m of computed tax, 30% beyond — capped by a
    gross-wage schedule with floors, exactly as published."""
    credit = np.where(computed_tax <= 1_300_000.0,
                      0.55 * computed_tax,
                      715_000.0 + 0.30 * (computed_tax - 1_300_000.0))
    cap = np.select(
        [gross <= 33e6, gross <= 70e6, gross <= 120e6],
        [np.full_like(gross, 740_000.0),
         np.maximum(740_000.0 - (gross - 33e6) * 0.008, 660_000.0),
         np.maximum(660_000.0 - (gross - 70e6) * 0.5, 500_000.0)],
        default=np.maximum(500_000.0 - (gross - 120e6) * 0.5, 200_000.0))
    return np.minimum(credit, cap)


def korea_income_tax(gross_wage: np.ndarray, employee_social: np.ndarray) -> dict:
    """National + local income tax on annual gross wages.

    `employee_social` is the employee's own social-insurance contribution (from
    `PayrollFICA.employee_fica` with the Korea components) — fully deductible under the
    pension-premium and special-income deductions. Passed in rather than recomputed so the
    payroll engine stays the single source of truth for contribution arithmetic.
    """
    gross = np.asarray(gross_wage, dtype=float)
    social = np.asarray(employee_social, dtype=float)
    base = gross - _wage_salary_deduction(gross) - BASIC_DEDUCTION - social
    base = np.maximum(base, 0.0)
    computed = _bracket_tax(base)
    national = np.maximum(computed - _wage_earner_credit(computed, gross), 0.0)
    local = LOCAL_SURTAX * national
    return {"national": national, "local": local, "total": national + local}
