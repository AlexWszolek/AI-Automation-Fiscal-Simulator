{{pagebreak}}

# 4. The dynamic multi-actor model

The dynamic layer runs the economy forward one year at a time. Workers move through seven states;
firms route the saved wage bill; the compute pool accumulates; survivor wages update under an
explicit budget constraint; the federal government borrows; the states balance; and the demand
consequences of all of it come back one period later as induced layoffs. This section walks one
period in execution order. Appendix A carries the complete equation reference; here we state the
load-bearing mechanics.

## 4.1 Workers: seven states and a diffusion ceiling

Each occupation × state cell tracks seven mutually exclusive stocks — employed, on unemployment
insurance, exhausted (post-UI), reabsorbed (re-employed at a lower wage), exited (out of the labor
force onto SSDI), induced (laid off by second-round demand), and retired (natural attrition of the
long-term unemployed, fiscally delta-neutral because the baseline counterfactual retires too).
Their sum equals baseline employment in every cell in every period — conservation identity C1.

Automation displacement follows a **cumulative diffusion ceiling**, not a compounding rate:

```
g_cell(t) = 1 − (1 − cog·cf) · (1 − rob·pf · min(1, t/robotics_lag))
target(t) = clip(g_cell(t) · adoption(t), 0, 1) · emp0
flow(t)   = clip(target(t) − auto_disp, 0, employed)
```

`adoption(t)` is the *cumulative share of feasible work automated by year t* — a ceiling against
baseline employment, so "60 percent by year ten" means exactly that, not 60 percent per year
compounding on a shrinking base. The two feasibility channels — cognitive (Yale exposure ×
cognitive feasibility) and physical (Webb robot exposure × robotics feasibility) — combine
multiplicatively, and the physical channel ramps in linearly over `robotics_lag` years: physical
automation waits for AI-built industrial capacity.

Displaced workers draw UI for the statutory window, then exhaust; the exhausted are reabsorbed at
`reabsorption_rate` per year into re-employment at `max(origin_wage·(1−haircut), service_floor)` —
the permanent scar the displacement literature measures — or exit the labor force at
`lfp_exit_rate` onto SSDI at $18,000 per year.

## 4.2 Firms: the disposition router

The **firm side is keyed to the cumulative automated stock**, not to worker states — a job stays
automated when its former holder finds other work. Each period the automated stock's compensation
defines the saved bill, and an explicit partition routes it:

```
saved_bill      = Σ_automated comp_per_worker
automation_spend = auto_cost · saved_bill              → the compute-capital pool
net_saving      = saved_bill − automation_spend        (≥ 0 by construction)
net_saving      = retained_profit + price_reduction + survivor_gains     (shares sum to 1)
```

Retained profit is taxed at sector effective corporate rates. Price reductions accrue to consumers
— taxed only through the ~2 percent state consumption channel, the quantitatively dominant leak in
the base-migration story. Survivor gains fund wage raises for the still-employed (below). The
compute pool is taxed at `compute_effective_rate` (5 percent in the AGI presets, per the effective
post-TCJA rate on equipment and software capital), with an optional offshore leakage share that is
zero in every shipped scenario.

## 4.3 Survivors: the funded wage index

Workers who keep their jobs may capture part of the surplus. The mechanical component is **funded**:
the routed `survivor_gains` flow must first pay the maintenance cost of the standing raise before
any increment, and unfundable raises snap back —

```
maintenance = ℓ · wage_bill · (W − 1)          ℓ = compensation loading ≈ 1.4
available   = survivor_gains − maintenance
W ← W + min(available, room)/(ℓ·wage_bill)     room = ℓ·wage_bill·(ceiling − W)
```

with the overflow above the raise ceiling routed to profit or prices by the spillover lever. A
market component responds to labor-market slack with elasticity `survivor_elasticity` (negative:
substitution pushes wages down; positive: complementarity pulls them up), evaluated on lagged
slack so the system never solves a within-period fixed point. Survivor raises are re-taxed through
the exact bracket schedules — the one channel where displacement *creates* labor-side revenue.

## 4.4 Government: one borrower, fifty-one balancers

The federal ledger nets every labeled flow — income and payroll losses, transfer and UI outlays,
UI benefit taxation, the corporate offset, survivor wage taxes, compute-pool tax, robot tax, UBI
gross and recapture, SSDI — into a deficit that accumulates into debt at the federal interest
rate. The reconciliation of that deficit to its components is asserted every period (C6).

The states cannot borrow. Each period, each state's revenue loss net of its recoveries defines a
gap that must close: rate increases on the remaining labor-income base up to a feasibility cap,
then forced spending cuts for whatever the cap leaves. The closure is solved per state (one Newton
step on the post-recomputation base, residual asserted ≈ 0, identity C7), and its real economy
consequences — spending cuts at a government-spending multiplier, rate hikes at the household
MPC — are not free: they enter the demand channel below, *in the state where they happen*.

## 4.5 Demand: a level-targeting controller

Second-round demand is modeled as a stock, not a ratchet. The standing net income withdrawal —
take-home pay lost by every non-employed stock, minus UI and transfers actually received, minus
UBI net of recapture, minus survivor raises — defines a target level of induced layoffs through an
Okun-style multiplier; the induced stock adjusts toward that target with a one-period lag, and
*releases* workers back when the withdrawal shrinks (a UBI visibly re-employs induced workers).
The loop gain is provably below one at every shipped configuration, so the feedback converges
geometrically instead of spiraling — and the model asserts this at construction rather than
trusting it.

## 4.6 Prices and productivity

Automation deflates prices through the price-reduction disposition (pass-through configurable) and
raises real output through an output-weighted productivity dividend (full automation of the
compensation bill raises GDP by `productivity_passthrough`). Both are **reporting-layer** effects
by design: the price level deflates real and percent-of-GDP columns but is never injected into
nominal tax computations — a discipline (the "A2 rule") that prevents double-counting deflation
through bracket schedules that are nominally indexed in reality. The consequences of this choice
for external comparability are quantified in Section 9.
