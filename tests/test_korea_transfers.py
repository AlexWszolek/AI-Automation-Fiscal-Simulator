"""The three Korean transfer formulas, pinned to their statutes: the EI floor/cap compression,
the EITC trapezoid knots of 조특법 §100조의5, and the Basic Pension constants."""
import numpy as np
import pytest

from fiscal_model import korea_transfers as kt


# ------------------------------------------------------------------ 구직급여 (EI benefit)
def test_ei_floor_and_cap_nearly_touch():
    """The 2026 compression fact: floor ₩66,048 (80% of the 8h minimum wage) vs cap ₩68,100 —
    within 3.2% of each other, so the benefit is effectively flat across the wage scale."""
    assert kt.EI_DAILY_FLOOR == pytest.approx(66_048.0)
    assert kt.EI_DAILY_CAP == 68_100.0
    assert kt.EI_DAILY_CAP / kt.EI_DAILY_FLOOR < 1.04


def test_ei_daily_benefit_clips_to_the_statutory_band():
    w = np.array([36_000_000.0, 41_000_000.0, 120_000_000.0])   # ₩3m, ~₩3.4m, ₩10m per month
    b = kt.ei_daily_benefit(w)
    assert b[0] == pytest.approx(66_048.0)                       # floor binds
    assert b[1] == pytest.approx(0.60 * 41_000_000.0 / 365.0)    # the narrow 60% band
    assert kt.EI_DAILY_FLOOR < b[1] < kt.EI_DAILY_CAP
    assert b[2] == pytest.approx(68_100.0)                       # cap binds


def test_ei_duration_matrix():
    yrs = np.array([0.5, 2.0, 4.0, 7.0, 15.0])
    assert kt.ei_duration_days(yrs).tolist() == [120, 150, 180, 210, 240]
    assert kt.ei_duration_days(yrs, age_50_plus=True).tolist() == [120, 180, 210, 240, 270]


def test_ei_spell_benefit_scale():
    """A floor-wage worker with 10+ insured years at 50+: 66,048 × 270 ≈ ₩17.8m per spell —
    the per-worker outlay scale the fund arithmetic runs on."""
    spell = kt.ei_spell_benefit(np.array([30_000_000.0]), np.array([12.0]), age_50_plus=True)
    assert spell[0] == pytest.approx(66_048.0 * 270)


# ------------------------------------------------------------------ 근로장려금 (EITC)
def test_eitc_statutory_knots_single():
    y = np.array([0.0, 2e6, 4e6, 9e6, 15.5e6, 21_999_999.0, 22e6, 30e6])
    c = kt.kr_eitc(y, "single")
    assert c[0] == 0.0                                   # requires earned income
    assert c[1] == pytest.approx(2e6 * 165 / 400)        # phase-in: ×165/400만
    assert c[2] == pytest.approx(1_650_000.0)            # plateau start
    assert c[3] == pytest.approx(1_650_000.0)            # plateau end
    assert c[4] == pytest.approx(825_000.0)              # halfway down the phase-out
    assert c[5] == pytest.approx(0.0, abs=0.2)           # continuous into the ceiling
    assert c[6] == 0.0 and c[7] == 0.0                   # ineligible at/above ₩22m


def test_eitc_all_household_types_hit_their_maxima_and_ceilings():
    for hh, (lo, mid, hi, mx) in kt.EITC_SCHEDULE.items():
        assert kt.kr_eitc(np.array([lo]), hh)[0] == pytest.approx(mx)
        assert kt.kr_eitc(np.array([mid - 1.0]), hh)[0] == pytest.approx(mx, rel=1e-6)
        assert kt.kr_eitc(np.array([hi]), hh)[0] == 0.0
    assert kt.kr_eitc(np.array([17e6]), "dual_earner")[0] == pytest.approx(3_300_000.0)


def test_eitc_asset_halving():
    c = kt.kr_eitc(np.array([9e6]), "single", asset_halved=True)
    assert c[0] == pytest.approx(825_000.0)


def test_eitc_never_negative_and_duration_rejects_garbage():
    """Adversarial-pass guards: negative income must not produce a negative credit, and
    negative/NaN insured-years must fail loud instead of index-wrapping to 240/270 days."""
    assert kt.kr_eitc(np.array([-1_000_000.0]), "single")[0] == 0.0
    for bad in (np.array([-0.5]), np.array([np.nan])):
        with pytest.raises(AssertionError, match="insured_years"):
            kt.ei_duration_days(bad)


def test_eitc_displacement_delta_is_the_lost_credit():
    d = kt.kr_eitc_delta_on_displacement(np.array([9e6]), residual_income=0.0)
    assert d[0] == pytest.approx(-1_650_000.0)
    # a residual income inside the phase-in keeps part of the credit
    d2 = kt.kr_eitc_delta_on_displacement(np.array([9e6]), residual_income=2e6)
    assert d2[0] == pytest.approx(2e6 * 165 / 400 - 1_650_000.0)


# ------------------------------------------------------------------ 기초연금 (Basic Pension)
def test_basic_pension_constants():
    assert kt.BASIC_PENSION_MONTH == 349_700.0
    assert kt.basic_pension_year() == pytest.approx(4_196_400.0)
    assert kt.BASIC_PENSION_COVERAGE == 0.70
    assert kt.BASIC_PENSION_THRESHOLD_SINGLE == 2_470_000.0
