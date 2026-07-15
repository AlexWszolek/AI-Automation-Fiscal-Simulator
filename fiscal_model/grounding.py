"""Grounding — turn model outputs into numbers a policy audience can feel.

Two ingredients, both pure (no streamlit):
- `CBOBaseline` / `load_cbo_baseline()`: CBO's February-2026 baseline (data/raw/cbo_baseline_2026.csv,
  FY2025 actual + FY2026-2036 projections). Revenue extrapolates past FY2036 at the baseline's own
  terminal growth rate; deficit/debt/GDP clamp at FY2036 — callers footnote via `.max_year`.
- `ANCHORS` + `ground(value, kind)`: ~15 sourced real-world quantities and a comparator picker that
  renders one caption line ("≈ 2.6 years of the FY2025 federal deficit, on top of what CBO already
  projects"). Every model dollar figure is a CHANGE against a no-AI baseline, so deficit/debt copy
  always carries the "on top of" clause.

`briefing_text(...)` assembles the current scenario into a few grounded plain-English sentences
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
    "nih_budget_fy2024": (47.1, "FY2024 NIH program level — appropriations"),
    "k12_public_spending": (880.0, "annual US public K-12 spending ≈ $880B — NCES (2023 vintage)"),
    # ---- jobs (millions) ----
    "great_recession_job_losses_M": (8.7, "peak-to-trough nonfarm payroll losses, Jan 2008-Feb 2010 — BLS"),
    "covid_peak_job_losses_M": (21.9, "nonfarm payroll losses, Feb-Apr 2020 — BLS"),
    "manufacturing_employment_M": (12.9, "total US manufacturing employment, 2024 — BLS CES"),
    "federal_civilian_workforce_M": (2.3, "federal civilian workforce (ex-postal) — OPM"),
}

# Per kind: ordered (anchor, template) candidates. {r} = ratio, {v} = |value| formatted. The first
# candidate whose ratio lands in [0.3, 30] wins (fallback: nearest to 1). Deficit/debt kinds carry
# the "on top of what CBO already projects" clause — every model figure is a delta vs no-AI.
_CANDIDATES: dict[str, list[tuple[str, str]]] = {
    "fed_deficit_flow": [
        ("defense_outlays_fy2024", "≈ {r}× the entire FY2024 defense budget, every year"),
        ("cbo_deficit_fy2025", "≈ {r}× the FY2025 federal deficit, every year"),
        ("nih_budget_fy2024", "≈ {r}× the annual NIH budget, every year"),
    ],
    "debt_stock": [
        ("cbo_deficit_fy2025", "≈ {r} extra years of the FY2025 federal deficit"),
        ("cbo_debt_public_fy2025", "≈ {r}× today's entire federal debt held by the public"),
    ],
    "jobs": [
        ("great_recession_job_losses_M", "≈ {r}× the jobs lost in the Great Recession"),
        ("covid_peak_job_losses_M", "≈ {r}× the jobs lost at the COVID trough"),
        ("manufacturing_employment_M", "≈ {r}× all of US manufacturing"),
        ("federal_civilian_workforce_M", "≈ {r}× the federal civilian workforce"),
    ],
    "state_flow": [
        ("k12_public_spending", "≈ {r}× what all states spend on K-12 schools, every year"),
        ("nih_budget_fy2024", "≈ {r}× the annual NIH budget, every year"),
    ],
    "revenue_flow": [
        ("individual_income_receipts_2024", "≈ {r} full years of federal individual income-tax receipts"),
        ("defense_outlays_fy2024", "≈ {r}× the FY2024 defense budget"),
        ("nih_budget_fy2024", "≈ {r}× the annual NIH budget"),
    ],
}
_ON_TOP = {"fed_deficit_flow", "debt_stock"}


def _fmt_ratio(r: float) -> str:
    return f"{r:,.1f}" if r < 10 else f"{r:,.0f}"


def ground(value: float, kind: str) -> str:
    """One caption line comparing `value` (a model DELTA: $B for fiscal kinds, millions for jobs)
    to the most legible real-world anchor. Empty string for negligible values."""
    cands = _CANDIDATES[kind]
    mag = abs(float(value))
    if mag < 1e-9:
        return ""
    scored = [(mag / ANCHORS[a][0], a, tmpl) for a, tmpl in cands]
    in_window = [s for s in scored if 0.3 <= s[0] <= 30]
    r, _a, tmpl = in_window[0] if in_window else min(scored, key=lambda s: abs(s[0] - 1.0))
    line = tmpl.format(r=_fmt_ratio(r))
    if kind in _ON_TOP:
        line += (" — on top of what CBO already projects" if value > 0
                 else " — an improvement against what CBO projects")
    elif value < 0 and kind != "jobs":
        line = "an improvement of " + line
    return line


# ---------------------------------------------------------------------------- briefing
def briefing_text(scenario_name: str, start_year: int, n_periods: int,
                  m: dict, share_qs: str = "") -> str:
    """A memo-ready plain-English summary of the current configuration.

    `m` keys (all final-year unless noted): jobs_lost_M, final_deficit_delta_B (positive = worse),
    debt_delta_B (cumulative), cum_income_tax_lost_B, state_gap_B, real_gdp_pct."""
    end = start_year + n_periods - 1
    jobs, ddef = m["jobs_lost_M"], m["final_deficit_delta_B"]
    debt, gap, gdp = m["debt_delta_B"], m["state_gap_B"], m["real_gdp_pct"]
    inc = m["cum_income_tax_lost_B"]
    worse = ddef > 0
    lines = [
        f"Under the “{scenario_name}” scenario, modeled {start_year}–{end}:",
        f"• By {end}, {jobs:,.1f} million workers are displaced and not re-employed "
        f"({ground(jobs, 'jobs')}).",
        f"• The federal deficit runs ${abs(ddef):,.0f}B/yr {'higher' if worse else 'LOWER'} than "
        f"a no-AI baseline by {end} ({ground(ddef, 'fed_deficit_flow')}).",
        f"• Cumulatively the shock {'adds' if debt > 0 else 'removes'} ${abs(debt):,.0f}B "
        f"{'to' if debt > 0 else 'from'} federal debt ({ground(debt, 'debt_stock')}), and "
        f"${inc:,.0f}B of federal individual income-tax revenue is lost over the horizon "
        f"({ground(inc, 'revenue_flow')}).",
        f"• States — which must balance their budgets — face a ${gap:,.0f}B shortfall "
        f"in {end} alone ({ground(gap, 'state_flow')}).",
        f"• Real output is {gdp:+.1f}% vs baseline at the same time: under heavy automation the "
        f"abundance arrives as profit and lower prices, not as taxed wages — that gap is the "
        f"policy problem.",
        "",
        f"Generated by the open-source AI Automation Fiscal Simulator ({REPO_URL}); every number is "
        f"a change against a no-AI baseline. Reproduce this exact configuration: "
        + (f"append “?{share_qs}” to the app URL." if share_qs
           else f"select the “{scenario_name}” preset."),
    ]
    return "\n".join(lines)
