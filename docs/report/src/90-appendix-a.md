{{pagebreak}}

# Appendix A — Equation reference

The complete reference, including the per-lever effect table and the Monte Carlo whitelist, lives
in the repository (`docs/EQUATIONS.md`); this appendix carries the load-bearing core in execution
order. Notation: per-cell quantities are (occupation × state) vectors; `Σ` sums over cells unless
subscripted.

## A.1 Displacement (per period t)

```
g_cell(t) = 1 − (1 − cog_exposure · cognitive_feasibility)
              · (1 − robot_exposure · physical_feasibility · min(1, t / robotics_lag))
target(t) = clip(g_cell(t) · adoption(t), 0, 1) · emp0        # cumulative ceiling vs baseline
flow(t)   = clip(target(t) − auto_disp, 0, employed)          # never un-automates, never overdraws
auto_disp += flow(t)                                          # the firm side keys off this stock
```

## A.2 Worker transitions

```
employed → on_ui → exhausted → { reabsorbed   at reabsorption_rate
                                 exited(SSDI) at lfp_exit_rate
                                 retired      at attrition_rate }     (induced joins the pool)
w_d = max(origin_wage · (1 − haircut), service_floor)          # re-employment wage, permanent scar
C1:  employed + on_ui + exhausted + reabsorbed + exited + induced + retired = emp0   (per cell)
```

## A.3 Disposition of the saved bill

```
saved_bill       = Σ_auto_disp comp_per_worker
automation_spend = auto_cost · saved_bill                      → compute pool
net_saving       = saved_bill − automation_spend               (≥ 0, C-gate)
net_saving       = retained_profit + price_reduction + survivor_gains        (simplex, C2)
corp_offset      = auto_disp · corp_per_worker · [retained_share·(1−auto_cost) − robot_tax_rate]
compute_pool_tax = compute_effective_rate · (1 − offshore_share) · automation_spend
automation_tax   = automation_tax_rate · saved_bill            # paid from retained profit
```

## A.4 Survivor wages (funded W*)

```
ℓ           = Σ emp_post · comp_pw / Σ emp_post · wage         # compensation loading ≈ 1.4
maintenance = ℓ · wage_bill · (W_mech − 1)
available   = survivor_gains − maintenance
if available ≥ 0:  room = ℓ·wage_bill·(ceiling − W_mech)
                   W_mech += min(available, room)/(ℓ·wage_bill);  overflow = available − room⁺
else:              W_mech = 1 + max(0, survivor_gains)/(ℓ·wage_bill)          # snap
C5c: ℓ·wage_bill·(W_mech_new − 1) + overflow_to_profit + overflow_to_price = survivor_gains
W = W_mech + elasticity · slack(t−1) · market_frac             # market component, lagged slack
```

## A.5 Macro

```
Y(t) = 1 + productivity_passthrough · saved_bill / COMP_TOTAL   # output-weighted dividend
P(t) = P(t−1) · (1 − price_passthrough · price_reduction_flow / consumption_base)
real X = nominal X / P(t)                                       # reporting only (A2 rule); C4
```

## A.6 Government

```
fed_deficit = inc_fed_loss + payroll_loss + transfer_fed + ui_outlay − ui_tax − corp_offset
            − survivor_gain_fed − compute_pool_tax − overflow_corp_tax + ubi_outlay
            − ubi_recapture − automation_tax + ssdi_outlay                          (C6, asserted)
fed_debt(t) = fed_debt(t−1) · (1 + r) + fed_deficit(t)
state gap_s = losses_s − recoveries_s ;  closed by Δrate ≤ cap · base_s, remainder forced cuts
contraction_s = cuts_s · MPC_gov + hikes_s · MPC_hh                                  (C7 ≈ 0)
```

## A.7 Demand (level-targeting controller)

```
withdrawal = Σ_stocks stock · net_income_pw − wage_bill·(W−1) − ubi_net       # standing LEVEL
target_induced = k · [max(0, withdrawal) · emp_share + contraction_s · state_share]
k = demand_multiplier · mpc · stickiness / va_per_worker
induced(t+1) → target_induced                                  # signed flow; releases on recovery
loop gain ρ = k · d̄ ≈ 0.22 · demand_multiplier < 1            # asserted at construction
```
