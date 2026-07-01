# V2 model — lever & equation reference

How every lever affects the model, as the exact equations in `fiscal_model/`. Reflects the post-accuracy-
overhaul v2 (`DynamicModelV2`). **Notation:** a *cell* = (occupation × state); `Σ` sums over cells (or
states where noted). Fiscal **losses are positive** (they worsen the deficit); recoveries subtract. `t` is
the period (year).

---

## Part 0 — The fixed per-worker channel deltas (precomputed, cached)

For each cell, displacing one worker produces a per-worker fiscal delta by channel. These are **baked once**
(scenario-invariant) into `data/interim/worker_deltas_by_occ_state.parquet` and scaled by worker counts in
the loop (`fiscal_model/kernel.py`, `rates.py`, `integrate.py`):

- **Income tax lost** (fed/state): `Δinc = T(HH) − T(HH − wage)` — exact progressive-bracket difference, per
  filing, integrated over the within-cell income distribution.
- **Payroll (FICA)**: `OASDI·min(wage,cap) + Medicare·wage + Addl·max(wage−thresh,0)` (employer+employee).
- **Consumption**: `Δcons = rate_state · marginal_taxable_multiplier · mpc · consumption_stickiness · max(0, disposable_loss)`.
- **Corporate offset** (per worker): `surplus_capture·comp → corp_tax + dividend_tax_rate·dividends + passthrough_individual_rate·pass_income`.
- **Transfers** (fed/state): `interp(income_after) − interp(income_before)` over the PolicyEngine-baked
  grids, split by FMAP `fed_share` (Medicaid 0.65, SNAP/EITC/CTC/ACA 1.0, TANF 0.5, SSI 0.95).

> **Build-time levers** (frozen in the cache): `surplus_capture, dividend_tax_rate,
> passthrough_individual_rate, mpc, consumption_stickiness, marginal_taxable_multiplier`. On a normal v2
> run with a fixed cache, **changing these does nothing to the cached channels** — they only take effect if
> the cache is rebuilt at that kernel. (Exception: `mpc` and `consumption_stickiness` *also* enter the
> lagged-demand impulse **live** — see Step 9.)

---

## Part 1 — The within-period sequence (period t)

### Step 1–2 · Diffusion & displacement  (`levers.py`, `workers.py`)
Per-occupation exposure→displacement fraction (built once at adoption=1):
```
cog(o)   = percentile-rank(PCA)   or   1/(1+exp(−logistic_steepness·(PCA − logistic_midpoint)))
g_cell   = 1 − (1 − cog·cognitive_feasibility)·(1 − robot·physical_feasibility)
```
Cumulative diffusion **ceiling**, tracking a per-cell automated stock `auto_disp` (`workers.displacement_flow`):
```
target_t = clip(g_cell · adoption(t), 0, 1) · emp0        # adoption(t) = adoption_path[t] (or scalar adoption)
flow_t   = clip(target_t − auto_disp, 0, employed)        # this period's automation displacement
auto_disp += flow_t
employed −= flow_t ;  on_ui = flow_t                      # displace()
```
Lagged induced layoffs from t−1 land now (Step 9 stores them; 0 at t=0):
```
induced_applied = min(induced_pending, employed) ;  employed −= induced_applied ;  induced += induced_applied
```

### Step 3–4 · Disposition router (the firm side)  (`firms/disposition.py`, `compute_pool.py`)
```
automated  = on_ui + exhausted + exited                   # NOT induced, NOT reabsorbed
saved_bill = Σ automated · comp_per_worker
automation_spend = auto_cost · saved_bill
net_saving = saved_bill − automation_spend
retained_profit = retained_profit_share · net_saving
price_reduction = price_reduction_share · net_saving
survivor_gains  = survivor_gains_share  · net_saving      # shares must sum to 1 (asserted)
corp_offset_cell = automated · corp_per_worker · [retained_profit_share · (1 − auto_cost)]
```
Compute pool:
```
offshore_leak = offshore_share · automation_spend         # shipped default 0
compute_tax   = (automation_spend − offshore_leak) · compute_effective_rate
```

### Step 5 · Survivor wage index (capacity-capped)  (`dynamics_v2.py`, `survivor.py`)
```
wage_bill = Σ employed · wage                             # post-displacement survivors
room      = wage_bill · (survivor_raise_ceiling − W_mech) # ∞ if ceiling = inf
actual_inflow = min(survivor_gains, room)                 # 0 if wage_bill = 0
overflow  = survivor_gains − actual_inflow
overflow_to_profit = overflow · survivor_spillover_to_profit
overflow_to_price  = overflow − overflow_to_profit
W_mech   += actual_inflow / wage_bill                     # sticky, ≤ ceiling
market_frac = survivor_elasticity · slack_prev            # slack_prev = prior cumulative drop; 0 at t=0
W_surv   = clip(W_mech + market_frac, 0, survivor_raise_ceiling)
```
Survivor tax effect (per cell, gain = revenue up), Δw = wage·(W_surv − 1):
```
sd_fed   = Σ_filing weight·[T_fed(hh+Δw) − T_fed(hh) + FICA(wage·W_surv) − FICA(wage)] · employed
sd_state = Σ_filing weight·[T_state(hh+Δw) − T_state(hh)] · employed
```
Survivor–capital coupling  (`r_corp = Σ(automated·corp_pw)/saved_bill`):
```
overflow_corp_tax       = r_corp · overflow_to_profit            # extra corp recovery
survivor_profit_netting = r_corp · wage_bill · (W_mech_old − 1)  # standing raise ⇒ less corp profit (raises deficit)
price_reduction_total   = price_reduction + overflow_to_price
```

### Step 6 · Macro  (`macro.py`)
```
Y    = 1 + productivity_passthrough · (saved_bill / COMP_TOTAL)   # output-weighted dividend
P    = 1 − price_passthrough · (price_reduction_total / (VA_BASE · Y))
nGDP = VA_BASE · Y · P                                            # VA_BASE = $29.3T, COMP_TOTAL = $15.0T
```

### Step 7 · Federal ledger (losses +)  (`dynamics_v2.py`)
```
fed_cell = inc_fed + payroll_fed + transfer_fed + ui_outlay − ui_tax − corp_offset_cell − sd_fed
net_fed  = Σ fed_cell − compute_tax − overflow_corp_tax + survivor_profit_netting
```
Reabsorbed contribution inside `inc_*/transfer_*`:
```
rung 0:  reabsorbed · reemployment_haircut · after_delta         (tax channels only — the C8 anchor)
rung 1:  reabsorbed · reab_delta[channel]                        (all 6 channels; see Step 10)
ui_outlay = on_ui · ui_benefit · ui_share  ;  ui_share = min(1, ui_weeks/52)  ;  ui_tax = 0.10·ui_outlay
```

### Step 8 · State balanced-budget close (each of 51 states)  (`government.py`)
```
state_net[s]     = Σ_{cells∈s} (inc_state + cons_state + transfer_state − sd_state)
taxable_base[s]  = Σ_{cells∈s} employed · wage · W_surv
gap[s]           = max(0, state_net[s])
cut_share        = 0 (raise_rates) | 1 (cut_spending) | state_cut_share (mix)
rate_target      = gap·(1 − cut_share)
recovered[s]     = min(rate_target, state_rate_hike_cap · taxable_base[s])
spending_cut[s]  = gap·cut_share + (rate_target − recovered)          # infeasible hike → forced cut
contraction      = Σ (spending_cut · MPC_GOV + recovered · mpc)       # MPC_GOV = 1.0 (mode-dependent)
```

### Step 8.5 · Federal policy flows  (`dynamics_v2.py`)
```
ubi_outlay     = ubi_annual · baseline_emp                   # a real outlay (raises deficit)
automation_tax = automation_tax_rate · saved_bill            # robot tax (lowers deficit)
net_fed       += ubi_outlay − automation_tax
debt           = debt·(1 + interest_rate) + net_fed
ubi_required_rate = ubi_annual · baseline_emp / wage_bill    # reported financing metric
```

### Step 9 · Second-round demand → stored for t+1  (`dynamics_v2.py`)
```
disposable_pw    = wage − inc_tax − emp_fica − ui
income_withdrawn = contraction + Σ (new + induced_applied) · disposable_pw
induced_dollars  = demand_multiplier · mpc · consumption_stickiness · income_withdrawn
induced_jobs     = induced_dollars / (VA_BASE / baseline_emp)
induced_pending  = induced_jobs · (employed / Σ employed)    # per-cell, applied at the START of t+1
```

### Step 10 · Period end — worker transitions  (`workers.age_and_transition`)
```
pool = exhausted + on_ui
reabsorbed += pool · reabsorption_rate
exited     += pool · lfp_exit_rate
exhausted   = pool − pool·(reabsorption_rate + lfp_exit_rate)
exited     += exhausted · attrition_rate ;  exhausted −= exhausted · attrition_rate   # baseline attrition
slack_prev  = 1 − (Σ employed)/baseline_emp
```
**Reabsorbed destination wage** (rung 1, live engine `reabsorption.ReabsorptionEngine`):
`w_d = max(wage·(1 − reemployment_haircut), service_floor)`,  `wage_removed = wage − w_d`. The 6-channel
`reab_delta` is `T(hh)−T(hh−wage_removed)`, `FICA(wage)−FICA(w_d)`, consumption on the take-home drop, and
`interp(hh−wage_removed) − interp(hh)` for transfers. **`haircut=0 ⇒ wage_removed=0 ⇒ all channels 0`
(reabsorbed fiscally whole).**

### Reporting
```
fed_deficit_B = net_fed/1e9    fed_deficit_real_B = net_fed/P/1e9    fed_deficit_pct_gdp = 100·net_fed/nGDP
fed_deficit_abs_B = 1833 + net_fed/1e9    state_gap_B = Σ gap / 1e9
```

---

## Part 2 — Per-lever effect table

| Lever | Enters | Effect |
|---|---|---|
| `cognitive_feasibility` | `g_cell = 1−(1−cog··)(1−robot··)` | ↑ cognitive displacement |
| `physical_feasibility` | `g_cell` (robot channel) | ↑ physical/robotics displacement |
| `exposure_mapping` / `logistic_steepness` / `logistic_midpoint` | `cog(o)` map | shape of exposure→share (percentile vs S-curve) |
| `adoption` / `adoption_path[t]` | `target = g_cell·adoption(t)·emp0` | **cumulative ceiling**: share of feasible work automated by t |
| `auto_cost` | `automation_spend = auto_cost·saved_bill`; shrinks `corp_offset` via `(1−auto_cost)` | shifts saved bill to the compute pool; less corp recovery |
| `retained_profit_share` | `corp_offset ∝ share`; `retained_profit` | corp recovery ↑ |
| `price_reduction_share` | `price_reduction → P` | deflation (real/%-GDP only) |
| `survivor_gains_share` | `survivor_gains → W_mech` | survivor raises → income/payroll ↑ |
| `offshore_share` | `offshore_leak`, `compute_tax` | leaks compute base (shipped **0**) |
| `compute_effective_rate` | `compute_tax = domestic·rate` | compute-pool federal revenue |
| `survivor_raise_ceiling` | caps `W_mech`, `W_surv` | bounds survivor raise; overflow spills |
| `survivor_elasticity` | `market_frac = elasticity·slack_prev` | − substitution / + complementarity on survivor wages |
| `survivor_spillover_to_profit` | splits `overflow` → profit vs price | fed/state split of un-absorbed raises |
| `productivity_passthrough` | `Y = 1 + pt·(saved_bill/COMP_TOTAL)` | real-GDP dividend → shrinks deficit/GDP |
| `price_passthrough` | `P = 1 − pp·(price_red/real_GDP)` | deflation → real/%-GDP columns only (nominal invariant) |
| `automation_tax_rate` | `automation_tax = rate·saved_bill` | robot tax → federal revenue ↑ |
| `reabsorption_rate` | `reabsorbed += pool·rate` | more re-employed (at `w_d`) |
| `reabsorption_rung` | 0 = flat haircut / 1 = live engine | which reabsorption model |
| `reemployment_haircut` | `w_d = max(wage·(1−haircut), floor)` | reabsorbed wage cut; **0 ⇒ whole** |
| `reabsorption_floor_pctile` | `service_floor` (p-th low-exposure wage) | the floor `w_d` can't drop below |
| `lfp_exit_rate` | `exited += pool·rate` | permanent LFP/SSDI exit |
| `attrition_rate` | `exited += exhausted·rate` | baseline natural exit of long-term unemployed |
| `ui_weeks` | `ui_share = min(1, weeks/52)` | UI outlay window (blend of during/after) |
| `demand_multiplier` | `induced_dollars = dm·mpc·stick·withdrawn` | strength of the second-round layoff spiral |
| `state_response` / `state_cut_share` | `cut_share` in the close | rate hikes vs spending cuts |
| `state_rate_hike_cap` | `recovered = min(target, cap·base)` | feasibility bound → spills to cuts → (via contraction) fed deficit |
| `interest_rate` | `debt = debt·(1+r) + net_fed` | debt compounding |
| `ubi_annual` | `ubi_outlay = ubi·baseline_emp` | federal outlay ↑ + reported required rate |
| `denominator` | headline = $B or %-GDP | reporting only |
| `mpc`, `consumption_stickiness` | **live** in Step 9 (+ frozen in cons cache) | second-round demand magnitude |
| `surplus_capture`, `dividend_tax_rate`, `passthrough_individual_rate`, `marginal_taxable_multiplier` | frozen in the delta cache | build-time only — inert on a fixed cache |

---

## Conservation identities (the invariants these equations satisfy)

`C1` six worker states sum to baseline per cell · `C2/C5b` disposition partition + meter · `C3` compute
pool flow · `C4` real = nominal/P · `C5c` survivor routing conserves survivor_gains · `C6` federal
reconciliation (`net_fed = Σ` labelled components incl. `+ubi_outlay − automation_tax`) · `C6-state`
per-state composition · `C7` state gap closes · `C8` v2 == v1 at `DEFAULTS_V1REDUCTION`. See
`tests/test_v2_phase*.py` and `tests/test_overhaul.py`.
