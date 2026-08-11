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


# ------------------------------------------------------------- extensive correctness additions
def test_preset_paths_ramp_to_2035_then_hold():
    """REGRESSION for the bug this suite caught: without adoption_reach_year the 40-year run
    silently became a 40-year ramp to 2065. The documented semantics — end value reached at
    period 9 (calendar 2035), flat after — must hold at every horizon."""
    from fiscal_model.korea_scenarios import KOREA_BAND_KEYS, KOREA_PRESETS
    from fiscal_model.presets import build_adoption_path
    for k in KOREA_BAND_KEYS:
        p = KOREA_PRESETS[k]
        for n in (10, 25, 40):
            a = build_adoption_path(p, n)
            assert len(a) == n
            assert a[0] == pytest.approx(p.adoption_start)
            assert a[9] == pytest.approx(p.adoption_end)
            assert all(v == pytest.approx(p.adoption_end) for v in a[9:])
            assert all(b >= x for x, b in zip(a, a[1:]))


def test_every_preset_reaches_then_holds_at_any_horizon():
    """The same regression, generalized: EVERY Korea preset must carry a reach year, and the
    end value must hold flat past it at every horizon (the 40-year NPS run is the hazard)."""
    from fiscal_model.korea_scenarios import KOREA_PRESETS
    from fiscal_model.presets import build_adoption_path
    for p in KOREA_PRESETS.values():
        r = p.adoption_reach_year
        assert r is not None, f"{p.key}: missing adoption_reach_year (silent horizon-stretch)"
        a = build_adoption_path(p, 40)
        assert a[r] == pytest.approx(p.adoption_end)
        assert all(v == pytest.approx(p.adoption_end) for v in a[r:])


def test_agi_presets_translate_cleanly():
    """The Korinek-Suh translations: every override is a real V2Params field, the three
    US-only fields are NOT ported (no state closure / no US GRT rate / robotics inert), and
    physical_feasibility is pinned at 0.0 — Korea has no robot-exposure vector wired, so the
    physical channel maps to zero. Wiring one later must consciously revisit these presets."""
    import dataclasses

    from fiscal_model.korea_scenarios import KOREA_BAND_KEYS, KOREA_PRESETS
    from fiscal_model.levers_v2 import V2Params
    fields = {f.name for f in dataclasses.fields(V2Params)}
    agi_keys = set(KOREA_PRESETS) - set(KOREA_BAND_KEYS)
    assert agi_keys == {"korea-agi-20y", "korea-agi-5y"}
    for k in agi_keys:
        p = KOREA_PRESETS[k]
        assert set(p.overrides) <= fields, f"{k}: unknown V2Params field"
        assert not set(p.overrides) & {"state_cut_share", "state_rate_hike_cap",
                                       "compute_effective_rate", "robotics_lag"}, \
            f"{k}: US-only override ported by mistake"
        assert p.overrides["physical_feasibility"] == 0.0, \
            f"{k}: physical channel opened without a Korean robot-exposure vector"
        assert p.adoption_end == 1.0
        assert set(p.overrides) <= set(p.provenance), f"{k}: override without provenance"
    # the aggressive world reaches full automation at year 5 and holds
    from fiscal_model.presets import build_adoption_path
    a5 = build_adoption_path(KOREA_PRESETS["korea-agi-5y"], 40)
    assert a5[5] == 1.0 and all(v == 1.0 for v in a5[5:])
    a20 = build_adoption_path(KOREA_PRESETS["korea-agi-20y"], 40)
    assert a20[19] == 1.0 and all(v == 1.0 for v in a20[19:])


def test_erosion_paths_bounded_monotone_and_deterministic():
    adoption = [0.0, 0.05, 0.1, 0.2, 0.2]
    p1 = korea_erosion_paths(adoption, exposure=UNIFORM)
    p2 = korea_erosion_paths(adoption, exposure=UNIFORM)
    for k in p1:
        assert np.array_equal(p1[k], p2[k]), k
        assert (p1[k] >= 0.0).all() and (p1[k] <= 1.0).all()
        assert (np.diff(p1[k]) >= -1e-15).all()      # cumulative adoption → cumulative erosion


def test_erosion_is_linear_in_adoption():
    a1 = korea_erosion_paths([0.04], exposure=UNIFORM)
    a2 = korea_erosion_paths([0.08], exposure=UNIFORM)
    for k in a1:
        assert a2[k][0] == pytest.approx(2 * a1[k][0], rel=1e-12), k


def test_full_displacement_is_the_identity():
    every = {k: 1.0 for k in range(1, 10)}
    p = korea_erosion_paths([1.0], exposure=every)
    for k, v in p.items():
        assert v[0] == pytest.approx(1.0, rel=1e-12), k


def test_nhi_variant_switch_uses_the_baseline_path():
    from fiscal_model.korea_funds import NHI_BASELINE
    a = list(np.linspace(0.0, 0.2, 10))
    r = korea_fund_headlines(a, nhi_wage_linked_share=0.85, nhi_variant=NHI_BASELINE)
    assert r["nhi"]["published_depletion"] == 2031


def test_band_covers_all_axes():
    from fiscal_model.korea_scenarios import KOREA_BAND_KEYS, korea_headline_band
    band = korea_headline_band()
    # band presets × share edges × read error — the AGI presets are scenario rows, NOT band
    # edges (a full-automation world would swamp the calibrated diffusion range)
    assert len(band) == len(KOREA_BAND_KEYS) * 2 * 3
    assert not any("agi" in key for key in band)
    for key, v in band.items():
        assert v["nhi_years_forward"] > 0.0, key
        assert v["ei_reserve_2029_shortfall_tn"] > 0.0, key
