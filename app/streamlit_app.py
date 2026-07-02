"""Interactive AI-automation fiscal model (briefing §1 end goal).

A user sets the levers; the app runs the dynamic model and shows the downstream fiscal consequences. Two
engines share the sidebar:
  • **v1** — the static per-worker kernel in a stock-flow loop (the original thesis demo).
  • **v2** — the multi-actor model with genuine feedbacks: a disposition router (saved wage bill →
    profit / price / survivor raises / compute), a compute-capital pool, survivor wages on the
    still-employed [A], a macro environment (price & productivity), and the government closure [H]
    (states balance within-year; the second-round demand contraction re-enters as layoffs).

v2 reduces EXACTLY to v1 when every behavioral lever is off — so the toggle is an honest A/B.

Run:  .venv/bin/streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # project root -> import fiscal_model

import numpy as np
import pandas as pd
import streamlit as st

from fiscal_model import loaders, levers, reabsorption
from fiscal_model.dynamics import DynamicModel, DynamicsParams, precompute_worker_deltas
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.kernel import KernelParams
from fiscal_model.levers_v2 import V2Params
from fiscal_model.transfers import TransferLookup

st.set_page_config(page_title="AI Automation Fiscal Model", layout="wide")


# ----------------------------------------------------------------- pure param builder (testable)
def build_v2_params(ui: dict) -> V2Params:
    """Map the sidebar dict to a V2Params. Disposition survivor share is the remainder of profit+price
    (clamped ≥0). Kept pure so a smoke test can construct it without Streamlit."""
    survivor_share = max(0.0, 1.0 - ui["retained_profit_share"] - ui["price_reduction_share"])
    ceiling = float("inf") if ui["survivor_unbounded"] else ui["survivor_raise_ceiling"]
    return V2Params(
        exposure_mapping=ui["mapping"], cognitive_feasibility=ui["cog"], physical_feasibility=ui["phys"],
        robotics_lag=ui["robotics_lag"],
        adoption=1.0, adoption_path=ui["adoption_path"], n_periods=ui["n_periods"],
        retained_profit_share=ui["retained_profit_share"], price_reduction_share=ui["price_reduction_share"],
        survivor_gains_share=survivor_share, auto_cost=ui["auto_cost"], offshore_share=ui["offshore_share"],
        compute_effective_rate=ui["compute_effective_rate"],
        survivor_raise_ceiling=ceiling, survivor_elasticity=ui["survivor_elasticity"],
        survivor_spillover_to_profit=ui["survivor_spillover_to_profit"],
        reabsorption_rung=ui["reabsorption_rung"], reabsorption_rate=ui["reab"],
        reemployment_haircut=ui["haircut"], lfp_exit_rate=ui["lfp_exit_rate"],
        attrition_rate=ui["attrition_rate"], ui_weeks=ui["ui_weeks"],
        price_passthrough=ui["price_passthrough"], productivity_passthrough=ui["productivity_passthrough"],
        demand_multiplier=ui["demand"], state_response=ui["state_resp"], state_cut_share=ui["state_cut_share"],
        state_rate_hike_cap=ui["state_rate_hike_cap"], automation_tax_rate=ui["automation_tax_rate"],
        interest_rate=ui["interest"], ubi_annual=ui["ubi"], ubi_recapture_rate=ui["ubi_recapture_rate"],
        baseline_growth_rate=ui["baseline_growth_rate"], denominator=ui["denominator"])


@st.cache_resource
def load_backend():
    try:
        data = loaders.load_all(validate=False)
        lookup = TransferLookup()
        deltas = precompute_worker_deltas(data, lookup, KernelParams())
        rung1_ok = reabsorption.engine_artifacts_exist()   # live engine — no prebuilt cache needed
        return (data, deltas, rung1_ok), None
    except FileNotFoundError as e:
        return None, str(e)


_backend, _err = load_backend()
if _err is not None:
    st.error("**Build artifacts are missing — the model can't load.**\n\n"
             f"```\n{_err}\n```\n\nBuild them first (README → *Setup*):\n\n```bash\nbash scripts/bootstrap.sh\n```")
    st.stop()
data, deltas, rung1_ok = _backend

st.title("AI Automation — Fiscal Consequences")
sb = st.sidebar
engine = sb.radio("Engine", ["v2 — multi-actor (feedbacks)", "v1 — static kernel"], index=0)
is_v2 = engine.startswith("v2")
st.caption("Set the levers; the accounting is the point. Watch the tax base migrate from **labor** to "
           "**capital**, revenue fall faster than employment, and — unlike Washington — **states must "
           "balance**, so they hike rates until they can't, then cut. "
           + ("**v2** adds the firm's disposition of saved wages, survivor raises, and the second-round "
              "demand spiral." if is_v2 else "**v1** is the static per-worker kernel."))

# ----------------------------------------------------------------- shared scenario levers
sb.header("Automation scenario")
cog = sb.slider("Cognitive feasibility (AI capability)", 0.0, 1.0, 0.70, 0.05)
phys = sb.slider("Robotics feasibility (physical work)", 0.0, 1.0, 0.20, 0.05)
robotics_lag = sb.slider("Robotics capacity build-out lag (years)", 0, 15, 4, 1,
                         help="Physical automation needs AI-driven industrial capacity: the robot channel "
                              "ramps linearly from 0 to full feasibility over this many years (0 = "
                              "capacity exists from day one). v2 only.")
adopt0 = sb.slider("Automated by year 1 — % of feasible work", 0.0, 1.0, 0.10, 0.05)
adopt1 = sb.slider("Automated by the final year — % of feasible work", 0.0, 1.0, 0.60, 0.05,
                   help="A cumulative diffusion CEILING: the automated stock reaches feasibility × this "
                        "share by the horizon (an S-curve), so 0.6 ≈ 60% of the feasibly-automatable jobs "
                        "are automated by the end — not a compounding per-year rate.")
n_periods = sb.slider("Horizon (years)", 3, 30, 10)
mapping = sb.selectbox("Exposure → share mapping", ["percentile", "logistic"])
adoption_path = list(np.linspace(adopt0, adopt1, n_periods))

sb.header("Labor market")
reab = sb.slider("Reabsorption rate / yr  (0 = the thesis)", 0.0, 1.0, 0.0, 0.05)
haircut = sb.slider("Re-employment wage cut (haircut)", 0.0, 1.0, 0.30, 0.05,
                    help="The reabsorbed re-emerge at (1−haircut)×origin wage, floored at a state service "
                         "wage. 0 = full-wage recovery (fiscally whole); a bigger cut drops the household "
                         "toward EITC/SNAP/Medicaid eligibility.")
ui_weeks = sb.slider("UI duration (weeks)", 0, 52, 26)
interest = sb.slider("Interest rate on federal debt", 0.0, 0.10, 0.03, 0.005)
ubi = sb.slider("UBI per worker / yr ($)", 0, 30_000, 0, 1_000)

if not is_v2:
    # -------------------------------------------------- v1 path (unchanged thesis demo) --------------
    sb.header("Offsets — steelman the optimistic case")
    corp_scale = sb.slider("Corporate-tax recapture ×", 0.0, 2.0, 1.0, 0.1)
    cons_scale = sb.slider("Consumption channel ×", 0.0, 2.0, 1.0, 0.1)
    demand = sb.slider("Second-round demand multiplier", 0.0, 1.0, 0.0, 0.05)
    state_resp = sb.selectbox("State budget response", ["mix", "cut_spending", "raise_rates"])
    lp = levers.LeverParams(exposure_mapping=mapping, cognitive_feasibility=cog,
                            physical_feasibility=phys, adoption=1.0)
    dp = DynamicsParams(n_periods=n_periods, ui_weeks=ui_weeks, reabsorption_rate=reab,
                        reemployment_haircut=haircut, demand_multiplier=demand, state_response=state_resp,
                        interest_rate=interest, adoption_path=adoption_path, ubi_annual=ubi,
                        corp_offset_scale=corp_scale, consumption_scale=cons_scale)
    res = DynamicModel(data, deltas, lp, dp).run()
    final = res.iloc[-1]
    c = st.columns(5)
    c[0].metric("Employment", f"−{final['employment_drop_pct']:.0f}%")
    c[1].metric("Labor revenue", f"−{final['revenue_lost_pct']:.0f}%")
    c[2].metric("Federal deficit (final yr)", f"${final['fed_deficit_B']:,.0f}B")
    c[3].metric("Federal debt (cumulative)", f"${final['fed_debt_B']:,.0f}B")
    c[4].metric("State gap (must close/yr)", f"${final['state_gap_B']:,.0f}B")
    left, right = st.columns(2)
    with left:
        st.subheader("Revenue falls faster than employment")
        st.line_chart(res.set_index("period")[["employment_drop_pct", "revenue_lost_pct"]])
        st.subheader("Federal deficit & cumulative debt ($B)")
        st.line_chart(res.set_index("period")[["fed_deficit_B", "fed_debt_B"]])
    with right:
        st.subheader("Cost → offset → net (federal+state, by year, $B)")
        st.bar_chart(pd.DataFrame({"revenue lost": res["revenue_lost_B"],
                                   "transfers + UI": res["transfers_added_B"],
                                   "− capital recapture": -res["corp_offset_B"]}, index=res["period"]))
        st.subheader("State budget gap — must be closed ($B/yr)")
        st.line_chart(res.set_index("period")[["state_gap_B"]])
    with st.expander("Per-year detail"):
        st.dataframe(res.style.format("{:,.1f}"), use_container_width=True)
    st.stop()

# -------------------------------------------------- v2 path (multi-actor) ----------------------------
sb.header("① Firm disposition of saved wages")
retained = sb.slider("→ Retained profit (share of net saving)", 0.0, 1.0, 0.6, 0.05)
price_max = round(1.0 - retained, 2)
if price_max > 0:
    price = sb.slider("→ Price reduction (share)", 0.0, price_max, min(0.2, price_max), 0.05)
else:
    price = 0.0                                              # retained = 100% → no room for price/survivor
survivor_share = max(0.0, 1.0 - retained - price)
sb.caption(f"→ **Survivor raises**: {survivor_share:.0%} (the remainder)")
auto_cost = sb.slider("Cost of automation (fraction of comp → compute)", 0.0, 1.0, 0.10, 0.05)
compute_rate = sb.slider("Compute pool — effective tax rate", 0.0, 0.4, 0.10, 0.01)

sb.header("② Survivor wages  [A]")
survivor_unbounded = sb.checkbox("Unbounded raise (optimistic)", value=False)
ceiling = sb.slider("Raise ceiling (× baseline wage)", 1.0, 3.0, 1.5, 0.1, disabled=survivor_unbounded)
elasticity = sb.slider("Market wage elasticity to slack (− substitute / + complement)", -0.5, 0.5, -0.15, 0.05)
spillover = sb.slider("Un-absorbable raise → profit (vs price)", 0.0, 1.0, 0.5, 0.05)

sb.header("③ Macro feedback")
price_pt = sb.slider("Price pass-through (deflation → real/%-GDP only)", 0.0, 1.0, 0.3, 0.05)
prod_pt = sb.slider("Productivity dividend (full automation → +this share of GDP)", 0.0, 1.0, 0.30, 0.05,
                    help="Output-weighted: automation of the high-value work first. Grows real GDP, so "
                         "it cushions the deficit as a share of GDP (switch the denominator below to see it).")
growth = sb.slider("Baseline trend growth (nominal, %-GDP denominators)", 0.0, 0.08, 0.04, 0.005,
                   help="≈2% real + 2% inflation. Grows the GDP denominator over time so debt/GDP is "
                        "honest at long horizons; nominal dollar columns are unchanged.")

sb.header("④ Government & demand  [H]")
rung = 1 if rung1_ok else 0
if not rung1_ok:
    sb.warning("Benefit-lookup / NOC artifacts absent — reabsorption falls back to the flat-haircut model.")
lfp_exit = sb.slider("LFP exit / SSDI rate (of exhausted)", 0.0, 0.2, 0.03, 0.01)
attrition = sb.slider("Natural attrition of long-term unemployed / yr", 0.0, 0.1, 0.025, 0.005,
                      help="Retirement / mortality / discouragement — so the exhausted don't sit forever.")
atx_max = max(0.01, round(min(0.30, retained * (1.0 - auto_cost)), 2))   # paid from retained profit
automation_tax = sb.slider("Automation (robot) tax — share of the automated comp bill", 0.0, atx_max,
                           min(0.07, atx_max), 0.01,
                           help="The government response: a federal levy on the automated jobs' saved "
                                "compensation, PAID from retained profit (corp-deductible) — so the max is "
                                "bounded by the profit share. Watch it pull the deficit back.")
ubi_recapture = sb.slider("UBI recapture (tax clawback + benefit crowd-out)", 0.0, 0.6, 0.25, 0.05,
                          help="Share of the UBI outlay the government gets back — income-tax clawback "
                               "plus means-tested benefits the UBI displaces (~20–30% in practice).")
demand = sb.slider("Second-round demand multiplier", 0.0, 1.0, 0.5, 0.05,
                   help="Okun-style LEVEL multiplier: the induced-layoff stock tracks the standing net "
                        "demand shortfall — UBI/raises visibly stabilize; austerity/wage cuts deepen it.")
state_resp = sb.selectbox("State budget response", ["mix", "raise_rates", "cut_spending"])
state_cut_share = sb.slider("Of the gap, share closed by spending cuts (mix)", 0.0, 1.0, 0.0, 0.05)
rate_cap = sb.slider("Max feasible rate hike (× base)", 0.1, 3.0, 1.0, 0.1)
denominator = sb.radio("Headline denominator", ["absolute", "pct_gdp"], horizontal=True,
                       help="Switch to % of GDP to see the productivity dividend and price channel move the headline.")

ui = dict(mapping=mapping, cog=cog, phys=phys, robotics_lag=float(robotics_lag),
          adoption_path=adoption_path, n_periods=n_periods,
          retained_profit_share=retained, price_reduction_share=price, auto_cost=auto_cost,
          offshore_share=0.0, compute_effective_rate=compute_rate, survivor_unbounded=survivor_unbounded,
          survivor_raise_ceiling=ceiling, survivor_elasticity=elasticity,
          survivor_spillover_to_profit=spillover, reabsorption_rung=rung, reab=reab, haircut=haircut,
          lfp_exit_rate=lfp_exit, attrition_rate=attrition, ui_weeks=ui_weeks, price_passthrough=price_pt,
          productivity_passthrough=prod_pt, demand=demand, state_resp=state_resp,
          state_cut_share=state_cut_share, state_rate_hike_cap=rate_cap, automation_tax_rate=automation_tax,
          interest=interest, ubi=ubi, ubi_recapture_rate=ubi_recapture, baseline_growth_rate=growth,
          denominator=denominator)
res = DynamicModelV2(data, deltas, build_v2_params(ui)).run()
final = res.iloc[-1]

# ----------------------------------------------------------------- v2 headline
c = st.columns(5)
c[0].metric("Employment", f"−{final['employment_drop_pct']:.0f}%")
if denominator == "pct_gdp":
    c[1].metric("Federal deficit (final yr)", f"{final['fed_deficit_abs_pct_gdp']:.1f}% GDP")
else:
    c[1].metric("Federal deficit (absolute)", f"${final['fed_deficit_abs_B']:,.0f}B")
c[2].metric("Federal debt (Δ cumulative)", f"${final['fed_debt_B']:,.0f}B")
c[3].metric("State gap (must close/yr)", f"${final['state_gap_B']:,.0f}B",
            help="Closed by rate hikes until the cap binds, then forced spending cuts.")
c[4].metric("States hitting rate cap", f"{int(final['n_states_capped'])} / 51")

left, right = st.columns(2)
with left:
    st.subheader("Where the workforce goes (millions)")
    st.area_chart(res.set_index("period")[["employed_M", "on_ui_M", "exhausted_M", "reabsorbed_M",
                                            "exited_M", "induced_M", "retired_M"]])
    st.subheader("Federal deficit — absolute, on the real 2024 base ($B)")
    st.line_chart(res.set_index("period")[["fed_deficit_abs_B", "fed_revenue_B"]])
    st.subheader("Firm disposition of the saved wage bill ($B)")
    st.bar_chart(res.set_index("period")[["retained_profit_B", "price_reduction_B", "survivor_gains_B",
                                          "automation_spend_B"]])
with right:
    st.subheader("The asymmetric amplifier — how states close the gap ($B)")
    st.bar_chart(res.set_index("period")[["state_rate_hike_B", "state_spending_cut_B"]])
    st.subheader("Second-round demand spiral — induced layoffs (millions)")
    st.line_chart(res.set_index("period")[["induced_M"]])
    st.subheader("Survivor wage channel — index & net tax effect")
    st.line_chart(res.set_index("period")[["W_survivor"]])
    st.line_chart(res.set_index("period")[["survivor_gain_fed_B", "survivor_wage_cost_B"]])

if ubi > 0 and final["ubi_required_rate"] > 1.0:
    st.warning(f"A \\${ubi:,}/yr UBI needs a **{final['ubi_required_rate']:.0%}** average rate on the eroded "
               "base by the final year — **>100% is unfundable**.")

with st.expander("Per-year detail (v2 columns)"):
    st.dataframe(res.style.format("{:,.2f}"), use_container_width=True)
with st.expander("Method — what v2 adds over v1"):
    st.markdown(
        "- **Disposition router**: the saved wage bill is split (profit / price / survivor raises / "
        "compute spend); corporate is computed once here (the XOR), and compute migrates to a low-tax, "
        "partly-offshore pool — the mechanical heart of base migration.\n"
        "- **Survivor wages [A]**: the still-employed majority's wage scales with a capacity-checked "
        "mechanical raise (capped; the overflow spills to profit/price) plus a market response to slack. "
        "The standing raise is netted against the corporate base (no double count).\n"
        "- **Government [H]**: states compose their ledger and **balance within-year** — rate hikes until "
        "the feasibility cap binds, then forced spending cuts; the austerity feeds the demand spiral.\n"
        "- **Lagged demand**: the contraction re-enters next period as a C1-guarded layoff flow (a 6th "
        "worker state), not a fiscal fudge.\n"
        "- **Absolute ledger**: the headline rides the real 2024 base-linkage totals, not a synthetic one.\n"
        "- v2 reduces **bit-for-bit to v1** when every behavioral lever is off (the C8 anchor).")
