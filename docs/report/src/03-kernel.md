{{pagebreak}}

# 3. The static kernel: pricing one displaced worker

The kernel answers a single question exactly: if this worker, in this occupation and this state,
loses this wage, what happens to every level of government? The answer is five additive channels,
each an independently inspectable ledger line.

```
Δfiscal(cell) = Δincome_tax + Δpayroll + Δtransfers + Δconsumption_tax + Δcorporate_offset
```

Income tax is computed by exact re-evaluation of the bracket schedules, federal 2025 and state
2026, stratified by filing status, at household income with and without the worker's wage:
T(HH) − T(HH − w). There are no elasticities and no average rates, as the marginal dollars come off
the top brackets first, which is precisely why revenue falls faster than employment when
displacement skews high-wage. Using an average rate here would erase the second thesis of this
report before the model had a chance to produce it.

Payroll applies the FICA schedule to the worker's own wage with the OASDI cap and the additional
Medicare rate, exactly rather than linearized, as the cap makes the schedule kinked in the same
wage range where AI exposure peaks.

Transfers are the reason the kernel integrates rather than averages. Means-tested programs are step
functions and humps: Medicaid eligibility is a cliff, SNAP phases out, the EITC rises and then
falls. The kernel evaluates the baked PolicyEngine entitlement schedules twice, at household income
including unemployment insurance during the UI window and at zero worker earnings after exhaustion,
because these are two distinct fiscal phases and the Medicaid and SNAP step-up mostly arrives at
exhaustion rather than at displacement. It then evaluates them as an expectation over the
within-cell lognormal wage distribution fitted to the OEWS percentiles, not at the cell mean. The
kink test of Section 2.3 is what forces this: the at-mean shortcut understates transfer deltas by
up to a factor of eight in threshold-straddling cells, and does so silently.

Consumption tax applies each state's effective consumption tax rate to the change in taxable
consumption implied by the change in disposable income, with a marginal propensity to consume of
0.95 and a stickiness parameter governing the transition.

The corporate offset is the first appearance of the base-migration thesis. The compensation a firm
stops paying does not vanish, as absent other dispositions it becomes operating surplus, taxed at
the sector's effective corporate rate. The kernel books this at the most generous plausible rate,
meaning full conversion of saved compensation into taxable surplus, and the generosity is
deliberate. The concession on this side is that this is not what firms actually do, since real
firms spend some of the saving on automation and pass some through to prices, both of which are
taxed less than surplus. Booking the optimistic case anyway means the result does not depend on a
pessimistic disposition assumption: even with the most favourable corporate recapture available,
the wedge between labor and capital taxation leaves the government short.

The per-worker deltas from these five channels, across 33,000 cells, seven benefit programs, and
two UI phases, are precomputed once and cached. Everything dynamic in the next section is
stock-flow arithmetic on top of them.
