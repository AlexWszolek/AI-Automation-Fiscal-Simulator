"""The Korean income-tax chain, pinned by hand-computed anchor cases and the properties the
argument depends on (progressivity, the credit floor, the +10% surtax identity)."""
import numpy as np
import pytest

from fiscal_model import rates
from fiscal_model.korea_tax import korea_income_tax

ENGINE = rates.PayrollFICA(components=rates.korea_payroll_components())


def _tax(wages):
    w = np.asarray(wages, dtype=float)
    return korea_income_tax(w, ENGINE.employee_fica(w, "Single"))


def test_hand_computed_anchor_w30m():
    """₩30m/yr, worked by hand: deduction 9.75m; employee social 2,915,220 (4.75% + 3.595% +
    0.4724% + 0.9%); basic 1.5m -> base 15,834,780; tax 15%·base − 1.26m = 1,115,217;
    credit 55% = 613,369.35 (under the ₩740k cap); national 501,847.65; local +10%."""
    r = _tax([30_000_000.0])
    assert r["national"][0] == pytest.approx(501_847.65)
    assert r["local"][0] == pytest.approx(50_184.765)
    assert r["total"][0] == pytest.approx(552_032.415)


def test_hand_computed_anchor_at_the_mean_wage():
    """The 2025 mean (₩53.784m/yr): deduction 12m+5%·8.784m=12.4392m; social 5,225,976
    (pension 2,554,740 + NHI 1,933,535.28 + LTC 254,075.62 + EI 484,056 — engine-exact);
    basic 1.5m → base 34,618,824-ish; 15% band; credit hits the ₩660k floor via the 33–70m
    cap rule. Effective rate ≈ 8% — Korea's PIT is light at the mean, which is the point."""
    w = 53_784_000.0
    social = float(ENGINE.employee_fica(np.array([w]), "Single")[0])
    base = w - 12_439_200.0 - 1_500_000.0 - social
    computed = base * 0.15 - 1_260_000.0
    cap = max(740_000.0 - (w - 33e6) * 0.008, 660_000.0)
    credit = min(715_000.0 + 0.30 * (computed - 1_300_000.0), cap)
    r = _tax([w])
    assert r["national"][0] == pytest.approx(computed - credit)
    assert 0.06 < r["total"][0] / w < 0.10


def test_progressive_and_monotone():
    w = np.linspace(5e6, 400e6, 500)
    r = _tax(w)
    eff = r["total"] / w
    total = r["total"]
    assert (np.diff(total) >= 0).all()              # liability never falls in wage
    positive = total > 0
    assert (np.diff(total[positive]) > 0).all()     # and strictly rises once it is positive
    assert eff[-1] > 0.30                           # top effective rates approach the 45%+10%
    assert eff[0] == 0.0                            # fully absorbed by deductions at the bottom
    assert (np.diff(eff) > -1e-12).all()            # effective rate never falls


def test_local_is_exactly_ten_percent_of_national():
    r = _tax(np.linspace(1e6, 300e6, 100))
    assert np.allclose(r["local"], 0.10 * r["national"])
    assert np.allclose(r["total"], r["national"] + r["local"])


def test_no_negative_tax_at_the_bottom():
    r = _tax([1_000_000.0, 4_000_000.0, 8_000_000.0])
    assert (r["national"] >= 0.0).all()
    assert r["national"][0] == 0.0                  # fully absorbed by deductions


# ------------------------------------------------------------- extensive correctness additions
def test_hand_computed_anchor_w200m_top_cap_floor():
    """₩200m/yr, worked by hand: WSD 16.75m; social 13,691,100 (pension CAPPED at 3,756,300 +
    flat 4.9674%×200m); base 168,058,900 → 38% bracket → 43,922,382; credit floored at the
    >₩120m minimum ₩200,000; national 43,722,382, +10% local."""
    r = _tax([200_000_000.0])
    assert r["national"][0] == pytest.approx(43_722_382.0)
    assert r["total"][0] == pytest.approx(43_722_382.0 * 1.1)


def test_no_discontinuities_anywhere():
    """₩10k steps over ₩0–500m: every liability step is bounded — piecewise-linear chains
    with floors/caps/credits must never JUMP (the class of bug a mistranscribed 누진공제
    would create)."""
    w = np.arange(0.0, 500_000_000.0, 10_000.0)
    t = _tax(w)["total"]
    steps = np.diff(t)
    assert (steps >= -1e-6).all()               # liability never falls in wage
    assert steps.max() < 10_000.0 * 1.05 + 1.0  # local marginal never exceeds ~105%


def test_effective_rate_asymptote_is_shaved_by_deductible_social():
    """The true supremum is NOT the statutory 49.5% (45% × 1.1): deductible employee social
    contributions (4.9674% flat above the pension cap) shave the base forever, so the
    effective rate approaches 0.495 × (1 − 0.049674) ≈ 47.04% from below."""
    asymptote = 0.495 * (1.0 - 0.049674)
    w = np.array([1e8, 1e9, 1e10, 1e11])
    eff = _tax(w)["total"] / w
    assert (eff < asymptote).all()
    assert eff[-1] == pytest.approx(asymptote, abs=1e-3)
    assert (np.diff(eff) > 0).all()              # …monotonically from below


def test_liability_monotone_nonincreasing_in_social_contributions():
    from fiscal_model.korea_tax import korea_income_tax
    w = np.full(50, 80_000_000.0)
    social = np.linspace(0.0, 10_000_000.0, 50)
    nat = korea_income_tax(w, social)["national"]
    assert (np.diff(nat) <= 1e-9).all()


def test_wsd_ceiling_binds_above_362_5m():
    from fiscal_model.korea_tax import _wage_salary_deduction
    assert _wage_salary_deduction(np.array([362_500_000.0]))[0] == pytest.approx(20_000_000.0)
    assert _wage_salary_deduction(np.array([1e9]))[0] == 20_000_000.0
    assert _wage_salary_deduction(np.array([362_400_000.0]))[0] < 20_000_000.0


def test_wsd_continuity_at_every_knot():
    from fiscal_model.korea_tax import _wage_salary_deduction
    for knot in (5e6, 15e6, 45e6, 100e6):
        lo, hi = _wage_salary_deduction(np.array([knot - 0.01, knot]))
        assert hi - lo < 0.011


def test_zero_and_empty_inputs():
    r = _tax([0.0])
    assert r["national"][0] == 0.0 and r["total"][0] == 0.0
    r2 = _tax([])
    assert r2["national"].size == 0
