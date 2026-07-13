"""Literature-anchored scenario presets + composable policy overlays.

A **preset** is a world state: what AI capability, diffusion, and the labor market do to the budget.
A **policy overlay** is a government response (robot tax, UBI, compute-pool taxation) applied ON TOP
of any preset. Presets ship with the robot tax OFF — the separation keeps the question clean: the
preset says what happens to the budget, the overlay says what policy recovers.

Every number is anchored to the fetch-verified evidence in docs/PRESET_EVIDENCE.md (quotes + URLs in
docs/research/preset-evidence-raw.json). Where a UI widget grid forced a snap, the provenance entry
records both the source value and the shipped value.

Pure module: no streamlit. The app derives its widget defaults from `to_params(preset)`; the CLI
(`scripts/monte_carlo.py --preset <key>`) and tests consume `PRESETS`/`OVERLAYS` directly.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Optional

import numpy as np

from .levers_v2 import DEFAULTS_SHIPPED, V2Params


@dataclass(frozen=True)
class Preset:
    key: str
    name: str
    blurb: str                       # one-liner shown under the UI selectbox
    adoption_start: float            # cumulative share of feasible work automated at year 0 …
    adoption_end: float              # … and at the end of the ramp
    n_periods: int                   # the preset's native horizon (overridable)
    overrides: dict                  # V2Params field -> value (survivor share is DERIVED, never set)
    provenance: dict                 # field -> short anchor string (paper, value, PRESET_EVIDENCE §)
    # Kink, stored PARAMETRICALLY so any horizon can synthesize the right path (a fixed-length list
    # would silently flat-extend/truncate — dynamics._adoption clamps indices without error):
    # linear start→end over years 0..reach, flat at end after. None = linear over the whole horizon.
    adoption_reach_year: Optional[int] = None


def build_adoption_path(preset: Preset, n_periods: int) -> list:
    """The preset's cumulative adoption ceiling per period, synthesized for the requested horizon."""
    n = int(n_periods)
    if preset.adoption_reach_year is None:
        return list(np.linspace(preset.adoption_start, preset.adoption_end, n))
    ramp = np.linspace(preset.adoption_start, preset.adoption_end, preset.adoption_reach_year + 1)
    if n <= ramp.size:               # horizon shorter than the transition: honest truncation
        return list(ramp[:n])
    return list(ramp) + [preset.adoption_end] * (n - ramp.size)


def to_params(preset: Preset, n_periods: Optional[int] = None,
              base: V2Params = DEFAULTS_SHIPPED) -> V2Params:
    """Build the full V2Params for a preset (fields not overridden inherit `base`).

    `survivor_gains_share` is derived with the app's exact remainder expression (streamlit_app.
    build_v2_params) so the sidebar round-trips bit-for-bit — a rounded literal would differ by 1 ulp
    and a plain replace() would keep the shipped 0.2 and break the disposition simplex.
    """
    n = int(n_periods) if n_periods is not None else preset.n_periods
    ov = dict(preset.overrides)
    ov["survivor_gains_share"] = max(0.0, 1.0 - ov["retained_profit_share"]
                                     - ov["price_reduction_share"])
    return replace(base, n_periods=n, adoption_path=build_adoption_path(preset, n), **ov)


# ---------------------------------------------------------------------------- the seven presets
# Values quantized to the sidebar widget grids; provenance records source vs shipped where snapped.
# Unlisted fields inherit DEFAULTS_SHIPPED (rung 1, ceiling 1.5, spillover 0.5, ui_weeks 26,
# attrition 0.025, ubi 0, robot tax 0 — taxation lives in OVERLAYS).

PRESETS: dict[str, Preset] = {p.key: p for p in [

    Preset(
        key="acemoglu-modest", name="Acemoglu — Modest AI",
        blurb="His 10-year upper bounds at face value: small exposed share, modest productivity, "
              "normal labor market, no wage response.",
        adoption_start=0.02, adoption_end=0.23, n_periods=10,
        overrides=dict(cognitive_feasibility=0.20, physical_feasibility=0.05, robotics_lag=8.0,
                       reabsorption_rate=0.50, reemployment_haircut=0.13, lfp_exit_rate=0.03,
                       retained_profit_share=0.60, price_reduction_share=0.35, auto_cost=0.05,
                       survivor_elasticity=0.0, productivity_passthrough=0.15,
                       price_passthrough=0.30, demand_multiplier=0.30,
                       baseline_growth_rate=0.04, compute_effective_rate=0.10),
        provenance=dict(
            cognitive_feasibility="Acemoglu 2024: 19.9% of the US wage bill exposed to AI (§1)",
            adoption="23% of exposed tasks profitably automatable within 10y (Svanberg et al. "
                     "extrapolation) → end 0.23; start 0.02 per Canaries realized pace (§1)",
            physical_feasibility="his frame is cognitive-only; token robot share (§1)",
            robotics_lag="Productivity J-Curve adoption→output lag 8-12y (§1)",
            productivity_passthrough="TFP ≤0.66%/10y, GDP ~1.1% incl. capital deepening → 0.12-0.155 (§1)",
            reabsorption_rate="Farber: 0.60-0.75/yr normal markets; 0.50 mild-slack (§1)",
            reemployment_haircut="Farber 2015 central 0.13 (survivor-selected; band 0.10-0.18) (§1)",
            lfp_exit_rate="Farber: ~10% of losers NILF → 0.03-0.05/yr (§1)",
            retained_profit_share="capital share +0.38pp, 'no sizable wage rises' → survivor 0.05 (§1)",
            price_reduction_share="remainder toward prices, 0.60/0.35/0.05 split (§1)",
            auto_cost="steady-state compute share, low (§1)",
            survivor_elasticity="no sizable wage response measured (§1)",
            price_passthrough="shipped default",
            demand_multiplier="active-Fed reading; Chodorow-Reich 1.8 is the no-offset pole (§1)",
            baseline_growth_rate="~2% real + 2% inflation (§1)",
            compute_effective_rate="shipped default (§1)"),
    ),

    Preset(
        key="brynjolfsson-augment", name="Brynjolfsson — Augmentation",
        blurb="AI complements more than it substitutes: slow realized adoption, gains shared with "
              "survivors, strong productivity, mild scarring.",
        adoption_start=0.02, adoption_end=0.30, n_periods=10,
        overrides=dict(cognitive_feasibility=0.30, physical_feasibility=0.10, robotics_lag=6.0,
                       reabsorption_rate=0.60, reemployment_haircut=0.10, lfp_exit_rate=0.02,
                       retained_profit_share=0.55, price_reduction_share=0.25, auto_cost=0.10,
                       survivor_elasticity=0.10, productivity_passthrough=0.50,
                       price_passthrough=0.30, demand_multiplier=0.30,
                       baseline_growth_rate=0.045, compute_effective_rate=0.10),
        provenance=dict(
            cognitive_feasibility="Eloundou β central ~0.30 of task content (§1)",
            adoption="Canaries: cumulative ~0.01-0.03 at year 3 → start 0.02; moderate end (§1)",
            physical_feasibility="low near-term robotics (§1)",
            robotics_lag="J-Curve intangible build-out, lower band (§1)",
            reabsorption_rate="Farber normal-market 0.60-0.75/yr (§1)",
            reemployment_haircut="mild scarring; DvW expansion-displacement ~0.10 (§1)",
            lfp_exit_rate="augmentation world: below Farber's 0.03 (§1)",
            retained_profit_share="GenAI-at-Work gains partly shared → survivor 0.20 (§1)",
            price_reduction_share="0.55/0.25/0.20 split (§1)",
            auto_cost="shipped default (§1)",
            survivor_elasticity="complementarity at low depth: novices +30% (GenAI at Work) → +0.10 (§1)",
            productivity_passthrough="GenAI at Work +15% avg / +30% novices → 0.5 for the cognitive "
                                     "channel (§1)",
            price_passthrough="shipped default",
            demand_multiplier="active-Fed reading (§1)",
            baseline_growth_rate="J-Curve real anchors 2.2-2.7% + 2% inflation (§1)",
            compute_effective_rate="shipped default (§1)"),
    ),

    Preset(
        key="windfall-medium", name="Windfall Trust — Medium",
        blurb="Their Medium scenario translated: 60% exposed, half automated in 10y, heavy scarring, "
              "high value capture, capital taxed at their ETR. Direct comparator (10y target -2.8%).",
        adoption_start=0.05, adoption_end=0.50, n_periods=10,
        overrides=dict(cognitive_feasibility=0.55, physical_feasibility=0.20, robotics_lag=5.0,
                       reabsorption_rate=0.30, reemployment_haircut=0.30, lfp_exit_rate=0.03,
                       retained_profit_share=0.50, price_reduction_share=0.50, auto_cost=0.10,
                       survivor_elasticity=-0.15, productivity_passthrough=0.30,
                       price_passthrough=0.50, demand_multiplier=0.50,
                       baseline_growth_rate=0.04, compute_effective_rate=0.27),
        provenance=dict(
            cognitive_feasibility="Windfall: exposed sectors = 60% of jobs; 0.55 cog + 0.20 phys ≈ "
                                  "their combined share (§1)",
            adoption="their Medium: 50% of exposed displaced over the decade (§2③)",
            physical_feasibility="component of the 0.6 combined exposure (§2③)",
            robotics_lag="mid-range build-out (§1)",
            reabsorption_rate="DvW slack-market band 0.15-0.35 (§1)",
            reemployment_haircut="their Medium scarring: re-employment at 70% of prior wage (§2③)",
            lfp_exit_rate="their 20%-of-displaced-over-6y ⇒ ~0.033/yr; ui grid → 0.03 (source 0.033) (§2③)",
            retained_profit_share="their high-capture: firms 45% / consumers 45% of displaced wages → "
                                  "0.50/0.50 of net saving (§2③)",
            price_reduction_share="see retained (their consumer share) (§2③)",
            auto_cost="their 10% residual (§2③)",
            survivor_elasticity="shipped default (mild substitution)",
            productivity_passthrough="shipped default",
            price_passthrough="their consumer share reaches prices (§2③)",
            demand_multiplier="shipped default",
            baseline_growth_rate="shipped default",
            compute_effective_rate="their capital ETR 26.7%; ui grid → 0.27 (source 0.267) (§1)"),
    ),

    Preset(
        key="china-shock", name="China-Shock Grind",
        blurb="A moderate shock met by the labor market ADH actually measured: decade-scale "
              "adjustment, LFP exit dominant, deep scarring, full demand amplification. 15 years.",
        adoption_start=0.05, adoption_end=0.40, n_periods=15,
        overrides=dict(cognitive_feasibility=0.30, physical_feasibility=0.20, robotics_lag=4.0,
                       reabsorption_rate=0.075, reemployment_haircut=0.25, lfp_exit_rate=0.10,
                       attrition_rate=0.04,
                       retained_profit_share=0.70, price_reduction_share=0.20, auto_cost=0.10,
                       survivor_elasticity=-0.30, productivity_passthrough=0.20,
                       price_passthrough=0.30, demand_multiplier=1.50,
                       baseline_growth_rate=0.035, compute_effective_rate=0.10),
        provenance=dict(
            cognitive_feasibility="moderate exposure; the mechanism, not the size, is the story (§2④)",
            adoption="moderate shock spread over 15y (§2④)",
            physical_feasibility="includes the manufacturing channel ADH measured (§2④)",
            robotics_lag="shipped default",
            reabsorption_rate="ADH: employment-to-population falls ~1:1 for a decade → 0.05-0.10/yr (§1)",
            reemployment_haircut="JLS-severity 0.25 for high-attachment cohorts (§1)",
            lfp_exit_rate="ADH: NILF +0.55pp vs unemployment +0.22pp — LFP exit dominates → 0.08-0.15 (§1)",
            attrition_rate="ADH grind band 0.03-0.05 (§1)",
            retained_profit_share="capital keeps most of the gains (§2④)",
            price_reduction_share="0.70/0.20/0.10 split (§2④)",
            auto_cost="shipped default",
            survivor_elasticity="Webb annualized wage drag, deep-slack end (§1)",
            productivity_passthrough="below shipped: gains real but local demand collapses (§2④)",
            price_passthrough="shipped default",
            demand_multiplier="ADH ≥2× amplification; Chodorow-Reich 1.8 no-offset (§1)",
            baseline_growth_rate="depressed-trend reading (§2④)",
            compute_effective_rate="shipped default"),
    ),
    
    Preset(
        key="agi-20y", name="Korinek-Suh — AGI in 20 years",
        blurb="Full automation over 20 years; wages collapse before the end; capital keeps the "
              "gains; states lean on spending cuts.",
        adoption_start=0.05, adoption_end=1.0, n_periods=20,
        overrides=dict(cognitive_feasibility=1.0, physical_feasibility=1.0, robotics_lag=10.0,
                       reabsorption_rate=0.05, reemployment_haircut=0.40, lfp_exit_rate=0.05,
                       retained_profit_share=0.80, price_reduction_share=0.15, auto_cost=0.15,
                       survivor_elasticity=-0.50, productivity_passthrough=0.90,
                       price_passthrough=0.50, demand_multiplier=1.00,
                       baseline_growth_rate=0.06, compute_effective_rate=0.05,
                       interest_rate=0.04, state_cut_share=0.5, state_rate_hike_cap=0.5),
        provenance=dict(
            cognitive_feasibility="Korinek-Suh baseline AGI: all tasks automatable within 20y (§1)",
            adoption="linear to full automation over the 20y horizon (§2⑤)",
            physical_feasibility="AGI includes physical work, behind the capacity ramp (§2⑤)",
            robotics_lag="physical capacity trails cognition by ~a decade (§2⑤)",
            reabsorption_rate="no recovery in their AGI scenarios: wages stay collapsed (§1)",
            reemployment_haircut="wage-collapse mapped onto re-employment (§2⑤)",
            lfp_exit_rate="elevated permanent exit (§2⑤)",
            retained_profit_share="capital share → 1 as labor share collapses (Korinek-Lockwood) (§1)",
            price_reduction_share="0.80/0.15/0.05 split (§2⑤)",
            auto_cost="sustained compute build-out (§1)",
            survivor_elasticity="wage collapse ~3y before full automation → slider max -0.50 (§1)",
            productivity_passthrough="near lever ceiling in AGI scenarios (§1)",
            price_passthrough="strong deflation channel (§2⑤)",
            demand_multiplier="no-offset regime (§1)",
            baseline_growth_rate="upper band that keeps %-GDP denominators interpretable (§1)",
            compute_effective_rate="GRT post-TCJA effective rate: capital undertaxed (§1)",
            interest_rate="Korinek-Lockwood discount-rate anchor ~4% (§1)",
            state_cut_share="labor-base rate hikes cannot close AGI-stage gaps (Korinek-Lockwood) (§1)",
            state_rate_hike_cap="see state_cut_share (§1)"),
    ),

    Preset(
        key="agi-5y", name="Korinek-Suh — AGI in 5 years",
        blurb="The aggressive transition: full automation at year 5 (kinked path), viewed over a "
              "10-year fiscal window. The stress case.",
        adoption_start=0.20, adoption_end=1.0, n_periods=10, adoption_reach_year=5,
        overrides=dict(cognitive_feasibility=1.0, physical_feasibility=1.0, robotics_lag=2.0,
                       reabsorption_rate=0.05, reemployment_haircut=0.40, lfp_exit_rate=0.10,
                       retained_profit_share=0.80, price_reduction_share=0.15, auto_cost=0.20,
                       survivor_elasticity=-0.50, productivity_passthrough=0.90,
                       price_passthrough=0.50, demand_multiplier=1.50,
                       baseline_growth_rate=0.08, compute_effective_rate=0.05,
                       interest_rate=0.04, state_cut_share=0.5, state_rate_hike_cap=0.5),
        provenance=dict(
            cognitive_feasibility="Korinek-Suh aggressive AGI: 5 years to full automation (§1)",
            adoption="kinked: linear to 1.0 at year 5, flat after — their wage collapse hits ~year 3 (§1)",
            physical_feasibility="compressed physical ramp (§2⑥)",
            robotics_lag="AI-2027-style crash build-out (§1)",
            reabsorption_rate="no recovery (§1)",
            reemployment_haircut="wage collapse (§2⑥)",
            lfp_exit_rate="mass permanent exit (§2⑥)",
            retained_profit_share="capital keeps the gains (§1)",
            price_reduction_share="0.80/0.15/0.05 split (§2⑥)",
            auto_cost="peak build-out compute share (§1)",
            survivor_elasticity="collapse: slider max -0.50 (§1)",
            productivity_passthrough="near ceiling (§1)",
            price_passthrough="strong deflation (§2⑥)",
            demand_multiplier="no-offset crisis regime (§1)",
            baseline_growth_rate="MacAskill-Moorhouse explosion band 0.06-0.08 (§1)",
            compute_effective_rate="capital undertaxed status quo (§1)",
            interest_rate="Korinek-Lockwood ~4% (§1)",
            state_cut_share="AGI-stage gaps close by cuts (§1)",
            state_rate_hike_cap="see state_cut_share (§1)"),
    ),

    Preset(
        key="ai-2027", name="AI 2027 — Fast takeoff",
        blurb="The AI Futures scenario shape: cognition maxes almost immediately, robots ramp in 3 "
              "years, heavy compute investment, 8-year horizon.",
        adoption_start=0.10, adoption_end=1.0, n_periods=8,
        overrides=dict(cognitive_feasibility=1.0, physical_feasibility=0.90, robotics_lag=3.0,
                       reabsorption_rate=0.10, reemployment_haircut=0.40, lfp_exit_rate=0.05,
                       retained_profit_share=0.70, price_reduction_share=0.20, auto_cost=0.30,
                       survivor_elasticity=-0.50, productivity_passthrough=0.90,
                       price_passthrough=0.50, demand_multiplier=1.20,
                       baseline_growth_rate=0.08, compute_effective_rate=0.05,
                       interest_rate=0.04),
        provenance=dict(
            cognitive_feasibility="superhuman coder → ASI within ~1y of scenario start (§1)",
            adoption="Davidson: 20%→100% capability median ~3y; deployment trails <1y (§1)",
            physical_feasibility="robot economy: ~1M robots/mo by end-2028 (§1)",
            robotics_lag="special-economic-zone build-out: 3-4y (§1)",
            reabsorption_rate="little re-employment during takeoff (§2⑦)",
            reemployment_haircut="displaced land at the service floor (§2⑦)",
            lfp_exit_rate="elevated exit (§2⑦)",
            retained_profit_share="0.70/0.20/0.10 split (§2⑦)",
            price_reduction_share="see retained (§2⑦)",
            auto_cost="$1T/yr global AI capex; 0.3-0.5 early, declining (§1)",
            survivor_elasticity="slider max -0.50 (§1)",
            productivity_passthrough="MacAskill-Moorhouse ≥10× acceleration → near ceiling (§1)",
            price_passthrough="strong deflation (§2⑦)",
            demand_multiplier="crisis regime, partial offset (§1)",
            baseline_growth_rate="explosion band upper end (§1)",
            compute_effective_rate="capital undertaxed status quo (§1)",
            interest_rate="Korinek-Lockwood ~4% (§1)"),
    ),
]}


# ---------------------------------------------------------------------------- policy overlays
# Applied AFTER the sidebar/preset params are built — they override the corresponding levers.
# The robot-tax literature is ad-valorem on robot SPENDING, so the rate on our saved-compensation
# base is t_av × auto_cost (docs/PRESET_EVIDENCE.md, "unit traps" #2), clipped to the model's
# fail-loud bound retained·(1-auto_cost) exactly like the MC sampler (fiscal_model/mc.py).

def _robot_tax(v2p: V2Params, t_av: float, label: str) -> tuple[V2Params, str]:
    bound = max(0.0, v2p.retained_profit_share * (1.0 - v2p.auto_cost))
    rate = min(t_av * v2p.auto_cost, bound)
    note = (f"{label}: {t_av:.1%} ad-valorem × auto_cost {v2p.auto_cost:.0%} → "
            f"automation_tax_rate = {rate:.4f} of the saved compensation bill")
    return replace(v2p, automation_tax_rate=rate), note


def _cw(v2p: V2Params) -> tuple[V2Params, str]:
    return _robot_tax(v2p, 0.027, "Costinot-Werning optimal robot tax")


def _grt(v2p: V2Params) -> tuple[V2Params, str]:
    p, note = _robot_tax(v2p, 0.051, "GRT transitional robot tax (decade 1)")
    if v2p.n_periods > 10:
        note += (" — held constant beyond year 10; GRT's decade-2 rate is 2.2% and their steady "
                 "state is ZERO, so this overstates the tax at long horizons")
    return p, note


def _ubi(v2p: V2Params) -> tuple[V2Params, str]:
    p = replace(v2p, ubi_annual=12_000.0, ubi_recapture_rate=0.30)
    return p, ("UBI: $12,000/worker/yr with 30% recapture (income-tax clawback, "
               "Korinek-Lockwood 0.25-0.375)")


def _parity(v2p: V2Params) -> tuple[V2Params, str]:
    p = replace(v2p, compute_effective_rate=0.27)
    return p, ("Compute-pool parity tax: effective rate 0.27 (Windfall capital ETR 26.7%) vs the "
               "0.05 post-TCJA status quo")


@dataclass(frozen=True)
class Overlay:
    key: str
    name: str
    blurb: str
    provenance: str
    apply: Callable[[V2Params], tuple[V2Params, str]]


OVERLAYS: dict[str, Overlay] = {o.key: o for o in [
    Overlay("cw-robot-tax", "Robot tax — optimal (Costinot-Werning)",
            "2.7% ad-valorem on robot spending (their 1-3.7% sufficient statistic, central).",
            "Costinot-Werning REStud 2023 (PRESET_EVIDENCE §3); should not scale UP with depth",
            _cw),
    Overlay("grt-robot-tax", "Robot tax — transitional (GRT)",
            "5.1% ad-valorem, their decade-1 Mirrleesian rate (steady state: zero).",
            "Guerreiro-Rebelo-Teles REStud 2022 (PRESET_EVIDENCE §3)", _grt),
    Overlay("ubi", "UBI $12k + 30% recapture",
            "A worker-based UBI financed with a pure tax clawback.",
            "Korinek-Lockwood NBER 34873 recapture 0.25-0.375 (PRESET_EVIDENCE §3)", _ubi),
    Overlay("compute-parity", "Compute-pool parity taxation",
            "Tax the compute-capital pool like domestic capital (ETR 0.27) instead of 0.05.",
            "Windfall capital ETR 26.7% vs GRT post-TCJA 5% (PRESET_EVIDENCE §1)", _parity),
]}

_EXCLUSIVE = ("cw-robot-tax", "grt-robot-tax")   # both write automation_tax_rate


def apply_overlays(v2p: V2Params, keys) -> tuple[V2Params, list]:
    """Apply overlays in OVERLAYS order (deterministic); returns (params, human-readable notes)."""
    keys = list(keys)
    unknown = [k for k in keys if k not in OVERLAYS]
    if unknown:
        raise KeyError(f"unknown overlay(s): {unknown}")
    if all(k in keys for k in _EXCLUSIVE):
        raise ValueError("cw-robot-tax and grt-robot-tax both set automation_tax_rate — pick one")
    notes = []
    for k in OVERLAYS:               # canonical order, not selection order
        if k in keys:
            v2p, note = OVERLAYS[k].apply(v2p)
            notes.append(note)
    return v2p, notes
