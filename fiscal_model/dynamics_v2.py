"""V2 orchestrator — Phases 0-1.

`DynamicModelV2` runs the multi-actor model through the new structure: the explicit 5-state worker
machine (`workers.py`: employed / on-UI / exhausted / reabsorbed / exited) and a baseline ledger
seeded from the base-linkage accounts. At a v1-reduction config (`levers_v2.DEFAULTS_V1REDUCTION`)
every new behavioral lever is off, so the fiscal math is bit-for-bit v1 and `exited == 0` — the C8
anchor every later phase is gated against. Phase 1 wired the real worker transitions + `lfp_exit`;
the disposition / compute-pool / macro / survivor / government seams remain pass-throughs until their
phases.

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

from . import loaders, workers
from .dynamics import DynamicModel
from .levers_v2 import V2Params


class DynamicModelV2:
    def __init__(self, data: loaders.FiscalData, deltas: pd.DataFrame, params: V2Params):
        self.data = data
        self.v2p = params
        lp, dp = params.to_v1()
        # Reuse v1's array preparation verbatim -> identical inputs guarantee the C8 anchor.
        self._v1 = DynamicModel(data, deltas, lp, dp)
        self._baseline = self._baseline_rates(data)

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
            # corp offset on the not-reabsorbed displaced (exited continue it; == v1's new+U at reduction)
            corp_offset_fed = (st.on_ui + st.exhausted + st.exited) * v1.corp

            fed = (ch["inc_fed"] + ch["payroll_fed"] + ch["transfer_fed"]
                   + ui_outlay_fed - ui_tax_fed - corp_offset_fed)
            net_fed = fed.sum()
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
                "corp_offset_B": corp_offset_fed.sum() / 1e9,
                "fed_deficit_B": net_fed / 1e9, "fed_debt_B": debt / 1e9,
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
