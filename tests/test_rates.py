"""Regression tests for the tax engine — proven against the file's baked schedules."""
import numpy as np

from fiscal_model import rates


def test_engine_reproduces_baked_schedules(data):
    res = rates.verify_against_baked(data, tol=1.0)   # raises if any cell off by > $1
    assert res["federal_max_diff"] <= 1.0
    assert res["state_max_diff"] <= 1.0
    assert res["fica_max_diff"] <= 1.0


def test_headline_federal_values(data):
    inc, _ = rates.build_engines(data)
    assert round(inc.federal_tax(100_000, "Single")) == 13_614
    assert round(inc.federal_tax(200_000, "Married filing jointly")) == 27_228
    assert inc.federal_tax(10_000, "Single") == 0.0   # below standard deduction


def test_payroll_oasdi_cap(data):
    _, fica = rates.build_engines(data)
    # OASDI caps at the wage base; Medicare uncapped; Addl Medicare above threshold.
    cap = fica.oasdi_cap
    below = fica.fica(cap, "Single")
    above = fica.fica(cap + 100_000, "Single")
    # marginal above the cap is only Medicare 2.9% (plus 0.9% past $200k) -> < 15.3%
    assert (above - below) < 0.153 * 100_000
    assert round(fica.fica(1_000_000, "Single") - fica.fica(1_000_000 - 1, "Single"), 3) == round(
        0.029 + 0.009, 3)  # marginal at $1M single = Medicare + Addl Medicare


def test_no_wage_tax_state_zero(data):
    inc, _ = rates.build_engines(data)
    assert inc.state_tax(200_000, "Texas", "Single") == 0.0
    assert inc.state_tax(200_000, "Florida", "Married filing jointly") == 0.0


def test_state_hoh_maps_to_single(data):
    inc, _ = rates.build_engines(data)
    # state brackets have no HoH -> uses Single
    assert inc.state_tax(100_000, "Alabama", "Head of household") == \
        inc.state_tax(100_000, "Alabama", "Single")


def test_marginal_income_tax_lost(data):
    inc, _ = rates.build_engines(data)
    d = inc.marginal_income_tax_lost(150_000, 60_000, "California", "Single")
    # removing a wage from the household lowers tax -> positive "lost" amount, fed+state
    assert d["federal"] > 0 and d["state"] > 0
    assert np.isclose(d["total"], d["federal"] + d["state"])
    # and it equals T(150k) - T(90k)
    expected = inc.total_income_tax(150_000, "California", "Single") - \
        inc.total_income_tax(90_000, "California", "Single")
    assert np.isclose(d["total"], expected)
