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

import math
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # project root -> import fiscal_model

import numpy as np
import pandas as pd
import streamlit as st

from fiscal_model import loaders, levers, reabsorption
from fiscal_model import presets as presets_mod
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

# ----------------------------------------------------------------- scenario presets (v2 only)
# Loading mechanism: NO sidebar widget passes key=, so streamlit hashes each widget's identity from
# its parameters (label/min/max/value/step/help). Swapping a widget's value= default when the preset
# changes therefore RESETS it to the preset value, while user tweaks persist as long as the preset
# stays put. DO NOT add a static key= to these widgets — with a user key the identity shrinks to
# min/max/step and preset loading silently stops working. Known limit: if two presets share a
# widget's default, switching between them does not clear a tweak on that widget — the "modified
# from preset" caption (main area) is the honest surface for that.
_CUSTOM_DEFAULTS = dict(cog=0.70, phys=0.20, robotics_lag=4, adopt0=0.10, adopt1=0.60, n_periods=10,
                        reab=0.0, haircut=0.30, ui_weeks=26, interest=0.03, ubi=0,
                        retained=0.6, price=0.2, auto_cost=0.10, compute_rate=0.10,
                        unbounded=False, ceiling=1.5, elasticity=-0.15, spillover=0.5,
                        price_pt=0.3, prod_pt=0.30, growth=0.04, lfp=0.03, attrition=0.025,
                        atax=0.0, ubi_recapture=0.25, demand=0.5,
                        state_resp="mix", state_cut=0.0, rate_cap=1.0)


def preset_widget_defaults(preset) -> dict:
    """Widget defaults derived from to_params(preset) — presets.py stays the single source of truth."""
    p = presets_mod.to_params(preset)
    return dict(cog=p.cognitive_feasibility, phys=p.physical_feasibility,
                robotics_lag=int(p.robotics_lag), adopt0=preset.adoption_start,
                adopt1=preset.adoption_end, n_periods=p.n_periods,
                reab=p.reabsorption_rate, haircut=p.reemployment_haircut, ui_weeks=p.ui_weeks,
                interest=p.interest_rate, ubi=int(p.ubi_annual),
                retained=p.retained_profit_share, price=p.price_reduction_share,
                auto_cost=p.auto_cost, compute_rate=p.compute_effective_rate,
                unbounded=math.isinf(p.survivor_raise_ceiling),
                ceiling=p.survivor_raise_ceiling if math.isfinite(p.survivor_raise_ceiling) else 1.5,
                elasticity=p.survivor_elasticity, spillover=p.survivor_spillover_to_profit,
                price_pt=p.price_passthrough, prod_pt=p.productivity_passthrough,
                growth=p.baseline_growth_rate, lfp=p.lfp_exit_rate, attrition=p.attrition_rate,
                atax=p.automation_tax_rate, ubi_recapture=p.ubi_recapture_rate,
                demand=p.demand_multiplier, state_resp=p.state_response,
                state_cut=p.state_cut_share, rate_cap=p.state_rate_hike_cap)


_preset = None
overlay_keys: list = []
if is_v2:
    _names = {p.name: k for k, p in presets_mod.PRESETS.items()}
    _choice = sb.selectbox("Scenario preset", ["Custom"] + list(_names),
                           help="Literature-anchored world states (docs/PRESET_EVIDENCE.md). "
                                "Selecting one loads its levers into the sliders below; tweak from "
                                "there. Government policy (robot tax, UBI, compute taxation) "
                                "composes separately as overlays.")
    if _choice != "Custom":
        _preset = presets_mod.PRESETS[_names[_choice]]
        sb.caption(_preset.blurb + ("" if rung1_ok else " ⚠️ Presets are calibrated to the "
                                    "service-floor reabsorption engine — artifacts absent, running "
                                    "the flat-haircut fallback degrades their fidelity."))
    overlay_keys = sb.multiselect(
        "Policy overlays", list(presets_mod.OVERLAYS),
        format_func=lambda k: presets_mod.OVERLAYS[k].name,
        help="Applied ON TOP of the sliders, after everything else — they OVERRIDE the "
             "corresponding levers (captions below show exactly what was set).")
    if all(k in overlay_keys for k in ("cw-robot-tax", "grt-robot-tax")):
        sb.warning("Both robot taxes set the same lever — using Costinot-Werning, dropping GRT.")
        overlay_keys.remove("grt-robot-tax")

d = preset_widget_defaults(_preset) if _preset is not None else _CUSTOM_DEFAULTS
st.caption("Set the levers; the accounting is the point. Watch the tax base migrate from **labor** to "
           "**capital**, revenue fall faster than employment, and — unlike Washington — **states must "
           "balance**, so they hike rates until they can't, then cut. "
           + ("**v2** adds the firm's disposition of saved wages, survivor raises, and the second-round "
              "demand spiral." if is_v2 else "**v1** is the static per-worker kernel."))

# ----------------------------------------------------------------- shared scenario levers
sb.header("Automation scenario")
cog = sb.slider("Cognitive feasibility (AI capability)", 0.0, 1.0, d["cog"], 0.05)
phys = sb.slider("Robotics feasibility (physical work)", 0.0, 1.0, d["phys"], 0.05)
robotics_lag = sb.slider("Robotics capacity build-out lag (years)", 0, 15, d["robotics_lag"], 1,
                         help="Physical automation needs AI-driven industrial capacity: the robot channel "
                              "ramps linearly from 0 to full feasibility over this many years (0 = "
                              "capacity exists from day one). v2 only.")
adopt0 = sb.slider("Automated by year 1 — % of feasible work", 0.0, 1.0, d["adopt0"], 0.01)
adopt1 = sb.slider("Automated by the final year — % of feasible work", 0.0, 1.0, d["adopt1"], 0.01,
                   help="A cumulative diffusion CEILING: the automated stock reaches feasibility × this "
                        "share by the horizon (an S-curve), so 0.6 ≈ 60% of the feasibly-automatable jobs "
                        "are automated by the end — not a compounding per-year rate.")
n_periods = sb.slider("Horizon (years)", 3, 30, d["n_periods"])
mapping = sb.selectbox("Exposure → share mapping", ["percentile", "logistic"])
# The kinked preset path survives horizon changes (it is parametric), but moving the adoption
# sliders reverts to a linear ramp. isclose, not ==: the frontend returns min+k·step in JS doubles.
if (_preset is not None and _preset.adoption_reach_year is not None
        and math.isclose(adopt0, _preset.adoption_start, abs_tol=0.004)
        and math.isclose(adopt1, _preset.adoption_end, abs_tol=0.004)):
    adoption_path = presets_mod.build_adoption_path(_preset, n_periods)
else:
    adoption_path = list(np.linspace(adopt0, adopt1, n_periods))
    if _preset is not None and _preset.adoption_reach_year is not None:
        sb.caption(f"⚠️ Adoption sliders moved — the preset's kinked path (full automation at year "
                   f"{_preset.adoption_reach_year}) was replaced by a linear ramp.")

sb.header("Labor market")
reab = sb.slider("Reabsorption rate / yr  (0 = the thesis)", 0.0, 1.0, d["reab"], 0.025)
haircut = sb.slider("Re-employment wage cut (haircut)", 0.0, 1.0, d["haircut"], 0.01,
                    help="The reabsorbed re-emerge at (1−haircut)×origin wage, floored at a state service "
                         "wage. 0 = full-wage recovery (fiscally whole); a bigger cut drops the household "
                         "toward EITC/SNAP/Medicaid eligibility.")
ui_weeks = sb.slider("UI duration (weeks)", 0, 52, d["ui_weeks"])
interest = sb.slider("Interest rate on federal debt", 0.0, 0.10, d["interest"], 0.005)
ubi = sb.slider("UBI per worker / yr ($)", 0, 30_000, d["ubi"], 1_000)

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
retained = sb.slider("→ Retained profit (share of net saving)", 0.0, 1.0, d["retained"], 0.05)
price_max = round(1.0 - retained, 2)
if price_max > 0:
    # min() keeps a preset's default legal after the user raises `retained` past it (e.g. Windfall
    # loads price=0.50; retained dragged to 0.80 would otherwise put value > max and crash).
    price = sb.slider("→ Price reduction (share)", 0.0, price_max, min(d["price"], price_max), 0.05)
else:
    price = 0.0                                              # retained = 100% → no room for price/survivor
survivor_share = max(0.0, 1.0 - retained - price)
sb.caption(f"→ **Survivor raises**: {survivor_share:.0%} (the remainder)")
auto_cost = sb.slider("Cost of automation (fraction of comp → compute)", 0.0, 1.0, d["auto_cost"], 0.05)
compute_rate = sb.slider("Compute pool — effective tax rate", 0.0, 0.4, d["compute_rate"], 0.01)

sb.header("② Survivor wages  [A]")
survivor_unbounded = sb.checkbox("Unbounded raise (optimistic)", value=d["unbounded"])
ceiling = sb.slider("Raise ceiling (× baseline wage)", 1.0, 3.0, d["ceiling"], 0.1,
                    disabled=survivor_unbounded)
elasticity = sb.slider("Market wage elasticity to slack (− substitute / + complement)", -0.5, 0.5,
                       d["elasticity"], 0.05)
spillover = sb.slider("Un-absorbable raise → profit (vs price)", 0.0, 1.0, d["spillover"], 0.05)

sb.header("③ Macro feedback")
price_pt = sb.slider("Price pass-through (deflation → real/%-GDP only)", 0.0, 1.0, d["price_pt"], 0.05)
prod_pt = sb.slider("Productivity dividend (full automation → +this share of GDP)", 0.0, 1.0,
                    d["prod_pt"], 0.05,
                    help="Output-weighted: automation of the high-value work first. Grows real GDP, so "
                         "it cushions the deficit as a share of GDP (switch the denominator below to see it).")
growth = sb.slider("Baseline trend growth (nominal, %-GDP denominators)", 0.0, 0.08, d["growth"], 0.005,
                   help="≈2% real + 2% inflation. Grows the GDP denominator over time so debt/GDP is "
                        "honest at long horizons; nominal dollar columns are unchanged.")

sb.header("④ Government & demand  [H]")
rung = 1 if rung1_ok else 0
if not rung1_ok:
    sb.warning("Benefit-lookup / NOC artifacts absent — reabsorption falls back to the flat-haircut model.")
lfp_exit = sb.slider("LFP exit / SSDI rate (of exhausted)", 0.0, 0.2, d["lfp"], 0.01)
attrition = sb.slider("Natural attrition of long-term unemployed / yr", 0.0, 0.1, d["attrition"], 0.005,
                      help="Retirement / mortality / discouragement — so the exhausted don't sit forever.")
# The robot tax is paid from retained profit, so its feasible max is retained·(1−auto_cost). When that
# bound collapses (e.g. auto_cost → 1: automation costs eat the whole saved bill), there is no profit to
# tax — force 0 instead of crashing the fail-loud model assert (user-reported at auto_cost=1).
atx_bound = round(min(0.30, retained * (1.0 - auto_cost)), 2)
if atx_bound < 0.01:
    automation_tax = 0.0
    sb.caption("Automation tax: **0%** — no retained profit left to pay it "
               "(retained × (1−auto cost) ≈ 0).")
else:
    automation_tax = sb.slider("Automation (robot) tax — share of the automated comp bill", 0.0, atx_bound,
                               min(d["atax"], atx_bound), 0.01,
                               help="A federal levy on the automated jobs' saved compensation, PAID from "
                                    "retained profit (corp-deductible) — so the max is bounded by the "
                                    "profit share. Ships at 0: the literature-anchored rates live in the "
                                    "policy overlays above (Costinot-Werning ≈ 0.3–1%, not 7%).")
ubi_recapture = sb.slider("UBI recapture (tax clawback + benefit crowd-out)", 0.0, 0.6,
                          d["ubi_recapture"], 0.05,
                          help="Share of the UBI outlay the government gets back — income-tax clawback "
                               "plus means-tested benefits the UBI displaces (~20–30% in practice).")
demand = sb.slider("Second-round demand multiplier", 0.0, 2.0, d["demand"], 0.05,
                   help="Okun-style LEVEL multiplier: the induced-layoff stock tracks the standing net "
                        "demand shortfall — UBI/raises visibly stabilize; austerity/wage cuts deepen it. "
                        "0.5 ≈ an active Fed offsetting half; 1.8 = Chodorow-Reich's no-offset multiplier.")
_sr_opts = ["mix", "raise_rates", "cut_spending"]
state_resp = sb.selectbox("State budget response", _sr_opts, index=_sr_opts.index(d["state_resp"]))
state_cut_share = sb.slider("Of the gap, share closed by spending cuts (mix)", 0.0, 1.0,
                            d["state_cut"], 0.05)
rate_cap = sb.slider("Max feasible rate hike (× base)", 0.1, 3.0, d["rate_cap"], 0.1)
denominator = sb.radio("Headline denominator", ["absolute", "pct_gdp"], horizontal=True,
                       help="Switch to % of GDP to see the productivity dividend and price channel move the headline.")

# assumptions export (mirrors the ai-shock pattern: a timestamped, reload-able lever snapshot)
import dataclasses as _dc
import datetime as _dt
import json as _json

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
# Overlays apply AFTER the sliders and OVERRIDE the corresponding levers; v2p is the single source
# of truth for every consumer below (model run, JSON export, MC base, UBI warning).
v2p, _overlay_notes = presets_mod.apply_overlays(build_v2_params(ui), overlay_keys)
for _note in _overlay_notes:
    sb.caption("🏛 " + _note)
res = DynamicModelV2(data, deltas, v2p).run()
sb.download_button("⬇ Export assumptions (JSON)",
                   _json.dumps({"engine": "v2",
                                "preset": _preset.key if _preset is not None else "custom",
                                "overlays": overlay_keys,
                                "exportedAt": _dt.datetime.now().isoformat(timespec="seconds"),
                                "levers": _dc.asdict(v2p)}, indent=1),
                   "assumptions.json", "application/json")
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

if _preset is not None:
    # deviation check on the preset-controlled fields only; isclose absorbs JS-double slider echoes
    _pp = presets_mod.to_params(_preset, n_periods=ui["n_periods"])
    _ui_p = build_v2_params(ui)

    def _differs(a, b):
        if isinstance(a, list) and isinstance(b, list):
            return not np.allclose(np.asarray(a, float), np.asarray(b, float), atol=1e-9)
        if isinstance(a, float) or isinstance(b, float):
            return not math.isclose(float(a), float(b), abs_tol=1e-6)
        return a != b

    _mods = [f for f in sorted(set(_preset.overrides) | {"adoption_path"})
             if _differs(getattr(_ui_p, f), getattr(_pp, f))]
    if _mods:
        st.caption("⚠️ sliders modified from the preset: " + ", ".join(f"`{f}`" for f in _mods))
    with st.expander(f"Preset provenance — {_preset.name}"):
        st.caption("Anchors from `docs/PRESET_EVIDENCE.md` — every number fetch-verified against "
                   "the cited paper (verbatim quotes + URLs in `docs/research/preset-evidence-raw.json`).")
        for _fld, _src in _preset.provenance.items():
            _val = getattr(_pp, _fld, None)
            st.markdown(f"- **{_fld}**{f' = `{_val:g}`' if isinstance(_val, float) else ''} — {_src}")

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

if v2p.ubi_annual > 0 and final["ubi_required_rate"] > 1.0:   # v2p, not the slider: overlays add UBI too
    st.warning(f"A \\${v2p.ubi_annual:,.0f}/yr UBI needs a **{final['ubi_required_rate']:.0%}** average rate "
               "on the eroded base by the final year — **>100% is unfundable**.")

# -------------------------------------------------- Fiscal summary table ----------------------------
st.subheader("Fiscal summary")
from fiscal_model import summary as summary_mod
from fiscal_model.government import RevenueLedger

fs1, fs2 = st.columns(2)
fs_group = fs1.radio("Group", ["By tax category", "By fiscal channel"], horizontal=True)
fs_units = fs2.radio("Units", ["$B", "% of baseline revenue"], horizontal=True)
_ledger = RevenueLedger(data)
fs_df = summary_mod.build_fiscal_summary(
    res, _ledger,
    grouping="tax" if fs_group == "By tax category" else "channel",
    units="busd" if fs_units == "$B" else "pct_baseline")
st.caption("Revenue lines are signed revenue **changes** (negative = lost revenue); outlay lines are "
           "spending changes (positive = more spending); **Net fiscal impact = −deficit change** "
           "(negative = worse). Flows sum into *Total*; levels show the final year. Memo rows document "
           "untaxed magnitudes (offshore leakage, consumer surplus) and are excluded from nets."
           + (" Channels follow the labour→capital / resident→non-resident / consumer-surplus / "
              "spending decomposition." if fs_group == "By fiscal channel" else ""))
_year_cols = [c for c in fs_df.columns if c.startswith("Year ")] + ["Total"]
_disp = fs_df.drop(columns="kind").set_index(["group", "label"])
_emph = fs_df["kind"].isin(["subtotal", "net"]).to_numpy()
styler = (_disp.style.format("{:,.1f}")
          .apply(lambda s: np.where(_emph, "font-weight: bold; background-color: rgba(128,128,128,0.15)",
                                    ""), axis=0)
          .map(lambda v: "color: #e4572e" if isinstance(v, float) and v < -0.05 else
                         ("color: #3fa34d" if isinstance(v, float) and v > 0.05 else ""),
               subset=_year_cols))
st.dataframe(styler, use_container_width=True)
st.download_button("⬇ Summary CSV", summary_mod.to_csv_bytes(fs_df), "fiscal-summary.csv", "text/csv")

# -------------------------------------------------- Uncertainty (Monte Carlo) -----------------------
with st.expander("Uncertainty (Monte Carlo) — bands + which levers matter"):
    import altair as alt
    from fiscal_model import mc as mc_mod

    st.caption("Samples N slightly-perturbed lever settings around YOUR configuration (seeded, "
               "constraint-aware; levers that are off stay off) and re-runs the model. Fan = P10–P90 and "
               "P25–P75 bands with the median and your base run; tornado = Spearman rank correlation of "
               "each varied lever with the final-year outcome. Note: mpc/stickiness sensitivity reflects "
               "only their live paths (demand, state close, reabsorption) — the cached displaced-worker "
               "consumption channel stays at bake-time values.")
    mc1, mc2, mc3 = st.columns(3)
    mc_n = mc1.slider("Draws (N)", 100, 1000, 300, 50)
    mc_spread = mc2.slider("Spread (relative 1σ, ±2σ truncated)", 0.05, 0.30, 0.15, 0.01)
    mc_seed = mc3.number_input("Seed", 0, 9999, 0)

    base_v2p = v2p          # the FINAL params: preset + slider tweaks + overlays

    @st.cache_resource
    def get_mc_context(base_repr, _data, _deltas, _base):
        # Keyed on the FULL base repr: presets/overlays change PERTURBED fields, which are not in
        # mc.FROZEN — a frozen-only key would silently return a context centered on a stale base.
        return mc_mod.ScenarioContext(_data, _deltas, _base)

    mc_key = (repr(base_v2p), mc_n, mc_spread, int(mc_seed))
    if st.button("Run Monte Carlo", type="primary"):
        ctx = get_mc_context(repr(base_v2p), data, deltas, base_v2p)
        bar = st.progress(0.0, text="running draws…")
        result = mc_mod.run_mc(ctx, n=mc_n, spread=mc_spread, seed=int(mc_seed),
                               progress=lambda i, n: bar.progress(i / n, text=f"draw {i}/{n}"))
        bar.empty()
        st.session_state["mc"] = {"key": mc_key, "result": result}

    if "mc" in st.session_state:
        if st.session_state["mc"]["key"] != mc_key:
            st.caption("⚠️ results below are for a previous setting — press *Run Monte Carlo* to refresh.")
        r: mc_mod.MCResult = st.session_state["mc"]["result"]

        METRICS = {"Federal deficit ($B)": "fed_deficit_B", "Federal debt ($B)": "fed_debt_B",
                   "Deficit (% GDP, absolute)": "fed_deficit_abs_pct_gdp",
                   "Employment drop (%)": "employment_drop_pct", "State gap ($B)": "state_gap_B",
                   "Induced layoffs (M)": "induced_M"}
        m_label = st.radio("Metric", list(METRICS), horizontal=True)
        mcol = METRICS[m_label]
        wide = (r.percentiles.query("metric == @mcol")
                .pivot(index="period", columns="pct", values="value").reset_index()
                .rename(columns={p: f"p{p}" for p in mc_mod.PCTS}))
        wide["base"] = r.base_run[mcol].to_numpy()
        outer = alt.Chart(wide).mark_area(opacity=0.22).encode(
            x=alt.X("period:Q", title="year"), y=alt.Y("p10:Q", title=m_label), y2="p90:Q")
        inner = alt.Chart(wide).mark_area(opacity=0.35).encode(x="period:Q", y="p25:Q", y2="p75:Q")
        med = alt.Chart(wide).mark_line(strokeWidth=2).encode(x="period:Q", y="p50:Q")
        base_ln = alt.Chart(wide).mark_line(strokeDash=[6, 3], color="white").encode(
            x="period:Q", y="base:Q")
        st.altair_chart((outer + inner + med + base_ln).properties(height=320),
                        use_container_width=True)

        t_label = st.radio("Tornado target", ["Final deficit", "Final employment drop"], horizontal=True)
        target = ("final_fed_deficit_B" if t_label == "Final deficit"
                  else "final_employment_drop_pct")
        t = r.tornado.query("target == @target").head(15)
        order = t["lever"].tolist()
        st.altair_chart(
            alt.Chart(t).mark_bar().encode(
                x=alt.X("spearman:Q", title=f"Spearman ρ vs {t_label.lower()}"),
                y=alt.Y("lever:N", sort=order, title=None),
                color=alt.condition("datum.spearman > 0", alt.value("#e4572e"), alt.value("#4c9be8")),
            ).properties(height=24 * len(t) + 20),
            use_container_width=True)

with st.expander("Per-year detail (v2 columns)"):
    st.dataframe(res.style.format("{:,.2f}"), use_container_width=True)
    st.download_button("⬇ Full detail CSV", res.to_csv(index=False).encode("utf-8"),
                       "run-detail.csv", "text/csv")
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
