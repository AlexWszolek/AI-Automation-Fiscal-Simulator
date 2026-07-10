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

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from fiscal_model import charts as charts_mod
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
        baseline_growth_rate=ui["baseline_growth_rate"], denominator=ui["denominator"],
        income_tax_mult=ui["income_tax_mult"], corp_tax_mult=ui["corp_tax_mult"],
        cons_tax_mult=ui["cons_tax_mult"])


# ----------------------------------------------------------------- chart layer (static, labeled)
# All charts are explicit altair specs rendered with theme=None and WITHOUT .interactive() —
# no zoom, no pan, no tooltips. Series names go through LABELS so no raw column name ever
# reaches a legend. Palette mirrors the report figures (colorblind-aware).
PALETTE = ["#3b6ea5", "#d9a441", "#4e937a", "#b3554d", "#7d6ca3", "#6b7b8c", "#a98467"]
NEG, POS = "#b3554d", "#4e937a"

LABELS = {
    "employed_M": "Employed", "on_ui_M": "On unemployment insurance",
    "exhausted_M": "Exhausted UI (no benefits)", "reabsorbed_M": "Re-employed at lower wage",
    "exited_M": "Left labor force (SSDI)", "induced_M": "Laid off by demand shortfall",
    "retired_M": "Retired (natural attrition)",
    "fed_deficit_abs_B": "Federal deficit (absolute)", "fed_revenue_B": "Federal revenue",
    "fed_deficit_B": "Federal deficit change", "fed_debt_B": "Federal debt change (cumulative)",
    "retained_profit_B": "Kept as profit", "price_reduction_B": "Passed to consumer prices",
    "survivor_gains_B": "Paid as raises to remaining staff",
    "automation_spend_B": "Spent on compute & automation",
    "state_rate_hike_B": "Closed by tax-rate increases",
    "state_spending_cut_B": "Closed by spending cuts",
    "state_gap_B": "Shortfall that year", "state_gap_cum_B": "Accumulated shortfall",
    "W_survivor": "Wage index of the still-employed (1.0 = baseline)",
    "survivor_gain_fed_B": "Extra federal tax from raises",
    "survivor_wage_cost_B": "What the raises cost firms",
    "employment_drop_pct": "Employment decline", "revenue_lost_pct": "Labor-tax revenue decline",
}


def ts_chart(df: pd.DataFrame, cols: list, y_title: str, kind: str = "line",
             stack: bool | str | None = None, height: int = 260) -> alt.Chart:
    """A static time-series chart: rows = periods, one colored series per column in `cols`."""
    labels = [LABELS.get(c, c) for c in cols]
    long = df[["period"] + cols].melt("period", var_name="series", value_name="value")
    long["series"] = long["series"].map({c: LABELS.get(c, c) for c in cols})
    mark = {"line": alt.Chart(long).mark_line(strokeWidth=2.5),
            "area": alt.Chart(long).mark_area(opacity=0.85),
            "bar": alt.Chart(long).mark_bar()}[kind]
    # legend below the plot, never truncated: labelLimit=0 disables label clipping; column count
    # adapts so long labels wrap into rows instead of running off the container edge
    legend = alt.Legend(orient="bottom", columns=1 if len(labels) <= 2 else 2,
                        labelLimit=0, symbolLimit=0, titleLimit=0)
    enc = mark.encode(
        x=alt.X("period:Q", title="year", axis=alt.Axis(tickMinStep=1, format="d")),
        y=alt.Y("value:Q", title=y_title, stack=stack),
        color=alt.Color("series:N", title=None, sort=labels,
                        scale=alt.Scale(domain=labels, range=PALETTE[:len(labels)]),
                        legend=legend),
        order=alt.Order("color_series_sort_index:Q") if kind == "area" else alt.Order(),
    )
    return enc.properties(height=height, padding={"left": 5, "right": 15, "top": 5, "bottom": 5})


def show_chart(chart: alt.Chart, caption: str) -> None:
    st.altair_chart(chart, use_container_width=True, theme=None)   # theme=None: our palette, static
    st.caption(caption)


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
                        income_mult=1.0, corp_mult=1.0, cons_mult=1.0,
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
                income_mult=p.income_tax_mult, corp_mult=p.corp_tax_mult, cons_mult=p.cons_tax_mult,
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
        sb.caption(_preset.blurb + ("" if rung1_ok else "Presets are calibrated to the "
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

# ----------------------------------------------------------------- lever groups (collapsible)
# NOTE: moving widgets between expanders does NOT disturb the keyless preset value-swap — widget
# identity hashes label/min/max/value/step/help, not the container. v2-only widgets are gated on
# is_v2 INSIDE their group so v1 mode shows only the shared levers.
rung = (1 if rung1_ok else 0)

with sb.expander("Automation & adoption", expanded=True):
    cog = st.slider("Cognitive feasibility (AI capability)", 0.0, 1.0, d["cog"], 0.05,
                    help="Of the work that is cognitively exposed to AI (Yale exposure index), the "
                         "share that is technically automatable. Literature anchors: ~0.15 (bare "
                         "LLMs, Eloundou) to ~0.55 (with LLM-built software); 1.0 = AGI.")
    phys = st.slider("Robotics feasibility (physical work)", 0.0, 1.0, d["phys"], 0.05,
                     help="Same idea for physical work (Webb robot-patent exposure). Anchored to "
                          "current robot technology — dexterity/care work scores near zero even "
                          "at 1.0.")
    robotics_lag = st.slider("Robotics capacity build-out lag (years)", 0, 15, d["robotics_lag"], 1,
                             help="Physical automation needs AI-driven industrial capacity first: "
                                  "the robot channel ramps in linearly over this many years "
                                  "(0 = capacity exists from day one). v2 only.")
    adopt0 = st.slider("Automated by year 1 — % of feasible work", 0.0, 1.0, d["adopt0"], 0.01,
                       help="Where the cumulative adoption ceiling starts. Early payroll evidence "
                            "(Brynjolfsson's 'Canaries') puts the realized start near 0.02.")
    adopt1 = st.slider("Automated by the final year — % of feasible work", 0.0, 1.0, d["adopt1"], 0.01,
                       help="A cumulative diffusion CEILING: the automated stock reaches "
                            "feasibility × this share by the horizon — NOT a compounding per-year "
                            "rate. 0.6 means 60% of the feasibly-automatable jobs are automated "
                            "by the end.")
    n_periods = st.slider("Horizon (years)", 3, 30, d["n_periods"],
                          help="Simulation length. Presets carry their native horizon (8–20 years).")
    mapping = st.selectbox("Exposure → share mapping", ["percentile", "logistic"],
                           help="How the continuous exposure score becomes a per-occupation "
                                "automatable share: by percentile rank (default) or a logistic "
                                "curve concentrated on the most-exposed occupations.")
# The kinked preset path survives horizon changes (it is parametric), but moving the adoption
# sliders reverts to a linear ramp. isclose, not ==: the frontend returns min+k·step in JS doubles.
if (_preset is not None and _preset.adoption_reach_year is not None
        and math.isclose(adopt0, _preset.adoption_start, abs_tol=0.004)
        and math.isclose(adopt1, _preset.adoption_end, abs_tol=0.004)):
    adoption_path = presets_mod.build_adoption_path(_preset, n_periods)
else:
    adoption_path = list(np.linspace(adopt0, adopt1, n_periods))
    if _preset is not None and _preset.adoption_reach_year is not None:
        sb.caption(f"Adoption sliders moved — the preset's kinked path (full automation at year "
                   f"{_preset.adoption_reach_year}) was replaced by a linear ramp.")

with sb.expander("Labor market", expanded=False):
    reab = st.slider("Reabsorption rate / yr  (0 = the thesis)", 0.0, 1.0, d["reab"], 0.025,
                     help="Annual rate at which long-term displaced workers find new (lower-wage) "
                          "work. Evidence: 0.6–0.75 in normal markets (Farber), 0.05–0.10 in the "
                          "China-shock adjustment. 0 = displacement is permanent.")
    haircut = st.slider("Re-employment wage cut (haircut)", 0.0, 1.0, d["haircut"], 0.01,
                        help="The re-employed earn (1−haircut) × their old wage, floored at a state "
                             "service wage. Evidence: ~0.13 typical, 0.25 for high-tenure mass "
                             "layoffs. A bigger cut can drop the household into EITC/SNAP/Medicaid "
                             "eligibility — which the model prices exactly.")
    ui_weeks = st.slider("UI duration (weeks)", 0, 52, d["ui_weeks"],
                         help="Unemployment-insurance window. During it, displaced workers draw "
                              "benefits (45% replacement, capped) and are taxed on them; most "
                              "means-tested benefits step up at EXHAUSTION, not at displacement.")
    if is_v2:
        lfp_exit = st.slider("LFP exit / SSDI rate (of exhausted)", 0.0, 0.2, d["lfp"], 0.01,
                             help="Share of benefit-exhausted workers who leave the labor force "
                                  "each year onto disability insurance ($18k/yr outlay). The "
                                  "dominant adjustment margin in the China-shock evidence.")
        attrition = st.slider("Natural attrition of long-term unemployed / yr", 0.0, 0.1,
                              d["attrition"], 0.005,
                              help="Retirement / mortality / discouragement. Fiscally neutral (the "
                                   "baseline counterfactual retires too) — it stops the exhausted "
                                   "pool from persisting forever.")

if is_v2:
    with sb.expander("Firms & compute", expanded=False):
        retained = st.slider("Saved wages → retained profit (share)", 0.0, 1.0, d["retained"], 0.05,
                             help="Of the wage bill firms stop paying (net of automation costs), "
                                  "the share kept as profit — taxed at effective corporate rates "
                                  "(~17–18%), far below the labor-tax wedge it replaces.")
        price_max = round(1.0 - retained, 2)
        if price_max > 0:
            # min() keeps a preset's default legal after the user raises `retained` past it
            price = st.slider("Saved wages → lower prices (share)", 0.0, price_max,
                              min(d["price"], price_max), 0.05,
                              help="The share competed away into consumer prices — a real gain to "
                                   "households, but taxed only through ~2% state consumption "
                                   "taxes. The biggest leak in the base-migration story.")
        else:
            price = 0.0                                  # retained = 100% → no room for price/survivor
        survivor_share = max(0.0, 1.0 - retained - price)
        st.caption(f"→ **Raises for remaining staff**: {survivor_share:.0%} (the remainder)")
        auto_cost = st.slider("Cost of automation (fraction of saved comp → compute)", 0.0, 1.0,
                              d["auto_cost"], 0.05,
                              help="What firms spend on compute/automation inputs per dollar of "
                                   "compensation saved. Flows to the compute-capital pool below. "
                                   "Evidence: 0.3–0.5 in build-out years, ~0.05–0.10 steady state.")
        compute_rate = st.slider("Compute pool — effective tax rate", 0.0, 0.4, d["compute_rate"], 0.01,
                                 help="Effective tax on the compute-capital pool. ~0.05 = the "
                                      "post-TCJA rate on equipment/software capital; 0.27 = parity "
                                      "with domestic capital (the compute-parity overlay).")

    with sb.expander("Survivor wages", expanded=False):
        survivor_unbounded = st.checkbox("Unbounded raise (optimistic)", value=d["unbounded"],
                                         help="Remove the raise ceiling entirely — survivors "
                                              "absorb whatever the routed share funds.")
        ceiling = st.slider("Raise ceiling (× baseline wage)", 1.0, 3.0, d["ceiling"], 0.1,
                            disabled=survivor_unbounded,
                            help="Cap on the still-employed wage index. Raises beyond it spill to "
                                 "profit or prices (spillover below). Raises are funded from the "
                                 "routed survivor share and re-taxed at full marginal rates.")
        elasticity = st.slider("Market wage response to slack (− substitute / + complement)",
                               -0.5, 0.5, d["elasticity"], 0.05,
                               help="How survivors' market wages respond to labor-market slack: "
                                    "negative = AI substitutes for labor and slack pushes wages "
                                    "down; positive = complementarity pulls them up (the "
                                    "augmentation evidence). Applied on last year's slack.")
        spillover = st.slider("Un-absorbable raise → profit (vs prices)", 0.0, 1.0, d["spillover"], 0.05,
                              help="Where raises above the ceiling go instead: 1.0 = all to profit "
                                   "(corporate-taxed), 0.0 = all to prices (nearly untaxed). "
                                   "Drives the federal/state split of that overflow.")

    with sb.expander("Macro & demand", expanded=False):
        price_pt = st.slider("Price pass-through (deflation → real/%-GDP views)", 0.0, 1.0,
                             d["price_pt"], 0.05,
                             help="Share of the firms' price-cut disposition that actually deflates "
                                  "the price level. By design it moves REAL and %-of-GDP views "
                                  "only — nominal tax dollars are never deflated (no bracket "
                                  "double-count).")
        prod_pt = st.slider("Productivity dividend (full automation → +this share of GDP)", 0.0, 1.0,
                            d["prod_pt"], 0.05,
                            help="Output-weighted real-GDP gain: automating the whole comp bill "
                                 "raises GDP by this fraction. Acemoglu's arithmetic implies "
                                 "~0.15; the micro/AGI evidence 0.5–1.0. Cushions %-GDP views.")
        growth = st.slider("Baseline trend growth (nominal, %-GDP denominators)", 0.0, 0.08,
                           d["growth"], 0.005,
                           help="≈2% real + 2% inflation. Grows the GDP denominator so debt/GDP "
                                "is honest at long horizons; nominal dollar columns unchanged.")
        demand = st.slider("Second-round demand multiplier", 0.0, 2.0, d["demand"], 0.05,
                           help="Okun-style LEVEL multiplier: the induced-layoff stock tracks the "
                                "standing net income withdrawal. UBI/raises visibly re-employ; "
                                "austerity deepens it. 0.5 ≈ an active Fed offsetting half; "
                                "1.8 = Chodorow-Reich's no-offset estimate.")

with sb.expander("Government policy", expanded=False):
    if is_v2:
        st.caption("**Tax-regime dials** — true flat surcharges/cuts (1.0 = current law): each "
                   "scales its channel's shock flows AND collects (×−1) of the 2024 baseline "
                   "receipts line, so revenue = mult × (baseline − losses). Raising a dial "
                   "reduces the deficit even with no automation. Static scoring: no behavioral "
                   "response, and no take-home/demand effect from the tax change itself.")
        income_mult = st.slider("Income tax ×", 0.5, 1.5, d["income_mult"], 0.05,
                                help="A surcharge on the $2,403B federal + $536B state baseline "
                                     "individual-income receipts, plus scaling of every income-tax "
                                     "dollar the shock moves (displaced losses, raises' recapture, "
                                     "tax on UI). Payroll (FICA) is statutorily separate and not "
                                     "covered. Two opposing effects under displacement: the "
                                     "surcharge collects more, but each displaced worker also "
                                     "loses more — the surcharge dominates until the wage base "
                                     "collapses.")
        corp_mult = st.slider("Capital taxes ×", 0.5, 1.5, d["corp_mult"], 0.05,
                              help="A surcharge on the $492B federal + $172B state baseline "
                                   "corporate receipts, plus scaling of the capital-recapture "
                                   "bundle (corporate offset incl. dividend and pass-through tax, "
                                   "overflow corporate tax). The compute-pool and robot taxes "
                                   "keep their own rates.")
        cons_mult = st.slider("Consumption taxes ×", 0.5, 1.5, d["cons_mult"], 0.05,
                              help="A surcharge on the $874B state sales/excise + $102B federal "
                                   "excise baselines, plus scaling of the state consumption-tax "
                                   "channel. The classic 'tax the spending, not the wage' "
                                   "response — note how small these bases are next to income "
                                   "taxes: the US has no VAT to fall back on.")
        # The robot tax is paid from retained profit, so its feasible max is retained·(1−auto_cost).
        atx_bound = round(min(0.30, retained * (1.0 - auto_cost)), 2)
        if atx_bound < 0.01:
            automation_tax = 0.0
            st.caption("Automation tax: **0%** — no retained profit left to pay it "
                       "(retained × (1−auto cost) ≈ 0).")
        else:
            automation_tax = st.slider("Automation (robot) tax — share of the automated comp bill",
                                       0.0, atx_bound, min(d["atax"], atx_bound), 0.01,
                                       help="A federal levy on the automated jobs' saved "
                                            "compensation, PAID from retained profit "
                                            "(corp-deductible). Ships at 0: the literature-anchored "
                                            "rates live in the policy overlays "
                                            "(Costinot-Werning ≈ 0.3–1%, not 7%).")
    ubi = st.slider("UBI per worker / yr ($)", 0, 30_000, d["ubi"], 1_000,
                    help="A universal payment per baseline worker, booked as a federal outlay. "
                         "The overlay ships $12k with 30% recapture.")
    if is_v2:
        ubi_recapture = st.slider("UBI recapture (tax clawback + benefit crowd-out)", 0.0, 0.6,
                                  d["ubi_recapture"], 0.05,
                                  help="Share of the UBI outlay the government gets back — "
                                       "income-tax clawback plus means-tested benefits the UBI "
                                       "displaces (~20–30% in practice).")
    interest = st.slider("Interest rate on federal debt", 0.0, 0.10, d["interest"], 0.005,
                         help="New deficits accumulate into debt at this rate. ~0.04 matches the "
                              "discount-rate anchor used in the AGI presets.")

if is_v2:
    with sb.expander("States (balanced budgets)", expanded=False):
        if not rung1_ok:
            st.warning("Benefit-lookup / NOC artifacts absent — reabsorption falls back to the "
                       "flat-haircut model.")
        _sr_opts = ["mix", "raise_rates", "cut_spending"]
        state_resp = st.selectbox("How states close their gaps", _sr_opts,
                                  index=_sr_opts.index(d["state_resp"]),
                                  help="States cannot borrow: each year's shortfall must be met by "
                                       "raising rates on the remaining wage base and/or cutting "
                                       "spending. Both withdraw demand from the same economy.")
        state_cut_share = st.slider("Of the gap, share closed by spending cuts (mix)", 0.0, 1.0,
                                    d["state_cut"], 0.05,
                                    help="Under 'mix': this share is cut from spending, the rest "
                                         "sought from rate hikes (subject to the cap).")
        rate_cap = st.slider("Max feasible rate hike (× base)", 0.1, 3.0, d["rate_cap"], 0.1,
                             help="Political/economic ceiling on rate increases. Once a state "
                                  "hits it, the remainder becomes FORCED spending cuts.")

    with sb.expander("Display", expanded=False):
        denominator = st.radio("Headline denominator", ["absolute", "pct_gdp"], horizontal=True,
                               help="Switch to % of GDP to see the productivity dividend and the "
                                    "price channel move the headline.")

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
        show_chart(ts_chart(res, ["employment_drop_pct", "revenue_lost_pct"], "% of baseline"),
                   "The thesis in one picture: displacement skews high-wage and the schedules are "
                   "progressive, so the revenue line falls below the employment line.")
        st.subheader("Federal deficit & cumulative debt")
        show_chart(ts_chart(res, ["fed_deficit_B", "fed_debt_B"], "$ billions / year"),
                   "The deficit change per year, and its accumulation into debt (with interest).")
    with right:
        st.subheader("Cost → offset → net")
        costs = pd.DataFrame({"period": res["period"],
                              "Labor-tax revenue lost": res["revenue_lost_B"],
                              "Transfers + UI paid out": res["transfers_added_B"],
                              "Capital recapture (offset)": -res["corp_offset_B"]})
        show_chart(ts_chart(costs, ["Labor-tax revenue lost", "Transfers + UI paid out",
                                    "Capital recapture (offset)"], "$ billions / year", kind="bar",
                            stack=True),
                   "Each year's fiscal damage and the corporate offset pulling against it "
                   "(negative bars = recovered revenue).")
        st.subheader("State budget gap")
        show_chart(ts_chart(res, ["state_gap_B"], "$ billions / year"),
                   "The shortfall states must close each year — they cannot run deficits.")
    with st.expander("Per-year detail"):
        st.dataframe(res.style.format("{:,.1f}"), use_container_width=True)
    st.stop()

# -------------------------------------------------- v2 path (multi-actor) ----------------------------
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
          denominator=denominator,
          income_tax_mult=income_mult, corp_tax_mult=corp_mult, cons_tax_mult=cons_mult)
# Overlays apply AFTER the sliders and OVERRIDE the corresponding levers; v2p is the single source
# of truth for every consumer below (model run, JSON export, MC base, UBI warning).
v2p, _overlay_notes = presets_mod.apply_overlays(build_v2_params(ui), overlay_keys)
for _note in _overlay_notes:
    sb.caption("🏛 " + _note)
m = DynamicModelV2(data, deltas, v2p)   # keep the model object: state_table lives on it
res = m.run()
_levers = _dc.asdict(v2p)
if not math.isfinite(_levers["survivor_raise_ceiling"]):
    _levers["survivor_raise_ceiling"] = None    # JSON has no Infinity token; null = unbounded raise
sb.download_button("⬇ Export assumptions (JSON)",
                   _json.dumps({"engine": "v2",
                                "preset": _preset.key if _preset is not None else "custom",
                                "overlays": overlay_keys,
                                "exportedAt": _dt.datetime.now().isoformat(timespec="seconds"),
                                "levers": _levers}, indent=1, allow_nan=False),
                   "assumptions.json", "application/json")
final = res.iloc[-1]

# ----------------------------------------------------------------- v2 headline (2 × 4)
_jobs_lost_M = final["population_M"] - final["employed_M"] - final["reabsorbed_M"] \
    - final["retired_M"]
_inc_tax_lost_cum = res["inc_fed_loss_B"].sum()
c = st.columns(4)
c[0].metric("Jobs lost (final yr)", f"{_jobs_lost_M:,.1f}M",
            help="Workers not employed at the final year who would be under the baseline: on UI, "
                 "exhausted, exited to SSDI, or laid off by the demand shortfall. Excludes the "
                 "re-employed and natural retirement.")
c[1].metric("Employment", f"−{final['employment_drop_pct']:.0f}%",
            help="Decline of the employed-at-original-wage stock vs the 163M baseline (the "
                 "re-employed-at-lower-wage count as not employed here).")
c[2].metric("Federal income tax lost (cumulative)", f"${_inc_tax_lost_cum:,.0f}B",
            help="Total federal individual income-tax revenue lost to displacement, summed over "
                 "the whole horizon — the single largest fiscal channel.")
if denominator == "pct_gdp":
    c[3].metric("Federal deficit (final yr)", f"{final['fed_deficit_abs_pct_gdp']:.1f}% GDP",
                help="The absolute federal deficit (baseline $1,833B + the shock) as a share of "
                     "the productivity-and-trend-adjusted GDP.")
else:
    c[3].metric("Federal deficit (final yr)", f"${final['fed_deficit_abs_B']:,.0f}B",
                help="The absolute federal deficit at the final year: the $1,833B baseline plus "
                     "the shock's net effect.")
c2 = st.columns(4)
c2[0].metric("Federal debt (Δ cumulative)", f"${final['fed_debt_B']:,.0f}B",
             help="All the shock's deficits accumulated with interest — new debt vs the baseline "
                  "path. Negative = the shock pays debt DOWN (capital recoveries outgrew losses).")
c2[1].metric("Net fiscal impact (final yr)", f"{-final['fed_deficit_B']:+,.0f}B",
             help="The signed change in the federal balance in the final year (negative = worse). "
                  "Reconciles exactly to the fiscal summary table below.")
c2[2].metric("State shortfall (final yr)", f"${final['state_gap_B']:,.0f}B",
             help="What states must close that year, BEFORE their rate hikes and cuts — see the "
                  "state section below for what closing it means.")
c2[3].metric("Real GDP effect", f"{100 * (final['productivity_index'] - 1):+.1f}%",
             help="The productivity dividend: real output vs baseline. In severe scenarios this "
                  "is large and POSITIVE while the fiscal picture collapses — the abundance "
                  "arrives as profit and lower prices, not as taxed wages.")

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
    st.subheader("Where the workforce goes")
    show_chart(ts_chart(res, ["employed_M", "on_ui_M", "exhausted_M", "reabsorbed_M",
                              "exited_M", "induced_M", "retired_M"],
                        "millions of workers", kind="area", stack=True, height=300),
               "Every worker in the 163M baseline is in exactly one band each year (conservation "
               "identity C1) — displacement moves people down the stack, reabsorption and "
               "attrition move them out of limbo.")
    st.subheader("Federal budget — absolute levels")
    show_chart(ts_chart(res, ["fed_revenue_B", "fed_deficit_abs_B"], "$ billions"),
               "Federal revenue and the absolute deficit (the $1,833B baseline plus the shock), "
               "in nominal dollars on the 2024 base.")
    st.subheader("What firms do with the saved wages")
    show_chart(ts_chart(res, ["retained_profit_B", "price_reduction_B", "survivor_gains_B",
                              "automation_spend_B"], "$ billions / year", kind="bar", stack=True),
               "The disposition of the compensation firms stop paying — every dollar goes to "
               "exactly one destination (identity C2), each taxed at a different rate: profit "
               "~18%, prices ~2% (state sales tax only), raises at full labor rates, compute at "
               "the capital rate.")
with right:
    st.subheader("Demand feedback — induced layoffs")
    show_chart(ts_chart(res, ["induced_M"], "millions of workers"),
               "Jobs lost because displaced households stopped spending and states cut budgets. "
               "The stock tracks the standing income withdrawal — stimulus (UBI, raises) visibly "
               "re-employs these workers.")
    st.subheader("Wages of the still-employed")
    show_chart(ts_chart(res, ["W_survivor"], "wage index (1.0 = baseline)"),
               "The wage index of workers who keep their jobs: raises funded from the survivor "
               "share push it up; labor-market slack (substitution) pulls it down.")
    show_chart(ts_chart(res, ["survivor_gain_fed_B", "survivor_wage_cost_B"], "$ billions / year"),
               "The same channel in dollars: what the raises cost firms vs the extra federal tax "
               "they generate — the one mechanism that rebuilds the labor tax base.")

if v2p.ubi_annual > 0 and final["ubi_required_rate"] > 1.0:   # v2p, not the slider: overlays add UBI too
    st.warning(f"A \\${v2p.ubi_annual:,.0f}/yr UBI needs a **{final['ubi_required_rate']:.0%}** average rate "
               "on the eroded base by the final year — **>100% is unfundable**.")

# -------------------------------------------------- the states -------------------------------------
st.subheader("The states — the asymmetric amplifier")
st.markdown(
    "Unlike the federal government, **states cannot borrow their way through a revenue shock** — "
    "nearly all operate under balanced-budget requirements, so a shortfall must be met within the "
    "year. The model closes each state's gap by raising tax rates on the remaining wage base up to "
    "a feasibility cap, then cutting spending for whatever the cap leaves. **That closure is a "
    "modeled response, not a prediction that legislatures act instantly** — in reality states lag "
    "(rainy-day funds, accounting deferrals, delayed sessions), so the near-term picture looks "
    "like the *shortfall* chart, and the closure split shows the pressure that eventually has to "
    "land somewhere. Either way the money comes out of the same economy that is shedding jobs, "
    "which is why the closure feeds the demand channel above.")
s_left, s_right = st.columns(2)
with s_left:
    gaps = res[["period", "state_gap_B"]].copy()
    gaps["state_gap_cum_B"] = gaps["state_gap_B"].cumsum()
    show_chart(ts_chart(gaps, ["state_gap_B", "state_gap_cum_B"], "$ billions"),
               "The combined shortfall states must close each year, BEFORE that year's rate hikes "
               "and cuts (given the austerity already imposed in prior years) — the deficit "
               "states would be running if they could borrow like Washington. The cumulative "
               "line is what a decade of it adds up to.")
with s_right:
    show_chart(ts_chart(res, ["state_rate_hike_B", "state_spending_cut_B"],
                        "$ billions / year", kind="bar", stack=True),
               "How the modeled closure splits: revenue recovered by raising rates on the "
               "remaining wage base vs spending cuts (chosen by the mix lever, or FORCED where "
               "the rate-hike cap binds).")
_stbl = m.state_table.sort_values("shortfall_B", ascending=False).reset_index(drop=True)
_stbl_disp = _stbl.rename(columns={
    "state": "State", "net_B": "Net position ($B, − = surplus)", "shortfall_B": "Shortfall ($B)",
    "rate_hike_B": "Rate hikes ($B)", "spending_cut_B": "Spending cuts ($B)",
    "implied_rate_hike_pct": "Implied rate hike (% of base)", "at_cap": "Hit rate cap"})
st.markdown(f"**Hardest-hit states (final year)** — "
            f"{int(final['n_states_capped'])} of 51 hit the rate-hike cap.")
st.dataframe(_stbl_disp.head(15).style.format({c: "{:,.1f}" for c in _stbl_disp.columns
                                               if c not in ("State", "Hit rate cap")}),
             use_container_width=True, hide_index=True)
st.caption("A state 'hits the cap' when the rate increase needed exceeds the feasibility ceiling "
           "— the remainder becomes forced spending cuts. Negative net positions are states whose "
           "survivor-wage gains outweigh their losses.")
with st.expander("All 51 states"):
    st.dataframe(_stbl_disp.style.format({c: "{:,.1f}" for c in _stbl_disp.columns
                                          if c not in ("State", "Hit rate cap")}),
                 use_container_width=True, hide_index=True)

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
    from fiscal_model import mc as mc_mod

    st.caption("Samples N slightly-perturbed lever settings around YOUR configuration (seeded, "
               "constraint-aware; levers that are off stay off) and re-runs the model. Fan = P10–P90 and "
               "P25–P75 bands with the median and your base run; tornado = Spearman rank correlation of "
               "each varied lever with the final-year outcome. **Read the bands as robustness to lever "
               "mis-calibration within this scenario, not as a probability interval** — the ±15% spread "
               "is a convention. The honest uncertainty statement is the spread ACROSS scenario presets "
               "(which world we are in), not the band around one of them. Note: mpc/stickiness "
               "sensitivity reflects only their live paths (demand, state close, reabsorption) — the "
               "cached displaced-worker consumption channel stays at bake-time values.")
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
        st.altair_chart(charts_mod.fan_chart(r.percentiles, r.base_run, mcol, y_title=m_label,
                                             height=320).properties(width="container"),
                        use_container_width=True, theme=None)
        st.caption("Shaded bands: where 80% (light) and 50% (dark) of the perturbed runs land; "
                   "solid line = median; dashed = your exact configuration.")

        t_label = st.radio("Tornado target", ["Final deficit", "Final employment drop"], horizontal=True)
        target = ("final_fed_deficit_B" if t_label == "Final deficit"
                  else "final_employment_drop_pct")
        st.altair_chart(charts_mod.tornado_chart(r.tornado, target, pos_color=NEG, neg_color=POS)
                        .properties(width="container"),
                        use_container_width=True, theme=None)
        st.caption("Which assumptions drive the outcome: rank correlation of each perturbed lever "
                   "with the final-year value. Red bars worsen it as the lever rises; green "
                   "improve it.")

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
