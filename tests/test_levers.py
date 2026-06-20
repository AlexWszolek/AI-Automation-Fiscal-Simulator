"""Tests for the exposure -> feasibility -> adoption displacement transform."""
import numpy as np

from fiscal_model import levers
from fiscal_model.levers import LeverParams


def test_fraction_in_unit_interval(data):
    f = levers.displacement_fraction(data.exposure_occ, LeverParams(cognitive_feasibility=0.8,
                                                                    physical_feasibility=0.3))
    assert f.between(0, 1).all()


def test_cognitive_monotone_in_pca(data):
    # percentile mapping + phys < cog -> displacement rises with PCA score
    p = LeverParams(cognitive_feasibility=0.7, physical_feasibility=0.0, adoption=1.0)
    f = levers.displacement_fraction(data.exposure_occ, p)
    merged = data.exposure_occ.set_index("soc_code").join(f)
    hi = merged.nlargest(20, "ai_pca_score")["displacement_fraction"].mean()
    lo = merged.nsmallest(20, "ai_pca_score")["displacement_fraction"].mean()
    assert hi > lo


def test_physical_channel_raises_low_exposure(data):
    base = LeverParams(cognitive_feasibility=0.6, physical_feasibility=0.0)
    robo = LeverParams(cognitive_feasibility=0.6, physical_feasibility=0.6)
    fb = levers.displacement_fraction(data.exposure_occ, base)
    fr = levers.displacement_fraction(data.exposure_occ, robo)
    # the least cognitively-exposed occupations gain the most from the robotics channel
    low = data.exposure_occ.nsmallest(20, "ai_pca_score")["soc_code"]
    assert (fr[low] > fb[low] + 0.1).all()


def test_adoption_scales_linearly(data):
    half = levers.displacement_fraction(data.exposure_occ, LeverParams(adoption=0.5,
                                        cognitive_feasibility=0.8, physical_feasibility=0.2))
    full = levers.displacement_fraction(data.exposure_occ, LeverParams(adoption=1.0,
                                        cognitive_feasibility=0.8, physical_feasibility=0.2))
    assert np.allclose(half.to_numpy(), 0.5 * full.to_numpy())


def test_flows_consistent(data):
    flows = levers.displacement_flows(data, LeverParams(cognitive_feasibility=0.5))
    assert np.allclose(flows["displaced"], flows["displacement_fraction"] * flows["employed"])
    assert flows["displaced"].sum() > 0
