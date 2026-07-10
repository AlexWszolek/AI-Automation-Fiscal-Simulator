"""Data loaders for the AI Automation Fiscal Model.

One loader per source file -> tidy DataFrames keyed by SOC / sector / state, with
**unit-suffixed column names** (so a unit is never ambiguous) and **control-total
assertions on load** so a bad file fails loudly.

Unit convention (encoded in column suffixes, NOT silently converted):
    *_thousands  employment in thousands of persons
    *_persons    employment in persons (OEWS)
    *_musd       money in $millions
    *_busd       money in $billions (government accounts)
    *_usd        money in dollars (wages, household income)
    *_frac       a fraction in [0,1]
    *_pct        a percentage (0..100)

Everything here is verified against the actual files (see docs/PROJECT_BRIEFING_v2.md
and the data-recon pass). Where the briefing and the file disagreed, the FILE wins and
the discrepancy is noted in-line.

Canonical join keys after loading:
    soc_code  : str 'NN-NNNN'           (renamed from 'Code' / 'SOC code')
    state     : full name, 'District of Columbia' for DC ('Washington DC' remapped)
    filing    : 'Single' | 'Head of household' | 'Married filing jointly'
    industry  : exact BEA sector/detail name (join on NAME, never position)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

SOC_PATTERN = r"^\d{2}-\d{4}$"

# ---- BEA 2024 control totals (verified) ----------------------------------------
EMP_TOTAL_THOUSANDS = 163_223.0      # briefing; file interior sums ~163,217 (rounding) -> rel tol
COMP_TOTAL_MUSD = 15_049_121.0
VA_TOTAL_MUSD = 29_298_075.0
CORP_PROFITS_BT_MUSD = 3_721_572.0
NONFARM_PROP_MUSD = 1_652_676.0
NET_INTEREST_MUSD = 579_219.0

NO_WAGE_TAX_STATES = frozenset(
    {"Alaska", "Florida", "Nevada", "New Hampshire", "South Dakota",
     "Tennessee", "Texas", "Washington", "Wyoming"}
)

_FILING_CANON = {
    "single": "Single",
    "head of household": "Head of household",
    "hoh": "Head of household",
    "married filing jointly": "Married filing jointly",
    "mfj": "Married filing jointly",
}


# --------------------------------------------------------------------------- utils
def _assert_close(observed, expected, rel=1e-3, abs_tol=0.0, name=""):
    obs, exp = float(observed), float(expected)
    denom = abs(exp) if exp != 0 else 1.0
    diff = abs(obs - exp)
    if diff / denom > rel and diff > abs_tol:
        raise AssertionError(
            f"control-total check failed [{name}]: observed {obs:,.4f} vs "
            f"expected {exp:,.4f} (rel diff {diff / denom:.2e} > tol {rel:.0e})"
        )


def canon_filing(x) -> str:
    s = str(x).strip()
    return _FILING_CANON.get(s.lower(), s)


def canon_state(x) -> str:
    s = str(x).strip()
    return "District of Columbia" if s == "Washington DC" else s


def _path(data_dir: Path, name: str) -> Path:
    p = Path(data_dir) / name
    if not p.exists():
        raise FileNotFoundError(f"expected data file not found: {p}")
    return p


# ------------------------------------------------------------------ 1. matrices
def load_matrices(data_dir: Path = DATA_DIR, validate: bool = True) -> dict:
    """occupation x industry employment & compensation (the spine).

    Returns tidy long frames keyed (soc_code, industry):
        'detail' : 833 occ x 71 detail industries  -> emp_thousands, comp_musd
        'sector' : 833 occ x 20 BEA sectors         -> emp_thousands, comp_musd
    plus the cleaned wide matrices under '*_wide'. The trailing 'Column total (BEA)'
    row (blank Code) is dropped.
    """
    path = _path(data_dir, "occ_industry_matrices_v2_aligned.xlsx")

    def _one(sheet: str, value_name: str):
        df = pd.read_excel(path, sheet_name=sheet, dtype={"Code": "string"})
        df = df[df["Code"].notna()].copy()                      # drop 'Column total (BEA)'
        df["Code"] = df["Code"].str.strip()
        df = df.rename(columns={"Code": "soc_code", "2024 NEM occupation": "occupation_title"})
        long = df.melt(
            id_vars=["soc_code", "occupation_title"],
            var_name="industry", value_name=value_name,
        )
        long[value_name] = long[value_name].astype(float)
        return df, long

    demp_w, demp = _one("Detail employment (000s)", "emp_thousands")
    semp_w, semp = _one("Sector employment (000s)", "emp_thousands")
    dcomp_w, dcomp = _one("Detail compensation ($m)", "comp_musd")
    scomp_w, scomp = _one("Sector compensation ($m)", "comp_musd")

    detail = demp.merge(dcomp.drop(columns="occupation_title"), on=["soc_code", "industry"])
    sector = semp.merge(scomp.drop(columns="occupation_title"), on=["soc_code", "industry"])

    if validate:
        assert len(demp_w) == 833, f"expected 833 occupation rows, got {len(demp_w)}"
        assert demp_w["soc_code"].is_unique, "duplicate SOC codes in matrices"
        assert demp_w["soc_code"].str.match(SOC_PATTERN).all(), "bad SOC format in matrices"
        assert "55-0000" in set(demp_w["soc_code"]), "Military pseudo-row 55-0000 missing"
        assert demp_w.shape[1] - 2 == 71, "expected 71 detail industries"
        assert semp_w.shape[1] - 2 == 20, "expected 20 BEA sectors"
        # emp tolerance is looser than comp's (1e-4) by design: EMP_TOTAL_THOUSANDS is the
        # briefing figure (163,223) while the file interior sums to ~163,217 — a ~3.4e-5
        # rounding gap baked in by construction, so 1e-4 would have little headroom.
        _assert_close(detail["emp_thousands"].sum(), EMP_TOTAL_THOUSANDS, rel=1e-3,
                      name="matrices detail employment total")
        _assert_close(detail["comp_musd"].sum(), COMP_TOTAL_MUSD, rel=1e-4,
                      name="matrices detail compensation total")
        # detail and sector are aggregations of each other -> equal within rounding only
        _assert_close(sector["emp_thousands"].sum(), detail["emp_thousands"].sum(), rel=1e-3,
                      name="sector vs detail employment")
        _assert_close(sector["comp_musd"].sum(), detail["comp_musd"].sum(), rel=1e-3,
                      name="sector vs detail compensation")

    return {"detail": detail, "sector": sector,
            "detail_wide": demp_w, "sector_wide": semp_w}


# --------------------------------------------------------------- 2. AI exposure
def load_ai_exposure(data_dir: Path = DATA_DIR, validate: bool = True) -> dict:
    """Yale Budget Lab AI exposure (PCA score) by occupation + industry aggregates.

    'occ'    : 832 occupations (Military absent entirely; NOT 833)
    'sector' : 20 BEA sectors  (the 'National (all industries)' total row is dropped)
    'detail' : 70 detail industries (Military industry absent; left-join from matrices)
    """
    path = _path(data_dir, "occupation_ai_exposure.xlsx")

    occ = pd.read_excel(path, sheet_name="Occupation AI exposure", dtype={"Code": "string"})
    occ = occ.rename(columns={
        "Code": "soc_code", "2024 NEM occupation": "occupation_title",
        "AI PCA score": "ai_pca_score", "Imputed?": "is_imputed",
        "Employees (000s)": "emp_thousands", "Compensation ($m)": "comp_musd",
        "Avg comp/worker ($)": "avg_comp_usd",
    })
    occ["soc_code"] = occ["soc_code"].str.strip()
    occ["is_imputed"] = occ["is_imputed"].eq("yes")              # NaN -> False (sparse 'yes')

    sec = pd.read_excel(path, sheet_name="Industry exposure (sector)").rename(columns={
        "Industry": "industry", "Employees (000s)": "emp_thousands",
        "Compensation ($m)": "comp_musd",
        "Emp-weighted exposure": "exposure_emp_wt", "Comp-weighted exposure": "exposure_comp_wt",
    })
    sec = sec[sec["industry"] != "National (all industries)"].copy()   # drop total row

    det = pd.read_excel(path, sheet_name="Industry exposure (detail)").rename(columns={
        "Detail industry": "industry", "Parent sector": "parent_sector",
        "Employees (000s)": "emp_thousands", "Compensation ($m)": "comp_musd",
        "Emp-weighted exposure": "exposure_emp_wt", "Comp-weighted exposure": "exposure_comp_wt",
    })

    if validate:
        assert len(occ) == 832, f"expected 832 exposure occupations, got {len(occ)}"
        assert occ["soc_code"].is_unique and occ["soc_code"].str.match(SOC_PATTERN).all()
        assert int(occ["is_imputed"].sum()) == 68, "expected 68 imputed occupations"
        assert -3.5 < occ["ai_pca_score"].min() < -3.3, "PCA min out of expected range"
        assert 7.0 < occ["ai_pca_score"].max() < 7.1, "PCA max out of expected range"
        assert len(sec) == 20, f"expected 20 sectors after dropping National, got {len(sec)}"
        assert len(det) == 70, f"expected 70 detail industries, got {len(det)}"

    return {"occ": occ, "sector": sec, "detail": det}


# ------------------------------------------------------------------ 3. capital
def load_capital(data_dir: Path = DATA_DIR, validate: bool = True) -> dict:
    """Capital income & corporate effective tax by sector.

    'sectors' : 20 BEA sectors (Government has zero corp base, NaN ratio cols).
    'total'   : the 'Total / aggregate' row as a Series (for cross-checks).
    """
    path = _path(data_dir, "capital_income_by_sector.xlsx")
    df = pd.read_excel(path, sheet_name="Capital income & tax by sector")
    df = df.rename(columns={
        "Industry": "industry", "Value added ($m)": "value_added_musd",
        "Compensation ($m)": "comp_musd", "Labor share": "labor_share",
        "Capital share": "capital_share",
        "Gross operating surplus ($m)": "gross_operating_surplus_musd",
        "Corp profits before tax ($m)": "corp_profits_bt_musd",
        "Taxes on corp income ($m)": "taxes_on_corp_income_musd",
        "Effective corp tax rate": "eff_corp_tax_rate",
        "Corp profits after tax ($m)": "corp_profits_at_musd",
        "Net dividends ($m)": "net_dividends_musd",
        "Dividend payout ratio": "dividend_payout_ratio",
        "Nonfarm proprietors' income ($m)": "nonfarm_proprietors_income_musd",
        "Net interest ($m)": "net_interest_musd",
        "Corp share of taxable capital income": "corp_share_taxable_capital_income",
    })
    total = df[df["industry"] == "Total / aggregate"].iloc[0]
    sectors = df[df["industry"] != "Total / aggregate"].copy()

    if validate:
        assert len(sectors) == 20, f"expected 20 sectors, got {len(sectors)}"
        _assert_close(total["value_added_musd"], VA_TOTAL_MUSD, rel=1e-6, name="capital VA total")
        _assert_close(total["comp_musd"], COMP_TOTAL_MUSD, rel=1e-6, name="capital comp total")
        _assert_close(total["corp_profits_bt_musd"], CORP_PROFITS_BT_MUSD, rel=1e-6,
                      name="capital corp profits BT total")
        _assert_close(total["nonfarm_proprietors_income_musd"], NONFARM_PROP_MUSD, rel=1e-6,
                      name="capital nonfarm proprietors total")
        _assert_close(total["net_interest_musd"], NET_INTEREST_MUSD, rel=1e-6,
                      name="capital net interest total")
        _assert_close(sectors["value_added_musd"].sum(), VA_TOTAL_MUSD, rel=1e-6,
                      name="capital VA interior sum")
        # Government: zero corporate profit base
        gov = sectors[sectors["industry"] == "Government"].iloc[0]
        assert gov["corp_profits_bt_musd"] == 0, "Government should have zero corp profit base"

    return {"sectors": sectors, "total": total}


# --------------------------------------------------------------- 4. government
def load_government(data_dir: Path = DATA_DIR, validate: bool = True) -> dict:
    """Government ledger ($billions, 2024). Trailing total/subtotal rows dropped.

    'receipts'     : 15 line items (federal + state-local), tagged to a model base.
    'transfers'    : 17 programs, tagged automation-sensitivity {HIGH,Medium,Med-High,Low,No}.
    'base_linkage' : starting effective rates by tax stream (Consumption/Property pending->NaN).
    """
    path = _path(data_dir, "government_fiscal_accounts.xlsx")

    receipts = pd.read_excel(path, sheet_name="Receipts")
    receipts = receipts[receipts["Level"].notna()].copy()       # drops trailing TOTAL row
    receipts = receipts.rename(columns={
        "Level": "level", "Receipt source": "receipt_source",
        "2024 ($B)": "amount_busd", "Maps to base": "maps_to_base", "Notes": "notes",
    })
    receipts["amount_busd"] = receipts["amount_busd"].astype(float)

    transfers = pd.read_excel(path, sheet_name="Transfers & stabilizers")
    transfers = transfers[transfers["Level"].notna()].copy()    # drops 2 trailing summary rows
    transfers = transfers.rename(columns={
        "Level": "level", "Program": "program", "2024 ($B)": "amount_busd",
        "Automation-sensitivity": "automation_sensitivity", "Notes": "notes",
    })
    transfers["amount_busd"] = transfers["amount_busd"].astype(float)
    # NOTE: tag casing is intentionally inconsistent ('HIGH' vs 'Medium'); preserve verbatim.

    base = pd.read_excel(path, sheet_name="Base linkage & eff. rates")
    base = base.rename(columns={
        "Tax stream": "tax_stream", "Federal ($B)": "federal_busd",
        "State & local ($B)": "state_local_busd", "Total ($B)": "total_busd",
        "Model base": "model_base", "Base ($B)": "base_busd",
        "Avg effective rate": "avg_effective_rate",
    })
    base["base_busd"] = pd.to_numeric(base["base_busd"], errors="coerce")     # 'pending' -> NaN
    base["avg_effective_rate"] = pd.to_numeric(base["avg_effective_rate"], errors="coerce")

    if validate:
        assert len(receipts) == 15, f"expected 15 receipt line items, got {len(receipts)}"
        assert len(transfers) == 17, f"expected 17 transfer programs, got {len(transfers)}"
        fed_inc = receipts.loc[receipts["receipt_source"].str.contains("income", case=False)
                              & receipts["level"].eq("Federal"), "amount_busd"]
        medicaid = transfers.loc[transfers["program"].str.contains("Medicaid", case=False),
                                 "amount_busd"]
        _assert_close(medicaid.iloc[0], 938.2, rel=1e-3, name="Medicaid outlay")
        ind = base.loc[base["tax_stream"].str.contains("income", case=False)
                       & base["model_base"].notna(), "avg_effective_rate"]
        # individual income effective rate ~ 19.5%
        assert any(abs(v - 0.1953) < 5e-3 for v in base["avg_effective_rate"].dropna()), \
            "individual income effective rate ~19.5% not found"

    return {"receipts": receipts, "transfers": transfers, "base_linkage": base}


# ---------------------------------------------------------------- 5. state OEWS
def load_state_oews(data_dir: Path = DATA_DIR, validate: bool = True) -> dict:
    """State x occupation wage distributions (OEWS May 2025).

    'detail' : detail occupations only (the 1,122 major-group '-0000' aggregate rows
               are removed). Wages in $/yr and $/hr; Employment in PERSONS.
               Blanks kept as NaN (hourly-only occupations + small-state suppression).
    'major'  : the dropped major-group aggregate rows (kept for reference).

    NOTE: no top-code censoring in this file (real values up to ~$627k flow through),
    contrary to the briefing -- so no top-code imputation is applied here. Annual wage
    is blank only for hourly-reported occupations; derive annual = hourly*2080 downstream.
    """
    path = _path(data_dir, "state_occupation_numbers_oews.xlsx")
    df = pd.read_excel(path, sheet_name="State OEWS (all groups)", dtype={"SOC code": "string"})
    df = df.rename(columns={
        "Area": "state", "SOC code": "soc_code", "Occupation": "occupation",
        "Employment": "employment_persons", "Emp % RSE": "emp_rse_pct",
        "Hourly mean wage": "hourly_mean_usd", "Annual mean wage": "annual_mean_usd",
        "Wage % RSE": "wage_rse_pct",
        "Hourly 10th": "hourly_p10_usd", "Hourly 25th": "hourly_p25_usd",
        "Hourly median": "hourly_p50_usd", "Hourly 75th": "hourly_p75_usd",
        "Hourly 90th": "hourly_p90_usd",
        "Annual 10th": "annual_p10_usd", "Annual 25th": "annual_p25_usd",
        "Annual median": "annual_p50_usd", "Annual 75th": "annual_p75_usd",
        "Annual 90th": "annual_p90_usd",
        "Emp per 1,000": "emp_per_1000", "Location quotient": "location_quotient",
    })
    df["soc_code"] = df["soc_code"].str.strip()
    df["state"] = df["state"].map(canon_state)

    is_major = df["soc_code"].str.endswith("-0000")
    detail = df[~is_major].copy()
    major = df[is_major].copy()

    if validate:
        assert df["state"].nunique() == 51, f"expected 51 areas, got {df['state'].nunique()}"
        assert df["soc_code"].str.match(SOC_PATTERN).all(), "bad SOC format in OEWS"
        assert len(major) == 22 * 51, f"expected 1122 major-group rows, got {len(major)}"
        assert "55-0000" not in set(df["soc_code"]), "Military 55-0000 unexpectedly present"

    return {"detail": detail, "major": major}


# --------------------------------------------------------------- 6. consumption
def load_consumption(data_dir: Path = DATA_DIR, validate: bool = True) -> pd.DataFrame:
    """Effective sales/excise tax per dollar of household consumption, by state.

    51 geographies (the 'United States' aggregate row is dropped). Rate columns are
    stored as PERCENT in the file; eff_tax_rate_frac is added in [0,1].
    """
    path = _path(data_dir, "taxable_consumption_base_by_state.xlsx")
    df = pd.read_excel(path, sheet_name="Effective consumption tax")
    df = df.rename(columns={
        "State": "state", "Total PCE ($m)": "total_pce_musd",
        "Taxable goods+services ($m)": "taxable_goods_services_musd",
        "Grocery treatment": "grocery_treatment",
        "Grocery taxable ($m)": "grocery_taxable_musd",
        "Total taxable PCE ($m)": "total_taxable_pce_musd",
        "Taxable share of PCE": "taxable_share_pct",
        "Combined sales rate": "combined_sales_rate_pct",
        "Eff. tax rate on consumption": "eff_tax_rate_pct",
        "Sales-tax breadth (T21)": "sales_tax_breadth_pct",
    })

    if validate:
        us = df[df["state"] == "United States"]
        assert len(us) == 1, "expected one 'United States' aggregate row"
        _assert_close(us.iloc[0]["eff_tax_rate_pct"], 2.093439, rel=1e-4,
                      name="US consumption eff rate (percent form)")

    df = df[df["state"] != "United States"].copy()
    df["state"] = df["state"].map(canon_state)
    df["eff_tax_rate_frac"] = df["eff_tax_rate_pct"] / 100.0
    df["total_taxable_pce_musd"] = df["total_taxable_pce_musd"].astype(float)

    if validate:
        assert len(df) == 51, f"expected 51 geographies, got {len(df)}"
        n_zero = int((df["eff_tax_rate_pct"] == 0).sum())
        assert n_zero == 4, f"expected 4 exactly-zero states (DE,MT,NH,OR), got {n_zero}"

    return df


# ----------------------------------------------------------------- 7. household
def load_household(data_dir: Path = DATA_DIR, validate: bool = True) -> pd.DataFrame:
    """Filing-status mix & mean HOUSEHOLD income (HINCP) by occupation x state (ACS 2024).

    38,021 rows (sparse: 795 SOC x 51 states with suppression). Income NaN kept as-is
    (small-cell suppression); negative incomes are valid HINCP losses -> not clipped.
    Income is the HOUSEHOLD total, NOT the worker's wage (scale OEWS multiplicatively).
    """
    path = _path(data_dir, "household_archetypes_by_state.xlsx")
    df = pd.read_excel(path, sheet_name="Household archetypes by SOC-state",
                       dtype={"SOC code": "string"})
    df = df.rename(columns={
        "State": "state", "SOC code": "soc_code", "Occupation": "occupation",
        "P(married/MFJ)": "p_mfj", "P(single parent/HoH)": "p_hoh", "P(single)": "p_single",
        "Avg HH income married ($)": "inc_married_usd",
        "Avg HH income HoH ($)": "inc_hoh_usd",
        "Avg HH income single ($)": "inc_single_usd",
        "Person weight": "person_weight",
    })
    df["soc_code"] = df["soc_code"].str.strip()
    df["state"] = df["state"].map(canon_state)

    if validate:
        assert df.shape == (38021, 10), f"expected (38021, 10), got {df.shape}"
        assert df["state"].nunique() == 51 and "District of Columbia" in set(df["state"])
        assert df["soc_code"].nunique() == 795, "expected 795 distinct SOC codes"
        assert df["soc_code"].str.match(SOC_PATTERN).all(), "bad SOC format in household"
        p_sum = df[["p_mfj", "p_hoh", "p_single"]].sum(axis=1)
        assert ((p_sum - 1.0).abs() <= 1e-3).all(), "filing-share P() columns must sum to 1"
        assert not df.duplicated(["state", "soc_code"]).any(), "duplicate (state, soc) cells"

    return df


# ------------------------------------------------------------- 8. tax schedule
def load_tax_schedule(data_dir: Path = DATA_DIR, validate: bool = True) -> dict:
    """Hand-rolled tax engine source-of-truth (federal/state income + payroll FICA).

    'fed_brackets'   : long (filing, bracket_floor_usd, marginal_rate, std_deduction_usd)
    'state_brackets' : long (state, filing, bracket_floor_usd, marginal_rate, std_deduction_usd)
                       taxing states only; NO Head-of-household (maps to Single downstream).
    'no_wage_tax'    : frozenset of the 9 no-wage-tax states.
    'payroll'        : OASDI / Medicare / Additional Medicare params.
    'baked_income'   : precomputed fed+state income tax by (income, filing, state) (cross-check).
    'baked_fica'     : precomputed FICA by (wage, filing) (cross-check).
    """
    path = _path(data_dir, "tax_side_schedule.xlsx")

    # -- Federal params: 'Filing' and 'Standard deduction' are sparse (first row of block) --
    fed = pd.read_excel(path, sheet_name="Federal params (2025)")
    fed = fed.rename(columns={
        "Filing": "filing", "Bracket floor ($)": "bracket_floor_usd",
        "Marginal rate": "marginal_rate", "Standard deduction ($)": "std_deduction_usd",
    })
    fed["filing"] = fed["filing"].ffill().map(canon_filing)
    fed["std_deduction_usd"] = fed.groupby("filing")["std_deduction_usd"].ffill()

    # -- State params: blocks keyed by 'State'; sub-blocks by 'Filing' --
    st = pd.read_excel(path, sheet_name="State params (2026)")
    st = st.rename(columns={
        "State": "state", "No wage tax?": "no_wage_tax", "Filing": "filing",
        "Bracket floor ($)": "bracket_floor_usd", "Marginal rate": "marginal_rate",
        "Std deduction ($)": "std_deduction_usd",
    })
    st["state"] = st["state"].ffill().map(canon_state)
    st["no_wage_tax"] = st.groupby("state")["no_wage_tax"].ffill()
    st["filing"] = st.groupby("state")["filing"].ffill()
    st["std_deduction_usd"] = st.groupby(["state", "filing"])["std_deduction_usd"].ffill()
    no_wage = frozenset(st.loc[st["no_wage_tax"].eq("YES"), "state"].unique())
    state_brackets = st[st["bracket_floor_usd"].notna()].copy()
    state_brackets["filing"] = state_brackets["filing"].map(canon_filing)
    state_brackets = state_brackets[
        ["state", "filing", "bracket_floor_usd", "marginal_rate", "std_deduction_usd"]
    ].reset_index(drop=True)

    # -- Payroll params --
    pay = pd.read_excel(path, sheet_name="Payroll params (2025)")
    pay = pay.rename(columns={
        "Component": "component", "Rate": "rate",
        "Cap / threshold ($)": "cap_threshold_usd", "Notes": "notes",
    })
    pay["cap_threshold_usd"] = pd.to_numeric(pay["cap_threshold_usd"], errors="coerce")

    # -- Baked lookup schedules (for cross-checking the from-params engine) --
    bi = pd.read_excel(path, sheet_name="Income tax schedule (baked)").rename(columns={
        "Household income ($)": "household_income_usd", "Filing": "filing", "State": "state",
        "Federal income tax ($)": "federal_tax_usd", "State income tax ($)": "state_tax_usd",
        "Total income tax ($)": "total_tax_usd", "Federal eff. rate": "federal_eff_rate",
        "State eff. rate": "state_eff_rate", "Combined eff. rate": "combined_eff_rate",
        "Federal marginal": "federal_marginal", "State marginal": "state_marginal",
    })
    bi["filing"] = bi["filing"].map(canon_filing)
    bi["state"] = bi["state"].map(canon_state)

    bf = pd.read_excel(path, sheet_name="Payroll FICA schedule (baked)").rename(columns={
        "Worker wage ($)": "wage_usd", "Filing": "filing", "OASDI ($)": "oasdi_usd",
        "Medicare ($)": "medicare_usd", "Addl Medicare ($)": "addl_medicare_usd",
        "Total FICA ($)": "total_fica_usd", "FICA eff. rate": "fica_eff_rate",
        "FICA marginal rate": "fica_marginal_rate",
    })
    bf["filing"] = bf["filing"].map(canon_filing)

    if validate:
        assert set(fed["filing"]) == {"Single", "Head of household", "Married filing jointly"}
        assert (fed.groupby("filing").size() == 7).all(), "expected 7 federal brackets per filing"
        assert no_wage == NO_WAGE_TAX_STATES, f"no-wage-tax set mismatch: {no_wage}"
        assert state_brackets["state"].nunique() == 42, "expected 42 taxing states"
        assert "Head of household" not in set(state_brackets["filing"]), \
            "state brackets unexpectedly include HoH"
        assert bi["state"].nunique() == 51 and len(bi) == 3366
        assert len(bf) == 57
        # MFJ $200k baked federal tax = 27,228 (the correct bracket math; Validation sheet's
        # 'expected $29,016' is a known typo in the source file).
        row = bi[(bi["household_income_usd"] == 200000)
                 & (bi["filing"] == "Married filing jointly")].iloc[0]
        _assert_close(row["federal_tax_usd"], 27228, rel=1e-3, name="baked MFJ $200k federal tax")

    return {"fed_brackets": fed, "state_brackets": state_brackets, "no_wage_tax": no_wage,
            "payroll": pay, "baked_income": bi, "baked_fica": bf}


# --------------------------------------------------------------------- bundle
@dataclass
class FiscalData:
    matrices_detail: pd.DataFrame
    matrices_sector: pd.DataFrame
    exposure_occ: pd.DataFrame
    exposure_sector: pd.DataFrame
    exposure_detail: pd.DataFrame
    capital: pd.DataFrame
    capital_total: pd.Series
    receipts: pd.DataFrame
    transfers: pd.DataFrame
    base_linkage: pd.DataFrame
    oews: pd.DataFrame
    oews_major: pd.DataFrame
    consumption: pd.DataFrame
    household: pd.DataFrame
    fed_brackets: pd.DataFrame
    state_brackets: pd.DataFrame
    state_no_wage_tax: frozenset
    payroll_params: pd.DataFrame
    baked_income: pd.DataFrame
    baked_fica: pd.DataFrame


def load_all(data_dir: Path = DATA_DIR, validate: bool = True) -> FiscalData:
    """Load and validate all eight files into one bundle. Fails loudly on a bad file."""
    m = load_matrices(data_dir, validate)
    e = load_ai_exposure(data_dir, validate)
    c = load_capital(data_dir, validate)
    g = load_government(data_dir, validate)
    o = load_state_oews(data_dir, validate)
    cons = load_consumption(data_dir, validate)
    hh = load_household(data_dir, validate)
    t = load_tax_schedule(data_dir, validate)
    return FiscalData(
        matrices_detail=m["detail"], matrices_sector=m["sector"],
        exposure_occ=e["occ"], exposure_sector=e["sector"], exposure_detail=e["detail"],
        capital=c["sectors"], capital_total=c["total"],
        receipts=g["receipts"], transfers=g["transfers"], base_linkage=g["base_linkage"],
        oews=o["detail"], oews_major=o["major"],
        consumption=cons, household=hh,
        fed_brackets=t["fed_brackets"], state_brackets=t["state_brackets"],
        state_no_wage_tax=t["no_wage_tax"], payroll_params=t["payroll"],
        baked_income=t["baked_income"], baked_fica=t["baked_fica"],
    )


if __name__ == "__main__":
    import time
    t0 = time.time()
    d = load_all()
    print(f"loaded & validated all files in {time.time() - t0:.1f}s\n")
    rows = [
        ("matrices_detail (soc x detail industry)", d.matrices_detail),
        ("matrices_sector (soc x sector)", d.matrices_sector),
        ("exposure_occ", d.exposure_occ),
        ("exposure_sector", d.exposure_sector),
        ("exposure_detail", d.exposure_detail),
        ("capital (sectors)", d.capital),
        ("receipts", d.receipts),
        ("transfers", d.transfers),
        ("base_linkage", d.base_linkage),
        ("oews (detail occs)", d.oews),
        ("oews_major (aggregates)", d.oews_major),
        ("consumption", d.consumption),
        ("household", d.household),
        ("fed_brackets", d.fed_brackets),
        ("state_brackets", d.state_brackets),
        ("payroll_params", d.payroll_params),
        ("baked_income", d.baked_income),
        ("baked_fica", d.baked_fica),
    ]
    for name, df in rows:
        print(f"  {name:42s} {df.shape}")
    print(f"\n  no-wage-tax states ({len(d.state_no_wage_tax)}): "
          f"{', '.join(sorted(d.state_no_wage_tax))}")
    print("\nAll control-total assertions passed.")
