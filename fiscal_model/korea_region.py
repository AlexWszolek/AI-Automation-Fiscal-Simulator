"""The descriptive provincial exposure layer (workstream D): each 시도's occupation mix
weighted by the BOK displacement-prone (HELC) shares — WHERE the exposed work sits, with
two disclosed frame differences from the model proper and NO provincial fiscal claims:

- the survey is 지역별고용조사 (all EMPLOYED, self-employed included) — the model's cells
  are establishment-survey wage workers; the map is the geography of exposure, not a
  provincial revenue projection;
- the HELC weights are national within-occupation shares (BOK 그림 9) applied to each
  region's occupation MIX — regional variation in within-occupation exposure is not
  observed anywhere and therefore not invented.

Source: 국가데이터처 「2025년 상반기 지역별고용조사」 press-release statistical tables
(fetch script header has the exact attachment); committed raw + tidy CSV in
data/raw/korea/.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .korea_exposure import EXPOSURE_HELC

REGION_CSV = Path(__file__).resolve().parent.parent / "data" / "raw" / "korea" / "region_occupation.tidy.csv"

LATEST_PERIOD = "2025.1/2"

# display key + the tile-cartogram position (col, row) — the standard South Korea grid:
# capital NW, 강원 NE, the 충청/호남/영남 bands south of it, 제주 offshore SW
REGION_META = {
    "서울특별시": ("Seoul", "서울", 1, 0),
    "강원특별자치도": ("Gangwon", "강원", 2, 0),
    "인천광역시": ("Incheon", "인천", 0, 1),
    "경기도": ("Gyeonggi", "경기", 1, 1),
    "충청북도": ("Chungbuk", "충북", 2, 1),
    "경상북도": ("Gyeongbuk", "경북", 3, 1),
    "충청남도": ("Chungnam", "충남", 0, 2),
    "세종특별자치시": ("Sejong", "세종", 1, 2),
    "대전광역시": ("Daejeon", "대전", 2, 2),
    "대구광역시": ("Daegu", "대구", 3, 2),
    "전북특별자치도": ("Jeonbuk", "전북", 0, 3),
    "광주광역시": ("Gwangju", "광주", 1, 3),
    "경상남도": ("Gyeongnam", "경남", 2, 3),
    "울산광역시": ("Ulsan", "울산", 3, 3),
    "전라남도": ("Jeonnam", "전남", 0, 4),
    "부산광역시": ("Busan", "부산", 3, 4),
    "제주특별자치도": ("Jeju", "제주", 0, 5),
}


def load_region_occupation(period: str = LATEST_PERIOD) -> pd.DataFrame:
    df = pd.read_csv(REGION_CSV)
    out = df[df["period"] == period].copy()
    assert set(out["region"]) == set(REGION_META) | {"전국"}, "unexpected region set"
    assert (out.groupby("region")["occ_code"].count() == 9).all(), "9 majors per region"
    return out


def region_exposure(period: str = LATEST_PERIOD) -> pd.DataFrame:
    """Per 시도: employment (thousands), occupation shares, and the HELC-weighted
    displacement-prone share of employment. Includes the 전국 row for reference."""
    df = load_region_occupation(period)
    rows = []
    for region, g in df.groupby("region"):
        emp = g.set_index("occ_code")["emp_k"]
        shares = emp / emp.sum()
        helc = float(sum(shares[o] * EXPOSURE_HELC[o] for o in range(1, 10)))
        meta = REGION_META.get(region)
        rows.append({
            "region": region,
            "key": meta[0] if meta else "national",
            "short": meta[1] if meta else "전국",
            "col": meta[2] if meta else -1,
            "row": meta[3] if meta else -1,
            "emp_k": float(emp.sum()),
            "helc_share": helc,
        })
    out = pd.DataFrame(rows).sort_values("helc_share", ascending=False).reset_index(drop=True)
    # the national figure must be the employment-weighted mean of the regions (same table)
    nat = out[out.region == "전국"].iloc[0]
    reg = out[out.region != "전국"]
    implied = float((reg.helc_share * reg.emp_k).sum() / reg.emp_k.sum())
    assert abs(implied - nat.helc_share) < 5e-4, (implied, nat.helc_share)
    return out
