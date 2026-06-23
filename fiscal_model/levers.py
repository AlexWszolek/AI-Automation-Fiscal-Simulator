"""Levers — the exposure → feasibility → adoption transform (briefing §2.2).

Turns the fixed Yale AI PCA exposure score into a per-occupation **displacement fraction**
(the share of an occupation automated this scenario), through three independent, composable,
user-settable layers:

  1. Exposure (fixed ground truth): the PCA score, mapped monotonically to a [0,1] task-
     exposure share (percentile rank by default, or a user-shaped logistic). The PCA score is
     NOT a fraction (≈ -3.4..+7.1), so it MUST be passed through such a mapping (briefing §3.2).
  2. Feasibility (time-varying, ≥2 channels): given exposure, what fraction AI can actually do.
     - cognitive channel: ramps with `cognitive_feasibility` for cognitively-exposed work;
     - physical channel: a separate robotics ramp (`physical_feasibility`) for physical jobs,
       which score LOW on Yale's cognitive exposure — this is where post-AGI mechatronics enters.
  3. Adoption (time-varying): given feasibility, how much actually gets deployed.

  displacement_fraction(o) = adoption x clip( cog(o)·cognitive_feasibility
                                            + (1 - cog(o))·physical_feasibility , 0, 1 )

so at physical_feasibility = 0 only cognitive work is displaced; as robotics ramps, physical
work follows. Every parameter is a lever — nothing is baked in.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import loaders


@dataclass
class LeverParams:
    # exposure -> [0,1] task-exposure share
    exposure_mapping: str = "percentile"     # 'percentile' | 'logistic'
    logistic_midpoint: float = 0.0           # PCA-score midpoint (logistic only)
    logistic_steepness: float = 0.6          # per PCA-score unit (logistic only)
    # feasibility (two channels, time-varying scenario knobs in [0,1])
    cognitive_feasibility: float = 0.5
    physical_feasibility: float = 0.0        # robotics; default 0 = pre-AGI-robotics
    # adoption in [0,1]
    adoption: float = 1.0


def cognitive_exposure(pca_scores: np.ndarray, params: LeverParams) -> np.ndarray:
    """Monotonic map from the PCA exposure score to a [0,1] cognitive task-exposure share."""
    pca = np.asarray(pca_scores, dtype=float)
    if params.exposure_mapping == "logistic":
        return 1.0 / (1.0 + np.exp(-params.logistic_steepness * (pca - params.logistic_midpoint)))
    # percentile rank (robust default): share of occupations at or below this score
    order = pca.argsort()
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(len(pca))
    return ranks / (len(pca) - 1) if len(pca) > 1 else np.zeros_like(pca)


def displacement_fraction(exposure_occ: pd.DataFrame, params: LeverParams) -> pd.Series:
    """Per-occupation displacement fraction in [0,1], indexed by soc_code."""
    df = exposure_occ.dropna(subset=["ai_pca_score"]).copy()
    cog = cognitive_exposure(df["ai_pca_score"].to_numpy(), params)
    frac = params.adoption * np.clip(
        cog * params.cognitive_feasibility + (1.0 - cog) * params.physical_feasibility, 0.0, 1.0)
    return pd.Series(frac, index=df["soc_code"].values, name="displacement_fraction")


def displacement_flows(data: loaders.FiscalData, params: LeverParams,
                       employed: pd.Series | None = None) -> pd.DataFrame:
    """Per-occupation displacement this period: fraction × current employment.

    `employed` (soc_code -> employed count, persons); defaults to occupation totals
    (exposure file Employees, in thousands -> persons). Returns soc_code, frac, employed,
    displaced (persons). Military (no PCA score) gets 0.
    """
    frac = displacement_fraction(data.exposure_occ, params)
    if employed is None:
        employed = (data.exposure_occ.set_index("soc_code")["emp_thousands"] * 1_000.0)
    out = pd.DataFrame({"displacement_fraction": frac}).join(employed.rename("employed"), how="left")
    out["employed"] = out["employed"].fillna(0.0)
    out["displaced"] = out["displacement_fraction"] * out["employed"]
    out.index.name = "soc_code"
    return out.reset_index()


if __name__ == "__main__":
    data = loaders.load_all()
    print("=== displacement fraction under three scenarios ===")
    scenarios = {
        "cognitive only (cog=0.6, phys=0, adopt=0.7)":
            LeverParams(cognitive_feasibility=0.6, physical_feasibility=0.0, adoption=0.7),
        "post-AGI robotics (cog=0.9, phys=0.7, adopt=0.8)":
            LeverParams(cognitive_feasibility=0.9, physical_feasibility=0.7, adoption=0.8),
    }
    exp = data.exposure_occ
    for name, p in scenarios.items():
        flows = displacement_flows(data, p)
        tot_disp = flows["displaced"].sum()
        tot_emp = flows["employed"].sum()
        print(f"\n{name}")
        print(f"   economy-wide displaced: {tot_disp/1e6:.1f}M of {tot_emp/1e6:.1f}M "
              f"({tot_disp/tot_emp:.1%})")
        # most/least displaced occupations
        m = flows.merge(exp[["soc_code", "occupation_title", "ai_pca_score"]], on="soc_code")
        top = m.nlargest(3, "displacement_fraction")[["occupation_title", "displacement_fraction"]]
        bot = m.nsmallest(3, "displacement_fraction")[["occupation_title", "displacement_fraction"]]
        print("   most exposed:", [f"{r.occupation_title[:32]} {r.displacement_fraction:.2f}" for r in top.itertuples()])
        print("   least exposed:", [f"{r.occupation_title[:32]} {r.displacement_fraction:.2f}" for r in bot.itertuples()])
