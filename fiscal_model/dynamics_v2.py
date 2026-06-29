"""V2 orchestrator — Phases 0-3.

`DynamicModelV2` runs the multi-actor model through the new structure: the explicit 5-state worker
machine (`workers.py`), the sector disposition router + compute pool (`firms/disposition.py`,
`compute_pool.py`), the macro environment (`macro.py`: P, Y), and a baseline ledger seeded from the
base-linkage accounts. At a v1-reduction config (`levers_v2.DEFAULTS_V1REDUCTION`) every new behavioral
lever is off, so the fiscal math is bit-for-bit v1 — the C8 anchor every later phase is gated against.
Phase 1 wired the worker transitions + `lfp_exit`; Phase 2 the disposition router (corporate-via-router
superseding `surplus_capture`) + compute pool; Phase 3 the macro state — P (price level) and Y
(productivity/GDP) drive the real / %-GDP reporting, and per the A2 rule P *only* deflates nominal
aggregates (it never enters the transfer interpolation). The `survivor_gains` share is recorded but
acquires its fiscal effect in Phase 4 (survivor → labor tax). Survivor / government seams remain
pass-throughs.

It reuses the v1 `DynamicModel`'s prepared arrays (g_cell, channel deltas, corp offset, ui, …) so
the inputs are *identical* to v1; the loop then reproduces v1's per-period arithmetic while also
carrying the 5-state population (for C1) and the baseline rates (for the Phase-0 t=0 gate).

Later phases replace the pass-through seams here (`_diffusion`, `_transitions`, `_disposition`,
`_survivor`, `_macro`, `_recompute`, `_government`, `_demand`) with real physics; this file is the
stable skeleton + the reduction guarantee.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import loaders, workers, compute_pool, macro
from .dynamics import DynamicModel
from .firms import disposition
from .levers_v2 import V2Params


class DynamicModelV2:
    def __init__(self, data: loaders.FiscalData, deltas: pd.DataFrame, params: V2Params):
        self.data = data
        self.v2p = params
        lp, dp = params.to_v1()
        # Reuse v1's array preparation verbatim -> identical inputs guarantee the C8 anchor.
        self._v1 = DynamicModel(data, deltas, lp, dp)
        self._baseline = self._baseline_rates(data)
        # per-cell fully-loaded compensation per worker (the disposition saved-bill basis)
        ms = data.matrices_sector.groupby("soc_code").agg(
            comp=("comp_musd", "sum"), emp=("emp_thousands", "sum"))
        ms["comp_pw"] = np.where(ms["emp"] > 0, ms["comp"] / ms["emp"] * 1000.0, 0.0)
        self._comp_pw = self._v1.d["soc_code"].map(ms["comp_pw"]).fillna(0.0).to_numpy()

    # ---- baseline ledger (t=0 gate, J.2): the absolute anchor for %-GDP & the tax-regime solver ----
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
        reab_factor = workers.reabsorbed_loss_factor(v2p)  # Rung-0 haircut residual
        debt = 0.0
        baseline_emp = v1.emp0.sum()
        baseline_rev = None
        out = []

        for t in range(p.n_periods):
            # --- steps 1-2: diffusion + displacement ---
            adopt = v1._adoption(t)
            frac = np.clip(v1.g_cell * adopt, 0.0, 1.0)
            st.displace(frac)

            # --- step 7: fiscal flows. on_ui -> UI blend; exhausted+exited -> 'after';
            #     reabsorbed -> Rung-0 haircut residual (tax channels only). ---
            out_after = st.exhausted + st.exited
            ch = {}
            for c in v1.arr["during"]:
                blend = v1.ui_share * v1.arr["during"][c] + (1 - v1.ui_share) * v1.arr["after"][c]
                cc = st.on_ui * blend + out_after * v1.arr["after"][c]
                if c in ("inc_fed", "inc_state", "payroll_fed", "cons_state"):
                    cc = cc + st.reabsorbed * reab_factor * v1.arr["after"][c]
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

            # --- step 6: macro update. P deflates reporting only (A2: never the nominal fiscal);
            #     Y is the real-GDP/productivity index for the denominator. ---
            automated_fraction = automated.sum() / baseline_emp
            Y = macro.productivity_index(automated_fraction, v2p)
            P = macro.price_level(disp.price_reduction, Y, v2p)
            ngdp = macro.nominal_gdp(Y, P)

            fed = (ch["inc_fed"] + ch["payroll_fed"] + ch["transfer_fed"]
                   + ui_outlay_fed - ui_tax_fed - disp.corporate_offset_cell)
            net_fed = fed.sum() - cp.tax_fed
            state_cell = ch["inc_state"] + ch["cons_state"] + ch["transfer_state"]
            state_net = np.bincount(v1.state_of_cell, weights=state_cell,
                                    minlength=len(v1.uniq_states))
            state_gap_total = state_net[state_net > 0].sum()

            induced = p.demand_multiplier * (net_fed + state_gap_total)
            net_fed += induced
            debt = debt * (1 + p.interest_rate) + net_fed

            base = (st.employed * v1.wage).sum()
            ubi_rate = (p.ubi_annual * baseline_emp / base) if (p.ubi_annual > 0 and base > 0) else 0.0

            rev_lost = ch["inc_fed"].sum() + ch["inc_state"].sum() + ch["payroll_fed"].sum()
            if baseline_rev is None:
                baseline_rev = (v1.emp0 * (v1.arr["after"]["inc_fed"] + v1.arr["after"]["inc_state"]
                                           + v1.arr["after"]["payroll_fed"])).sum()

            out.append({
                "period": t, "adoption": adopt,
                "employed_M": st.employed.sum() / 1e6,
                "on_ui_M": st.on_ui.sum() / 1e6, "exhausted_M": st.exhausted.sum() / 1e6,
                "reabsorbed_M": st.reabsorbed.sum() / 1e6, "exited_M": st.exited.sum() / 1e6,
                "population_M": st.total().sum() / 1e6,
                "employment_drop_pct": 100 * (1 - st.employed.sum() / baseline_emp),
                "revenue_lost_B": rev_lost / 1e9,
                "revenue_lost_pct": 100 * rev_lost / baseline_rev if baseline_rev else 0.0,
                "transfers_added_B": (ch["transfer_fed"].sum() + ch["transfer_state"].sum()
                                      + ui_outlay_fed.sum()) / 1e9,
                "corp_offset_B": disp.corporate_offset_cell.sum() / 1e9,
                "compute_pool_tax_B": cp.tax_fed / 1e9,
                "automation_spend_B": disp.automation_spend / 1e9,
                "price_reduction_B": disp.price_reduction / 1e9,
                "survivor_gains_B": disp.survivor_gains / 1e9,
                "offshore_leak_B": cp.offshore_leak / 1e9,
                "fed_deficit_B": net_fed / 1e9, "fed_debt_B": debt / 1e9,
                # macro (Phase 3): nominal is P-invariant; real = nominal/P; %-GDP = nominal/nominal-GDP
                "price_level": P, "productivity_index": Y,
                "fed_deficit_real_B": net_fed / P / 1e9, "fed_debt_real_B": debt / P / 1e9,
                "fed_deficit_pct_gdp": 100 * net_fed / ngdp, "fed_debt_pct_gdp": 100 * debt / ngdp,
                "state_gap_pct_gdp": 100 * state_gap_total / ngdp,
                "state_gap_B": state_gap_total / 1e9, "ubi_required_rate": ubi_rate,
            })

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
