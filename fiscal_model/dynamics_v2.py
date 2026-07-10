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

from . import loaders, workers, compute_pool, macro, survivor, reabsorption, government, levers
from .dynamics import DynamicModel
from .firms import disposition
from .levers_v2 import V2Params


class DynamicModelV2:
    def __init__(self, data: loaders.FiscalData, deltas: pd.DataFrame, params: V2Params):
        # Two-stage construction (the Monte Carlo fast path): `_build_shared` holds everything
        # lever-free or STRUCTURAL (heavy — engines, cell maps, ledger); `_bind_params` recomputes the
        # cheap lever-dependent members. `mc.ScenarioContext` shallow-copies a built template and calls
        # `_bind_params(draw)` per draw — bit-identical to fresh construction because the per-draw
        # formulas live only here.
        self._build_shared(data, deltas, params)
        self._bind_params(params)

    # ---- stage 1: lever-free / structural construction (built once per session for MC) --------------
    def _build_shared(self, data: loaders.FiscalData, deltas: pd.DataFrame, params: V2Params) -> None:
        self.data = data
        lp, dp = params.to_v1()
        # Reuse v1's array preparation verbatim -> identical inputs guarantee the C8 anchor. (v1's
        # lever-dependent members — p, lp, ui_share, g_cell — are overwritten by _bind_params.)
        self._v1 = DynamicModel(data, deltas, lp, dp)
        self._baseline = self._baseline_rates(data)
        # per-cell fully-loaded compensation per worker (the disposition saved-bill basis)
        ms = data.matrices_sector.groupby("soc_code").agg(
            comp=("comp_musd", "sum"), emp=("emp_thousands", "sum"))
        ms["comp_pw"] = np.where(ms["emp"] > 0, ms["comp"] / ms["emp"] * 1000.0, 0.0)
        self._comp_pw = self._v1.d["soc_code"].map(ms["comp_pw"]).fillna(0.0).to_numpy()

        # The two exposure channels mapped to cells — FEASIBILITY-FREE (they depend only on the fixed
        # mapping fields), so a draw's g_cell is one combine_channels call in _bind_params.
        _cog_s, _rob_s = levers.channel_shares(data.exposure_occ, params.lever_params())
        self._cog_cell = self._v1.d["soc_code"].map(_cog_s).fillna(0.0).to_numpy()
        self._rob_cell = self._v1.d["soc_code"].map(_rob_s).fillna(0.0).to_numpy()

        # Phase 4: the survivor channel (decision A) — exact income+payroll re-eval of the still-employed
        # at a scaled wage. Construction is lever-free (data + deltas only).
        self._survivor = survivor.SurvivorEngine(data, deltas)
        # Reabsorption: rung 0 = legacy flat haircut (the C8 anchor); rung 1 = the unified LIVE engine.
        # The ENGINE is retained (structural: kernel params + floor pctile); the haircut-dependent
        # 6-channel delta is computed per bind via engine.delta(...).
        self._reab_eng = None
        if params.reabsorption_rung == 1:
            from .transfers import TransferLookup
            self._reab_eng = reabsorption.ReabsorptionEngine(
                data, deltas, TransferLookup(), params.kernel_params(), params.reabsorption_floor_pctile)
        elif params.reabsorption_rung != 0:
            raise NotImplementedError("reabsorption Rung 2 (cross-cell routing) is post-Phase-4")

        # Phase 5: the absolute revenue ledger (deltas net against the real base-linkage absolutes).
        self._ledger = government.RevenueLedger(data)
        # tax-regime surcharge bases (lever-free): the 2024 receipts per line, and per-state
        # allocation shares for the state-side surcharges. Anchored on maps_to_base (NOT the
        # receipt_source label — 'income' collides with the corporate-income row) and assert-pinned
        # so a receipts-file edit fails loud.
        _r = data.receipts

        def _base(level, maps):
            return float(_r.loc[(_r["level"] == level)
                                & _r["maps_to_base"].str.contains(maps, na=False),
                                "amount_busd"].sum()) * 1e9
        self._fed_inc_base = _base("Federal", "Labor")
        self._fed_corp_base = _base("Federal", "Corporate profits")
        self._fed_cons_base = _base("Federal", "Consumption")
        self._st_inc_base = _base("State & local", "Labor")
        self._st_corp_base = _base("State & local", "Corporate profits")
        self._st_cons_base = _base("State & local", "Consumption")
        for _v, _exp in ((self._fed_inc_base, 2403.2e9), (self._fed_corp_base, 491.7e9),
                         (self._fed_cons_base, 101.6e9), (self._st_inc_base, 536.2e9),
                         (self._st_corp_base, 172.0e9), (self._st_cons_base, 873.7e9)):
            assert abs(_v - _exp) < 1e6, f"receipts surcharge base drifted: {_v} != {_exp}"
        _v1 = self._v1
        _n_st = len(_v1.uniq_states)
        _wb = np.bincount(_v1.state_of_cell, weights=_v1.emp0 * _v1.wage, minlength=_n_st)
        self._surch_inc_share = _wb / _wb.sum()                      # income: by baseline wage bill
        _eb = np.bincount(_v1.state_of_cell, weights=_v1.emp0, minlength=_n_st)
        self._surch_corp_share = _eb / _eb.sum()                     # corporate: by employment (crude)
        _cb = (data.consumption.set_index("state").reindex(_v1.uniq_states)
               ["total_taxable_pce_musd"].to_numpy())
        assert not np.isnan(_cb).any(), "consumption base missing a state"
        self._surch_cons_share = _cb / _cb.sum()                     # consumption: by taxable PCE
        # Hoisted lever-free pieces of the demand-withdrawal basis (per-cell arrays; see _bind_params).
        v1 = self._v1
        self._inc_after_pw = v1.arr["after"]["inc_fed"] + v1.arr["after"]["inc_state"]
        self._tr_after_pw = v1.arr["after"]["transfer_fed"] + v1.arr["after"]["transfer_state"]
        self._emp_fica_pw = sum(self._survivor.weight[f]
                                * np.asarray(self._survivor.fica.employee_fica(v1.wage, f), float)
                                for f in ("Married filing jointly", "Head of household", "Single"))
        # Value-added per worker — the divisor turning a $ demand shortfall into a job count (decision I).
        # A direct-requirements (Type-I) divisor: it OMITS the Type-II output/employment multiplier
        # (~1.5–2×), so it under-counts induced jobs; `demand_multiplier` absorbs that calibration.
        self._va_per_worker = macro.VA_BASELINE_USD / baseline_emp if (baseline_emp := v1.emp0.sum()) else 0.0
        # Structural fields frozen into the shared arrays/engines — _bind_params refuses a mismatch.
        self._built_structural = (params.reabsorption_rung, params.reabsorption_floor_pctile,
                                  params.consumption_scale, params.exposure_mapping,
                                  params.logistic_midpoint, params.logistic_steepness)

    # ---- stage 2: cheap lever-dependent bind (called per Monte Carlo draw) ---------------------------
    def _bind_params(self, params: V2Params) -> None:
        """Recompute every lever-dependent member for `params`. REBIND ATTRIBUTE REFERENCES ONLY — never
        mutate an array in place: the underlying arrays are SHARED across Monte Carlo draws."""
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
                       ("price_passthrough", params.price_passthrough),
                       ("automation_tax_rate", params.automation_tax_rate),
                       ("survivor_spillover_to_profit", params.survivor_spillover_to_profit),
                       ("ubi_recapture_rate", params.ubi_recapture_rate)):
            assert 0.0 <= _v <= 1.0, f"{_n}={_v} is out of its documented [0, 1] domain"
        # The robot tax is paid from retained profit (corp-deductible via disp_factor) — a rate above the
        # retained-profit capacity would drive the corporate base negative. Fail loud.
        assert params.automation_tax_rate <= params.retained_profit_share * (1.0 - params.auto_cost) + 1e-9, \
            "automation_tax_rate exceeds retained_profit_share·(1−auto_cost) — no profit left to pay it"
        assert 0.0 <= params.baseline_growth_rate <= 0.10, "baseline_growth_rate out of [0, 0.10]"
        for _n, _v in (("income_tax_mult", params.income_tax_mult),
                       ("corp_tax_mult", params.corp_tax_mult),
                       ("cons_tax_mult", params.cons_tax_mult)):
            # surcharges may exceed 1 (not the [0,1] loop above); negative/non-finite is nonsense
            assert np.isfinite(_v) and _v >= 0.0, f"{_n}={_v} must be finite and ≥ 0"
        assert params.ssdi_annual >= 0.0, "ssdi_annual must be ≥ 0"
        assert params.robotics_lag >= 0.0, "robotics_lag must be ≥ 0 (years of capacity build-out)"
        assert (params.reabsorption_rung, params.reabsorption_floor_pctile, params.consumption_scale,
                params.exposure_mapping, params.logistic_midpoint,
                params.logistic_steepness) == self._built_structural, \
            "structural field differs from the built template — rebuild, don't bind"

        # v1's lever-dependent members: p/lp carry interest, ubi, demand_multiplier, reabsorption_rate,
        # adoption_path, n_periods, kernel mpc/stickiness; ui_share and g_cell are derived here.
        # g_cell via combine_channels is BIT-IDENTICAL to v1's displacement_fraction (levers.py: the
        # single source of the float-op order) — the C8 sweep is the gate.
        v1 = self._v1
        v1.lp, v1.p = params.lever_params(), params.to_v1()[1]
        v1.ui_share = min(1.0, params.ui_weeks / 52.0)
        v1.g_cell = levers.combine_channels(self._cog_cell, self._rob_cell,
                                            params.cognitive_feasibility, params.physical_feasibility)

        # reabsorption: the haircut-dependent delta from the retained engine (rung 1) / legacy factors.
        if self._reab_eng is not None:
            self._reab1 = self._reab_eng.delta(params.reemployment_haircut, params.mpc,
                                               params.consumption_stickiness)
            self._reab_wage = np.maximum(self._reab_eng.worker_wage * (1.0 - params.reemployment_haircut),
                                         self._reab_eng.service_floor)
            self._reab_scar_pw = self._reab1["net_takehome_loss"]
        else:
            self._reab1 = None
            self._reab_wage = v1.wage * (1.0 - params.reemployment_haircut)
            self._reab_scar_pw = params.reemployment_haircut * (v1.wage - self._inc_after_pw
                                                                - self._emp_fica_pw)

        # STANDING per-worker net income withdrawal by worker state — the level-targeting demand basis.
        # ONE budget constraint, shared with the fiscal side (nets the taxes stopped AND the transfers/UI
        # actually paid); cons_state deliberately EXCLUDED (keyed to the same take-home drop).
        self._net_after_pw = v1.wage - self._inc_after_pw - self._emp_fica_pw - self._tr_after_pw
        blend = lambda c: (v1.ui_share * v1.arr["during"][c]
                           + (1 - v1.ui_share) * v1.arr["after"][c])
        self._net_ui_pw = (v1.wage - blend("inc_fed") - blend("inc_state") - self._emp_fica_pw
                           - blend("transfer_fed") - blend("transfer_state") - v1.ui * v1.ui_share)
        # Level-controller stability guard: the induced stock appears in its own target (the multiplier
        # fixed point); with the one-period lag it converges geometrically iff the loop gain
        # ρ = dm·mpc·stickiness·d̄/va_pw < 1 (ρ ≈ 0.1 at the shipped dm=0.5). Fail loud, don't diverge.
        if params.demand_multiplier > 0 and self._va_per_worker > 0:
            d_bar = float((v1.emp0 * self._net_after_pw).sum()) / v1.emp0.sum()
            rho = (params.demand_multiplier * params.mpc * params.consumption_stickiness
                   * d_bar / self._va_per_worker)
            assert rho < 1.0, f"demand loop gain ρ={rho:.2f} ≥ 1 — the induced fixed point diverges"

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
        # tax-regime multipliers (static scoring, ledger-only). Skip the multiply entirely at 1.0 —
        # the C8 fast path stays bit-identical and no extra arrays are allocated.
        im, cm, km = v2p.income_tax_mult, v2p.corp_tax_mult, v2p.cons_tax_mult
        # BASELINE surcharges: a real tax change also collects on the un-displaced baseline, so
        # with the delta scaling the lever is a true flat surcharge: total = mult·(baseline−losses).
        # With no automation, raising a mult now reduces the deficit — constants, hoisted once;
        # exact zeros at mult=1 keep every new column 0.0 and C8 untouched.
        _mults_live = im != 1.0 or cm != 1.0 or km != 1.0
        if _mults_live:
            inc_surch_fed = (im - 1.0) * self._fed_inc_base
            corp_surch_fed = (cm - 1.0) * self._fed_corp_base
            cons_surch_fed = (km - 1.0) * self._fed_cons_base
            surch_fed_total = inc_surch_fed + corp_surch_fed + cons_surch_fed
            inc_surch_st = (im - 1.0) * self._st_inc_base * self._surch_inc_share
            corp_surch_st = (cm - 1.0) * self._st_corp_base * self._surch_corp_share
            cons_surch_st = (km - 1.0) * self._st_cons_base * self._surch_cons_share
            surch_state = inc_surch_st + corp_surch_st + cons_surch_st   # per-state GAIN array
        else:
            inc_surch_fed = corp_surch_fed = cons_surch_fed = surch_fed_total = 0.0
            inc_surch_st = corp_surch_st = cons_surch_st = None
            surch_state = None
        debt = 0.0
        baseline_emp = v1.emp0.sum()
        baseline_rev = None
        slack_prev = 0.0                                  # t−1 labour-market slack (J.1); 0 at t=0
        W_mech = 1.0                                      # accumulated survivor mechanical wage multiplier
        induced_flow_pending = np.zeros(len(v1.wage))     # SIGNED level-controller flow for t+1; 0 at t=0
        auto_disp = np.zeros(len(v1.wage))                # cumulative automation-displaced stock (fix 1)
        out = []

        for t in range(p.n_periods):
            # --- steps 1-2: diffusion + displacement (cumulative diffusion ceiling — fix 1). The robot
            #     channel ramps over `robotics_lag` years (AI-built industrial capacity — coherence C6);
            #     lag==0 uses v1.g_cell verbatim (the bit-identical C8 fast path). ---
            adopt = v1._adoption(t)
            if v2p.robotics_lag > 0:
                ramp_t = min(1.0, t / v2p.robotics_lag)
                g_cell_t = levers.combine_channels(self._cog_cell, self._rob_cell,
                                                   v2p.cognitive_feasibility,
                                                   v2p.physical_feasibility * ramp_t)
            else:
                g_cell_t = v1.g_cell
            flow = workers.displacement_flow(g_cell_t, adopt, v1.emp0, auto_disp, st.employed)
            auto_disp = auto_disp + flow
            new = st.displace(flow)
            # decision I (level-targeting): last period's SIGNED controller flow lands NOW as a
            # C1-guarded employment movement — layoffs when the induced stock is below target,
            # RELEASES (re-hiring) when the standing withdrawal fell. 0 at t=0.
            st.displace_extra(np.maximum(induced_flow_pending, 0.0))
            st.release_induced(np.maximum(-induced_flow_pending, 0.0))

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
            # tax-regime mults on the displaced channels — ONE site covers the during-UI blend, the
            # after-phase, and BOTH reabsorption rungs (everything flows through ch). Fresh arrays,
            # so no shared-cache mutation; every downstream consumer (net_fed, state_net, ledger
            # deltas, output columns → C6/C6-state) reads these same entries.
            if im != 1.0:
                ch["inc_fed"] = ch["inc_fed"] * im
                ch["inc_state"] = ch["inc_state"] * im
            if km != 1.0:
                ch["cons_state"] = ch["cons_state"] * km

            ui_outlay_fed = st.on_ui * v1.ui * v1.ui_share
            ui_tax_fed = 0.10 * ui_outlay_fed                 # income tax on UI benefits
            if im != 1.0:
                ui_tax_fed = ui_tax_fed * im

            # --- steps 3-4: disposition router. The AUTOMATED-JOBS base is the cumulative automation-
            #     displaced stock `auto_disp` (coherence fix): a job stays automated after the worker moves
            #     on — reabsorption/attrition must not retroactively un-automate it (which used to collapse
            #     saved_bill and flip the federal balance). Worker states keep driving the HOUSEHOLD fiscal
            #     channels above; `auto_disp` excludes induced (demand layoffs produce no saved comp). ---
            disp = disposition.route(auto_disp, self._comp_pw, v1.corp, v2p)
            cp = compute_pool.route_to_compute_pool(disp.automation_spend, v2p)

            # --- step 5: survivor wage index — FUNDED W* (coherence fix) + market level. ---
            #   The routed survivor_gains flow pays the standing raise's recurring cost FIRST (maintenance,
            #   in comp-$ — the ℓ loading folds the comp-vs-wage units wedge); only the surplus raises W
            #   further (converging W* = 1 + gains/(ℓ·wage_bill), capped by the ceiling); unfundable → W
            #   snaps down to the funded level. The raise is SELF-FINANCING — the old survivor_profit_netting
            #   (which deducted corporate tax never booked, up to 81×) is deleted; the raise is taxed once,
            #   as labour income via sd. C5c (every branch, exact):
            #       wage_cost + overflow_to_profit + overflow_to_price == survivor_gains,
            #   with wage_cost = ℓ·wage_bill·(W_mech_new − 1) = maintenance + increment.
            #   Market (unconserved, C5-market-exempt): elasticity × t−1 slack (J.1, 0 at t=0); the part
            #   that would push total W above the ceiling is simply TRUNCATED (no capital counterparty).
            ceiling = v2p.survivor_raise_ceiling
            comp_bill = (employed_post * self._comp_pw).sum()
            comp_loading = (comp_bill / wage_bill) if wage_bill > 0 else 1.0   # ℓ ≈ 1.4 (comp per wage $)
            W_mech, survivor_wage_cost, increment, overflow = survivor.funded_w_update(
                disp.survivor_gains, W_mech, wage_bill, comp_loading, ceiling)
            overflow_to_profit = overflow * v2p.survivor_spillover_to_profit
            overflow_to_price = overflow - overflow_to_profit
            market_frac = v2p.survivor_elasticity * slack_prev
            W_surv = W_mech + market_frac
            if np.isfinite(ceiling):
                W_surv = min(W_surv, ceiling)                            # market truncated at the cap
            W_surv = max(W_surv, 0.0)
            sd = self._survivor.delta(W_surv)
            # income mult on the raises' income-tax recapture; payroll stays statutory (separable —
            # the engine returns the three channels distinct)
            sd_inc_fed = sd["inc_fed"] * im if im != 1.0 else sd["inc_fed"]
            sd_inc_state = sd["inc_state"] * im if im != 1.0 else sd["inc_state"]
            sd_fed = (sd_inc_fed + sd["payroll"]) * employed_post         # per-cell GAIN (revenue +)
            sd_state = sd_inc_state * employed_post

            # the profit overflow is recovered as corporate tax at the same per-profit-$ rate the router
            # uses (Σ auto_disp·corp_pw / saved_bill — linear in the surplus base, note C); the price
            # overflow joins the disposition's price reduction in deflating P. Both vanish at reduction.
            corp_full = float((auto_disp * v1.corp).sum())
            corp_rate_per_profit = (corp_full / disp.saved_bill) if disp.saved_bill > 0 else 0.0
            overflow_corp_tax = corp_rate_per_profit * overflow_to_profit
            # corp mult on the capital-recapture bundle — ONE local consumed at all three corp-offset
            # sites (net_fed, ledger delta, corp_offset_B column); never inside route(), so the
            # C2/C5b partition legs (retained/price/survivor) stay untouched.
            corp_offset_cell = disp.corporate_offset_cell if cm == 1.0 \
                else disp.corporate_offset_cell * cm
            if cm != 1.0:
                overflow_corp_tax = overflow_corp_tax * cm
            price_reduction_total = disp.price_reduction + overflow_to_price

            # --- step 6: macro update. P deflates reporting only (A2: never the nominal fiscal);
            #     Y is the real-GDP/productivity index for the denominator. The dividend is OUTPUT-weighted
            #     (fix 3): the automated share of the COMP bill (saved_bill / total comp), not headcount. ---
            automated_comp_fraction = disp.saved_bill / macro.COMP_TOTAL_USD
            Y = macro.productivity_index(automated_comp_fraction, v2p)
            P = macro.price_level(price_reduction_total, Y, v2p)
            ngdp = macro.nominal_gdp(Y, P) * (1.0 + v2p.baseline_growth_rate) ** t
            # ^ baseline trend growth g scales the %-GDP DENOMINATORS only (coherence fix: r>g=0 used to
            #   invert the long-horizon debt/GDP dynamics). Nominal dollar columns are unchanged.

            # federal: losses positive; the survivor GAIN and the profit-overflow recovery are subtracted
            # (W<1 → sd<0 → adds to deficit); the survivor netting is ADDED (less corp recovery).
            fed = (ch["inc_fed"] + ch["payroll_fed"] + ch["transfer_fed"]
                   + ui_outlay_fed - ui_tax_fed - corp_offset_cell - sd_fed)
            net_fed = fed.sum() - cp.tax_fed - overflow_corp_tax

            # --- step 8: state balanced-budget close (H, C6-state, C7). Compose per-state net loss, then
            #     close it within-year by rate hikes (capped) and/or spending cuts. The reported gap stays
            #     the PRE-close austerity magnitude (= v1 → C8-safe); the close's only feedback is the
            #     contraction, which feeds lagged demand (I) and is gated by demand_multiplier. ---
            state_cell = ch["inc_state"] + ch["cons_state"] + ch["transfer_state"] - sd_state
            state_net = np.bincount(v1.state_of_cell, weights=state_cell, minlength=len(v1.uniq_states))
            if _mults_live:                              # baseline surcharges SHRINK the state gaps
                state_net = state_net - surch_state      # (revenue gain; enters BEFORE the close)
            # remaining labour income (W-scaled) + the reabsorbed's actual earnings at w_d (coherence fix:
            # they pay taxes, so the close can tax them — ~12% of the base was invisible before)
            taxable_base = np.bincount(v1.state_of_cell,
                                       weights=employed_post * v1.wage * W_surv
                                       + st.reabsorbed * self._reab_wage,
                                       minlength=len(v1.uniq_states))
            close = government.close_state_gaps(state_net, taxable_base, v2p)
            state_gap_total = close.gap.sum()                           # pre-close magnitude (= v1)

            # --- step 8.5: federal policy flows. UBI is a real outlay NET of recapture (income-tax
            #     clawback + means-tested crowd-out — the coherence fix: UBI now has a recipient side);
            #     the robot tax recovers revenue on the automated comp bill, PAID from retained profit
            #     (its corp-deductibility already shrank the corporate offset via disp_factor). ---
            ubi_outlay = p.ubi_annual * baseline_emp                    # gross: per-worker UBI × workforce
            ubi_recapture = v2p.ubi_recapture_rate * ubi_outlay
            automation_tax = v2p.automation_tax_rate * disp.saved_bill  # X% of the automated comp bill
            # SSDI outlay on the exited stock (coherence fix: they carried the after-loss but drew no
            # benefit — ~$162B/yr missing by y10). Federal; not in the baked transfer grids (no overlap
            # beyond the small documented SSI-concurrency approximation). Inert at reduction (exited ≡ 0).
            ssdi_outlay = st.exited.sum() * v2p.ssdi_annual
            net_fed = net_fed + ubi_outlay - ubi_recapture - automation_tax + ssdi_outlay \
                - surch_fed_total                        # baseline tax surcharges: federal revenue

            debt = debt * (1 + p.interest_rate) + net_fed

            # UBI financing metric: NET cost over the LIVE labour-income base (survivor raises scale it;
            # rung-1 reabsorbed earn w_d). At reduction (W=1, rung 0, recapture 0) == v1's ubi_rate exactly.
            # rung-gated reabsorbed term: ubi_required_rate is a C8 column, and at reduction (rung 0) the
            # base must collapse to v1's wage_bill exactly (W_surv=1, no reabsorbed earnings term).
            ubi_base = wage_bill * W_surv + ((st.reabsorbed * self._reab_wage).sum()
                                             if v2p.reabsorption_rung == 1 else 0.0)
            ubi_rate = ((p.ubi_annual * baseline_emp * (1.0 - v2p.ubi_recapture_rate)) / ubi_base
                        if (p.ubi_annual > 0 and ubi_base > 0) else 0.0)

            # --- step 9: LEVEL-TARGETING demand (coherence fix, replaces the flow ratchet). The induced
            #     stock TRACKS a target = k·(standing net withdrawal): a stationary shock ⇒ a stationary
            #     induced stock (no unbounded minting), and the channel is SIGNED — transfers/UI/SSDI the
            #     ledger pays these households, survivor raises, and net UBI all reduce the withdrawal;
            #     a falling target RELEASES induced workers back to employed. One-period lag (J.1).
            #     retired: zero (their baseline twin retired too). cons_state excluded (double-count).
            #     max(0,·) on the household aggregate: stimulus can zero induced, never push employment
            #     above baseline. State austerity stays IN-STATE (CA's cuts no longer lay off Texans);
            #     the household component is allocated nationally. ---
            hh_withdrawal = float(
                (st.on_ui * self._net_ui_pw
                 + (st.exhausted + st.induced) * self._net_after_pw
                 + st.exited * (self._net_after_pw - v2p.ssdi_annual)
                 + st.reabsorbed * self._reab_scar_pw).sum())
            hh_withdrawal -= wage_bill * (W_surv - 1.0)                 # survivor raises inject; cuts withdraw
            hh_withdrawal -= ubi_outlay - ubi_recapture                 # net UBI injects
            k = (p.demand_multiplier * p.kernel_params.mpc
                 * p.kernel_params.consumption_stickiness / self._va_per_worker
                 if self._va_per_worker > 0 else 0.0)
            contraction_s = close.spending_cut * government.MPC_GOV + close.recovered * v2p.mpc
            # Allocation key = the ACTIVE demand-exposed pool (employed + induced), NOT employed
            # alone. The induced target is a per-cell STOCK target: with an employed-only key, a
            # cell whose employment automation zeroed but whose induced stock persists gets
            # share→0 → target→0 → a spurious FULL release of workers into jobs that no longer
            # exist, which the target then re-concentrates on and re-displaces — a period-2 limit
            # cycle at near-total automation (audit-verified: employed oscillated 1.0M↔13.9M at
            # agi-20y t=17-19; with this key the decline is monotone and sign-flips drop to 0).
            # Inert at reduction: demand_multiplier=0 ⇒ k=0 ⇒ the key is never consulted.
            active = employed_post + st.induced
            state_active = np.bincount(v1.state_of_cell, weights=active,
                                       minlength=len(v1.uniq_states))
            in_state_share = active / np.where(state_active > 0, state_active, 1.0)[v1.state_of_cell]
            emp_share = active / active.sum() if active.sum() > 0 else 0.0
            induced_target = k * (max(0.0, hh_withdrawal) * emp_share
                                  + contraction_s[v1.state_of_cell] * in_state_share)
            induced_flow_pending = induced_target - st.induced          # SIGNED; consumed at START of t+1
            standing_withdrawal = max(0.0, hh_withdrawal) + contraction_s.sum()

            rev_lost = ch["inc_fed"].sum() + ch["inc_state"].sum() + ch["payroll_fed"].sum()
            if baseline_rev is None:
                # income mult on the two inc components (payroll not) keeps revenue_lost_pct a
                # rate-consistent ratio — the numerator inherited the scaling through ch.
                baseline_rev = (v1.emp0 * ((v1.arr["after"]["inc_fed"]
                                            + v1.arr["after"]["inc_state"]) * im
                                           + v1.arr["after"]["payroll_fed"])).sum()

            # absolute ledger (Phase 5): federal revenue-side delta ($B, negative = revenue lost) +
            # post-close state figures, netted against the real base-linkage absolutes.
            fed_rev_delta_B = (-(ch["inc_fed"].sum() + ch["payroll_fed"].sum()) + ui_tax_fed.sum()
                               + corp_offset_cell.sum() + cp.tax_fed + sd_fed.sum()
                               + overflow_corp_tax
                               + automation_tax
                               + surch_fed_total) / 1e9  # automation tax + surcharges are revenue
            led_fed = self._ledger.federal(net_fed / 1e9, fed_rev_delta_B, ngdp)
            led_state = self._ledger.state(state_gap_total / 1e9, close.recovered.sum() / 1e9)

            out.append({
                "period": t, "adoption": adopt,
                "employed_M": st.employed.sum() / 1e6,
                "on_ui_M": st.on_ui.sum() / 1e6, "exhausted_M": st.exhausted.sum() / 1e6,
                "reabsorbed_M": st.reabsorbed.sum() / 1e6, "exited_M": st.exited.sum() / 1e6,
                "induced_M": st.induced.sum() / 1e6,                    # 6th state: demand-driven layoffs (I)
                "retired_M": st.retired.sum() / 1e6,                    # 7th state: delta-neutral attrition
                "population_M": st.total().sum() / 1e6,
                # C1 PER-CELL: the worst per-cell mass residual (the aggregate population_M can hide a
                # per-cell leak that nets to zero across the 33k cells).
                "max_cell_resid_M": float(np.abs(st.total() - v1.emp0).max()) / 1e6,
                "employment_drop_pct": 100 * (1 - st.employed.sum() / baseline_emp),
                "revenue_lost_B": rev_lost / 1e9,
                "revenue_lost_pct": 100 * rev_lost / baseline_rev if baseline_rev else 0.0,
                "transfers_added_B": (ch["transfer_fed"].sum() + ch["transfer_state"].sum()
                                      + ui_outlay_fed.sum()) / 1e9,
                "corp_offset_B": corp_offset_cell.sum() / 1e9,
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
                "survivor_wage_cost_B": survivor_wage_cost / 1e9,       # ℓ·wb·(W−1): maintenance+increment
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
                "ubi_outlay_B": ubi_outlay / 1e9,                       # fix 2: gross UBI outlay
                "ubi_recapture_B": ubi_recapture / 1e9,                # coherence: clawback + crowd-out
                "automation_tax_B": automation_tax / 1e9,              # fix 4: robot tax (lowers the deficit)
                "ssdi_outlay_B": ssdi_outlay / 1e9,                    # coherence: SSDI on the exited
                # baseline tax-regime surcharges ((mult−1)·2024 receipts line; 0.0 at mult=1)
                "income_surcharge_fed_B": inc_surch_fed / 1e9,
                "corp_surcharge_fed_B": corp_surch_fed / 1e9,
                "excise_surcharge_fed_B": cons_surch_fed / 1e9,
                "income_surcharge_state_B": (inc_surch_st.sum() / 1e9 if _mults_live else 0.0),
                "corp_surcharge_state_B": (corp_surch_st.sum() / 1e9 if _mults_live else 0.0),
                "cons_surcharge_state_B": (cons_surch_st.sum() / 1e9 if _mults_live else 0.0),
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
                "induced_target_M": float(induced_target.sum()) / 1e6,
                "induced_pending_M": float(induced_flow_pending.sum()) / 1e6,   # SIGNED flow queued for t+1
                "standing_withdrawal_B": standing_withdrawal / 1e9,             # a LEVEL, not a flow
                # --- Phase 5: absolute revenue ledger ---
                "fed_revenue_B": led_fed["fed_revenue_B"],
                "fed_deficit_abs_B": led_fed["fed_deficit_abs_B"],
                "fed_deficit_abs_pct_gdp": led_fed["fed_deficit_abs_pct_gdp"],
                "state_fiscal_position_B": led_state["state_fiscal_position_B"],
            })

            # carry this period's cumulative slack to t+1 (decision J.1 keeps ΔW_market predetermined).
            # slack (coherence fix): the reabsorbed are EMPLOYED (service jobs) and the retired left the
            # labour force with their baseline twin — neither should suppress survivor wages. At reduction
            # the only consumer (market_frac) is elasticity-gated → C8-safe.
            lf = baseline_emp - st.retired.sum()
            slack_prev = 1.0 - (employed_post.sum() + st.reabsorbed.sum()) / lf if lf > 0 else 0.0
            # --- period end: age on-UI into exhausted, split {exited, reabsorbed, stay}, then attrition ---
            st.age_and_transition(p.reabsorption_rate, v2p.lfp_exit_rate, v2p.attrition_rate)

        # retain the FINAL period's state close for the per-state table (fresh arrays each call —
        # verified safe to keep). An attribute, not output columns, so C8 (a column comparison) and
        # the MC fast path (attribute lands on the per-draw shallow copy) are untouched.
        self._last_close, self._last_state_net, self._last_taxable_base = close, state_net, taxable_base
        return pd.DataFrame(out)

    @property
    def state_table(self) -> pd.DataFrame:
        """Final-year per-state close, one row per jurisdiction (row i ↔ v1.uniq_states[i]).

        `net_B` is SIGNED (survivor-gain-heavy states can run a surplus; `shortfall_B` floors them
        at 0); `spending_cut_B` includes PLANNED cuts under the mix — `at_cap` flags where a forced
        component exists. Only populated after run(); unavailable through mc.ScenarioContext.run
        (which returns just the DataFrame)."""
        close = self._last_close
        base = np.where(self._last_taxable_base > 0, self._last_taxable_base, np.nan)
        return pd.DataFrame({
            "state": self._v1.uniq_states,
            "net_B": self._last_state_net / 1e9,
            "shortfall_B": close.gap / 1e9,
            "rate_hike_B": close.recovered / 1e9,
            "spending_cut_B": close.spending_cut / 1e9,
            "implied_rate_hike_pct": 100.0 * close.recovered / base,
            "at_cap": close.capped,
        })


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
