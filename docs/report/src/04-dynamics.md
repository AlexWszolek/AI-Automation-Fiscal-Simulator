{{pagebreak}}

# 4. The dynamic multi-actor model

The dynamic layer runs the economy forward one year at a time. Workers move through seven states,
firms route the saved wage bill, the compute pool accumulates, survivor wages update under an
explicit budget constraint, the federal government borrows, the states balance, shareholders accrue
a claim they realize only slowly, and the demand consequences of all of it come back one period
later as induced layoffs. This section walks one period in execution order and states the
load-bearing mechanics; Appendix A carries the complete equation reference.

## 4.1 Workers: a ceiling, not a rate

Each occupation × state cell tracks seven mutually exclusive stocks: employed, on unemployment
insurance, exhausted after UI, reabsorbed into re-employment at a lower wage, exited from the labor
force onto SSDI, induced out by second-round demand, and retired through natural attrition of the
long-term unemployed. The retired stock is fiscally delta-neutral, as the baseline counterfactual
retires too. Their sum equals baseline employment in every cell in every period, which is
conservation identity C1.

Automation displacement follows a cumulative diffusion ceiling rather than a compounding rate:

```
g_cell(t) = 1 − (1 − cog·cf) · (1 − rob·pf · min(1, t/robotics_lag))
target(t) = clip(g_cell(t) · adoption(t), 0, 1) · emp0
flow(t)   = clip(target(t) − auto_disp, 0, employed)
```

Here `adoption(t)` is the cumulative share of feasible work automated by year t, measured as a
ceiling against baseline employment, so "60 percent by year ten" means exactly that rather than 60
percent per year compounding on a shrinking base. The distinction is not cosmetic, as the
compounding reading of the same headline number produces a materially larger shock from an
identical source quote. The two feasibility channels, cognitive (Yale exposure × cognitive
feasibility) and physical (Webb robot exposure × robotics feasibility), combine multiplicatively,
and the physical channel ramps in linearly over `robotics_lag` years, as physical automation waits
for AI-built industrial capacity.

The path of `adoption(t)` is linear between anchored points. Where a source publishes only endpoints,
such as half of exposed work automated over a decade, a straight ramp is the minimal-assumption
reading, as smooth S-shaped families fitted to those same endpoints require shape constants no
source pins down, and the families the diffusion literature suggests were measured to move mid-path
adoption more than any defensible choice among them could justify. Section 10 quantifies what the
linear convention costs. Where a source publishes its own trajectory, the ramp threads
piecewise-linearly through the published points instead, so every knot is a number in the source
text and none is a fitting parameter.

Displaced workers draw UI for the statutory window and then exhaust. The exhausted are reabsorbed at
`reabsorption_rate` per year into re-employment at `max(origin_wage·(1−haircut), service_floor)`,
which is the permanent scar the displacement literature measures, or they exit the labor force at
`lfp_exit_rate` onto SSDI at $18,000 per year.

The refuge those workers move into is finite, and this is one of the few places where the model's
own structure produces a result rather than carrying an assumption. The re-employed move into
low-exposure service work, which is the same occupation set the service floor prices, and that work
is itself automatable. The effective reabsorption rate therefore scales by the un-automated share of
low-exposure employment, so under AGI-grade scenarios the refuge shrinks and reabsorption chokes
off, with capacity falling toward the share of care and dexterity work that even full-feasibility
robotics cannot reach.

The refuge wage is also contested, as two optional forces move the re-employed wage index each year.
A Baumol pull (`reab_wage_baumol`) makes the work humans still do expensive as everything else gets
cheap, while a crowding pressure (`reab_wage_crowding`) has displaced supply flooding into service
work bid its wage down against last year's slack. When the Baumol pull dominates, re-employed wages
rise even amid mass displacement, which is abundance reaching labor through the price of human
service work. Both ship at zero, as the presets are calibrated without them, and the fiscal side
re-prices all six channels at the shifted wage, cliffs included.

## 4.2 Firms: where the saved wage bill actually goes

The firm side is keyed to the cumulative automated stock rather than to worker states, as a job
stays automated when its former holder finds other work. Each period the automated stock's
compensation defines the saved bill, and an explicit partition routes it:

```
saved_bill      = Σ_automated comp_per_worker
automation_spend = auto_cost · saved_bill              → the compute-capital pool
net_saving      = saved_bill − automation_spend        (≥ 0 by construction)
net_saving      = retained_profit + price_reduction + survivor_gains     (shares sum to 1)
```

Retained profit is taxed at sector effective corporate rates. Price reductions accrue to consumers
and are taxed only through the roughly 2 percent state consumption channel, which makes them the
quantitatively dominant leak in the base-migration story. Survivor gains fund wage raises for the
still-employed, treated below. The compute pool is taxed at `compute_effective_rate`, set to 5
percent in the AGI presets after the effective post-TCJA rate on equipment and software capital,
with an optional offshore leakage share that is zero in every shipped scenario.

## 4.3 Survivors: raises have to be paid for

Workers who keep their jobs may capture part of the surplus, but the mechanical component is funded
rather than assumed. The routed `survivor_gains` flow must first pay the maintenance cost of the
standing raise before any increment, and unfundable raises snap back:

```
maintenance = ℓ · wage_bill · (W − 1)          ℓ = compensation loading ≈ 1.4
available   = survivor_gains − maintenance
W ← W + min(available, room)/(ℓ·wage_bill)     room = ℓ·wage_bill·(ceiling − W)
```

Overflow above the raise ceiling routes to profit or prices through the spillover lever. A market
component responds to labor-market slack with elasticity `survivor_elasticity`, negative when
substitution pushes wages down and positive when complementarity pulls them up, evaluated on lagged
slack so the system never solves a within-period fixed point. Survivor raises are re-taxed through
the exact bracket schedules, which makes this the one channel where displacement creates labor-side
revenue rather than destroying it.

## 4.4 Government: one borrower, fifty-one balancers

The federal ledger nets every labeled flow into a deficit that accumulates into debt at the federal
interest rate: income and payroll losses, transfer and UI outlays, UI benefit taxation, the
corporate offset, survivor wage taxes, compute-pool tax, robot tax, UBI gross and recapture, and
SSDI. The reconciliation of that deficit to its components is asserted every period as identity C6.

The states cannot borrow. Each period, each state's revenue loss net of its recoveries defines a gap
that must close, met by rate increases on the remaining labor-income base up to a feasibility cap
and then by forced spending cuts for whatever the cap leaves. The closure is solved per state with
one Newton step on the post-recomputation base, with the residual asserted at approximately zero as
identity C7. Its real-economy consequences are not free: spending cuts enter at a government
spending multiplier and rate hikes at the household MPC, and both feed the demand channel below in
the state where they happen.

## 4.5 Shareholders: a claim taxed only when someone sells

The disposition router books corporate tax, dividend tax, and pass-through individual tax on the
routed surplus. What it leaves at zero is the undistributed share: after-corporate-tax retained
earnings that never flow out as dividends, capitalize into equity value, and are taxed only when
somebody sells. That is a first-order federal revenue line, and this channel prices it.

The obvious objection is that equity prices cannot be projected, and this channel never projects
them. It prices the incremental claim conditionally, in the same way the corporate offset already
steelmans full conversion of saved compensation into taxable surplus. The undistributed earnings the
automated stock adds are computed per cell on the corporate offset's own construction with taxes and
payout removed; automation-tax and sovereign-fund instruments are conservatively paid from that same
pool; a capitalization multiple converts each increment to the permanent earnings level, never the
standing stream, into paper wealth; and realizations draw the accrued stock down at a measured rate:

```
E_t      = max(0, undistributed_t − automation_tax − swf_revenue)
R_t      = cg_realization_rate · G_{t−1}                      (t = 0 realizes nothing)
G_t      = G_{t−1} + equity_taxable_share · equity_pe_multiple · max(0, E_t − E_{t−1}) − R_t
cg_tax_t = shareholder_eff_rate · R_t                         → federal revenue (C6)
```

Every parameter is externally measured: the long-run market price-to-earnings mean rather than
today's richer multiple, which is the conservative convention; the taxable-account share of US
corporate equity; the measured fraction of the accrued gain stock realized per year; and the average
effective rate on realized gains. None is calibrated against anything the model targets. The
multiple is the one input no source can pin, and it is not where the answer comes from, as the
bottleneck is the measured leakage chain, which is why the finding survives generous multiples. The
result is conditional accounting rather than a forecast: if the surplus lands as permanent corporate
earnings, this is what the current shareholder-side regime collects on it. Section 7.13 reports the
magnitude and why it is small.

## 4.6 Demand: a stock, not a ratchet

Second-round demand is modeled as a level rather than a one-way accumulation. The standing net
income withdrawal, meaning take-home pay lost by every non-employed stock less UI and transfers
actually received, less UBI net of recapture, less survivor raises, defines a target level of
induced layoffs through an Okun-style multiplier. The induced stock adjusts toward that target with
a one-period lag and releases workers back when the withdrawal shrinks, which is why a UBI visibly
re-employs induced workers rather than merely offsetting their income. The loop gain is provably
below one at every shipped configuration, so the feedback converges geometrically instead of
spiraling, and the model asserts this at construction rather than trusting it.

## 4.7 Prices and productivity stay in the reporting layer

Automation deflates prices through the price-reduction disposition, with pass-through configurable,
and raises real output through an output-weighted productivity dividend, under which full automation
of the compensation bill raises GDP by `productivity_passthrough`. Both are reporting-layer effects
by design: the price level deflates real and percent-of-GDP columns but is never injected into
nominal tax computations. This discipline, the A2 rule, prevents double-counting deflation through
bracket schedules that are nominally indexed in reality. The concession on this side is that it also
means the model cannot represent bracket creep or its reverse, which is a real fiscal channel in a
deflationary scenario. Section 9 quantifies what the choice costs in external comparability.
