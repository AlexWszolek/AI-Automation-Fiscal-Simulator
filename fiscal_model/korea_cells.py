"""The Korea cell structure — occupation × wage-bracket cells from MOEL PAYM39.

This is the Korean analogue of the US occupation × state cell table: the unit of account
every downstream engine prices over. The US model has 832 SOC × 51 states; the Korean data
ceiling (public tables carry only KSCO 6th major groups) gives **9 occupations × 24 total-
monthly-wage brackets = 216 cells, of which ~209 are populated**. Deliberately coarse,
transparently so — and for a progressive-tax model a joint wage *distribution* beats the
per-cell mean wages the US table provides.

Source: `data/raw/korea/DT_118N_PAYM39.tidy.csv` (regenerate offline with
`scripts/fetch_korea_tables.py --parse-only`), an establishment survey covering ~12.4m of
roughly 22m wage workers nationally — larger firms over-represented, no public
administration. That coverage is a headline disclosure, not a footnote.

The one derived number: the open top bracket (₩6.0m+/month) has no published mean, so its
mean is **solved from the published economy-wide mean wage** (₩4,482k/month in 2025,
PAYN42) — one unknown pinned by one external anchor, shared across occupations. Closed
brackets use midpoints; the bottom bracket ("~₩799.9k") uses half its ceiling.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "korea"
PAYM39_CSV = RAW / "DT_118N_PAYM39.tidy.csv"

# Published economy-wide mean total monthly wage (₩1,000/month), PAYN42, by year —
# the external anchor that pins the open top bracket's mean.
MEAN_WAGE_K = {"2025": 4482.0}

TOTAL_OCC = "전직종"
TOTAL = "전체"
WORKERS = "근로자수"
HOURS = "근로시간"


@dataclass(frozen=True)
class KoreaCells:
    """The cell table plus the reconciliation facts a caller may need to disclose."""

    cells: pd.DataFrame          # one row per populated occupation × bracket cell
    year: str
    total_workers: float         # published 전직종 total (persons)
    mean_wage_k: float           # published economy-wide mean (₩1,000/month)
    top_bracket_mean_k: float    # solved mean of the open top bracket (₩1,000/month)


def _parse_bracket(label: str) -> tuple[float, float | None]:
    """'800.0 ~ 899.9' -> (800, 900); '~799.9천원' -> (0, 800); '6000.0천원~' -> (6000, None)."""
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", label)]
    if label.strip().startswith("~"):
        return 0.0, round(nums[0] + 0.1, 1)
    if label.strip().endswith("~"):
        return nums[0], None
    assert len(nums) == 2, f"unparseable bracket label: {label!r}"
    return nums[0], round(nums[1] + 0.1, 1)


def load_korea_cells(year: str = "2025") -> KoreaCells:
    if not PAYM39_CSV.exists():
        raise FileNotFoundError(
            f"{PAYM39_CSV} missing — run scripts/fetch_korea_tables.py --parse-only")
    occ_rows: dict[tuple[str, str], dict] = {}
    total_workers = None
    with open(PAYM39_CSV, newline="", encoding="utf-8") as f:
        rdr = csv.reader(f)
        header = next(rdr)
        assert header[:4] == ["직종별", "성별", "임금계층별", "연령"], header
        for occ, sex, br, age, item, unit, yr, val in rdr:
            if yr != year or sex != TOTAL or age != TOTAL or val in ("", "-"):
                continue
            # the whole downstream contract hangs on these units — fail loud, not 1000× off
            if item == WORKERS:
                assert unit == "명", f"근로자수 unit changed: {unit!r} (expected 명/persons)"
            elif item == HOURS:
                assert unit == "시간", f"근로시간 unit changed: {unit!r} (expected 시간/hours)"
            if occ == TOTAL_OCC and br == TOTAL and item == WORKERS:
                total_workers = float(val)
            if occ == TOTAL_OCC or br == TOTAL:
                continue
            occ_rows.setdefault((occ, br), {})[item] = float(val)
    assert total_workers is not None, f"no published total for {year}"

    recs = []
    for (occ, br), items in sorted(occ_rows.items()):
        if WORKERS not in items:
            continue
        m = re.search(r"\((\d)\)$", occ)
        assert m, f"occupation label without KSCO group number: {occ!r}"
        lo, hi = _parse_bracket(br)
        recs.append({
            "occ_code": int(m.group(1)),
            "occ_label": occ,
            "bracket_label": br,
            "bracket_lo_k": lo,
            "bracket_hi_k": hi,
            "emp": items[WORKERS],
            "hours_month": items.get(HOURS, np.nan),
        })
    cells = pd.DataFrame(recs)

    # cells must reconcile with the published total up to independent rounding
    assert abs(cells["emp"].sum() - total_workers) <= 25, (
        cells["emp"].sum(), total_workers)

    # wage per cell: closed brackets at midpoint; the open top bracket's mean is solved
    # so the employment-weighted mean equals the published economy-wide mean
    mean_k = MEAN_WAGE_K[year]
    closed = cells["bracket_hi_k"].notna()
    cells.loc[closed, "wage_month_k"] = (
        (cells.loc[closed, "bracket_lo_k"] + cells.loc[closed, "bracket_hi_k"]) / 2.0)
    emp_top = cells.loc[~closed, "emp"].sum()
    assert emp_top > 0, "no workers in the open top bracket?"
    wsum_closed = (cells.loc[closed, "wage_month_k"] * cells.loc[closed, "emp"]).sum()
    top_mean = (mean_k * cells["emp"].sum() - wsum_closed) / emp_top
    top_floor = float(cells.loc[~closed, "bracket_lo_k"].iloc[0])
    assert top_floor < top_mean < 6 * top_floor, (
        f"solved top-bracket mean {top_mean:.0f}k implausible against floor {top_floor:.0f}k "
        "— midpoints or the published mean moved; re-derive before trusting")
    cells.loc[~closed, "wage_month_k"] = top_mean

    # by construction; guards regressions in the arithmetic above
    got_mean = (cells["wage_month_k"] * cells["emp"]).sum() / cells["emp"].sum()
    assert abs(got_mean - mean_k) < 1e-6

    cells["wage_year_won"] = cells["wage_month_k"] * 12_000.0   # ₩1,000/month -> ₩/year
    cells = cells.sort_values(["occ_code", "bracket_lo_k"]).reset_index(drop=True)
    return KoreaCells(cells=cells, year=year, total_workers=total_workers,
                      mean_wage_k=mean_k, top_bracket_mean_k=float(top_mean))
