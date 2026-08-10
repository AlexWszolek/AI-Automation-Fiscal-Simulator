"""The scenario scaffolding: the exposure seam must refuse to run unsourced, the pipeline
must be homogeneous where it should be, and the composition asymmetry must survive the whole
chain from exposure vector to fund shift."""
import numpy as np
import pytest

from fiscal_model.korea_cells import PAYM39_CSV
from fiscal_model.korea_scenarios import (
    WAGE_LINKED_SHARE, korea_erosion_paths, korea_fund_headlines, require_exposure)

pytestmark = pytest.mark.skipif(
    not PAYM39_CSV.exists(),
    reason="Korea tidy CSV not built — scripts/fetch_korea_tables.py --parse-only")

UNIFORM = {k: 0.30 for k in range(1, 10)}


def test_exposure_seam_default_is_the_published_vector(monkeypatch):
    """The seam now defaults to the BOK-published HELC vector — and still refuses to run if
    the wired vector were absent (the discipline survives the wiring)."""
    from fiscal_model import korea_exposure, korea_scenarios
    assert require_exposure(None) == korea_exposure.EXPOSURE_HELC
    monkeypatch.setattr(korea_scenarios, "EXPOSURE_BY_OCC", None)
    with pytest.raises(RuntimeError, match="korea-primary-docs-request"):
        require_exposure(None)
    with pytest.raises(AssertionError, match="KSCO majors"):
        require_exposure({1: 0.5})
    with pytest.raises(AssertionError):
        require_exposure({**UNIFORM, 3: 1.4})


def test_ei_share_is_pinned_to_its_published_components():
    """₩18.92tn contributions (표 146) of ₩20.35tn whole-fund revenue (표 149), FY2025."""
    ei = WAGE_LINKED_SHARE["ei"]
    assert ei.value == pytest.approx(189_177 / 203_485)
    assert ei.status == "verified"
    nhi = WAGE_LINKED_SHARE["nhi"]
    assert nhi.value is None and nhi.low == 0.65 and nhi.high == 0.97


def test_uniform_exposure_is_homogeneous_through_the_pipeline():
    """exposure e everywhere × adoption a → every institution erodes by exactly e·a."""
    adoption = [0.0, 0.1, 0.25, 0.5]
    paths = korea_erosion_paths(adoption, exposure=UNIFORM)
    for k, series in paths.items():
        assert series == pytest.approx([0.30 * a for a in adoption]), k


def test_composition_asymmetry_survives_the_whole_chain():
    """Managers/professionals-only exposure vs elementary-only: the income-tax base must
    erode hardest under the first and barely under the second, with the pension the mirror
    image — the institution-routing claim, end to end."""
    white_collar = {k: (0.6 if k in (1, 2) else 0.0) for k in range(1, 10)}
    elementary = {k: (0.6 if k == 9 else 0.0) for k in range(1, 10)}
    a = [0.5]
    wc = {k: v[0] for k, v in korea_erosion_paths(a, exposure=white_collar).items()}
    el = {k: v[0] for k, v in korea_erosion_paths(a, exposure=elementary).items()}
    assert wc["income tax (national)"] > wc["NHI health"] > wc["NPS pension"]
    assert el["NPS pension"] > el["NHI health"] > el["income tax (national)"]


def test_fund_headlines_compose_and_respect_the_band():
    adoption = list(np.linspace(0.0, 0.4, 10))
    out = korea_fund_headlines(adoption, nhi_wage_linked_share=0.85, exposure=UNIFORM)
    assert out["nhi"]["years_pulled_forward"] > 0
    assert out["nhi"]["published_depletion"] == 2029          # reform variant default
    assert out["ei"]["years_pulled_forward"] is None          # EI never crosses on paper
    assert (out["ei"]["eroded_reserves"] <= np.asarray(
        [10.9, 14.4, 18.0, 21.8]) + 1e-12).all()
    with pytest.raises(AssertionError, match="documented band"):
        korea_fund_headlines(adoption, nhi_wage_linked_share=0.5, exposure=UNIFORM)


def test_adoption_must_be_cumulative_and_long_enough():
    with pytest.raises(AssertionError, match="non-decreasing"):
        korea_erosion_paths([0.3, 0.2], exposure=UNIFORM)
    with pytest.raises(AssertionError, match="NHI horizon"):
        korea_fund_headlines([0.1] * 4, nhi_wage_linked_share=0.8, exposure=UNIFORM)
