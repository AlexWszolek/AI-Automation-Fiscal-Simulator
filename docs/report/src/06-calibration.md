{{pagebreak}}

# 6. Calibration: scenarios and policy overlays

The model has roughly thirty continuous levers. Rather than defend one setting, we anchor them to
the literature — every anchor fetch-verified against the source text, with verbatim quotes and
URLs preserved in the repository's evidence base — and package coherent configurations as
**presets**. Three unit conversions recur and are worth stating once, because getting them wrong
changes answers by an order of magnitude.

1. **Exposure is not feasibility is not adoption.** Task-exposure measures (Eloundou et al.'s
   "GPTs are GPTs") are time-savings potentials, agnostic between augmentation and substitution.
   We treat them as upper bounds on *feasibility* and let *adoption* — a cumulative ceiling with
   its own timeline — carry realized automation.
2. **Ad-valorem robot taxes are levied on robot spending, not on saved wages.** The
   optimal-taxation literature's "1–3.7 percent robot tax" (Costinot–Werning) applies to the price
   of automation inputs. On this model's saved-compensation base the equivalent rate is that
   number **times `auto_cost`** — roughly 0.3–1 percent, not 3 percent. Presets that skip this
   conversion overstate optimal robot-tax revenue by 10–25×.
3. **Present-value earnings losses bundle spells with scars.** Davis–von Wachter's 1.4–2.8 years
   of pre-displacement earnings include unemployment time the model prices separately through UI
   and reabsorption; only the long-run *annual* loss (10–20 percent, ten-plus years out) maps to
   the permanent re-employment haircut.

## 6.1 The seven scenarios

Each preset is a full lever configuration with per-lever provenance (the application surfaces the
anchor sentence for every value; the evidence document carries the quotes). In brief:

1. **Acemoglu — Modest AI.** His ten-year upper bounds at face value: 19.9 percent of the wage
   bill exposed, 23 percent of exposed tasks profitably automatable within the decade, a
   0.15 productivity pass-through implied by his TFP arithmetic, no wage response, and a normal
   labor market (Farber-central haircut 0.13, reabsorption 0.5/year).
2. **Brynjolfsson — Augmentation.** AI complements more than it substitutes: adoption starts near
   the realized pace measured in early payroll data (~2 percent cumulative), survivors capture a
   fifth of the surplus with positive wage complementarity, scarring is mild, and productivity
   pass-through is strong (the GenAI-at-Work gains).
3. **Windfall Trust — Medium.** Their medium displacement scenario translated onto our levers: 60
   percent of jobs exposed, half of exposed work automated over the decade, re-employment at 70
   percent of prior wage, their high-value-capture disposition, and capital taxed at their
   26.7 percent ETR. The direct external comparator (Section 9).
4. **China-Shock Grind.** A moderate shock met by the labor market Autor, Dorn, and Hanson
   actually measured: reabsorption at 0.075/year (decade-scale adjustment), labor-force exit the
   dominant margin, JLS-severity scarring, and full demand amplification, over fifteen years. The
   mechanism preset: displacement is moderate but nothing heals.
5. **Korinek–Suh — AGI in 20 years.** Full automation over twenty years, wages collapsing before
   the end, capital keeping the gains, states forced onto spending cuts.
6. **Korinek–Suh — AGI in 5 years.** The aggressive transition as its own stress case: a kinked
   adoption path reaching full automation at year five, viewed over a ten-year fiscal window.
7. **AI 2027 — Fast takeoff.** The AI Futures Project's scenario shape: cognition maxes almost
   immediately, robots ramp over three years through crash build-out, heavy compute investment,
   an eight-year horizon.

The as-shipped lever table for all seven appears in Appendix B.

## 6.2 The four policy overlays

Policy composes on top of any scenario and overrides the corresponding levers:

- **Robot tax, Costinot–Werning optimal** — 2.7 percent ad-valorem on robot spending (their
  sufficient-statistic central value), converted through `auto_cost`.
- **Robot tax, Guerreiro–Rebelo–Teles transitional** — their 5.1 percent decade-one Mirrleesian
  rate; their steady state is zero, and the overlay flags that holding decade-one constant
  overstates the tax beyond year ten.
- **UBI** — $12,000 per worker per year with 30 percent recapture (income-tax clawback per
  Korinek–Lockwood's 0.25–0.375 range).
- **Compute-pool parity** — the compute-capital pool taxed like domestic capital (26.7 percent,
  the Windfall capital ETR) instead of the 5 percent post-TCJA effective rate.

Scenarios ship with the robot tax at zero deliberately. The separation keeps the question clean:
Section 7 reports what each world does to the budget; Section 8 reports what policy recovers.
