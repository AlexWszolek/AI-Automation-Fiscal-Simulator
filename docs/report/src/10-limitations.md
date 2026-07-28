{{pagebreak}}

# 10. Simplifications and biases

**The deliberate simplifications of this model.** There are two significant structural decisions
that this model makes. First, capital income does not spend: retained profit reaches the economy
only as tax — corporate tax, and for the undistributed remainder the shareholder realization
channel of Section 4.5 — and never as shareholder consumption or investment, with the latter likely
being a significant source of economic growth. Second, there is no task
creation: displaced workers re-enter only through a fixed re-employment rate into a finite set of
low-exposure occupations; automation never endogenously creates new kinds of work. Both of these
decisions are deliberate. The history of automation shows that offsets will eventually arrive, but
this model asks what the fiscal impacts will be if the offsets arrive late or never. Fiscal
authorities will still need to be able to respond to this scenario, but consider the numbers to be
in a world with no offsets.

Following the practice we admired in the Windfall Trust's paper, every known simplification is
listed with its direction of bias on the headline (the federal fiscal gap). "Overstates" means the
true gap is likely smaller than modeled; "understates" means larger.

| Simplification | Direction of bias on the fiscal gap |
|---|---|
| No behavioral response of automation to the robot tax (Korea evidence: a 2pp tax-credit cut reduced robot installations 28%) | overlay recoveries are upper bounds; scenario paths unaffected at shipped tax = 0 |
| No monetary-policy block (no Fed response to the demand shock) | overstates in crisis scenarios (dm calibrated to partially compensate) |
| Within-job augmentation not represented (a worker made more productive but retained) | overstates where augmentation dominates (the Brynjolfsson preset carries it only via survivor shares) |
| Corporate channel books full conversion of saved compensation to taxable surplus | **understates** (a deliberate steelman of the recovery) |
| Pass-through (proprietor) capital tax routed federal-only | overstates the federal share, understates the state share |
| Shareholder channel omits the 1 percent buyback excise (IRC §4501, JCT-scored $74B/10y) and all state-side taxation of dividends and realized gains (following the same federal-only convention as pass-through capital) | understates the channel's recovery, therefore **overstates** the gap — both omissions are small against a channel that is itself near-mute |
| Shareholder capitalization uses a disclosed price/earnings convention (the long-run market mean, not the current richer multiple) rather than a modeled equity price | direction depends on the multiple; the finding is insensitive to it because the binding constraint is the measured taxable-holder × realization chain, not the multiple (§4.5) |
| UI parameters national (45% replacement, 26 weeks, $20k cap), not per-state DOL schedules | direction ambiguous, small |
| Transfer federal/state splits flat (e.g. Medicaid 65/35) vs. actual FMAP 50–77% by state | shifts fed/state composition, not the total |
| Benefits are entitlement values, not take-up-adjusted spending | overstates transfer outlays (especially ACA PTC) |
| Benefits looked up by total household income, not earned income | understates EITC deltas |
| Robot exposure anchored to the current patent stock (dexterity/care/performance occupations near zero even at full feasibility) | **understates** AGI scenarios' physical channel |
| Price level never enters nominal tax computations (A2 rule) | understates relative to deflation-driven models (quantified in §9.2) |
| Cross-sectional local evidence (China shock, fiscal multipliers) applied nationally | overstates if national general-equilibrium offsets are large |
| Fixed baseline economy (no counterfactual growth in the wage base beyond a denominator trend) | understates losses at long horizons in level terms |
| AGI presets run a wage-economy accounting frame through a post-wage transition | the frame itself strains; treat the near-total-automation scenarios (⑤–⑨) as transition stories, not steady states |
| Adoption is linear between anchored points (piecewise through published trajectory knots; §4.1). Measured cost of the convention: re-running every non-knotted scenario under asymmetric-S alternatives moves cumulative debt by up to {{n:sensitivity.adoption_shape.summary.max_debt_shift_pct_large|.0f}} percent in the large-displacement worlds and at most ${{n:sensitivity.adoption_shape.summary.max_debt_shift_B_small|,.0f}}B in the modest ones; final-year deficits leave the Monte Carlo P10–P90 band in {{n:sensitivity.adoption_shape.summary.n_final_deficit_outside_band}} of {{n:sensitivity.adoption_shape.summary.n_runs}} re-runs, but in only {{n:sensitivity.adoption_shape.summary.n_outside_band_large}} of the {{n:sensitivity.adoption_shape.summary.n_runs_large}} large-displacement runs — the excursions concentrate in the modest worlds, where a band only tens of billions wide makes a small dollar move look like a large one | direction depends on which S variant — front-loaded shapes raise cumulative debt in the severe worlds, back-loaded shapes lower it; endpoints are pinned by construction |
| Monte Carlo perturbs levers locally and independently (no correlated shocks, no Latin-hypercube global exploration) | bands are local credibility intervals, not full uncertainty |
| Reabsorption is rationed by refuge capacity (inflow), but already-reabsorbed workers are never re-displaced (no outflow churn) | understates AGI scenarios modestly — the inflow choke already carries most of the effect |
| Reabsorbed wage dynamics (Baumol pull, crowding pressure) ship at zero in every preset | direction depends on which force dominates; both are exposed as levers |

Two of these deserve emphasis because they cut *against* the model's thesis: the corporate
steelman and the robotics floor both make the modeled fiscal gap smaller than the mechanism
implies. The headline findings survive their correction in the wrong-for-the-thesis direction.
