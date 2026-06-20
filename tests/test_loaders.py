"""Regression tests for the data layer — control totals, shapes, and the
file-vs-briefing corrections the recon surfaced."""
import numpy as np

from fiscal_model import loaders


def test_load_all_validates(data):
    # load_all(validate=True) raising would fail the session fixture already; assert bundle.
    assert data.matrices_detail.shape == (833 * 71, 5)
    assert data.matrices_sector.shape == (833 * 20, 5)


def test_matrices_control_totals(data):
    assert abs(data.matrices_detail["emp_thousands"].sum() - 163_223) / 163_223 < 1e-3
    assert abs(data.matrices_detail["comp_musd"].sum() - 15_049_121) / 15_049_121 < 1e-4
    assert "55-0000" in set(data.matrices_detail["soc_code"])


def test_capital_totals_exact(data):
    t = data.capital_total
    assert round(t["value_added_musd"]) == 29_298_075
    assert round(t["comp_musd"]) == 15_049_121
    assert round(t["corp_profits_bt_musd"]) == 3_721_572
    # Government has zero corporate base
    gov = data.capital[data.capital["industry"] == "Government"].iloc[0]
    assert gov["corp_profits_bt_musd"] == 0


def test_exposure_shape_and_imputed(data):
    assert len(data.exposure_occ) == 832          # Military absent (NOT 833)
    assert int(data.exposure_occ["is_imputed"].sum()) == 68
    assert -3.5 < data.exposure_occ["ai_pca_score"].min() < -3.3
    assert 7.0 < data.exposure_occ["ai_pca_score"].max() < 7.1


def test_government_key_values(data):
    medicaid = data.transfers.loc[
        data.transfers["program"].str.contains("Medicaid"), "amount_busd"].iloc[0]
    assert abs(medicaid - 938.2) < 1e-6
    # automation-sensitivity tags preserved verbatim (mixed casing)
    assert "HIGH" in set(data.transfers["automation_sensitivity"].dropna())


def test_oews_aggregates_removed(data):
    assert not data.oews["soc_code"].str.endswith("-0000").any()
    assert len(data.oews_major) == 22 * 51
    assert data.oews["state"].nunique() == 51


def test_consumption_four_zero_states(data):
    # recon correction: 4 exactly-zero states, not 5 (Alaska has local rates)
    zero = set(data.consumption.loc[data.consumption["eff_tax_rate_pct"] == 0, "state"])
    assert zero == {"Delaware", "Montana", "New Hampshire", "Oregon"}
    assert len(data.consumption) == 51
    assert "District of Columbia" in set(data.consumption["state"])


def test_household_filing_shares_sum_to_one(data):
    p = data.household[["p_mfj", "p_hoh", "p_single"]].sum(axis=1)
    assert ((p - 1.0).abs() <= 1e-3).all()
    assert data.household["soc_code"].nunique() == 795
    # negative HINCP is valid and must survive loading
    assert data.household["inc_single_usd"].min() < 0


def test_state_join_keys_canonical(data):
    for df_name in ("consumption", "household"):
        df = getattr(data, df_name)
        assert "Washington DC" not in set(df["state"])
        assert "District of Columbia" in set(df["state"])


def test_no_wage_tax_states(data):
    assert data.state_no_wage_tax == loaders.NO_WAGE_TAX_STATES
    assert "Washington" in data.state_no_wage_tax
