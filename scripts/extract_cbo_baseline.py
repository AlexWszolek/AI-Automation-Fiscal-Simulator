"""One-off extraction: CBO Budget Projections workbook -> data/raw/cbo_baseline_2026.csv.

Source: CBO, "The Budget and Economic Outlook: 2026 to 2036" (February 2026),
supplemental data workbook 51118-2026-02-Budget-Projections.xlsx, sheet "Table 1-1"
(CBO's Baseline Budget Projections, by Category) — www.cbo.gov/publication/61882.

The committed CSV is the small, load-bearing slice the app needs (8 series x FY2025..FY2036,
billions of dollars, FY2025 = actual). Re-run only when CBO publishes a new baseline:
  .venv/bin/python scripts/extract_cbo_baseline.py [path-to-xlsx]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "cbo_baseline_2026.csv"
DEFAULT_XLSX = Path.home() / "Downloads" / "51118-2026-02-Budget-Projections.xlsx"
YEARS = list(range(2025, 2037))

# (csv series name, row-label prefix in Table 1-1, which match to take)
# The sheet has a $B block followed by a %-of-GDP block with identical labels — we always take
# the FIRST match ("Total" appears once under Revenues and once under Outlays, hence nth).
ROWS = [
    ("individual_income_taxes", "Individual income taxes", 0),
    ("payroll_taxes", "Payroll taxes", 0),
    ("corporate_income_taxes", "Corporate income taxes", 0),
    ("total_revenues", "Total", 0),
    ("total_outlays", "Total", 1),
    ("total_deficit", "Total deficit", 0),
    ("debt_held_by_public", "Debt held by the public", 0),
    ("gdp", "GDP", 0),
]

HEADER = """\
# CBO baseline budget projections, billions of dollars, federal fiscal years (FY2025 = actual).
# Source: CBO, The Budget and Economic Outlook: 2026 to 2036 (February 2026), Table 1-1,
# supplemental workbook 51118-2026-02-Budget-Projections.xlsx — www.cbo.gov/publication/61882.
# total_deficit is stored as published (negative = deficit).
# Extracted by scripts/extract_cbo_baseline.py — do not hand-edit.
"""


def main() -> None:
    xlsx = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XLSX
    t = pd.ExcelFile(xlsx).parse("Table 1-1", header=None)
    labels = t.iloc[:, 0].astype(str).str.strip()
    out = {}
    for name, prefix, nth in ROWS:
        matches = labels[labels.str.startswith(prefix)].index
        idx = matches[nth]
        out[name] = [round(float(t.iloc[idx, c]), 3) for c in range(1, 1 + len(YEARS))]
    df = pd.DataFrame(out, index=YEARS).T
    df.columns = YEARS
    df.index.name = "series"
    assert round(df.loc["total_revenues", 2026], 3) == 5595.916, df.loc["total_revenues", 2026]
    assert round(df.loc["total_deficit", 2025], 2) == -1775.37, df.loc["total_deficit", 2025]
    with open(OUT, "w") as f:
        f.write(HEADER)
        df.to_csv(f)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
