"""Phase 2 — the compute-capital pool actor (plan module `compute_pool.py`).

Receives the automation spend routed out by the disposition router. Its fiscal signature is
**parameterized** (the low-tax / partly-offshore character is not in any data file — domestic tech
is actually high-taxed, Information ≈ 28.8%): a fraction `offshore_share` of the spend leaks out of
the US base entirely, and the domestic remainder is taxed at a low `compute_effective_rate`.

The tax it generates is the mechanical counterpart of base migration — far below the labor + corporate
tax on the compensation it replaced — so federal revenue falls as comp migrates here. (Low labor share:
the small payroll/income tax from compute-sector workers is omitted in v2; a later refinement.)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ComputePoolResult:
    inflow: float          # = automation_spend (C3 flow balance)
    offshore_leak: float   # leaves the US tax base entirely
    domestic: float        # taxable base
    tax_fed: float         # federal revenue from the pool (lightly taxed)


def route_to_compute_pool(automation_spend: float, v2p) -> ComputePoolResult:
    inflow = float(automation_spend)
    offshore_leak = v2p.offshore_share * inflow
    domestic = inflow - offshore_leak
    tax_fed = domestic * v2p.compute_effective_rate
    return ComputePoolResult(inflow, offshore_leak, domestic, tax_fed)
