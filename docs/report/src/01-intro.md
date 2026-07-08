# 1. Introduction and summary of findings

The question this model answers is narrower and more concrete than "what will AI do to the
economy": *if AI automates some share of the work Americans currently do, what happens to the
public finances that depend on that work being done by taxed humans?* The United States raises
roughly ${{n:baselines.fed_revenue0_B|,.0f}} billion of federal revenue and
${{n:baselines.state_revenue0_B|,.0f}} billion of state and local revenue against a
$15.0 trillion compensation base. Eighty-four percent of federal receipts come from individual
income and payroll taxes — taxes on people being employed. When a job is automated, the wage
disappears from that base, but the value the job produced does not disappear: it re-emerges as
corporate profit, lower prices, or capital income, each taxed at a different — usually lower, and
sometimes zero — effective rate. The fiscal question is therefore an *accounting* question about
base migration, and this model is built as an accounting machine first: every dollar of displaced
compensation is tracked to a destination, every destination has a tax treatment, and the books are
forced to balance by construction.

Three theses organize everything that follows.

1. **The tax base migrates from labor to capital.** The saved wage bill flows to retained profit
   (taxed at effective corporate rates near 17–18 percent), to price reductions (taxed at roughly
   2 percent through state consumption taxes, and not at all federally), and to compute capital
   (taxed at an effective rate near 5 percent post-TCJA). Every one of those destinations yields
   the government less than the 25–40 percent combined marginal wedge on the wages they replace.
2. **Revenue falls faster than employment.** Displacement is not uniform: AI exposure concentrates
   in above-median-wage occupations, so the workers displaced first carry more than their
   per-capita share of income tax. Progressive rate schedules do the rest.
3. **The states are the asymmetric amplifier.** The federal government meets lost revenue with
   deficits. The states cannot: they must close their gaps each year by raising rates on a
   shrinking base or cutting spending, and both responses withdraw demand from the same economy
   that is shedding jobs, feeding back into further displacement.

## 1.1 What the model is

The model is a two-layer system. The **static kernel** computes, for each of roughly 33,000
occupation-by-state cells, the exact fiscal delta of removing one worker: federal and state income
tax from hand-rolled bracket schedules, payroll tax with the OASDI cap, means-tested transfers
(Medicaid, SNAP, EITC, CTC, ACA, SSI, TANF) from an offline PolicyEngine bake integrated over the
within-cell wage distribution, a consumption-tax channel, and a corporate offset. The **dynamic
layer** turns those deltas into a multi-actor simulation: a seven-state worker stock-flow machine,
a firm disposition router, a compute-capital pool, survivor wage dynamics, a price and productivity
macro block, the federal debt ledger, a fifty-one-state balanced-budget closure, and a lagged
demand feedback. Section 4 walks the within-period sequence; Appendix A carries the full equation
reference.

Two design disciplines distinguish the exercise. First, **conservation**: eight identities (worker
headcounts partition the baseline; the disposition of the saved bill sums exactly; the federal
deficit reconciles to its labeled components; state gaps close to numerical residual zero; and so
on) are asserted on every period of every run, including every Monte Carlo draw sampled for this
report. Second, **reduction**: with every behavioral lever switched off, the dynamic system
reproduces the static kernel bit-for-bit — an anchor that pins the elaborate machinery to a
hand-checkable base case. Section 5 states the identities precisely.

## 1.2 What the model is not

It is not a general-equilibrium forecast. There is no monetary policy block, no endogenous
interest rate, no behavioral response of automation investment to taxation, and no representation
of within-job augmentation (a worker made more productive but not displaced). Prices deflate
reported real aggregates but are never injected into nominal tax computations. Section 10 lists
every known simplification with its direction of bias; the external-validation exercises in
Section 9 quantify how far these omissions move the results relative to models that make the
opposite choices.

## 1.3 The scenario space and the headline result

Rather than defend one forecast, the model ships seven **scenario presets**, each anchored
lever-by-lever to a specific literature (Section 6): Acemoglu's deliberately modest bounds; an
augmentation-leaning reading of the Brynjolfsson micro-evidence; the Windfall Trust's medium
displacement scenario (our closest external comparator); a "China-shock grind" that pairs a
moderate shock with the slow, scarring labor-market adjustment Autor, Dorn, and Hanson actually
measured; Korinek and Suh's twenty-year and five-year AGI transitions; and the AI Futures
Project's fast takeoff. Government policy composes separately as **overlays** — two robot taxes at
literature-optimal rates, a universal basic income with recapture, and compute-pool tax parity —
so that each scenario answers "what does the world do to the budget" and each overlay answers
"what does policy recover."

{{tbl:cross_preset|Cross-scenario comparison: final-year outcomes with Monte Carlo P10–P90 bands (N={{n:config.n}}, seed {{n:config.seed}}). Net fiscal impact is the signed change in the federal balance (negative = worse); the band applies to the final-year federal deficit change.}}

{{fig:comparison.final_outcome_dotplot|Final-year federal deficit change by scenario: P10–P90 range (rule) and median (dot) across {{n:config.n}} Monte Carlo draws per scenario.}}

The range is the finding. A world that stays inside Acemoglu's bounds is fiscally almost
invisible — the deficit change turns *negative* (a small improvement) by the end of the decade as
capital-side recoveries outgrow modest labor losses. A world in which the Korinek–Suh five-year
transition happens is a fiscal regime change: employment falls
{{n:presets.agi-5y.final.employment_drop_pct|.0f}} percent, the federal deficit widens by
${{n:presets.agi-5y.final.fed_deficit_delta_B|,.0f}} billion in the final year alone, and
cumulative new federal debt reaches ${{n:presets.agi-5y.final.fed_debt_B|,.0f}} billion inside ten
years. Between those poles, the scenarios differ not mainly in how much work is automated but in
*what the labor market and the firms do with it* — reabsorption rates, wage scarring, and the
disposition of the saved wage bill move the fiscal outcome as much as the displacement share does.
The Monte Carlo tornados in Section 7 make that attribution precise, and the policy analysis in
Section 8 shows that the taxes the optimal-taxation literature actually recommends recover only a
small fraction of the gap in every scenario where the gap is large.

## 1.4 How to read this document

Sections 2–5 are the model: data, kernel, dynamics, and the correctness discipline. Section 6 is
calibration. Sections 7–9 are results: the seven scenarios, the policy overlays, and validation
against external models (RAND, Windfall Trust, Acemoglu). Section 10 is the honest-limitations
table. Every model-derived number in the text, including those in this introduction, is resolved
at build time from a manifest generated by a seeded pipeline (Appendix D); numbers cannot drift
from the model without breaking the build.
