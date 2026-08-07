"""The country seam — the facts that vary between national fiscal systems.

Everything the engine does is country-agnostic in *structure*: pricing a displaced worker's fiscal
delta across five channels, the 7-state worker stock-flow, the disposition router, the survivor and
reabsorption engines, the MC/tornado apparatus, the conservation invariants. What varies is the
parameterisation, and until now those variations were assumptions baked into module bodies rather
than named facts.

This module names them, with the **US as the reference implementation**. Nothing here changes any
US number — `US` restates today's behaviour. The point is that adding a second country becomes
*additive* rather than a rewrite, and that the genuinely structural differences (below) become
explicit decisions instead of silent assumptions.

The structural difference that matters most, discovered while researching a Korea port
(`docs/research/korea-fiscal-system.md`): **the subnational layer is not universal.** The US model's
signature mechanism is that 51 states must balance within-year while the federal government need
not, so state austerity feeds back as layoffs (`government.close_state_gaps`). Korea has no
analogue — local government is majority-funded by statutory central transfers fixed as a share of
national internal taxes (19.24% Local Share Tax + 20.79% Local Education Subsidy = 40.03%), so a
national revenue shock propagates to local budgets *by formula, with no decision anywhere*. That is
a different mechanism, not a different parameter, which is why it is a `Country` field.

A second country must supply: raw data files in the loader's shapes, a payroll component builder,
its subnational mode, its transfer programme set, grounding anchors, and its macro aggregates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from . import macro, rates, transfers

# ---------------------------------------------------------------------------- subnational modes
# How a national revenue shock reaches subnational budgets.
SUBNATIONAL_BALANCED_BUDGET = "balanced_budget"   # US: each unit must erase its gap within-year
SUBNATIONAL_FORMULA_TRANSFER = "formula_transfer"  # KR: transfers are a fixed share of national tax
SUBNATIONAL_NONE = "none"                          # no modelled subnational layer


@dataclass(frozen=True)
class Country:
    """The country-varying facts. `US` below is the reference implementation."""

    key: str
    name: str

    # ---- data ----
    raw_files: tuple                       # expected files in data/raw for this country
    currency_code: str
    currency_symbol: str
    money_unit_label: str                  # how headline money figures are labelled

    # ---- payroll / social insurance ----
    # payroll_params DataFrame -> ordered tuple[rates.PayrollComponent]; order is part of the
    # bit-parity contract (the sum is left-associative), so a country pins its own order.
    payroll_components: Callable

    # ---- subnational fiscal structure ----
    subnational_mode: str
    subnational_label: str                 # "state", "province", "local government"
    # `formula_transfer` only: the statutory share of national internal taxes passed through.
    subnational_transfer_share: Optional[float] = None

    # ---- transfers ----
    transfer_programs: tuple = ()

    # ---- macro / fiscal anchors ----
    va_baseline: float = 0.0               # nominal value-added base at Y=1, P=1
    comp_total: float = 0.0                # total labour compensation (the automation base)
    baseline_deficit_bn: float = 0.0       # national baseline deficit, headline units

    # ---- grounding ----
    # Comparator anchors are entirely country-specific (`grounding.ANCHORS` is US: CBO, Apollo,
    # Walmart, the US military). A second country supplies its own or gets no grounding line.
    grounding_anchors: dict = field(default_factory=dict)

    @property
    def has_balanced_budget_subnational(self) -> bool:
        """Whether `government.close_state_gaps` applies — the asymmetric-amplifier mechanism."""
        return self.subnational_mode == SUBNATIONAL_BALANCED_BUDGET


US = Country(
    key="us",
    name="United States",
    raw_files=(
        "occ_industry_matrices_v2_aligned.xlsx",
        "occupation_ai_exposure.xlsx",
        "robot_exposure_by_soc.xlsx",
        "capital_income_by_sector.xlsx",
        "government_fiscal_accounts.xlsx",
        "state_occupation_numbers_oews.xlsx",
        "taxable_consumption_base_by_state.xlsx",
        "household_archetypes_by_state.xlsx",
        "tax_side_schedule.xlsx",
        "cbo_baseline_2026.csv",
    ),
    currency_code="USD",
    currency_symbol="$",
    money_unit_label="$B",
    payroll_components=rates.us_payroll_components,
    subnational_mode=SUBNATIONAL_BALANCED_BUDGET,
    subnational_label="state",
    transfer_programs=tuple(transfers.PROGRAMS),
    va_baseline=macro.VA_BASELINE_USD,
    comp_total=macro.COMP_TOTAL_USD,
    baseline_deficit_bn=1833.0,            # government.BASELINE_FED_DEFICIT_BUSD (CBO FY2024)
)

REGISTRY = {US.key: US}


def get(key: str = "us") -> Country:
    if key not in REGISTRY:
        raise ValueError(f"unknown country {key!r}; known: {sorted(REGISTRY)}")
    return REGISTRY[key]
