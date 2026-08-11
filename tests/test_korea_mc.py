"""Korea MC: deterministic, convention-pinned, and honest about what varies.

The traps this file guards: a reseeded axes stream silently reshuffling share draws
(determinism), the Korea conventions leaking into the sampled levers (pinning), and a
zero-spread run pretending lever uncertainty it doesn't have (variance accounting)."""
import numpy as np
import pandas as pd
import pytest

from fiscal_model.korea_cells import PAYM39_CSV

pytestmark = pytest.mark.skipif(
    not PAYM39_CSV.exists(),
    reason="Korea tidy CSV not built — scripts/fetch_korea_tables.py --parse-only")


@pytest.fixture(scope="module")
def mc8():
    from fiscal_model.korea_mc import run_korea_mc
    return run_korea_mc(n=8, spread=0.15, seed=3, invariant_every=4)


def test_same_seed_is_bit_identical(mc8):
    from fiscal_model.korea_mc import run_korea_mc
    again = run_korea_mc(n=8, spread=0.15, seed=3, invariant_every=4)
    pd.testing.assert_frame_equal(mc8.draws, again.draws)
    pd.testing.assert_frame_equal(mc8.tornado, again.tornado)


def test_pinned_conventions_never_reach_the_draws(mc8):
    from fiscal_model.korea_mc import KOREA_PINNED
    assert not set(KOREA_PINNED) & set(mc8.draws.columns)
    # the Korea axes are sampled per draw and inside their documented bounds
    from fiscal_model.korea_scenarios import WAGE_LINKED_SHARE
    assert mc8.draws["nhi_share"].between(WAGE_LINKED_SHARE["nhi"].low,
                                          WAGE_LINKED_SHARE["nhi"].high).all()
    assert mc8.draws["nps_share"].between(WAGE_LINKED_SHARE["nps"].low,
                                          WAGE_LINKED_SHARE["nps"].high).all()
    assert set(mc8.draws["exposure_delta"]) <= {-0.5, 0.0, 0.5}


def test_base_row_matches_the_bundle_central_pins(mc8):
    assert mc8.base["nhi_years_forward"] == pytest.approx(0.50, abs=0.02)
    assert mc8.base["ei_shortfall_tn"] == pytest.approx(5.5, abs=0.2)
    assert mc8.base["nps_given_back"] == pytest.approx(1.14, abs=0.03)
    assert mc8.base["nhi_erosion_2035"] == pytest.approx(0.091, abs=0.005)


def test_zero_spread_leaves_only_the_korea_axes(mc8):
    """spread=0 must collapse every LEVER to its base value — remaining headline variance
    can come only from the exposure read and the share bands (and the tornado must contain
    only those inputs, not constant-lever noise rows)."""
    from fiscal_model.korea_mc import run_korea_mc
    r = run_korea_mc(n=8, spread=0.0, seed=3, invariant_every=0)
    lever_cols = [c for c in r.draws.columns
                  if c not in ("exposure_delta", "nhi_share", "nps_share", "draw")
                  and c not in ("nhi_years_forward", "nps_given_back", "ei_shortfall_tn",
                                "employment_drop_pct", "nhi_erosion_2035")]
    for c in lever_cols:
        assert r.draws[c].nunique() == 1, c
    assert set(r.tornado["input"]) <= {"exposure_delta", "nhi_share", "nps_share"}
    # shares move the projection: nps_given_back must not be constant across draws
    assert r.draws["nps_given_back"].nunique() > 1


def test_percentiles_are_ordered(mc8):
    for h, g in mc8.percentiles.groupby("headline"):
        v = g.sort_values("pct")["value"].to_numpy()
        assert (np.diff(v) >= -1e-12).all(), h
