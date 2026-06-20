"""Interactive AI-automation fiscal model (briefing §1 end goal).

A user sets the levers; the app runs the dynamic model and shows the downstream fiscal
consequences — lost revenue, transfer outlays, the partial capital-tax offset, federal
deficits/debt, and the within-year state budget gap — with the cost → offset → net framing.

Run:  .venv/bin/streamlit run app/streamlit_app.py
(The model backend is reused as-is; the scenario-invariant per-worker deltas are precomputed
and cached, so each lever change re-runs in well under a second.)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # project root -> import fiscal_model

import numpy as np
import pandas as pd
import streamlit as st

from fiscal_model import loaders, levers
from fiscal_model.dynamics import DynamicModel, DynamicsParams, precompute_worker_deltas
from fiscal_model.kernel import KernelParams
from fiscal_model.transfers import TransferLookup

st.set_page_config(page_title="AI Automation Fiscal Model", layout="wide")


@st.cache_resource
def load_backend():
    data = loaders.load_all(validate=False)
    lookup = TransferLookup()
    deltas = precompute_worker_deltas(data, lookup, KernelParams())   # loads the cached table
    return data, deltas


data, deltas = load_backend()

st.title("AI Automation — Fiscal Consequences")
st.caption("Set the levers. The accounting is the point: every assumption is yours to dial, and the "
           "consequences propagate. Watch the tax base migrate from **labor** to **capital** — and "
           "why revenue can fall faster than employment while states, unlike Washington, must balance.")

# ----------------------------------------------------------------- levers
sb = st.sidebar
sb.header("Automation scenario")
cog = sb.slider("Cognitive feasibility (AI capability)", 0.0, 1.0, 0.70, 0.05)
phys = sb.slider("Robotics feasibility (physical work)", 0.0, 1.0, 0.20, 0.05)
adopt0 = sb.slider("Adoption — start", 0.0, 1.0, 0.10, 0.05)
adopt1 = sb.slider("Adoption — end", 0.0, 1.0, 0.80, 0.05)
n_periods = sb.slider("Horizon (years)", 3, 30, 10)
mapping = sb.selectbox("Exposure → share mapping", ["percentile", "logistic"])

sb.header("Labor market")
reab = sb.slider("Reabsorption rate / yr  (0 = the thesis)", 0.0, 1.0, 0.0, 0.05)
haircut = sb.slider("Re-employment wage haircut", 0.0, 1.0, 0.30, 0.05)

sb.header("Offsets — steelman the optimistic case")
corp_scale = sb.slider("Corporate-tax recapture ×", 0.0, 2.0, 1.0, 0.1,
                       help="Scales the capital-income tax recovered when labour cost becomes profit.")
cons_scale = sb.slider("Consumption response × (stickiness)", 0.0, 2.0, 1.0, 0.1)
demand = sb.slider("Second-round demand multiplier", 0.0, 1.0, 0.0, 0.05)

sb.header("Fiscal & policy")
interest = sb.slider("Interest rate on federal debt", 0.0, 0.10, 0.03, 0.005)
ui_weeks = sb.slider("UI duration (weeks)", 0, 52, 26)
state_resp = sb.selectbox("State budget response", ["mix", "cut_spending", "raise_rates"])
ubi = sb.slider("UBI per capita / yr ($)", 0, 30_000, 0, 1_000)

# ----------------------------------------------------------------- run
lp = levers.LeverParams(exposure_mapping=mapping, cognitive_feasibility=cog,
                        physical_feasibility=phys, adoption=1.0)
dp = DynamicsParams(
    n_periods=n_periods, ui_weeks=ui_weeks, reabsorption_rate=reab, reemployment_haircut=haircut,
    demand_multiplier=demand, state_response=state_resp, interest_rate=interest,
    adoption_path=list(np.linspace(adopt0, adopt1, n_periods)), ubi_annual=ubi,
    corp_offset_scale=corp_scale, consumption_scale=cons_scale)
res = DynamicModel(data, deltas, lp, dp).run()
final = res.iloc[-1]

# ----------------------------------------------------------------- headline
c = st.columns(5)
c[0].metric("Employment", f"−{final['employment_drop_pct']:.0f}%")
c[1].metric("Labor revenue", f"−{final['revenue_lost_pct']:.0f}%",
            help="Falls faster than employment — the most-exposed work is the highest-paid.")
c[2].metric("Federal deficit (final yr)", f"${final['fed_deficit_B']:,.0f}B")
c[3].metric("Federal debt (cumulative)", f"${final['fed_debt_B']:,.0f}B")
c[4].metric("State gap (must close/yr)", f"${final['state_gap_B']:,.0f}B")

if ubi > 0:
    st.info(f"To fund a \\${ubi:,}/yr UBI on the **eroded** labor-income base, the required average "
            f"tax rate rises to **{final['ubi_required_rate']:.0%}** by year {n_periods} "
            f"(from {res['ubi_required_rate'].iloc[0]:.0%}).")

# ----------------------------------------------------------------- charts
left, right = st.columns(2)
with left:
    st.subheader("Revenue falls faster than employment")
    st.line_chart(res.set_index("period")[["employment_drop_pct", "revenue_lost_pct"]])
    st.subheader("Federal deficit & cumulative debt ($B)")
    st.line_chart(res.set_index("period")[["fed_deficit_B", "fed_debt_B"]])
with right:
    st.subheader("Cost → offset → net (federal+state, by year, $B)")
    decomp = pd.DataFrame({
        "revenue lost": res["revenue_lost_B"],
        "transfers + UI": res["transfers_added_B"],
        "− capital recapture": -res["corp_offset_B"],
    }, index=res["period"])
    st.bar_chart(decomp)
    st.subheader("State budget gap — unfinanceable, must be closed ($B/yr)")
    st.line_chart(res.set_index("period")[["state_gap_B"]])

with st.expander("Per-year detail"):
    st.dataframe(res.style.format("{:,.1f}"), use_container_width=True)

with st.expander("Method & v1 caveats (transparency)"):
    st.markdown(
        "- **Channels are separate & additive**: hand-rolled income/payroll tax, PolicyEngine-baked "
        "transfers, corporate (capital file), consumption (state). The corporate recapture is the "
        "*offset* — generally taxed lower than the labor it replaces, hence base migration.\n"
        "- **States must balance within-year**; the federal government runs the deficit — a "
        "contractionary asymmetry.\n"
        "- **v1 simplifications**: benefits are entitlement (not take-up-adjusted); pass-through "
        "capital tax routed federal-only; UI params are national defaults; corporate offset tied to "
        "the displaced worker. See the repo README.")
