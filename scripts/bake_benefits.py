"""Part B — PolicyEngine benefit bake (offline -> static lookup).

Runs in the .venv (Python 3.12 + policyengine-us); the main fiscal_model code never
imports PolicyEngine. Produces `data/interim/benefit_lookup.parquet`:
net means-tested benefits as a function of household income, keyed by
(state, filing, n_children, household_income), so the kernel can interpolate and
difference it across the three residual-income phases (employed / on-UI / exhausted).

Run:  .venv/bin/python scripts/bake_benefits.py

Modeling choices (per transfer_side_build_plan.md Part B):
- One PolicyEngine Simulation per (state, filing, n_children) cell, with a dense income
  axis (resolves the EITC hump, SNAP phase-out, and Medicaid cliff). Medicaid value =
  eligibility x per-enrollee value (state expansion status matters and is baked in via state).
- Household structure: Single=1 adult/0 kids; HoH=1 adult + kids; MFJ=2 married adults + kids.
  Children get representative ages under 17 (CTC-eligible). Filing status is derived from
  structure (matches the archetype proxy; HoH-with-0-kids is structurally a single adult).
- Total household earnings on the axis (means tests use household income; the marginal
  delta differences net_benefits at income_before / _during / _after at kernel time).
- net_benefits = eitc + refundable_ctc + snap + medicaid + aca_ptc + tanf + ssi.
- PE income_tax / employee_payroll_tax are saved for the B.6 tax cross-check (NOT added to
  the kernel — taxes are hand-rolled from tax_side_schedule.xlsx).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from policyengine_us import Simulation

YEAR = 2024
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "interim"

# Dense income grid (constant $). $500 steps to $150k resolve the benefit kinks;
# above $150k means-tested benefits are 0 (kernel extrapolates flat).
INCOME_MIN, INCOME_MAX, INCOME_STEP = 0, 150_000, 500
N_INCOME = (INCOME_MAX - INCOME_MIN) // INCOME_STEP + 1     # 301 points

BENEFIT_VARS = ["eitc", "refundable_ctc", "snap", "medicaid", "aca_ptc", "tanf", "ssi"]
CROSSCHECK_VARS = ["income_tax", "employee_payroll_tax"]

# filing label -> (n_adults, child counts to bake)
FILINGS = {
    "Single": (1, [0]),
    "Head of household": (1, [0, 1, 2, 3]),
    "Married filing jointly": (2, [0, 1, 2, 3]),
}
CHILD_AGES = [8, 11, 14]   # representative, all < 17 (CTC-eligible); index by child number

STATE_TO_USPS = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


def build_situation(usps: str, n_adults: int, n_children: int) -> dict:
    people, members = {}, []
    for a in range(n_adults):
        pid = f"adult{a}"
        people[pid] = {"age": {YEAR: 40}}
        members.append(pid)
    for c in range(n_children):
        pid = f"child{c}"
        people[pid] = {"age": {YEAR: CHILD_AGES[min(c, len(CHILD_AGES) - 1)]}}
        members.append(pid)
    adults = [m for m in members if m.startswith("adult")]
    return {
        "people": people,
        "families": {"f": {"members": members}},
        "marital_units": {"m": {"members": adults}},
        "tax_units": {"t": {"members": members}},
        "spm_units": {"s": {"members": members}},
        "households": {"h": {"members": members, "state_name": {YEAR: usps}}},
        "axes": [[{"name": "employment_income", "count": N_INCOME,
                   "min": INCOME_MIN, "max": INCOME_MAX, "period": YEAR}]],
    }


def bake_cell(state: str, filing: str, n_adults: int, n_children: int) -> pd.DataFrame:
    sim = Simulation(situation=build_situation(STATE_TO_USPS[state], n_adults, n_children))
    income = np.array(sim.calculate("employment_income", YEAR, map_to="household"))
    data = {"state": state, "filing": filing, "n_children": n_children,
            "household_income": np.round(income).astype(int)}
    net = np.zeros(N_INCOME)
    for v in BENEFIT_VARS:
        col = np.array(sim.calculate(v, YEAR, map_to="household"))
        data[v] = col
        net += col
    data["net_benefits"] = net
    for v in CROSSCHECK_VARS:
        data["pe_" + v] = np.array(sim.calculate(v, YEAR, map_to="household"))
    return pd.DataFrame(data)


def ui_params_table() -> pd.DataFrame:
    """v1 UI parameters. Replacement rate / max weeks are national defaults; real
    state-by-state weekly-benefit caps and durations (DOL data) are a later refinement.
    UI is countable income for SNAP/MAGI Medicaid and partly taxable (handled at the
    residual point in the integration)."""
    rows = [{"state": s, "replacement_rate": 0.45, "max_weeks": 26,
             "annual_cap_usd": 20_000, "source": "v1 national default (refine w/ DOL)"}
            for s in STATE_TO_USPS]
    return pd.DataFrame(rows)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cells = [(s, f, na, nc) for s in STATE_TO_USPS for f, (na, ncs) in FILINGS.items()
             for nc in ncs]
    print(f"baking {len(cells)} cells x {N_INCOME} income points "
          f"(${INCOME_MIN}-{INCOME_MAX} step {INCOME_STEP}) ...", flush=True)

    frames, failures, t0 = [], [], time.time()
    last_state = None
    for i, (state, filing, na, nc) in enumerate(cells):
        if state != last_state:
            print(f"  [{i:3d}/{len(cells)}] {state}  ({time.time()-t0:.0f}s)", flush=True)
            last_state = state
        try:
            frames.append(bake_cell(state, filing, na, nc))
        except Exception as e:
            failures.append((state, filing, nc, f"{type(e).__name__}: {e}"))
            print(f"     ! FAILED {state}/{filing}/{nc}: {type(e).__name__}: {e}", flush=True)

    lookup = pd.concat(frames, ignore_index=True)
    lookup = lookup.rename(columns={"refundable_ctc": "ctc_refundable", "medicaid": "medicaid_value"})
    lookup.to_parquet(OUT_DIR / "benefit_lookup.parquet", index=False)
    ui_params_table().to_parquet(OUT_DIR / "ui_params.parquet", index=False)

    import importlib.metadata as md
    meta = pd.DataFrame([{
        "policyengine_us_version": md.version("policyengine-us"), "parameter_year": YEAR,
        "income_min": INCOME_MIN, "income_max": INCOME_MAX, "income_step": INCOME_STEP,
        "n_cells": len(cells), "n_failures": len(failures), "n_rows": len(lookup),
    }])
    meta.to_parquet(OUT_DIR / "benefit_lookup_meta.parquet", index=False)

    print(f"\ndone in {time.time()-t0:.0f}s. rows={len(lookup):,}  failures={len(failures)}")
    print(f"-> {OUT_DIR/'benefit_lookup.parquet'}")
    if failures:
        print("FAILURES:", failures[:10])


if __name__ == "__main__":
    main()
