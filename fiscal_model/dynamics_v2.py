"""V2 orchestrator — Phases 0-5.

`DynamicModelV2` runs the multi-actor model through the new structure: the explicit 6-state worker
machine (`workers.py`), the sector disposition router + compute pool (`firms/disposition.py`,
`compute_pool.py`), the macro environment (`macro.py`: P, Y), the survivor wage channel
(`survivor.py`, decision A), reabsorption Rung 1 (`reabsorption.py`, decision D), and the government
closure + absolute ledger (`government.py`: the per-state balanced-budget close H/C7, and the lagged
demand contraction I that lands as a 6th-state `induced` employment flow). At a v1-reduction config
(`levers_v2.DEFAULTS_V1REDUCTION`) every new behavioral lever is off, so the fiscal math is bit-for-bit
v1 — the C8 anchor every later phase is gated against.

Phase 1 wired the worker transitions + `lfp_exit`; Phase 2 the disposition router — the **sole** V2
corporate path (the corporate XOR: v1's `surplus_capture` / `corp_offset_scale` are superseded and
asserted inert in `__init__`) — plus the compute pool; Phase 3 the macro state, where P (price level)
and Y (productivity/GDP) drive the real / %-GDP reporting and, per the A2 rule, P *only* deflates nominal
aggregates (it never enters the transfer interpolation). Phase 4 turns the `survivor_gains` share into a
real labour-tax effect (`survivor.py`): the still-employed stock's wage scales by W = mechanical (the
router's survivor_gains, conserved → C5c) + market (elasticity × t−1 slack, unconserved → J.1), and the
exact income+payroll re-eval lands on the federal/state ledgers. Reabsorption Rung 1 re-employs the
reabsorbed stock at a service-floor wage, tripping the means-tested channel Rung 0 misses.

It reuses the v1 `DynamicModel`'s prepared arrays (g_cell, channel deltas, corp offset, ui, …) so the
inputs are *identical* to v1; the loop **inlines** calls to the actor modules (`workers`,
`firms.disposition.route`, `compute_pool`, `macro`) — there are no `_diffusion`/`_transitions`/… seam
methods. It carries the 5-state population (C1) and the t=0 base-rate gate via `baseline_rates()`.

NOTE: there is not yet an absolute revenue *ledger* the deltas net against — every reported fiscal column
is a delta, and %-GDP rides a consistent synthetic baseline (`macro.VA_BASELINE · Y · P`). The absolute
base-linkage ledger is Phase-5 work (the tax-regime solver needs it).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import loaders, workers, compute_pool, macro, survivor, reabsorption, government
from .dynamics import DynamicModel
from .firms import disposition
from .levers_v2 import V2Params


class DynamicModelV2:
    def __init__(self, data: loaders.FiscalData, deltas: pd.DataFrame, params: V2Params):
        self.data = data
        self.v2p = params
        # Corporate XOR (note C): the disposition router is the SOLE V2 corporate path. v1's
        # corp_offset_scale would double-apply with the router's disp_factor, and surplus_capture is
        # inert (frozen in the delta cache). Both must stay at their defaults — fail loud otherwise.
        assert params.corp_offset_scale == 1.0, \
            "corp_offset_scale is superseded by the disposition router (corporate XOR) — keep it 1.0"
        assert params.surplus_capture == 1.0, \
            "surplus_capture is inert in V2 (frozen in the delta cache); the router controls corporate"
        # Input-domain guards (fail loud — an off-sum or out-of-range lever silently breaks conservation:
        # off-sum disposition shares break C2/C5b; auto_cost>1 drives net_saving<0 past the C-gate;
        # offshore>1 makes compute tax negative; price_passthrough>1 can push the price level negative).
        assert abs(disposition.shares_sum(params) - 1.0) < 1e-9, \
            "disposition shares (retained/price/survivor) must sum to 1"
        for _n, _v in (("retained_profit_share", params.retained_profit_share),
                       ("price_reduction_share", params.price_reduction_share),
                       ("survivor_gains_share", params.survivor_gains_share),
                       ("auto_cost", params.auto_cost), ("offshore_share", params.offshore_share),
                       ("price_passthrough", params.price_passthrough)):
            assert 0.0 <= _v <= 1.0, f"{_n}={_v} is out of its documented [0, 1] domain"
        lp, dp = params.to_v1()
        # Reuse v1's array preparation verbatim -> identical inputs guarantee the C8 anchor.
        self._v1 = DynamicModel(data, deltas, lp, dp)
        self._baseline = self._baseline_rates(data)
        # per-cell fully-loaded compensation per worker (the disposition saved-bill basis)
        ms = data.matrices_sector.groupby("soc_code").agg(
            comp=("comp_musd", "sum"), emp=("emp_thousands", "sum"))
        ms["comp_pw"] = np.where(ms["emp"] > 0, ms["comp"] / ms["emp"] * 1000.0, 0.0)
        self._comp_pw = self._v1.d["soc_code"].map(ms["comp_pw"]).fillna(0.0).to_numpy()

        # Phase 4: the survivor channel (decision A) — exact income+payroll re-eval of the still-employed
        # at a scaled wage. Shares the delta cache's wage basis (the C5c leak detector relies on it).
        self._survivor = survivor.SurvivorEngine(data, deltas)
        # Phase 4: reabsorption Rung 1 (decision D). Built/loaded only when live (rung 1) — the per-cell
        # service-floor delta is scenario-invariant and disk-cached; rung 0 pays nothing (keeps C8 fast).
        self._reab1 = None
        if params.reabsorption_rung == 1:
            from .transfers import TransferLookup
            r1 = reabsorption.load_or_build_rung1_deltas(
                data, TransferLookup(), params.kernel_params(), params.reabsorption_floor_pctile)
            r1 = self._v1.d[["soc_code", "state"]].merge(r1, on=["soc_code", "state"], how="left")
            self._reab1 = {c: r1[c].fillna(0.0).to_numpy() for c in reabsorption.REAB_CHANNELS}
        elif params.reabsorption_rung not in (0,):
            raise NotImplementedError("reabsorption Rung 2 (cross-cell routing) is post-Phase-4")

        # Phase 5: the absolute revenue ledger (deltas net against the real base-linkage absolutes).
        self._ledger = government.RevenueLedger(data)
        # Disposable income lost per displaced worker — the lagged-demand impulse base (decision I). Same
        # take-home basis the kernel's consumption channel uses (wage − income tax − employee FICA − UI),
        # NOT gross wage (which would overstate the withdrawn demand by the tax+FICA the worker stops paying).
        v1 = self._v1
        inc_tax_pw = v1.arr["after"]["inc_fed"] + v1.arr["after"]["inc_state"]
        emp_fica_pw = sum(self._survivor.weight[f]
                          * np.asarray(self._survivor.fica.employee_fica(v1.wage, f), float)
                          for f in ("Married filing jointly", "Head of household", "Single"))
        self._disposable_pw = np.maximum(v1.wage - inc_tax_pw - emp_fica_pw - v1.ui, 0.0)
        # Value-added per worker — the divisor turning a $ demand shortfall into a job count (decision I).
        # A direct-requirements (Type-I) divisor: it OMITS the Type-II output/employment multiplier (~1.5–2×),
        # so it under-counts induced jobs; `demand_multiplier` absorbs that calibration.
        self._va_per_worker = macro.VA_BASELINE_USD / baseline_emp if (baseline_emp := v1.emp0.sum()) else 0.0

    # ---- t=0 base-rate gate (J.2): the published base-linkage effective rates. (The absolute
    #      revenue ledger the deltas net against is Phase-5 work for the tax-regime solver.) ----
    @staticmethod
    def _baseline_rates(data: loaders.FiscalData) -> dict:
        bl = data.base_linkage
        def rate(*keys):
            for k in keys:
                m = bl[bl["tax_stream"].str.contains(k, case=False, na=False)]
                if len(m):
                    return float(m["avg_effective_rate"].iloc[0])
            return float("nan")
        return {"income": rate("individual income", "income"),
                "payroll": rate("payroll", "social insurance"),
                "corporate": rate("corporate", "corp")}

    def baseline_rates(self) -> dict:
        return dict(self._baseline)

    # ---- the period loop (Phase 0: faithful v1 reproduction with 5-state tracking) ----
    def run(self) -> pd.DataFrame:
        v1, v2p = self._v1, self.v2p
        p = v1.p
        st = workers.WorkerStocks.initial(v1.emp0)        # 5-state machine (Phase 1)
        reab_factor = workers.reabsorbed_loss_factor(v2p) if v2p.reabsorption_rung == 0 else None
        debt = 0.0
        baseline_emp = v1.emp0.sum()
        baseline_rev = None
        slack_prev = 0.0                                  # t−1 labour-market slack (J.1); 0 at t=0
        W_mech = 1.0                                      # accumulated survivor mechanical wage multiplier
        induced_pending = np.zeros(len(v1.wage))          # decision I: induced layoffs for NEXT period; 0 at t=0
        out = []

        for t in range(p.n_periods):
            # --- steps 1-2: diffusion + displacement ---
            adopt = v1._adoption(t)
            frac = np.clip(v1.g_cell * adopt, 0.0, 1.0)
            new = st.displace(frac)
            # decision I: last period's demand contraction lands NOW as a C1-guarded employment movement
            # (employed→induced), priced as a job loss but NOT as automation (separate bucket). 0 at t=0.
            induced_applied = st.displace_extra(induced_pending)

            # post-transition survivor stock (decision A/G): excludes on_ui/exhausted/reabsorbed/exited,
            # so this period's newly-displaced are priced ONLY as displaced, never also as survivors.
            employed_post = st.employed
            wage_bill = (employed_post * v1.wage).sum()

            # --- step 7: fiscal flows. on_ui -> UI blend; exhausted+exited -> 'after'. Reabsorbed:
            #     Rung 0 -> flat-haircut residual on tax channels only (v1 anchor); Rung 1 -> the full
            #     per-cell service-floor delta over ALL channels incl. transfers (the cross-threshold fire). ---
            out_after = st.exhausted + st.exited + st.induced   # induced carry the full 'after' loss (I)
            ch = {}
            for c in v1.arr["during"]:
                blend = v1.ui_share * v1.arr["during"][c] + (1 - v1.ui_share) * v1.arr["after"][c]
                cc = st.on_ui * blend + out_after * v1.arr["after"][c]
                if v2p.reabsorption_rung == 0:
                    if c in ("inc_fed", "inc_state", "payroll_fed", "cons_state"):
                        cc = cc + st.reabsorbed * reab_factor * v1.arr["after"][c]
                else:                                          # Rung 1: full re-eval at w_d, all channels
                    cc = cc + st.reabsorbed * self._reab1[c]
                ch[c] = cc

            ui_outlay_fed = st.on_ui * v1.ui * v1.ui_share
            ui_tax_fed = 0.10 * ui_outlay_fed

            # --- steps 3-4: disposition router. The automated stock's saved comp routes to
            #     {retained profit -> corporate tax (per cell), automation spend -> compute pool,
            #     price reduction -> Phase 3, survivor gains -> Phase 4}. corp offset on the
            #     not-reabsorbed displaced; == v1's (new+U)×corp at the reduction config. ---
            automated = st.on_ui + st.exhausted + st.exited
            disp = disposition.route(automated, self._comp_pw, v1.corp, v2p)
            cp = compute_pool.route_to_compute_pool(disp.automation_spend, v2p)

            # --- step 5: survivor wage index — capacity-checked mechanical raise + market level. ---
            #   Mechanical: the router's survivor_gains is what firms WANT to pay survivors this period.
            #   A per-period FLOW check caps how much the surviving wage bill can absorb under the ceiling
            #   (room = wage_bill·(ceiling − W_mech)); the un-absorbable overflow spills by the spillover
            #   lever into retained profit (taxed at the corp recovery rate) and price reduction (ΔP).
            #   C5c conserves THIS PERIOD'S ROUTING only:
            #       actual_inflow + overflow_to_profit + overflow_to_price == survivor_gains   (exact).
            #   W_mech is a PERSISTENT (sticky) wage level: it accumulates the absorbed inflows and never
            #   exceeds the ceiling. The survivor TAX BASE is wage_bill·(W_mech−1) — the STANDING raise on
            #   the current survivors — deliberately NOT equal to the cumulative routed inflow once the cap
            #   binds (the raise persists even in periods where actual_inflow==0; see test_sticky_rate_*).
            #   The standing raise IS netted against the corporate profit base below (survivor_profit_netting,
            #   Phase 5) — so it is no longer taxed as BOTH wages and profit (the Phase-4 double-count is gone).
            #   Market (unconserved, C5-market-exempt): elasticity × t−1 slack (J.1, 0 at t=0); the part
            #   that would push total W above the ceiling is simply TRUNCATED (no capital counterparty).
            ceiling = v2p.survivor_raise_ceiling
            desired = disp.survivor_gains
            W_mech_old = W_mech                            # the standing raise carried IN (for the netting)
            if wage_bill <= 0:
                actual_inflow = 0.0
            elif not np.isfinite(ceiling):
                actual_inflow = desired                                  # unbounded lever
            else:
                room = max(0.0, wage_bill * (ceiling - W_mech))
                actual_inflow = min(desired, room)
            overflow = desired - actual_inflow
            overflow_to_profit = overflow * v2p.survivor_spillover_to_profit
            overflow_to_price = overflow - overflow_to_profit
            if wage_bill > 0:
                W_mech = W_mech + actual_inflow / wage_bill              # ≤ ceiling by construction
            market_frac = v2p.survivor_elasticity * slack_prev
            W_surv = W_mech + market_frac
            if np.isfinite(ceiling):
                W_surv = min(W_surv, ceiling)                            # market truncated at the cap
            W_surv = max(W_surv, 0.0)
            sd = self._survivor.delta(W_surv)
            sd_fed = (sd["inc_fed"] + sd["payroll"]) * employed_post      # per-cell GAIN (revenue +)
            sd_state = sd["inc_state"] * employed_post
            survivor_mech_inflow = actual_inflow

            # the profit overflow is recovered as corporate tax at the same per-profit-$ rate the router
            # uses (Σ automated·corp_pw / saved_bill — linear in the surplus base, note C); the price
            # overflow joins the disposition's price reduction in deflating P. Both vanish at reduction.
            corp_full = float((automated * v1.corp).sum())
            corp_rate_per_profit = (corp_full / disp.saved_bill) if disp.saved_bill > 0 else 0.0
            overflow_corp_tax = corp_rate_per_profit * overflow_to_profit
            price_reduction_total = disp.price_reduction + overflow_to_price

            # Phase 5 survivor NETTING (resolves the Phase-4 double-count): the PRE-existing standing raise
            # wage_bill·(W_mech_old−1) is a firm cost funded from PROFIT — this period's increment came from
            # survivor_gains (disjoint from retained_profit; the market component is unfunded/exempt) — so it
            # REDUCES the taxable corporate base. Netted at the SAME corp rate as overflow_corp_tax (one
            # basis); ADDED to net_fed (less recovery → higher deficit). 0 at reduction (W_mech_old=1). The
            # net survivor effect is now labor_tax(raise) − capital_tax(raise), not a double count.
            survivor_profit_netting = corp_rate_per_profit * wage_bill * (W_mech_old - 1.0)

            # --- step 6: macro update. P deflates reporting only (A2: never the nominal fiscal);
            #     Y is the real-GDP/productivity index for the denominator. ---
            automated_fraction = automated.sum() / baseline_emp
            Y = macro.productivity_index(automated_fraction, v2p)
            P = macro.price_level(price_reduction_total, Y, v2p)
            ngdp = macro.nominal_gdp(Y, P)

            # federal: losses positive; the survivor GAIN and the profit-overflow recovery are subtracted
            # (W<1 → sd<0 → adds to deficit); the survivor netting is ADDED (less corp recovery).
            fed = (ch["inc_fed"] + ch["payroll_fed"] + ch["transfer_fed"]
                   + ui_outlay_fed - ui_tax_fed - disp.corporate_offset_cell - sd_fed)
            net_fed = fed.sum() - cp.tax_fed - overflow_corp_tax + survivor_profit_netting

            # --- step 8: state balanced-budget close (H, C6-state, C7). Compose per-state net loss, then
            #     close it within-year by rate hikes (capped) and/or spending cuts. The reported gap stays
            #     the PRE-close austerity magnitude (= v1 → C8-safe); the close's only feedback is the
            #     contraction, which feeds lagged demand (I) and is gated by demand_multiplier. ---
            state_cell = ch["inc_state"] + ch["cons_state"] + ch["transfer_state"] - sd_state
            state_net = np.bincount(v1.state_of_cell, weights=state_cell, minlength=len(v1.uniq_states))
            taxable_base = np.bincount(v1.state_of_cell, weights=employed_post * v1.wage * W_surv,
                                       minlength=len(v1.uniq_states))   # remaining labour income (W-scaled)
            close = government.close_state_gaps(state_net, taxable_base, v2p)
            state_gap_total = close.gap.sum()                           # pre-close magnitude (= v1)

            debt = debt * (1 + p.interest_rate) + net_fed

            base = wage_bill
            ubi_rate = (p.ubi_annual * baseline_emp / base) if (p.ubi_annual > 0 and base > 0) else 0.0

            # --- step 9: second-round demand (I). Income withdrawn this period = the state austerity (the
            #     close removes income/services ≈ the gap) + the disposable income lost by everyone newly
            #     out of work this period (tech + induced). Stored, it re-enters at t+1 as an employment
            #     movement (NOT a fiscal subtraction). value-added/worker turns the $ shortfall into jobs. ---
            fresh_disposable_loss = float(((new + induced_applied) * self._disposable_pw).sum())
            income_withdrawn = close.contraction + fresh_disposable_loss
            induced_dollars = p.demand_multiplier * p.kernel_params.mpc \
                * p.kernel_params.consumption_stickiness * income_withdrawn
            induced_jobs = induced_dollars / self._va_per_worker if self._va_per_worker > 0 else 0.0
            emp_share = employed_post / employed_post.sum() if employed_post.sum() > 0 else 0.0
            induced_pending = induced_jobs * emp_share                  # consumed at the START of t+1

            rev_lost = ch["inc_fed"].sum() + ch["inc_state"].sum() + ch["payroll_fed"].sum()
            if baseline_rev is None:
                baseline_rev = (v1.emp0 * (v1.arr["after"]["inc_fed"] + v1.arr["after"]["inc_state"]
                                           + v1.arr["after"]["payroll_fed"])).sum()

            # absolute ledger (Phase 5): federal revenue-side delta ($B, negative = revenue lost) +
            # post-close state figures, netted against the real base-linkage absolutes.
            fed_rev_delta_B = (-(ch["inc_fed"].sum() + ch["payroll_fed"].sum()) + ui_tax_fed.sum()
                               + disp.corporate_offset_cell.sum() + cp.tax_fed + sd_fed.sum()
                               + overflow_corp_tax - survivor_profit_netting) / 1e9
            led_fed = self._ledger.federal(net_fed / 1e9, fed_rev_delta_B, ngdp)
            led_state = self._ledger.state(state_gap_total / 1e9, close.recovered.sum() / 1e9)

            out.append({
                "period": t, "adoption": adopt,
                "employed_M": st.employed.sum() / 1e6,
                "on_ui_M": st.on_ui.sum() / 1e6, "exhausted_M": st.exhausted.sum() / 1e6,
                "reabsorbed_M": st.reabsorbed.sum() / 1e6, "exited_M": st.exited.sum() / 1e6,
                "induced_M": st.induced.sum() / 1e6,                    # 6th state: demand-driven layoffs (I)
                "population_M": st.total().sum() / 1e6,
                # C1 PER-CELL: the worst per-cell mass residual (the aggregate population_M can hide a
                # per-cell leak that nets to zero across the 33k cells).
                "max_cell_resid_M": float(np.abs(st.total() - v1.emp0).max()) / 1e6,
                "employment_drop_pct": 100 * (1 - st.employed.sum() / baseline_emp),
                "revenue_lost_B": rev_lost / 1e9,
                "revenue_lost_pct": 100 * rev_lost / baseline_rev if baseline_rev else 0.0,
                "transfers_added_B": (ch["transfer_fed"].sum() + ch["transfer_state"].sum()
                                      + ui_outlay_fed.sum()) / 1e9,
                "corp_offset_B": disp.corporate_offset_cell.sum() / 1e9,
                "compute_pool_tax_B": cp.tax_fed / 1e9,
                "saved_bill_B": disp.saved_bill / 1e9,
                "automation_spend_B": disp.automation_spend / 1e9,
                "net_saving_B": disp.net_saving / 1e9,
                "retained_profit_B": disp.retained_profit / 1e9,
                "price_reduction_B": disp.price_reduction / 1e9,
                "survivor_gains_B": disp.survivor_gains / 1e9,
                "offshore_leak_B": cp.offshore_leak / 1e9,
                "fed_deficit_B": net_fed / 1e9, "fed_debt_B": debt / 1e9,
                # macro (Phase 3): nominal is P-invariant; real = nominal/P; %-GDP = nominal/nominal-GDP
                "price_level": P, "productivity_index": Y,
                "fed_deficit_real_B": net_fed / P / 1e9, "fed_debt_real_B": debt / P / 1e9,
                "fed_deficit_pct_gdp": 100 * net_fed / ngdp, "fed_debt_pct_gdp": 100 * debt / ngdp,
                "state_gap_pct_gdp": 100 * state_gap_total / ngdp,
                # denominator toggle — value is $B when 'absolute', else % of GDP
                "headline_deficit": (net_fed / 1e9 if v2p.denominator == "absolute"
                                     else 100 * net_fed / ngdp),
                # survivor channel (Phase 4): gains positive = revenue up; W + overflow for the gates.
                "survivor_gain_fed_B": sd_fed.sum() / 1e9,
                "survivor_gain_state_B": sd_state.sum() / 1e9,
                "survivor_mech_inflow_B": survivor_mech_inflow / 1e9,   # wage actually absorbed (C5c leg)
                "survivor_overflow_profit_B": overflow_to_profit / 1e9,
                "survivor_overflow_price_B": overflow_to_price / 1e9,   # C5c: inflow+profit+price==gains
                "survivor_overflow_corp_tax_B": overflow_corp_tax / 1e9,
                "survivor_market_frac": market_frac, "survivor_slack_prev": slack_prev,
                "W_survivor": W_surv, "W_survivor_mech": W_mech,
                # C6 federal reconciliation components (net_fed = Σ these; see test_c6)
                "inc_fed_loss_B": ch["inc_fed"].sum() / 1e9,
                "payroll_fed_loss_B": ch["payroll_fed"].sum() / 1e9,
                "transfer_fed_B": ch["transfer_fed"].sum() / 1e9,
                "ui_outlay_fed_B": ui_outlay_fed.sum() / 1e9, "ui_tax_fed_B": ui_tax_fed.sum() / 1e9,
                "survivor_netting_B": survivor_profit_netting / 1e9,    # C6 component (raises the deficit)
                # --- Phase 5: state balanced-budget close (H, C7) ---
                # C6-state composition: the signed state total reconstructs from its labeled components
                # (inc + cons + transfer − survivor gain), pinning sd_state's sign and the bincount.
                "state_net_total_B": state_net.sum() / 1e9,
                "inc_state_loss_B": ch["inc_state"].sum() / 1e9,
                "cons_state_loss_B": ch["cons_state"].sum() / 1e9,
                "transfer_state_B": ch["transfer_state"].sum() / 1e9,
                "state_gap_B": state_gap_total / 1e9, "ubi_required_rate": ubi_rate,
                "state_rate_hike_B": close.recovered.sum() / 1e9,
                "state_spending_cut_B": close.spending_cut.sum() / 1e9,
                "state_close_residual_B": close.residual.sum() / 1e9,
                "n_states_capped": int(close.capped.sum()),
                "state_balanced": bool(np.all(close.residual <= 1e-6 * np.maximum(close.gap, 1.0))),
                # --- Phase 5: lagged demand (I) — induced jobs QUEUED for next period ---
                "induced_pending_M": induced_pending.sum() / 1e6,
                "income_withdrawn_B": income_withdrawn / 1e9,
                # --- Phase 5: absolute revenue ledger ---
                "fed_revenue_B": led_fed["fed_revenue_B"],
                "fed_deficit_abs_B": led_fed["fed_deficit_abs_B"],
                "fed_deficit_abs_pct_gdp": led_fed["fed_deficit_abs_pct_gdp"],
                "state_fiscal_position_B": led_state["state_fiscal_position_B"],
            })

            # carry this period's cumulative slack to t+1 (decision J.1 keeps ΔW_market predetermined).
            slack_prev = 1.0 - employed_post.sum() / baseline_emp
            # --- period end: age on-UI into exhausted, then split {exited, reabsorbed, stay} ---
            st.age_and_transition(p.reabsorption_rate, v2p.lfp_exit_rate)

        return pd.DataFrame(out)


if __name__ == "__main__":
    from .dynamics import precompute_worker_deltas
    from .transfers import TransferLookup
    from . import levers_v2
    data = loaders.load_all()
    deltas = precompute_worker_deltas(data, TransferLookup(), V2Params().kernel_params())
    m = DynamicModelV2(data, deltas, levers_v2.DEFAULTS_V1REDUCTION)
    print("baseline rates (t=0 gate):", {k: round(v, 4) for k, v in m.baseline_rates().items()})
    res = m.run()
    print(res[["period", "employed_M", "on_ui_M", "exhausted_M", "population_M",
               "fed_deficit_B", "state_gap_B"]].head().to_string(index=False))
