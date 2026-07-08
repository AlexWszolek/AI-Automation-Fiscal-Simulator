{{pagebreak}}

# 2. Data

The model is anchored to the 2024 United States economy as measured by the statistical agencies,
with every input file carrying control totals that the loader asserts on every run — a load that
does not reconcile to the published aggregates fails before a single scenario is computed.

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

The loader asserts, among others: total employment 163.2 million; total compensation
$15,049 billion; value added (GDP proxy) $29,298 billion; federal receipts
${{n:baselines.fed_revenue0_B|,.1f}} billion; state and local receipts
${{n:baselines.state_revenue0_B|,.1f}} billion; Medicaid outlays $938.2 billion; corporate profits
before tax $3,722 billion. The baseline federal deficit is anchored at
${{n:baselines.fed_deficit0_B|,.0f}} billion. These are the denominators for every percentage in
this report.

## 2.3 Validation gates

Four checks connect the constructed inputs to independent references.

- **Tax cross-check.** The hand-rolled bracket engine is compared to PolicyEngine-US on a grid of
  incomes, states, and filing statuses: income tax agrees within 2.5 percent (a 2024/2025 bracket
  vintage gap), payroll tax exactly (excluding state disability insurance, which the model does
  not levy).
- **The kink test.** Fiscal deltas computed at the within-cell *mean* wage understate the
  integrated delta by a factor of 2.7–7.8 in cells whose wage distribution straddles a
  means-tested eligibility threshold. This is the empirical justification for Section 3's
  within-cell integration: the EITC hump, the SNAP phase-out, and the Medicaid cliff are exactly
  where displacement lands, and evaluating at the mean silently steps over them.
- **Aggregate transfer reconciliation.** Population-weighting the baked benefit entitlements
  reproduces the working-family program aggregates (EITC plus refundable CTC: $228.8 billion
  actual) and deliberately undershoots the aged/disabled-dominated programs (Medicaid, SSI), which
  the working-household bake does not represent. The reconciliation validates marginal mechanics,
  not program levels; Section 10 carries the caveat.
- **The t = 0 base-rate gate.** Before any displacement, the dynamic model must reproduce the
  published base-linkage effective rates — individual income receipts at 19.5 percent of the wage
  base, with payroll and corporate rates matched to their published rows — tying the simulated
  economy's starting point to the national accounts.

## 2.4 From files to per-worker deltas

The construction pipeline joins occupation × state wage distributions to household archetypes
(filing status, household income, number of children from ACS PUMS), evaluates the five kernel
channels of Section 3 on a frozen quadrature grid over each cell's lognormal wage distribution, and
caches the result: one vector of per-worker fiscal deltas per (occupation, state) cell, by channel
and by benefit program. The dynamic layer never re-derives these; it prices worker *stocks* against
frozen per-worker deltas and recomputes only what the levers actually move (survivor wages,
re-employment wages, and the government ledgers). That split is what makes a 33,000-cell model run
a full scenario in a quarter of a second.
