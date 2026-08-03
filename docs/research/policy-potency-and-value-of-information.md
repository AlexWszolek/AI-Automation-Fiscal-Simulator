# Instrument potency and the value of information

**What this is:** the evidence base for deciding what a funded research programme should buy. It
answers three questions the committed §7.14 screening structurally cannot, using a paired sweep
built for the purpose.

**What this is not:** a proposal, or prose for one. The framing, the ask, and the voice are Alex's.
This document supplies numbers, mechanisms, and the caveats that go with them.

**Reproduce:** `.venv/bin/python scripts/policy_sweep.py` (~70 min, 35,000 runs, every one passing
the C1–C8 battery) then `.venv/bin/python scripts/policy_sweep_report.py`. Summary tables are
committed under `docs/research/policy-sweep/`; the raw parquet is gitignored and regenerable.
Run of record: n = 5,000 per arm, seed 0, 10-year horizon, `DEFAULTS_SHIPPED` template.

---

## Why a new sweep

`scripts/global_screening.py` samples the 7 policy dims uniformly alongside the 19 uncertainty
dims. That is the correct design for "what matters anywhere in the lever space", and it is what
report §7.14 reports. But it means **the policy dims carry 79% of total outcome variance**, with
`ubi_annual` alone at 63% — so the marginal outcome distribution is substantially a picture of how
expensive a UBI is, and every marginal correlation is contaminated by it.

This sweep samples the same 19 uncertainty dims by the same LHS construction and **pins** the
policy dims to a named regime. Same seed and same dims dict means the permutations are identical
across arms, so the draws are **paired**: each arm re-runs the *same 5,000 worlds* under different
policy. Arm-to-arm differences are therefore per-world treatment effects, and "how much of the hole
does this close" is a per-world ratio rather than a comparison of two marginal medians.

`ubi_annual` is pinned at 0 in every arm deliberately. A UBI is an *outlay* whose size is a
political choice spanning $0–7.8T gross; letting it vary would once again drown the instrument
question, which it has nothing to do with.

---

## Finding 1 — the hole is robust, and smaller than the headline

With no automation-side instrument and no UBI, across 5,000 sampled worlds:

| | final-year federal deficit Δ, year 10 |
|---|---|
| worsens | **95.2%** of worlds |
| p5 | +$2B |
| p25 | +$154B |
| **median** | **+$414B** |
| p75 | +$878B |
| p95 | +$1,917B |
| max | +$4,801B |

The direction is close to universal: only 4.8% of worlds improve the federal balance. You cannot
pick a favourable corner of the uncertainty space and make the problem go away.

**But the magnitude is well below the §7.14 headline.** That sweep reports a median of +$1,478B and
53% of draws worsening by more than 3% of GDP. Most of that gap is UBI outlay, not AI. The honest
headline is the one above: **a median of roughly $400B/yr by year ten, robust in sign across
essentially the whole uncertainty space.** Quoting the $1,478B figure as "the fiscal cost of AI"
would not survive a reviewer who reads the sampling design.

---

## Finding 2 — the ladder: what rate closes it

Paired, per world. "% of hole closed" is the median across worlds of `1 − arm/no-instruments`.

| regime | median Δdeficit | worlds worsening | vs no-instruments | % of hole closed | fully closed |
|---|---|---|---|---|---|
| no-instruments | +$414B | 95.2% | — | — | 4.8% |
| status-quo (10% compute) | +$282B | 90.6% | −$105B | 26.5% | 9.4% |
| compute-20 | +$150B | 78.2% | −$209B | 53.0% | 21.8% |
| **compute-40** | **−$40B** | **41.7%** | **−$419B** | **106.1%** | **58.3%** |
| auto-25 | +$197B | 80.4% | −$205B | 41.6% | 19.6% |
| auto-50 | +$129B | 70.6% | −$273B | 52.7% | 29.4% |
| max-revenue | −$288B | 17.0% | −$823B | 167.2% | 83.0% |

Read `max-revenue` as an upper bound, not a proposal: `automation_tax_frac = 1.0` taxes away *all*
retained automation profit net of cost.

The substantive result is the middle of the ladder. **A compute tax at 40% closes the median hole
outright** and fully closes it in 58% of worlds; the 10% already in the baseline closes about a
quarter of it. The automation-side tax base is large relative to the fiscal hole — which does *not*
mean it is large relative to a UBI, a far bigger number that this sweep deliberately excludes.

> **This corrects an earlier reading of §7.14.** The marginal η² ranking (`ubi_annual` 0.63,
> `compute_effective_rate` 0.03) was taken to mean the automation-side instruments were an order of
> magnitude too weak to matter. That inference does not hold: η² is variance share *over the
> sampled range*, so the ratio reflects how wide the ranges were drawn as much as what the
> instruments can raise. Potency has to be measured by a paired intervention, which is what this
> sweep does.

---

## Finding 3 — a compute tax is an automatic stabiliser

Median final-year deficit Δ, by how far automation actually goes (`adoption_end` quintile):

| adoption_end | no-instruments | status-quo | compute-20 | compute-40 |
|---|---|---|---|---|
| 0.05–0.24 | +$112B | +$75B | +$36B | −$21B |
| 0.24–0.43 | +$300B | +$208B | +$113B | −$43B |
| 0.43–0.62 | +$502B | +$343B | +$187B | −$60B |
| 0.62–0.81 | +$707B | +$491B | +$277B | −$80B |
| 0.81–1.00 | +$963B | +$701B | +$420B | −$49B |
| **spread (max−min)** | **$851B** | $626B | $385B | **$59B** |

Without an instrument, the fiscal outcome is almost linear in how much automation happens — an
$851B spread across the range. Under a 40% compute tax that spread collapses to **$59B**: the
outcome becomes nearly independent of the single largest driver of the harm.

The mechanism is not subtle — the tax base *is* automation spending, so revenue grows with exactly
the thing causing the revenue loss — and it shows up in the driver table as `adoption_end` falling
from η² 0.277 to 0.001 between those two arms. The same structure appears in the scaling test:
Spearman ρ between "size of the hole" and "revenue raised" is **0.74** for every compute-tax arm,
and a 40% compute tax raises $98B in the mildest quintile of worlds against $1,339B in the worst.

**This is the strongest single result here, and the one most worth attacking.** It is a model
result contingent on how compute spending is tied to adoption and on `auto_cost` — and the price of
the hedge is visible: under compute-40, `auto_cost` becomes the *top* driver (η² 0.153, up from
0.085). You have not removed uncertainty, you have swapped "how much automation happens" for "what
automation costs". Whether that trade is as favourable in reality as it is here is a question worth
funding, not a conclusion to assert.

---

## Finding 4 — what we don't know, and it depends on the policy

Debiased first-order η² against the final-year federal deficit, by arm (n = 5,000; null bias 0.004,
removed via the same `eta_squared` used in §7.14). Levels below 0.01 in every arm are omitted:
`robotics_lag`, `ui_weeks`, `attrition_rate`, `productivity_passthrough`, `baseline_growth_rate`,
`survivor_raise_ceiling`, `survivor_spillover_to_profit`, `price_passthrough`.

| uncertain input | no-instr | status-quo | compute-20 | compute-40 | auto-25 | auto-50 | max-rev |
|---|---|---|---|---|---|---|---|
| `adoption_end` | **0.277** | 0.224 | 0.136 | 0.001 | 0.141 | 0.065 | 0.105 |
| `cognitive_feasibility` | 0.103 | 0.078 | 0.041 | 0.003 | 0.046 | 0.018 | 0.062 |
| `auto_cost` | 0.085 | 0.031 | 0.001 | **0.153** | 0.084 | **0.143** | 0.008 |
| `reabsorption_rate` | 0.067 | 0.094 | **0.123** | 0.116 | 0.096 | 0.084 | 0.055 |
| `survivor_elasticity` | 0.042 | 0.062 | 0.085 | 0.089 | 0.065 | 0.059 | 0.048 |
| `physical_feasibility` | 0.040 | 0.034 | 0.023 | 0.001 | 0.024 | 0.013 | 0.009 |
| `demand_multiplier` | 0.039 | 0.055 | 0.074 | 0.072 | 0.056 | 0.048 | 0.034 |
| `price_reduction_share` | 0.038 | 0.054 | 0.072 | 0.071 | 0.093 | 0.124 | **0.170** |
| `lfp_exit_rate` | 0.037 | 0.050 | 0.063 | 0.056 | 0.052 | 0.047 | 0.029 |
| `reemployment_haircut` | 0.031 | 0.043 | 0.055 | 0.050 | 0.042 | 0.036 | 0.022 |
| `retained_profit_share` | 0.000 | 0.000 | 0.000 | 0.000 | 0.019 | 0.073 | **0.222** |
| Σ first-order | 0.773 | 0.741 | 0.691 | 0.624 | 0.730 | 0.720 | 0.766 |

Three things fall out:

1. **Value of information is policy-dependent.** With no instrument, the thing worth knowing is how
   far automation goes. Adopt a compute tax and that question is hedged away, while the cost of
   automation — the tax base — becomes what you most need to know.
2. **`reabsorption_rate` is the one input that matters under every policy** (0.055–0.123 across all
   seven arms). It is the robust research target: whatever policy is chosen, labour-market
   reabsorption still drives the outcome.
3. **Σ first-order ≈ 0.62–0.77**, so a quarter to a third of the variance is interaction. Ranking
   single inputs is informative but incomplete; total-effect (Sobol) indices need a different
   sampling design and are not computable from this one.

### A measurement trap worth stating explicitly

`automation_tax_frac` is a fraction of the capacity bound `retained·(1−auto_cost)`, so
**`retained_profit_share` literally *is* the automation tax base.** In the row above it reads
exactly 0.000 in all four arms with no automation tax, then climbs 0.019 → 0.073 → 0.222 as the
tax rises. Any sweep with the automation tax live will rank it as a top "uncertainty" driver purely
through that coupling.

This matters because an earlier pass over §7.14 did exactly that, and concluded that the
disposition of the saved wage bill was the dominant empirical unknown — ahead of reabsorption,
where the labour literature has concentrated. **That conclusion was an artifact** of the coupling
plus small-sample η² bias in the thin conditioning subsets (n = 165–500, where the null bias alone
is 0.04–0.12). Under a clean policy-pinned design, `retained_profit_share` is indistinguishable
from zero. Rank uncertainty drivers on a policy-pinned arm; never on a sweep with policy live.

---

## Sizing the state channel honestly

The README thesis says states "bear an unfinanceable gap". In the §7.14 sweep the central case is
milder: median cumulative state adjustment of **$413B over ten years** (hikes plus cuts) against a
cumulative federal deterioration of **$15,026B** — about 3%. States hit their rate-hike cap
anywhere in 0.6% of draws, though in the worst draws all 51 jurisdictions do.

The state story is real and it is a *different kind* of harm — realised service cuts and tax rises
rather than federal borrowing — but "unfinanceable" overstates the central case, and a reviewer who
runs the numbers will find that. Worth softening before it reaches one.

---

## What this does not show

- **Rates are not calibrated to feasibility.** 40% is the top of the §7.14 sampled range, not an
  estimate of what is administrable or incidence-neutral. There is no behavioural response to the
  tax in the model: no compute relocating offshore, no investment timing shift, no avoidance. A
  compute tax that raises $419B in the median world here would face all three.
- **One horizon, one template.** Ten years, `DEFAULTS_SHIPPED` structure, reabsorption rung 1.
- **First-order indices only** — see the interaction share above.
- **The UBI question is excluded by construction**, not answered. "Can automation-side taxes fund a
  UBI" is a different and much harder question than "can they close the fiscal hole", and only the
  second is answered here.

---

## The agenda this argues for

Ordered by what the evidence actually supports, not by what is easiest to fund:

1. **Empirical work on the compute/automation tax base — its size, elasticity, and avoidability.**
   This is where the model says the leverage is, and it is the input the model is currently least
   entitled to: `auto_cost` becomes the top driver the moment an instrument is adopted, and there
   is no behavioural response modelled at all. Highest value of information, conditional on the
   policy actually being on the table.
2. **Reabsorption rates and scarring.** The one input that matters under every policy regime, and
   the one with an existing empirical literature to build on (ADH and the displacement work already
   anchoring the presets).
3. **A Sobol-design screening for total effects.** A quarter to a third of outcome variance is
   interaction that the current design cannot attribute. Cheap relative to its interpretive value,
   and it would tell you whether the single-driver story above survives.
4. **External review of the accounting.** §9 triangulates against three models; no person outside
   the project has checked the ledger. This is the cheapest credibility available and it is not a
   research task.

The claim that carries this, and that the sweep supports: **the fiscal hole is robust in sign
across essentially the entire uncertainty space, its median size is on the order of $400B/yr by
year ten, and the instrument best matched to it is one whose base grows with the harm.** That is a
finding about the structure of the problem, and it is falsifiable.
