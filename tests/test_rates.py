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
    (oasdi,) = [c for c in fica.components if c.name == "OASDI"]
    cap = oasdi.cap
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


def test_payroll_components_match_legacy_bitwise(data):
    """PERMANENT ANCHOR: the component-list PayrollFICA must equal the original hardcoded-US-schema
    engine BIT-FOR-BIT — same operands, same left-associative sum order. This is what lets the
    engine take Korea's five schemes without touching a single US number (the same discipline
    mc.run_mc / survivor._delta_loop / reabsorption._delta_loop are retained for)."""
    new = rates.PayrollFICA(data.payroll_params)
    ref = rates._PayrollFICALegacy(data.payroll_params)
    w = np.concatenate([np.linspace(0.0, 500_000.0, 5001),
                        np.array([0.0, 1e-9, new.components[0].cap, new.components[0].cap + 0.01,
                                  200_000.0, 250_000.0, 1e7])])
    for filing in ("Single", "Married filing jointly", "Head of household"):
        for meth in ("fica", "employee_fica"):
            assert np.array_equal(getattr(new, meth)(w, filing),
                                  getattr(ref, meth)(w, filing)), (filing, meth)
            # scalar path keeps returning a float, not a 0-d array
            s = getattr(new, meth)(123_456.78, filing)
            assert isinstance(s, float) and s == getattr(ref, meth)(123_456.78, filing)


def test_payroll_component_shapes_are_country_general(data):
    """The three shapes cover Korea's schemes too: capped (national pension, health), flat
    (employment, industrial accident), surcharge (unused there). Build a synthetic Korean-style
    list and check it evaluates sensibly — no US assumption leaks into the engine."""
    kr = (rates.PayrollComponent("national pension", "capped", 0.095, 0.0475, cap=79_080_000.0),
          rates.PayrollComponent("health", "flat", 0.0719, 0.03595),
          rates.PayrollComponent("industrial accident", "flat", 0.0147, 0.0))   # employer-only
    eng = rates.PayrollFICA(components=kr)
    below, above = 50_000_000.0, 200_000_000.0
    # capped component stops growing above the ceiling; flat ones keep going
    assert eng.fica(above, "Single") > eng.fica(below, "Single")
    assert np.isclose(eng.fica(above, "Single"),
                      0.095 * 79_080_000.0 + 0.0719 * above + 0.0147 * above)
    # employer-only component contributes nothing to the employee side
    assert np.isclose(eng.employee_fica(below, "Single"),
                      0.0475 * below + 0.03595 * below)
