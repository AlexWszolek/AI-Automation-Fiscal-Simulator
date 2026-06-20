# AI Automation Fiscal Model — Project Briefing & Data Dictionary (v2)

> Self-contained handoff for an agent with **no prior context**. Documents the project's
> purpose, the seven data files, every column and unit, the baseline numbers and effective
> tax rates to hard-code, the model to build, what is still external, and the gotchas that
> would otherwise produce silently wrong code. Read fully before writing code. The build is
> iterative — do not try to one-shot it.
>
> **v2 changes vs the first handoff:** the two occupation×industry matrix files were merged
> and rebuilt — their interior is now **survey-observed** (BLS OEWS) rather than inferred, and
> all four matrices live in **one** workbook (`occ_industry_matrices_v2_aligned.xlsx`). The
> **household-archetype file now exists** (`household_archetypes_by_state.xlsx`); it is no
> longer a pending external input. Everything else is unchanged.

---

## 0. The files (load these seven)

1. `occ_industry_matrices_v2_aligned.xlsx` — occupation×industry **employment & compensation**,
   at **detail (71 industries)** and **sector (20)** resolution. One workbook, four matrix
   sheets. *Replaces the old `Industry_Numbers_*` and `Industry_Compensation_*` files.*
2. `Occupation_AI_Exposure_Claude_.xlsx` — AI exposure by occupation (+ industry aggregates).
3. `Capital_Income_by_Sector_Claude_.xlsx` — capital income & corporate effective tax by sector.
4. `Government_Fiscal_Accounts_Claude_.xlsx` — receipts, transfers, base linkage & effective rates.
5. `State_Occupation_Numbers_Claude_.xlsx` — state-level OEWS wage distributions.
6. `Taxable_Consumption_Base_by_State_Claude_.xlsx` — state consumption-tax channel.
7. `household_archetypes_by_state.xlsx` — filing-status mix & household income by occupation×state.

---

## 1. What this project is

An **interactive, user-driven model of the fiscal effects of AI/automation on the U.S.
economy**, federal *and* state-and-local. End goal: a website where a user sets levers (how
much of each occupation/industry is automated, how fast, reabsorption rate, state budget
response, optional UBI) and sees the downstream consequences — lost tax revenue, rising
transfer outlays, deficits, and distributional/structural shifts.

**Design philosophy (shapes how to write the code):**
- Every assumption is a **user-set lever**, never baked in. Credibility comes from the
  *accounting being correct*, not from our choice of inputs. Whatever a user dials in,
  consequences must propagate correctly.
- **Transparency**: the chain (automation → lost compensation → lost income tax → lost demand →
  second-round effects) is inspectable, with second-round/multiplier effects toggleable.
- **Steelman the optimistic case**: include offsets (reabsorption, productivity/price effects,
  capital income being taxed and recirculated) with the same prominence as costs, so the model
  shows "cost, offset, net" rather than only counting losses.

**The thesis the accounting must surface:** under serious automation the tax base **migrates
from labor to capital**. Labor income is taxed at a high, *top-heavy* effective rate (top 10%
pay ~70% of federal income tax); capital income is taxed lower. Because the most AI-exposed
work is high-wage cognitive work, revenue can fall **faster than employment**. Meanwhile
**automatic-stabilizer outlays rise** (UI, Medicaid, SNAP, EITC) and **states must balance
their budgets** (a contractionary amplifier the federal government doesn't face).

---

## 2. Core conceptual architecture

### 2.1 Why occupation→industry mapping is the backbone
AI exposure is measured at the **occupation/task** level (Yale). GDP, factor shares, and taxes
live at the **industry** level (BEA). Mapping occupations onto industries connects "this task
is automated" to "this much value added and tax base moves." That **occupation × industry
matrix**, whose columns reconcile exactly to BEA control totals, is the spine; several files
are layers on it (employment, compensation, exposure). In v2 the matrix **interior** (which
occupations sit in which industry) is observed from BLS OEWS staffing patterns; the **column
margins remain BEA-exact**.

### 2.2 The three layers of automation (independent, composable factors)
1. **Exposure** (Yale, fixed ground truth): *can* a task be touched by AI.
2. **Automation feasibility** (time-varying, scenario-driven): given exposure, what fraction AI
   can actually do. This is where post-AGI **mechatronics/robotics** enters — physical jobs that
   score low on Yale's *cognitive* exposure get a separate robotics-feasibility ramp. Build
   feasibility as its own occupation-level multiplier with ≥2 channels (cognitive vs physical).
3. **Displacement / adoption** (time-varying): given feasibility, how much actually gets
   automated (prices, deployment cost, regulation, substitution).
Displacement of an occupation = exposure-gated × feasibility × adoption, all user-settable.

### 2.3 The fiscal mechanism (what the kernel computes)
Displacing a worker: **lost revenue** (their income tax, payroll/FICA capped at the SS wage
base, sales/excise tax on spending they can no longer do) + **gained outlays** (UI then
means-tested transfers). The disappearing compensation becomes operating surplus (capital
income), taxed via the **corporate** channel (corporate) or **individual** rates (pass-through),
generally **lower** than the labor it replaced — the base-migration result.

---

## 3. Data dictionary

Units and join keys are explicit. Read sheet and column names exactly.

### 3.1 `occ_industry_matrices_v2_aligned.xlsx` — the employment & compensation matrices
One workbook, four matrix sheets + README. **Each matrix sheet:** row 1 = header; col A `Code`
= SOC code (`NN-NNNN`), col B `2024 NEM occupation` = title, cols C..onward = industries; the
**last row is `Column total (BEA)` — skip it when reading occupation rows.** 833 occupation
rows incl. a Military pseudo-row `55-0000`.

- **Sheet `Detail employment (000s)`** — 71 BEA detail industries; cells = employees in
  **thousands**. Columns are the BEA detail industries (e.g. `Farms`, `Oil and gas extraction`,
  `Computer systems design and related services`, `Hospitals`, `State and local education`, …).
- **Sheet `Sector employment (000s)`** — same rows, 20 BEA sectors (see §4.2); thousands.
- **Sheet `Detail compensation ($m)`** — 71 detail industries; cells = compensation in **$millions**.
- **Sheet `Sector compensation ($m)`** — 20 sectors; $millions.

**Control totals (assert on load):** employment grand total **163,223k** (= BEA 6.4D, full-time
+ part-time employees, 2024); compensation grand total **$15,049,121 m** (= BEA 6.2D, 2024).
The **sector matrices are exact aggregations of the detail matrices**, so detail↔sector ties by
construction; compensation aggregates to the same sector totals the capital file uses.

**How built / what's trustworthy:**
- **Margins are BEA-exact** (industry employment and compensation totals, and occupation totals).
  The **interior** (occupation mix within an industry) is the **observed BLS OEWS May-2025
  staffing pattern**, mapped NAICS→BEA and RAS-calibrated to the BEA margins. 830/833 occupations
  matched OEWS; ~37% of employment was reallocated off the earlier inferred interior, so interior
  placements now match reality (e.g. software developers concentrate in *Computer systems design*
  + *Misc professional* + *Finance*, not *Information*; public nurses/teachers appear in the
  *State and local* government columns).
- **Caveats:** OEWS counts wage-and-salary jobs (excludes self-employed) on a May-2025 basis;
  BEA margins are 2024 employees — RAS reconciles the level, the seed supplies the *pattern*.
  **Farms** and **Military** are outside OEWS scope and keep an inferred interior. Interior cells
  remain estimates of *placement*; the **margins** are what the fiscal accounting rides.

### 3.2 `Occupation_AI_Exposure_Claude_.xlsx` — AI exposure
- **Sheet `Occupation AI exposure`** (833×7): `Code` (SOC), `2024 NEM occupation`, **`AI PCA
  score`**, `Imputed?`, `Employees (000s)`, `Compensation ($m)`, `Avg comp/worker ($)`.
- **Score scale:** Yale Budget Lab **PCA-weighted exposure**, a *standardized, relative* measure
  (≈ **−3.38 to +7.06**, mean ≈ 0). **Higher = more exposed.** **Not** a 0–1 probability, **not**
  a "share automatable" — pass it through the feasibility/adoption layers (§2.2) via a monotonic
  mapping (rank/percentile or a user-shaped logistic) to get a displacement fraction.
- `Imputed?` flags **68** occupations imputed from SOC-group means. Military excluded.
- **Sheets `Industry exposure (sector)` and `(detail)`**: exposure aggregated to industry, both
  employment-weighted and compensation-weighted. Key finding: comp-weighted ≫ emp-weighted —
  **higher-paid work is more exposed** (Professional/Scientific/Technical, Finance, Information
  most; Construction, Agriculture, Manufacturing least). This drives "revenue falls faster than
  employment."
- The occupation-level `Employees`/`Compensation` here are **occupation totals** and are
  unaffected by the v2 interior rebuild (margins unchanged) — still valid.

### 3.3 `Capital_Income_by_Sector_Claude_.xlsx` — capital income & corporate tax
- **Sheet `Capital income & tax by sector`** (22×15): 20 sectors + `Total / aggregate`. Columns:
  `Industry`, `Value added ($m)`, `Compensation ($m)`, `Labor share`, `Capital share`,
  `Gross operating surplus ($m)`, `Corp profits before tax ($m)`, `Taxes on corp income ($m)`,
  `Effective corp tax rate`, `Corp profits after tax ($m)`, `Net dividends ($m)`,
  `Dividend payout ratio`, `Nonfarm proprietors' income ($m)`, `Net interest ($m)`,
  `Corp share of taxable capital income`.
- **Use:** `Effective corp tax rate` per-sector (≈3%–33%, aggregate ~18.3%) instead of a flat 21%.
  `Corp share of taxable capital income` = corporate-vs-pass-through split (corporate → corp tax
  then dividends; proprietors → individual rates).
- **Control totals (BEA 2024):** VA $29,298,075 m (GDP), comp $15,049,121 m, corp profits before
  tax $3,721,572 m, nonfarm proprietors $1,652,676 m, net interest $579,219 m.
- **Caveats:** capital share is **gross** (incl. depreciation + production taxes; ~49% vs ~40% net)
  — use the corporate-profits columns for the *tax* base, not VA−comp. Nonfarm proprietors
  **excludes farms** (Ag understated). Net interest is messy (Finance negative, RE huge, much
  tax-exempt). **Government** has no taxable corporate profit (its capital share is depreciation)
  — **zero it** in the corporate channel.

### 3.4 `Government_Fiscal_Accounts_Claude_.xlsx` — the government ledger ($billions, 2024)
- **Sheet `Receipts`** (17×5): federal (Table 3.2) + state-local (3.3) receipts tagged to the
  model base each attaches to. Key: fed income **2403.2**, fed social insurance **1902.7**, fed
  corporate **491.7**, fed excise+customs **185.2**; state income **536.2**, sales **602.4**,
  excise **271.3**, property **752.2**, corporate **172.0**, plus **961.5** federal grants-in-aid
  (the Medicaid pipe — not a tax base).
- **Sheet `Transfers & stabilizers`** (20×5): programs (Table 3.12) tagged automation-sensitivity.
  **Automation-sensitive (~$1,434B):** Medicaid **938.2** (HIGH), refundable credits/EITC-CTC
  **228.8**, SNAP **97.4** (HIGH), SSI **60+5.2**, UI **36.5** (HIGH, *time-limited*), TANF
  **24.5**, general assistance **38.6**, energy **5.2**. **Insensitive (hold fixed):** Social
  Security **1448**, Medicare **1102**, veterans **229**, education **64.5**.
- **Sheet `Base linkage & eff. rates`** (6×7): starting effective rates — individual income
  **19.5%** (⚠ aggregate incl. capital; use the percentile schedule §5.1 for labor), payroll
  **12.8%** (capped, §5.2), corporate **17.8%** (cross-checks 18.3%), consumption→PCE (use §3.7),
  property→wealth (treat automation-insensitive short-run).
- **Federal↔state linkage:** Medicaid is **~65% federally funded** via grants-in-aid → split
  ~65/35 fed/state, don't dump on states. **State balanced-budget asymmetry:** state operating
  budgets must balance within-year (spending cuts or rate hikes) — a contractionary amplifier and
  a required lever; the federal government can run the deficit.

### 3.5 `State_Occupation_Numbers_Claude_.xlsx` — state wage distributions (OEWS, May 2025)
- **Sheet `State OEWS (all groups)`** (36346×20): one row per (state × occupation). Columns:
  `Area` (50 states + DC, **no territories**), `SOC code`, `Occupation`, `Employment`, `Emp % RSE`,
  `Hourly mean wage`, `Annual mean wage`, `Wage % RSE`, then **`Hourly/Annual 10th/25th/median/
  75th/90th`**, `Emp per 1,000`, `Location quotient`. All 22 SOC major groups.
- **Use:** state income tax (apply state brackets to the distribution), UI (replacement rate on
  wage up to cap), and the **income spread within household cells** (§7/§8.1). Join on `SOC code`.
- **Caveats:** small states suppress low-employment cells. **Top-coding:** very high wages
  (≥ ~$239k/yr) come through as **blank**, not zero — impute the national occupation mean before
  any income-tax step or you understate the high earners who matter most.

### 3.6 `Taxable_Consumption_Base_by_State_Claude_.xlsx` — consumption-tax channel ($m, 2024)
- **Sheet `Effective consumption tax`** (53×10): one row per state (50 + DC + `United States`).
  Columns: `State`, `Total PCE ($m)`, `Taxable goods+services ($m)`, `Grocery treatment`,
  `Grocery taxable ($m)`, `Total taxable PCE ($m)`, `Taxable share of PCE`, `Combined sales rate`,
  **`Eff. tax rate on consumption`**, `Sales-tax breadth (T21)`.
- **Key column:** `Eff. tax rate on consumption` = sales/excise tax lost **per dollar of household
  consumption** a displaced worker cuts in that state (0% in the 5 no-sales-tax states to ~3% in
  LA/TN; U.S. avg **2.09%**).
- **Caveats:** household-PCE base (~28% of PCE), **intentionally smaller** than total sales-tax
  collections imply (~40% of the real base is **B2B**, not household consumption — don't
  reconcile it away). `Sales-tax breadth` is context only (includes B2B, relative to income).
  **Marginal basket** ≠ average: displaced workers protect exempt necessities (groceries, rent,
  utilities, health) and cut taxable discretionary goods, so the marginal taxable share can exceed
  the average. Consumption is **sticky in v1** (muted/delayed short-run) — make it a parameter.

### 3.7 `household_archetypes_by_state.xlsx` — household conditioning (ACS 2024 PUMS) **[new]**
For each occupation×state: the filing-status mix and household income, for conditioning the kernel.
- **Sheet `Household archetypes by SOC-state`** (~38k rows): `State`, `SOC code`, `Occupation`,
  `P(married/MFJ)`, `P(single parent/HoH)`, `P(single)`, `Avg HH income married ($)`,
  `Avg HH income HoH ($)`, `Avg HH income single ($)`, `Person weight`.
- **Meaning:** the three P() columns sum to 1 and give the share of workers in that occupation×state
  who are in married-couple households (→ MFJ), other-family-no-spouse households (→ head of
  household), and nonfamily households (→ single). The income columns are **mean total HOUSEHOLD
  income (HINCP, all earners)** for each group — count-weighted across the underlying sub-types.
- **Coverage:** 795/833 SOC occupations, **97.5% of employment**. Census PUMS OCCP categories were
  joined to SOC via the OCCP→SOC crosswalk; combined categories (e.g. "Astronomers and Physicists")
  share one household profile across their constituent SOCs. Income is populated for ~96%/72%/80%
  of married/HoH/single cells; blanks are ACS small-cell suppression (fall back to the occupation
  overall or the wage-based estimate).
- **How to use:** household income here is the **household total, not the worker's wage**. It is
  *closer to AGI* than individual wage, so use it to pick the income-tax bracket / transfer regime
  by filing status. To get a within-cell income distribution, take the worker's own OEWS wage
  percentiles (§3.5) and **scale them multiplicatively** to this mean (preserves right-skew,
  constant CV, no negatives) — **do not shift additively**.
- **Caveat:** **number of own children (NOC) is not available** — EITC/CTC need a dependent-count
  assumption per filing status (e.g. HoH → 1–2 children) or a separate NOC cross-tab.

---

## 4. Identifiers & join keys

### 4.1 Occupations
All seven files key on **2018 SOC codes** (`NN-NNNN`). Join directly on `SOC code` everywhere —
including the household file (the OCCP→SOC join was already done when building it).

### 4.2 The 20 BEA sectors (canonical order)
`Agriculture, forestry, fishing, and hunting` · `Mining` · `Utilities` · `Construction` ·
`Manufacturing` · `Wholesale trade` · `Retail trade` · `Transportation and warehousing` ·
`Information` · `Finance and insurance` · `Real estate and rental and leasing` ·
`Professional, scientific, and technical services` · `Management of companies and enterprises` ·
`Administrative and waste management services` · `Educational services` ·
`Health care and social assistance` · `Arts, entertainment, and recreation` ·
`Accommodation and food services` · `Other services, except government` · `Government`.
The 71 detail industries aggregate into these (the detail and sector sheets are consistent).

### 4.3 States
Full names (`Alabama` … `Wyoming`, + `District of Columbia`). Consumption, state-OEWS, and
household files use full names — join on those.

---

## 5. Baseline effective rates & numbers to hard-code

Where a file contains them, read the file; the rest are Tax Foundation *Facts & Figures 2025*.

### 5.1 Federal individual income tax — average effective rate by AGI percentile (T9, TY2022)
| Group | Avg effective income-tax rate | AGI threshold |
|---|---|---|
| All | 14.5% | — |
| Top 1% | 26.1% | > $663,164 |
| Top 5% | 23.1% | > $261,591 |
| Top 10% | 21.1% | > $178,611 |
| Top 25% | 18.1% | > $99,857 |
| Top 50% | 15.9% | > $50,339 |
| Bottom 50% | 3.7% | — |
Map a worker's **household income** (§3.7, closer to AGI) to its band for the labor income-tax
channel. Replace with a PolicyEngine-generated schedule (§8.2) for precision.

### 5.2 Federal payroll / FICA (2025; effective ≈ 12.8% of compensation)
15.3% on wages up to the **Social Security wage base $176,100** (12.4% OASDI + 2.9% Medicare),
then **2.9%** above the cap, plus **0.9%** additional Medicare on wages > $200,000. Because OASDI
is capped, automating a high-wage job loses *less* payroll tax per wage-dollar than a low-wage one
— the opposite skew from income tax. Model the cap.

### 5.3 Federal income-tax brackets (2025, if building schedules directly)
Single: 10/12/22/24/32/35/37% at $0/11,925/48,475/103,350/197,300/250,525/626,350. MFJ ≈ doubled.
Head of Household separate. Corporate flat **21%** federal.

### 5.4 Corporate effective rate by sector → file §3.3 (`Effective corp tax rate`), ~3%–33%, agg ~18.3%.
### 5.5 Consumption tax effective rate by state → file §3.6, 0%–~3%, U.S. avg 2.09%.
### 5.6 State individual income tax brackets — T11 (2025) / the 2026 state-bracket file (available
separately, not in the core set). 9 no-income-tax states (AK, FL, NV, NH, SD, TN, TX, WA-wages, WY).
Apply standard deductions/exemptions for effective (not statutory) rates; some states have local
income taxes a state table misses.
### 5.7 Net tax-and-transfer incidence by quintile (T43, FY2019; validation): total incl. transfers
Q1 **−127.0%**, Q2 −31.0%, Q3 +2.0%, Q4 +15.9%, Q5 +30.7%. Tax-only: Q1 10.1% / Q5 41.4% total;
federal Q1 2.3% / Q5 29.3%; state-local Q1 7.8% / Q5 12.1%. Validate kernel aggregates by quintile.

---

## 6. The static fiscal kernel (build this first)

A function returning the **net fiscal delta of displacing one worker**, by **wage bracket × state
× household type × industry**, split federal vs state-local. Pure and deterministic; the per-period
engine the dynamics call.

```
fiscal_delta(worker) =  lost_revenue  +  gained_outlays         # both positive = worse for gov
  lost_revenue   = lost_individual_income_tax(household_income, filing_status, state)  # §5.1 + §5.6
                 + lost_payroll_tax(wage)                                              # §5.2, SS cap
                 + lost_consumption_tax(spending(wage), state)                         # §3.6 eff rate
  gained_outlays = UI(wage, replacement_rate, until_exhaustion)                        # time-limited
                 + means_tested_transfers(new_income, household)                       # SNAP/Medicaid/EITC Δ
```

- **Household conditioning (now data-backed):** use `household_archetypes_by_state.xlsx` (§3.7) to
  weight each occupation×state across filing types and to set household income → bracket/transfer
  regime. The object wanted is the **marginal** fiscal change from removing one earner's wage from
  the household, not an average rate.
- **Corporate channel (separate, industry-level):** displaced compensation becomes operating
  surplus; tax the corporate portion at the sector `Effective corp tax rate` (§3.3), route the
  pass-through portion to individual rates; net the *partial* corporate offset against the lost
  labor tax (showing it's partial is the headline).
- **Fed vs state split** everywhere (income fed+state, payroll mostly fed, consumption state,
  Medicaid 65/35).
- **Validate** against the base-linkage totals (§3.4), quintile incidence (§5.7), and PolicyEngine
  (§8.2) if used.

---

## 7. The dynamic model (wrap the kernel)

- **Stocks/flows:** each period a user-set **displacement flow** (per occupation = exposure-gated ×
  feasibility × adoption, §2.2) moves workers employed→unemployed; the kernel computes the delta on
  the flow; the federal deficit accumulates into a debt stock with interest.
- **UI exhaustion:** UI is time-limited (~26 weeks federal-standard). Track displacement **cohorts**
  and age them off UI; after exhaustion they fall to means-tested programs or nothing. Modeling UI
  as permanent is a large error.
- **State balanced-budget response (required lever):** close the state gap each period — toggle cut
  spending vs raise effective rate vs mix.
- **Headline levers:** displacement rate per occupation/industry; **reabsorption rate** (default
  visibly **0** = the thesis, framed as a setting not a hidden assumption); re-employment wage
  haircut; second-round demand multiplier (toggle); state budget response; optional **UBI** (a
  transfer financed by a user-set tax — the interesting output is the tax rate required to fund UBI
  at level X given the eroded base).
- **Offsets** (so it isn't one-sided): productivity/price effects (lost labor tax partly reappears
  as taxable capital income — already in the capital channel), reabsorption, GDP-base growth. Show
  **cost, offset, net**.
- **Consumption sticky in v1** — make stickiness a parameter (relax later with an MPC + marginal basket).

---

## 8. External inputs still needed (NOT in the seven files)

### 8.1 State individual income-tax brackets
T11 (2025) or the 2026 state-bracket file — see §5.6. Code load-if-present with §5.1/§5.6 fallbacks.

### 8.2 PolicyEngine-derived effective-rate / fiscal-delta schedule (recommended upgrade)
Use **PolicyEngine US** (`policyengine-us`) — not TAXSIM — for income+payroll **and** 55+ benefit
programs in one engine, so the per-worker delta (lost income/payroll **and** gained EITC/SNAP/
Medicaid) is consistent. **Run offline** to bake a lookup schedule (net fiscal delta by wage × state
× household type), then the site reads the static table — don't call it live. Validate vs §3.4/§5.7.
Our own layers own the **corporate** (§3.3) and **consumption** (§3.6) channels; PolicyEngine owns
income/payroll/transfers — no overlap.

### 8.3 Excise detail (optional)
Gasoline/tobacco/alcohol are **per-unit**, not ad valorem (Tax Foundation T22–T29). Handle separately
from the ad-valorem consumption base, or fold into a single national effective excise rate.

### 8.4 NOC (children) for EITC/CTC
Not in the household file — assume dependent counts per filing status or obtain a NOC cross-tab.

---

## 9. Caveats & gotchas (read before coding — these cause silent errors)

1. **Units differ:** employment **thousands**; compensation/value-added/capital **$millions**;
   government ledger **$billions**; consumption base **$millions**; household income **$ (dollars)**.
2. **Matrix sheets:** four sheets in one workbook (`Detail/Sector employment (000s)`,
   `Detail/Sector compensation ($m)`); each has a trailing **`Column total (BEA)` row — skip it**.
   The interior is OEWS-observed; the **margins** are exact and are what the accounting rides.
3. **AI PCA score is not a fraction** (−3.38…+7.06, higher=more exposed) — pass through
   feasibility/adoption before treating as a displacement share.
4. **Gross vs net capital share** — use the corporate-profits columns for the tax base, not VA−comp.
5. **Corporate ≠ all capital income** — split corporate (corp tax + dividend tax) vs pass-through
   (individual). Government and (largely) Agriculture have ~no corporate base.
6. **Income tax is top-heavy; payroll is capped** — opposite skews by wage. Include both.
7. **OEWS top-coding** — blank high wages are censored, not zero; impute before income tax.
8. **Consumption base is household-PCE (~28% of PCE)** — the gap to total collections is B2B; don't
   reconcile it away. Marginal basket ≠ average.
9. **Medicaid ~65% federally funded** — split 65/35, don't dump on states.
10. **States must balance**; the federal government need not — a core result.
11. **UI is time-limited** — cohort-age it; permanent UI is a large error.
12. **Reabsorption=0 is the default but a visible lever**, framed as a setting.
13. **Household income is household total, not the worker's wage** — use it for bracket/transfer
    regime; scale (don't shift) OEWS percentiles to it for within-cell spread; NOC not included.
14. **Mixed vintages** (employment/comp/VA 2024; OEWS wages & staffing May-2025; household ACS-2024;
    SOC-2018; Tax Foundation 2025). Acceptable as structural weights; keep 2024 as base year.
15. **No territories** (50 states + DC).

---

## 10. Suggested code architecture

- `data/loaders.py` — one loader per file → tidy DataFrames keyed by SOC / sector / state, units
  normalized (suggest $millions + thousands). **Read the four matrix sheets by their exact names and
  drop the `Column total (BEA)` row.** Assert control totals on load (163,223k employees;
  $15,049,121m comp; $29,298,075m VA; $3,721,572m corp profits) so a bad file fails loudly.
- `rates.py` — the §5 schedules (federal income by percentile, payroll w/ caps, corporate by sector,
  consumption by state, state brackets), each replaceable by a PolicyEngine table.
- `kernel.py` — `fiscal_delta(wage, state, household_type, industry) -> {fed, state, by-channel}`
  implementing §6; condition on the household archetypes (§3.7). Pure, unit-tested vs §3.4/§5.7.
- `dynamics.py` — the §7 stock-flow loop (cohorts, UI exhaustion, deficit accumulation, state
  balanced-budget), calling `kernel` each period; all levers explicit parameters.
- `levers.py` — exposure→feasibility→adoption transform (§2.2) → per-occupation displacement flows.
- `validate.py` — reconciliation checks (control totals, quintile incidence, PolicyEngine aggregates).

Build and test **kernel.py** to exactness first (one period, no dynamics), then wrap in dynamics —
a dynamics bug is otherwise indistinguishable from an accounting bug.
