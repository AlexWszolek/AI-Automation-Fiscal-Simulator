"""Grounding — turn model outputs into numbers a policy audience can feel.

Two ingredients, both pure (no streamlit):
- `CBOBaseline` / `load_cbo_baseline()`: CBO's February-2026 baseline (data/raw/cbo_baseline_2026.csv,
  FY2025 actual + FY2026-2036 projections). Revenue extrapolates past FY2036 at the baseline's own
  terminal growth rate; deficit/debt/GDP clamp at FY2036 — callers footnote via `.max_year`.
- `ANCHORS` + `ground(value, kind)`: ~15 sourced real-world quantities and a comparator picker that
  renders one caption line ("≈ 2.6 years of the FY2025 federal deficit, on top of what CBO already
  projects"). Every model dollar figure is a CHANGE against a no-AI baseline, so deficit/debt copy
  always carries the "on top of" clause.

ready to paste into a memo — the communicating-with-politicians use case.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

_CSV = Path(__file__).resolve().parent.parent / "data" / "raw" / "cbo_baseline_2026.csv"
REPO_URL = "https://github.com/AlexWszolek/AI-Automation-Fiscal-Simulator"


class CBOBaseline:
    """Accessor over the committed CBO baseline slice ($B, federal fiscal years)."""

    def __init__(self, df: pd.DataFrame):
        self._df = df                       # index = series, columns = int years 2025..2036
        self.min_year = int(df.columns.min())
        self.max_year = int(df.columns.max())
        # the baseline's own terminal nominal revenue growth — used to extrapolate past FY2036
        self.terminal_growth = float(df.loc["total_revenues", self.max_year]
                                     / df.loc["total_revenues", self.max_year - 1] - 1.0)

    def _get(self, series: str, year: int, extrapolate: bool) -> float:
        if year < self.min_year:
            raise ValueError(f"CBO baseline starts at FY{self.min_year} (asked for {year})")
        if year <= self.max_year:
            return float(self._df.loc[series, year])
        if extrapolate:
            return float(self._df.loc[series, self.max_year]
                         * (1.0 + self.terminal_growth) ** (year - self.max_year))
        return float(self._df.loc[series, self.max_year])          # clamp

    def revenue(self, year: int) -> float:
        """Total federal revenues; extrapolated past FY2036 at the terminal growth rate."""
        return self._get("total_revenues", year, extrapolate=True)

    def deficit(self, year: int) -> float:
        """Total deficit AS PUBLISHED (negative = deficit); clamped at FY2036."""
        return self._get("total_deficit", year, extrapolate=False)

    def debt(self, year: int) -> float:
        """Debt held by the public; clamped at FY2036."""
        return self._get("debt_held_by_public", year, extrapolate=False)

    def gdp(self, year: int) -> float:
        return self._get("gdp", year, extrapolate=False)


@lru_cache(maxsize=1)
def load_cbo_baseline() -> CBOBaseline:
    df = pd.read_csv(_CSV, comment="#").set_index("series")
    df.columns = df.columns.astype(int)
    cbo = CBOBaseline(df)
    # fail loud if the committed CSV drifts from the published workbook
    assert abs(cbo.revenue(2026) - 5595.916) < 1e-6, cbo.revenue(2026)
    assert abs(cbo.revenue(2036) - 8300.755) < 1e-6, cbo.revenue(2036)
    assert abs(cbo.deficit(2025) - (-1775.370)) < 1e-3, cbo.deficit(2025)
    assert abs(cbo.debt(2025) - 30172.402) < 1e-3, cbo.debt(2025)
    assert abs(cbo.gdp(2025) - 30362.025) < 1e-3, cbo.gdp(2025)
    return cbo


# ---------------------------------------------------------------------------- anchors
# Real-world quantities a policy reader can feel, all $B/yr or millions of jobs. Each value carries
# its source; the CBO trio must match the committed CSV and the receipts trio must match the repo's
# own 2024 ledger (both cross-checked in tests/test_grounding.py).
ANCHORS: dict[str, tuple[float, str]] = {
    # ---- fiscal ($B) ----
    "cbo_deficit_fy2025": (1775.4, "FY2025 federal deficit (actual) — CBO Feb-2026 Table 1-1"),
    "cbo_debt_public_fy2025": (30172.4, "debt held by the public, end FY2025 — CBO Feb-2026"),
    "federal_revenue_2024": (4982.8, "total 2024 federal receipts — BEA/NIPA (the repo's own ledger)"),
    "individual_income_receipts_2024": (2403.2, "2024 federal individual income-tax receipts — BEA"),
    "state_local_revenue_2024": (3514.9, "total 2024 state & local receipts — BEA (repo ledger)"),
    "defense_outlays_fy2024": (850.0, "FY2024 national-defense discretionary outlays ≈ $850B — CBO"),
    "social_security_outlays_fy2024": (1454.0, "FY2024 Social Security (OASDI) outlays — SSA/CBO"),
    "medicare_net_outlays_fy2024": (869.0, "FY2024 Medicare net outlays (after premiums) — CBO"),
    "apollo_program_total": (300.0, "the entire Apollo program, inflation-adjusted ≈ $300B in 2024$ "
                                    "— Planetary Society ($25.8B nominal; $257B in 2020$)"),
    "k12_public_spending": (880.0, "annual US public K-12 spending ≈ $880B — NCES (2023 vintage)"),
    # ---- jobs (millions) ----
    "great_recession_job_losses_M": (8.7, "peak-to-trough nonfarm payroll losses, Jan 2008-Feb 2010 — BLS"),
    "covid_peak_job_losses_M": (21.9, "nonfarm payroll losses, Feb-Apr 2020 — BLS"),
    "manufacturing_employment_M": (12.9, "total US manufacturing employment, 2024 — BLS CES"),
    "active_duty_military_M": (1.3, "US active-duty military personnel — DoD, 2024"),
    "walmart_us_employees_M": (1.6, "Walmart's US workforce — company fact sheet, 2024"),
    "california_population_M": (39.2, "population of California — Census Bureau, 2024"),
    "germany_population_M": (84.5, "population of Germany — Destatis, 2024"),
    "japan_population_M": (123.8, "population of Japan — Statistics Bureau of Japan, 2024"),
}

# Per kind: (anchor, template) candidates. {r} = ratio. Among candidates whose ratio lands in
# [0.3, 30], the one NEAREST ×1 wins (log distance — 0.5× and 2× are equally near); fallback:
# nearest overall. A ratio within ±7% of 1 drops the "{r}× " multiplier ("≈ the population of
# Japan"). Deficit/debt kinds carry the "on top of what CBO already projects" clause — every
# model figure is a delta vs no-AI. EXCEPTION: debt_stock ALWAYS uses deficit-years (user call:
# "extra years of the federal deficit" is the one debt comparison that lands).
_CANDIDATES: dict[str, list[tuple[str, str]]] = {
    "fed_deficit_flow": [
        ("cbo_deficit_fy2025", "≈ {r}× the FY2025 federal deficit, every year"),
        ("defense_outlays_fy2024", "≈ {r}× the entire FY2024 defense budget, every year"),
        ("social_security_outlays_fy2024", "≈ {r}× annual Social Security outlays, every year"),
        ("apollo_program_total", "≈ {r}× the entire Apollo program, every year"),
    ],
    "debt_stock": [
        ("cbo_deficit_fy2025", "≈ {r} extra years of the FY2025 federal deficit"),
    ],
    "jobs": [
        ("active_duty_military_M", "≈ {r}× the active-duty US military"),
        ("walmart_us_employees_M", "≈ {r}× Walmart's entire US workforce"),
        ("great_recession_job_losses_M", "≈ {r}× the jobs lost in the Great Recession"),
        ("manufacturing_employment_M", "≈ {r}× all of US manufacturing"),
        ("covid_peak_job_losses_M", "≈ {r}× the jobs lost at the COVID trough"),
        ("california_population_M", "≈ {r}× the population of California"),
        ("germany_population_M", "≈ {r}× the population of Germany"),
        ("japan_population_M", "≈ {r}× the population of Japan"),
    ],
    "state_flow": [
        ("k12_public_spending", "≈ {r}× what all states spend on K-12 schools, every year"),
        ("apollo_program_total", "≈ {r}× the entire Apollo program, every year"),
    ],
    "revenue_flow": [
        ("individual_income_receipts_2024", "≈ {r} full years of federal individual income-tax receipts"),
        ("defense_outlays_fy2024", "≈ {r}× the FY2024 defense budget"),
        ("apollo_program_total", "≈ {r}× the entire Apollo program"),
    ],
}
_ON_TOP = {"fed_deficit_flow", "debt_stock"}


def _fmt_ratio(r: float) -> str:
    return f"{r:,.1f}" if r < 10 else f"{r:,.0f}"


def ground(value: float, kind: str) -> str:
    """One caption line comparing `value` (a model DELTA: $B for fiscal kinds, millions for jobs)
    to the most legible real-world anchor. Empty string for negligible values."""
    import math as _math
    cands = _CANDIDATES[kind]
    mag = abs(float(value))
    if mag < 1e-9:
        return ""
    scored = [(mag / ANCHORS[a][0], a, tmpl) for a, tmpl in cands]
    in_window = [s for s in scored if 0.3 <= s[0] <= 30]
    pool = in_window if in_window else scored
    r, _a, tmpl = min(pool, key=lambda s: abs(_math.log(s[0])))
    if r < 0.095:                    # "≈ 0.0× the Apollo program" communicates nothing — stay silent
        return ""
    if 0.93 <= r <= 1.07 and "{r}× " in tmpl:
        line = tmpl.replace("{r}× ", "")                # "≈ the population of Japan"
    else:
        line = tmpl.format(r=_fmt_ratio(r))
    if kind in _ON_TOP:
        line += (" — on top of what CBO already projects" if value > 0
                 else " — an improvement against what CBO projects")
    elif value < 0 and kind != "jobs":
        line = "an improvement of " + line
    return line


def gdp_years_line(pct_effect: float, normal_rate: float = 0.02) -> str:
    """The real-GDP comparator: how many years of normal growth the effect equals (compounded).
    years = ln(1 + effect) / ln(1 + normal). Empty below noise."""
    if pct_effect < 0.05:
        return ""
    import math as _math
    years = _math.log1p(pct_effect / 100.0) / _math.log1p(normal_rate)
    return (f"≈ {years:,.1f} years of normal (~{normal_rate:.0%}/yr) real growth, "
            "arriving all at once")
