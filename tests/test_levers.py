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


def test_robot_exposure_loads(data):
    r = levers.load_robot_exposure()
    assert len(r) == 832 and r.between(0.0, 1.0).all()


def test_physical_channel_raises_high_robot_not_low_robot(data):
    # v2: the robotics channel acts on Webb robot exposure, NOT the complement of cognitive.
    robot = levers.load_robot_exposure()
    base = LeverParams(cognitive_feasibility=0.6, physical_feasibility=0.0)
    robo = LeverParams(cognitive_feasibility=0.6, physical_feasibility=0.8)
    fb = levers.displacement_fraction(data.exposure_occ, base)
    fr = levers.displacement_fraction(data.exposure_occ, robo)
    gain = (fr - fb)
    high_robot = [s for s in robot.nlargest(20).index if s in gain.index]
    low_robot = [s for s in robot.nsmallest(20).index if s in gain.index]
    # high-robot jobs gain materially from robotics; low-robot manual jobs barely move
    assert gain[high_robot].mean() > 0.15
    assert gain[low_robot].mean() < 0.05
    assert gain[high_robot].mean() > 3 * gain[low_robot].mean()


def test_low_robot_jobs_stay_low_under_full_robotics(data):
    # barbers/surgeons etc. (low robot exposure) are not automated even at physical_feasibility=1
    robot = levers.load_robot_exposure()
    p = LeverParams(cognitive_feasibility=0.0, physical_feasibility=1.0)  # isolate the robot channel
    f = levers.displacement_fraction(data.exposure_occ, p)
    low_robot = [s for s in robot.nsmallest(15).index if s in f.index]
    assert (f[low_robot] < 0.30).all()


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
