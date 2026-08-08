"""Korea scenario scaffolding: cells × exposure × adoption → erosion paths → fund shifts.

This is the bridge from the model's units to the presentation's headline unit. The chain:

    exposure[occ] × adoption_path[t]  →  displaced share per cell per year (a CEILING:
    gross of reabsorption — the assembled V2 run replaces this with net displacement)
    →  korea_funds.erosion_fractions per year  →  per-fund erosion paths
    →  korea_funds.depletion_shift  →  "pulled forward by N years"

**The exposure seam refuses to run unsourced.** `EXPOSURE_BY_OCC` is None until a published
occupation-level vector lands (the top ask in docs/research/korea-primary-docs-request.md —
OECD StatLink / BOK 이슈노트 2023-30 / IMF SIP 2025/013). Passing exposure explicitly is for
tests and sensitivity work; the discipline is that no Korea headline is produced from an
invented vector.

**Adoption reuses the existing preset machinery** (`presets.Preset` + `build_adoption_path`)
— no new dynamics, per the necessity test. Korean calibration anchors for the eventual
presets are collected in docs/KOREA_PRESET_EVIDENCE.md; the load-bearing ones: Korean AI
adoption is LOW by international standards (✓ 31% of SMEs vs >50% Germany — Korea sits
earlier on the adoption curve), while KDI's technical ceiling is HIGH (✓ 38.8% of jobs >70%
automatable at 2023 technology, ~99% at the 2030 expert forecast) — a wide feasible-minus-
realized gap that adoption_path, not feasibility, must carry.

`WAGE_LINKED_SHARE` carries the per-fund share of published revenue that scales with the
wage-employee contribution base (the projector's second input), each with provenance.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .korea_cells import load_korea_cells
from .korea_funds import (EI_BASELINE, NHI_BASELINE, NHI_REFORM, depletion_shift,
                          erosion_fractions)

# ---------------------------------------------------------------- the exposure seam
# occ_code (KSCO 6th major, 1..9) -> fraction of the group's jobs technically automatable.
# None until a PUBLISHED vector lands. Do not hand-roll: an invented exposure vector is a
# free parameter calibrated against nothing, and it carries the whole composition story.
EXPOSURE_BY_OCC: dict | None = None


def require_exposure(exposure: dict | None = None) -> dict:
    exposure = exposure if exposure is not None else EXPOSURE_BY_OCC
    if exposure is None:
        raise RuntimeError(
            "No published Korea exposure vector is wired yet — see the top ask in "
            "docs/research/korea-primary-docs-request.md (OECD StatLink / BOK 이슈노트 / "
            "IMF SIP). Pass an explicit vector only for tests or sensitivity work.")
    assert set(exposure) == set(range(1, 10)), "exposure must cover KSCO majors 1..9"
    vals = np.array([exposure[k] for k in range(1, 10)], dtype=float)
    assert np.isfinite(vals).all() and (0.0 <= vals).all() and (vals <= 1.0).all(), \
        "exposure entries are job-share fractions in [0, 1]"
    return exposure


# ------------------------------------------- wage-linked share of published fund revenue
@dataclass(frozen=True)
class WageLinkedShare:
    """Share of a fund's published revenue that scales with the wage-employee base."""
    value: float | None          # None = a band, not a point — scenario must choose
    low: float
    high: float
    status: str
    source: str


WAGE_LINKED_SHARE = {
    # 2025: contributions ₩18.92tn (표 146) of whole-fund revenue ₩20.35tn (표 149); the
    # non-contribution rest is investment income, the maternity general-account transfer and
    # other income. Contributions are levied on wages (self-employed opt-in is negligible).
    "ei": WageLinkedShare(
        value=189_177 / 203_485, low=0.90, high=0.95,
        status="verified",
        source="「2026 대한민국 사회보험」 [표 146]/[표 149], FY2025"),
    # Two ✓ components and one ⚠: contributions are 84.9% of revenue (표 203, 2025:
    # 872,776억/1,028,585억) and the state subsidy statutorily TRACKS expected contribution
    # revenue (14% general account + 6% health-promotion fund, 표 202) — which argues the
    # effective share approaches (contributions+subsidy)/revenue ≈ 0.97 — but the workplace
    # (직장) share of contributions is not tabulated in the annual (NHIS statistics needed).
    # No central value until that lands; scenarios must choose inside the band and disclose.
    "nhi": WageLinkedShare(
        value=None, low=0.65, high=0.97,
        status="band only — workplace share of contributions pending (NHIS statistics)",
        source="「2026 대한민국 사회보험」 [표 202]/[표 203], FY2025"),
}


# ---------------------------------------------------------------- the pipeline
def korea_erosion_paths(adoption_path, exposure: dict | None = None, cells=None) -> dict:
    """Per-year erosion fractions per institution, from the direct exposure × adoption chain.

    `adoption_path[t]` is the cumulative share of technically-automatable work realized by
    period t (the presets' `build_adoption_path` output). The product exposure × adoption is
    a displacement CEILING — gross of reabsorption — so headline uses must either say so or
    feed net displacement from an assembled model run instead.

    Returns {institution: np.ndarray over the horizon}, keys as in `erosion_fractions`."""
    exposure = require_exposure(exposure)
    c = cells if cells is not None else load_korea_cells("2025").cells
    a = np.asarray(adoption_path, dtype=float)
    assert a.ndim == 1 and a.size > 0 and np.isfinite(a).all()
    assert (0.0 <= a).all() and (a <= 1.0).all(), "adoption is a cumulative share in [0, 1]"
    assert (np.diff(a) >= -1e-12).all(), "adoption is cumulative — must be non-decreasing"

    exp_per_cell = c["occ_code"].map(exposure).to_numpy(dtype=float)
    emp = c["emp"].to_numpy()
    out: dict[str, list] = {}
    for a_t in a:
        frac_t = erosion_fractions(emp * exp_per_cell * a_t, cells=c)
        for k, v in frac_t.items():
            out.setdefault(k, []).append(v)
    return {k: np.asarray(v) for k, v in out.items()}


def korea_fund_headlines(adoption_path, nhi_wage_linked_share: float,
                         exposure: dict | None = None, cells=None,
                         nhi_variant=NHI_REFORM) -> dict:
    """Depletion shifts for the funds with published paths, from one adoption scenario.

    The NHI share must be chosen explicitly from `WAGE_LINKED_SHARE["nhi"]`'s band (and
    disclosed); EI uses its verified share. Erosion is sliced to each fund's published
    horizon. NPS joins when a post-reform path lands."""
    lo, hi = WAGE_LINKED_SHARE["nhi"].low, WAGE_LINKED_SHARE["nhi"].high
    assert lo <= nhi_wage_linked_share <= hi, \
        f"nhi_wage_linked_share outside the documented band [{lo}, {hi}]"
    paths = korea_erosion_paths(adoption_path, exposure=exposure, cells=cells)
    # NHI contributions are levied on the same uncapped wage base as the LTC rider; the
    # health line is the right erosion series for the NHI fund.
    nhi_erosion = paths["NHI health"]
    ei_erosion = paths["EI unemployment benefit"]
    assert len(nhi_erosion) >= len(nhi_variant.revenue), \
        f"adoption path shorter than the NHI horizon ({len(nhi_variant.revenue)} years)"
    assert len(ei_erosion) >= len(EI_BASELINE.revenue), \
        f"adoption path shorter than the EI horizon ({len(EI_BASELINE.revenue)} years)"
    return {
        "nhi": depletion_shift(nhi_variant, nhi_erosion[:len(nhi_variant.revenue)],
                               wage_linked_share=nhi_wage_linked_share),
        "ei": depletion_shift(EI_BASELINE, ei_erosion[:len(EI_BASELINE.revenue)],
                              wage_linked_share=WAGE_LINKED_SHARE["ei"].value),
        "erosion_paths": paths,
    }
