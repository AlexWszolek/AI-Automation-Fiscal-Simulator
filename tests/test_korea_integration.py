"""End-to-end regression pins for the Korea headline chain. These freeze the CURRENT sourced
results — if data, exposure, presets, or projector arithmetic change, these go red and the
recorded numbers in docs/KOREA_PRESET_EVIDENCE.md must be re-derived together with them."""
import numpy as np
import pytest

from fiscal_model.korea_cells import PAYM39_CSV
from fiscal_model.korea_scenarios import KOREA_PRESETS, korea_fund_headlines
from fiscal_model.presets import build_adoption_path

pytestmark = pytest.mark.skipif(
    not PAYM39_CSV.exists(),
    reason="Korea tidy CSV not built — scripts/fetch_korea_tables.py --parse-only")


def _run(preset_key, n, **kw):
    return korea_fund_headlines(build_adoption_path(KOREA_PRESETS[preset_key], n), **kw)


def test_pinned_nhi_central_headline():
    r = _run("korea-central", 10, nhi_wage_linked_share=0.85)
    assert r["nhi"]["years_pulled_forward"] == pytest.approx(0.544, abs=0.01)
    assert r["nhi"]["published_depletion"] == 2029
    assert int(r["nhi"]["base_date"]) == 2029


def test_pinned_nhi_band_endpoints():
    lo = _run("korea-slow", 10, nhi_wage_linked_share=0.65)
    hi = _run("korea-fast", 10, nhi_wage_linked_share=0.97)
    assert lo["nhi"]["years_pulled_forward"] == pytest.approx(0.25, abs=0.02)
    assert hi["nhi"]["years_pulled_forward"] == pytest.approx(0.93, abs=0.02)


def test_pinned_ei_central_shortfall():
    r = _run("korea-central", 10, nhi_wage_linked_share=0.85)
    shortfall = 21.8 - r["ei"]["eroded_reserves"][-1]
    assert shortfall == pytest.approx(1.5, abs=0.1)
    assert r["ei"]["years_pulled_forward"] is None          # never crosses on paper


def test_pinned_nps_pension_headline_corrected_semantics():
    """The corrected pension answer (ramp to 2035 then flat): central preset gives back
    0.67–0.84 of the reform's eight bought years across the NPS share band."""
    lo = _run("korea-central", 40, nhi_wage_linked_share=0.85, nps_wage_linked_share=0.75)
    hi = _run("korea-central", 40, nhi_wage_linked_share=0.85, nps_wage_linked_share=0.95)
    assert lo["nps"]["years_pulled_forward"] == pytest.approx(0.67, abs=0.03)
    assert hi["nps"]["years_pulled_forward"] == pytest.approx(0.84, abs=0.03)
    assert lo["nps"]["published_depletion"] == 2065
    fast = _run("korea-fast", 40, nhi_wage_linked_share=0.85, nps_wage_linked_share=0.95)
    assert fast["nps"]["years_pulled_forward"] == pytest.approx(1.64, abs=0.05)


def test_headlines_are_exactly_reproducible():
    a = _run("korea-central", 40, nhi_wage_linked_share=0.85, nps_wage_linked_share=0.85)
    b = _run("korea-central", 40, nhi_wage_linked_share=0.85, nps_wage_linked_share=0.85)
    for fund in ("nhi", "ei", "nps"):
        assert a[fund]["eroded_date"] == b[fund]["eroded_date"]
        assert np.array_equal(a[fund]["eroded_reserves"], b[fund]["eroded_reserves"])


def test_more_adoption_always_hurts_every_fund():
    rs = [_run(k, 40, nhi_wage_linked_share=0.85, nps_wage_linked_share=0.85)
          for k in ("korea-slow", "korea-central", "korea-fast")]
    for a, b in zip(rs, rs[1:]):
        assert b["nhi"]["eroded_date"] < a["nhi"]["eroded_date"]
        assert b["nps"]["eroded_date"] < a["nps"]["eroded_date"]
        assert b["ei"]["eroded_reserves"][-1] < a["ei"]["eroded_reserves"][-1]


def test_payroll_marginal_rates_across_the_pension_cap():
    """Per-won marginal payroll rate: 20.9048% below the cap, 11.4048% above it (flat schemes
    only) — the mechanism behind the institutional routing, checked at the boundary."""
    from fiscal_model import rates
    engine = rates.PayrollFICA(components=rates.korea_payroll_components())
    cap = 79_080_000.0
    w = np.array([cap - 1.0, cap, cap + 1.0, cap + 2.0])
    f = engine.fica(w, "Single")
    assert f[1] - f[0] == pytest.approx(0.209048, abs=1e-6)
    assert f[3] - f[2] == pytest.approx(0.209048 - 0.095, abs=1e-6)
