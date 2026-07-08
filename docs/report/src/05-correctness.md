{{pagebreak}}

# 5. Correctness discipline

A model whose output is an accounting claim should be held to accounting standards. Two mechanisms
do that here: conservation identities asserted at runtime, and an exact reduction anchor.

## 5.1 The conservation battery

Eight identities hold on every period of every run — including every Monte Carlo draw sampled for
this report, and including the presentation layer (the fiscal summary tables in Section 7 assert
their own reconciliation before rendering):

- **C1 (headcount).** The seven worker stocks sum to baseline employment in every occupation ×
  state cell, every period. No worker is created, destroyed, or double-counted.
- **C2 (disposition partition).** `automation_spend + retained_profit + price_reduction +
  survivor_gains = saved_bill`, per sector, per period — every saved dollar has exactly one
  destination.
- **C3 (compute pool).** Pool tax equals the domestic inflow times the effective rate; leakage is
  metered, not lost.
- **C4 (deflation).** Real aggregates equal nominal divided by the price level — the price channel
  cannot double-apply.
- **C5c (funded raises).** Survivor wage cost plus overflows exactly equals the routed survivor
  gains, in every branch of the funding logic — raises cannot be paid out of nothing.
- **C6 (federal reconciliation).** The federal deficit equals the signed sum of its thirteen
  labeled components. Any new fiscal flow that is not added to the reconciliation breaks the
  build, which is the point: the ledger cannot silently drop a leg.
- **C6-state / C7 (state composition and closure).** Each state's revenue change is composed from
  its labeled parts before the balanced-budget solve, and the solve closes the gap to numerical
  residual zero.
- **C8 (reduction).** With every behavioral lever at its off value, the full multi-actor system
  reproduces the static kernel's dynamic wrapper **bit-for-bit** — not approximately: the test is
  exact float equality across output columns, and it is differential (v2 against v1 run on the
  same inputs), so shared re-bases cannot mask a divergence.

## 5.2 Why C8 matters

Every behavioral mechanism in Section 4 is gated by a lever whose off value removes it exactly.
That means the elaborate system is pinned, at a reachable point of its configuration space, to a
small model that can be checked by hand against the national accounts (the t = 0 base-rate gate of
Section 2.3). Complexity added above that anchor must justify itself lever by lever, and a
regression anywhere in the machinery — including refactors that merely change floating-point
operation order — is caught as a bit-level diff. The Monte Carlo machinery is held to the same
standard: the fast path that re-binds lever values onto a prebuilt model is verified to reproduce
fresh construction exactly, so 1,000-draw uncertainty bands are 1,000 real model runs, not an
approximation of them.

## 5.3 Test surface

The repository carries 245 regression tests: the conservation battery across lever sweeps, numeric
anchors for each kernel channel, the displacement-literature behavioral pins (attrition lowers the
deficit; a job stays automated after its worker is reabsorbed; a stationary shock produces a
stationary induced-layoff stock), sampler domain properties for the Monte Carlo, UI-grid
representability and provenance completeness for every scenario preset, and the C8 sweep. The
artifact pipeline that generated every number in this document is seeded and re-runs
deterministically; its build stamp is in the footer of every page.
