"""The country seam: the US descriptor must restate today's behaviour exactly, and the facts that
genuinely differ between fiscal systems must be reachable as data rather than baked into modules."""
import numpy as np
import pytest

from fiscal_model import country, government, macro, rates, transfers


def test_us_descriptor_matches_the_live_constants():
    """The US Country restates what the modules already do — if a constant moves and the descriptor
    does not, this goes red rather than the two drifting apart silently."""
    us = country.get("us")
    assert us.va_baseline == macro.VA_BASELINE_USD
    assert us.comp_total == macro.COMP_TOTAL_USD
    assert us.baseline_deficit_bn == government.BASELINE_FED_DEFICIT_BUSD
    assert us.transfer_programs == tuple(transfers.PROGRAMS)
    assert us.payroll_components is rates.us_payroll_components


def test_us_is_the_balanced_budget_subnational_case():
    """The asymmetric-amplifier mechanism (close_state_gaps) is a US property, not a universal one —
    Korea's local government is funded by statutory transfers instead, so this must be a flag."""
    us = country.get("us")
    assert us.subnational_mode == country.SUBNATIONAL_BALANCED_BUDGET
    assert us.has_balanced_budget_subnational
    assert us.subnational_transfer_share is None      # only the formula-transfer mode uses it
    assert us.subnational_label == "state"


def test_build_engines_defaults_to_us_payroll(data):
    """Threading the seam must not change the default path: build_engines with no country argument
    is bit-identical to the explicit US builder AND to the retained legacy engine."""
    _, default_engine = rates.build_engines(data)
    _, explicit = rates.build_engines(data, payroll_components=country.US.payroll_components)
    legacy = rates._PayrollFICALegacy(data.payroll_params)
    w = np.linspace(0.0, 400_000.0, 2001)
    for filing in ("Single", "Married filing jointly"):
        a = default_engine.fica(w, filing)
        assert np.array_equal(a, explicit.fica(w, filing))
        assert np.array_equal(a, legacy.fica(w, filing))
        assert np.array_equal(default_engine.employee_fica(w, filing),
                              legacy.employee_fica(w, filing))


def test_unknown_country_raises():
    with pytest.raises(ValueError, match="unknown country"):
        country.get("atlantis")
