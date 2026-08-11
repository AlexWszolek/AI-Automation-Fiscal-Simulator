"""Korea's earmarked funds: institution routing and the depletion projector.

The headline metric — "automation pulls the depletion date forward by N years" — needs two
pieces the kernel does not have:

**1. Institution routing.** Which institution takes the hit depends on which cells automate:
the pension contribution is capped at ₩79.08m/yr (binding inside the model's wage range)
while health/LTC/EI are flat, and income tax is concentrated at the top. Given per-cell
employment losses, `contribution_losses` prices each scheme's loss with the same
`PayrollComponent.levy` arithmetic the payroll engine uses, plus the income-tax loss
(national + the 10% local surtax) and the statutory 40.03% local-transfer passthrough.
`erosion_fractions` normalises scheme losses by their cell-table baselines — the bridge
into the projector.

**2. The projector.** Each fund carries its PUBLISHED year-by-year revenue and year-end
reserve path (₩tn, primary sources in docs/research/sources/ — see the research doc §2).
Automation shifts the reserve path down by the cumulative eroded contribution revenue:

    reserve'_t = published_reserve_t − Σ_{s≤t} revenue_s · wage_linked_share · erosion_s

We deliberately do NOT re-accumulate from balances: NHI's published reserves chain from its
balances to within rounding (verified), but EI's whole-fund reserves also move with planned
Public-Capital-Management-Fund borrowing flows — published paths already embed the financing
assumptions, and the model's claim is only about the contribution side. Zero erosion
therefore reproduces the published path *identically* — the anchor test for the module.

Legislated rate rises (the pension phase-in, NHI's 8%-cap trajectory) live inside the
published revenue paths, so the kernel needs no time-varying payroll rates; the model
supplies erosion *fractions* of the wage-linked base, which are rate-invariant to first
order.

**NPS joined 2026-08-10** via NABO's own post-reform projection ([표 25] of the June-2025
reform analysis, `sources/nabo-pension-reform-analysis-2025.pdf`): published knots
interpolated annually, contribution revenue as its own column so erosion applies to the
right base. NABO's post-reform depletion is **2065** (deficit transition 2047; pre-reform
2057 per Focus 92 — the reform bought eight years on NABO's own numbers).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import rates
from .country import KOREA
from .korea_cells import load_korea_cells
from .korea_tax import korea_income_tax

# ------------------------------------------------------------------ published fund paths (₩tn)
# NHI: NABO Focus 162 (2026-06-09), sources/nabo-focus-162-nhi-reestimate-2026-2035.pdf.
# Revenue is common to both variants (the reform changes expenditure); reserves are the
# published 누적 준비금 series, which chain from the published balances to ≤0.1 rounding.
# EI: NABO mid-term projection, 「2026 대한민국 사회보험」 [표 151] — whole-fund baseline whose
# reserve path embeds planned PCMF borrowing (steps exceed operating balances; that is why the
# projector shifts published reserves instead of re-accumulating).


@dataclass(frozen=True)
class FundPath:
    name: str
    base_year: int
    revenue: tuple               # published annual revenue, ₩tn
    reserves: tuple              # published year-end cumulative reserves, ₩tn
    source: str

    def __post_init__(self):
        assert len(self.revenue) == len(self.reserves) > 0, self.name

    @property
    def years(self) -> tuple:
        return tuple(self.base_year + t for t in range(len(self.revenue)))


NHI_REVENUE = (107.6, 113.0, 118.7, 126.2, 133.8, 141.7, 149.5, 155.1, 160.7, 166.4)

NHI_BASELINE = FundPath(
    "NHI (natural trend, pre-reform-investment)", 2026, NHI_REVENUE,
    (29.8, 26.8, 21.1, 14.7, 6.9, -4.2, -19.5, -42.2, -70.8, -108.3),
    "NABO Focus 162, 의료개혁 반영 전")

NHI_REFORM = FundPath(
    "NHI (with medical-reform investment)", 2026, NHI_REVENUE,
    (25.0, 17.0, 7.6, -1.1, -10.9, -24.0, -41.3, -66.0, -96.6, -136.1),
    "NABO Focus 162, 의료개혁 반영 후")

EI_BASELINE = FundPath(
    "Employment Insurance (whole fund, incl. planned PCMF borrowing)", 2026,
    (21.6, 22.6, 23.6, 24.7),
    (10.9, 14.4, 18.0, 21.8),
    "NABO 2025~2029 mid-term projection via 「2026 대한민국 사회보험」 [표 151]")


def shifted_reserves(fund: FundPath, erosion, wage_linked_share: float = 1.0,
                     extra_outlays_tn=None) -> np.ndarray:
    """The published reserve path under a contribution-erosion path.

    `erosion[t]` is the fraction of the fund's wage-linked contribution base gone in year
    (base_year + t) relative to the no-AI counterfactual — the model's output.
    `wage_linked_share` is the share of published revenue that scales with that base
    (contributions from wage employees vs subsidies, investment income, other subscribers)."""
    e = np.asarray(erosion, dtype=float)
    assert e.ndim == 1 and 0 < len(e) <= len(fund.revenue), \
        f"erosion path empty or longer than {fund.name}'s published horizon ({len(fund.revenue)})"
    assert np.isfinite(e).all() and (e >= 0.0).all() and (e <= 1.0).all()
    assert 0.0 <= wage_linked_share <= 1.0
    n = len(e)
    lost = np.asarray(fund.revenue[:n]) * wage_linked_share * e
    if extra_outlays_tn is not None:
        x = np.asarray(extra_outlays_tn, dtype=float)[:n]
        assert x.shape == (n,) and (x >= 0.0).all()
        lost = lost + x                      # the OUTLAY side (e.g. EI benefit spending)
    return np.asarray(fund.reserves[:n]) - np.cumsum(lost)


def first_negative_year(reserves, base_year: int):
    """The calendar year whose year-end reserve first goes negative — NABO's own phrasing
    ("depleted in 2031"). None if the path never crosses within the horizon."""
    r = np.asarray(reserves, dtype=float)
    idx = np.where(r < 0.0)[0]
    return int(base_year + idx[0]) if idx.size else None


def depletion_date(reserves, base_year: int):
    """Fractional crossing date in calendar-decimal terms: the year-end reserve of calendar
    year Y sits at coordinate Y+1.0 (1 January of Y+1), so a crossing between the Y−1 and Y
    year-ends happens DURING calendar year Y and floor(date) equals `first_negative_year` —
    NABO's own phrasing. Linear interpolation between year-ends; None if no crossing."""
    r = np.asarray(reserves, dtype=float)
    if r[0] < 0.0:
        return float(base_year)                          # already negative at the first year-end
    for t in range(1, len(r)):
        if r[t] < 0.0:
            return base_year + t + r[t - 1] / (r[t - 1] - r[t])
    return None


def depletion_shift(fund: FundPath, erosion, wage_linked_share: float,
                    extra_outlays_tn=None) -> dict:
    """The headline object: how far erosion pulls the fund's depletion forward.

    `wage_linked_share` is deliberately required — the share of published revenue that
    scales with the wage-employee contribution base is a per-fund calibration decision, not
    a default. The erosion path must cover the fund's full published horizon so the base and
    eroded dates are compared over the same window. For a fund whose published path never
    crosses (EI), `years_pulled_forward` is None even when erosion CREATES a crossing —
    check `eroded_date` for that case."""
    assert len(np.asarray(erosion)) == len(fund.revenue), \
        f"depletion_shift needs a full-horizon erosion path ({len(fund.revenue)} years)"
    base = depletion_date(fund.reserves, fund.base_year)
    eroded_path = shifted_reserves(fund, erosion, wage_linked_share, extra_outlays_tn)
    eroded = depletion_date(eroded_path, fund.base_year)
    return {
        "fund": fund.name,
        "published_depletion": first_negative_year(fund.reserves, fund.base_year),
        "base_date": base,
        "eroded_date": eroded,
        "years_pulled_forward": (base - eroded) if (base and eroded) else None,
        "eroded_reserves": eroded_path,
    }


# ------------------------------------------------------------------ institution routing
_COMPONENTS = rates.korea_payroll_components()
_ENGINE = rates.PayrollFICA(components=_COMPONENTS)


def contribution_losses(emp_loss: np.ndarray, cells=None) -> dict:
    """Annual revenue losses (₩) by receiving institution for per-cell employment losses.

    `emp_loss` aligns with the 209-row cell table (persons). Returns each scheme priced by
    its own component arithmetic — the pension's cap is what routes high-wage damage away
    from the funds — plus the income-tax loss, its 10% local surtax, and the statutory
    40.03% local-transfer passthrough of the national income-tax loss."""
    c = cells if cells is not None else load_korea_cells("2025").cells
    loss = np.asarray(emp_loss, dtype=float)
    assert loss.shape == (len(c),), (loss.shape, len(c))
    assert (loss >= 0.0).all() and (loss <= c["emp"].to_numpy() + 1e-9).all()
    w = c["wage_year_won"].to_numpy()

    out = {comp.name: float(comp.levy(w, "Single", comp.rate) @ loss)
           for comp in _COMPONENTS}
    tax = korea_income_tax(w, _ENGINE.employee_fica(w, "Single"))
    out["income tax (national)"] = float(tax["national"] @ loss)
    out["local income surtax"] = float(tax["local"] @ loss)
    # memo item, NOT additive: the statutory local-transfer slice OF the national loss
    # above. Summing the non-memo entries partitions the total loss; including this
    # would double-count 40.03% of the income-tax line.
    out["memo: local share of national tax (40.03%)"] = (
        KOREA.subnational_transfer_share * out["income tax (national)"])
    return out


def erosion_fractions(emp_loss: np.ndarray, cells=None) -> dict:
    """Scheme losses as fractions of their own cell-table baselines — the projector's
    erosion input, and the composition result in one dict: which institution's base erodes
    fastest under a given displacement pattern."""
    c = cells if cells is not None else load_korea_cells("2025").cells
    baseline = contribution_losses(c["emp"].to_numpy(), cells=c)
    losses = contribution_losses(emp_loss, cells=c)
    return {k: losses[k] / baseline[k] for k in losses}


# ------------------------------------------------------------- NPS (post-reform), NABO 표 25
# NABO 현안보고서 「2025년 국민연금법 개정의 재정 및 정책효과 분석」 (2025-06), [표 25]:
# the post-reform projection (contribution rate 13% + replacement 43% + credit expansion).
# Stated in the text above the table: deficit transition 2047, FUND DEPLETION 2065 — NABO's
# own post-reform date (the ministry-attributed "~2064" in press coverage is a different
# estimate; quote NABO's 2065 now that the primary is in hand). Pre-reform NABO: 2057
# (Focus 92) — the reform bought eight years on NABO's own numbers.
# Columns kept: 보험료 (contribution revenue — erosion applies to THIS, not total revenue,
# which is investment-income-heavy pre-depletion) and 적립금 경상 (nominal reserves).
# Units ₩tn. Published at knot years; interpolated annually below, disclosed.
NPS_REFORM_KNOTS = {
    #      contributions  reserves(nominal)
    2025: (62.5, 1_285.3),
    2030: (88.2, 1_715.6),
    2040: (109.9, 2_653.7),
    2047: (111.6, 2_895.8),
    2050: (112.2, 2_830.5),
    2060: (108.5, 1_495.3),
    2065: (109.3, -133.8),
}


def _interp_annual(knots: dict, col: int, base_year: int, end_year: int) -> tuple:
    years = sorted(knots)
    out = []
    for y in range(base_year, end_year + 1):
        lo = max(k for k in years if k <= y)
        hi = min(k for k in years if k >= y)
        if lo == hi:
            out.append(knots[lo][col])
        else:
            f = (y - lo) / (hi - lo)
            out.append(knots[lo][col] + f * (knots[hi][col] - knots[lo][col]))
    return tuple(round(v, 2) for v in out)


NPS_REFORM = FundPath(
    "NPS (post-2025-reform: 13% rate, 43% replacement, credits)", 2026,
    _interp_annual(NPS_REFORM_KNOTS, 0, 2026, 2065),
    _interp_annual(NPS_REFORM_KNOTS, 1, 2026, 2065),
    "NABO 현안보고서 2025-06, [표 25] (sources/nabo-pension-reform-analysis-2025.pdf), "
    "annual by linear interpolation between the published knots")
