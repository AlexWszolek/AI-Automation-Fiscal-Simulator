"""V2 unified scenario config + the two named default sets (plan principle 1 / note E).

`V2Params` carries every lever — the v1 scenario knobs (diffusion / labor-market / kernel /
government) plus the new v2 behavioral levers (disposition, compute pool, survivor wages, macro
feedbacks). The new levers default to their **v1-reduction** ("off") values, so a bare `V2Params()`
is exactly `DEFAULTS_V1REDUCTION`.

Two named configs, per note E:
- `DEFAULTS_V1REDUCTION` — every behavioral lever off. **C8 (the v1-reduction master invariant) is
  always evaluated against this**, at every phase gate, never the shipped set.
- `DEFAULTS_SHIPPED` — the out-of-box product scenario (reabsorption Rung 1, literature elasticity, …).

`to_v1()` projects a V2Params onto the v1 (LeverParams, DynamicsParams) so dynamics_v2 can reproduce
v1 exactly when the new levers are off (the Phase-0 anchor).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional

from . import levers
from .kernel import KernelParams


@dataclass
class V2Params:
    # ---------------- diffusion (v1 shared scenario knobs) ----------------
    exposure_mapping: str = "percentile"
    logistic_midpoint: float = 0.0
    logistic_steepness: float = 0.6
    cognitive_feasibility: float = 0.5
    physical_feasibility: float = 0.0
    robotics_maturity: float = 0.0
    adoption: float = 1.0
    adoption_path: Optional[list] = None
    # ---------------- diffusion (NEW v2 levers; off = v1) ----------------
    robotics_cognitive_coupling: float = 0.0   # 0 = physical_feasibility used directly (v1)
    robotics_lag: float = 0.0                  # periods robotics trails cognitive
    sector_adoption_mult: float = 1.0          # per-sector multiplier (scalar stand-in; table seam later)
    sector_adoption_ceiling: float = 1.0       # saturation ceiling (1 = none)
    task_job_passthrough: float = 1.0          # 1 = task automation -> full headcount cut (v1)

    # ---------------- disposition router (NEW; off = 100% retained profit = v1) ----------------
    retained_profit_share: float = 1.0
    price_reduction_share: float = 0.0
    survivor_gains_share: float = 0.0
    auto_cost: float = 0.0                      # cost-of-automation fraction of comp (0 = v1)

    # ---------------- compute-capital pool (NEW; inert when auto_cost = 0) ----------------
    offshore_share: float = 0.0
    compute_effective_rate: float = 0.10        # low-tax signature (anchored to Information later)

    # ---------------- labor market (v1 + NEW) ----------------
    ui_weeks: int = 26
    reabsorption_rate: float = 0.0
    reabsorption_rung: int = 0                  # 0 flat-haircut (v1 anchor) | 1 service-floor | 2 routed
    reemployment_haircut: float = 0.30          # Rung 0
    lfp_exit_rate: float = 0.0                  # share of exhausted who exit the labor force (SSDI)
    survivor_elasticity: float = 0.0            # substitution(−) vs complementarity(+); 0 = off

    # ---------------- macro (v1 + NEW) ----------------
    mpc: float = 0.95
    consumption_stickiness: float = 1.0
    marginal_taxable_multiplier: float = 1.0
    demand_multiplier: float = 0.0
    price_passthrough: float = 0.0              # share of price_reduction that deflates P
    productivity_passthrough: float = 0.0       # automation -> GDP/Y growth
    denominator: str = "absolute"               # 'absolute' | 'pct_gdp'

    # ---------------- corporate kernel rates (v1) ----------------
    surplus_capture: float = 1.0                # INERT in V2: it only enters the frozen worker-delta
    # cache (built once at KernelParams()), so changing it does nothing. The disposition router
    # controls corporate (the alias is (1-auto_cost)*retained_profit_share). Asserted ==1.0 in V2.
    dividend_tax_rate: float = 0.188
    passthrough_individual_rate: float = 0.25

    # ---------------- government (v1) ----------------
    state_response: str = "mix"
    interest_rate: float = 0.03
    ubi_annual: float = 0.0
    corp_offset_scale: float = 1.0   # v1-DEPRECATED: superseded by the disposition router (corporate
    #                                  XOR) — would double-apply with disp_factor; asserted ==1.0 in V2.
    consumption_scale: float = 1.0   # v1 post-hoc consumption scale (applied once; not superseded yet)

    # ---------------- simulation ----------------
    n_periods: int = 10

    def kernel_params(self) -> KernelParams:
        return KernelParams(
            surplus_capture=self.surplus_capture, dividend_tax_rate=self.dividend_tax_rate,
            passthrough_individual_rate=self.passthrough_individual_rate,
            mpc=self.mpc, consumption_stickiness=self.consumption_stickiness,
            marginal_taxable_multiplier=self.marginal_taxable_multiplier)

    def lever_params(self) -> levers.LeverParams:
        return levers.LeverParams(
            exposure_mapping=self.exposure_mapping, logistic_midpoint=self.logistic_midpoint,
            logistic_steepness=self.logistic_steepness, cognitive_feasibility=self.cognitive_feasibility,
            physical_feasibility=self.physical_feasibility, adoption=self.adoption,
            robotics_maturity=self.robotics_maturity)

    def to_v1(self):
        """Project onto the v1 (LeverParams, DynamicsParams) — used by the Phase-0 anchor & C8."""
        from .dynamics import DynamicsParams
        dp = DynamicsParams(
            n_periods=self.n_periods, ui_weeks=self.ui_weeks,
            reabsorption_rate=self.reabsorption_rate, reemployment_haircut=self.reemployment_haircut,
            demand_multiplier=self.demand_multiplier, state_response=self.state_response,
            interest_rate=self.interest_rate, adoption_path=self.adoption_path,
            ubi_annual=self.ubi_annual, corp_offset_scale=self.corp_offset_scale,
            consumption_scale=self.consumption_scale, kernel_params=self.kernel_params())
        return self.lever_params(), dp


# C8 binds to this — every behavioral lever off. A bare V2Params() already satisfies it.
DEFAULTS_V1REDUCTION = V2Params()

# Out-of-box product scenario: the realistic-default levers (their magnitudes are literature
# anchors, refined later via the load_* seams). Distinct object from the reduction set (note E).
DEFAULTS_SHIPPED = replace(
    DEFAULTS_V1REDUCTION,
    reabsorption_rung=1,            # service floor, not flat haircut
    survivor_elasticity=0.0,        # stays 0 until Phase 4 wires the channel; bumped then
    retained_profit_share=0.6, price_reduction_share=0.2, survivor_gains_share=0.2,
    auto_cost=0.10, offshore_share=0.25,
    price_passthrough=0.3, productivity_passthrough=0.01,
    lfp_exit_rate=0.03,
)


def is_v1_reduction(p: V2Params) -> bool:
    """True iff every NEW behavioral lever is at its off value (what the C8 harness requires)."""
    r = DEFAULTS_V1REDUCTION
    return all(getattr(p, f) == getattr(r, f) for f in (
        "robotics_cognitive_coupling", "task_job_passthrough", "sector_adoption_mult",
        "sector_adoption_ceiling", "retained_profit_share", "price_reduction_share",
        "survivor_gains_share", "auto_cost", "offshore_share", "reabsorption_rung",
        "lfp_exit_rate", "survivor_elasticity", "price_passthrough", "productivity_passthrough"))
