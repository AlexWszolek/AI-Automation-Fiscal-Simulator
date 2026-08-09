{{pagebreak}}

# 2. Data

The model is anchored to the 2024 United States economy as the statistical agencies measured it.
Every input file carries control totals that the loader asserts on every run, so a load that does
not reconcile to the published aggregates fails before a single scenario is computed.

## 2.1 Sources

| Input | Source and vintage | Role |
|---|---|---|
| Employment × industry matrix | BLS OEWS 2024, interior aligned to BEA 2024 industry totals | 833 occupations × 71 industries; employment and compensation |
| State wage distributions | BLS OEWS May 2025 | 51 jurisdictions × 822 occupations; mean wages and p10–p90 percentiles |
| AI exposure | Yale Budget Lab PCA | standardized cognitive-exposure score per occupation |
| Robot exposure | Webb (2020) robot-patent measure | physical-automation feasibility per occupation |
| Capital income by sector | BEA 2024 NIPA | value added, capital share, corporate profits, effective corporate rates |
| Government fiscal accounts | BEA 2024 national accounts | receipts by stream (federal and state-local), 17 transfer programs, base-linkage effective rates |
| Consumption tax base | state PCE and taxable-base analysis | effective consumption tax rate per state |
| Household archetypes | ACS PUMS 2024 (WGTP-weighted) | filing-status mix and household income by occupation × state; children distribution |
| Tax schedules | 2025 federal / 2026 state brackets; FICA parameters | the hand-rolled tax engine |
| Benefit lookup | PolicyEngine-US, baked offline | means-tested benefits as a function of (state, filing, children, income) |

## 2.2 Control totals

The loader asserts, among others: total employment 163.2 million; total compensation $15,049
billion; value added (GDP proxy) $29,298 billion; federal receipts
${{n:baselines.fed_revenue0_B|,.1f}} billion; state and local receipts
${{n:baselines.state_revenue0_B|,.1f}} billion; Medicaid outlays $938.2 billion; corporate profits
before tax $3,722 billion. The baseline federal deficit is anchored at
${{n:baselines.fed_deficit0_B|,.0f}} billion. These are the denominators for every percentage in
this report.

The dynamic model runs on the 33,369 occupation × state cells with complete data, meaning wages,
exposure scores, household archetypes, and state tax rules all present, which covers 154.0 million
of the 163.2 million measured workers, or 94 percent. The remainder sit in suppressed or unmatched
cells and are excluded rather than imputed, as an imputed cell would carry a fiscal delta that no
data supports while being indistinguishable in the output from one that is measured. Every modeled
percentage therefore uses the 154.0 million baseline, not the 163.2 million published one.

## 2.3 Validation gates

Four checks connect the constructed inputs to independent references, and the second of them is the
reason the kernel is built the way it is.

The tax cross-check compares the hand-rolled bracket engine to PolicyEngine-US on a grid of
incomes, states, and filing statuses. Income tax agrees within 2.5 percent, a gap explained by the
2024 versus 2025 bracket vintages, and payroll tax agrees exactly, excluding state disability
insurance, which the model does not levy.

The kink test measures what is lost by evaluating a cell at its average worker. Fiscal deltas
computed at the within-cell mean wage understate the integrated delta by a factor of 2.7 to 7.8 in
cells whose wage distribution straddles a means-tested eligibility threshold. This is the empirical
justification for the within-cell integration of Section 3: the EITC hump, the SNAP phase-out, and
the Medicaid cliff sit exactly where displacement lands, and evaluating at the mean steps over them
without leaving any trace in the output that it has done so.

Aggregate transfer reconciliation population-weights the baked benefit entitlements and reproduces
the working-family program aggregates, with EITC plus refundable CTC at $228.8 billion against the
actual, while deliberately undershooting the aged- and disabled-dominated programs, namely Medicaid
and SSI, which a working-household bake does not represent. The reconciliation validates marginal
mechanics rather than program levels, and Section 10 carries the caveat.

The t = 0 base-rate gate requires that, before any displacement, the dynamic model reproduce the
published base-linkage effective rates: individual income receipts at 19.5 percent of the wage base,
with payroll and corporate rates matched to their published rows. This ties the simulated economy's
starting point to the national accounts rather than to the model's own internal consistency.

## 2.4 From files to per-worker deltas

The construction pipeline joins occupation × state wage distributions to household archetypes,
taking filing status, household income, and number of children from ACS PUMS, then evaluates the
five kernel channels of Section 3 on a frozen quadrature grid over each cell's lognormal wage
distribution, and caches the result as one vector of per-worker fiscal deltas per occupation-state
cell, by channel and by benefit program.

The dynamic layer never re-derives those deltas. It prices worker stocks against the frozen
per-worker values and recomputes only what the levers actually move, which is survivor wages,
re-employment wages, and the government ledgers. That split is what lets a 33,000-cell model run a
full scenario in a quarter of a second, and the speed is not cosmetic, as it is what makes the
Monte Carlo sampling in Section 7 affordable at all.
