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
from .korea_funds import (EI_BASELINE, NHI_BASELINE, NHI_REFORM, NPS_REFORM,
                          depletion_shift, erosion_fractions)

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
    # NPS_REFORM.revenue is already CONTRIBUTIONS ONLY (표 25's 보험료 column), so this band
    # covers one thing: the workplace-subscriber share of contribution revenue (지역가입자
    # pay their own full contributions on non-wage income). Pending the NPS statistical
    # yearbook split; scenarios choose inside the band and disclose.
    "nps": WageLinkedShare(
        value=None, low=0.75, high=0.95,
        status="band only — workplace share of contribution revenue pending (NPS yearbook)",
        source="NABO 표 25 gives contributions separately; split not yet primary-sourced"),
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
                         nhi_variant=NHI_REFORM,
                         nps_wage_linked_share: float | None = None) -> dict:
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
    out = {
        "nhi": depletion_shift(nhi_variant, nhi_erosion[:len(nhi_variant.revenue)],
                               wage_linked_share=nhi_wage_linked_share),
        "ei": depletion_shift(EI_BASELINE, ei_erosion[:len(EI_BASELINE.revenue)],
                              wage_linked_share=WAGE_LINKED_SHARE["ei"].value),
        "erosion_paths": paths,
    }
    if nps_wage_linked_share is not None:
        lo_n, hi_n = WAGE_LINKED_SHARE["nps"].low, WAGE_LINKED_SHARE["nps"].high
        assert lo_n <= nps_wage_linked_share <= hi_n, \
            f"nps_wage_linked_share outside the documented band [{lo_n}, {hi_n}]"
        nps_erosion = paths["NPS pension"]
        n = len(NPS_REFORM.revenue)
        assert len(nps_erosion) >= n, \
            f"adoption path shorter than the NPS horizon ({n} years — pass n_periods={n})"
        out["nps"] = depletion_shift(NPS_REFORM, nps_erosion[:n],
                                     wage_linked_share=nps_wage_linked_share)
    return out


# ---------------------------------------------------------------- Korea presets (direct chain)
# Adoption semantics in this chain: adoption_path[t] = cumulative share of the DISPLACEMENT-
# PRONE (HELC) jobs actually displaced by period t. Anchors per field in the provenance dicts
# and docs/KOREA_PRESET_EVIDENCE.md. `blurb` strings are PLACEHOLDERS — user-facing preset
# copy is Alex's voice and gets written before any UI exposure, never here.
from .presets import Preset, build_adoption_path  # noqa: E402

KOREA_PRESETS = {
    "korea-slow": Preset(
        key="korea-slow", name="Korea — slow diffusion", blurb="Slow diffusion in the pattern of the China shock, where SME lag holds realized displacement of exposed work to 10% by 2035.",
        adoption_start=0.005, adoption_end=0.10, n_periods=10, overrides={},
        adoption_reach_year=9,
        provenance={
            "adoption_start": "US realized canaries ~0.01–0.03 at year 3, discounted: Korea "
                              "is EARLIER on the curve (31% SME adoption vs >50% DEU, OECD "
                              "2025 first-hand)",
            "adoption_end": "China-shock-grind analogue: SME-laggard persistence holds "
                            "realized displacement of HELC jobs to ~10% by 2035",
        }),
    "korea-central": Preset(
        key="korea-central", name="Korea — central", blurb="US-observed early adoption discounted for Korea's SME lag, reaching 20% of exposed work by 2035.",
        adoption_start=0.01, adoption_end=0.20, n_periods=10, overrides={},
        adoption_reach_year=9,
        provenance={
            "adoption_start": "US canaries lower bound; OECD 31%-SME Korea discount",
            "adoption_end": "Acemoglu/Svanberg-class ~23% of exposed work profitably "
                            "automatable within 10y → 0.20 with the Korea adoption lag",
        }),
    "korea-fast": Preset(
        key="korea-fast", name="Korea — fast catch-up", blurb="Half of feasible automation realized by 2035, with Korea's ICT readiness driving a fast catch-up.",
        adoption_start=0.02, adoption_end=0.40, n_periods=10, overrides={},
        adoption_reach_year=9,
        provenance={
            "adoption_start": "US canaries upper bound",
            "adoption_end": "Windfall-Medium-class half-of-feasible with Korea ICT-readiness "
                            "catch-up → 0.40 of HELC jobs by 2035",
        }),

    # ---- the forecast-literature family, translated onto Korean data. Same discipline as
    # the AGI pair below: adoption paths, labor-market, disposition, and macro overrides
    # carry over parametrically; cognitive_feasibility is NOT carried — the US presets
    # discount a broad exposure measure (cf × PCA composite), while Korea's exposure IS the
    # BOK displacement-prone classification, which already embeds the complementarity
    # discount — carrying a second cf would double-discount. physical_feasibility stays
    # pinned at 0.0 (no Korean robot-exposure vector; disclosed). US-only fields (state
    # closure, US GRT compute rate, robotics_lag) are dropped. Calibration anchors are the
    # US papers' — carried parametrically onto Korean structure, disclosed per preset.
    # US presets without a reach year ramp linearly over their native horizon; the Korea
    # invariant (every preset reaches-then-holds at ANY horizon) pins reach_year=9 here.
    "korea-acemoglu": Preset(
        key="korea-acemoglu", name="Acemoglu — Modest AI",
        blurb="Acemoglu's 10-year upper bounds, which are small exposed share, modest productivity, normal labor market, and no wage response.",
        adoption_start=0.02, adoption_end=0.23, n_periods=10, adoption_reach_year=9,
        overrides=dict(reabsorption_rate=0.50, reemployment_haircut=0.13, lfp_exit_rate=0.03,
                       retained_profit_share=0.60, price_reduction_share=0.35, auto_cost=0.05,
                       survivor_elasticity=0.0, productivity_passthrough=0.15,
                       price_passthrough=0.30, demand_multiplier=0.30,
                       baseline_growth_rate=0.04),
        provenance=dict(
            adoption="Acemoglu/Svanberg: 23% of exposed tasks profitably automatable in 10y; "
                     "US canaries start (§1); applied to the BOK HELC base, which replaces "
                     "the US cf×exposure composite",
            reabsorption_rate="Farber normal-market 0.50 mild-slack (§1)",
            reemployment_haircut="Farber 2015 central 0.13 (§1)",
            lfp_exit_rate="Farber ~10% of losers NILF (§1)",
            retained_profit_share="capital share +0.38pp, no sizable wage rises (§1)",
            price_reduction_share="0.60/0.35/0.05 split (§1)",
            auto_cost="steady-state compute share, low (§1)",
            survivor_elasticity="no wage response measured (§1)",
            productivity_passthrough="TFP ≤0.66%/10y (§1)",
            price_passthrough="shipped default", demand_multiplier="active-Fed reading (§1)",
            baseline_growth_rate="~2% real + 2% inflation (§1)"),
    ),
    "korea-brynjolfsson": Preset(
        key="korea-brynjolfsson", name="Brynjolfsson — Augmentation",
        blurb="AI augments more than it automates, so slow realized adoption, gains shared with survivors, strong productivity, and mild impacts.",
        adoption_start=0.02, adoption_end=0.30, n_periods=10, adoption_reach_year=9,
        overrides=dict(reabsorption_rate=0.60, reemployment_haircut=0.10, lfp_exit_rate=0.02,
                       retained_profit_share=0.55, price_reduction_share=0.25, auto_cost=0.10,
                       survivor_elasticity=0.10, productivity_passthrough=0.50,
                       price_passthrough=0.30, demand_multiplier=0.30,
                       baseline_growth_rate=0.045),
        provenance=dict(
            adoption="Canaries realized pace, moderate end (§1); BOK HELC base",
            reabsorption_rate="Farber normal-market 0.60 (§1)",
            reemployment_haircut="mild scarring, DvW ~0.10 (§1)",
            lfp_exit_rate="augmentation world, below Farber (§1)",
            retained_profit_share="GenAI-at-Work gains partly shared → survivor 0.20 (§1)",
            price_reduction_share="0.55/0.25/0.20 split (§1)",
            auto_cost="shipped default (§1)",
            survivor_elasticity="complementarity at low depth: +0.10 (§1)",
            productivity_passthrough="GenAI at Work +15%/+30% novices → 0.5 (§1)",
            price_passthrough="shipped default", demand_multiplier="active-Fed reading (§1)",
            baseline_growth_rate="J-Curve real anchors + inflation (§1)"),
    ),
    "korea-karger": Preset(
        key="korea-karger", name="Karger et al. — Expert survey, rapid",
        blurb="The NBER expert survey's rapid scenario, which sits at a 14% probability. This means strong growth, modest displacement that exits the labor force, and a falling labor share.",
        adoption_start=0.03, adoption_end=0.16, n_periods=10, adoption_reach_year=9,
        overrides=dict(reabsorption_rate=0.35, reemployment_haircut=0.13, lfp_exit_rate=0.06,
                       retained_profit_share=0.55, price_reduction_share=0.25, auto_cost=0.15,
                       survivor_elasticity=0.0, productivity_passthrough=0.95,
                       price_passthrough=0.30, demand_multiplier=0.30,
                       baseline_growth_rate=0.05, reab_wage_baumol=0.30),
        provenance=dict(
            adoption="NBER w35046 rapid: net employment −≈3.1% by 2030, US-calibrated, "
                     "carried parametrically (§5); BOK HELC base",
            reabsorption_rate="0.35 mid-slack, churn with stable unemployment (§5)",
            reemployment_haircut="Farber central (§1)",
            lfp_exit_rate="the survey's signature: displacement exits the labour force (§5)",
            retained_profit_share="labor share 55.5→52.0 by 2030 (§5)",
            price_reduction_share="0.55/0.25/0.20 split (§5)",
            auto_cost="heavy AI infrastructure investment (§5)",
            survivor_elasticity="raises via the funded share, not tightness (§5)",
            productivity_passthrough="0.95 near ceiling (§5)",
            price_passthrough="shipped default", demand_multiplier="no doom loop in the "
            "expert median (§5)",
            baseline_growth_rate="rapid ≈3.3% real + inflation (§5)",
            reab_wage_baumol="service wages ride growth under rapid (§5)"),
    ),
    "korea-metaculus": Preset(
        key="korea-metaculus", name="Metaculus — Crowd median, 2035",
        blurb="The Labor Automation Hub's community medians, which are employment below the no-AI baseline, labor share down, and survivor wages up. The medians are US-calibrated and carried over parametrically.",
        adoption_start=0.02, adoption_end=0.20, n_periods=10, adoption_reach_year=9,
        overrides=dict(reabsorption_rate=0.45, reemployment_haircut=0.12, lfp_exit_rate=0.04,
                       retained_profit_share=0.45, price_reduction_share=0.20, auto_cost=0.10,
                       survivor_elasticity=0.0, productivity_passthrough=0.45,
                       price_passthrough=0.30, demand_multiplier=0.50,
                       baseline_growth_rate=0.04,
                       reab_wage_baumol=0.35, reab_wage_crowding=0.10),
        provenance=dict(
            adoption="Labor Automation Hub crowd medians: ≈7.5% AI-attributed employment "
                     "gap by 2035, US-calibrated, carried parametrically (§6); BOK HELC base",
            reabsorption_rate="growth concentrated in care/licensed occupations (§6)",
            reemployment_haircut="55% grad underemployment → downshift re-employment (§6)",
            lfp_exit_rate="long-term unemployment stays ≤4.5%: exits (§6)",
            retained_profit_share="labor share −4 to −5pp by 2035 (§6)",
            price_reduction_share="0.45/0.20/0.35: visible survivor raises (§6)",
            auto_cost="shipped default",
            survivor_elasticity="crowd wage growth is partly composition (§6)",
            productivity_passthrough="automation-linked part of crowd +28.6% (§6)",
            price_passthrough="shipped default",
            demand_multiplier="commentary flags a consumption problem; mid (§6)",
            baseline_growth_rate="~2% real + 2% inflation (§6)",
            reab_wage_baumol="service wages rise with tight refuge demand (§6)",
            reab_wage_crowding="crowding from the displaced inflow (§6)"),
    ),
    "korea-ai-2027": Preset(
        key="korea-ai-2027", name="AI 2027 — Fast takeoff",
        blurb="Cognition automated almost immediately with heavy compute investment. The scenario's robot economy is not modeled here, since the model only covers cognitive work.",
        adoption_start=0.20, adoption_end=1.0, n_periods=8, adoption_reach_year=5,
        overrides=dict(reabsorption_rate=0.10, reemployment_haircut=0.40, lfp_exit_rate=0.05,
                       retained_profit_share=0.70, price_reduction_share=0.20, auto_cost=0.30,
                       survivor_elasticity=-0.50, productivity_passthrough=0.90,
                       price_passthrough=0.50, demand_multiplier=1.20,
                       baseline_growth_rate=0.08, interest_rate=0.04),
        provenance=dict(
            adoption="Davidson: capability 20%→100% ~3y + diffusion → ceiling at year 5, "
                     "flat after (§2⑦); BOK HELC base — COGNITIVE ONLY, so the scenario's "
                     "robot economy (~1M robots/mo by 2028) is ABSENT: a deep understatement "
                     "for this preset in particular",
            reabsorption_rate="little re-employment during takeoff (§2⑦)",
            reemployment_haircut="displaced land at the service floor (§2⑦)",
            lfp_exit_rate="elevated exit (§2⑦)",
            retained_profit_share="0.70/0.20/0.10 split (§2⑦)",
            price_reduction_share="see retained (§2⑦)",
            auto_cost="$1T/yr global AI capex (§1)",
            survivor_elasticity="slider max −0.50 (§1)",
            productivity_passthrough="≥10× acceleration → near ceiling (§1)",
            price_passthrough="strong deflation (§2⑦)",
            demand_multiplier="crisis regime, partial offset (§1)",
            baseline_growth_rate="explosion band upper end (§1)",
            interest_rate="Korinek-Lockwood ~4% (§1)"),
    ),

    # ---- fast worlds: the US Korinek-Suh AGI presets translated onto Korean data.
    # These are forecast-literature scenarios, NOT Korea-calibrated diffusion: capability-
    # driven adoption overrides the SME-laggard discount, so the adoption numbers carry over
    # from presets.py unchanged. Three US override fields are deliberately DROPPED, not
    # ported: state_cut_share/state_rate_hike_cap (Korea has no state closure — the gap is
    # reported, never closed, by construction) and compute_effective_rate (the US GRT rate;
    # Korea's deltas carry the 24.2% effective corporate rate directly). robotics_lag is
    # also dropped and physical_feasibility pinned at 0.0: Korea has no published robot-
    # exposure vector wired, so the physical channel maps to zero and AGI displacement here
    # is the COGNITIVE channel only — an understatement for manual occupations, disclosed
    # wherever these scenarios are shown. A test enforces the pin so wiring a robot vector
    # later forces a conscious revisit.
    "korea-agi-20y": Preset(
        key="korea-agi-20y", name="Korinek-Suh — AGI in 20 years",
        blurb="Full automation of exposed work over 20 years, with wages collapsing and capital keeping the gains.",
        adoption_start=0.05, adoption_end=1.0, n_periods=20, adoption_reach_year=19,
        overrides=dict(cognitive_feasibility=1.0, physical_feasibility=0.0,
                       reabsorption_rate=0.05, reemployment_haircut=0.40, lfp_exit_rate=0.05,
                       retained_profit_share=0.80, price_reduction_share=0.15, auto_cost=0.15,
                       survivor_elasticity=-0.50, productivity_passthrough=0.90,
                       price_passthrough=0.50, demand_multiplier=1.00,
                       baseline_growth_rate=0.06, interest_rate=0.04),
        provenance=dict(
            adoption="Korinek-Suh baseline AGI: linear to full automation of exposed work "
                     "over 20y (§1); Korea lag overridden — capability drives diffusion",
            cognitive_feasibility="all cognitive tasks automatable within 20y (§1)",
            physical_feasibility="HELD AT ZERO for Korea: no published robot-exposure vector "
                                 "— cognitive channel only; understates AGI displacement in "
                                 "manual occupations (korea_exposure.py disclosure)",
            reabsorption_rate="no recovery in their AGI scenarios: wages stay collapsed (§1)",
            reemployment_haircut="wage-collapse mapped onto re-employment (§2⑤)",
            lfp_exit_rate="elevated permanent exit (§2⑤)",
            retained_profit_share="capital share → 1 as labor share collapses "
                                  "(Korinek-Lockwood) (§1)",
            price_reduction_share="0.80/0.15/0.05 split (§2⑤)",
            auto_cost="sustained compute build-out (§1)",
            survivor_elasticity="wage collapse ~3y before full automation → lever max -0.50 (§1)",
            productivity_passthrough="near lever ceiling in AGI scenarios (§1)",
            price_passthrough="strong deflation channel (§2⑤)",
            demand_multiplier="no-offset regime (§1)",
            baseline_growth_rate="upper band that keeps denominators interpretable (§1)",
            interest_rate="Korinek-Lockwood discount-rate anchor ~4% (§1)"),
    ),
    "korea-agi-5y": Preset(
        key="korea-agi-5y", name="Korinek-Suh — AGI in 5 years",
        blurb="Full automation of exposed work at year 5, viewed over a 10-year fiscal window.",
        adoption_start=0.20, adoption_end=1.0, n_periods=10, adoption_reach_year=5,
        overrides=dict(cognitive_feasibility=1.0, physical_feasibility=0.0,
                       reabsorption_rate=0.05, reemployment_haircut=0.40, lfp_exit_rate=0.10,
                       retained_profit_share=0.80, price_reduction_share=0.15, auto_cost=0.20,
                       survivor_elasticity=-0.50, productivity_passthrough=0.90,
                       price_passthrough=0.50, demand_multiplier=1.50,
                       baseline_growth_rate=0.08, interest_rate=0.04),
        provenance=dict(
            adoption="Korinek-Suh aggressive AGI: full automation of exposed work at year 5, "
                     "flat after (§1); Korea lag overridden — capability drives diffusion",
            cognitive_feasibility="5 years to full cognitive automation (§1)",
            physical_feasibility="HELD AT ZERO for Korea: no published robot-exposure vector "
                                 "— cognitive channel only; understates AGI displacement in "
                                 "manual occupations (korea_exposure.py disclosure)",
            reabsorption_rate="no recovery (§1)",
            reemployment_haircut="wage collapse (§2⑥)",
            lfp_exit_rate="mass permanent exit (§2⑥)",
            retained_profit_share="capital keeps the gains (§1)",
            price_reduction_share="0.80/0.15/0.05 split (§2⑥)",
            auto_cost="peak build-out compute share (§1)",
            survivor_elasticity="collapse: lever max -0.50 (§1)",
            productivity_passthrough="near ceiling (§1)",
            price_passthrough="strong deflation (§2⑥)",
            demand_multiplier="no-offset crisis regime (§1)",
            baseline_growth_rate="MacAskill-Moorhouse explosion band 0.06-0.08 (§1)",
            interest_rate="Korinek-Lockwood ~4% (§1)"),
    ),
}

# The uncertainty band sweeps the Korea-calibrated diffusion family ONLY. The AGI presets
# are separate scenario rows (shown as their own lines/columns), never band edges — folding
# a full-automation world into the band would swamp the calibrated range it exists to show.
KOREA_BAND_KEYS = ("korea-slow", "korea-central", "korea-fast")


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
    for pkey in KOREA_BAND_KEYS:
        preset = KOREA_PRESETS[pkey]
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
