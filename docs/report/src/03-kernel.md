{{pagebreak}}

# 3. The static kernel: pricing one displaced worker

The kernel answers a single question exactly: *if this worker, in this occupation and this state,
loses this wage, what happens to every level of government?* Five additive channels, each an
independently inspectable ledger line.

```
Δfiscal(cell) = Δincome_tax + Δpayroll + Δtransfers + Δconsumption_tax + Δcorporate_offset
```

**Income tax** is computed by exact re-evaluation of the bracket schedules — federal 2025 and
state 2026, stratified by filing status — at household income with and without the worker's wage:
T(HH) − T(HH − w). No elasticities, no average rates; the marginal dollars come off the top
brackets first, which is precisely why revenue falls faster than employment when displacement
skews high-wage.

**Payroll** applies the FICA schedule to the worker's own wage with the OASDI cap and the
additional Medicare rate — exact, not linearized, because the cap makes the schedule kinked in
exactly the wage range where AI exposure peaks.

**Transfers** are the reason the kernel integrates rather than averages. Means-tested programs are
step functions and humps: Medicaid eligibility is a cliff, SNAP phases out, the EITC rises then
falls. The kernel evaluates the baked PolicyEngine entitlement schedules at household income
*including* unemployment insurance during the UI window and at zero worker earnings after
exhaustion — two distinct fiscal phases, because the Medicaid/SNAP step-up mostly arrives at UI
exhaustion, not at displacement. And it evaluates them as an expectation over the within-cell
lognormal wage distribution fitted to the OEWS percentiles, not at the cell mean: the kink test
(Section 2.3) shows the at-mean shortcut understates transfer deltas by up to a factor of eight in
threshold-straddling cells.

**Consumption tax** applies each state's effective consumption tax rate to the change in taxable
consumption implied by the change in disposable income, with a marginal propensity to consume of
0.95 and a stickiness parameter for the transition.

**The corporate offset** is the first appearance of the base-migration thesis: the compensation a
firm stops paying does not vanish — absent other dispositions it becomes operating surplus, taxed
at the sector's effective corporate rate. The kernel books this at the most generous plausible
rate (full conversion of saved compensation to taxable surplus) as a deliberate steelman: even
with the *most* optimistic corporate recapture, the wedge between labor and capital taxation
leaves the government short.

The per-worker deltas from these five channels — 33,000 cells, seven benefit programs, two UI
phases — are precomputed once and cached. Everything dynamic in the next section is stock-flow
arithmetic on top of them.
