{{pagebreak}}

# 7. Findings: seven worlds

Each subsection reports one scenario: the story its levers tell, its fiscal summary (revenue lines
are signed changes, negative = lost revenue; the keystone row *Net fiscal impact* equals the signed
change in the federal balance and reconciles exactly to the deficit by identity C6), the Monte
Carlo fan around the federal deficit path ({{n:config.n}} draws, ±2σ-truncated relative
perturbations of spread {{n:config.spread}}, seed {{n:config.seed}}), and the tornado attributing
final-year deficit variance to individual assumptions. Dollar figures are nominal changes against
the 2024 baseline; the fiscal summary "Total" column sums flow rows over the scenario horizon.

## 7.1 Acemoglu — Modest AI

If AI stays inside Acemoglu's ten-year bounds, the fiscal system barely notices. Employment falls
{{n:presets.acemoglu-modest.final.employment_drop_pct|.1f}} percent by year ten; the federal
balance moves by {{n:presets.acemoglu-modest.final.net_fiscal_impact_B|+,.1f}} billion dollars in
the final year — the sign is worth pausing on: after a decade of modest displacement met by a
healthy labor market (half of the exhausted re-employed every year at a 13 percent haircut), the
capital-side recoveries — corporate offset, compute-pool tax, survivor wage taxes — have grown
past the shrinking labor losses, and the deficit change turns *favorable*. Cumulative new debt
over the decade is {{n:presets.acemoglu-modest.final.fed_debt_B|,.0f}} billion dollars — a
rounding error against the ${{n:baselines.fed_deficit0_B|,.0f}} billion baseline deficit. The
Monte Carlo band is correspondingly tight: the final-year deficit change spans
{{n:presets.acemoglu-modest.mc.final_fed_deficit_B.p10|,.0f}} to
{{n:presets.acemoglu-modest.mc.final_fed_deficit_B.p90|,.0f}} billion dollars between the 10th and
90th percentiles. The strongest single driver of that residual variance is
`{{n:presets.acemoglu-modest.mc.top_deficit_levers.0.lever}}`
(ρ = {{n:presets.acemoglu-modest.mc.top_deficit_levers.0.spearman|+.2f}}).

{{tbl:summary_tax:acemoglu-modest|condensed|Acemoglu — Modest AI: fiscal summary ($B, condensed years; full table in Appendix C).}}

{{fig:presets.acemoglu-modest.fan_deficit|Acemoglu — Modest AI: federal deficit change, Monte Carlo fan (P10–P90 and P25–P75 bands, median, dashed base run).}}

{{fig:presets.acemoglu-modest.tornado_deficit|Acemoglu — Modest AI: Spearman rank correlation of each perturbed lever with the final-year deficit change.}}

## 7.2 Brynjolfsson — Augmentation

The augmentation world is the optimist's case with the optimism located in the *labor market*
rather than in the technology being small. Adoption reaches 30 percent of a moderately exposed
economy, but survivors share a fifth of the surplus, complementarity lifts wages, scarring is mild
(10 percent), and reabsorption runs at 0.6 per year. Employment falls
{{n:presets.brynjolfsson-augment.final.employment_drop_pct|.1f}} percent; the final-year federal
balance change is {{n:presets.brynjolfsson-augment.final.net_fiscal_impact_B|+,.1f}} billion
dollars, and the cumulative debt change is
{{n:presets.brynjolfsson-augment.final.fed_debt_B|,.0f}} billion — a net *paydown*: this is the
one scenario in which AI improves the federal fiscal position over its whole horizon.
The survivor-wage channel does real fiscal work here: raises re-taxed at full marginal rates
partially rebuild the labor base that displacement erodes — the one mechanism by which the labor
share of revenue defends itself.

{{tbl:summary_tax:brynjolfsson-augment|condensed|Brynjolfsson — Augmentation: fiscal summary ($B, condensed).}}

{{fig:presets.brynjolfsson-augment.fan_deficit|Brynjolfsson — Augmentation: federal deficit fan.}}

{{fig:presets.brynjolfsson-augment.tornado_deficit|Brynjolfsson — Augmentation: deficit tornado.}}

## 7.3 Windfall Trust — Medium

The comparator scenario. Sixty percent of jobs exposed, half of exposed work automated in a
decade, re-employment at 70 percent of prior wage, high value capture split evenly between firms
and consumers, capital taxed at their 26.7 percent ETR. Employment falls
{{n:presets.windfall-medium.final.employment_drop_pct|.0f}} percent; the final-year federal
balance deteriorates by {{n:presets.windfall-medium.final.net_fiscal_impact_B|abs,,.0f}} billion
dollars and cumulative debt reaches {{n:presets.windfall-medium.final.fed_debt_B|,.0f}} billion.
The ten-year total-revenue change of {{n:presets.windfall-medium.cumulative.cum10y_total_revenue_pct|.2f}}
percent of the combined federal-plus-state baseline is the number compared against the Windfall
Trust's own −2.8 percent target in Section 9. Note the composition: the state consumption-tax
line barely moves even as consumer prices fall — the taxable-to-consumer-surplus channel is
quantitatively real and almost entirely untaxed.

{{tbl:summary_tax:windfall-medium|condensed|Windfall Trust — Medium: fiscal summary ($B, condensed).}}

{{fig:presets.windfall-medium.fan_deficit|Windfall Trust — Medium: federal deficit fan.}}

{{fig:presets.windfall-medium.tornado_deficit|Windfall Trust — Medium: deficit tornado.}}

## 7.4 China-Shock Grind

The displacement here is *smaller* than Windfall-Medium's — 40 percent of a moderately exposed
economy over fifteen years — but the labor market is the one Autor, Dorn, and Hanson measured:
reabsorption at 0.075 per year, labor-force exit the dominant adjustment margin, a 25 percent
permanent wage scar, and demand amplification at the no-monetary-offset end of the evidence.
Nothing heals, so everything accumulates: employment is down
{{n:presets.china-shock.final.employment_drop_pct|.0f}} percent at year fifteen, the final-year
deficit change is {{n:presets.china-shock.final.net_fiscal_impact_B|abs,,.0f}} billion dollars,
induced layoffs stand at {{n:presets.china-shock.final.induced_M|.1f}} million, and cumulative
debt reaches {{n:presets.china-shock.final.fed_debt_B|,.0f}} billion — the grind converts a
moderate technology shock into a large fiscal one purely through adjustment failure. This is the
scenario that most cleanly isolates the model's second and third theses: revenue falls much faster
than output, and the state closure ({{n:presets.china-shock.final.state_gap_B|,.0f}} billion
dollars of gap to close in the final year) feeds austerity back into demand.

{{tbl:summary_tax:china-shock|condensed|China-Shock Grind: fiscal summary ($B, condensed).}}

{{fig:presets.china-shock.fan_deficit|China-Shock Grind: federal deficit fan.}}

{{fig:presets.china-shock.tornado_deficit|China-Shock Grind: deficit tornado.}}

## 7.5 Korinek–Suh — AGI in 20 years

Full automation, slowly. Over twenty years the adoption ceiling climbs to one, wages collapse
ahead of it (elasticity at the slider floor, a 40 percent re-employment haircut, reabsorption near
zero), and capital keeps 80 percent of the net saving. By the final year employment is down
{{n:presets.agi-20y.final.employment_drop_pct|.0f}} percent, the deficit change is
{{n:presets.agi-20y.final.net_fiscal_impact_B|abs,,.0f}} billion dollars per year, and cumulative
new debt is {{n:presets.agi-20y.final.fed_debt_B|,.0f}} billion. The productivity dividend is
enormous — real output ends {{n:presets.agi-20y.final.productivity_gain_pct|.0f}} percent above
baseline — which is precisely the point: **the fiscal crisis and the abundance are simultaneous**,
because the tax system is plumbed to wages and the abundance arrives as profit, price declines,
and capital income. The states close a gap of
{{n:presets.agi-20y.final.state_gap_B|,.0f}} billion dollars in the final year alone — half of it,
by this scenario's Korinek–Lockwood-motivated configuration, through direct spending cuts whose
demand consequences feed straight back into the induced-layoff channel.

{{tbl:summary_tax:agi-20y|condensed|Korinek–Suh — AGI in 20 years: fiscal summary ($B, condensed).}}

{{fig:presets.agi-20y.fan_deficit|AGI in 20 years: federal deficit fan.}}

{{fig:presets.agi-20y.tornado_deficit|AGI in 20 years: deficit tornado.}}

## 7.6 Korinek–Suh — AGI in 5 years

The stress case: the same destination reached at year five (a kinked adoption path — linear to
full automation at year five, flat thereafter — viewed over a ten-year fiscal window), with crash
robotics build-out, mass labor-force exit, and crisis-regime demand amplification. Employment
effectively ceases to be the tax base: down
{{n:presets.agi-5y.final.employment_drop_pct|.0f}} percent, with the final-year deficit change at
{{n:presets.agi-5y.final.net_fiscal_impact_B|abs,,.0f}} billion dollars and cumulative debt of
{{n:presets.agi-5y.final.fed_debt_B|,.0f}} billion — against a GDP that is simultaneously
{{n:presets.agi-5y.final.productivity_gain_pct|.0f}} percent larger in real terms. No plausible
parameter perturbation changes the qualitative picture: the P10–P90 band on the final-year deficit
change runs from {{n:presets.agi-5y.mc.final_fed_deficit_B.p10|,.0f}} to
{{n:presets.agi-5y.mc.final_fed_deficit_B.p90|,.0f}} billion dollars — the *best* decile of this
world is fiscally worse than the worst decile of every scenario outside the AGI-and-takeoff class.

{{tbl:summary_tax:agi-5y|condensed|Korinek–Suh — AGI in 5 years: fiscal summary ($B, condensed).}}

{{fig:presets.agi-5y.fan_deficit|AGI in 5 years: federal deficit fan.}}

{{fig:presets.agi-5y.tornado_deficit|AGI in 5 years: deficit tornado.}}

## 7.7 AI 2027 — Fast takeoff

The AI Futures shape: cognitive feasibility maxes almost immediately, robots ramp over three years
of crash build-out, and nearly a third of the saved bill flows to compute investment. Over its
eight-year window employment falls {{n:presets.ai-2027.final.employment_drop_pct|.0f}} percent and
cumulative debt reaches {{n:presets.ai-2027.final.fed_debt_B|,.0f}} billion dollars. The heavy
`auto_cost` matters fiscally: a large automation-input bill shrinks the net saving available for
profit (and therefore the corporate offset) while the compute pool it feeds is taxed at 5 percent
— the fast-takeoff world is one where an unusually large share of the migrated base lands at the
*lowest*-taxed destination, which is what makes the compute-parity overlay bind hardest here
(Section 8).

{{tbl:summary_tax:ai-2027|condensed|AI 2027 — Fast takeoff: fiscal summary ($B, condensed).}}

{{fig:presets.ai-2027.fan_deficit|AI 2027 — Fast takeoff: federal deficit fan.}}

{{fig:presets.ai-2027.tornado_deficit|AI 2027 — Fast takeoff: deficit tornado.}}

## 7.8 The three theses, across worlds

**Base migration.** In every scenario with substantial displacement, the channel decomposition
(the four-channel view for the Windfall comparator appears in Appendix C) shows the same anatomy:
labor taxes lost at combined marginal rates, partially recovered through capital-side channels at
roughly half those rates or less, with the consumer-surplus channel — price declines — recovered
at roughly two cents on the dollar through state consumption taxes.

**Revenue vs. employment.** Because exposure skews above-median-wage and the schedules are
progressive, the percentage revenue loss exceeds the percentage employment loss early in every
scenario; the wedge narrows only where survivor raises rebuild the base (the augmentation world)
and widens where scarring is deep (the grind).

**The state amplifier.** The federal government's deficit is a shock absorber; the states' balance
requirement is a shock *transmitter*. Across scenarios, state gaps scale with displacement, the
rate-hike caps bind in the severe worlds, and every dollar of forced spending cuts re-enters the
demand channel as first-round-multiplier withdrawal — visible in the induced-layoff stocks and in
the difference between scenarios with and without state stress in their configuration.
