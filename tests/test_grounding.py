"""Grounding gate — the CBO baseline accessor (pins, extrapolation, clamps), the anchor table's
cross-checks against the committed CSV and the repo ledger, and the comparator picker."""
import numpy as np
import pytest

from fiscal_model import grounding
from fiscal_model.grounding import ANCHORS, ground, load_cbo_baseline


@pytest.fixture(scope="module")
def cbo():
    return load_cbo_baseline()


def test_csv_pins_and_shape(cbo):
    assert cbo.min_year == 2025 and cbo.max_year == 2036
    assert abs(cbo.revenue(2026) - 5595.916) < 1e-6
    assert abs(cbo.deficit(2031) - (-2285.7)) < 0.05
    assert cbo.debt(2036) > 56_000


def test_revenue_extrapolation(cbo):
    g = cbo.terminal_growth
    assert 0.03 < g < 0.05                                   # ~4.1%/yr nominal
    expect = cbo.revenue(2036) * (1 + g) ** 4
    assert np.isclose(cbo.revenue(2040), expect, rtol=1e-12)


def test_clamp_and_domain(cbo):
    assert cbo.deficit(2050) == cbo.deficit(2036)            # clamped, not extrapolated
    assert cbo.debt(2050) == cbo.debt(2036)
    with pytest.raises(ValueError):
        cbo.revenue(2024)


def test_anchor_cross_checks(cbo, data):
    from fiscal_model.government import RevenueLedger
    ledger = RevenueLedger(data)
    assert abs(ANCHORS["cbo_deficit_fy2025"][0] - abs(cbo.deficit(2025))) < 0.1
    assert abs(ANCHORS["cbo_debt_public_fy2025"][0] - cbo.debt(2025)) < 0.1
    assert abs(ANCHORS["federal_revenue_2024"][0] - ledger.fed_revenue0) < 0.1
    assert abs(ANCHORS["state_local_revenue_2024"][0] - ledger.state_revenue0) < 0.1
    for name, (value, source) in ANCHORS.items():
        assert value > 0 and source, name


def test_ground_picks_legible_ratio():
    # nearest-×1 among in-window candidates: 2200/1775 = 1.24 (deficit) beats 2200/850 = 2.6
    line = ground(2200.0, "fed_deficit_flow")
    assert "1.2× the FY2025 federal deficit" in line
    assert "on top of what CBO already projects" in line
    # a small figure lands on the Apollo comparator (no small-agency budgets)
    small = ground(200.0, "fed_deficit_flow")
    assert "Apollo" in small and "NIH" not in small
    # improvements get the mirrored clause, never "on top of"
    imp = ground(-500.0, "debt_stock")
    assert "improvement" in imp and "on top of" not in imp
    # the debt stock ALWAYS grounds in deficit-years (the user's call), even at huge ratios
    assert "extra years of the FY2025 federal deficit" in ground(39_663.0, "debt_stock")
    # jobs: nearest ×1 — 26M sits closest to the COVID trough (21.9M), not 3× Great Recession
    assert "COVID" in ground(26.0, "jobs")
    assert "Great Recession" in ground(9.5, "jobs")           # 9.5/8.7 = 1.09 → nearest
    assert ground(0.0, "jobs") == ""


def test_ground_near_equal_drops_the_multiplier():
    # within ±7% of an anchor the line reads "≈ the ..." with no ratio
    line = ground(124.0, "jobs")                              # 124/123.8 → population of Japan
    assert line == "≈ the population of Japan"
    # the years-form template keeps its number even near 1
    assert "extra years" in ground(1775.0, "debt_stock")


def test_ground_fallback_nearest_ratio():
    # absurdly large: nothing lands in [0.3, 30] → nearest-to-1 anchor still yields a line
    line = ground(1_000_000.0, "state_flow")
    assert "×" in line and line != ""


def test_gdp_years_line():
    # +7.9% at 2%/yr: ln(1.079)/ln(1.02) ≈ 3.84 years
    line = grounding.gdp_years_line(7.9)
    assert "3.8 years" in line and "2%/yr" in line
    assert grounding.gdp_years_line(62.7).startswith("≈ 24.")   # compounding, not 31.4
    assert grounding.gdp_years_line(0.0) == ""
