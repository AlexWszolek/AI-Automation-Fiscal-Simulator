"""Fiscal Consequences of AI Automation — the interactive site.

Pick a scenario (published AI forecasts translated into model levers), optionally add policy
responses, and read every number as a CHANGE on top of a no-AI baseline. The engine is the
multi-actor model: a disposition router (saved wage bill → profit / prices / survivor raises /
compute), survivor wages on the still-employed, a macro environment, and the state balanced-budget
closure whose austerity re-enters as a demand-driven layoff flow.

Audience: AI-safety policy researchers and the people they brief — every headline carries a
real-world comparator (fiscal_model/grounding.py) and the sensitivity tornado is always on.

Run:  .venv/bin/streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import math
import sys
from urllib.parse import urlencode
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # project root -> import fiscal_model

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from fiscal_model import charts as charts_mod
from fiscal_model import loaders, reabsorption
from fiscal_model import presets as presets_mod
from fiscal_model.app_params import (CUSTOM_DEFAULTS, UI_GRID, build_v2_params, canon,
                                     cfg_key, encode_query_config, parse_query_config,
                                     preset_widget_defaults, ui_from_defaults)
from fiscal_model.dynamics import precompute_worker_deltas
from fiscal_model import grounding as grounding_mod
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.kernel import KernelParams
from fiscal_model.transfers import TransferLookup

st.set_page_config(page_title="AI Automation Fiscal Model", layout="wide")


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


def ts_chart(df: pd.DataFrame, cols: list[str], y_title: str, kind: str = "line",
             stack: bool | None = None, height: int = 260) -> alt.Chart:
    """A static time-series chart: one colored series per column in `cols`. The x-axis shows
    CALENDAR years (period 0 = the module-level `start_year`, set by the active preset)."""
    labels = [LABELS.get(c, c) for c in cols]
    long = df[["period"] + cols].melt("period", var_name="series", value_name="value")
    long["year"] = long["period"] + start_year
    long["series"] = long["series"].map(lambda c: LABELS.get(c, c))
    mark = {"line": alt.Chart(long).mark_line(strokeWidth=2.5),
            "area": alt.Chart(long).mark_area(opacity=0.85),
            "bar": alt.Chart(long).mark_bar()}[kind]
    # legend below the plot, never truncated: labelLimit=0 disables label clipping; column count
    # adapts so long labels wrap into rows instead of running off the container edge
    legend = alt.Legend(orient="bottom", columns=1 if len(labels) <= 2 else 2,
                        labelLimit=0, symbolLimit=0, titleLimit=0)
    enc = mark.encode(
        x=alt.X("year:Q", title=None, axis=alt.Axis(tickMinStep=1, format="d")),
        y=alt.Y("value:Q", title=y_title, stack=stack),
        color=alt.Color("series:N", title=None, sort=labels,
                        scale=alt.Scale(domain=labels, range=PALETTE[:len(labels)]),
                        legend=legend),
        order=alt.Order("color_series_sort_index:Q") if kind == "area" else alt.Order(),
    )
    return enc.properties(height=height, padding={"left": 5, "right": 15, "top": 5, "bottom": 5})


def show_chart(chart: alt.Chart, caption: str) -> None:
    st.altair_chart(chart, width='stretch', theme=None)   # theme=None: our palette, static
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
assert _backend is not None   # st.stop() above is terminal; load_backend returns a tuple when _err is None
data, deltas, rung1_ok = _backend

from fiscal_model import mc as mc_mod


@st.cache_resource(max_entries=4)
def get_mc_context(key: str, _data, _deltas, _base):
    """Build-once/run-many model context. Keyed on cfg_key(base-without-overlays): overlays touch
    only PERTURBED fields, so ONE context serves the base, every overlay variant, and all tornado
    draws. max_entries bounds Cloud memory (a context holds the per-cell template arrays)."""
    return mc_mod.ScenarioContext(_data, _deltas, _base)


@st.cache_data(max_entries=64)
def final_metrics(key: str, _ctx, _v2p) -> dict:
    """Final-year scalars for a config through the fast path — small entries, repr-keyed."""
    r = _ctx.run(_v2p)
    f = r.iloc[-1]
    return {"fed_deficit_B": float(f["fed_deficit_B"]), "state_gap_B": float(f["state_gap_B"])}


st.title("Fiscal Consequences of AI Automation")
sb = st.sidebar

# ----------------------------------------------------------------- scenario presets (v2 only)
# Loading mechanism: NO sidebar widget passes key=, so streamlit hashes each widget's identity from
# its parameters (label/min/max/value/step/help). Swapping a widget's value= default when the preset
# changes therefore RESETS it to the preset value, while user tweaks persist as long as the preset
# stays put. DO NOT add a static key= to these widgets — with a user key the identity shrinks to
# min/max/step and preset loading silently stops working. Known limit: if two presets share a
# widget's default, switching between them does not clear a tweak on that widget — the "modified
# from preset" caption (main area) is the honest surface for that.
# Shareable URLs: parse query params ONCE per session (the codec clamps + grid-snaps every
# value, so a hand-edited link can never crash a widget). The URL acts as a preset-modifier:
# its lever diffs merge into the widget DEFAULTS while the user stays on the URL's preset, and
# disarm permanently the moment they switch presets.
if "url_cfg" not in st.session_state:
    st.session_state["url_cfg"] = parse_query_config(dict(st.query_params))
    st.session_state["url_armed"] = bool(st.session_state["url_cfg"]["levers"])
_url_cfg = st.session_state["url_cfg"]

_preset = None
overlay_keys: list = []
_names = {p.name: k for k, p in presets_mod.PRESETS.items()}
_keys = list(presets_mod.PRESETS)
_url_index = (1 + _keys.index(_url_cfg["preset"])) if _url_cfg["preset"] in _keys else 0
_choice = sb.selectbox("Scenario preset", ["Custom"] + list(_names), index=_url_index,
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
    "Policy responses", list(presets_mod.OVERLAYS), default=_url_cfg["overlays"],
    format_func=lambda k: presets_mod.OVERLAYS[k].name,
    help="What could government do about it? Each response is a policy from the economics "
         "literature, applied ON TOP of the scenario (it overrides the matching levers). "
         "The captions below show what each one recovers — the punchline is usually how "
         "small that is next to the gap.")
if all(k in overlay_keys for k in ("cw-robot-tax", "grt-robot-tax")):
    sb.warning("Both robot taxes set the same lever — using Costinot-Werning, dropping GRT.")
    overlay_keys.remove("grt-robot-tax")

d: dict[str, Any] = dict(preset_widget_defaults(_preset)) if _preset is not None else dict(CUSTOM_DEFAULTS)
if st.session_state.get("url_armed"):
    _on_target = (_preset.key if _preset is not None else None) == _url_cfg["preset"]
    if _on_target:
        d.update({k: v for k, v in _url_cfg["levers"].items() if k in d})
    else:
        st.session_state["url_armed"] = False    # user navigated away — the URL never re-applies
start_year = _preset.start_year if _preset is not None else 2026   # calendar year of period 0
st.markdown(
    "**How to use this:** pick a *scenario* in the sidebar — each one is a published AI forecast "
    "(Acemoglu, Korinek, AI 2027/2040, …) translated into this model's levers, with citations. "
    "Optionally add *policy responses* to see what they recover. **Every number on this page is a "
    "change on top of a no-AI baseline** — the deficits Washington already projects come first, "
    "and this is added to them. The story the accounting keeps telling: the tax base migrates "
    "from **wages** (taxed ~25-30%) to **profits, prices, and compute** (taxed far less), so "
    "revenue falls faster than employment — and states, which must balance their budgets, have "
    "no shock absorber.")

# ----------------------------------------------------------------- lever groups (collapsible)
# NOTE: moving widgets between expanders does NOT disturb the keyless preset value-swap — widget
# identity hashes label/min/max/value/step/help, not the container.
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
                          help="Simulation length. Presets carry their native horizon (8-20 years).")
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
                          "work. Evidence: 0.6-0.75 in normal markets (Farber), 0.05-0.10 in the "
                          "China-shock adjustment. 0 = displacement is permanent.")
    haircut = st.slider("Re-employment wage cut (haircut)", 0.0, 1.0, d["haircut"], 0.01,
                        help="The re-employed earn (1-haircut) × their old wage, floored at a state "
                             "service wage. Evidence: ~0.13 typical, 0.25 for high-tenure mass "
                             "layoffs. A bigger cut can drop the household into EITC/SNAP/Medicaid "
                             "eligibility — which the model prices exactly.")
    ui_weeks = st.slider("UI duration (weeks)", 0, 52, d["ui_weeks"],
                         help="Unemployment-insurance window. During it, displaced workers draw "
                              "benefits (45% replacement, capped) and are taxed on them; most "
                              "means-tested benefits step up at EXHAUSTION, not at displacement.")
    lfp_exit = st.slider("LFP exit / SSDI rate (of exhausted)", 0.0, 0.2, d["lfp"], 0.01,
                         help="Share of benefit-exhausted workers who leave the labor force "
                              "each year onto disability insurance ($18k/yr outlay). The "
                              "dominant adjustment margin in the China-shock evidence.")
    attrition = st.slider("Natural attrition of long-term unemployed / yr", 0.0, 0.1,
                          d["attrition"], 0.005,
                          help="Retirement / mortality / discouragement. Fiscally neutral (the "
                               "baseline counterfactual retires too) — it stops the exhausted "
                               "pool from persisting forever.")

with sb.expander("Firms & compute", expanded=False):
    retained = st.slider("Saved wages → retained profit (share)", 0.0, 1.0, d["retained"], 0.05,
                         help="Of the wage bill firms stop paying (net of automation costs), "
                              "the share kept as profit — taxed at effective corporate rates "
                              "(~17-18%), far below the labor-tax wedge it replaces.")
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
                               "Evidence: 0.3-0.5 in build-out years, ~0.05-0.10 steady state.")
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
    elasticity = st.slider("Market wage response to slack (- substitute / + complement)",
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
                             "~0.15; the micro/AGI evidence 0.5-1.0. Cushions %-GDP views.")
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
    st.caption("**Tax-regime dials** — true flat surcharges/cuts (1.0 = current law): each "
               "scales its channel's shock flows AND collects (×-1) of the 2024 baseline "
               "receipts line, so revenue = mult × (baseline - losses). Raising a dial "
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
    # The robot tax is paid from retained profit, so its feasible max is retained·(1-auto_cost).
    atx_bound = round(min(0.30, retained * (1.0 - auto_cost)), 2)
    if atx_bound < 0.01:
        automation_tax = 0.0
        st.caption("Automation tax: **0%** — no retained profit left to pay it "
                   "(retained × (1-auto cost) ≈ 0).")
    else:
        automation_tax = st.slider("Automation (robot) tax — share of the automated comp bill",
                                   0.0, atx_bound, min(d["atax"], atx_bound), 0.01,
                                   help="A federal levy on the automated jobs' saved "
                                        "compensation, PAID from retained profit "
                                        "(corp-deductible). Ships at 0: the literature-anchored "
                                        "rates live in the policy overlays "
                                        "(Costinot-Werning ≈ 0.3-1%, not 7%).")
    ubi = st.slider("UBI per worker / yr ($)", 0, 30_000, d["ubi"], 1_000,
                    help="A universal payment per baseline worker, booked as a federal outlay. "
                         "The overlay ships $12k with 30% recapture.")
    ubi_recapture = st.slider("UBI recapture (tax clawback + benefit crowd-out)", 0.0, 0.6,
                              d["ubi_recapture"], 0.05,
                              help="Share of the UBI outlay the government gets back — "
                                   "income-tax clawback plus means-tested benefits the UBI "
                                   "displaces (~20-30% in practice).")
    interest = st.slider("Interest rate on federal debt", 0.0, 0.10, d["interest"], 0.005,
                         help="New deficits accumulate into debt at this rate. ~0.04 matches the "
                              "discount-rate anchor used in the AGI presets.")

with sb.expander("Display", expanded=False):
    denominator = st.radio("Headline denominator", ["absolute", "pct_gdp"], horizontal=True,
                           help="Switch to % of GDP to see the productivity dividend and the "
                                "price channel move the headline.")



# -------------------------------------------------- page scaffolding --------------------------------
# The state-response widgets must EXECUTE before the model runs but RENDER inside the state section
# further down the page — so the blocks above them are pre-allocated container slots filled after
# the run. (Main-area widgets are keyless like the sidebar's: the preset value-swap still applies.)
main_top = st.container()      # headline metrics + preset provenance + the four chart panels

st.subheader("The states — where the shock has no shock absorber")
st.markdown(
    "Unlike the federal government, **states cannot borrow their way through a revenue shock** — "
    "nearly all operate under balanced-budget rules, so a shortfall has to be met within the year. "
    "**How they meet it is a political choice, not an economic law**, so it is a control here, not "
    "an assumption: raise taxes on the people still working, cut spending, or a mix. Two honest "
    "caveats. First, legislatures lag — rainy-day funds and deferrals mean the first year or two "
    "look like the *shortfall* chart, not the closure. Second, whichever response they choose "
    "takes demand out of the same economy that is shedding jobs, which feeds the layoff spiral "
    "above.")
with st.container(border=True):
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        _sr_opts = ["mix", "raise_rates", "cut_spending"]
        state_resp = st.selectbox("What do states do?", _sr_opts,
                                  index=_sr_opts.index(d["state_resp"]),
                                  format_func={"mix": "Mix of both", "raise_rates": "Raise taxes",
                                               "cut_spending": "Cut spending"}.get,
                                  help="The closure rule for every state, every year. 'Raise "
                                       "taxes' hikes rates on the remaining wage base up to the "
                                       "cap; 'cut spending' takes it all out of budgets; 'mix' "
                                       "splits by the slider.")
    with sc2:
        state_cut_share = st.slider("Of the gap, share closed by spending cuts (mix)", 0.0, 1.0,
                                    d["state_cut"], 0.05,
                                    help="Under 'Mix of both': this share is cut from spending, "
                                         "the rest sought from rate hikes (subject to the cap).")
    with sc3:
        rate_cap = st.slider("Max feasible rate hike (× base)", 0.1, 3.0, d["rate_cap"], 0.1,
                             help="Political/economic ceiling on rate increases. Once a state "
                                  "hits it, the remainder becomes FORCED spending cuts — the "
                                  "cap is where 'just raise taxes' stops being an option.")
    if not rung1_ok:
        st.warning("Benefit-lookup / NOC artifacts absent — reabsorption falls back to the "
                   "flat-haircut model.")
states_rest = st.container()   # the state map/table + closure charts land here after the run

# -------------------------------------------------- v2 path (multi-actor) ----------------------------
# assumptions export (mirrors the ai-shock pattern: a timestamped, reload-able lever snapshot)
import dataclasses as _dc
import datetime as _dt
import json as _json

ui: dict[str, Any] = dict(mapping=mapping, cog=cog, phys=phys, robotics_lag=float(robotics_lag),
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
if overlay_keys:
    # live what-did-it-do readout: base-without-responses vs each response alone (cached, ~0.3s
    # each on first render), all through ONE ScenarioContext (overlay fields are PERTURBED)
    _base_no = canon(build_v2_params(ui))
    _bkey = cfg_key(_base_no)
    _ctx0 = get_mc_context(_bkey, data, deltas, _base_no)
    _gap = final_metrics(_bkey, _ctx0, _base_no)["fed_deficit_B"]
    for _k in overlay_keys:
        _ovp = canon(presets_mod.apply_overlays(_base_no, [_k])[0])
        _rec = _gap - final_metrics(cfg_key(_ovp), _ctx0, _ovp)["fed_deficit_B"]
        if _gap > 1.0:
            sb.caption(f"→ **{presets_mod.OVERLAYS[_k].name}** recovers **\\${_rec:,.0f}B/yr** of "
                       f"the \\${_gap:,.0f}B/yr final-year gap (**{100 * _rec / _gap:.0f}%**)")
        else:
            sb.caption(f"→ **{presets_mod.OVERLAYS[_k].name}**: the base scenario shows no "
                       f"final-year deficit deterioration to recover against")
    if len(overlay_keys) > 1 and _gap > 1.0:
        _allp = canon(v2p)
        _rec_all = _gap - final_metrics(cfg_key(_allp), _ctx0, _allp)["fed_deficit_B"]
        sb.caption(f"→ **All selected together** recover **\\${_rec_all:,.0f}B/yr** "
                   f"(**{100 * _rec_all / _gap:.0f}%** of the gap)")
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

# URL write-back: the address bar always encodes the current configuration (preset + overlays +
# only the levers that differ from the preset's own defaults). query_params writes never rerun.
_pristine = preset_widget_defaults(_preset) if _preset is not None else dict(CUSTOM_DEFAULTS)
_wvals = dict(cog=cog, phys=phys, robotics_lag=robotics_lag, adopt0=adopt0, adopt1=adopt1,
              n_periods=n_periods, reab=reab, haircut=haircut, ui_weeks=ui_weeks,
              lfp=lfp_exit, attrition=attrition, retained=retained, price=price,
              auto_cost=auto_cost, compute_rate=compute_rate, unbounded=survivor_unbounded,
              ceiling=ceiling, elasticity=elasticity, spillover=spillover,
              price_pt=price_pt, prod_pt=prod_pt, growth=growth, demand=demand,
              state_resp=state_resp, state_cut=state_cut_share, rate_cap=rate_cap,
              atax=automation_tax, ubi=ubi, ubi_recapture=ubi_recapture, interest=interest,
              income_mult=income_mult, corp_mult=corp_mult, cons_mult=cons_mult)
_qp = encode_query_config(_preset.key if _preset is not None else None, overlay_keys,
                          _wvals, _pristine, mapping)
if dict(st.query_params) != _qp:
    st.query_params.from_dict(_qp)
_share_qs = urlencode(_qp)

with main_top:
    # ----------------------------------------------------------------- v2 headline (2 × 4)
    _jobs_lost_M = final["population_M"] - final["employed_M"] - final["reabsorbed_M"] \
        - final["retired_M"]
    _inc_tax_lost_cum = res["inc_fed_loss_B"].sum()
    c = st.columns(4)
    c[0].metric("Jobs lost (final yr)", f"{_jobs_lost_M:,.1f}M",
                help="Workers not employed at the final year who would be under the baseline: on UI, "
                     "exhausted, exited to SSDI, or laid off by the demand shortfall. Excludes the "
                     "re-employed and natural retirement.")
    c[0].caption(grounding_mod.ground(_jobs_lost_M, "jobs"))
    c[1].metric("Employment", f"-{final['employment_drop_pct']:.0f}%",
                help="Decline of the employed-at-original-wage stock vs the 163M baseline (the "
                     "re-employed-at-lower-wage count as not employed here).")
    c[2].metric("Federal income tax lost (cumulative)", f"${_inc_tax_lost_cum:,.0f}B",
                help="Total federal individual income-tax revenue lost to displacement, summed over "
                     "the whole horizon — the single largest fiscal channel.")
    c[2].caption(grounding_mod.ground(_inc_tax_lost_cum, "revenue_flow"))
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
    c2[0].caption(grounding_mod.ground(final["fed_debt_B"], "debt_stock"))
    c2[1].metric("Net fiscal impact (final yr)", f"{-final['fed_deficit_B']:+,.0f}B",
                 help="The signed change in the federal balance in the final year (negative = worse). "
                      "Reconciles exactly to the fiscal summary table below.")
    c2[1].caption(grounding_mod.ground(final["fed_deficit_B"], "fed_deficit_flow"))
    c2[2].metric("State shortfall (final yr)", f"${final['state_gap_B']:,.0f}B",
                 help="What states must close that year, BEFORE their rate hikes and cuts — see the "
                      "state section below for what closing it means.")
    c2[2].caption(grounding_mod.ground(final["state_gap_B"], "state_flow"))
    c2[3].metric("Real GDP effect", f"{100 * (final['productivity_index'] - 1):+.1f}%",
                 help="The productivity dividend: real output vs baseline. In severe scenarios this "
                      "is large and POSITIVE while the fiscal picture collapses — the abundance "
                      "arrives as profit and lower prices, not as taxed wages.")

    if _preset is not None:
        # deviation check on the preset-controlled fields only; isclose absorbs JS-double slider echoes
        _pp = presets_mod.to_params(_preset, n_periods=ui["n_periods"])
        _ui_p = build_v2_params(ui)

        def _differs(a, b):
            if isinstance(a, list) or isinstance(b, list):
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
                   "Federal revenue and the absolute deficit. Revenue falls faster than employment "
                   "because the displaced skew high-wage and the tax schedule is progressive — the "
                   "budget loses its best taxpayers first.")
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


with states_rest:
    _stbl = m.state_table
    _tax_base = float(_stbl["taxable_base_B"].sum())
    _implied = 100.0 * final["state_gap_B"] / _tax_base if _tax_base > 0 else 0.0
    if final["state_gap_B"] > 1:
        st.markdown(f"**Closing the final-year gap with taxes alone would mean raising state "
                    f"taxes ≈ {_implied:,.1f}% on everyone still working** — that is the "
                    f"politician-legible size of a \\${final['state_gap_B']:,.0f}B shortfall on a "
                    f"\\${_tax_base:,.0f}B remaining wage base. "
                    f"{int(final['n_states_capped'])} of 51 states hit the rate-hike cap under "
                    f"the current response.")
    _sv1, _sv2 = st.columns([1, 3])
    state_view = _sv1.radio("View", ["Map", "Table"], horizontal=True, label_visibility="collapsed")
    if state_view == "Map":
        st.altair_chart(charts_mod.state_choropleth(
            _stbl, "net_B", "Net position ($B/yr, red = shortfall)",
            tooltip=[("net_B", "Net position ($B, − = surplus)", ",.1f"),
                     ("shortfall_B", "Shortfall to close ($B)", ",.1f"),
                     ("rate_hike_B", "Closed by rate hikes ($B)", ",.1f"),
                     ("spending_cut_B", "Closed by spending cuts ($B)", ",.1f"),
                     ("implied_rate_hike_pct", "Implied rate hike (%)", ",.1f")],
            neg_color=POS, pos_color=NEG),
            width='stretch', theme=None)
        st.caption("Final-year net position by state — hover any state for its shortfall, how "
                   "the chosen response closes it, and the implied rate hike on its remaining "
                   "workers. Red = losses to close; green = survivor-wage gains outweigh losses. "
                   "(Shapes load from a CDN — if the map is blank, switch to Table. DC is on the "
                   "map but easier to read in the Table.)")
    else:
        _st_disp = (_stbl.sort_values("shortfall_B", ascending=False).reset_index(drop=True)
                    .drop(columns="taxable_base_B")
                    .rename(columns={
                        "state": "State", "net_B": "Net position ($B, − = surplus)",
                        "shortfall_B": "Shortfall ($B)", "rate_hike_B": "Rate hikes ($B)",
                        "spending_cut_B": "Spending cuts ($B)",
                        "implied_rate_hike_pct": "Implied rate hike (% of base)",
                        "at_cap": "Hit rate cap"}))
        st.dataframe(_st_disp.style.format({c: "{:,.1f}" for c in _st_disp.columns
                                            if c not in ("State", "Hit rate cap")}),
                     width='stretch', hide_index=True, height=420)
        st.caption("A state 'hits the cap' when the rate increase needed exceeds the feasibility "
                   "ceiling — the remainder becomes forced spending cuts. Negative net positions "
                   "are states whose survivor-wage gains outweigh their losses.")
    s_left, s_right = st.columns(2)
    with s_left:
        gaps = pd.DataFrame({"period": res["period"], "state_gap_B": res["state_gap_B"]})
        gaps["state_gap_cum_B"] = gaps["state_gap_B"].cumsum()
        show_chart(ts_chart(gaps, ["state_gap_B", "state_gap_cum_B"], "$ billions"),
                   "The shortfall BEFORE any response — the deficit states would run if they "
                   "could borrow like Washington. This is what the first year or two actually "
                   "look like while legislatures catch up; the cumulative line is what a decade "
                   "of it adds up to.")
    with s_right:
        show_chart(ts_chart(res, ["state_rate_hike_B", "state_spending_cut_B"],
                            "$ billions / year", kind="bar", stack=True),
                   "The consequence of the response you chose above: revenue recovered by rate "
                   "hikes vs spending cuts (including cuts FORCED where the cap binds). Try "
                   "'Raise taxes' vs 'Cut spending' — the federal picture changes too, because "
                   "both withdraw demand differently.")

# -------------------------------------------------- Fiscal summary table ----------------------------
st.subheader("Fiscal summary")
from fiscal_model import summary as summary_mod
from fiscal_model.government import RevenueLedger

_cbo = grounding_mod.load_cbo_baseline()
fs1, fs2 = st.columns(2)
fs_group = fs1.radio("View", ["By tax category", "By fiscal channel", "Detailed per-year"],
                     horizontal=True,
                     help="The two summary views group the same reconciled flows differently; "
                          "'Detailed per-year' is every raw model column.")
if fs_group == "Detailed per-year":
    _detail = res.copy()
    _detail.insert(0, "year", (start_year + _detail["period"]).astype(int))
    st.dataframe(_detail.style.format("{:,.2f}", subset=[c for c in _detail.columns
                                                         if c not in ("year", "period")]),
                 width='stretch')
    st.caption("Every column the model produces, per year — the source data behind every chart "
               "and table on this page. Columns ending _B are $ billions; _M millions of workers.")
    st.download_button("⬇ Full detail CSV", _detail.to_csv(index=False).encode("utf-8"),
                       "run-detail.csv", "text/csv")
else:
    fs_units = fs2.radio("Units", ["$B", "% of projected federal revenue (CBO)"], horizontal=True,
                         help="The CBO view divides each year by THAT year's projected total "
                              "federal revenue (Feb-2026 baseline) — 'how big is this against "
                              "the money the government actually expects to have'.")
    _ledger = RevenueLedger(data)
    fs_df = summary_mod.build_fiscal_summary(
        res, _ledger,
        grouping="tax" if fs_group == "By tax category" else "channel",
        units="busd" if fs_units == "$B" else "pct_cbo_revenue",
        start_year=start_year, cbo=_cbo)
    st.caption("Revenue lines are signed revenue **changes** (negative = lost revenue); outlay lines are "
               "spending changes (positive = more spending); **Net fiscal impact = -deficit change** "
               "(negative = worse). Flows sum into *Total*; levels show the final year. Memo rows document "
               "untaxed magnitudes (offshore leakage, consumer surplus) and are excluded from nets."
               + (" Channels follow the labour→capital / resident→non-resident / consumer-surplus / "
                  "spending decomposition." if fs_group == "By fiscal channel" else ""))
    _year_cols = [c for c in fs_df.columns if str(c)[:2] == "20" and str(c).isdigit()] + ["Total"]
    _disp = fs_df.drop(columns="kind").set_index(["group", "label"])
    _emph = fs_df["kind"].isin(["subtotal", "net"]).to_numpy()
    styler = (_disp.style
              .apply(lambda s: np.where(_emph, "font-weight: bold; background-color: rgba(128,128,128,0.15)",
                                        ""), axis=0)
              .map(lambda v: "color: #e4572e" if isinstance(v, float) and v < -0.05 else
                             ("color: #3fa34d" if isinstance(v, float) and v > 0.05 else ""),
                   subset=_year_cols)
              .format("{:,.1f}"))
    st.dataframe(styler, width='stretch')
    _final_year = start_year + int(final["period"])
    _cbo_def = abs(_cbo.deficit(_final_year))
    _add_pct = 100.0 * final["fed_deficit_B"] / _cbo_def
    if abs(_add_pct) >= 1:
        st.caption(f"**Scale check:** in {_final_year} this scenario "
                   f"{'adds' if _add_pct > 0 else 'removes'} **{abs(_add_pct):,.0f}%** "
                   f"{'to' if _add_pct > 0 else 'from'} CBO's projected {min(_final_year, _cbo.max_year)} "
                   f"deficit (${_cbo_def:,.0f}B) — on top of what CBO already projects."
                   + (" (CBO's projections end at FY2036; the comparison holds their 2036 value.)"
                      if _final_year > _cbo.max_year else ""))
    if start_year + int(final["period"]) > _cbo.max_year and fs_units != "$B":
        st.caption(f"% columns past FY{_cbo.max_year} extrapolate CBO revenue at the baseline's "
                   f"terminal growth rate ({_cbo.terminal_growth:.1%}/yr).")
    st.download_button("⬇ Summary CSV", summary_mod.to_csv_bytes(fs_df), "fiscal-summary.csv", "text/csv")

# -------------------------------------------------- Uncertainty (Monte Carlo) -----------------------
# -------------------------------------------------- which assumptions drive this ---------------------
# The always-on sensitivity tornado. Presets are served instantly from data/app_precomputed/
# (N=200, seed 0, built by scripts/precompute_app_mc.py; a freshness test pins the keys). Modified
# settings auto-recompute at N=150 after a short debounce — no buttons. State machine: the
# @st.fragment interval is re-evaluated every full script run (None once a result exists → static
# render; 1s while waiting/computing); the compute happens inside a fragment tick and finishes
# with st.rerun(scope="app"), which is legal from a tick and flips the interval off.
import time as _time

st.subheader("Which assumptions drive this number?")

TORNADO_LABELS = {
    "cognitive_feasibility": "AI capability (cognitive work)",
    "physical_feasibility": "Robot capability (physical work)",
    "robotics_lag": "Robot build-out lag",
    "adoption_end": "How much feasible work is automated",
    "ui_weeks": "UI benefit duration",
    "reabsorption_rate": "Re-employment rate",
    "reemployment_haircut": "Re-employment wage cut",
    "lfp_exit_rate": "Labor-force exit (SSDI)",
    "attrition_rate": "Natural attrition",
    "survivor_elasticity": "Wage response to slack",
    "survivor_raise_ceiling": "Raise ceiling",
    "survivor_spillover_to_profit": "Overflow raises → profit",
    "retained_profit_share": "Saved wages kept as profit",
    "price_reduction_share": "Saved wages → lower prices",
    "survivor_gains_share": "Saved wages → raises",
    "auto_cost": "Automation input costs (→ compute)",
    "offshore_share": "Compute pool offshore share",
    "compute_effective_rate": "Compute pool tax rate",
    "automation_tax_rate": "Robot tax rate",
    "ubi_recapture_rate": "UBI recapture",
    "baseline_growth_rate": "Trend growth",
    "demand_multiplier": "Demand multiplier",
    "price_passthrough": "Price pass-through",
    "productivity_passthrough": "Productivity dividend",
    "mpc": "Household spending propensity",
    "consumption_stickiness": "Consumption stickiness",
    "interest_rate": "Interest rate on debt",
    "ubi_annual": "UBI amount",
    "ssdi_annual": "SSDI benefit level",
    "state_cut_share": "State cut share",
    "state_rate_hike_cap": "State rate-hike cap",
}

_TORNADO_DEBOUNCE_S, _TORNADO_N, _TORNADO_KEEP = 3.0, 150, 4


_PRECOMP_PATH = Path(__file__).resolve().parent.parent / "data" / "app_precomputed" / "mc_tornado.json"


@st.cache_resource
def _load_precomputed_mc(mtime: float) -> dict:
    """cfg_repr -> entry from the committed precompute artifact ({} if absent — the app degrades
    to one auto-run per session instead of erroring). Keyed on the file's mtime so regenerating
    the artifact takes effect without a server restart."""
    try:
        payload = _json.loads(_PRECOMP_PATH.read_text())
    except FileNotFoundError:
        return {}
    return {e["cfg_repr"]: e for e in payload["entries"]}


def load_precomputed_mc() -> dict:
    return _load_precomputed_mc(_PRECOMP_PATH.stat().st_mtime if _PRECOMP_PATH.exists() else 0.0)


def _render_tornado(entry: dict, n_draws: int, stale: bool = False) -> None:
    tor = pd.DataFrame(entry["tornado"]).assign(target="final_fed_deficit_B")
    tor["lever"] = tor["lever"].map(lambda x: TORNADO_LABELS.get(x, x))
    chart = charts_mod.tornado_chart(tor, "final_fed_deficit_B", top=12,
                                     pos_color=NEG, neg_color=POS).properties(width="container")
    if stale:
        chart = chart.configure_mark(opacity=0.35)   # gray the whole bar set while recomputing
        st.caption("⏳ **Settings changed — updating the sensitivity analysis in a few seconds…** "
                   "(showing the previous configuration meanwhile)")
    st.altair_chart(chart, width='stretch', theme=None)
    st.caption(f"Each bar: how strongly that assumption drives the final-year deficit across "
               f"{n_draws} model runs that jitter every live assumption ±15% around your settings "
               f"(red = raising it worsens the deficit; green = improves it). Across those runs "
               f"the final-year deficit increase stays between **\\${entry['p10']:,.0f}B and "
               f"\\${entry['p90']:,.0f}B** (P10–P90). Read that band as robustness to "
               f"mis-calibrated assumptions WITHIN this scenario — the honest uncertainty about "
               f"the future is the spread across the scenario presets themselves.")


_mc_base = canon(v2p)
_mc_key = cfg_key(_mc_base)
_tss = st.session_state.setdefault("tornado", {"results": {}, "pending": None,
                                               "t0": 0.0, "last_shown": None})


def _tornado_lookup(k):
    if k is None:
        return None
    e = _tss["results"].get(k)
    return e if e is not None else load_precomputed_mc().get(k)


_have = _tornado_lookup(_mc_key) is not None
if not _have and _tss["pending"] != _mc_key:
    _tss["pending"], _tss["t0"] = _mc_key, _time.monotonic()    # (re)start the debounce clock
_tornado_interval = None if _have else 1.0


@st.fragment(run_every=_tornado_interval)
def tornado_section():
    entry = _tornado_lookup(_mc_key)
    if entry is not None:                        # steady state (or a coalesced late tick)
        n = entry.get("_n", 200)
        _render_tornado(entry, n)
        _tss["last_shown"] = _mc_key
        return
    age = _time.monotonic() - _tss["t0"]
    if age < _TORNADO_DEBOUNCE_S:                # debouncing — the 1s timer re-enters
        prev = _tornado_lookup(_tss["last_shown"])
        if prev is not None:
            _render_tornado(prev, prev.get("_n", 200), stale=True)
        else:
            st.caption("⏳ Sensitivity analysis starts a few seconds after you stop moving "
                       "sliders…")
        return
    # debounce elapsed — compute inside this tick, then hand back to a full run
    ctx = get_mc_context(_mc_key, data, deltas, _mc_base)
    bar = st.progress(0.0, text=f"stress-testing your settings… 0/{_TORNADO_N} runs")
    r = mc_mod.run_mc(ctx, n=_TORNADO_N, spread=0.15, seed=0,
                      progress=lambda i, n: bar.progress(i / n, text=f"stress-testing your "
                                                                     f"settings… {i}/{n} runs"))
    finals = r.paths[r.paths["period"] == r.paths["period"].max()]["fed_deficit_B"]
    tor = r.tornado.query("target == 'final_fed_deficit_B'")
    _tss["results"][_mc_key] = {
        "tornado": [{"lever": t.lever, "spearman": float(t.spearman)} for t in tor.itertuples()],
        "p10": float(finals.quantile(0.10)), "p50": float(finals.quantile(0.50)),
        "p90": float(finals.quantile(0.90)),
        "base_final": float(r.base_run["fed_deficit_B"].iloc[-1]), "_n": _TORNADO_N,
    }
    while len(_tss["results"]) > _TORNADO_KEEP:  # bounded session memory (insertion-ordered)
        _tss["results"].pop(next(iter(_tss["results"])))
    _tss["pending"] = None
    st.rerun(scope="app")


tornado_section()

_sh1, _sh2 = st.columns(2)
with _sh1.expander("🔗 Share this configuration"):
    _app_url = getattr(getattr(st, "context", None), "url", None)
    _share_url = (f"{str(_app_url).rstrip('/')}" + (f"?{_share_qs}" if _share_qs else "")
                  if _app_url else (f"?{_share_qs}" if _share_qs else ""))
    if _share_qs or _app_url:
        st.code(_share_url or "?", language=None)
        st.caption("Anyone opening this link sees exactly this configuration — preset, policy "
                   "responses, and every modified lever. (Your browser's address bar stays in "
                   "sync too — copying it works just as well.)")
    else:
        st.caption("You are on the unmodified default configuration — the plain app URL "
                   "reproduces it.")
with _sh2.expander("📋 For your memo — copy-ready summary"):
    _scenario_name = _preset.name if _preset is not None else "Custom settings"
    st.code(grounding_mod.briefing_text(
        _scenario_name, start_year, int(ui["n_periods"]),
        dict(jobs_lost_M=float(_jobs_lost_M),
             final_deficit_delta_B=float(final["fed_deficit_B"]),
             debt_delta_B=float(final["fed_debt_B"]),
             cum_income_tax_lost_B=float(_inc_tax_lost_cum),
             state_gap_B=float(final["state_gap_B"]),
             real_gdp_pct=float(100 * (final["productivity_index"] - 1))),
        share_qs=_share_qs), language=None)
    st.caption("Plain-English, grounded, and provenanced — paste it into an email or briefing "
               "note as-is (the copy icon is in the top-right of the block).")

with st.expander("About this model"):
    st.markdown(
        "This is a bottom-up accounting model of what AI automation does to US public finances: it "
        "prices every displaced worker's taxes and benefits at the occupation-by-state level, follows "
        "the saved wages to where they actually go (profit, prices, raises, compute), and makes all "
        "51 states balance their budgets. Every number you see is a **change against a no-AI "
        "baseline** — the deficits Washington already projects are on top of this. Every assumption "
        "is a slider, not a hidden constant; the scenario presets are published forecasts translated "
        "into those sliders with citations.\n\n"
        "The code is open source and the accounting is machine-checked: **270+ automated tests**, "
        "including conservation identities that re-verify every run — every worker and every dollar "
        "must land in exactly one place.\n\n"
        "[Source code](https://github.com/AlexWszolek/AI-Automation-Fiscal-Simulator) · "
        "[Technical report](https://github.com/AlexWszolek/AI-Automation-Fiscal-Simulator/blob/main/docs/report/report.docx) · "
        "[Preset evidence](https://github.com/AlexWszolek/AI-Automation-Fiscal-Simulator/blob/main/docs/PRESET_EVIDENCE.md)")
