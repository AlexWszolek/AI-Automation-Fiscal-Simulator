"""The fund projector and institution routing. The load-bearing test is the first one: with
zero erosion the projector must reproduce NABO's published reserve paths and depletion years
IDENTICALLY — the module adds arithmetic to primary sources, never a competing projection."""
import numpy as np
import pytest

from fiscal_model.korea_cells import PAYM39_CSV, load_korea_cells
from fiscal_model.korea_funds import (
    EI_BASELINE, NHI_BASELINE, NHI_REFORM, contribution_losses, depletion_date,
    depletion_shift, erosion_fractions, first_negative_year, shifted_reserves)

pytestmark = pytest.mark.skipif(
    not PAYM39_CSV.exists(),
    reason="Korea tidy CSV not built — scripts/fetch_korea_tables.py --parse-only")


# ------------------------------------------------------------------ the anchor
def test_zero_erosion_reproduces_the_published_paths_identically():
    for fund in (NHI_BASELINE, NHI_REFORM, EI_BASELINE):
        z = np.zeros(len(fund.revenue))
        assert np.array_equal(shifted_reserves(fund, z), np.asarray(fund.reserves))


def test_published_depletion_years_match_nabo():
    """Focus 162's own statements: baseline depleted 2031, reform 2029 — two years earlier.
    The EI whole-fund baseline never crosses within its horizon (reserves rebuilt via
    planned borrowing); its story is the 0.1× benefit account, not a depletion date."""
    assert first_negative_year(NHI_BASELINE.reserves, 2026) == 2031
    assert first_negative_year(NHI_REFORM.reserves, 2026) == 2029
    assert first_negative_year(EI_BASELINE.reserves, 2026) is None


def test_fractional_depletion_dates_floor_to_nabo_years():
    """Calendar-decimal convention: the crossing happens DURING the first-negative year, so
    floor(fractional date) must equal NABO's published phrasing (adversarial-pass fix: the
    original convention was a year low)."""
    base = depletion_date(NHI_BASELINE.reserves, 2026)
    reform = depletion_date(NHI_REFORM.reserves, 2026)
    assert base == pytest.approx(2031 + 6.9 / 11.1)
    assert reform == pytest.approx(2029 + 7.6 / 8.7)
    assert int(base) == first_negative_year(NHI_BASELINE.reserves, 2026) == 2031
    assert int(reform) == first_negative_year(NHI_REFORM.reserves, 2026) == 2029
    assert depletion_date(EI_BASELINE.reserves, 2026) is None


# ------------------------------------------------------------------ shift mechanics
def test_erosion_pulls_depletion_forward_monotonically():
    n = len(NHI_REFORM.revenue)
    dates = [depletion_shift(NHI_REFORM, np.full(n, e), wage_linked_share=1.0)["eroded_date"]
             for e in (0.0, 0.02, 0.05, 0.10)]
    assert dates[0] == pytest.approx(depletion_date(NHI_REFORM.reserves, 2026))
    assert all(b < a for a, b in zip(dates, dates[1:]))
    shift = depletion_shift(NHI_REFORM, np.full(n, 0.05), wage_linked_share=1.0)
    assert shift["years_pulled_forward"] == pytest.approx(
        shift["base_date"] - shift["eroded_date"])
    assert shift["years_pulled_forward"] > 0


def test_depletion_shift_requires_the_full_horizon():
    with pytest.raises(AssertionError, match="full-horizon"):
        depletion_shift(NHI_REFORM, np.zeros(4), wage_linked_share=1.0)


def test_wage_linked_share_scales_the_erosion():
    n = len(NHI_REFORM.revenue)
    e = np.full(n, 0.10)
    full = shifted_reserves(NHI_REFORM, e, wage_linked_share=1.0)
    half = shifted_reserves(NHI_REFORM, e, wage_linked_share=0.5)
    published = np.asarray(NHI_REFORM.reserves)
    assert np.allclose(published - half, (published - full) / 2.0)


def test_erosion_path_longer_than_horizon_is_rejected():
    with pytest.raises(AssertionError, match="published horizon"):
        shifted_reserves(EI_BASELINE, np.zeros(10))


# ------------------------------------------------------------------ institution routing
@pytest.fixture(scope="module")
def cells():
    return load_korea_cells("2025").cells


def test_uniform_loss_erodes_every_institution_equally(cells):
    frac = erosion_fractions(0.01 * cells["emp"].to_numpy(), cells=cells)
    for k, v in frac.items():
        assert v == pytest.approx(0.01), k


def test_high_wage_loss_routes_to_the_general_account(cells):
    """The composition asymmetry, made testable: automate only the top wage bracket and the
    pension (capped) erodes proportionally LESS than the flat schemes, while the income-tax
    base (concentrated at the top) erodes the most. Which institution takes the hit depends
    on which cells automate — the claim a finance ministry can act on."""
    top = cells["bracket_hi_k"].isna().to_numpy()
    loss = np.where(top, 0.5 * cells["emp"].to_numpy(), 0.0)
    f = erosion_fractions(loss, cells=cells)
    assert f["NPS pension"] < f["NHI health"] == pytest.approx(f["LTC long-term care"])
    assert f["income tax (national)"] > f["NHI health"] > f["NPS pension"]


def test_low_wage_loss_routes_to_the_funds(cells):
    """The mirror image: automate the bottom brackets and the funds take the hit while the
    income-tax loss is negligible — and the PENSION erodes proportionally hardest, because
    the cap compresses top earners' weight in its base, leaving it relatively bottom-heavy.
    Low-wage automation is a pension-fund event; high-wage automation is a general-account
    event. Sharper than the research doc's symmetric phrasing, same direction."""
    bottom = (cells["bracket_hi_k"] <= 2000.0).to_numpy()
    loss = np.where(bottom, 0.5 * cells["emp"].to_numpy(), 0.0)
    f = erosion_fractions(loss, cells=cells)
    assert f["income tax (national)"] < f["NHI health"] / 5.0
    assert f["NPS pension"] > f["NHI health"] > f["income tax (national)"]


def test_losses_reconcile_with_the_payroll_engine(cells):
    """Scheme losses for the whole workforce must equal the engine's total payroll take."""
    from fiscal_model import rates
    engine = rates.PayrollFICA(components=rates.korea_payroll_components())
    losses = contribution_losses(cells["emp"].to_numpy(), cells=cells)
    w, emp = cells["wage_year_won"].to_numpy(), cells["emp"].to_numpy()
    scheme_sum = sum(losses[c.name] for c in rates.korea_payroll_components())
    assert scheme_sum == pytest.approx(float(engine.fica(w, "Single") @ emp))


def test_local_passthrough_is_a_memo_item_not_part_of_the_partition(cells):
    """The 40.03% line is an allocation OF the national loss — labelled memo so nobody sums
    it into the institutional partition (adversarial-pass fix: double-count hazard)."""
    losses = contribution_losses(0.01 * cells["emp"].to_numpy(), cells=cells)
    assert losses["memo: local share of national tax (40.03%)"] == pytest.approx(
        0.4003 * losses["income tax (national)"])
    non_memo = {k: v for k, v in losses.items() if not k.startswith("memo:")}
    assert len(non_memo) == 7           # 5 schemes + national income tax + local surtax


def test_nps_reform_path_reproduces_nabo_published_values():
    """The NPS anchor: zero erosion reproduces NABO's 표 25 — knot years hit the published
    contribution and reserve values exactly, and depletion lands in NABO's stated 2065
    (deficit transition 2047, pre-reform 2057 → the reform's eight bought years)."""
    from fiscal_model.korea_funds import NPS_REFORM, NPS_REFORM_KNOTS
    z = np.zeros(len(NPS_REFORM.revenue))
    assert np.array_equal(shifted_reserves(NPS_REFORM, z, 1.0),
                          np.asarray(NPS_REFORM.reserves))
    for year, (contrib, reserve) in NPS_REFORM_KNOTS.items():
        if year < 2026:
            continue
        t = year - 2026
        assert NPS_REFORM.revenue[t] == pytest.approx(contrib)
        assert NPS_REFORM.reserves[t] == pytest.approx(reserve)
    assert first_negative_year(NPS_REFORM.reserves, 2026) == 2065
    d = depletion_date(NPS_REFORM.reserves, 2026)
    assert 2065.0 < d < 2066.0


def test_nps_headline_composes_with_the_band():
    from fiscal_model.korea_scenarios import KOREA_PRESETS, korea_fund_headlines
    from fiscal_model.presets import build_adoption_path
    a = build_adoption_path(KOREA_PRESETS["korea-central"], 40)
    r = korea_fund_headlines(a, nhi_wage_linked_share=0.85, nps_wage_linked_share=0.85)
    assert 0.0 < r["nps"]["years_pulled_forward"] < 2.0
    with pytest.raises(AssertionError, match="documented band"):
        korea_fund_headlines(a, nhi_wage_linked_share=0.85, nps_wage_linked_share=0.5)
    with pytest.raises(AssertionError, match="NPS horizon"):
        korea_fund_headlines(a[:10], nhi_wage_linked_share=0.85, nps_wage_linked_share=0.85)


# ------------------------------------------------------------- extensive correctness additions
def test_shifted_reserves_matches_a_manual_loop():
    """Closed-form cumsum vs an explicit year-by-year loop — the shift arithmetic itself."""
    e = np.array([0.01, 0.03, 0.02, 0.05])
    got = shifted_reserves(EI_BASELINE, e, wage_linked_share=0.9)
    cum = 0.0
    for t in range(4):
        cum += EI_BASELINE.revenue[t] * 0.9 * e[t]
        assert got[t] == pytest.approx(EI_BASELINE.reserves[t] - cum)


def test_full_erosion_removes_exactly_the_cumulative_revenue():
    e = np.ones(len(NHI_REFORM.revenue))
    got = shifted_reserves(NHI_REFORM, e, wage_linked_share=1.0)
    expect = np.asarray(NHI_REFORM.reserves) - np.cumsum(NHI_REFORM.revenue)
    assert np.allclose(got, expect)


def test_date_conventions_agree_on_synthetic_paths():
    """floor(fractional date) must equal first_negative_year for any path that starts
    non-negative — including non-monotone paths, where only the FIRST crossing counts."""
    paths = [(5.0, 3.0, 1.0, -1.0), (5.0, -1.0, 2.0, -3.0), (0.0, 0.0, -0.5, -1.0),
             (10.0, 2.0, -0.1, -5.0), (1.0, 0.5, 0.25, 0.1)]
    for p in paths:
        fn = first_negative_year(p, 2030)
        d = depletion_date(p, 2030)
        if fn is None:
            assert d is None
        else:
            assert int(d) == fn, p


def test_depletion_date_first_crossing_only():
    assert depletion_date((5.0, -1.0, 2.0, -3.0), 2030) == pytest.approx(2031 + 5.0 / 6.0)


def test_contribution_losses_is_linear_and_zero_at_zero(cells):
    x = 0.004 * cells["emp"].to_numpy()
    one = contribution_losses(x, cells=cells)
    two = contribution_losses(2 * x, cells=cells)
    for k in one:
        assert two[k] == pytest.approx(2 * one[k], rel=1e-12), k
    zero = contribution_losses(np.zeros(len(cells)), cells=cells)
    assert all(v == 0.0 for v in zero.values())


def test_contribution_losses_rejects_bad_inputs(cells):
    emp = cells["emp"].to_numpy()
    with pytest.raises(AssertionError):
        contribution_losses(np.zeros(len(cells) - 1), cells=cells)      # wrong shape
    bad = np.zeros(len(cells)); bad[0] = -1.0
    with pytest.raises(AssertionError):
        contribution_losses(bad, cells=cells)                            # negative
    with pytest.raises(AssertionError):
        contribution_losses(emp * 1.01, cells=cells)                     # exceeds employment


def test_full_workforce_erosion_is_exactly_one(cells):
    f = erosion_fractions(cells["emp"].to_numpy(), cells=cells)
    for k, v in f.items():
        assert v == pytest.approx(1.0, rel=1e-12), k


def test_nps_interpolation_between_knots():
    from fiscal_model.korea_funds import NPS_REFORM
    t2035 = 2035 - 2026
    assert NPS_REFORM.revenue[t2035] == pytest.approx(88.2 + (109.9 - 88.2) / 2, abs=0.01)
    assert NPS_REFORM.reserves[t2035] == pytest.approx(1715.6 + (2653.7 - 1715.6) / 2, abs=0.01)
    # reserves peak at the 2047 knot (deficit transition), then decline monotonically
    r = np.asarray(NPS_REFORM.reserves)
    assert int(np.argmax(r)) == 2047 - 2026
    assert (np.diff(r[2047 - 2026:]) < 0).all()


def test_fundpath_rejects_mismatched_series():
    from fiscal_model.korea_funds import FundPath
    with pytest.raises(AssertionError):
        FundPath("bad", 2026, (1.0, 2.0), (1.0,), "test")
    with pytest.raises(AssertionError):
        FundPath("empty", 2026, (), (), "test")
