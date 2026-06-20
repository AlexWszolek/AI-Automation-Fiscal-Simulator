"""Part B.6 — validate the benefit bake.

(1) Aggregate reconciliation: weight the baked net benefits by the ACS household population
    (PUMS WGTP) and compare to the Government_Fiscal_Accounts stabilizer totals.
(2) Tax cross-check: PolicyEngine's income/payroll tax (stored in the bake) vs the hand-rolled
    tax_side_schedule engine, at points where refundable credits vanish.

Run: .venv/bin/python scripts/validate_transfers.py

Interpretation note: the bake models WORKING-AGE, non-disabled representative households
(adults age 40, kids). So EITC + refundable CTC (working-family programs) is the clean
reconciliation target; Medicaid/SSI/SNAP totals include the aged & disabled (long-term care,
SSI disability) our working-household bake does not represent, so those will UNDER-shoot by
design — that is expected, not a bug.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from fiscal_model import loaders
from fiscal_model.noc import load_pums_households
from fiscal_model.rates import build_engines

INTERIM = Path(__file__).resolve().parent.parent / "data" / "interim"

# Government_Fiscal_Accounts stabilizer actuals ($B, 2024)
ACTUALS_B = {"medicaid_value": 938.2, "snap": 97.4, "eitc_ctc": 228.8, "tanf": 24.5, "ssi": 65.2}


def aggregate_reconciliation():
    lk = pd.read_parquet(INTERIM / "benefit_lookup.parquet")
    pums = load_pums_households()                      # state, filing, hincp_adj, noc_bucket, wgt
    progs = ["eitc", "ctc_refundable", "snap", "medicaid_value", "aca_ptc", "tanf", "ssi"]

    # vectorized population weighting per (state, filing, n_children) group
    grids = {(s, f, int(nc)): g.sort_values("household_income")
             for (s, f, nc), g in lk.groupby(["state", "filing", "n_children"])}
    totals = {p: 0.0 for p in progs}
    pums["nc"] = pums["noc_bucket"].clip(upper=3)
    for (state, filing, nc), grp in pums.groupby(["state", "filing", "nc"]):
        key = (state, filing, int(nc))
        if key not in grids:
            key = (state, filing, 0)
        g = grids[key]
        xs = g["household_income"].to_numpy(float)
        inc = grp["hincp_adj"].clip(lower=0).to_numpy(float)
        w = grp["wgt"].to_numpy(float)
        for p in progs:
            totals[p] += float((np.interp(inc, xs, g[p].to_numpy(float)) * w).sum())

    modeled_b = {p: totals[p] / 1e9 for p in progs}
    rows = [
        ("EITC + refundable CTC", modeled_b["eitc"] + modeled_b["ctc_refundable"], ACTUALS_B["eitc_ctc"], "clean target (working-family)"),
        ("SNAP", modeled_b["snap"], ACTUALS_B["snap"], "partial (excl. aged/disabled)"),
        ("Medicaid", modeled_b["medicaid_value"], ACTUALS_B["medicaid_value"], "undershoot by design (no aged/disabled/LTC)"),
        ("TANF", modeled_b["tanf"], ACTUALS_B["tanf"], "partial"),
        ("SSI", modeled_b["ssi"], ACTUALS_B["ssi"], "undershoot by design (disability/aged)"),
        ("ACA PTC", modeled_b["aca_ptc"], float("nan"), "(no stabilizer line)"),
    ]
    print("=== Aggregate reconciliation: modeled (working pop) vs actual program totals ($B) ===")
    print(f"  {'program':24s} {'modeled':>9s} {'actual':>9s} {'ratio':>7s}  note")
    for name, mod, act, note in rows:
        ratio = f"{mod/act:6.2f}" if act == act and act else "   —  "
        act_s = f"{act:9.1f}" if act == act else "      n/a"
        print(f"  {name:24s} {mod:9.1f} {act_s} {ratio}  {note}")
    return modeled_b


def tax_crosscheck():
    data = loaders.load_all(validate=False)
    inc_engine, fica_engine = build_engines(data)
    lk = pd.read_parquet(INTERIM / "benefit_lookup.parquet")
    # Single, 0 kids (no CTC), high incomes where EITC=0 -> PE income_tax ~ federal bracket tax
    sub = lk[(lk["filing"] == "Single") & (lk["n_children"] == 0)
             & (lk["household_income"].isin([80_000, 100_000, 120_000, 150_000]))]
    print("\n=== Tax cross-check: PolicyEngine vs tax_side_schedule (Single, 0 kids) ===")
    print(f"  {'state':12s} {'income':>8s} {'PE inc tax':>11s} {'ours (fed)':>11s} {'PE payroll':>11s} {'ours(ee)':>10s}")
    samp = sub[sub["state"].isin(["California", "Texas", "New York"])].drop_duplicates(
        ["state", "household_income"])
    maxdiff_inc = maxdiff_pay = 0.0
    for _, r in samp.iterrows():
        ours_fed = inc_engine.federal_tax(r["household_income"], "Single")
        ours_ee = fica_engine.employee_fica(r["household_income"], "Single")
        maxdiff_inc = max(maxdiff_inc, abs(r["pe_income_tax"] - ours_fed) / max(ours_fed, 1))
        maxdiff_pay = max(maxdiff_pay, abs(r["pe_employee_payroll_tax"] - ours_ee) / max(ours_ee, 1))
        print(f"  {r['state']:12s} {r['household_income']:8.0f} {r['pe_income_tax']:11,.0f} "
              f"{ours_fed:11,.0f} {r['pe_employee_payroll_tax']:11,.0f} {ours_ee:10,.0f}")
    print(f"  -> max relative diff: income {maxdiff_inc:.1%}, payroll {maxdiff_pay:.1%}")


if __name__ == "__main__":
    aggregate_reconciliation()
    tax_crosscheck()
