"""Tables for the paired policy sweep — reads policy_sweep.parquet, writes committable CSVs.

Four questions, one table each (docs/research/policy-sweep/*.csv):
  ladder.csv     what each instrument setting does, paired per world
  scaling.csv    does the instrument collect most where it hurts most
  drivers.csv    debiased first-order η² of every uncertainty dim, per policy arm
  adoption.csv   median outcome by how far automation actually goes, per arm

η² debiasing reuses global_screening.eta_squared so numbers here and in report §7.14 mean the same
thing: raw η² carries an upward null bias of (k−1)/(n−1), which at n=5,000 with 20 bins is 0.004 —
small, but exactly the size of the effects that would otherwise look real.

Usage:  .venv/bin/python scripts/policy_sweep_report.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

from fiscal_model import mc
from global_screening import eta_squared

OUT = Path(__file__).resolve().parent.parent / "docs" / "research" / "policy-sweep"
ARMS = ["no-instruments", "status-quo", "compute-20", "compute-40", "auto-25", "auto-50",
        "max-revenue"]
UNC = [d for d, (_lo, _hi, t) in mc.GLOBAL_RANGES.items() if t == "uncertainty"]


def main() -> None:
    src = OUT / "policy_sweep.parquet"
    if not src.exists():
        sys.exit(f"{src} absent — run scripts/policy_sweep.py first")
    d = pd.read_parquet(src)
    arms = [a for a in ARMS if a in set(d.regime)]
    P = d.pivot(index="draw", columns="regime", values="fed_deficit_B")
    hole = P["no-instruments"]

    # ---- 1/2. the ladder -------------------------------------------------------------------
    ladder = pd.DataFrame([{
        "regime": a,
        "median_deficit_delta_B": round(P[a].median(), 1),
        "pct_worlds_worsen": round(100 * (P[a] > 0).mean(), 1),
        "median_vs_no_instruments_B": round((P[a] - hole).median(), 1),
        "median_pct_of_hole_closed": round(float(
            (1 - P[a] / hole).replace([np.inf, -np.inf], np.nan).median() * 100), 1),
        "pct_worlds_fully_closed": round(100 * (P[a] <= 0).mean(), 1),
    } for a in arms])
    ladder.to_csv(OUT / "ladder.csv", index=False)

    # ---- 3. does the instrument scale with the harm? ---------------------------------------
    sev = pd.qcut(hole, 5, labels=["mildest", "2nd", "3rd", "4th", "worst"])
    rows = []
    for a in arms:
        if a == "no-instruments":                 # the baseline raises exactly 0 — ρ undefined
            continue
        raised = hole - P[a]                      # deficit avoided == revenue raised, per world
        rows.append({"regime": a,
                     "spearman_raised_vs_hole": round(float(raised.rank().corr(hole.rank())), 3),
                     "median_raised_B": round(raised.median(), 1),
                     **{f"raised_{k}_B": round(raised[sev == k].median(), 1)
                        for k in sev.cat.categories},
                     **{f"hole_{k}_B": round(hole[sev == k].median(), 1)
                        for k in sev.cat.categories}})
    pd.DataFrame(rows).to_csv(OUT / "scaling.csv", index=False)

    # ---- 4. what drives the outcome, per arm ------------------------------------------------
    drivers = pd.DataFrame({a: {c: round(eta_squared(d[d.regime == a][c],
                                                     d[d.regime == a].fed_deficit_B)[1], 3)
                                for c in UNC} for a in arms})
    drivers.index.name = "lever"
    drivers.loc["_sum_first_order"] = drivers.sum().round(3)
    drivers.to_csv(OUT / "drivers.csv")

    # ---- 5. the adoption hedge --------------------------------------------------------------
    base = d[d.regime == "no-instruments"][["draw", "adoption_end"]].set_index("draw")
    q = pd.qcut(base.adoption_end, 5)
    rows = []
    for lab in q.cat.categories:
        ids = base.index[q == lab]
        r = {"adoption_end_quintile": str(lab)}
        for a in arms:
            r[a] = round(d[d.regime == a].set_index("draw").loc[ids, "fed_deficit_B"].median(), 1)
        rows.append(r)
    adopt = pd.DataFrame(rows)
    adopt.loc["spread"] = ["max−min of medians"] + [round(adopt[a].max() - adopt[a].min(), 1)
                                                    for a in arms]
    adopt.to_csv(OUT / "adoption.csv", index=False)

    print(f"n = {len(hole):,} worlds per arm; {len(arms)} arms")
    print(f"\nno-instruments hole: {100*(hole>0).mean():.1f}% of worlds worsen, "
          f"median {hole.median():,.0f}B, p95 {hole.quantile(.95):,.0f}B")
    print("\n" + ladder.to_string(index=False))
    print(f"\nwrote ladder.csv, scaling.csv, drivers.csv, adoption.csv → {OUT}")


if __name__ == "__main__":
    main()
