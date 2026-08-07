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
