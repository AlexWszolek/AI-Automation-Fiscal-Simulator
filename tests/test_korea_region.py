"""The provincial exposure layer: parse integrity, the cross-survey consistency anchor
(the BOK national HELC aggregate must reproduce from the LAFS occupation mix), and the
tile-grid geometry the map draws."""
import numpy as np
import pytest

from fiscal_model.korea_region import REGION_CSV, REGION_META

pytestmark = pytest.mark.skipif(
    not REGION_CSV.exists(),
    reason="region CSV not built — scripts/fetch_korea_region_occupation.py --parse-only")


@pytest.fixture(scope="module")
def regions():
    from fiscal_model.korea_region import region_exposure
    return region_exposure()


def test_seventeen_sido_plus_national(regions):
    assert len(regions) == 18
    assert set(regions["region"]) == set(REGION_META) | {"전국"}
    assert (regions["emp_k"] > 0).all()


def test_national_reproduces_the_bok_aggregate(regions):
    """THE anchor: BOK 그림 9 puts the displacement-prone (HELC) share at ~27% of
    employment. Weighting a DIFFERENT survey's occupation mix (LAFS all-employed) by the
    within-occupation HELC shares must land on it — two independent sources agreeing."""
    nat = float(regions.loc[regions.region == "전국", "helc_share"].iloc[0])
    assert nat == pytest.approx(0.27, abs=0.01)


def test_helc_shares_are_convex_combinations(regions):
    from fiscal_model.korea_exposure import EXPOSURE_HELC
    lo, hi = min(EXPOSURE_HELC.values()), max(EXPOSURE_HELC.values())
    assert (regions["helc_share"] > lo).all() and (regions["helc_share"] < hi).all()


def test_the_geography_is_the_expected_story(regions):
    """세종 (administrative capital, clerical epicentre) tops; 전남 (agriculture/heavy
    industry) bottoms; the capital belt sits above the national mean."""
    r = regions.set_index("short")["helc_share"]
    assert r.idxmax() == "세종" and r.idxmin() == "전남"
    nat = r["전국"]
    for cap in ("서울", "경기", "인천"):
        assert r[cap] > nat, cap


def test_tile_grid_positions_are_distinct(regions):
    tiles = regions[regions.region != "전국"]
    pos = list(zip(tiles["col"], tiles["row"]))
    assert len(pos) == len(set(pos)) == 17
    assert (tiles["col"] >= 0).all() and (tiles["row"] >= 0).all()
