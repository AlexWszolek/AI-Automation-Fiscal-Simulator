"""Grounding gate — the CBO baseline accessor (pins, extrapolation, clamps), the anchor table's
cross-checks against the committed CSV and the repo ledger, the comparator picker, and the
memo-briefing text."""
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
    # 2200 B/yr deficit → defense (850) gives ratio 2.6, inside [0.3, 30] → first candidate wins
    line = ground(2200.0, "fed_deficit_flow")
    assert "2.6× the entire FY2024 defense budget" in line
    assert "on top of what CBO already projects" in line
    # a small figure falls through to the NIH comparator
    small = ground(60.0, "fed_deficit_flow")
    assert "NIH" in small
    # improvements get the mirrored clause, never "on top of"
    imp = ground(-500.0, "debt_stock")
    assert "improvement" in imp and "on top of" not in imp
    # jobs
    assert "Great Recession" in ground(26.0, "jobs")          # 26M / 8.7M = 3.0 ✓ window
    assert ground(0.0, "jobs") == ""


def test_ground_fallback_nearest_ratio():
    # absurdly large: nothing lands in [0.3, 30] → nearest-to-1 anchor still yields a line
    line = ground(1_000_000.0, "state_flow")
    assert "×" in line and line != ""


def test_briefing_text_contents():
    m = dict(jobs_lost_M=40.4, final_deficit_delta_B=2497.0, debt_delta_B=4341.0,
             cum_income_tax_lost_B=2674.0, state_gap_B=211.0, real_gdp_pct=7.9)
    txt = grounding.briefing_text("AI 2040 — Plan A (The Deal)", 2027, 14, m, share_qs="preset=ai2040-plan-a")
    assert "AI 2040 — Plan A (The Deal)" in txt
    assert "2040" in txt                                      # 2027 + 14 - 1
    assert "?preset=ai2040-plan-a" in txt
    assert "on top of what CBO already projects" in txt
    assert "no-AI baseline" in txt
    # without a query string the provenance falls back to the preset name
    txt2 = grounding.briefing_text("Custom", 2026, 10, m)
    assert "select the" in txt2 and "?" not in txt2.splitlines()[-1]
