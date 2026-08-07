# The Korean fiscal system — a systems overview for the Korea port

**Purpose.** Understand how Korean public finance actually works, keyed to the five channels this
model prices, so that (a) the data-availability audit has a specification, (b) the presentation to
Korean policymakers rests on verified institutional facts, and (c) the scope of any Korea model is
decided deliberately rather than by accident.

**Status.** Compiled 2026-08-06 from primary and near-primary sources (list at the end). Figures
marked ✓ were verified this session with a citable source. Figures marked ⚠ are pending primary
verification and must not appear in an external artifact until pulled from the issuing institution.
Nothing here is model output.

**Update 2026-08-07.** The three headline primary documents were retrieved directly from NABO
(PDFs + provenance in `sources/README.md`). §2.1, §2.3 and §5.0 were corrected against them:
health baseline depletion is **2031** (not 2030), the EI statutory reserve bands are **per
account** (not fund-wide), and the long-term scenario variants are pinned at 163.2%–181.9%.
Year-by-year NHI paths (2026–2035) and the official EI baseline (2026–2029) are now in hand —
these are the fund-projector inputs.

**Standing scope decision.** Any Korea model is **national-only** and **wage-employee-only**,
stated openly. See §7 — this excludes roughly a quarter of Korean employment and that exclusion is
a headline caveat, not a footnote.

---

## 1. The finding that carries the argument

✓ **Social security contributions are Korea's single largest tax revenue source: 30.2% of total
taxation (2024)**, ahead of personal income tax at 20.1%. Total tax-to-GDP is 25.3% (2024), up from
22.8% in 2007, having fallen 1.5pp between 2023 and 2024. (OECD *Revenue Statistics 2025*.)

This is the thesis in one statistic. The largest single revenue source in the Korean state is:

1. levied exclusively on **labour**,
2. **earmarked** to funds with their own actuarial balances, not general revenue, and
3. exactly what automation removes.

No single labour-linked source dominates the US system this way. The consequence is that in Korea,
automation does not merely shift revenue from a heavily-taxed base to a lightly-taxed one — it
shifts revenue **out of actuarially-committed funds and into the general account**, and no mechanism
moves money back without new legislation. The damage is *institutional*, not merely quantitative.

**The honest complication.** Korea leans on corporate tax more than most rich countries — 14.4% of
total taxes in 2023 (OECD average 11.8%, G7 9.0%), 3.6% of GDP. ✓ So when wages convert to profits,
Korea's general account recaptures *more* than America's would. State this before someone in the
room does. It does not weaken the argument: the recapture lands in the general account while the
losses land in the pension and health funds, which is precisely the point.

---

## 2. Three earmarked funds, three deadlines — one already passed

The most useful framing for a policy audience. All three draw on the same eroding wage base.

| Fund | Reserve status | 2026 contribution rate | Horizon |
|---|---|---|---|
| **Employment Insurance** | ✓ **effectively exhausted now** | ⚠ pending | Already here |
| **National Health Insurance** | ✓ depleted **2029–2030** | ✓ 7.19% of wage | Immediate |
| **National Pension (NPS)** | ✓ depleted ~2064 (post-reform) | ✓ 9.5% → 13% by 2033 | Generational |

### 2.1 Health insurance — the near-term deadline

✓ **Primary: NABO Focus No. 162 (2026-06-09)**, 「의료개혁 1·2차 실행방안을 반영한 건강보험
재정 재추계」 (`sources/nabo-focus-162-nhi-reestimate-2026-2035.pdf`). NHI moves into **deficit
in 2026**; cumulative reserves are **depleted in 2031** on the natural-trend baseline, and **2029
— two years earlier — once the medical-reform investment plans (1st ’24.8.30, 2nd ’25.3.19) are
included**: annual balances −₩5.2tn (2026), −₩8.0tn (2027), −₩9.4tn (2028), −₩8.7tn (2029),
ten-year cumulative deficit worse by **₩27.8tn** versus baseline.

*Correction against the primary:* earlier press-derived drafts of this section said "2030 baseline";
the primary says 2031 → 2029. And the source is Focus 162 — **not** the dedicated 「2023~2032
건강보험 재정전망」 report, which is an October 2023 vintage with superseded results (deficit from
2024, depletion 2028; kept in `sources/` for its methodology and policy scenarios only).

**Focus 162 also publishes the full year-by-year paths 2026–2035** — revenue, expenditure, annual
balance, cumulative reserve, for both baseline and reform variants, with the contribution-rate
assumptions stated (1.43%/yr increases ’27–28, 2.05% from ’29, the statutory 8% rate cap binding
from 2032). This is the NHI input to the fund-depletion projector, verbatim.

**This is the number to lead with.** A senior official in 2026 discounts 2064 heavily; 2029 is
inside the planning horizon.

### 2.2 National pension — the structural case

✓ Reform passed the National Assembly **20 March 2025**, gazetted **2 April 2025**:

- Contribution rate **9% → 13%**, phased **+0.5pp/year from 2026 to 2033**; employer and employee
  each move 4.5% → 6.5%. Rate is **9.5% in 2026**.
- Income replacement rate raised to **43%** from 2026.
- Projected depletion moves from **~2056** to **~2064** — roughly **8 years bought**. Some estimates
  reach 2071 if the fund's average annual return rises from 4.5% to 5.5%.
- Fund AUM **over ₩1,200tn**.

✓ **Vintage discipline for any NPS depletion date.** NABO's long-term projection (Focus No. 92,
published 2025-02-27 — *three weeks before the reform passed*) shows the **pre-reform** path: NPS
balance negative from 2040, fund peak 2039, **depletion 2057** (and 사학연금, the private-school
pension, depleting 2042; combined post-depletion cumulative deficit 63.3% of GDP by 2072). The
~2064 figure is the **post-reform** estimate from the reform-analysis documents. Cite whichever
matches the counterfactual being discussed, never mix them; the projector's published pension path
must be a post-reform one.

The framing this unlocks:

> Korea just raised pension contributions by 44% — the first increase in 28 years, after 18 years of
> deadlock — to buy 8 years. Automation erodes the base that increase is levied on. **How many of
> those 8 years does it give back?**

That is the question the model answers, in a unit the audience already reasons in.

### 2.3 Employment Insurance — the fund that would pay for displacement is already empty

This may be the strongest single finding in this document.

✓ **Primary: NABO 결산분석시리즈 IV, FY2025 settlement analysis (labor-committee volume)** and
**「2026 대한민국 사회보험」 [표 149]** — the latter citing MOEL's own 「2025회계연도 고용보험기금
결산보고서」 (2026-06). Both in `sources/`. FY2025 figures:

- **Whole fund:** revenue ₩20.35tn, expenditure ₩20.94tn → **balance −₩592bn**. Year-end reserves
  **₩7.80tn nominal, ₩79.6bn net** of accumulated borrowings from the Public Capital Management
  Fund (공공자금관리기금).
- **Unemployment-benefit account:** spending **₩17.46tn** — a record, past ₩17tn for the first
  time; balance −₩1.78tn; reserves **₩1.73tn nominal, −₩5.99tn net of borrowings**; reserve ratio
  **0.1×** (−0.3× net). Settlement history 2021–2025: ratios 0.3 / 0.3 / 0.3 / 0.2 / 0.1.
- ✓ *Refinement against the primary:* the Employment Insurance Act (고용보험법 §84, quoted in the
  annual) sets reserve bands **per account**, not fund-wide: **1.5–2× of annual spending for the
  unemployment-benefit account**, 1–1.5× for the employment-stabilization/vocational account. The
  stabilization account is at **1.7×** (above its band, +₩1.2tn balance, ₩5.9tn reserves) — it is
  precisely **the account that pays displacement benefits** that sits at 0.1×. Sharper than the
  press version, and stronger for the argument.
- ⚠ "Short of the statutory level for **16 consecutive years**" remains press-sourced (한국경제);
  the 2021–25 settlement ratios above are consistent with it but only cover five years.
- ✓ The stated cause: **employment fell, so contribution revenue fell, while benefit spending rose.**
- ✓ The official near-term baseline exists: NABO's mid-term projection ([표 151] in the annual,
  Oct 2025, from 2024 actuals) shows whole-fund reserves rebuilt to ₩21.8tn by 2029 — but via
  planned PCMF borrowings (₩750bn more into the benefit account in 2026) and the stabilization
  account's surplus, not the benefit account healing; and FY2025's outturn already undershot it.
  This is the published path the projector erodes for EI.

Note what that last line is. It is *this model's mechanism*, already running in Korea for
demographic and cyclical reasons, before AI displacement at scale. The argument writes itself:

> The fund that would pay for AI displacement holds one-tenth of its legally required reserves, and
> the reason is that Korea already has fewer workers paying in and more people drawing out.

(Resolved 2026-08-07: the 2026 EI and Industrial Accident rates are confirmed in §3 Channel 2, and
the fund figures above are now primary-sourced — the earlier press-coverage caveat no longer
applies.)

---

## 3. Channel-by-channel map to the model

### Channel 1 — Personal income tax (소득세): weaker and far more concentrated than the US

✓ Latest official figures (NTS, 2023 tax year):

- **33% of wage earners paid zero income tax** — 6.89m of 20.85m filers.
- Down from **48.1% in 2014**, after the deduction-to-credit restructuring.
- Earning **>₩80m/yr: only 0.13% exempt**. Earning **≤₩50m/yr: 45.6% exempt**.
- By age: 20s **49.1%**, 30s 28.7%, 40s 26.0%, 50s 26.6%.
- ✓ **The top 1% of earners pay roughly 31% of all income tax.**

**Modelling consequence.** Korean income tax revenue is concentrated in the upper wage distribution
to a greater degree than America's — and that is the segment most exposed to cognitive automation.
The income-tax channel carries *less* of the total burden than in the US (19.8% of taxes vs OECD
23.7% ✓) but is *more* sensitive to which occupations automate.

✓ **The full wage-earner computation, verified 2026-08-07** (NTS 종합소득세 세율 page, primary;
cross-checked against KOTRA *Taxation in Korea 2025*, local copy in `sources/`). Four stages:

1. **Wage & salary income deduction** (근로소득공제, ceiling ₩20m): 70% of gross up to ₩5m;
   ₩3.5m + 40% of the excess to ₩15m; ₩7.5m + 15% to ₩45m; ₩12m + 5% to ₩100m; ₩14.75m + 2%
   above. Then the **basic deduction**: ₩1.5m per taxpayer and per dependent.
2. **Bracket schedule** (2023–2025 tax years, current law — watch for a 2026 amendment):

   | Tax base | Rate | | Tax base | Rate |
   |---|---|---|---|---|
   | ≤ ₩14m | 6% | | ₩150–300m | 38% |
   | ₩14–50m | 15% | | ₩300–500m | 40% |
   | ₩50–88m | 24% | | ₩500m–1bn | 42% |
   | ₩88–150m | 35% | | > ₩1bn | 45% |

3. **Wage-earner tax credit** (근로소득세액공제) against the computed tax: 55% of the first
   ₩1.3m, ₩715k + 30% beyond — capped by gross wage: ≤₩33m → ₩740k; ₩33–70m →
   max(₩740k − 0.8%·excess, ₩660k); ₩70–120m → max(₩660k − 50%·excess, ₩500k); >₩120m →
   max(₩500k − 50%·excess, ₩200k). This credit is what zeroes out a third of wage earners.
4. ✓ **Local income surtax** (지방소득세): **+10% of the national liability** (resolves the
   earlier ⚠).

This is the minimum faithful engine for Channel 1: deduction → brackets → credit → +10%. Personal
credits beyond the basic deduction (child credit ₩150k+, insurance/medical/card credits) shift
individual liabilities but are second-order for cell-level means; disclose the simplification.

**Engine vs published aggregates** (`fiscal_model/korea_tax.py` over the 209-cell table, 2025):
aggregate PIT+local from covered workers ₩57.9tn — the right ballpark of published wage-income-tax
revenue given ~56% worker coverage skewed to larger firms. Two divergences to disclose, both
conservative for the argument: the engine's zero-tax share is ~2% against NTS's 33% (no dependents
or discretionary credits modelled; cell means hide within-cell dispersion), so low-wage income-tax
losses are *over*stated — i.e. the "low-wage automation hits the funds, not income tax" claim is
understated, not manufactured. And "top 1% pays 31%" cannot be resolved below cell granularity
(the top cell holds ~5% of workers; engine: top cell pays 23.3%) — quote NTS for concentration
facts, never the model.

### Channel 2 — Social insurance (the payroll engine): the dominant channel

✓ 2026 rates:

| Scheme | Rate | Base / notes |
|---|---|---|
| National Pension | **9.5%** (4.75 + 4.75) | Capped — see below; → 13% by 2033 |
| National Health Insurance | **7.19%** (up from 7.09%) | |
| Long-Term Care | **0.9448% of wage** | = 13.14% of the NHI contribution |
| Employment Insurance | **1.8%** (0.9 + 0.9) | Unemployment-benefit portion; frozen for 2026 |
| Industrial Accident | **1.47%** average | Employer-only, industry-rated; held at 2025 level |
| **Combined (2026)** | **≈ 20.9% of payroll** | vs US FICA 15.3% |

✓ All 2026 rates now confirmed. Also note the wage-claim guarantee levy (임금채권부담금) rising
0.6‰ → 0.9‰ — its first adjustment since 2015. EI carries additional employer-only components for
employment stabilisation and vocational training beyond the 1.8% unemployment-benefit rate.

**Combined burden reaches roughly 24.4% of payroll by 2033** as the pension phase-in completes —
against US FICA's flat 15.3%. Every point of it is levied on labour.

✓ **The pension base is capped.** Standard monthly income (기준소득월액) ceiling is **₩6.59m from
July 2026** (₩6.17m previously, up from ₩5.90m in 2024); floor ₩410k. The ceiling is reset annually
by MOHW each March, effective July, tracking the 3-year average income growth of subscribers.

✓ **The NHI base is also bounded, but inertly so** (verified 2026-08-07, 「2026 대한민국 사회보험」
fn. 275): the monthly contribution ceiling is 30× the year-before-last average workplace
contribution — **₩9,183,480/month in 2026 including the employer share**, i.e. a salary-equivalent
of ≈ ₩127.7m/month at 7.19%; floor ₩20,160/month. That ceiling sits ~14× above the model's top
cell wage and cannot bind — so in the engine the pension is `capped` and health is `flat`, and
"which institution takes the hit" turns on the **pension** cap alone. (The pension floor —
₩410k/month — binds only below the bottom bracket midpoint; effect ≤ ~₩1k/month/worker,
disclosed and not modelled.)

**This ceiling generates a real asymmetry.** It binds at roughly twice median earnings, so:

- Automating a **high-wage** worker → large income-tax loss, only the *capped* pension loss →
  damage lands on the **general account**.
- Automating a **low-wage** worker → negligible income-tax loss, *proportionally full*
  social-insurance loss → damage lands on the **earmarked funds**.

Which occupations automate therefore determines **which institution takes the hit**, not just how
much. That is a distinction this model can produce and one a finance ministry can act on.

**Engine implication.** `rates.PayrollFICA` is rate- and cap-parameterised (no hardcoded 6.2%), but
its *component schema* is fixed: the constructor pulls exactly four rows by name-match
(`contains("OASDI")`, `fullmatch("Medicare")`, `"single"`, `"MFJ"`). Korea's four schemes either get
mapped onto those names or the constructor generalises to a component list. Half a day, not zero —
but no new math.

### Channel 3 — Consumption (부가가치세): simpler than the US, with headroom

✓ Single national VAT at **10%**, broad-based, unchanged since 1977. **15.3% of total tax revenue
(2023) against an OECD average of 20.5%** — Korea is a *low*-VAT country by OECD standards.

Two consequences. First, this **replaces 51 state sales-tax regimes with one parameter** — the
consumption channel gets genuinely simpler than the US version. Second, VAT is the primary
instrument Korinek recommends for shifting taxation off labour, and Korea has more headroom on it
than most peers. **The existing `fed-vat` overlay ports as a live Korean policy question**, not a
hypothetical.

⚠ Verify: exemption structure, zero-rating, the simplified-taxpayer regime, and whether any rate
increase is politically live.

### Channel 4 — Corporate (법인세)

✓ 14.4% of total taxes (2023), 3.6% of GDP — above OECD and well above G7. Progressive bracket
structure, unusual internationally.

✓ **Rates rise by 1pp in every bracket for income accruing from 2026** (filed March 2027):

| Tax base | Rate (2026 onward) | Incl. local income tax |
|---|---|---|
| ≤ ₩200m | **10%** | 11% |
| ₩200m – ₩20bn | **20%** | 22% |
| ₩20bn – ₩300bn | **22%** | 24.2% |
| > ₩300bn | **25%** | 27.5% |

Effective burden including the local income surtax (10% of the national liability) runs **11%–27.5%**.
Note the direction: Korea cut corporate tax in 2023 and is **raising it back in 2026** — relevant
context for any argument about where automation-era revenue should come from. Korean commentary
also treats corporate-tax revenue volatility as a structural budgeting problem.

Note the **SWF overlay has a natural Korean vehicle**: the National Pension Fund is among the
world's largest public pension funds (>₩1,200tn ✓) and already a major institutional equity holder.
"Let the fund capture the automation windfall" is a question about NPS mandate and asset allocation,
not a thought experiment.

### Channel 5 — Transfers and outlays

**Basic Pension (기초연금)** ✓ — the demographic outlay that dominates the welfare budget:

- 2026 standard payment **₩349,700/month**, up from ₩342,510 in 2025 (+2.1%, CPI-indexed).
- Eligibility set to cover the **bottom 70% of the 65+ population** by income and assets. 2026
  selection thresholds: **₩2.47m/month single household, ₩3.952m couple**.
- **2024 budget ₩24.4 trillion** (national + local combined) — **Korea's largest single welfare
  expenditure**.
- ⚠ A policy to raise the amount toward ₩400,000 for low-income elderly first appears to be in
  train — verify status and phasing.

✓ **Korea's elderly poverty rate was 38.1% (2022) against an OECD average of 14.2%** — roughly
three times the OECD level, and the highest in the OECD. This single number explains why the Basic
Pension exists, why it grows automatically with the 65+ population, and why §7.3 matters: the
informal old-age safety net is doing work the formal system does not.

**Earned Income Tax Credit (근로장려금)** ✓ — 2026 parameters:

| Household type | Max credit | Income ceiling |
|---|---|---|
| Single | **₩1.65m** | ₩22m |
| Single-earner | **₩2.85m** | ₩32m |
| Dual-earner | **₩3.30m** | ₩44m |

Asset test: household total under **₩240m**; between ₩170m and ₩240m only **50%** is paid. Regular
application window 1–31 May 2026. ⚠ Total cost and recipient count still to confirm.

**Public social spending** ✓ — the structural context for everything above: Korea spent
**₩337.4tn, 15.2% of GDP (2021)**, ranking **34th of 38 OECD countries** against an OECD average of
**22.1%** — about 69% of the average. Only Ireland, Costa Rica, Türkiye and Mexico spend less. But
Korean commentary consistently notes the **growth rate is among the OECD's highest.**

That combination — near-lowest level, near-highest growth — is the frame a Korean policymaker
already lives in: obligations are arriving faster than the system was built for, and the
contribution base is what has to carry them.

⚠ Still unverified: National Basic Livelihood Security (국민기초생활보장) and its
생계/의료/주거/교육 components; the NHI government subsidy.

---

## 4. The intergovernmental formula — the Korean analogue to the state-austerity amplifier

The US model's signature mechanism (51 states must balance within-year, so state austerity feeds
back as layoffs) has **no direct Korean counterpart** — Korean local governments are not independent
balanced-budget constraints. But it is **not** true that shocks are simply absorbed nationally.

✓ Local finance is dominated by **statutory, formula-linked central transfers**:

| Transfer | Share of national internal taxes (내국세) |
|---|---|
| Local Share Tax (지방교부세) | **19.24%** (+ all comprehensive real-estate tax, + 45% of tobacco excise) |
| Local Education Subsidy (지방교육재정교부금) | **20.79%** (raised from 20.46%) |
| **Combined** | **40.03%** |

✓ The Local Education Subsidy alone supplies about **70% of local education finance revenue**, and
Korean sources state the linkage explicitly: the transfer scales with national internal tax receipts.

**This is better for modelling than the US mechanism, not worse.** It is one statutory elasticity
rather than 51 political reaction functions. A national wage-base erosion of X% flows to local
budgets at roughly 0.4× **mechanically, with no decision anywhere**. The provincial layer can be
dropped entirely (correct for Korea) while still saying something quantified about local government.

Worth knowing as colour: the education subsidy is formula-linked to national tax revenue while the
school-age population collapses — a well-known Korean fiscal absurdity. Not the argument, but it
signals system literacy.

⚠ Verify: national subsidy programmes (국고보조금), local own-source revenue share, and whether
local governments face binding within-year balance requirements.

---

## 5. Demographics — the counterfactual problem

✓ Statistics Korea, 장래인구추계 2022–2072 (the standard reference projection):

- Working-age share (15–64): **71.1% (2022) → 66.6% (2030) → 51.9% (2050) → 45.8% (2072)**
- Working-age population falling **~320k/year in the 2020s, ~500k/year in the 2030s**
- 65+ share: **20% (2025) → 30% (2036) → over 40% (2050)**; 65+ passes 10m in 2025, peaks at 18.91m
  in 2050, easing to 17.27m by 2072
- Old-age dependency: **24.4 elderly per 100 working-age (2022) → 104.2 (2072)**

### 5.0 The official long-term fiscal baseline

✓ NABO publishes a **2025–2072 long-term fiscal projection** (장기재정전망); MOEF runs a parallel
**3rd Long-Term Fiscal Projection (2025–2065)**. NABO's framing is directly useful: Korea has
entered a **super-aged society** (초고령사회, 65+ above 20%), and a rising elderly share produces
*slower potential growth, a weakening revenue base, and rising welfare spending* — the three
pressures this model prices.

✓ NABO's baseline (report published 21 Feb 2025), assuming current law and institutions hold:

- National debt **₩1,270.4tn (2025) → ₩7,303.6tn (2072)** in constant prices.
- **Debt-to-GDP 47.8% (2025) → 173.0% (2072).**
- The potential growth rate falls toward **0.3%** by 2072.

✓ **Scenario variants pinned from the primary** (NABO Focus No. 92, 2025-02-27,
`sources/nabo-focus-92-longterm-2025-2072.pdf`): 2072 debt-to-GDP is **181.9%** under the *low*
population variant (+9.0pp vs baseline), **163.2%** under *high* (−9.7pp), and **176.6%** if
discretionary spending grows faster than the government's fiscal-management plan (+3.7pp). The
99.3%–161.9% figures seen earlier in secondary coverage do not appear in the primary and are
dropped. Focus 92 also tabulates the full aggregates (revenue, mandatory/discretionary spending,
consolidated and managed balances, social-security-fund balance) at 2025/30/40/50/60/72. **Quote
the 173.0% baseline; this projection is the baseline any Korean result should be expressed as a
delta against.**

**Model implication — this is the one genuine mechanism change.** `dynamics_v2.py` holds
`baseline_emp = v1.emp0.sum()` as a scalar, and the C1 conservation gate pins per-cell totals to
`emp0`. Holding employment flat while the working-age population falls by a third makes the no-AI
counterfactual **a world that cannot happen**, and every delta measured against it is mis-scaled.

The fix is conservation against a **path** rather than a constant, anchored to the Statistics Korea
projection — no free parameter added. It passes the necessity test: it fixes a specific wrong
number, sits on the path to the headline, and is externally anchored. It is also delicate, because
C1 is the model's credibility mechanism, so it should not be rushed.

### 5.1 Cancellation versus compounding — settle this verbally, not by modelling

The obvious objection is "Korea *needs* automation; we have no workers." It does not require a model
to answer:

- **Cancellation** operates on **real output**: automation substitutes for workers who won't exist.
- **Compounding** operates on the **tax base**: Korean public finance is funded by contributions
  *per employed worker*, not by output.

These act on different variables, so they do not net out. Hence the finding:

> **Even in the optimistic scenario — where AI rescues Korea from labour shortage and output is
> fine — the fiscal system still breaks, because it is wired to labour rather than to output.**

That is a transition-risk argument in the precise sense an AI-safety diplomacy audience cares about:
it does not require AI to go badly. It requires AI to go *well* and the fiscal plumbing to stay as
it is.

The declining baseline (§5) is needed for **counterfactual correctness**, not to represent
cancellation. Keep the two separate.

---

## 6. Existing Korean research — and the gap this work fills

- **KDI**, 「인공지능으로 인한 노동시장의 변화와 정책방향」 (English edition published; user is
  preparing a translation — not summarised here deliberately). Reported findings include ~12% of
  jobs (3.41m) at high replacement risk, ~38.8% of jobs with >70% of tasks automatable as of 2023,
  and an estimate of ~256k jobs/year over a decade. KDI builds a **routinisation index on the 2020
  Korea Dictionary of Occupations (한국직업사전)**, scoring occupations 0–2 on data/people/objects.
- **OECD**, *Artificial Intelligence and the Labour Market in Korea* (Oct 2025). Most-exposed
  occupations are white-collar — IT, business, managerial, science/engineering. Observed negative
  employment effects in Korea concentrate among **younger, low- to medium-skilled** workers.
  ✓ **Korean AI adoption is low by international standards: 31% of SMEs vs over 50% in Germany** —
  a direct calibration input implying Korea sits earlier on the adoption curve than peers.
- **East Asian Economic Review**, *Analysis of Artificial Intelligence Exposure Across Industries in
  South Korea and the United States* — a direct KR–US exposure comparison.
- **IMF**, Selected Issues Paper 2025/013, *Transforming the Future – The Impact of AI in Korea*.

**Two things follow.**

**(a) The exposure-crosswalk risk is much smaller than feared.** Korea-native AI exposure measures
exist on Korean occupational classifications. Using a Korean-authored measure is also far better
rhetorically than importing US O*NET/SOC scores — it removes the most obvious line of attack. A
KSCO→ISCO→SOC crosswalk becomes a fallback, not the critical path.

**(b) The gap is the fiscal channel.** This body of work addresses **jobs, wages and skills**. None
of it addresses **the tax base**. KDI has told Korean policymakers what happens to employment.
Nobody has told them what happens to the health fund or the pension fund. That is the sentence that
justifies the whole exercise.

Note the tension to be ready for: *exposure* (white-collar, per OECD) and *realised displacement*
(younger and lower-skilled, per observed Korean data) are different measures. Do not conflate them.

---

## 7. Self-employment — the scope decision, and why it is a headline caveat

✓ **Korea's self-employment rate is 23.9% (2021)**, 6th highest in the OECD, down from 28.8% in
2010. The OECD measure includes employers with employees, solo self-employed, and unpaid family
workers. That is roughly **three to four times the US rate**.

So a wage-employee model covers about **three-quarters of Korean employment**. This must be stated
prominently. 자영업자 are a central political constituency and a chronic policy concern; a Korean
policymaker will raise them early. *"Deliberately scoped to wage employees, ~76% of employment,
self-employed treated qualitatively"* is a strong answer. Being caught without one is not.

### 7.1 Composition — highly concentrated

✓ Roughly two-thirds of self-employed businesses sit in three sectors: **wholesale/retail (~30%),
accommodation/food service (~18%), transport (~16%)**, plus personal services and construction.
Among 60+ entrants over 2014–2024, **61.7% went into transport/warehousing, food/accommodation,
retail or construction**. The sector is structurally fragile — excessive competition, thin margins,
and ✓ about **₩141tn of self-employed debt**.

✓ Data exists: KOSIS 경제활동인구조사 (Economically Active Population Survey) non-wage-worker
supplements, by industry, and — importantly — splitting **고용원이 있는 자영업자** (with employees)
from **고용원이 없는 자영업자** (solo).

### 7.2 Two rounds, running at different speeds on different channels

**Round one — the self-employed are the automators.** ✓ Kiosks are in roughly one of every two to
three outlets at major fast-food chains; **42.9% of convenience stores and supermarkets and 40.0%
of coffee/retail** report considering unmanned automation. The driver is explicit: ✓ **92.7% of
small business owners with employees** said minimum-wage increases cut operating profit. Korea's
first automation wave displaced the **wage employees of the self-employed** — part-timers — and that
**is inside the model's scope**.

**Round two — the owner's own function goes.** Korean trade coverage describes the shift from kiosks
to "AX": AI handling ordering, inventory, demand forecasting, marketing and cooking — *technology
that runs the store itself* rather than technology that replaces a counter worker. This automates
the owner-operator and sits outside a wage-employee model.

**Timing is not one clock — it is the model's two channels at different speeds.** The
self-employment mix splits across exactly the channels the engine already separates:

| Self-employment sector | Channel | Speed |
|---|---|---|
| Retail, food service, personal services | Cognitive / service automation | Fast — already underway |
| Transport, construction | Physical / robotics | Slow — gated by `robotics_lag` |

Transport and construction are self-employment-heavy but **not strongly AI-exposed**; their second
round waits on robotics, which is precisely what `robotics_lag` governs. Do not present the two
rounds as a single timeline.

### 7.3 Why this is worse than it looks: self-employment as the old-age safety net

Elderly Koreans enter low-barrier food and retail self-employment because pension income is
inadequate — Korea has the OECD's highest elderly poverty rate. **Self-employment in these sectors
functions as Korea's de facto old-age safety net.**

That is this model's **finite refuge**, and the Korean version binds far harder than the American
one: the refuge is already saturated, already indebted, and already the sector where automation is
furthest advanced. If automation closes it, displaced and elderly workers do not land in
low-exposure service work — they land on **Basic Pension and the National Basic Livelihood Security
system**, i.e. directly on the outlay side of the same budget.

The mechanism built for the US transfers directly. The parameters are simply harsher. This is
probably the single most policy-relevant interaction in the Korean case, and it is one the existing
engine can express.

### 7.4 Fiscal treatment differs

The self-employed participate in the pension as **지역가입자** (regional subscribers), paying the
full contribution themselves with no employer match; under-reporting of self-employed income is a
long-standing equity issue in the Korean pension debate. ⚠ Verify mechanics and the scale of
under-reporting before relying on this.

---

## 8. The owner-operator question (US model robustness)

Raised while reviewing the US model; the answer also constrains Korea.

✓ **OEWS excludes** the self-employed and owners/partners in *unincorporated* firms, but **includes**
"salaried officers, executives, and staff members of *incorporated* firms." So sole proprietors and
partnerships were never in the model, while **S-corp and C-corp owner-officers taking W-2 salary are
in the data as ordinary employees** — the IRS "reasonable compensation" rule actively forces those
owners onto payroll.

For such a person, the firm side is right (the saved wage routes to retained profit) but the worker
side is wrong (they are put on UI and made transfer-eligible, when the "saved" profit is their own
pocket). The model double-counts.

✓ **Smith, Yagan, Zidar & Zwick (QJE 2019)** cuts against the intuition that top income is safe
because it is capital: linking 11m firms to owners, they find **~75% of pass-through profit is
owners' labour income**, and pass-through profit **falls by roughly three-quarters after the owner
retires or dies**. Top earners are the "working rich" — human capital flowing through a business.

So the correct statement is not "their income is safe" but:

> For owner-operators, automation **converts wage income into profit income**. The income tax
> largely survives; the payroll tax does not.

That is a composition error, and note where it bites: in Korea, where social insurance is 30.2% of
all taxation, "income tax survives, payroll tax does not" is exactly the damage pattern that matters
most. It **strengthens** the earmarking argument.

**Verdict.** Fixing this properly needs an owner-officer share by occupation, for which there is no
clean dataset — it would add a free parameter calibrated against nothing, and **fails the necessity
test as a mechanism change**. US magnitude is roughly 3% of wage employment (~5m S-corps),
concentrated in high-wage high-exposure occupations: small on jobs, larger on the income-tax channel
specifically. The effect is also **self-limiting** — the owner's labour-attributable share shrinks
as a fraction of total profit precisely in the scenarios where automation is largest.

**Disposition: a few sentences in the report, plus a bounded sensitivity if cheap. Not a model
change.**

---

## 9. Data availability for modelling

### 9.0 Probe results (2026-08-06) — access solved, granularity is the constraint

Attempted acquisition rather than confirmation. Findings:

**Access: SOLVED.** `kosis.kr` deep links redirect to an SSO session handshake and the English
category tree is a JS accordion that resists scripted navigation. **But MOEL mirrors the same
tables at `stathtml.moel.go.kr/statHtml/statHtml.do?orgId=118&tblId=<ID>&conn_path=I2` with no
login, no SSO, and the data rendered as plain scrapeable HTML.** That is the acquisition route —
no microdata application needed for the aggregate tables.

**Tables located and verified live:**

| Table ID | Content | Vintage | Granularity |
|---|---|---|---|
| `DT_118N_PAYN42` | **Industry** × education × age × sex: mean wage + worker count | ✓ 2020–2025, updated 2026-04-30 | 19 industries |
| `DT_118N_PAYM39` | **Occupation** × sex × **wage bracket** × age: worker count + hours | ✓ 2020–2025, updated 2026-04-30 | **10 occupations × 25 wage brackets** |
| `DT_118N_PAYM22` | **Occupation** × education × age × sex: mean wage + worker count | ⚠ **2009–2015 only**, last updated 2017 | 10 occupations (KSCO 6th) |
| `DT_118N_LCE0001` | Employment type × wage/hours | current | by employment type |

**The binding constraint is occupation granularity: the public tables carry only the 10 KSCO
major groups**, not the 세분류 (minor-group) level assumed in §10. Against the US model's 832 SOC
cells that is very coarse. Two mitigations:

1. `PAYM39` is **current and gives a joint distribution, not a mean** — 10 occupations × 25 wage
   brackets × 11 age groups × sex. For a progressive-tax model a wage *distribution* is strictly
   better than a mean, and 10 × 25 = 250 cells sits above the 50–150 the plan budgeted. Combined
   with `PAYN42`'s 19 industries this is a workable cell structure.
2. Finer KSCO requires a **microdata application** (마이크로데이터신청 via `laborstat.moel.go.kr`)
   — Korean-language process, non-trivial turnaround. **Route via the diplomacy organisation** if
   finer occupation detail turns out to be necessary.

**2025 totals (from `PAYM39`, for calibration):** 12,413,858 wage workers covered — managers
120,892; professionals 3,669,625; clerks 3,447,778; service 960,008; sales 561,179; agriculture
28,684; craft 758,694; machine operators 1,835,977; elementary 1,031,019. Mean monthly wage
₩4,482k (`PAYN42`). Note this is an **establishment survey**: ~12.4m against roughly 22m wage
workers nationally, so coverage is partial and skews to larger firms — a caveat to disclose, and
a second reason the self-employed exclusion (§7) matters.

**Consequence for exposure mapping:** 10 major groups is coarse for scoring AI exposure. This
raises the value of KDI's routinisation index (built on the Korea Dictionary of Occupations, §6)
over any crosswalk — but the *join* will still be at major-group level unless microdata lands.

### 9.1 Other sources

✓ **Occupational employment and wages**: MOEL's 고용형태별근로실태조사 (Survey on Labour Conditions
by Employment Type), published on KOSIS (orgId 118), classified by **KSCO (한국표준직업분류)**,
with wage *and* employment. The genuine OEWS analogue — see §9.0 for what is actually reachable.

✓ **AI exposure**: Korea-native measures exist (§6) — KDI's routinisation index on the Korea
Dictionary of Occupations; the EAER KR–US industry comparison. Prefer these to a SOC crosswalk.

✓ **Population projections**: Statistics Korea 장래인구추계 2022–2072, with low/medium/high variants.

✓ **Fiscal projections**: NABO publishes long-term fiscal outlooks and a dedicated 2023–2032 health
and long-term-care projection.

⚠ **Still to confirm**: English-language access and licensing for KOSIS extracts; granularity of the
occupation × wage cross-tabs; whether employment and wages are jointly available at the same
KSCO level; the KSCO↔ISCO-08 correspondence table as fallback.

---

## 10. What ports, what changes, what is excluded

**Ports unchanged** (country-agnostic in structure): the fiscal kernel, the 7-state worker
stock-flow, the disposition router, the survivor-wage and reabsorption engines, the MC/tornado
apparatus, the conservation invariants, and the entire web layer.

**Data swap, no new math**: payroll/social-insurance parameters (with the component-schema caveat,
§3 Channel 2), income tax schedules, VAT, corporate rates.

**Genuine mechanism change**: the declining baseline (§5) — conservation against a path, anchored to
Statistics Korea. Touches C1, so unhurried.

**Simplifications relative to the US model**: one national VAT replaces 51 state sales-tax regimes;
the provincial layer is dropped entirely and replaced by the 40.03% statutory transfer elasticity
(§4). The Korean model is *structurally simpler* than the US one while being sharper in message.

**Explicitly excluded and disclosed**: the self-employed (~24% of employment, §7); behavioural
responses to instruments; task creation; cancellation-as-rescue (answered verbally, §5.1).

**Reduced form**: national-only, on the order of 50–150 occupation cells rather than 33,000
occupation × state cells. "Deliberately coarse, transparently so" is defensible before this
audience; "approximately right about your provinces" is not.

---

## 11. Presentation implications

- **Lead with the health fund (2029–2030), not the pension.** It sits inside the audience's
  planning horizon. Use the pension for the structural long-run case and the "8 years bought"
  framing.
- **Express results as a shift in a depletion date**, not a won-denominated fiscal delta. Korea
  already reasons in those units, it needs no explanation, and it survives a presenter who does not
  know the model internals — which matters, since the diplomacy organisation may deliver this.
- **The one-pager must carry its own sources inline**, so the answer to "where is that from?" is
  "it is on the sheet."
- **The website should open on a Korea default that tells the story without touching a slider.**
  A presenter improvising with levers in front of officials generates numbers nobody can defend.
- Fewer claims, more heavily sourced. A presenter can deliver three well-cited findings; they
  cannot improvise caveats.

---

## 12. Open items — after two research passes

Closed 2026-08-06: Basic Pension, elderly poverty, Employment Insurance fund status and 2026 rates,
industrial-accident rate, NABO long-term projection baseline, corporate tax brackets, local income
surtax, EITC parameters, public social spending vs OECD.

**Closed 2026-08-07 — the three headline primary documents, retrieved directly from NABO**
(`sources/README.md` has provenance and retrieval mechanics; the "PDF fetching defeated the
tooling" finding from 08-06 was wrong for NABO — a browser User-Agent suffices):

1. ~~Employment Insurance fund accounts~~ → NABO FY2025 settlement analysis (labor-committee
   volume) + 「2026 대한민국 사회보험」 citing MOEL's FY2025 fund settlement report. §2.3 corrected
   (statutory bands are per-account) and now primary-sourced throughout.
2. ~~NABO 2025–2072 long-term projection~~ → Focus No. 92: scenario variants pinned (§5.0);
   pre-reform NPS depletion 2057 noted (§2.2). The full report PDF remains optional nice-to-have.
3. ~~NABO health projection~~ → Focus No. 162 (2026-06-09), which supersedes the 2023–2032 report:
   §2.1 corrected (baseline depletion 2031, not 2030), year-by-year 2026–2035 paths in hand.

**Remaining, in priority order:**

1. National Basic Livelihood Security components; NHI government subsidy; EITC total cost and
   recipient count. (The 「2026 대한민국 사회보험」 annual in `sources/` likely covers the NHI
   subsidy — check before searching elsewhere.)
2. The "16 consecutive years below the statutory reserve level" claim (§2.3) — still press-only;
   five years of settlement ratios confirm the recent tail.
3. VAT exemption and zero-rating structure; the simplified-taxpayer regime.
4. Self-employed pension treatment (지역가입자) and the scale of income under-reporting (§7.4).
5. Basic Pension increase toward ₩400,000 for low-income elderly — status and phasing.
6. KOSIS extract licensing, English access, and the occupation × wage cross-tab granularity (§9).
7. Optional: full 2025–2072 long-term report PDF; NABO Focus No. 163 (2026-06-11) on comparative
   NHI revenue structures — directly relevant to the VAT/funding-mix argument.

**The pattern has inverted.** All three headline claims — EI exhaustion, health depletion 2029/31,
the long-run debt path — now rest on the issuing institution's own documents, and two of them carry
the published fund paths the depletion projector needs as inputs. What remains is parameter-level
verification, not headline-level.

---

## Sources

Verified this session. Korean-language sources noted.

**Primary documents retrieved 2026-08-07** — PDFs in `sources/`, provenance and download FIDs in
`sources/README.md` (all KR):
- NABO Focus 제92호 — 2025~2072년 NABO 장기재정전망 (2025-02-27)
- NABO Focus 제162호 — 의료개혁 1·2차 실행방안을 반영한 건강보험 재정 재추계 (2026-06-09)
- NABO Focus 제84호 — 의료개혁과 비상진료대책을 반영한 건강보험 재정전망 (2024-12-20)
- NABO — 2023~2032년 건강보험 재정전망 (full report, 2023-10; superseded, kept for methodology)
- NABO 결산분석시리즈 IV — 2025회계연도 결산 위원회별 분석 [기후에너지환경노동위원회] (2026)
- NABO — 2026 대한민국 사회보험 (annual, 452 pp)

**Pension reform and NPS**
- [Korea Herald — Assembly passes pension bill](https://www.koreaherald.com/article/10446290)
- [OECD *Pensions at a Glance 2025*: Korea](https://www.oecd.org/en/publications/pensions-at-a-glance-2025-country-notes_8a53ef12-en/korea-republic-of_5cd52913-en.html)
- [SSA *International Update*, April 2025](https://www.ssa.gov/policy/docs/progdesc/intl_update/index.html)
- [Lockton — NPS contribution rate increase](https://global.lockton.com/us/en/news-insights/south-korea-to-increase-national-pension-service-contribution-rates)
- [정책브리핑 — 2025년 연금개혁의 역사적 의미](https://www.korea.kr/news/policyNewsView.do?newsId=148941915) (KR)
- [KDI — 2025년 「국민연금법」 개정의 재정 및 정책효과 분석](https://eiec.kdi.re.kr/policy/domesticView.do?ac=0000195652) (KR)
- [NPS — 기준소득월액 상·하한액](https://www.nps.or.kr/pnsgdnc/newgdnc/getOHAE0001M1.do?menuId=MN24000897&pstId=NE202500000000030479) (KR)

**Health insurance**
- [보건복지부 — 2026년 건강보험료율 7.19% 결정](https://www.mohw.go.kr/board.es?mid=a10503010100&bid=0027&act=view&list_no=1487279) (KR)
- [NHIS — Contribution Rate (English)](https://www.nhis.or.kr/english/wbheaa02500m01.do)
- [경향신문 — 건강보험 재정 2026년 적자](https://www.khan.co.kr/article/202508181700001) (KR)
- [청년의사 — 누적 준비금 소진 2년 빨라진다](http://www.docdocdoc.co.kr/news/articleView.html?idxno=3039918) (KR)
- [국회예산정책처 — 2023~2032 건강보험 및 노인장기요양보험 재정전망](https://www.nabo.go.kr/ko/notice/releasesView.do?key=2507040045&idx=8108) (KR)

**Employment insurance**
- [뉴스1 — 고용보험기금 적자 6000억 육박, 실업급여 지출 역대 최대](https://www.news1.kr/economy/employment-labor/6196765) (KR)
- [헤럴드경제 — 고용보험 적자 5920억, 실업급여 17.5조](https://biz.heraldcorp.com/article/10771084) (KR)
- [한국경제 — 16년째 적립금 미달](https://www.hankyung.com/article/2025111323387) (KR)

**Transfers and outlays**
- [복지로 — 2026년 기초연금 인상](https://www.bokjiro.go.kr/ssis-tbu/cms/pc/news/news/1307148_1114.html) (KR)
- [기초연금 2026년 월 최대 34만 9700원, 선정기준액 상향](https://v.daum.net/v/20260211181635083) (KR)
- [서울신문 — 사회복지지출 GDP의 15.2%, OECD 최하위권](https://m.go.seoul.co.kr/news/society/2025/04/09/20250409500247?cp=go) (KR)
- [무역뉴스 — 복지지출 OECD 최하위권, 증가속도는 최상위](https://www.kita.net/cmmrcInfo/cmmrcNews/cmmrcNews/cmmrcNewsDetail.do?nIndex=62235) (KR)
- [위기브 — 2026년 근로장려금 자격 요건](https://www.wegive.co.kr/wezine/detail/1651) (KR)

**Social insurance rates**
- [MOEL — 2026년 평균 산재보험료율 1.47% 유지](https://www.moel.go.kr/news/enews/report/enewsView.do?news_seq=18810) (KR)
- [고용노동부 — 사업종류별 산재보험요율 (공공데이터)](https://www.data.go.kr/data/15068737/fileData.do) (KR)

**Corporate tax**
- [국세청 — 법인세 세율 (2026년 이후)](https://www.nts.go.kr/nts/cm/cntnts/cntntsView.do?cntntsId=7746&mi=2372) (KR)

**Long-term fiscal projections**
- [NABO — 2025~2072년 장기재정전망 (PDF)](https://www.nabo.go.kr/system/common/JSPservlet/download.jsp?fBid=68&fCode=33318450&fMime=application/pdf&flag=bluenet) (KR)
- [세계일보 — 2072년 국가채무 7303조, 성장률 0.3%](https://www.segye.com/newsView/20250223504965) (KR)
- [NABO — 2025~2072년 장기재정전망](https://eiec.kdi.re.kr/policy/domesticView.do?ac=0000192610) (KR)
- [NABO — 2025 대한민국 재정](https://nabo.go.kr/q/CYlCJLf5) (KR)
- [MOEF — 제3차 장기재정전망(2025~2065)](https://eiec.kdi.re.kr/policy/materialView.do?num=270579) (KR)

**Tax system**
- [OECD *Revenue Statistics 2025*](https://www.oecd.org/en/publications/2025/12/revenue-statistics-2025_07ca0a8e.html)
- [KOTRA — *Taxation in Korea 2025*](https://www.investkorea.org/file/ik-en/252025Taxation_in_Korea.pdf) — local copy `sources/kotra-taxation-in-korea-2025.pdf`
- [국세청 — 종합소득세 세율 (2017~2025 귀속)](https://www.nts.go.kr/nts/cm/cntnts/cntntsView.do?mi=2227&cntntsId=7667) (KR) — bracket schedule incl. 누진공제
- [한국경제 — 면세자 비율 33%](https://www.hankyung.com/article/2025100455487) (KR)
- [서울신문 — 상위 1%가 소득세의 31% 부담](https://www.seoul.co.kr/news/economy/policy/2024/10/09/20241009500105) (KR)
- [세계일보 — 연령대별 면세자 비율](https://www.segye.com/newsView/20250314509959) (KR)

**Intergovernmental transfers**
- [KDI — 내국세 20.79% 자동 배정된 교육교부금](https://www.kdi.re.kr/share/pressContriView?bd_no=45564) (KR)
- [재정통계 BRIEF — 지방교부세](https://www.fis.kr/egf/bp/board/article/download?fileSeq=3068) (KR)

**Demographics**
- [통계청 — 장래인구추계 2022~2072](https://www.korea.kr/briefing/policyBriefingView.do?newsId=156605259) (KR)

**AI and the labour market**
- [KDI — *The Impact of AI on the Labor Market and Policy Implications* (EN)](https://www.kdi.re.kr/eng/research/reportView?pub_no=18370)
- [OECD — *Artificial Intelligence and the Labour Market in Korea* (Oct 2025)](https://www.oecd.org/en/publications/artificial-intelligence-and-the-labour-market-in-korea_68ab1a5a-en.html)
- [East Asian Economic Review — AI exposure across industries, Korea and the US](https://www.eaerweb.org/selectArticleInfo.do?article_a_no=JE0001_2025_v29n1_3&ano=JE0001_2025_v29n1_3)
- [IMF — *Transforming the Future: The Impact of AI in Korea*, SIP 2025/013](https://www.elibrary.imf.org/view/journals/018/2025/013/article-A001-en.xml)

**Self-employment**
- [OECD — Self-employment rate indicator](https://www.oecd.org/en/data/indicators/self-employment-rate.html)
- [한국경제 — OECD 국가 중 자영업 비중](https://www.hankyung.com/article/202107270159Y) (KR)
- [e-나라지표 — 자영업자 현황](https://www.index.go.kr/unity/potal/main/EachDtlPageDetail.do?idx_cd=2779) (KR)
- [아시아경제 — 60세 이상 자영업 진입 업종](https://www.asiae.co.kr/visual-news/article/2025072115255684747) (KR)
- [시사저널 — 자영업자 부채 141조](https://www.sisajournal.com/news/articleView.html?idxno=357804) (KR)
- [뉴스웨이 — 키오스크에서 AX로](https://www.newsway.co.kr/news/view?ud=2026070315345379186) (KR)
- [news2day — 키오스크 확산 팩트체크](https://www.news2day.co.kr/article/20190123119235) (KR)

**US model robustness**
- [Smith, Yagan, Zidar & Zwick, *Capitalists in the Twenty-First Century*, QJE 134(4)](https://academic.oup.com/qje/article-abstract/134/4/1675/5542244)
- [BLS OEWS — coverage and technical notes](https://dol.ny.gov/occupational-employment-and-wage-statistics-technical-notes)
- [IRS — Wage Compensation for S Corporation Officers](https://www.irs.gov/pub/irs-news/fs-08-25.pdf)

**Data sources for modelling**
- [KOSIS — 고용형태별근로실태조사](https://kosis.kr/statHtml/statHtml.do?orgId=118&tblId=DT_118N_LCE0001&conn_path=I2) (KR)
