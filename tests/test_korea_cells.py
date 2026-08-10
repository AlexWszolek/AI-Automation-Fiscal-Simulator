"""The Korea cell structure: 209 occupation × wage-bracket cells that must reconcile with the
published survey totals, with the single derived number (the open top bracket's mean) pinned to
the published economy-wide mean wage rather than to anything internal."""
import pytest

from fiscal_model.korea_cells import PAYM39_CSV, load_korea_cells

pytestmark = pytest.mark.skipif(
    not PAYM39_CSV.exists(),
    reason="Korea tidy CSV not built — scripts/fetch_korea_tables.py --parse-only")


@pytest.fixture(scope="module")
def kc():
    return load_korea_cells("2025")


def test_cell_count_is_the_published_joint_distribution(kc):
    """9 KSCO major groups × 24 brackets = 216 combinations, of which 7 are structurally empty
    (managers do not appear in the lowest wage bands). A different count means the scrape or the
    survey vintage changed."""
    assert len(kc.cells) == 209
    assert set(kc.cells["occ_code"]) == set(range(1, 10))
    assert kc.cells.groupby("occ_code")["bracket_label"].count().sum() == 209


def test_totals_reconcile_with_published_marginals(kc):
    """Cells must sum to the published 2025 total (12,413,858) up to the survey's own
    independent rounding of each cell."""
    assert kc.total_workers == 12_413_858
    assert abs(kc.cells["emp"].sum() - kc.total_workers) <= 25


def test_top_bracket_mean_is_anchored_not_free(kc):
    """The only derived number: the ₩6.0m+ bracket mean is solved so the employment-weighted
    mean wage equals PAYN42's published ₩4,482k/month — and the solution must sit above the
    bracket floor at a plausible multiple."""
    assert kc.mean_wage_k == 4482.0
    got = (kc.cells["wage_month_k"] * kc.cells["emp"]).sum() / kc.cells["emp"].sum()
    assert abs(got - kc.mean_wage_k) < 1e-6
    assert 6000.0 < kc.top_bracket_mean_k < 36_000.0
    top = kc.cells[kc.cells["bracket_hi_k"].isna()]
    assert (top["wage_month_k"] == kc.top_bracket_mean_k).all()


def test_bracket_boundaries_partition_the_wage_axis(kc):
    """Within each occupation, brackets must tile [0, ∞) without gaps or overlaps — the parsed
    boundaries are load-bearing for every progressive-tax calculation downstream."""
    for _, grp in kc.cells.groupby("occ_code"):
        grp = grp.sort_values("bracket_lo_k")
        prev_hi = 0.0
        for _, row in grp.iterrows():
            # a group may skip empty brackets; the next lo must never sit below the last hi
            assert row["bracket_lo_k"] >= prev_hi
            hi = row["bracket_hi_k"]
            if hi == hi:  # not NaN (the open top bracket)
                assert hi > row["bracket_lo_k"]
                prev_hi = hi
    full = kc.cells[kc.cells["occ_code"] == 3].sort_values("bracket_lo_k")  # clerks: all 24
    assert len(full) == 24
    assert (full["bracket_lo_k"].values[1:] == full["bracket_hi_k"].values[:-1]).all()


def test_wages_are_annualised_in_won(kc):
    assert (kc.cells["wage_year_won"] == kc.cells["wage_month_k"] * 12_000.0).all()
    assert kc.cells["wage_year_won"].min() == pytest.approx(4_800_000.0)


# ------------------------------------------------------------- extensive correctness additions
def test_parse_bracket_shapes_directly():
    from fiscal_model.korea_cells import _parse_bracket
    assert _parse_bracket("800.0 ~ 899.9") == (800.0, 900.0)
    assert _parse_bracket("~799.9천원") == (0.0, 800.0)
    assert _parse_bracket("6000.0천원~") == (6000.0, None)
    assert _parse_bracket("2000.0 ~ 2199.9") == (2000.0, 2200.0)
    with pytest.raises(AssertionError, match="unparseable"):
        _parse_bracket("garbage label")


def test_only_2025_is_loadable_and_says_so(kc):
    """MEAN_WAGE_K pins the top-bracket anchor per year; other vintages must fail loud, not
    silently reuse 2025's anchor."""
    with pytest.raises(KeyError):
        load_korea_cells("2024")


def test_every_closed_cell_wage_sits_inside_its_bracket(kc):
    closed = kc.cells[kc.cells["bracket_hi_k"].notna()]
    assert (closed["wage_month_k"] > closed["bracket_lo_k"]).all()
    assert (closed["wage_month_k"] < closed["bracket_hi_k"]).all()
    top = kc.cells[kc.cells["bracket_hi_k"].isna()]
    assert (top["wage_month_k"] == kc.top_bracket_mean_k).all()
    assert (top["bracket_lo_k"] == 6000.0).all()


def test_occ_codes_are_exactly_the_nine_ksco_majors(kc):
    assert sorted(kc.cells["occ_code"].unique()) == list(range(1, 10))
    for code, grp in kc.cells.groupby("occ_code"):
        assert grp["occ_label"].nunique() == 1
        assert grp["occ_label"].iloc[0].endswith(f"({code})")


def test_loading_is_deterministic(kc):
    again = load_korea_cells("2025")
    assert again.cells.equals(kc.cells)
    assert again.top_bracket_mean_k == kc.top_bracket_mean_k


def test_hours_are_plausible_monthly_hours(kc):
    hours = kc.cells["hours_month"].dropna()
    assert len(hours) == len(kc.cells)          # every populated cell reports hours
    assert (hours > 20).all() and (hours < 250).all()
