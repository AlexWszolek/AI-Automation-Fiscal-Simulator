"""The Korea V2 assembly — Korean data in the shapes the engine actually consumes.

The engine's working interface (contract inventory in the artifacts plan worksheet) is the
per-worker deltas table plus a handful of `data.*` fields — not all of FiscalData. This
module builds both from the Korean modules that already exist and are test-pinned:
`korea_cells` (209 occupation × wage-bracket cells), `korea_tax`, the Korean payroll
components, `korea_transfers`, and the ILOSTAT occupation × industry joint matrix.

Simplifications the Korean integrate makes EXACTLY (not approximately):
- cells ARE wage brackets → one evaluation per cell (the US integrates over within-cell
  wage percentiles × filing statuses × household archetypes; Korea taxes individuals and
  the bracket midpoint world is already the cell definition, disclosed);
- 구직급여 is tax-exempt (비과세) → the during-phase income-tax loss is the full tax on the
  wage, and EI benefits are not 근로소득, so the EITC is lost in BOTH phases;
- payroll contributions stop entirely in both phases (benefits are not wage).

Ledger mapping, single-region: state = "KR" = the LOCAL-government ledger. National income
tax → inc_fed; the 10% local surtax → inc_state; all five social-insurance schemes →
payroll_fed; VAT → the consumption channel (national — see the channel note below); EITC
delta → transfer_fed (negative: a lost in-work credit REDUCES outlays, as with the US EITC).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import rates
from .korea_cells import load_korea_cells
from .korea_exposure import EXPOSURE_HELC
from .korea_tax import korea_income_tax
from .korea_transfers import ei_daily_benefit, kr_eitc_delta_on_displacement

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "korea"

# ISCO-08 majors ↔ KSCO 6th majors: 1:1 except ISCO 5 (service AND sales) covering KSCO 4+5.
# The ILOSTAT joint matrix is ISCO-side; occupation rows are split to KSCO 4/5 by the two
# groups' national employment weights (from the cell table) — disclosed approximation.
_ISCO_TO_KSCO = {"1": (1,), "2": (2,), "3": (3,), "4": (3,), "5": (4, 5), "6": (6,),
                 "7": (7,), "8": (8,), "9": (9,)}
# note: ISCO 3 (technicians) has no clean KSCO major twin — KSCO folds technicians into
# 전문가(2); ILOSTAT's Korean submission reports ISCO 3 ≈ 0 or folds it too (verify at
# build time; the builder asserts and reroutes if the submission carries mass there).


def load_joint_matrix(year: str = "2024") -> pd.DataFrame:
    """ILOSTAT ISIC-section × ISCO-major employment (thousands) → long frame with KSCO
    occupation codes. Shares only — the LFS frame difference is disclosed at the seam."""
    path = RAW / "ilostat_eco_ocu.csv"
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r["time"] != year or not r["obs_value"]
                    or r["classif1"] == "ECO_ISIC4_TOTAL"
                    or r["classif2"] in ("OCU_ISCO08_TOTAL", "OCU_ISCO08_X")):
                continue
            sec = r["classif1"].replace("ECO_ISIC4_", "")
            isco = r["classif2"].replace("OCU_ISCO08_", "")
            if len(sec) != 1 or isco not in _ISCO_TO_KSCO:
                continue
            rows.append({"section": sec, "isco": isco, "emp_k": float(r["obs_value"])})
    df = pd.DataFrame(rows)
    assert len(df) > 100 and df["emp_k"].sum() > 20_000, "joint matrix looks truncated"
    return df


@dataclass
class KoreaFiscalData:
    """The minimal FiscalData surface the engine touches, Korean-shaped. Carries a country
    tag so the (few) US-pinned code paths can branch without touching US behaviour."""
    country: str
    oews: pd.DataFrame
    exposure_occ: pd.DataFrame
    matrices_sector: pd.DataFrame
    consumption: pd.DataFrame
    receipts: pd.DataFrame = field(default_factory=pd.DataFrame)
    base_linkage: pd.DataFrame = field(default_factory=pd.DataFrame)


_ENGINE = rates.PayrollFICA(components=rates.korea_payroll_components())

# Korean corporate parameters for the offset channel (per-worker corporate tax recovered on
# the retained share of the saved wage). Effective rate: statutory 24.2% incl. local surtax
# at the ₩20–300bn bracket — the blended large-firm band where automation-scale savings
# land; recorded in KOREA_PRESET_EVIDENCE as a calibration row.
KR_CORP_EFF_RATE = 0.242


def build_cells_frames(year: str = "2025") -> tuple:
    """The cell table in engine shapes: (oews, exposure_occ, matrices_sector)."""
    kc = load_korea_cells(year)
    c = kc.cells.copy()
    c["soc_code"] = [f"{o}:{int(lo):04d}" for o, lo in zip(c["occ_code"], c["bracket_lo_k"])]

    oews = pd.DataFrame({
        "soc_code": c["soc_code"], "state": "KR",
        "employment_persons": c["emp"], "annual_mean_wage": c["wage_year_won"],
    })

    # cognitive channel: the BOK HELC displacement-prone share, already a [0,1] share —
    # carried in a `cognitive_share` column the channel seam consumes directly (the US
    # ai_pca_score → transform path stays untouched)
    exposure_occ = pd.DataFrame({
        "soc_code": c["soc_code"],
        "ai_pca_score": np.nan,
        "cognitive_share": c["occ_code"].map(EXPOSURE_HELC).astype(float),
    })

    # occupation × industry: ILOSTAT shares allocate each cell's employment/comp over
    # ISIC sections; comp = wage bill (₩m units, emp in thousands — only the per-worker
    # RATIO is consumed by the engine)
    jm = load_joint_matrix()
    ksco_rows = []
    w45 = c.groupby("occ_code")["emp"].sum()
    for r in jm.itertuples():
        targets = _ISCO_TO_KSCO[r.isco]
        if len(targets) == 1:
            ksco_rows.append({"section": r.section, "occ_code": targets[0], "emp_k": r.emp_k})
        else:
            tot = sum(w45[t] for t in targets)
            for t in targets:
                ksco_rows.append({"section": r.section, "occ_code": t,
                                  "emp_k": r.emp_k * w45[t] / tot})
    shares = (pd.DataFrame(ksco_rows).groupby(["occ_code", "section"])["emp_k"].sum()
              .groupby(level=0).transform(lambda s: s / s.sum()).rename("share").reset_index())
    ms = c.merge(shares, on="occ_code")
    matrices_sector = pd.DataFrame({
        "soc_code": ms["soc_code"], "industry": ms["section"],
        "emp_thousands": ms["emp"] * ms["share"] / 1000.0,
        "comp_musd": ms["emp"] * ms["share"] * ms["wage_year_won"] / 1e6,   # ₩m, ratio-only
    })
    return oews, exposure_occ, matrices_sector


def build_korea_deltas(year: str = "2025", kp=None) -> pd.DataFrame:
    """The per-worker deltas table in the engine's exact column contract.

    `kp` is a kernel.KernelParams: the consumption channel mirrors the US integrator's own
    construction (mpc × consumption_stickiness × disposable-income withdrawal × the
    consumption tax rate) with Korea's 10% VAT as the rate — the propensity comes from the
    kernel's parameters, not a Korea-invented constant."""
    from .kernel import KernelParams
    kp = kp or KernelParams()
    oews, _, _ = build_cells_frames(year)
    w = oews["annual_mean_wage"].to_numpy()

    tax = korea_income_tax(w, _ENGINE.employee_fica(w, "Single"))
    payroll = _ENGINE.fica(w, "Single")
    ui_annual = ei_daily_benefit(w) * 365.0
    eitc_delta = kr_eitc_delta_on_displacement(w, residual_income=0.0)

    df = pd.DataFrame({
        "soc_code": oews["soc_code"], "state": "KR",
        "employed": oews["employment_persons"].astype(float),
        "worker_wage": w, "ui_benefit": ui_annual,
    })
    for phase in ("during", "after"):
        # 비과세 benefit + individual taxation → the wage's full tax is lost in both phases
        df[f"{phase}_inc_fed"] = tax["national"]
        df[f"{phase}_inc_state"] = tax["local"]
        df[f"{phase}_payroll_fed"] = payroll
        df[f"{phase}_transfer_fed"] = eitc_delta          # negative: in-work credit lost
        df[f"{phase}_transfer_state"] = 0.0
    # consumption channel (VAT, 10%): the US integrator's own construction — mpc ×
    # consumption_stickiness × disposable-income withdrawal × rate — with the withdrawal
    # net of the (tax-exempt) EI benefit during the window
    KR_VAT_RATE = 0.10
    propensity = kp.mpc * kp.consumption_stickiness
    net_after_tax = w - tax["total"] - _ENGINE.employee_fica(w, "Single")
    for phase, residual in (("during", ui_annual), ("after", 0.0)):
        withdrawal = np.maximum(net_after_tax - residual, 0.0)
        df[f"{phase}_cons_state"] = withdrawal * propensity * KR_VAT_RATE
    # corporate offset: Korean effective rate on the retained share of saved compensation —
    # sector-invariant v1 (aggregate corporate treatment), so per-worker = rate × wage ×
    # retained share resolved by the kernel's disposition at runtime; the deltas table
    # carries the FULL-retention value exactly as the US table does (kernel scales it)
    df["corp_per_worker_fed"] = KR_CORP_EFF_RATE * w
    df["undist_per_worker"] = (1.0 - KR_CORP_EFF_RATE) * w
    return df

