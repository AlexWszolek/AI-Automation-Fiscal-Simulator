"""Fetch Korea's occupation × industry joint employment matrix from ILOSTAT.

The public MOEL/KOSIS tables give only the marginals (PAYM39 occupations, PAYN42
industries); ILOSTAT's open API carries the LFS-based joint distribution — employment by
ISIC rev.4 section × ISCO-08 major group (indicator EMP_TEMP_ECO_OCU_NB_A) — and KSCO/KSIC
majors correspond 1:1 to ISCO/ISIC at this level (ISCO 5 splits into KSCO 4+5; noted where
consumed). Frame note, disclosed wherever this matrix is used: LFS covers ALL employed
persons (incl. self-employed), while the cell table is establishment-survey wage employees —
the matrix supplies allocation SHARES, not levels.

    .venv/bin/python scripts/fetch_ilostat_matrix.py     # writes data/raw/korea/ilostat_eco_ocu.csv
"""
from __future__ import annotations

import csv
import sys
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "korea" / "ilostat_eco_ocu.csv"
URL = ("https://rplumber.ilo.org/data/indicator/?id=EMP_TEMP_ECO_OCU_NB_A"
       "&ref_area=KOR&timefrom=2022&timeto=2024&format=.csv")


def main() -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=180).read().decode("utf-8-sig")
    rows = list(csv.DictReader(raw.splitlines()))
    keep = [r for r in rows if r["classif1"].startswith("ECO_ISIC4_")
            and r["classif2"].startswith("OCU_ISCO08_")]
    if not keep:
        sys.exit("ILOSTAT returned no ISIC×ISCO rows — API shape changed?")

    # validation: detail cells must reconcile with the published total per year
    for year in ("2022", "2023", "2024"):
        total = next(float(r["obs_value"]) for r in keep
                     if r["time"] == year and r["classif1"] == "ECO_ISIC4_TOTAL"
                     and r["classif2"] == "OCU_ISCO08_TOTAL")
        cells = sum(float(r["obs_value"]) for r in keep
                    if r["time"] == year and r["obs_value"]
                    and r["classif1"] != "ECO_ISIC4_TOTAL"
                    and r["classif2"] not in ("OCU_ISCO08_TOTAL",))
        assert abs(cells - total) / total < 0.02, (year, cells, total)
        print(f"{year}: cells {cells:,.0f}k vs total {total:,.0f}k ✓")

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keep[0].keys())
        w.writeheader()
        w.writerows(keep)
    print(f"wrote {OUT} ({len(keep)} rows)")


if __name__ == "__main__":
    main()
