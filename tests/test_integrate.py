"""Tests for the Part C within-cell integration wrapper. The headline acceptance test
(per transfer_side_build_plan.md §Sequencing 3): a cell straddling a benefit cliff must
yield a materially different integrated transfer delta than the at-the-mean delta."""
from pathlib import Path

import numpy as np
import pytest

LOOKUP = Path(__file__).resolve().parent.parent / "data" / "interim" / "benefit_lookup.parquet"
NOC = Path(__file__).resolve().parent.parent / "data" / "interim" / "noc_distribution.csv"


@pytest.fixture(scope="module")
def ci(data):
    if not LOOKUP.exists() or not NOC.exists():
        pytest.skip("transfer artifacts not built (bake_benefits / noc)")
    from fiscal_model.integrate import CellIntegrator
    from fiscal_model.transfers import TransferLookup
    return CellIntegrator(data, TransferLookup())


def test_kink_integration_differs_from_mean(ci):
    # high-wage SW dev: household mean above thresholds, but the distribution's left tail
    # crosses benefit cliffs after displacement -> integrated >> at-mean
    r = ci.integrate("15-1252", "California")
    rm = ci.integrate("15-1252", "California", collapse_to_mean=True)
    integrated = r.after.gained_outlays_fed + r.after.gained_outlays_state
    at_mean = rm.after.gained_outlays_fed + rm.after.gained_outlays_state
    assert integrated > at_mean * 1.2          # materially larger (resolves the kink)
    assert integrated - at_mean > 500


def test_fiscaldelta_consistency(ci):
    r = ci.integrate("35-3023", "Texas")
    for fd in (r.during, r.after):
        assert np.isclose(fd.net_total, fd.net_fed + fd.net_state)
        assert fd.offset == 0      # corporate is layered on by the dynamics, not here


def test_income_and_payroll_phase_invariant(ci):
    r = ci.integrate("35-3023", "Texas")
    assert np.isclose(r.during.lost_income_tax_fed, r.after.lost_income_tax_fed)
    assert np.isclose(r.during.lost_payroll_fed, r.after.lost_payroll_fed)


def test_phases_differ(ci):
    r = ci.integrate("35-3023", "California")
    # UI cushions consumption and suppresses means-tested benefits during the window
    assert r.during.net_total < r.after.net_total
    assert r.during.lost_consumption_tax_state < r.after.lost_consumption_tax_state


def test_dispersion_positive(ci):
    r = ci.integrate("15-1252", "California")
    assert r.net_std_after > 0      # there is genuine within-cell spread


def test_missing_cell_returns_none(ci):
    assert ci.integrate("99-9999", "California") is None


def test_low_wage_bigger_relative_pickup(ci):
    # low-wage workers pull more means-tested transfers relative to their wage than high-wage
    lo = ci.integrate("35-3023", "California")
    hi = ci.integrate("15-1252", "California")
    lo_ratio = (lo.after.gained_outlays_fed + lo.after.gained_outlays_state) / lo.worker_wage
    hi_ratio = (hi.after.gained_outlays_fed + hi.after.gained_outlays_state) / hi.worker_wage
    assert lo_ratio > hi_ratio
