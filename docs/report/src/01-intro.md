# 1. Introduction and summary of findings

The useful question is not what AI will do to the economy, as that question is too large to answer
and too vague to test. It is narrower and more concrete: if AI automates some share of the work
Americans currently do, what happens to the public finances that depend on that work being done by
taxed humans? The United States raises roughly ${{n:baselines.fed_revenue0_B|,.0f}} billion of
federal revenue and ${{n:baselines.state_revenue0_B|,.0f}} billion of state and local revenue
against a $15.0 trillion compensation base, and eighty-four percent of federal receipts come from
individual income and payroll taxes, which are taxes on people being employed. When a job is
automated the wage leaves that base, but the value the job produced does not leave with it. It
re-emerges as corporate profit, as lower prices, or as capital income, each taxed at a different
and usually lower effective rate, and sometimes at no rate at all. The fiscal question is therefore
an accounting question about base migration, which is why this model is built as an accounting
machine first: every dollar of displaced compensation is tracked to a destination, every
destination has a tax treatment, and the books are forced to balance by construction.

Three theses organize everything that follows. The first is that **the tax base migrates from labor
to capital**. The saved wage bill flows to retained profit, taxed at effective corporate rates near
17 to 18 percent; to price reductions, taxed at roughly 2 percent through state consumption taxes
and not at all federally; to compute capital, taxed at an effective rate near 5 percent post-TCJA;
and, for the undistributed remainder that capitalizes into equity value, to shareholders, who are
reached at a fraction of a cent per dollar per year once the taxable-holder share and measured
realization rates are applied. Every one of those destinations yields the government less than the
25 to 40 percent combined marginal wedge on the wages they replace. The second is that **revenue
falls faster than employment**, as displacement is not uniform: AI exposure concentrates in
above-median-wage occupations, so the workers displaced first carry more than their per-capita
share of income tax, and progressive rate schedules do the rest. The third is that **the states are
the asymmetric amplifier**. The federal government meets lost revenue with deficits and the states
cannot, as nearly all of them must close their gaps within the year by raising rates on a shrinking
base or cutting spending, and both responses withdraw demand from the same economy that is shedding
jobs, which feeds back into further displacement.

## 1.1 The model is an accounting machine first

The model is a two-layer system. The static kernel computes, for each of roughly 33,000
occupation-by-state cells, the exact fiscal delta of removing one worker: federal and state income
tax from hand-rolled bracket schedules, payroll tax with the OASDI cap, means-tested transfers
(Medicaid, SNAP, EITC, CTC, ACA, SSI, TANF) from an offline PolicyEngine bake integrated over the
within-cell wage distribution, a consumption-tax channel, and a corporate offset. The dynamic layer
turns those deltas into a multi-actor simulation: a seven-state worker stock-flow machine, a firm
disposition router, a compute-capital pool, survivor wage dynamics, a shareholder channel that
prices the undistributed corporate earnings the surplus capitalizes, a price and productivity macro
block, the federal debt ledger, a fifty-one-state balanced-budget closure, and a lagged demand
feedback. Section 4 walks the within-period sequence and Appendix A carries the full equation
reference.

Two design disciplines distinguish the exercise. The first is conservation. Nine identities are
asserted on every period of every run, including every Monte Carlo draw sampled for this report:
worker headcounts partition the baseline, the disposition of the saved bill sums exactly, the
federal deficit reconciles to its labeled components, state gaps close to numerical residual zero,
and so on. A run that violates any of them raises rather than reporting a number. The second is
reduction. With every behavioral lever switched off, the dynamic system reproduces the static
kernel bit for bit, so every result in this document can be traced back to a base case that is
small enough to check by hand. Section 5 states the identities precisely.

## 1.2 What the model deliberately leaves out

It is not a general-equilibrium forecast. There is no monetary policy block, no endogenous interest
rate, no behavioral response of automation investment to taxation, and no representation of
within-job augmentation, meaning a worker made more productive but not displaced. Prices deflate
reported real aggregates but are never injected into nominal tax computations.

Two of these omissions are large enough to name here rather than leave to Section 10. Capital
income does not spend: retained profit reaches the economy only through corporate tax, as there is
no shareholder-consumption or investment channel, and the latter is likely a significant source of
growth. And there is no task creation, as displaced workers re-enter only through a fixed
re-employment rate into a finite set of low-exposure occupations, so automation never endogenously
creates new kinds of work. Both decisions are deliberate. The history of automation says offsets
eventually arrive, but the question here is what the fiscal path looks like if they arrive late or
never, because fiscal authorities have to be able to respond to that world too. The numbers should
be read as a world with no offsets. Section 10 lists every known simplification with its direction
of bias, and the external validations in Section 9 quantify how far these choices move the results
against models that made the opposite ones.

## 1.3 The range is the finding

Rather than defend one forecast, the model ships twelve scenario presets, each anchored lever by
lever to a specific literature, and Section 7 introduces each where its results are reported:
Acemoglu's deliberately modest bounds; an augmentation-leaning reading of the Brynjolfsson
micro-evidence; the Windfall Trust's medium displacement scenario, which is the closest external
comparator this model has; a China-shock grind that pairs a moderate shock with the slow, scarring
labor-market adjustment Autor, Dorn, and Hanson actually measured; Korinek and Suh's twenty-year and
five-year AGI transitions; the AI Futures Project's fast takeoff and the two branches of their
managed-versus-race successor scenario; the rapid branch of an NBER expert elicitation at its own 14
percent probability; a forecasting crowd's 2035 median; and OpenAI's own map of displacement
pressure. Government policy composes separately as overlays, namely two robot taxes at
literature-optimal rates, a universal basic income with recapture, and compute-pool tax parity, so
that each scenario answers what the world does to the budget while each overlay answers what policy
recovers.

{{tbl:cross_preset|Cross-scenario comparison: final-year outcomes with Monte Carlo P10–P90 bands (N={{n:config.n}}, seed {{n:config.seed}}). Net fiscal impact is the signed change in the federal balance (negative = worse); the band applies to the final-year federal deficit change.}}

{{fig:comparison.final_outcome_dotplot|Final-year federal deficit change by scenario: P10–P90 range (rule) and median (dot) across {{n:config.n}} Monte Carlo draws per scenario.}}

The range is the finding, and it is wide enough that any single headline number taken from this
document without its scenario label is being misused. A world that stays inside Acemoglu's bounds
is fiscally almost invisible, as the deficit change turns negative by the end of the decade, a
small improvement, once capital-side recoveries outgrow modest labor losses. A world in which the
Korinek–Suh five-year transition happens is a fiscal regime change: employment falls
{{n:presets.agi-5y.final.employment_drop_pct|.0f}} percent, the federal deficit widens by
${{n:presets.agi-5y.final.fed_deficit_delta_B|,.0f}} billion in the final year alone, and cumulative
new federal debt reaches ${{n:presets.agi-5y.final.fed_debt_B|,.0f}} billion inside ten years.

What separates those poles is the more useful result. Between them, the scenarios differ not mainly
in how much work is automated but in what the labor market and the firms do with it, as
reabsorption rates, wage scarring, and the disposition of the saved wage bill move the fiscal
outcome as much as the displacement share does. This matters for policy in a way the headline range
does not, since the displacement share is largely not a policy variable while the disposition of
the saved bill largely is. The Monte Carlo tornados in Section 7 make that attribution precise, and
the policy analysis in Section 8 shows that the taxes the optimal-taxation literature actually
recommends recover only a small fraction of the gap in every scenario where the gap is large.

## 1.4 How to read this document

Sections 2 through 5 are the model: data, kernel, dynamics, and the correctness discipline. Section
6 is calibration. Sections 7 through 9 are results, covering the twelve scenarios, the policy
overlays, and validation against external models (RAND, the Windfall Trust, Acemoglu). Section 10
is the honest-limitations table, and it is the section a skeptical reader should probably read
second. Every model-derived number in the text, including those in this introduction, is resolved
at build time from a manifest generated by a seeded pipeline (Appendix D), so the numbers cannot
drift from the model without breaking the build.
