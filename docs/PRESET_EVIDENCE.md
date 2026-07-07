# Preset evidence — literature anchors for scenario presets

Fetch-verified calibration evidence from 25 papers, mapped onto the model's levers, plus draft
preset definitions. Every number below was verified against the fetched source text (URLs in the
appendix; verbatim quotes preserved in [research/preset-evidence-raw.json](research/preset-evidence-raw.json)).
Companion to [EQUATIONS.md](EQUATIONS.md) (what the levers do) — this file is *what values the
literature supports* (where they should sit).

**How to read the mappings.** Most papers do not estimate our levers directly; each mapping states
the conversion. Three recurring unit traps:
1. *Exposure ≠ feasibility ≠ adoption.* Eloundou-style "exposure" is a time-savings potential
   (≥50% faster at equal quality), agnostic between augmentation and substitution. Treat it as an
   upper bound on `cognitive_feasibility`, and let `adoption_path` carry realized automation.
2. *Ad-valorem robot taxes are levied on robot spending, not the saved wage bill.* Our
   `automation_tax_rate` is a share of saved compensation, so the conversion is
   `automation_tax_rate = t_ad_valorem × auto_cost`. A "3% robot tax" at `auto_cost=0.2` is
   `automation_tax_rate = 0.006` — *not* 0.03.
3. *PDV earnings losses bundle unemployment spells with wage scars.* The model prices spells via
   `reabsorption_rate`/UI and the scar via `reemployment_haircut` separately — mapping a full PDV
   loss onto the haircut double-counts. Use the long-run *annual* loss (10–20y out) for the haircut.

---

## 1. Lever crosswalk — what the literature supports, by lever

### Diffusion

| Lever | Evidence | Range |
|---|---|---|
| `cognitive_feasibility` | Eloundou α (bare-LLM: 15% of all tasks; mean occ. 0.14–0.15) → floor **0.15**; β central **~0.30**; ζ with LLM-built software (47–56% of tasks) → ceiling **~0.50–0.55**. Acemoglu: 19.9% of the wage bill exposed → conservative **0.20**. Korinek-Stiglitz (cites Frey-Osborne): combined feasible ~0.47. Windfall: exposed sectors = 0.60 of jobs (their upper bound). AGI scenarios (Korinek-Suh, Davidson, AI 2027): **1.0**. | 0.15 → 1.0 |
| `physical_feasibility` | No LLM-exposure paper anchors this (manual occupations score ~0 by construction). AI 2027 robot economy: 0.8–1.0. Anchor low today (0.05–0.2), high only in takeoff presets. | 0.05 → 1.0 |
| `robotics_lag` | Productivity J-Curve (adoption→measured output analog): **8–12y** (range 5–15). Webb (robots' historical diffusion): 10–30y. AI 2027 (special economic zones, ~1M robots/mo by 2028): **3–4y**; authors' updated medians → 5–6y. | 3 → 12 yr |
| `adoption_path` end | Acemoglu: 23% of *exposed* tasks profitably automatable within 10y (Svanberg extrapolation) → end **0.23**, sensitivity 0.30. Windfall: 0.20 / 0.50 / 0.80 (Low/Med/High) of a 0.6 feasible share. Korinek-Suh: BAU λg=0.01/yr (~0.18–0.26 over 20–30y); AGI-20y → 1.0 over 20y; AGI-5y → 1.0 over 5y. GATE: back-loaded ramp — hold ~0.10 for ~a decade, then steep. Canaries (realized so far): cumulative ~0.01–0.03 at year 3 of the cognitive channel — adoption *starts* near 0.02, not 0.05+. Farber pacing check: displacement flow above ~5.5%/yr of the workforce exceeds the worst US 3-year window on record. | 0.23 → 1.0 |

### Labor market

| Lever | Evidence | Range |
|---|---|---|
| `reemployment_haircut` | Davis–von Wachter long-run annual loss: ~10% (expansion) / ~20% (recession displacements) 10–20y out → central **0.15**, band 0.11–0.22. Farber (DWS, survivor-selected, understates): **0.13** central (0.10–0.18). JLS (high-tenure, mass-layoff, rust-belt — the literature's upper bound): **0.25**. Windfall presets: 0.20/0.30/0.40. Exposure-gradient note (Eloundou/Felten/Webb): AI-displaced skew *above-median wage* (peak ~p90 per Webb), so service-floor re-employment implies 0.3–0.5 — higher than historical displacement studies. | 0.10 → 0.40 |
| `reabsorption_rate` | Farber cumulative job-finding: 44% within ~1y in deep slack, 69% within 1.5–3y → **0.40–0.50/yr** slack, **0.60–0.75/yr** normal markets. DvW slack-market: 0.15–0.35. China Shock: employment-to-population falls ~1:1 with mfg jobs lost for a full decade → **0.05–0.10/yr** in grind presets. RAND S1/S3 spec: full return after exactly 5y (≈0.2/yr). | 0.05 → 0.75 |
| `lfp_exit_rate` | Farber: ~10% of job losers NILF at survey date, stable across cycles → **0.03–0.05/yr**. Windfall: 10/20/30% of displaced over 3/6/9y — all annualize to **~0.033/yr**. China Shock: NILF +0.55pp vs unemployment +0.22pp per $1k exposure (LFP exit is the *dominant* margin) → **0.08–0.15/yr** in grind presets. | 0.03 → 0.15 |
| `attrition_rate` | Farber: carve 1–2pp of the 10% NILF share into natural attrition. China Shock grind: 0.03–0.05. Shipped 0.025 is consistent. | 0.02 → 0.05 |
| `survivor_elasticity` | Webb (robots/software 1980–2010, within-industry): wages −8/−14% (robots), −2/−6% (software) per interquartile exposure over 30y → annualized ~−0.1 to −0.5%/yr → modest negative. GenAI at Work: complementarity at low depth (novices +30%) → **+0.05 to +0.2** in augmentation presets. Canaries: ~0 salary differential so far → ~0 for the first 3–5 model years. Korinek-Suh AGI: wage collapse ~3y before full automation → **−0.5** (slider max) in AGI presets. | −0.5 → +0.2 |

### Firms / disposition / compute

| Lever | Evidence | Range |
|---|---|---|
| `retained/price/survivor` shares | Acemoglu: capital share +0.38pp, "no sizable wage rises" → survivor ~**0.00–0.05**, e.g. 0.60/0.35/0.05. Windfall high-capture: firms 45% / consumers 45% / residual 10% → ours ≈ 0.50/0.50/0.00 with `auto_cost=0.10` (their residual; our shares partition *net* saving). RAND monopolistic: retained ≈ 1.0; RAND at-cost: price_reduction ≈ 1.0 with full passthrough. GenAI at Work: gains accrued mostly to the firm → survivor share low (0.05–0.15). | see presets |
| `auto_cost` | J-Curve: intangible co-investment 2.7–4.1× observable AI investment → **0.3–0.6** in buildout years, declining. Davidson/AI 2027: 0.3–0.5 early, → 0.1–0.2. Steady-state: ~0.05–0.10. | 0.05 → 0.5 |
| `compute_effective_rate` | GRT: US effective capital tax 10% → **5%** post-TCJA (status quo). Windfall capital ETR: **0.267** (avg 20.5% corporate EATR + top-up) = domestic-parity taxation. Korinek-Lockwood AGI-stage: ~0.04 of the AGI capital *stock* (different base — normative). | 0.05 → 0.27 |

### Macro & demand

| Lever | Evidence | Range |
|---|---|---|
| `productivity_passthrough` | Acemoglu 10y bound: TFP ≤0.66% (≤0.53% hard-task-adjusted), GDP ~1.1% incl. capital deepening — with his 4.6%-of-tasks automation this implies **0.12–0.155**. GenAI at Work micro (+15% avg, +30% novices): 0.5–0.9 for the cognitive channel. J-Curve: 0.4–0.7 measured in the first decade (intangibles hide the rest), → 0.9–1.0 later. Korinek-Suh/MacAskill AGI: ~1.0. Shipped 0.30 sits between Acemoglu and the micro studies. | 0.12 → 1.0 |
| `demand_multiplier` | Chodorow-Reich preferred cross-sectional multiplier: **1.8** (national, no monetary offset: ≥1.7); ~2 job-years per $100k; balanced-budget state-spending multiplier (Clemens-Miran): 0.29 = the conservative lower bound. China Shock: induced losses ≥ direct (≈2× incl. linkages) → ≥1.0. Shipped 0.5 is the Fed-offsets-half reading; crisis presets should use **1.0–1.8**. Stability: ρ ≈ 0.218·dm → dm=1.8 is safely below the guard. | 0.3 → 1.8 |
| `baseline_growth_rate` | J-Curve real GDP anchors 2.2–2.7% + ~2% inflation → **0.042–0.047** nominal. Korinek-Suh BAU ~2% real (validation). MacAskill-Moorhouse explosion: 0.06–0.08 nominal if denominators are to stay interpretable (their 18%/yr post-AGI output growth is outside the model's frame). | 0.035 → 0.08 |

### Policy

| Lever | Evidence | Range |
|---|---|---|
| `automation_tax_rate` | All three optimal-tax papers are ad-valorem on robot *spending* → multiply by `auto_cost`. Costinot-Werning sufficient statistic: **1–3.7%** ad-valorem (central 2.7%; magnitude should *fall* as automation deepens) → 0.003–0.011 on our base at auto_cost 0.3. Thuemmel: 0.86–1.8% (published version: ≈0, subsidy while robots are expensive). GRT: transitional **5.1% → 2.2% → 0.6%** by decade, **zero in steady state**. Korea quasi-robot tax: a 2pp credit cut → **−28% robot installations** — a behavioral response our model does NOT have (flag on any preset with ad-valorem-equivalent > ~2pp: displacement would fall too, or hand-code via a lower adoption end / longer robotics_lag). **Shipped 0.07 on the saved bill ≈ 23–70% ad-valorem — an order of magnitude above every optimum in this literature.** | 0 → ~0.015 |
| `ubi_annual` / `ubi_recapture_rate` | Korinek-Lockwood: recapture **0.25–0.375** as pure tax clawback; Korinek-Stiglitz: non-distorting windfall/rent taxation can finance compensation. | recapture 0.25–0.375 |
| `state_cut_share` / caps | Chodorow-Reich: apply the full multiplier to forced state cuts (0.29 = lower bound). Korinek-Lockwood: labor-base rate hikes cannot close AGI-stage gaps → low `state_rate_hike_cap`, lean on cuts, in AGI presets. | — |

---

## 2. Scenario presets — as shipped (`fiscal_model/presets.py`)

Seven world-states. Values not shown inherit `DEFAULTS_SHIPPED`. All presets keep rung 1
(service-floor) reabsorption; `reemployment_haircut` binds via `w_d = max(w·(1−haircut), floor)`.
Two values are snapped to their sidebar widget grids (recorded in the preset provenance): Windfall
`lfp_exit_rate` 0.033 → **0.03** and capital ETR 0.267 → **0.27**.

| Lever | ①Acemoglu<br>Modest AI | ②Brynjolfsson<br>Augmentation | ③Windfall<br>Medium | ④China-Shock<br>Grind | ⑤Korinek-Suh<br>AGI-20y | ⑥Korinek-Suh<br>AGI-5y | ⑦AI 2027<br>Takeoff |
|---|---|---|---|---|---|---|---|
| `cognitive_feasibility` | 0.20 | 0.30 | 0.55 | 0.30 | 1.0 | 1.0 | 1.0 |
| `physical_feasibility` | 0.05 | 0.10 | 0.20 | 0.20 | 1.0 | 1.0 | 0.90 |
| `robotics_lag` | 8 | 6 | 5 | 4 | 10 | 2 | 3 |
| adoption start → end | 0.02→0.23 | 0.02→0.30 | 0.05→0.50 | 0.05→0.40 | 0.05→1.0 | 0.20→1.0 † | 0.10→1.0 |
| `n_periods` | 10 | 10 | 10 | 15 | 20 | 10 | 8 |
| `reabsorption_rate` | 0.50 | 0.60 | 0.30 | 0.075 | 0.05 | 0.05 | 0.10 |
| `reemployment_haircut` | 0.13 | 0.10 | 0.30 | 0.25 | 0.40 | 0.40 | 0.40 |
| `lfp_exit_rate` | 0.03 | 0.02 | 0.03 | 0.10 | 0.05 | 0.10 | 0.05 |
| `attrition_rate` | 0.025 | 0.025 | 0.025 | 0.04 | 0.025 | 0.025 | 0.025 |
| retained/price/survivor | .60/.35/.05 | .55/.25/.20 | .50/.50/.00 | .70/.20/.10 | .80/.15/.05 | .80/.15/.05 | .70/.20/.10 |
| `auto_cost` | 0.05 | 0.10 | 0.10 | 0.10 | 0.15 | 0.20 | 0.30 |
| `survivor_elasticity` | 0.0 | +0.10 | −0.15 | −0.30 | −0.50 | −0.50 | −0.50 |
| `productivity_passthrough` | 0.15 | 0.50 | 0.30 | 0.20 | 0.90 | 0.90 | 0.90 |
| `price_passthrough` | 0.3 | 0.3 | 0.5 | 0.3 | 0.5 | 0.5 | 0.5 |
| `demand_multiplier` | 0.3 | 0.3 | 0.5 | 1.5 | 1.0 | 1.5 | 1.2 |
| `baseline_growth_rate` | 0.04 | 0.045 | 0.04 | 0.035 | 0.06 | 0.08 | 0.08 |
| `compute_effective_rate` | 0.10 | 0.10 | 0.27 | 0.10 | 0.05 | 0.05 | 0.05 |
| `interest_rate` | 0.03 | 0.03 | 0.03 | 0.03 | 0.04 | 0.04 | 0.04 |
| state cut share / hike cap | — | — | — | — | .5 / .5 | .5 / .5 | — |
| `automation_tax_rate` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

† ⑥'s path is kinked and PARAMETRIC (it survives horizon changes): linear 0.20→1.0 reaching **full
automation at year 5**, flat thereafter — Korinek-Suh's aggressive transition viewed over a 10-year
fiscal window. ⑤⑥ also set `interest_rate=0.04` (Korinek-Lockwood discount anchor) and close state
gaps half by spending cuts under a low rate-hike cap (labor-base hikes cannot close AGI-stage gaps).

Presets ship with the robot tax **off**; taxation is a composable *policy overlay* (§3), so the
scenario answers "what does the world do to the budget" and the overlay answers "what does policy
recover".

**① Acemoglu — Modest AI.** His upper bounds taken at face value: 19.9% of the wage bill exposed
(`cf=0.20`), 23% of exposed tasks profitably automatable in 10y (end 0.23), TFP arithmetic →
`productivity_passthrough=0.15`, "no sizable wage rises" → survivor share 0.05, elasticity 0.
Labor market normal: Farber-central haircut 0.13, reabsorption 0.50/yr.

**② Brynjolfsson — Augmentation.** AI complements more than it substitutes: slow realized adoption
(Canaries: ~0.02 cumulative at year 3), gains split toward survivors (share 0.20, elasticity +0.10),
strong productivity (GenAI at Work → 0.50), mild scarring (haircut 0.10, reabsorption 0.60/yr).
J-Curve lag keeps robotics at 6y.

**③ Windfall — Medium.** Their Medium scenario translated: 0.6 feasible × adoption→0.50,
haircut 0.30, lfp 0.033/yr (ui 0.03), high-value-capture disposition (0.50/0.50/0), capital taxed at
their ETR (0.267 → ui 0.27). The closest thing to a direct comparator run — their Medium/high-capture
10y total-revenue target is **−2.8%** (low-capture −7.7%).

**④ China-Shock Grind.** A moderate shock met by the labor market ADH actually measured: reabsorption
0.075/yr (decade-scale adjustment), LFP exit dominant (0.10/yr), JLS-severity haircut 0.25, demand
amplification ≥1 (dm 1.5), 15-year horizon. The pessimist's *mechanism* preset — displacement is
moderate but nothing heals.

**⑤ Korinek-Suh — AGI in 20 years.** Full automation over 20 periods, wage collapse before the end
(elasticity −0.50, haircut 0.40, reabsorption ~0), productivity near ceiling, capital keeps the
gains (0.80 retained), states forced onto spending cuts.

**⑥ Korinek-Suh — AGI in 5 years.** The aggressive transition as its own preset (the stress case the
fiscal question most needs): kinked adoption reaching 1.0 at year 5 — their wage collapse hits ~year
3 — over a 10-year window, crash robotics build-out (lag 2), heavy compute (auto_cost 0.20), mass LFP
exit (0.10/yr), crisis demand regime (dm 1.5), growth at the explosion band's edge (0.08).

**⑦ AI 2027 — Takeoff.** Cognitive feasibility 1.0 near-immediately, robots ramp in 3y (SEZ
build-out), adoption ceiling by year ~5, heavy compute investment (auto_cost 0.30), growth 0.08.
Note the authors' own updated medians (Dec 2030 / Jan 2035) have slipped from the scenario's dates —
this preset is the *shape* of a fast takeoff, dated optimistically.

## 3. Policy overlays (composable on any preset)

| Overlay | Levers | Anchor |
|---|---|---|
| **Robot tax — optimal (Costinot-Werning)** | `automation_tax_rate = 0.027 × auto_cost` (≈0.003–0.008) | Sufficient-statistic 1–3.7% ad-valorem; ramp *down* with depth |
| **Robot tax — transitional (GRT)** | `= 0.051 × auto_cost` decade 1, `0.022×` decade 2, 0 after | Mirrleesian transition path; steady-state zero |
| **UBI (Korinek-Lockwood financing)** | `ubi_annual = 12_000`, `ubi_recapture_rate = 0.30` | Recapture 0.25–0.375 as pure clawback |
| **Compute-pool parity tax** | `compute_effective_rate = 0.267` (vs 0.05 status quo) | Windfall capital ETR vs GRT post-TCJA effective rate |

## 4. Validation targets (report material, not presets)

| Model | Target | Their spec |
|---|---|---|
| RAND (Price-Suresh) | ~**25% lower federal revenue** by 2035 (via ~26% lower nominal GDP) under at-cost AI pricing | +10pp unemployment for 5y (S3); FRB/US with Fed response |
| RAND baseline shares | 84% of 2024 federal revenue from individual+payroll; ~66% directly from labor | static accounting ladder: 0%/65%/20% vulnerable by scenario |
| Windfall | 10y total tax revenue: +0.2%/−2.8%/−7.3% (high capture); −1.8%/−7.7%/−15.x% (low capture) | avg OECD country — tax base 46% labor, has VAT; US is more labor-skewed |
| Acemoglu | 10y GDP +~1.1% (upper bound incl. capital deepening) | matches preset ① by construction |
| Korinek-Suh BAU | ~2%/yr real output growth | matches `baseline_growth_rate` in ①–④ |

## 5. Calibration tensions with DEFAULTS_SHIPPED

1. **`automation_tax_rate = 0.07` was far above the optimal-tax literature.** On the saved-bill base
   it was equivalent to a ~23–70% ad-valorem robot tax (depending on auto_cost); Costinot-Werning's
   ceiling is 3.7%, Thuemmel's published answer is ≈0, GRT's steady state is 0.
   **RESOLVED (presets build): `DEFAULTS_SHIPPED.automation_tax_rate = 0.0`** — taxation moved
   entirely to the policy overlays (`fiscal_model/presets.py`).
2. **`demand_multiplier = 0.5` is the monetary-offset reading.** Chodorow-Reich's cross-sectional
   1.8 (national ≥1.7 with passive Fed) and ADH's ≥2× amplification argue crisis presets need
   1.0–1.8; 0.5 remains defensible as a shipped default with an active Fed.
3. **`productivity_passthrough = 0.30`** sits between Acemoglu (0.12–0.155) and the micro/AGI
   evidence (0.5–1.0) — defensible; presets span the range.
4. **`lfp_exit_rate = 0.03` and `attrition_rate = 0.025`** match Farber/Windfall almost exactly. ✓
5. **Reabsorption default 0 ("the thesis")** is *below* every empirical anchor (worst measured:
   China Shock ~0.05–0.10/yr). Keep as the thesis pole; presets carry the literature values.

## 6. Known gaps the evidence exposed (report caveats)

- **No behavioral response to the robot tax** (Korea: −28% installations per 2pp). Our
  `automation_tax_rate` changes only the fiscal split, never adoption. Hand-code via lower adoption
  end or longer `robotics_lag` when running high-tax counterfactuals.
- **Augmentation is not represented** — the model displaces or leaves alone; GenAI-at-Work-style
  within-job productivity with retention maps only loosely onto survivor gains.
- **CZ→national external validity**: China Shock and Chodorow-Reich are cross-sectional local
  estimates; national general-equilibrium offsets (and Fed response) could shrink them.
- **Exposure measures disagree in shape**: Eloundou flattens at the top (Job Zone 4 > 5), Webb
  peaks at ~p90. The percentile exposure mapping should eventually take a distribution choice.
- **AGI presets strain the frame**: Korinek-Suh's 18%/yr post-collapse growth and MacAskill-Moorhouse's
  century-in-a-decade are outside a fixed-baseline fiscal ledger; presets ⑤⑥ are transition stories,
  not steady states.

---

## Appendix — per-paper verified anchors

*(All quotes verbatim in [research/preset-evidence-raw.json](research/preset-evidence-raw.json).)*

**Exposure.** Eloundou et al. 2023 (arxiv.org/abs/2303.10130): 80% of workers ≥10% tasks exposed;
19% ≥50%; α=15% of all tasks (bare LLM), ζ=47–56% (with software); exposure rises with wage.
Felten-Raj-Seamans 2023 (arxiv 2303.01157): LM-AIOE relative index over 774 occupations (no levels);
corr. 0.979 with all-application AIOE. Webb 2020 (webb_ai.pdf): robots p25→p75 exposure = −9 to −18%
employment, −8 to −14% wages over 1980–2010; AI exposure peaks ~p90 wages.

**Acemoglu 2024** (NBER w32487): TFP ≤0.66%/10y (≤0.53% adjusted); 19.9% wage-bill exposure ×
23% profitable = 4.6% of tasks in 10y; 27% task-level labor-cost savings; GDP ~1.1%; capital share
+0.38pp.

**Brynjolfsson micro.** GenAI at Work (QJE 2025): +15% avg, +30% novices, ~0 experts; −40%
attrition of newer agents. Canaries (Stanford DEL 2025): −16% relative employment ages 22–25 in
most-exposed occupations; declines only where AI *automates*, growth where it augments; ~0 salary
differential. J-Curve (AEJ:Macro 2021): TFP understated 11.3–15.9%; intangible co-investment
2.7–4.1× observable.

**Scarring.** Davis–von Wachter 2011 (Brookings): PDV loss 1.4y (tight) / 2.8y (slack) of
pre-displacement earnings; persistent annual loss ~10%/~20% at 10–20y. JLS 1993 (AER): 25%/yr
long-term loss, high-tenure mass layoffs. Farber 2015 (w21216): 16% lost jobs 2007–09; 44%
re-employed within ~1y (deep slack); weekly earnings decline 13–17.5% (survivor-selected); ~10% NILF.

**Adjustment.** ADH China Shock 2016: ≥10y depressed wages/LFP; per $1k exposure: mfg emp −0.60pp,
NILF +0.55pp, unemployment +0.22pp; transfers offset ~10% of lost earnings. Chodorow-Reich 2019:
cross-sectional multiplier 1.8; ~2 job-years per $100k; no-offset national ≥1.7; Clemens-Miran
balanced-budget multiplier 0.29 (lower bound).

**Robot tax.** GRT (REStud 2022): optimal 5.1%→2.2%→0.6% by decade, steady state 0; US effective
robot taxation 10%→5% post-TCJA. Thuemmel (JEEA 2023): 0.86–1.8% (WP); published: ≈0, subsidy when
robots expensive. Costinot-Werning (REStud 2023): 1–3.7% sufficient statistic; decreases with
depth. Holtmann et al. 2025: Korea 2pp credit cut → −28% installations.

**Korinek.** Korinek-Suh (w32255): BAU λg=0.01/yr; AGI 20y/5y to full automation; wage collapse ~3y
before full automation (aggressive); post-AGI output growth 18%/yr. Korinek-Stiglitz (w24174):
taxonomy; Frey-Osborne 47% cited; non-distorting windfall taxation possible. Korinek-Lockwood
(w34873): AGI-capital tax ≈ discount rate ~4%/yr of stock; rents taxable up to ~100%; labor-tax
revenue → 0 as capital share → 1; US tax/GDP ~0.25.

**Takeoff.** Davidson 2023: 20%→100% automation capability median ~3y (~50% <3y, ~80% <10y);
median full cognitive automation 2043. AI 2027: SC Mar 2027 → ASI ~Apr 2028; ~1M robots/mo by end
2028; authors' updated TED-AI medians Dec 2030 (Kokotajlo) / Jan 2035 (Lifland).
MacAskill-Moorhouse 2025: ≥century of progress in <10y; effective compute >30×/yr; AI research
effort ~10×/yr over a decade.

**Fiscal comparators.** RAND WRA4443-1: see §4. Windfall (local PDF): labor ETR 39% vs capital
26.7%; exposed = 60% of jobs; displacement 20/50/80%; scarring 20/30/40%; LFP exit 10/20/30% over
3/6/9y. Epoch GATE (arxiv 2503.04941): full-automation compute 1e36.5 eFLOP (1e33–1e41); f_init
0.1; ρ=−0.65 (subst. elasticity ~0.6); reallocation modeled only as perfect-vs-none brackets.
