"""Korea scenario scaffolding: cells × exposure × adoption → erosion paths → fund shifts.

This is the bridge from the model's units to the presentation's headline unit. The chain:

    exposure[occ] × adoption_path[t]  →  displaced share per cell per year (a CEILING:
    gross of reabsorption — the assembled V2 run replaces this with net displacement)
    →  korea_funds.erosion_fractions per year  →  per-fund erosion paths
    →  korea_funds.depletion_shift  →  "pulled forward by N years"

**The exposure seam is now WIRED to a published vector**: the within-group high-exposure/
low-complementarity shares from BOK 이슈노트 2025-2 <그림 9> (confirmed by IMF SIP 2025/013
Fig. 7) — see korea_exposure.py for provenance and the figure-read disclosure. The seam still
refuses any run without a vector; passing exposure explicitly remains for tests and
sensitivity work.

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
from .korea_exposure import EXPOSURE_HEHC, EXPOSURE_HELC
from .korea_funds import (EI_BASELINE, NHI_BASELINE, NHI_REFORM, depletion_shift,
                          erosion_fractions)

# ---------------------------------------------------------------- the exposure seam
# occ_code (KSCO 6th major, 1..9) -> displacement-prone fraction of the group's jobs: the
# within-group high-exposure/LOW-complementarity share from BOK 이슈노트 2025-2 <그림 9>
# (IMF SIP 2025/013 Fig. 7 confirms; full provenance and the figure-read disclosure in
# korea_exposure.py). The manual groups' zeros are the AI-cognitive channel only — their
# automation runs through the physical channel, gated by robotics_lag.
EXPOSURE_BY_OCC: dict | None = dict(EXPOSURE_HELC)


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


# ---------------------------------------------------------------- Korea presets (direct chain)
# Adoption semantics in this chain: adoption_path[t] = cumulative share of the DISPLACEMENT-
# PRONE (HELC) jobs actually displaced by period t. Anchors per field in the provenance dicts
# and docs/KOREA_PRESET_EVIDENCE.md. `blurb` strings are PLACEHOLDERS — user-facing preset
# copy is Alex's voice and gets written before any UI exposure, never here.
from .presets import Preset, build_adoption_path  # noqa: E402

KOREA_PRESETS = {
    "korea-slow": Preset(
        key="korea-slow", name="Korea — slow diffusion", blurb="[copy TBD — not model-authored]",
        adoption_start=0.005, adoption_end=0.10, n_periods=10, overrides={},
        provenance={
            "adoption_start": "US realized canaries ~0.01–0.03 at year 3, discounted: Korea "
                              "is EARLIER on the curve (31% SME adoption vs >50% DEU, OECD "
                              "2025 first-hand)",
            "adoption_end": "China-shock-grind analogue: SME-laggard persistence holds "
                            "realized displacement of HELC jobs to ~10% by 2035",
        }),
    "korea-central": Preset(
        key="korea-central", name="Korea — central", blurb="[copy TBD — not model-authored]",
        adoption_start=0.01, adoption_end=0.20, n_periods=10, overrides={},
        provenance={
            "adoption_start": "US canaries lower bound; OECD 31%-SME Korea discount",
            "adoption_end": "Acemoglu/Svanberg-class ~23% of exposed work profitably "
                            "automatable within 10y → 0.20 with the Korea adoption lag",
        }),
    "korea-fast": Preset(
        key="korea-fast", name="Korea — fast catch-up", blurb="[copy TBD — not model-authored]",
        adoption_start=0.02, adoption_end=0.40, n_periods=10, overrides={},
        provenance={
            "adoption_start": "US canaries upper bound",
            "adoption_end": "Windfall-Medium-class half-of-feasible with Korea ICT-readiness "
                            "catch-up → 0.40 of HELC jobs by 2035",
        }),
}


def korea_headline_band(cells=None) -> dict:
    """The parametric uncertainty band over the direct chain: adoption preset ×
    NHI wage-linked band edges × exposure figure-read error (±0.5pp on each HELC segment,
    renormalized within group). Returns per-fund ranges of the headline.

    This is the September vehicle if the assembled-V2 route stays gated; every axis of the
    band is a SOURCED uncertainty (preset anchors, the NHIS pending split, the figure read),
    not a free parameter."""
    from .korea_exposure import FIG9_SHARES

    def _exposure_variant(delta_pp: float) -> dict:
        out = {}
        for g, (le, hehc, helc) in FIG9_SHARES.items():
            total = le + hehc + helc
            if total == 0.0:
                out[g] = 0.0
                continue
            helc_v = min(max(helc + delta_pp if helc > 0 else helc, 0.0), total)
            out[g] = helc_v / total
        return out

    results: dict[str, dict] = {}
    for pkey, preset in KOREA_PRESETS.items():
        adoption = build_adoption_path(preset, 10)
        for share_edge, share in (("nhi-share-low", WAGE_LINKED_SHARE["nhi"].low),
                                  ("nhi-share-high", WAGE_LINKED_SHARE["nhi"].high)):
            for ekey, delta in (("exp-low", -0.5), ("exp-central", 0.0), ("exp-high", 0.5)):
                run = korea_fund_headlines(adoption, nhi_wage_linked_share=share,
                                           exposure=_exposure_variant(delta), cells=cells)
                results[f"{pkey}|{share_edge}|{ekey}"] = {
                    "nhi_years_forward": run["nhi"]["years_pulled_forward"],
                    "nhi_eroded_date": run["nhi"]["eroded_date"],
                    "ei_reserve_2029_shortfall_tn": float(
                        21.8 - run["ei"]["eroded_reserves"][-1]),
                }
    return results
