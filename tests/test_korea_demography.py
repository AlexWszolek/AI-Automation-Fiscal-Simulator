"""The Korea demography path: pinned to the published medium-variant table, reconciled with
the press-release anchors, and shaped exactly as V2Params.demography_path consumes it."""
import numpy as np
import pytest

from fiscal_model.korea_demography import (
    MODEL_BASE_YEAR, WORKING_AGE_K, korea_demography_path, working_age_k)


def test_published_anchors():
    """2022 is 71.1% of the 51,673k total; 2030 is the quoted 3,417만; the press headline
    '332만 decline in ten years' is 2022→2032; 2072 closes the table."""
    assert WORKING_AGE_K[2022] == 36_743
    assert WORKING_AGE_K[2022] / 51_673 == pytest.approx(0.711, abs=5e-4)
    assert WORKING_AGE_K[2030] == 34_166
    assert WORKING_AGE_K[2022] - WORKING_AGE_K[2032] == pytest.approx(3_320, abs=5)
    assert WORKING_AGE_K[2072] == 16_575


def test_path_shape_for_v2params():
    """Index t with year 0 = 1.0, strictly positive, and — for Korea — strictly falling."""
    path = korea_demography_path(10)
    assert len(path) == 10
    assert path[0] == 1.0
    assert all(p > 0 for p in path)
    assert all(b < a for a, b in zip(path, path[1:]))
    # 2035 vs 2026, straight from the published table
    assert path[9] == pytest.approx(31_878 / 35_488)


def test_decade_scale_of_the_decline():
    """The model-horizon fact: the 2026 cohort's working-age population is ~10.2% smaller by
    2035 — the no-AI counterfactual the flat baseline would have missed."""
    path = korea_demography_path(10)
    assert 1.0 - path[-1] == pytest.approx(0.1017, abs=1e-3)


def test_interpolation_between_late_knots():
    assert working_age_k(2043) == pytest.approx(29_029 + (26_654 - 29_029) * 3 / 5)
    assert working_age_k(2045) == 26_654.0
    with pytest.raises(ValueError, match="outside the published projection"):
        working_age_k(2080)


def test_long_path_reaches_the_2050_halving_story():
    """Through 2050: 24,448/35,488 ≈ 0.689 — a third of the contribution base gone relative
    to 2026, before any automation. The projector consumes this horizon."""
    path = korea_demography_path(25)
    assert path[24] == pytest.approx(24_448 / 35_488, rel=1e-6)


def test_v2params_accepts_the_path():
    from fiscal_model.levers_v2 import V2Params
    p = V2Params(demography_path=list(korea_demography_path(10)))
    dp = np.asarray(p.demography_path, float)
    assert dp.size == 10 and np.isfinite(dp).all() and (dp > 0).all()


# ------------------------------------------------------------- extensive correctness additions
def test_every_knot_is_returned_exactly():
    for y, v in WORKING_AGE_K.items():
        assert working_age_k(y) == float(v)


def test_interpolation_is_piecewise_linear_in_the_late_segments():
    assert working_age_k(2041) == pytest.approx(29_029 + (26_654 - 29_029) / 5)
    assert working_age_k(2044) == pytest.approx(29_029 + (26_654 - 29_029) * 4 / 5)
    assert working_age_k(2071) == pytest.approx((17_111 + 16_575) / 2)
    for y in range(2041, 2072):
        lo = max(k for k in WORKING_AGE_K if k < y)
        hi = min(k for k in WORKING_AGE_K if k > y)
        assert min(WORKING_AGE_K[hi], WORKING_AGE_K[lo]) <= working_age_k(y) \
            <= max(WORKING_AGE_K[hi], WORKING_AGE_K[lo])


def test_single_period_path_and_bad_n():
    assert korea_demography_path(1) == (1.0,)
    with pytest.raises(ValueError, match="n_periods"):
        korea_demography_path(0)
