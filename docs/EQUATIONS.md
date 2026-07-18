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
Per-occupation exposure→displacement fraction. The ROBOT channel ramps over `robotics_lag` years
(physical automation needs AI-built industrial capacity; ramp=1 when lag=0):
```
cog(o)   = percentile-rank(PCA)   or   1/(1+exp(−logistic_steepness·(PCA − logistic_midpoint)))
ramp_t   = min(1, t/robotics_lag)                         # 1 if robotics_lag == 0; at robotics_base b>1
         = min(1, (b^t − 1)/(b^robotics_lag − 1))         #   exponential build-out (robots building robots)
g_cell_t = 1 − (1 − cog·cognitive_feasibility)·(1 − robot·physical_feasibility·ramp_t)
```
Cumulative diffusion **ceiling**, tracking a per-cell automated stock `auto_disp` (`workers.displacement_flow`):
```
target_t = clip(g_cell_t · adoption(t), 0, 1) · emp0      # adoption(t) = adoption_path[t] (or scalar adoption)
flow_t   = clip(target_t − auto_disp, 0, employed)        # this period's automation displacement
auto_disp += flow_t
employed −= flow_t ;  on_ui = flow_t                      # displace()
```
The t−1 SIGNED demand-controller flow lands now (Step 9 stores it; 0 at t=0):
```
positive → displace_extra (employed → induced, capped at employed)
negative → release_induced (induced → employed, capped at induced)   # stimulus re-hires
```

### Step 3–4 · Disposition router (the firm side)  (`firms/disposition.py`, `compute_pool.py`)
The automated-jobs base is the CUMULATIVE `auto_disp` (a job stays automated after its worker moves on —
reabsorption/attrition never un-automate it; induced excluded, demand layoffs save no comp):
```
saved_bill = Σ auto_disp · comp_per_worker
automation_spend = auto_cost · saved_bill
net_saving = saved_bill − automation_spend
retained_profit = retained_profit_share · net_saving      # the PRE-tax partition leg
price_reduction = price_reduction_share · net_saving
survivor_gains  = survivor_gains_share  · net_saving      # shares must sum to 1 (asserted)
corp_offset_cell = auto_disp · corp_per_worker · [retained_profit_share·(1−auto_cost) − automation_tax_rate]
```
(the robot tax is PAID from retained profit, corp-deductibly — the offset shrinks by corp_rate·tax;
`automation_tax_rate ≤ retained_profit_share·(1−auto_cost)` asserted). Compute pool:
```
offshore_leak = offshore_share · automation_spend         # shipped default 0
compute_tax   = (automation_spend − offshore_leak) · compute_effective_rate
```

### Step 5 · Survivor wage index — FUNDED W*  (`survivor.funded_w_update`)
The routed `survivor_gains` flow pays the standing raise's recurring cost FIRST; only the surplus raises
W (converging W* = 1 + gains/(ℓ·wage_bill), ceiling-capped); unfundable → W snaps to the funded level.
ℓ = comp_bill/wage_bill (~1.4) prices raises in fully-loaded comp-$:
```
wage_bill   = Σ employed · wage ;  ℓ = Σ employed·comp_pw / wage_bill
maintenance = ℓ·wage_bill·(W_mech_old − 1)
available   = survivor_gains − maintenance
if available ≥ 0:  room = ℓ·wage_bill·(ceiling − W_mech_old); increment = min(available, room)
                   overflow = available − increment;  W_mech += increment/(ℓ·wage_bill)
else:              W_mech = 1 + survivor_gains/(ℓ·wage_bill);  increment = overflow = 0    # snap
wage_cost = ℓ·wage_bill·(W_mech_new − 1)                  # = maintenance + increment
C5c (every branch, exact):  wage_cost + overflow_to_profit + overflow_to_price == survivor_gains
market_frac = survivor_elasticity · slack_prev            # slack_prev: see Step 10; 0 at t=0
W_surv   = clip(W_mech + market_frac, 0, survivor_raise_ceiling)
```
The raise is SELF-FINANCING — taxed once, as labour income (below); there is no profit netting.
Survivor tax effect (per cell, gain = revenue up), Δw = wage·(W_surv − 1):
```
sd_fed   = Σ_filing weight·[T_fed(hh+Δw) − T_fed(hh) + FICA(wage·W_surv) − FICA(wage)] · employed
sd_state = Σ_filing weight·[T_state(hh+Δw) − T_state(hh)] · employed
```
Overflow–capital coupling  (`r_corp = Σ(auto_disp·corp_pw)/saved_bill`):
```
overflow_corp_tax     = r_corp · overflow_to_profit              # extra corp recovery
price_reduction_total = price_reduction + overflow_to_price
```

### Step 6 · Macro  (`macro.py`)
```
Y    = 1 + productivity_passthrough · (saved_bill / COMP_TOTAL)   # output-weighted dividend
P    = 1 − price_passthrough · (price_reduction_total / (VA_BASE · Y))
nGDP = VA_BASE · Y · P · (1 + baseline_growth_rate)^t             # trend growth: %-GDP denominators ONLY
```
(VA_BASE = $29.3T, COMP_TOTAL = $15.0T; nominal dollar columns never see g.)

### Step 7 · Federal ledger (losses +)  (`dynamics_v2.py`)
```
fed_cell = inc_fed + payroll_fed + transfer_fed + ui_outlay − ui_tax − corp_offset_cell − sd_fed
net_fed  = Σ fed_cell − compute_tax − overflow_corp_tax
```
Reabsorbed contribution inside `inc_*/transfer_*`:
```
rung 0:  reabsorbed · reemployment_haircut · after_delta         (tax channels only — the C8 anchor)
rung 1:  reabsorbed · reab_delta[channel]                        (all 6 channels; see Step 10)
ui_outlay = on_ui · ui_benefit · ui_share  ;  ui_share = min(1, ui_weeks/52)  ;  ui_tax = 0.10·ui_outlay
```
`retired` carry NOTHING (delta-neutral — the baseline twin retired too); `exited` carry the after-loss
plus draw SSDI (Step 8.5); `induced` carry the full after-loss.

### Step 8 · State balanced-budget close (each of 51 states)  (`government.py`)
```
state_net[s]     = Σ_{cells∈s} (inc_state + cons_state + transfer_state − sd_state)
taxable_base[s]  = Σ_{cells∈s} (employed · wage · W_surv  +  reabsorbed · w_d)   # reabsorbed pay taxes too
gap[s]           = max(0, state_net[s])
cut_share        = 0 (raise_rates) | 1 (cut_spending) | state_cut_share (mix)
rate_target      = gap·(1 − cut_share)
recovered[s]     = min(rate_target, state_rate_hike_cap · taxable_base[s])
spending_cut[s]  = gap·cut_share + (rate_target − recovered)          # infeasible hike → forced cut
contraction[s]   = spending_cut[s]·MPC_GOV + recovered[s]·mpc         # MPC_GOV = 1.0 (mode-dependent)
```

### Step 8.5 · Federal policy flows  (`dynamics_v2.py`)
```
ubi_outlay     = ubi_annual · baseline_emp                   # gross outlay
ubi_recapture  = ubi_recapture_rate · ubi_outlay             # tax clawback + means-test crowd-out
automation_tax = automation_tax_rate · saved_bill            # robot tax (payer: retained profit, Step 3-4)
ssdi_outlay    = Σ exited · ssdi_annual                      # SSDI on the LFP-exited
net_fed       += ubi_outlay − ubi_recapture − automation_tax + ssdi_outlay
debt           = debt·(1 + interest_rate) + net_fed
ubi_required_rate = ubi_annual·baseline_emp·(1−recapture) / [wage_bill·W_surv + Σ reabsorbed·w_d]
```

### Step 9 · LEVEL-TARGETING demand (the stock controller; signed; one-period lag)  (`dynamics_v2.py`)
The induced stock TRACKS a target proportional to the STANDING net withdrawal — a stationary shock gives
a stationary induced stock; injections lower the target and RELEASE workers back to employed:
```
net_pw:  exhausted/induced = wage − after_inc − emp_fica − after_transfers
         exited            = the same − ssdi_annual
         on_ui             = wage − blend(inc) − emp_fica − blend(transfers) − ui·ui_share
         reabsorbed        = the take-home scar net of the transfers replacing it ;  retired = 0
hh_withdrawal = Σ stocks·net_pw − wage_bill·(W_surv−1) − ubi_outlay·(1−recapture)     [signed]
k             = demand_multiplier·mpc·stickiness / (VA_BASE/baseline_emp)
active        = employed_post + induced        # allocation key: the demand-exposed pool. Keying on
                                               # employed alone made cells with induced stock but
                                               # zero employment lose their target → spurious full
                                               # releases → a limit cycle at near-total automation.
target_cell   = k·[ max(0, hh_withdrawal)·active_share_national                       [national]
                  + contraction[s]·employed/state_emp[s] ]                            [austerity in-state]
flow          = target_cell − induced_stock              # SIGNED; applied at the START of t+1 (Step 1-2)
```
Stability: loop gain ρ = dm·mpc·stickiness·d̄/va_pw ≈ 0.1 at shipped dm=0.5 (asserted < 1 at construction).
cons_state is excluded from net_pw (it is keyed to the same take-home drop — double-count).

### Step 10 · Period end — worker transitions  (`workers.age_and_transition`)
```
pool = exhausted + on_ui                                  # the bit-identical v1-anchor arithmetic
rate_eff    = reabsorption_rate · refuge_capacity_t       # FINITE REFUGE (rung 1; rung 0: capacity ≡ 1)
refuge_capacity_t = 1 − Σ_refuge auto_disp_t / Σ_refuge emp0   # refuge = low-exposure SOCs (the same
                                                          # occupation set the service floor prices)
reabsorbed += pool · rate_eff ;  exited += pool · lfp_exit_rate
exhausted   = pool − pool·(rate_eff + lfp_exit_rate)
induced: the SAME split in parallel (reabsorption + lfp_exit apply; demand-displaced find jobs too)
retired    += (exhausted + induced) · attrition_rate      # DELTA-NEUTRAL retirement (baseline twin too)
slack_prev  = 1 − (Σ employed + Σ reabsorbed)/(baseline − Σ retired)   # reabsorbed work; retirees left
```
**Reabsorbed destination wage** (rung 1, live engine `reabsorption.ReabsorptionEngine`):
`w_d = max(wage·(1 − reemployment_haircut), service_floor) · W_reab_t`,  `wage_removed = wage − w_d`, with
the WAGE DYNAMICS index (both levers 0 ⇒ W_reab ≡ 1, the exact legacy path reusing the bind-time delta):
```
W_reab_t = max(0.25, 1 + reab_wage_baumol·(Y_{t−1} − 1) − reab_wage_crowding·slack_{t−1})
```
Baumol pull (service work rides economy-wide productivity) vs crowding pressure (displaced supply bids
refuge wages down) — Baumol can dominate, so re-employed wages can RISE amid mass displacement. The 6-channel
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
| `robotics_lag` | `ramp_t = min(1, t/lag)` on the robot channel | physical automation waits for AI-built industrial capacity |
| `robotics_base` | ramp shape: 1 = linear (exact legacy form), b>1 = `(b^t−1)/(b^lag−1)` | exponential capacity build-out — robots build the factories that build robots |
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
| `automation_tax_rate` | `automation_tax = rate·saved_bill`; deducted in `disp_factor` | robot tax PAID from retained profit (net recovery = tax·(1−corp_rate)) |
| `reabsorption_rate` | `reabsorbed += pool·rate·refuge_capacity` | more re-employed (at `w_d`); the refuge is FINITE — capacity falls as automation reaches low-exposure work |
| `reabsorption_rung` | 0 = flat haircut / 1 = live engine | which reabsorption model |
| `reemployment_haircut` | `w_d = max(wage·(1−haircut), floor)` | reabsorbed wage cut; **0 ⇒ whole** |
| `reab_wage_baumol` | `W_reab += baumol·(Y_{t−1}−1)` | Baumol pull: re-employed wages ride productivity (deficit ↓) |
| `reab_wage_crowding` | `W_reab −= crowding·slack_{t−1}` | crowding: slack bids refuge wages down (deficit ↑) |
| `reabsorption_floor_pctile` | `service_floor` (p-th low-exposure wage) | the floor `w_d` can't drop below |
| `lfp_exit_rate` | `exited += pool·rate` | permanent LFP/SSDI exit |
| `attrition_rate` | `retired += (exhausted+induced)·rate` | DELTA-NEUTRAL retirement — the standing loss decays (deficit ↓) |
| `ssdi_annual` | `ssdi_outlay = Σ exited·ssdi` | SSDI on the LFP-exited (deficit ↑) |
| `ubi_recapture_rate` | `net UBI = outlay·(1−recapture)` | tax clawback + means-test crowd-out |
| `baseline_growth_rate` | `nGDP ×= (1+g)^t` | %-GDP denominators only (fixes r>g=0) |
| `ui_weeks` | `ui_share = min(1, weeks/52)` | UI outlay window (blend of during/after) |
| `demand_multiplier` | `induced_target = dm·mpc·stick·standing_withdrawal/va_pw` | Okun-style LEVEL multiplier: the induced stock tracks the standing shortfall (signed; releases on recovery) |
| `state_response` / `state_cut_share` | `cut_share` in the close | rate hikes vs spending cuts |
| `state_rate_hike_cap` | `recovered = min(target, cap·base)` | feasibility bound → spills to cuts → (via contraction) fed deficit |
| `interest_rate` | `debt = debt·(1+r) + net_fed` | debt compounding |
| `ubi_annual` | `ubi_outlay = ubi·baseline_emp` | federal outlay ↑ + reported required rate |
| `denominator` | headline = $B or %-GDP | reporting only |
| `mpc`, `consumption_stickiness` | **live** in Step 9 (+ frozen in cons cache) | second-round demand magnitude |
| `income_tax_mult` | scales `ch[inc_fed]`, `ch[inc_state]`, `ui_tax`, survivor inc recapture (Step 7) **+ surcharge (m−1)·[$2,403.2B fed + $536.2B state] baseline receipts (Step 8.5 / state_net)** | true flat surcharge: revenue = m·(baseline − losses); with no automation, raising it cuts the deficit. Payroll NOT covered. Static scoring: no behavioral or take-home/demand effect |
| `corp_tax_mult` | scales `corp_offset` + `overflow_corp_tax` (Steps 3–5) **+ surcharge (m−1)·[$491.7B fed + $172.0B state]** | capital-tax mult on the recapture bundle (corp+dividend+pass-through); compute/robot taxes keep their own rates |
| `cons_tax_mult` | scales `ch[cons_state]` (Step 7) **+ surcharge (m−1)·[$873.7B state + $101.6B fed excise]** | consumption-tax surcharge/cut; reaches the rung-1 reab term that `consumption_scale` cannot. State surcharges allocated per state (income: wage-bill share; corporate: employment share; consumption: taxable-PCE share) and SHRINK gaps before the close |

**Monte Carlo whitelist** (`fiscal_model/mc.py`): the local-uncertainty sampler perturbs all CONTINUOUS
levers above (constraint-aware: disposition shares renormalized on the simplex; the robot tax clipped to
retained′·(1−auto_cost′); off values never perturbed). FROZEN per draw: categorical/structural switches
(`state_response`, `reabsorption_rung`, `exposure_mapping`, `denominator`, `n_periods`,
`reabsorption_floor_pctile`, the logistic shape), fields baked into caches/templates (`consumption_scale`,
`dividend_tax_rate`, `passthrough_individual_rate`, `marginal_taxable_multiplier`), the corporate-XOR pins,
and the declared-but-inert placeholders. mpc/stickiness sensitivity reflects only their live paths.
| `surplus_capture`, `dividend_tax_rate`, `passthrough_individual_rate`, `marginal_taxable_multiplier` | frozen in the delta cache | build-time only — inert on a fixed cache |

**Global LHS screening** (`mc.lhs_draws` + `mc.GLOBAL_RANGES`; runner `scripts/global_screening.py`):
the whole-space complement to the local sampler — a Latin hypercube over 26 dimensions at their full UI
ranges, each tagged `uncertainty` | `policy` and analyzed on separate tornado panels (Spearman ρ +
debiased binned η²; disagreement flags non-monotone/conditionally-activated levers). The disposition
simplex is drawn exactly uniform via stick-breaking (retained = 1−√(1−u), the Beta(1,2) marginal); the
robot tax is sampled as a FRACTION of the bound retained·(1−auto_cost) so its rank is independent of
retained's. Every point passes `assert_all_invariants`; a dedicated 20-year batch in the
high-adoption/hot-demand/low-reabsorption corner regression-guards the demand-controller allocation fix
(flag: ≥2 above-threshold employment-diff sign alternations). Interpretation discipline: the local MC
bands measure robustness to lever mis-calibration WITHIN a scenario; the cross-preset spread plus this
screening carry the model's uncertainty story (report §7.9).

**Scenario presets & policy overlays** (`fiscal_model/presets.py`): seven literature-anchored world
states (Acemoglu-modest → AI-2027 takeoff) load full lever configurations into the sidebar; four
policy overlays (Costinot-Werning / GRT robot taxes, UBI + recapture, compute-pool parity) compose on
top and OVERRIDE the corresponding levers. Presets ship with `automation_tax_rate = 0` — taxation is
an overlay, so scenario (what the world does) and policy (what government recovers) stay separable.
Robot-tax overlays convert ad-valorem-on-robot-spending rates to our saved-bill base by × `auto_cost`.
Values, anchors, and validation targets: `docs/PRESET_EVIDENCE.md`; every preset passes the full
conservation battery (`tests/test_presets.py`). CLI: `scripts/monte_carlo.py --preset ai-2027
--overlay cw-robot-tax`.

---

## Conservation identities (the invariants these equations satisfy)

`C1` seven worker states sum to baseline per cell · `C2/C5b` disposition partition + meter · `C3` compute
pool flow · `C4` real = nominal/P · `C5c` funded-W* partition (`wage_cost + overflows == survivor_gains`,
every branch) · `C6` federal reconciliation (`net_fed = Σ` labelled components incl.
`+ubi_outlay − ubi_recapture − automation_tax + ssdi_outlay`) · `C6-state`
per-state composition · `C7` state gap closes · `C8` v2 == v1 at `DEFAULTS_V1REDUCTION`. See
`tests/test_v2_phase*.py` and `tests/test_overhaul.py`.
