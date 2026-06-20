"""Tests for the static kernel — accounting invariants and channel behaviour."""
import numpy as np

from fiscal_model.kernel import Kernel, KernelParams, Worker, FiscalDelta


def _hi(k):
    return k.fiscal_delta(Worker(180_000, 250_000, "Married filing jointly", "California",
                                 "Professional, scientific, and technical services", 220_000))


def _lo(k):
    return k.fiscal_delta(Worker(35_000, 55_000, "Single", "Texas",
                                 "Accommodation and food services", 40_000))


def test_net_equals_cost_minus_offset(data):
    k = Kernel(data)
    for fd in (_hi(k), _lo(k)):
        assert np.isclose(fd.net_total, fd.cost - fd.offset)
        assert np.isclose(fd.net_total, fd.net_fed + fd.net_state)


def test_high_wage_loses_more_income_tax(data):
    k = Kernel(data)
    hi, lo = _hi(k), _lo(k)
    assert hi.lost_income_tax_fed > lo.lost_income_tax_fed
    # base-migration: more of the high earner's revenue is income tax; payroll is capped
    assert hi.lost_payroll_fed / 180_000 < 0.153          # OASDI cap bites
    assert np.isclose(lo.lost_payroll_fed / 35_000, 0.153, atol=1e-3)   # under cap = full 15.3%


def test_government_sector_zero_corporate(data):
    k = Kernel(data)
    fd = k.fiscal_delta(Worker(60_000, 80_000, "Single", "Ohio", "Government", 90_000))
    assert fd.recovered_corp_tax_fed == 0
    assert fd.recovered_dividend_tax_fed == 0
    assert fd.recovered_passthrough_tax_fed == 0
    assert fd.offset == 0


def test_consumption_zero_in_zero_rate_state(data):
    k = Kernel(data)
    # Oregon has a 0% effective consumption tax rate
    fd = k.fiscal_delta(Worker(50_000, 70_000, "Single", "Oregon",
                               "Retail trade", 58_000))
    assert fd.lost_consumption_tax_state == 0


def test_residual_income_reduces_consumption(data):
    k = Kernel(data)
    w = Worker(50_000, 70_000, "Single", "California", "Retail trade", 58_000)
    full = k.fiscal_delta(w, residual_income=0.0)
    partial = k.fiscal_delta(w, residual_income=40_000)
    assert partial.lost_consumption_tax_state < full.lost_consumption_tax_state


def test_n_scaling(data):
    k = Kernel(data)
    one = k.fiscal_delta(Worker(50_000, 70_000, "Single", "California", "Retail trade", 58_000))
    two = k.fiscal_delta(Worker(50_000, 70_000, "Single", "California", "Retail trade", 58_000, n=2))
    assert np.isclose(two.net_total, 2 * one.net_total)
    assert np.isclose(two.lost_payroll_fed, 2 * one.lost_payroll_fed)


def test_surplus_capture_lever_scales_offset(data):
    k_full = Kernel(data, KernelParams(surplus_capture=1.0))
    k_half = Kernel(data, KernelParams(surplus_capture=0.5))
    w = Worker(180_000, 250_000, "Married filing jointly", "California",
               "Professional, scientific, and technical services", 220_000)
    assert np.isclose(k_half.fiscal_delta(w).offset, 0.5 * k_full.fiscal_delta(w).offset)


def test_fiscaldelta_add(data):
    k = Kernel(data)
    s = _hi(k) + _lo(k)
    assert np.isclose(s.net_total, _hi(k).net_total + _lo(k).net_total)
