"""The KOREA descriptor: every field pinned to the ✓-verified research doc, and the payroll
component list behaving as the five legislated 2026 schemes on an annual wage."""
import numpy as np
import pytest

from fiscal_model import country, rates

KR = country.get("kr")
COMPONENTS = rates.korea_payroll_components()


def test_korea_is_the_formula_transfer_case():
    """Korea's subnational layer is one statutory elasticity (19.24% Local Share Tax + 20.79%
    Local Education Subsidy), NOT 51 balanced budgets — close_state_gaps must not run."""
    assert KR.subnational_mode == country.SUBNATIONAL_FORMULA_TRANSFER
    assert not KR.has_balanced_budget_subnational
    assert KR.subnational_transfer_share == pytest.approx(0.4003)
    assert KR.subnational_label == "local government"


def test_korea_macro_anchors_match_their_stated_derivations():
    """va = debt/(debt-to-GDP) from NABO Focus 92; comp = mean wage x 12 x covered workers."""
    assert KR.va_baseline == pytest.approx(1_270.4e12 / 0.478)          # ≈ ₩2,657.7tn
    assert KR.va_baseline == pytest.approx(2.6577e15, rel=1e-4)
    assert KR.comp_total == pytest.approx(4_482_000.0 * 12 * 12_413_858)  # ≈ ₩667.7tn
    assert KR.baseline_deficit_bn == 85.5                               # 관리재정수지 2025, ₩tn
    assert KR.money_unit_label == "₩tn"
    assert KR.currency_code == "KRW"


def test_the_five_schemes_sum_to_the_published_combined_burden():
    """9.5 + 7.19 + 0.9448 + 1.8 + 1.47 = 20.9048% of payroll below the pension cap — the
    research doc's '≈20.9% vs US FICA 15.3%' headline."""
    names = [c.name for c in COMPONENTS]
    assert names == ["NPS pension", "NHI health", "LTC long-term care",
                     "EI unemployment benefit", "IACI industrial accident"]
    assert sum(c.rate for c in COMPONENTS) == pytest.approx(0.209048)
    # employee side: half of everything except industrial accident (employer-only)
    assert sum(c.employee_rate for c in COMPONENTS) == pytest.approx((0.209048 - 0.0147) / 2)


def test_pension_cap_binds_and_only_the_pension_is_capped():
    """The pension caps at ₩6.59m/month (₩79.08m/yr) — inside the model's wage range, which is
    what routes high-wage damage to the general account instead of the funds. Everything else
    is flat: the NHI ceiling (≈₩127.7m/month salary) cannot bind below the top cell wage."""
    pension = COMPONENTS[0]
    assert pension.kind == "capped"
    assert pension.cap == pytest.approx(79_080_000.0)
    assert all(c.kind == "flat" for c in COMPONENTS[1:])

    engine = rates.PayrollFICA(components=COMPONENTS)
    w = np.array([30_000_000.0, 79_080_000.0, 200_000_000.0])   # below / at / above the cap
    total = engine.fica(w, "Single")
    below, at_cap, above = total
    assert below == pytest.approx(30e6 * 0.209048)
    assert at_cap == pytest.approx(79.08e6 * 0.209048)
    # above the cap only the four flat schemes keep accruing
    flat_rates = 0.209048 - 0.095
    assert above == pytest.approx(79.08e6 * 0.095 + 200e6 * flat_rates)


def test_employee_share_excludes_industrial_accident():
    engine = rates.PayrollFICA(components=COMPONENTS)
    w = np.array([50_000_000.0])
    employee = engine.employee_fica(w, "Single")[0]
    assert employee == pytest.approx(50e6 * (0.095 + 0.0719 + 0.009448 + 0.018) / 2)


def test_korea_transfer_programs_have_formula_implementations():
    """Every declared programme maps to a formula in korea_transfers.py — the tuple is a
    contract, not a wish list. NBLSS is deferred until its parameters verify."""
    from fiscal_model import korea_transfers as kt
    impl = {"ei_unemployment_benefit": kt.ei_spell_benefit,
            "kr_eitc": kt.kr_eitc,
            "basic_pension": kt.basic_pension_year}
    assert set(KR.transfer_programs) == set(impl)
    for fn in impl.values():
        assert callable(fn)


def test_korea_raw_files_exist_in_the_repo():
    from pathlib import Path
    raw = Path(country.__file__).resolve().parent.parent / "data" / "raw"
    for f in KR.raw_files:
        assert (raw / f).exists(), f"missing {f}"
