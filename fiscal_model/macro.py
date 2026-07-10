"""Phase 3 — the macro environment (plan module `macro.py`).

Economy-wide quasi-actor state: price level P, productivity/GDP index Y, survivor-wage index W.
Read by reporting and the denominator toggle; written by the disposition's price-reduction share
and by automation productivity.

**Price feedback follows the A2 rule (the #1 correctness trap):** P only DEFLATES nominal aggregates
for *reporting* (and shrinks the nominal-GDP denominator). It is NEVER injected into the transfer
`np.interp` income argument — a price reduction does not change *nominal* income, only the real value
of unchanged nominal income, so pushing ΔP into the lookup would double-apply the price effect.

Deferred refinements (documented, not in v2 yet): year-boundary statutory threshold re-indexing on the
benefit axis, and consumption-base deflation. W (survivor wage) is inert here — wired in Phase 4.
"""
from __future__ import annotations

from dataclasses import dataclass

from .loaders import COMP_TOTAL_MUSD, VA_TOTAL_MUSD

VA_BASELINE_USD = VA_TOTAL_MUSD * 1e6         # $29.3T nominal GDP base at Y=1, P=1
COMP_TOTAL_USD = COMP_TOTAL_MUSD * 1e6        # $15.0T total labour compensation (the automation base)


@dataclass
class MacroState:
    price_level: float = 1.0     # P
    productivity: float = 1.0    # Y (real-GDP index)
    survivor_wage: float = 1.0   # W — Phase 4


def productivity_index(automated_comp_fraction: float, v2p) -> float:
    """Y_t: the automation productivity dividend. OUTPUT-weighted (the caller passes the automated share
    of the COMPENSATION bill, not headcount — high-value cognitive work automates first, so output runs
    ahead of headcount). NOTE the reachable ceiling: the per-cell comp base sums to ~0.93·COMP_TOTAL
    (different BEA aggregates), so at full automation of the MODELED base fraction ≈ 0.93 and
    Y ≈ 1 + 0.93·productivity_passthrough — not the full 1 + passthrough. Reporting/denominator only;
    the taxable side is the automation-tax lever."""
    return 1.0 + v2p.productivity_passthrough * automated_comp_fraction


def price_level(price_reduction_usd: float, productivity: float, v2p) -> float:
    """P_t: a LEVEL pinned to the current automated stock's annual price reduction relative to real
    GDP (not compounding). P=1 when price_passthrough=0 or there is no price reduction."""
    real_gdp = VA_BASELINE_USD * productivity
    if real_gdp <= 0:
        return 1.0
    deflation = v2p.price_passthrough * (price_reduction_usd / real_gdp)
    return 1.0 - deflation


def nominal_gdp(productivity: float, price: float) -> float:
    """Nominal GDP = real GDP (VA_base · Y) × price level P."""
    return VA_BASELINE_USD * productivity * price
