{{pagebreak}}

# 5. Correctness discipline

A model whose output is an accounting claim should be held to accounting standards. Two mechanisms
do that here: conservation identities asserted at runtime, and an exact reduction anchor.

## 5.1 The conservation battery

Nine identities hold on every period of every run, including every Monte Carlo draw sampled for
this report, and including the presentation layer, as the fiscal summary tables in Section 7 assert
their own reconciliation before rendering.

C1, headcount, requires the seven worker stocks to sum to baseline employment in every occupation ×
state cell in every period, so no worker is created, destroyed, or double-counted. C2, the
disposition partition, requires that `automation_spend + retained_profit + price_reduction +
survivor_gains = saved_bill` per sector per period, so every saved dollar has exactly one
destination. C3 requires pool tax to equal the domestic inflow times the effective rate, which
meters leakage rather than losing it. C4 requires real aggregates to equal nominal divided by the
price level, so the price channel cannot double-apply. C5c requires survivor wage cost plus
overflows to equal the routed survivor gains exactly, in every branch of the funding logic, so
raises cannot be paid out of nothing.

C6, federal reconciliation, requires the federal deficit to equal the signed sum of its nineteen
labeled components. Any new fiscal flow not added to the reconciliation breaks the build, which is
the point, as the ledger cannot silently drop a leg. The shareholder windfall line of Section 4.5
was added under exactly that constraint. C-sh extends the same treatment to the shareholder stock
ledger: the accrued windfall stock moves by capitalized increment minus realizations, realizations
are the measured rate times last period's stock, and the tax is the effective rate times
realizations, all asserted per period, so the channel cannot book revenue without a stock to draw it
from and the stock cannot go negative. C6-state and C7 require each state's revenue change to be
composed from its labeled parts before the balanced-budget solve, and require the solve to close the
gap to numerical residual zero.

C8, reduction, requires that with every behavioral lever at its off value the full multi-actor
system reproduce the static kernel's dynamic wrapper bit for bit. Not approximately: the test is
exact float equality across output columns, and it is differential, running v2 against v1 on the
same inputs, so a shared re-base cannot mask a divergence.

## 5.2 Why C8 is the load-bearing one

Every behavioral mechanism in Section 4 is gated by a lever whose off value removes it exactly.
That means the elaborate system is pinned, at a reachable point of its own configuration space, to
a small model that can be checked by hand against the national accounts through the t = 0 base-rate
gate of Section 2.3. Complexity added above that anchor has to justify itself lever by lever, and a
regression anywhere in the machinery is caught as a bit-level diff, including refactors that merely
change floating-point operation order.

The Monte Carlo machinery is held to the same standard. The fast path that re-binds lever values
onto a prebuilt model is verified to reproduce fresh construction exactly, so the uncertainty bands
in this report are a thousand real model runs rather than an approximation of a thousand runs.

## 5.3 Test surface

The repository carries 434 regression tests: the conservation battery across lever sweeps, numeric
anchors for each kernel channel, the displacement-literature behavioral pins (attrition lowers the
deficit; a job stays automated after its worker is reabsorbed; a stationary shock produces a
stationary induced-layoff stock), sampler domain properties for the Monte Carlo, UI-grid
representability and provenance completeness for every scenario preset, and the C8 sweep. The
artifact pipeline that generated every number in this document is seeded and re-runs
deterministically, and its build stamp appears in the footer of every page.
