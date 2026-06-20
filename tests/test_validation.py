"""Part B.6 tax cross-check as a regression guard. The aggregate benefit reconciliation
is interpretive (entitlement-vs-take-up, income-proxy, working-age scope) and lives in
scripts/validate_transfers.py, not here."""
from pathlib import Path

import pandas as pd
import pytest

LOOKUP = Path(__file__).resolve().parent.parent / "data" / "interim" / "benefit_lookup.parquet"


@pytest.fixture(scope="module")
def lk_and_engines(data):
    if not LOOKUP.exists():
        pytest.skip("benefit_lookup not built")
    from fiscal_model.rates import build_engines
    return pd.read_parquet(LOOKUP), build_engines(data)


def _row(lk, state, income):
    return lk[(lk["filing"] == "Single") & (lk["n_children"] == 0)
             & (lk["state"] == state) & (lk["household_income"] == income)].iloc[0]


def test_income_tax_crosscheck(lk_and_engines):
    # Single, 0 kids, high income (EITC=0): PE income tax ~ our federal bracket tax.
    # Residual <~3% is the 2024(PE)-vs-2025(tax_side) bracket vintage difference.
    lk, (inc, _) = lk_and_engines
    for income in (100_000, 150_000):
        r = _row(lk, "Texas", income)
        ours = inc.federal_tax(income, "Single")
        assert abs(r["pe_income_tax"] - ours) / ours < 0.05


def test_payroll_crosscheck_no_state_payroll(lk_and_engines):
    # In a state with no state payroll tax (TX), PE employee payroll == our federal FICA.
    lk, (_, fica) = lk_and_engines
    for income in (80_000, 120_000):
        r = _row(lk, "Texas", income)
        ours = fica.employee_fica(income, "Single")
        assert abs(r["pe_employee_payroll_tax"] - ours) / ours < 0.01
