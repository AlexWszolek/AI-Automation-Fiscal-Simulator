{{pagebreak}}

# 7. Findings: twelve worlds

Each unit below is one scenario: the anchor its levers encode, its headline numbers, and the one
thing it shows that the others do not. Dollar figures are nominal changes against the 2024 baseline,
and net fiscal impact is the signed change in the federal balance, which reconciles to the deficit
by identity C6. Two small-multiples grids carry the paths and attributions for all twelve at once,
while the cross-scenario table and dot plot in Section 1.3 carry the levels. Per-year fiscal
summaries, channel decompositions, and full lever rankings live in the artifact CSVs and the web
application.

{{fig:comparison.fan_grid|Federal deficit change by scenario, {{n:config.n}}-draw Monte Carlo fans (P10–P90 and P25–P75 bands, median line, dashed base run). Axes are $B per year against years from scenario start, **scaled per panel**: horizons run eight to twenty years and final-year deficits span three orders of magnitude, so the grid compares path *shape*. Levels are in the cross-scenario table.}}

{{fig:comparison.tornado_grid|Deficit attribution by scenario: Spearman rank correlation of each perturbed lever with the final-year deficit change, top six levers per scenario. Which assumptions matter is itself scenario-dependent — that dependence is the figure's content.}}

The bands need a word, as they are easy to over-read. The Monte Carlo perturbs each lever
independently by ±15 percent around its scenario setting, so a band measures robustness to lever
mis-calibration within a world, meaning how wrong the headline could be if each anchor is somewhat
off. It is not a calibrated probability interval, as the perturbation spread is a convention rather
than an estimated distribution. The model's honest uncertainty statement is the spread across the
twelve scenarios, carried by the cross-scenario table and comparison dot plot in Section 1.3, which
is driven by genuinely contested quantities: how much work AI can do, how fast firms adopt it, and
whether the labor market heals or scars. Which of those matter anywhere in the lever space rather
than only near a preset is the subject of the global screening in Section 7.14.

Two structural features of the set are visible before any individual world. The first is that five
of the twelve end with the federal balance better than baseline, and three of those are cumulative
paydowns across the whole horizon, as capital-side recoveries do overtake labor-side losses inside a
decade where displacement is modest and the labor market functions. The fiscal problem is not
automatic, and a report that only carried the severe worlds would be making a selection rather than
a finding.

The second is that the twelve do not spread evenly. They cluster, with final-year deficit changes
sitting either below roughly ${{n:presets.china-shock.final.fed_deficit_delta_B|,.0f}} billion or
above ${{n:presets.agi-20y.final.fed_deficit_delta_B|,.0f}} billion, and nothing anchored between
them. No published scenario found for this exercise lands in the middle, as the literature offers
manageable worlds and regime changes with no gradual path between. The concession on this side is
that this is a fact about the literature and not necessarily about the world: it may reflect what is
publishable rather than what is likely, since a scenario that is neither reassuring nor alarming is
harder to write.

## 7.1 Acemoglu — Modest AI

His ten-year upper bounds at face value: a fifth of the wage bill exposed, 23 percent of that
profitably automatable within the decade, a 0.15 productivity pass-through from his own TFP
arithmetic, no wage response, and a normal labor market. Employment falls
{{n:presets.acemoglu-modest.final.employment_drop_pct|.1f}} percent by year ten and the federal
balance moves by {{n:presets.acemoglu-modest.final.net_fiscal_impact_B|+,.1f}} billion dollars,
favorably. That sign is the finding: given modest displacement and a functioning labor market, the
capital-side recoveries outgrow the shrinking labor losses within a decade. Cumulative new debt is
{{n:presets.acemoglu-modest.final.fed_debt_B|,.0f}} billion against a
${{n:baselines.fed_deficit0_B|,.0f}} billion baseline deficit. This scenario sets the floor of the
set, as inside Acemoglu's bounds the fiscal system barely notices.

## 7.2 Brynjolfsson — Augmentation

AI complements more than it substitutes: adoption starts at the roughly 2 percent cumulative pace
early payroll data actually measured, survivors capture a fifth of the surplus with positive wage
complementarity, scarring is mild, and productivity pass-through is strong. Employment falls
{{n:presets.brynjolfsson-augment.final.employment_drop_pct|.1f}} percent, the final-year balance
changes by {{n:presets.brynjolfsson-augment.final.net_fiscal_impact_B|+,.1f}} billion dollars, and
the cumulative debt change is {{n:presets.brynjolfsson-augment.final.fed_debt_B|,.0f}} billion, a net
paydown. The distinctive mechanism is the survivor-wage channel doing real fiscal work, as raises
re-taxed at full marginal rates rebuild part of the base displacement erodes. It is the one channel
by which the labor share of revenue defends itself, and this is the world built to show it working.

## 7.3 Windfall Trust — Medium

The comparator, and the only scenario whose target comes from another model's published output: 60
percent of jobs exposed, half of exposed work automated in a decade, re-employment at 70 percent of
prior wage, value capture split evenly between firms and consumers, capital at their 26.7 percent
effective rate. Employment falls {{n:presets.windfall-medium.final.employment_drop_pct|.0f}} percent,
the final-year balance deteriorates by
{{n:presets.windfall-medium.final.net_fiscal_impact_B|abs,,.0f}} billion dollars, and cumulative debt
reaches {{n:presets.windfall-medium.final.fed_debt_B|,.0f}} billion. The ten-year total-revenue change
of {{n:presets.windfall-medium.cumulative.cum10y_total_revenue_pct|.2f}} percent is what Section 9.1
sets against their −2.8 percent. The composition is worth noting: the state consumption-tax line
barely moves even as prices fall, which is the taxable-to-consumer-surplus channel showing up as
quantitatively real and almost entirely untaxed.

{{tbl:summary_tax:windfall-medium|condensed|Windfall Trust — Medium: fiscal summary ($B, condensed years; the full table and the four-channel decomposition are in Appendix C).}}

## 7.4 Autor et al. — China-shock dynamics

The displacement here is smaller than Windfall-Medium's, at 40 percent of a moderately exposed
economy over fifteen years, but the labor market is the one Autor, Dorn, and Hanson actually
measured: reabsorption at 0.075 per year, labor-force exit as the dominant margin, a 25 percent
permanent scar, and demand amplification at the no-monetary-offset end of the evidence. Nothing
heals, so everything accumulates. Employment ends
{{n:presets.china-shock.final.employment_drop_pct|.0f}} percent down, the final-year deficit change is
{{n:presets.china-shock.final.net_fiscal_impact_B|abs,,.0f}} billion dollars, induced layoffs stand at
{{n:presets.china-shock.final.induced_M|.1f}} million, and cumulative debt reaches
{{n:presets.china-shock.final.fed_debt_B|,.0f}} billion. This is the mechanism scenario, as it
converts a moderate technology shock into a large fiscal one purely through adjustment failure.

## 7.5 Korinek–Suh — AGI in 20 years

Full automation, slowly: over twenty years the ceiling climbs to one, wages collapse ahead of it, and
capital keeps 80 percent of the net saving. Employment ends
{{n:presets.agi-20y.final.employment_drop_pct|.0f}} percent down, the deficit change is
{{n:presets.agi-20y.final.net_fiscal_impact_B|abs,,.0f}} billion dollars per year, and cumulative new
debt is {{n:presets.agi-20y.final.fed_debt_B|,.0f}} billion, the largest in the set, as twenty years
of near-total automation is simply more years of it. Real output ends
{{n:presets.agi-20y.final.productivity_gain_pct|.0f}} percent above baseline, which is the point: the
fiscal crisis and the abundance are simultaneous, as the tax system is plumbed to wages while the
abundance arrives as profit, price declines, and capital income. The states close
{{n:presets.agi-20y.final.state_gap_B|,.0f}} billion in the final year alone, half of it by spending
cuts that feed back into demand.

## 7.6 Korinek–Suh — AGI in 5 years

The same destination at year five, linear to full automation and flat thereafter over a ten-year
fiscal window, with crash robotics build-out, mass labor-force exit, and crisis-regime demand.
Employment effectively ceases to be the tax base: down
{{n:presets.agi-5y.final.employment_drop_pct|.0f}} percent, final-year deficit change
{{n:presets.agi-5y.final.net_fiscal_impact_B|abs,,.0f}} billion dollars, cumulative debt
{{n:presets.agi-5y.final.fed_debt_B|,.0f}} billion, against a GDP simultaneously
{{n:presets.agi-5y.final.productivity_gain_pct|.0f}} percent larger in real terms. The distinctive
result is insensitivity: the final-year P10–P90 band spans
{{n:presets.agi-5y.mc.final_fed_deficit_B.p10|,.0f}} to
{{n:presets.agi-5y.mc.final_fed_deficit_B.p90|,.0f}} billion, so the best decile of this world is
worse than the worst decile of everything outside the AGI-and-takeoff class. It is also where the
state caps bind hardest, with {{n:presets.agi-5y.final.n_states_capped}} states at their ceiling in
the final year.

## 7.7 AI 2027 — Fast takeoff

The AI Futures shape: cognition maxes almost immediately, robots ramp over three years of crash
build-out, and nearly a third of the saved bill goes to compute. The path starts at the scenario's
own 20-percent-AI milestone and saturates at year five, three years inside the eight-year window.
Employment falls {{n:presets.ai-2027.final.employment_drop_pct|.0f}} percent and cumulative debt
reaches {{n:presets.ai-2027.final.fed_debt_B|,.0f}} billion. The finding is where the base lands
rather than how much of it moves: the heavy automation-input bill shrinks the net saving available
for profit, and so shrinks the corporate offset, while swelling a compute pool taxed at 5 percent.
Fast takeoff routes an unusually large share of the migrated base to the lowest-taxed destination
available, which is why compute parity binds hardest here, as Section 8 shows.

## 7.8 AI 2040 — Plan A (The Deal)

The AI Futures Project's managed transition: a 2029 US–China deal slows the takeoff, 95 percent of
tasks are automatable by 2035–36, and employment falls from 62 to 12 percent over 2032–2040. The
adoption path is knotted to their published trajectory, 20 percent of value-weighted labor by 2032
and 85 percent by 2035, so its shape is theirs rather than a fitted curve. Employment ends
{{n:presets.ai2040-plan-a.final.employment_drop_pct|.0f}} percent down over fourteen years, the
final-year deficit change is
{{n:presets.ai2040-plan-a.final.net_fiscal_impact_B|abs,,.0f}} billion dollars, and cumulative debt is
{{n:presets.ai2040-plan-a.final.fed_debt_B|,.0f}} billion. What earns it a place is the exclusion:
their permit-fee regime and Citizen's Dividend are policy rather than world state, so this prices
Plan A's world under current US law, and the gap it reports measures the hole their policy was
designed to fill.

## 7.9 AI 2040 — Plan D (The Race)

The same authors' no-deal branch, with identical technology and opposite governance, which makes it
a controlled comparison. Superintelligence arrives in early 2031 and integration then runs as fast as
markets and laws allow: the path holds at its starting level through year four, as nothing integrates
before takeoff, then runs to full automation by year seven, the steepest ramp in the set. Employment
ends {{n:presets.ai2040-plan-d.final.employment_drop_pct|.0f}} percent down, the final-year deficit
change is {{n:presets.ai2040-plan-d.final.net_fiscal_impact_B|abs,,.0f}} billion dollars, and
{{n:presets.ai2040-plan-d.final.n_states_capped}} states hit their rate-hike caps. The comparison is
the finding: the deferred-then-vertical path buys four quiet years and spends them all at once,
reaching a worse annual deficit than Plan A on a horizon four years shorter. Speed, not eventual
extent, is what the fiscal system cannot absorb.

## 7.10 Karger et al. — Expert survey, rapid

The NBER expert survey's rapid branch at its elicited 14 percent probability, and the first preset
anchored to an elicited distribution rather than an authored scenario. It carries the survey's
signature, which is that unemployment stays at 5 to 6 percent because displacement exits the labor
force instead of joining the unemployment rolls. Employment falls
{{n:presets.karger-rapid.final.employment_drop_pct|.1f}} percent, the final-year balance moves by
{{n:presets.karger-rapid.final.net_fiscal_impact_B|+,.1f}} billion dollars, and the cumulative change
is {{n:presets.karger-rapid.cumulative.net_fiscal_impact_B|+,.0f}} billion, which is a world that
costs money on the way through and ends better than it started. It is also the first to switch on the
Baumol pull, as the work humans still do gets expensive while everything else gets cheap, which is
how the survey's rising median income reaches labor in this accounting.

## 7.11 Metaculus — Crowd median, 2035

The Labor Automation Hub's community medians: employment roughly 7.5 percent below the no-AI baseline
by 2035, labor share down four to five points, and survivor wages up, which is displacement without a
doom loop. It is also the only anchor here that is a live, revisable forecast rather than a fixed
publication. Employment falls {{n:presets.metaculus-2035.final.employment_drop_pct|.1f}} percent, the
final-year balance moves by
{{n:presets.metaculus-2035.final.net_fiscal_impact_B|+,.1f}} billion dollars, and cumulative debt
changes by {{n:presets.metaculus-2035.final.fed_debt_B|+,.0f}} billion. It is the only scenario
running both refuge-wage forces, a Baumol pull and a crowding pressure, because that is what the
crowd's simultaneous forecasts of falling labor share and rising real wages require: the two
reconcile only if the gains concentrate in the work that stays human.

## 7.12 OpenAI — Jobs transition framework

Their four archetypes read as a decade of displacement pressure, being the 18 percent high-risk
cohort plus partial staffing compression where jobs reorganize. Their framing is explicit that this
maps pressure rather than job losses, and the preset honors that by pairing substantial cognitive
exposure with the healthiest labor market in the set, meaning reabsorption at 0.55 with the
grow-with-AI bucket absorbing, and a physical channel near zero. Employment falls
{{n:presets.openai-transition.final.employment_drop_pct|.1f}} percent, which is more than in either
survey-anchored world, yet the final-year balance improves by
{{n:presets.openai-transition.final.net_fiscal_impact_B|+,.0f}} billion dollars and the horizon is a
cumulative paydown of {{n:presets.openai-transition.cumulative.net_fiscal_impact_B|+,.0f}} billion,
the largest here. That inversion is the cleanest demonstration of the recurring result, which is that
how the labor market responds moves the fiscal outcome more than how much work is automated. The
same displacement met by the China-shock labor market is a crisis.

## 7.13 The three theses, across worlds

Base migration holds in every scenario with substantial displacement, and the channel decomposition
shows the same anatomy each time, with the four-channel view for the Windfall comparator in Appendix
C: labor taxes lost at combined marginal rates, partially recovered through capital-side channels at
roughly half those rates or less, and the consumer-surplus channel, meaning price declines, recovered
at roughly two cents on the dollar through state consumption taxes.

The shareholder leg completes the capital-side picture and is the smallest of them. In the five-year
AGI world the windfall capital-gains line raises
{{n:presets.agi-5y.final.shareholder_cg_tax_B|,.1f}} billion dollars in the final year against a
standing unrealized stock of ${{n:presets.agi-5y.final.shareholder_windfall_stock_B|,.0f}} billion,
so the accrued equity claim the automation surplus creates is real and large while current law
reaches almost none of it inside the fiscal window. Deferral, the taxable-holder share, and step-up
at death do that work. Pricing the channel rather than assuming it is what licenses the conclusion
that the equity windfall is fiscally near-mute, and Section 4.5 sets out the construction.

Revenue falls faster than employment because exposure skews above the median wage and the schedules
are progressive, so the percentage revenue loss exceeds the percentage employment loss early in every
scenario. The wedge narrows only where survivor raises rebuild the base, as in the augmentation and
crowd-median worlds, and widens where scarring is deep, as in the grind.

The state amplifier operates because the federal deficit is a shock absorber while the states'
balance requirement is a shock transmitter. Across scenarios, state gaps scale with displacement, the
rate-hike caps bind in the severe worlds, and every dollar of forced spending cuts re-enters the
demand channel as first-round-multiplier withdrawal, which is visible both in the induced-layoff
stocks and in the difference between scenarios with and without state stress in their configuration.

## 7.14 Global sensitivity screening

The per-scenario bands above are deliberately local. Asking which assumptions matter anywhere, and
where in the lever space the fiscal picture changes qualitatively, requires sweeping the whole space:
a {{n:screening.config.n|,.0f}}-point Latin hypercube over {{n:screening.config.n_dims}} lever
dimensions spanning the full interface ranges, with adoption ceilings from 5 to 100 percent of
exposed work, reabsorption from frozen to near-frictionless, demand amplification from none to
crisis-regime, and the policy dials from off to their maxima, each point run at a common ten-year
horizon.

Every one of the {{n:screening.config.n|,.0f}} runs passes the full conservation battery, as the
C1–C8 identities hold at every sampled corner of the space with
{{n:screening.checks.invariant_failures}} failures, alongside an employment-oscillation screen with
{{n:screening.checks.oscillation_flagged}} runs flagged. A dedicated
{{n:screening.config.n_cycle}}-point batch at a twenty-year horizon, concentrated in the
near-total-automation corner that produced the demand-controller artifact fixed during development,
meaning high adoption with hot demand feedback and cold re-employment, regression-guards that fix:
no sampled path shows more than {{n:screening.checks.cycle_batch_max_alternations}} above-threshold
employment reversal against a flag threshold of two.

Classified by the final-year deficit change as a share of GDP, the global space splits into four
regimes. The federal balance improves in {{n:screening.regimes.improves_pct|.0f}} percent of the
space, where survivor-wage and capital-recapture channels outrun small displacement; it worsens by
under one percent of GDP in {{n:screening.regimes.band_0_1_pct|.0f}} percent, by one to three percent
in {{n:screening.regimes.band_1_3_pct|.0f}} percent, and by more than three percent of GDP, which is
fiscal stress on the scale of a permanent Great-Recession revenue shock, in
{{n:screening.regimes.band_gt3_pct|.0f}} percent. State rate-hike caps bind somewhere along the path
in {{n:screening.regimes.capped_anywhere_pct|.1f}} percent of the space. The twelve presets of this
section were chosen before this sweep was run, and the map confirms they span the regimes rather than
clustering in one. The four shareholder-channel levers are not swept as dimensions, as they are
measured current-law constants riding at their shipped values in every run, so the sweep explores the
worlds that create the equity claim rather than alternative tax treatments of it.

{{fig:screening.figures.regime_scatter|Global regime map: each point is one sampled world, positioned by the two strongest uncertainty drivers and colored by its final-year fiscal regime.}}

Rank correlations against the final-year deficit are computed per lever and reported on two panels,
separating the uncertainty dimensions, meaning what the world does, from the policy dimensions,
meaning what governments choose. The separation is necessary because the policy dollars are
mechanically large: a maxed UBI dial moves trillions and would otherwise drown the attribution of
genuine uncertainty. Among the uncertainty dimensions the strongest global driver is
`{{n:screening.top_drivers.uncertainty.0.lever}}`
(ρ = {{n:screening.top_drivers.uncertainty.0.spearman|+.2f}}); among policy dimensions it is
`{{n:screening.top_drivers.policy.0.lever}}`
(ρ = {{n:screening.top_drivers.policy.0.spearman|+.2f}}). Alongside the rank correlation each lever
carries a binned correlation ratio, η², used as a first-order Sobol proxy. Agreement between the two
indicates a monotone effect, while a high η² with a near-zero ρ flags the conditionally activated
levers, such as a robotics lag that matters only where physical feasibility is high or a UBI
recapture that matters only where UBI is on, whose influence rank correlation alone understates.

{{fig:screening.figures.global_tornado_uncertainty|Global drivers of the final-year federal deficit across the whole lever space — uncertainty dimensions.}}

{{fig:screening.figures.global_tornado_policy|Global drivers of the final-year federal deficit — policy dimensions. The UBI dial dominates by construction: it is the only lever that moves trillions of dollars directly.}}

Two caveats bound what the sweep can say. It samples the lever space uniformly, weighting a
five-year-AGI corner equally with a modest-AI corner, so the regime frequencies describe the model's
behavior over its input space rather than probabilities over futures. And it holds the model's
structure fixed, exploring parameter space rather than specification space, for which the
simplifications table of Section 10 is the honest account.
