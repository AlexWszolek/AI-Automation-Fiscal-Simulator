"""Levers — the exposure -> feasibility -> adoption transform (briefing §2.2), v2.

Turns the fixed occupation exposure scores into a per-occupation **displacement fraction**
through three independent, composable, user-settable layers. v2 replaces the old physical
proxy (1 - cognitive_exposure) with an INDEPENDENT robot-exposure measure (Webb 2020,
data/raw/robot_exposure_by_soc.xlsx) and combines the two channels multiplicatively.

  1. Exposure (fixed ground truth), two independent measures:
       - cognitive: the Yale AI PCA score, mapped monotonically to a [0,1] share (percentile
         rank by default, or a user-shaped logistic). The PCA score is NOT a fraction
         (~ -3.4..+7.1), so it must pass through such a mapping.
       - robot: Webb's robot-patent exposure percentile (pct_robot/100 -> [0,1]). An
         INDEPENDENT physical-automatability measure -- NOT the complement of cognitive.
         (corr(robot, cognitive) ~ -0.78, but the per-occupation differences are the point:
         dancers/barbers/surgeons score low on robot AND low on cognitive.)
  2. Feasibility (time-varying, two channels in [0,1]):
       - cognitive_feasibility ramps the cognitive channel;
       - physical_feasibility ramps the robot channel (post-AGI mechatronics).
  3. Adoption (time-varying): how much of what's feasible actually gets deployed.

Combination (independent channels -- a job is automated if EITHER channel can do its tasks):

  displacement(o) = adoption * [ 1 - (1 - cog(o)*cognitive_feasibility)
                                   * (1 - robot(o)*physical_feasibility) ]

so at physical_feasibility = 0 only cognitive work is displaced; as robotics ramps, the jobs
robot patents actually target follow. Naturally bounded in [0,1]; no zero-sum split between
channels. Every parameter is a lever.

NOTE (robotics-maturity ceiling -- future extension): pct_robot reflects the CURRENT robot-patent
stock (industrial/material-handling), so it is a current-technology ANCHOR, not the post-AGI
dexterity ceiling -- even physical_feasibility=1 leaves barbers/surgeons near zero. The intended
refinement interpolates robot exposure between pct_robot (now) and a physical-task-content measure
(DOT/O*NET manual-task scores) under a `robotics_maturity` lever. Until that data is wired,
`robotics_maturity` is inert and `physical_feasibility` scales pct_robot directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from . import loaders

ROBOT_XLSX = Path(__file__).resolve().parent.parent / "data" / "raw" / "robot_exposure_by_soc.xlsx"


@dataclass
class LeverParams:
    # cognitive exposure -> [0,1] task-exposure share (Yale PCA)
    exposure_mapping: str = "percentile"     # 'percentile' | 'logistic'
    logistic_midpoint: float = 0.0           # PCA-score midpoint (logistic only)
    logistic_steepness: float = 0.6          # per PCA-score unit (logistic only)
    # feasibility (two independent channels, time-varying knobs in [0,1])
    cognitive_feasibility: float = 0.5
    physical_feasibility: float = 0.0        # robotics; default 0 = pre-AGI-robotics
    # adoption in [0,1]
    adoption: float = 1.0
    # robotics-maturity ceiling lever (0 = current robot patents only; 1 = physical-task ceiling).
    # Inert until a physical-task-content measure is supplied; documented hook for the extension.
    robotics_maturity: float = 0.0


def cognitive_exposure(pca_scores: np.ndarray, params: LeverParams) -> np.ndarray:
    """Monotonic map from the Yale PCA exposure score to a [0,1] cognitive task-exposure share."""
    pca = np.asarray(pca_scores, dtype=float)
    if params.exposure_mapping == "logistic":
        return 1.0 / (1.0 + np.exp(-params.logistic_steepness * (pca - params.logistic_midpoint)))
    order = pca.argsort()
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(len(pca))
    return ranks / (len(pca) - 1) if len(pca) > 1 else np.zeros_like(pca)


def load_robot_exposure(path: Path = ROBOT_XLSX) -> pd.Series:
    """soc_code -> robot exposure in [0,1] (pct_robot/100). Empty Series if the file is absent
    (the physical channel then contributes 0 until the data is provided)."""
    p = Path(path)
    if not p.exists():
        return pd.Series(dtype=float, name="robot_exposure")
    df = pd.read_excel(p, sheet_name="Robot exposure by SOC", dtype={"SOC code": str})
    soc_col = "SOC code" if "SOC code" in df.columns else "soc_code"
    s = (df.set_index(soc_col)["pct_robot"].astype(float) / 100.0).clip(0.0, 1.0)
    s.index = s.index.astype(str).str.strip()
    s.name = "robot_exposure"
    return s[~s.index.duplicated()]


def channel_shares(exposure_occ: pd.DataFrame, params: LeverParams,
                   robot_exposure: Optional[pd.Series] = None) -> tuple:
    """The two per-occupation exposure channels as Series indexed by soc_code:
    (cognitive share in [0,1], robot share in [0,1]). The seam the robotics-lag lever needs — a
    time-varying ramp on the PHYSICAL channel requires recombining the channels per period."""
    df = exposure_occ.dropna(subset=["ai_pca_score"])
    cog = cognitive_exposure(df["ai_pca_score"].to_numpy(), params)
    if robot_exposure is None:
        robot_exposure = load_robot_exposure()
    robot = df["soc_code"].map(robot_exposure).fillna(0.0).to_numpy()
    idx = df["soc_code"].values
    return (pd.Series(cog, index=idx, name="cognitive_share"),
            pd.Series(robot, index=idx, name="robot_share"))


def combine_channels(cog: np.ndarray, robot: np.ndarray, cognitive_feasibility: float,
                     physical_feasibility: float) -> np.ndarray:
    """Independent-channels combination (a job is automated if EITHER channel can do its tasks).
    The single source of the float-op order — `displacement_fraction` and the per-period
    robotics-lag path must produce BIT-IDENTICAL results at ramp=1."""
    surv_cog = 1.0 - cog * cognitive_feasibility
    surv_rob = 1.0 - robot * physical_feasibility
    return 1.0 - surv_cog * surv_rob                       # P(automated) = 1 - P(neither channel)


def displacement_fraction(exposure_occ: pd.DataFrame, params: LeverParams,
                          robot_exposure: Optional[pd.Series] = None) -> pd.Series:
    """Per-occupation displacement fraction in [0,1], indexed by soc_code.

    Independent-channels form: a job is automated if the cognitive OR the robot channel can do
    its tasks. `robot_exposure` (soc_code -> [0,1]); loaded from ROBOT_XLSX if None. Missing
    robot scores default to 0 (the physical channel simply doesn't act on those occupations).
    """
    cog_s, robot_s = channel_shares(exposure_occ, params, robot_exposure)
    auto = combine_channels(cog_s.to_numpy(), robot_s.to_numpy(),
                            params.cognitive_feasibility, params.physical_feasibility)
    frac = params.adoption * np.clip(auto, 0.0, 1.0)
    return pd.Series(frac, index=cog_s.index, name="displacement_fraction")


def displacement_flows(data: loaders.FiscalData, params: LeverParams,
                       employed: pd.Series | None = None,
                       robot_exposure: Optional[pd.Series] = None) -> pd.DataFrame:
    """Per-occupation displacement this period: fraction x current employment.

    `employed` (soc_code -> persons); defaults to occupation totals (exposure Employees x1000).
    Military (no PCA score) gets 0.
    """
    frac = displacement_fraction(data.exposure_occ, params, robot_exposure)
    if employed is None:
        employed = (data.exposure_occ.set_index("soc_code")["emp_thousands"] * 1_000.0)
    out = pd.DataFrame({"displacement_fraction": frac}).join(employed.rename("employed"), how="left")
    out["employed"] = out["employed"].fillna(0.0)
    out["displaced"] = out["displacement_fraction"] * out["employed"]
    out.index.name = "soc_code"
    return out.reset_index()


if __name__ == "__main__":
    data = loaders.load_all()
    robot = load_robot_exposure()
    print(f"robot exposure loaded for {len(robot)} SOC codes "
          f"({'OK' if len(robot) else 'MISSING -- physical channel inert'})\n")

    scenarios = {
        "cognitive only (cog_feas=0.6, phys_feas=0, adopt=0.7)":
            LeverParams(cognitive_feasibility=0.6, physical_feasibility=0.0, adoption=0.7),
        "post-AGI robotics (cog_feas=0.9, phys_feas=0.7, adopt=0.8)":
            LeverParams(cognitive_feasibility=0.9, physical_feasibility=0.7, adoption=0.8),
    }
    exp = data.exposure_occ
    for name, p in scenarios.items():
        flows = displacement_flows(data, p, robot_exposure=robot)
        tot_disp, tot_emp = flows["displaced"].sum(), flows["employed"].sum()
        print(f"{name}\n   economy-wide displaced: {tot_disp/1e6:.1f}M of {tot_emp/1e6:.1f}M "
              f"({tot_disp/tot_emp:.1%})")
        m = flows.merge(exp[["soc_code", "occupation_title", "ai_pca_score"]], on="soc_code")
        m["robot"] = m["soc_code"].map(robot)
        top = m.nlargest(4, "displacement_fraction")
        print("   most displaced:", [f"{r.occupation_title[:30]} {r.displacement_fraction:.2f}"
                                      for r in top.itertuples()], "\n")
