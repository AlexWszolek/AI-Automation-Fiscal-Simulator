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
NEG, POS = "#8c2f28", "#5b7c99"   # oxblood = fiscally bad, muted slate blue = good (no green)

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
    "W_reab": "Wage index of the re-employed (1.0 = baseline)",
    "survivor_gain_fed_B": "Extra federal tax from raises",
    "survivor_wage_cost_B": "What the raises cost firms",
    "employment_drop_pct": "Employment decline", "revenue_lost_pct": "Labor-tax revenue decline",
}


_LEARN_MORE_MD = """#### The data

The model is anchored to the 2024 US economy as the statistical agencies measured it. Every input file carries control totals that are re-asserted on every run — 163.2 million workers, \\$15.0 trillion in total compensation, \\$29.3 trillion GDP, \\$4,983 billion in federal receipts — and a load that fails to reconcile stops before a single scenario is computed.

| Source | What it contributes |
|---|---|
| BLS OEWS 2024 | employment and wages for 833 occupations, 71 industries, all 51 jurisdictions |
| BEA 2024 NIPA | capital income, corporate profits, and government receipts by stream |
| Yale Budget Lab AI exposure | how cognitively automatable each occupation is |
| Webb robot exposure | how physically automatable each occupation is, from robot patents |
| ACS PUMS 2024 | who workers live with — filing status, household income, children |
| PolicyEngine-US, baked offline | means-tested benefit entitlements by state, family shape, and income |
| 2025 tax schedules | the brackets and FICA parameters behind the hand-rolled tax engine |

#### How a displaced worker is priced

For each of roughly 33,000 occupation-by-state cells, the model answers one question exactly: if this worker loses this wage, what happens to every level of government? Five channels add up to the answer.

- **Income tax** — the bracket schedules re-evaluated at household income with and without the wage. No elasticities, no average rates; the lost dollars come off the top brackets first.
- **Payroll (FICA)** — the exact schedule with the Social Security cap, which kinks precisely in the wage range where AI exposure peaks.
- **Transfers** — new benefit claims looked up in the offline PolicyEngine tables, in two phases: during unemployment insurance, and after it runs out. The Medicaid and SNAP step-ups mostly arrive at UI exhaustion, not at the layoff.
- **Corporate recapture** — the wage the firm stops paying becomes taxable profit, deliberately booked at the most generous plausible rate.
- **Consumption** — state consumption taxes on the resulting drop in spending.

One design choice matters most: the model integrates over the full wage distribution inside each cell rather than pricing the average worker. Safety-net programs are humps and cliffs — the EITC rises then falls, SNAP phases out, Medicaid eligibility is a cliff — and the average-wage shortcut steps right over them, understating transfer costs by up to a factor of eight in cells that straddle a threshold.

#### The dynamic model

The simulation then runs the economy forward one year at a time:

1. An **adoption ceiling** sets how much feasible work is automated by that year — cumulative, so "60 percent by year ten" means exactly that. Physical automation ramps in later than cognitive.
2. **Firms route the saved wage bill** four ways: compute spending, retained profit, price cuts for consumers, and raises for surviving workers. Every dollar goes to exactly one destination.
3. **Survivor raises are funded** — paid out of the routed gains, never out of thin air, and taxed back through the same bracket schedules.
4. A **macro block** applies the price cuts and a productivity dividend to real output — reporting effects only; deflation is never fed into nominal tax math.
5. The **federal government** books the net loss and borrows.
6. **All 51 states must balance** their budgets every year: rate hikes up to a feasibility cap, forced spending cuts for whatever remains.
7. Lost take-home pay plus state austerity **withdraw demand**, which returns one year later as induced layoffs — a feedback loop mathematically guaranteed to converge rather than spiral, and checked at every run.

#### Why trust it

- **Conservation, enforced.** Eight accounting identities are re-verified on every period of every run: every worker sits in exactly one of seven states that sum to baseline employment; every saved dollar lands in exactly one place; the federal deficit reconciles to its labeled components; every state gap closes to zero. A new fiscal flow that skips the ledger breaks the build.
- **A hand-checkable anchor.** With every behavioral mechanism switched off, the full system reproduces the simple static calculation bit-for-bit.
- **~300 automated tests** cover the identities, each channel's numbers, and behavioral pins from the displacement literature.
- **Honest framing.** Every result is a *delta* against a no-AI baseline — what automation changes, not a forecast of the whole economy. The always-on sensitivity tornado shows exactly which assumptions move the answer, and by how much.

#### What it deliberately leaves out

- No Federal Reserve response to the demand shock — **overstates** damage in crisis scenarios.
- Corporate recapture booked at full conversion of saved wages to taxable profit — **understates** the gap (a deliberate steelman).
- No within-job augmentation (workers made more productive but kept) — overstates where augmentation dominates.
- Benefits are entitlement values, not take-up-adjusted spending — overstates transfer outlays.
- Robot exposure anchored to today's patent stock — understates the physical channel in AGI scenarios.
- No counterfactual growth in the wage base — understates losses at long horizons.

The two bolded items cut *against* the model's own thesis; the headline findings survive both.

#### Validation

Three independent external models triangulate the result. Replicating the Windfall Trust's scenario grid reproduces their sign and ordering everywhere — worse with more displacement, worse with less value capture — at roughly half their magnitudes, a wedge fully explained by their average-OECD tax base versus the actual US system. Replicating RAND's 10-point unemployment shock lands in their order of magnitude once their deflation mechanism (which this model deliberately excludes from tax math) is applied. And the Acemoglu preset's GDP gain sits inside his published ~1.1 percent bound. None of the presets are tuned to hit these targets."""


def ts_chart(df: pd.DataFrame, cols: list[str], y_title: str, kind: str = "line",
             stack: bool | None = None, height: int = 260,
             colors: list[str] | None = None, y_zero: bool = True) -> alt.Chart:
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
    enc_kw = dict(
        x=alt.X("year:Q", title=None, axis=alt.Axis(tickMinStep=1, format="d")),
        y=alt.Y("value:Q", title=y_title, stack=stack,
                scale=alt.Scale(zero=y_zero)),
        color=alt.Color("series:N", title=None, sort=labels,
                        scale=alt.Scale(domain=labels, range=colors or PALETTE[:len(labels)]),
                        legend=legend),
    )
    if kind == "area":       # stack order only; an EMPTY alt.Order() breaks vega's line sort
        enc_kw["order"] = alt.Order("color_series_sort_index:Q")
    enc = mark.encode(**enc_kw)
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
                       help="World states anchored to the published literature "
                            "(docs/PRESET_EVIDENCE.md). Selecting one loads its levers "
                            "into the sliders below, and you can tweak from there. "
                            "Government policy (robot taxes, UBI, compute taxation) is "
                            "applied separately, as overlays.")
if _choice != "Custom":
    _preset = presets_mod.PRESETS[_names[_choice]]
    sb.caption(_preset.blurb + ("" if rung1_ok else "Presets are calibrated to the "
                                "service-floor reabsorption engine — artifacts absent, running "
                                "the flat-haircut fallback degrades their fidelity."))
overlay_keys = sb.multiselect(
    "Policy responses", list(presets_mod.OVERLAYS), default=_url_cfg["overlays"],
    format_func=lambda k: presets_mod.OVERLAYS[k].name,
    help="What could government do about it? Each response is a policy from the economics "
         "literature, applied on top of the scenario by overriding the matching levers. "
         "The captions below show what each one does.")
if all(k in overlay_keys for k in ("cw-robot-tax", "grt-robot-tax")):
    sb.warning("Both robot taxes set the same lever; using Costinot-Werning, dropping GRT.")
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
    "How to use this: pick a scenario in the sidebar. Each one is a published AI forecast "
    "(Acemoglu, Korinek, AI 2027/2040, …) translated into this model's levers, with "
    "citations, and you can add policy responses on top to see how much they recover. "
    "Every number on this page is a change against a no-AI baseline: the deficits "
    "Washington already projects come first, and this is added to them. The story the "
    "accounting keeps telling is simple: the tax base migrates from wages, taxed at "
    "roughly 25-30%, to profits, prices, and compute, taxed far less, so revenue falls "
    "faster than employment — and states, which must balance their budgets every year, "
    "must either cut benefits or raise tax rates.")

# ----------------------------------------------------------------- lever groups (collapsible)
# NOTE: moving widgets between expanders does NOT disturb the keyless preset value-swap — widget
# identity hashes label/min/max/value/step/help, not the container.
rung = (1 if rung1_ok else 0)


with sb.expander("Automation & adoption", expanded=True):
    cog = st.slider("Cognitive feasibility (AI capability)", 0.0, 1.0, d["cog"], 0.05,
                    help="Of the work cognitively exposed to AI (the Yale exposure index),"
                         " the share that is technically automatable. Literature anchors "
                         "run from ~0.15 (bare LLMs, Eloundou) to ~0.55 (LLMs plus the "
                         "software they can build); 1.0 is AGI.")
    phys = st.slider("Robotics feasibility (physical work)", 0.0, 1.0, d["phys"], 0.05,
                     help="The same idea for physical work (Webb's robot-patent exposure)."
                          " Anchored to current robot technology, as dexterity and care "
                          "work score near zero even at 1.0.")
    robotics_lag = st.slider("Robotics capacity build-out lag (years)", 0, 15, d["robotics_lag"], 1,
                             help="Physical automation needs AI-driven industrial capacity"
                                  " first: the robot channel ramps in over this many years "
                                  "(0 = the capacity exists from day one).")
    rob_base = st.slider("Robot build-out growth (exponential base)", 1.0, 2.0, d["rob_base"], 0.05,
                         help="The shape of that build-out. 1.0 is a straight linear ramp;"
                              " higher values make capacity compound — robots building the"
                              " factories that build robots — so the ramp starts slow and "
                              "finishes explosively. At 1.5, half of all capacity arrives "
                              "in the last fifth of the lag.")
    adopt0 = st.slider("Automated by year 1 — % of feasible work", 0.0, 1.0, d["adopt0"], 0.01,
                       help="Where the cumulative adoption ceiling starts. Early payroll evidence "
                            "(Brynjolfsson's 'Canaries') puts the realized start near 0.02.")
    adopt1 = st.slider("Automated by the final year — % of feasible work", 0.0, 1.0, d["adopt1"], 0.01,
                       help="A cumulative diffusion ceiling: the automated stock reaches "
                            "feasibility × this share by the horizon, so 0.6 means 60% of "
                            "the feasibly-automatable jobs are automated by the end.")
    n_periods = st.slider("Horizon (years)", 3, 30, d["n_periods"],
                          help="Simulation length. Presets carry their native horizon.")
# The kinked preset path survives horizon changes (it is parametric), but moving the adoption
# sliders reverts to a linear ramp. isclose, not ==: the frontend returns min+k·step in JS doubles.
if (_preset is not None and _preset.adoption_reach_year is not None
        and math.isclose(adopt0, _preset.adoption_start, abs_tol=0.004)
        and math.isclose(adopt1, _preset.adoption_end, abs_tol=0.004)):
    adoption_path = presets_mod.build_adoption_path(_preset, n_periods)
else:
    adoption_path = list(np.linspace(adopt0, adopt1, n_periods))
    if _preset is not None and _preset.adoption_reach_year is not None:
        sb.caption(f"Adoption sliders moved: the preset's kinked path, which reached full automation at year {_preset.adoption_reach_year}, has been replaced by a linear ramp.")

with sb.expander("Labor market", expanded=False):
    reab = st.slider("Reabsorption rate / yr (0 = displacement is permanent)", 0.0, 1.0, d["reab"], 0.025,
                     help="The annual rate at which long-term displaced workers find new, "
                          "lower-wage work. The evidence runs 0.6-0.75 in normal labor "
                          "markets (Farber) and 0.05-0.10 in the China-shock adjustment; 0"
                          " makes displacement permanent. The refuge is FINITE: this rate "
                          "scales down as automation reaches the low-exposure service work"
                          " the re-employed move into, and stops entirely once it is gone.")
    haircut = st.slider("Re-employment wage cut (haircut)", 0.0, 1.0, d["haircut"], 0.01,
                        help="The re-employed earn (1 − haircut) × their old wage, floored"
                             " at a state service wage. The evidence is ~0.13 typically, "
                             "and 0.25 for high-tenure mass layoffs. A bigger cut can drop"
                             " the household into EITC/SNAP/Medicaid eligibility, which is"
                             " taken into account.")
    reab_baumol = st.slider("Re-employed wage — Baumol pull", 0.0, 1.0, d["reab_baumol"], 0.05,
                            help="How strongly re-employment wages ride the economy's "
                                 "productivity gains: the work humans still do gets "
                                 "expensive as everything else gets cheap (Baumol's cost "
                                 "disease, working in labor's favor). At 1.0, a +20% "
                                 "productivity economy pays re-employed workers +20%. This"
                                 " is how wages can RISE despite mass displacement.")
    reab_crowd = st.slider("Re-employed wage — crowding pressure", 0.0, 1.0, d["reab_crowd"], 0.05,
                           help="How strongly displaced workers flooding into service "
                                "work bid its wage down: the wage falls with last year's "
                                "labor-market slack. The China-shock evidence supports a "
                                "meaningful value; it competes directly with the Baumol "
                                "pull above.")
    ui_weeks = st.slider("UI duration (weeks)", 0, 52, d["ui_weeks"],
                         help="The unemployment-insurance window. During it, displaced "
                              "workers draw benefits (45% replacement, capped) and are "
                              "taxed on them; most means-tested benefits step up at "
                              "exhaustion, not at displacement.")
    lfp_exit = st.slider("LFP exit / SSDI rate (of exhausted)", 0.0, 0.2, d["lfp"], 0.01,
                         help="The share of benefit-exhausted workers who leave the labor "
                              "force each year onto disability insurance, an $18k/yr "
                              "outlay. This is the dominant adjustment margin in the "
                              "China-shock evidence.")
    attrition = st.slider("Natural attrition of long-term unemployed / yr", 0.0, 0.1,
                          d["attrition"], 0.005,
                          help="Retirement, mortality, and discouragement. Fiscally "
                               "neutral, as the baseline counterfactual retires too; its "
                               "role is to stop the exhausted pool from persisting "
                               "forever.")

with sb.expander("Firms & compute", expanded=False):
    retained = st.slider("Saved wages → retained profit (share)", 0.0, 1.0, d["retained"], 0.05,
                         help="Of the wage bill firms stop paying (net of automation "
                              "costs), the share kept as profit, taxed at effective "
                              "corporate rates of roughly 17-18%, which is significantly "
                              "below the labor-tax wedge it replaces.")
    price_max = round(1.0 - retained, 2)
    if price_max > 0:
        # min() keeps a preset's default legal after the user raises `retained` past it
        price = st.slider("Saved wages → lower prices (share)", 0.0, price_max,
                          min(d["price"], price_max), 0.05,
                          help="The share competed away into lower consumer prices: a real"
                               " gain to households, but taxed only through ~2% state "
                               "consumption taxes, which makes it the biggest leak in the "
                               "base-migration story.")
    else:
        price = 0.0                                  # retained = 100% → no room for price/survivor
    survivor_share = max(0.0, 1.0 - retained - price)
    st.caption(f"→ Raises for remaining staff: {survivor_share:.0%} (the remainder)")
    auto_cost = st.slider("Cost of automation (fraction of saved comp → compute)", 0.0, 1.0,
                          d["auto_cost"], 0.05,
                          help="What firms spend on compute and automation inputs per "
                               "dollar of compensation saved; it flows to the "
                               "compute-capital pool below. The evidence is 0.3-0.5 in "
                               "build-out years and ~0.05-0.10 in steady state.")
    compute_rate = st.slider("Compute pool — effective tax rate", 0.0, 0.4, d["compute_rate"], 0.01,
                             help="The effective tax on the compute-capital pool. ~0.05 is"
                                  " the post-TCJA rate on equipment and software capital; "
                                  "0.27 is parity with domestic capital (the "
                                  "compute-parity overlay).")

with sb.expander("Survivor wages", expanded=False):
    survivor_unbounded = st.checkbox("Unbounded raise (optimistic)", value=d["unbounded"],
                                     help="Removes the raise ceiling entirely, so "
                                          "survivors absorb whatever the routed share "
                                          "funds.")
    ceiling = st.slider("Raise ceiling (× baseline wage)", 1.0, 3.0, d["ceiling"], 0.1,
                        disabled=survivor_unbounded,
                        help="The cap on the still-employed wage index. Raises beyond it "
                             "spill to profit or prices (spillover below); raises "
                             "themselves are funded from the routed survivor share and "
                             "re-taxed at full marginal rates.")
    elasticity = st.slider("Market wage response to slack (− substitute / + complement)",
                           -0.5, 0.5, d["elasticity"], 0.05,
                           help="How survivors' market wages respond to labor-market "
                                "slack: negative means AI substitutes for labor and slack "
                                "pushes wages down, positive means complementarity pulls "
                                "them up (the augmentation scenario). Applied to last "
                                "year's slack.")
    spillover = st.slider("Un-absorbable raise → profit (vs prices)", 0.0, 1.0, d["spillover"], 0.05,
                          help="Where raises above the ceiling go instead: 1.0 sends all "
                               "of it to profit, which is corporate-taxed, and 0.0 sends "
                               "all of it to prices, which are nearly untaxed. This drives"
                               " the federal/state split of the overflow.")

with sb.expander("Macro & demand", expanded=False):
    price_pt = st.slider("Price pass-through (deflation → real/%-GDP views)", 0.0, 1.0,
                         d["price_pt"], 0.05,
                         help="The share of the firms' price cuts that actually deflates "
                              "the price level. By design it moves only the real and "
                              "%-of-GDP views, as nominal tax dollars are never deflated.")
    prod_pt = st.slider("Productivity dividend (full automation → +this share of GDP)", 0.0, 1.0,
                        d["prod_pt"], 0.05,
                        help="The output-weighted real-GDP gain: automating the entire "
                             "compensation bill raises GDP by this fraction. Acemoglu's "
                             "\"The Simple Macroeconomics of AI\" implies ~0.15; the micro "
                             "and AGI evidence implies 0.5-1.0. It cushions the %-of-GDP "
                             "views.")
    growth = st.slider("Baseline trend growth (nominal, %-GDP denominators)", 0.0, 0.08,
                       d["growth"], 0.005,
                       help="≈2% real + 2% inflation. Grows the GDP denominator so that "
                            "debt-to-GDP is more accurate at long horizons; nominal dollar"
                            " columns are unchanged.")
    demand = st.slider("Second-round demand multiplier", 0.0, 2.0, d["demand"], 0.05,
                       help="An Okun-style level multiplier: the induced-layoff stock "
                            "tracks the standing net income withdrawal, so UBI and raises "
                            "re-employ while austerity deepens the spiral. 0.5 "
                            "approximates an active Fed offsetting half the shock; 1.8 is "
                            "Chodorow-Reich's no-offset estimate.")

with sb.expander("Government policy", expanded=False):
    st.caption("Tax-regime dials are true flat surcharges or cuts, with 1.0 meaning "
               "current law. Each dial scales its channel's shock flows and applies the "
               "same multiplier to that channel's 2024 baseline receipts, so revenue = "
               "multiplier × (baseline − losses), and raising a dial reduces the deficit "
               "even with no automation. Scoring is static: no behavioral response, and no"
               " take-home or demand effect from the tax change itself.")
    income_mult = st.slider("Income tax multiplier", 0.5, 1.5, d["income_mult"], 0.05,
                            help="A surcharge on the $2,403B federal and $536B state "
                                 "baseline individual-income receipts, plus scaling of "
                                 "every income-tax dollar the shock moves: displaced "
                                 "losses, the raises' recapture, and the tax on UI. "
                                 "Payroll (FICA) is statutorily separate and not covered. "
                                 "Displacement sets up two opposing effects, as the "
                                 "surcharge collects more but each displaced worker also "
                                 "loses more — the surcharge dominates until the wage base"
                                 " collapses.")
    corp_mult = st.slider("Capital taxes multiplier", 0.5, 1.5, d["corp_mult"], 0.05,
                          help="A surcharge on the $492B federal and $172B state baseline "
                               "corporate receipts, plus scaling of the capital-recapture "
                               "bundle: the corporate offset including dividend and "
                               "pass-through tax, and the overflow corporate tax. The "
                               "compute-pool and robot taxes keep their own rates.")
    cons_mult = st.slider("Consumption taxes multiplier", 0.5, 1.5, d["cons_mult"], 0.05,
                          help="A surcharge on the $874B state sales-and-excise and $102B "
                               "federal excise baselines, plus scaling of the state "
                               "consumption-tax channel. This is the classic 'tax the "
                               "spending, not the wage' response; note how small these "
                               "bases are next to income taxes, as the US has no VAT to "
                               "fall back on.")
    # The robot tax is paid from retained profit, so its feasible max is retained·(1-auto_cost).
    atx_bound = round(min(0.30, retained * (1.0 - auto_cost)), 2)
    if atx_bound < 0.01:
        automation_tax = 0.0
        st.caption("Automation tax: 0% — no retained profit left to pay it (retained × (1 "
                   "− auto cost) ≈ 0).")
    else:
        automation_tax = st.slider("Automation (robot) tax — share of the automated comp bill",
                                   0.0, atx_bound, min(d["atax"], atx_bound), 0.01,
                                   help="A federal levy on the automated jobs' saved "
                                        "compensation, paid from retained profit and "
                                        "corporate-deductible. It ships at 0, as the "
                                        "literature-anchored rates live in the policy "
                                        "overlays: Costinot-Werning is roughly 0.3-1%, not"
                                        " 7%.")
    ubi = st.slider("UBI per worker / yr ($)", 0, 30_000, d["ubi"], 1_000,
                    help="A universal payment per baseline worker, booked as a federal "
                         "outlay.")
    ubi_recapture = st.slider("UBI recapture", 0.0, 0.6,
                              d["ubi_recapture"], 0.05,
                              help="The share of the UBI outlay the government gets back: "
                                   "the income-tax clawback plus the means-tested benefits"
                                   " the UBI displaces, ~20-30% in practice.")
    interest = st.slider("Interest rate on federal debt", 0.0, 0.10, d["interest"], 0.005,
                         help="New deficits accumulate into debt at this rate. ~0.04 matches the "
                              "discount-rate anchor used in the AGI presets.")


# -------------------------------------------------- page scaffolding --------------------------------
# The state-response widgets must EXECUTE before the model runs but RENDER inside the state section
# further down the page — so the blocks above them are pre-allocated container slots filled after
# the run. (Main-area widgets are keyless like the sidebar's: the preset value-swap still applies.)
main_top = st.container()      # headline metrics + preset provenance + the four chart panels

st.subheader("The states — where the shock has no shock absorber")
st.markdown(
    "Unlike the federal government, states cannot borrow their way through a revenue "
    "shock: nearly all operate under balanced-budget rules, so a shortfall has to be met "
    "within the year. How they meet it is a political choice, not an economic law, which "
    "is why it is a control here rather than an assumption: raise taxes on the people "
    "still working, cut spending, or a mix of the two. However, there are two caveats. "
    "First, legislatures lag, as rainy-day funds and deferrals mean the first year or two "
    "look like the shortfall chart rather than the closure. Second, whichever response "
    "they choose takes demand out of the same economy that is shedding jobs, which feeds "
    "the layoff spiral above.")
with st.container(border=True):
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        _sr_opts = ["mix", "raise_rates", "cut_spending"]
        state_resp = st.selectbox("What do states do?", _sr_opts,
                                  index=_sr_opts.index(d["state_resp"]),
                                  format_func={"mix": "Mix of both", "raise_rates": "Raise taxes",
                                               "cut_spending": "Cut spending"}.get,
                                  help="The closure rule for every state, every year: "
                                       "'raise taxes' raises rates on the remaining wage "
                                       "base up to the cap, 'cut spending' takes the whole"
                                       " gap out of budgets, and 'mix' splits it by the "
                                       "slider.")
    with sc2:
        state_cut_share = st.slider("Share of the gap closed by spending cuts (mix)", 0.0, 1.0,
                                    d["state_cut"], 0.05,
                                    help="Under 'mix of both', this share comes out of "
                                         "spending and the rest is sought from rate hikes,"
                                         " subject to the cap.")
    with sc3:
        rate_cap = st.slider("Max feasible rate hike (× base)", 0.1, 3.0, d["rate_cap"], 0.1,
                             help="The political and economic ceiling on rate increases. "
                                  "Once a state hits it, the remainder becomes forced "
                                  "spending cuts: the cap is where 'just raise taxes' is "
                                  "not longer a option.")
    if not rung1_ok:
        st.warning("Benefit-lookup / NOC artifacts absent — reabsorption falls back to the "
                   "flat-haircut model.")
states_rest = st.container()   # the state map/table + closure charts land here after the run

# -------------------------------------------------- v2 path (multi-actor) ----------------------------
import json as _json

ui: dict[str, Any] = dict(mapping="percentile", cog=cog, phys=phys,
          robotics_lag=float(robotics_lag), robotics_base=float(rob_base),
          adoption_path=adoption_path, n_periods=n_periods,
          retained_profit_share=retained, price_reduction_share=price, auto_cost=auto_cost,
          offshore_share=0.0, compute_effective_rate=compute_rate, survivor_unbounded=survivor_unbounded,
          survivor_raise_ceiling=ceiling, survivor_elasticity=elasticity,
          survivor_spillover_to_profit=spillover, reabsorption_rung=rung, reab=reab, haircut=haircut,
          reab_wage_baumol=reab_baumol, reab_wage_crowding=reab_crowd,
          lfp_exit_rate=lfp_exit, attrition_rate=attrition, ui_weeks=ui_weeks, price_passthrough=price_pt,
          productivity_passthrough=prod_pt, demand=demand, state_resp=state_resp,
          state_cut_share=state_cut_share, state_rate_hike_cap=rate_cap, automation_tax_rate=automation_tax,
          interest=interest, ubi=ubi, ubi_recapture_rate=ubi_recapture, baseline_growth_rate=growth,
          denominator="absolute",
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
            sb.caption(f"→ {presets_mod.OVERLAYS[_k].name} recovers \\${_rec:,.0f}B/yr of the \\${_gap:,.0f}B/yr final-year gap ({100 * _rec / _gap:.0f}%)")
        else:
            sb.caption(f"→ {presets_mod.OVERLAYS[_k].name}: the base scenario shows no final-year deficit deterioration to recover against")
    if len(overlay_keys) > 1 and _gap > 1.0:
        _allp = canon(v2p)
        _rec_all = _gap - final_metrics(cfg_key(_allp), _ctx0, _allp)["fed_deficit_B"]
        sb.caption(f"→ All selected together recover \\${_rec_all:,.0f}B/yr ({100 * _rec_all / _gap:.0f}% of the gap)")
m = DynamicModelV2(data, deltas, v2p)   # keep the model object: state_table lives on it
res = m.run()
final = res.iloc[-1]

# URL write-back: the address bar always encodes the current configuration (preset + overlays +
# only the levers that differ from the preset's own defaults). query_params writes never rerun.
_pristine = preset_widget_defaults(_preset) if _preset is not None else dict(CUSTOM_DEFAULTS)
_wvals = dict(cog=cog, phys=phys, robotics_lag=robotics_lag, rob_base=rob_base,
              adopt0=adopt0, adopt1=adopt1,
              n_periods=n_periods, reab=reab, haircut=haircut,
              reab_baumol=reab_baumol, reab_crowd=reab_crowd, ui_weeks=ui_weeks,
              lfp=lfp_exit, attrition=attrition, retained=retained, price=price,
              auto_cost=auto_cost, compute_rate=compute_rate, unbounded=survivor_unbounded,
              ceiling=ceiling, elasticity=elasticity, spillover=spillover,
              price_pt=price_pt, prod_pt=prod_pt, growth=growth, demand=demand,
              state_resp=state_resp, state_cut=state_cut_share, rate_cap=rate_cap,
              atax=automation_tax, ubi=ubi, ubi_recapture=ubi_recapture, interest=interest,
              income_mult=income_mult, corp_mult=corp_mult, cons_mult=cons_mult)
_qp = encode_query_config(_preset.key if _preset is not None else None, overlay_keys,
                          _wvals, _pristine)
if dict(st.query_params) != _qp:
    st.query_params.from_dict(_qp)
_share_qs = urlencode(_qp)

# ----------------------------------------------------------------- sidebar footer: share + about
with sb.expander("Share this configuration"):
    _app_url = getattr(getattr(st, "context", None), "url", None)
    _share_url = (f"{str(_app_url).rstrip('/')}" + (f"?{_share_qs}" if _share_qs else "")
                  if _app_url else (f"?{_share_qs}" if _share_qs else ""))
    if _share_qs or _app_url:
        st.code(_share_url or "?", language=None)
        st.caption("Anyone opening this link sees exactly this configuration: preset, "
                   "policy responses, and modified levers. The browser's address bar stays"
                   " in sync as well, so copying that also works.")
    else:
        st.caption("You are on the unmodified default configuration; the plain app URL "
                   "reproduces it.")


@st.dialog("How the model works", width="large")
def _learn_more() -> None:
    st.markdown(_LEARN_MORE_MD)


with sb.expander("About this model"):
    st.markdown(
        "A bottom-up accounting model of what AI automation does to US public finances, "
        "built for policy research and for briefing people who do not read code.\n\n"
        "**How it works.** It prices every displaced worker's taxes and benefits at the "
        "occupation-by-state level — 33,000 cells against BLS, BEA, and Census data — then "
        "follows the wages firms stop paying to where they actually go: profit, lower "
        "prices, raises for the remaining staff, and compute. Each destination is taxed at "
        "its real rate, which is the whole story: wages are taxed at roughly 25-30% and "
        "their replacements far less. All 51 states must balance their budgets every year, "
        "and the lost paychecks and state austerity feed back as further layoffs.\n\n"
        "**What it is not.** A forecast. It is a scenario calculator: the presets translate "
        "published forecasts (Acemoglu, Korinek, AI 2027, AI 2040) into the model's levers,"
        " with citations, and every number is a *change* against a no-AI baseline — the "
        "deficits CBO already projects come first, and this adds to them.\n\n"
        "**Why trust the arithmetic.** The code is open source and machine-checked: 300+ "
        "automated tests, including conservation identities re-verified on every run, so "
        "workers and dollars cannot multiply or vanish. Claude Fable 5 and Opus 4.8 wrote "
        "the code in this project under those checks.\n\n"
        "[Source code](https://github.com/AlexWszolek/AI-Automation-Fiscal-Simulator) · "
        "[Technical report](https://github.com/AlexWszolek/AI-Automation-Fiscal-Simulator/blob/main/docs/report/report.docx)"
        " · [Preset evidence](https://github.com/AlexWszolek/AI-Automation-Fiscal-Simulator/blob/main/docs/PRESET_EVIDENCE.md)")
    if st.button("Learn more — the model in 900 words"):
        _learn_more()

with main_top:
    # ----------------------------------------------------------------- v2 headline (2 × 4)
    _jobs_lost_M = final["population_M"] - final["employed_M"] - final["reabsorbed_M"] \
        - final["retired_M"]
    _inc_tax_lost_cum = res["inc_fed_loss_B"].sum()
    c = st.columns(4)
    c[0].metric("Jobs lost (final yr)", f"{_jobs_lost_M:,.1f}M",
                help="Workers not employed in the final year who would be employed under "
                     "the baseline: on unemployment insurance, exhausted, exited to SSDI, "
                     "or laid off by the demand shortfall. The re-employed and natural "
                     "retirements are excluded.")
    c[0].caption(grounding_mod.ground(_jobs_lost_M, "jobs"))
    c[1].metric("Employment", f"−{final['employment_drop_pct']:.0f}%",
                help="The decline in workers still employed at their original wage, "
                     "against the 163M baseline; the re-employed at lower wages count as "
                     "not employed here.")
    c[1].caption("share of the 163.2M baseline workforce")
    c[2].metric("Federal income tax lost (cumulative)", f"${_inc_tax_lost_cum:,.0f}B",
                help="Total federal individual income-tax revenue lost to displacement, "
                     "summed over the whole horizon. This is the single largest fiscal "
                     "channel.")
    c[2].caption(grounding_mod.ground(_inc_tax_lost_cum, "revenue_flow"))
    c[3].metric("Federal deficit (final yr)", f"${final['fed_deficit_abs_B']:,.0f}B",
                help="The absolute federal deficit at the final year: the $1,833B baseline plus "
                     "the shock's net effect. The line below restates it as a share of "
                     "productivity-and-trend-adjusted GDP.")
    c[3].caption(f"= {final['fed_deficit_abs_pct_gdp']:.1f}% of GDP")
    c2 = st.columns(4)
    c2[0].metric("Federal debt (Δ cumulative)", f"${final['fed_debt_B']:,.0f}B",
                 help="Every deficit the shock produces, accumulated with interest: the "
                      "new debt relative to the baseline path. A negative value means the "
                      "shock pays debt down, as capital recoveries outgrew the losses.")
    c2[0].caption(grounding_mod.ground(final["fed_debt_B"], "debt_stock"))
    c2[1].metric("Net fiscal impact (final yr)",
                 f"{-final['fed_deficit_B']:+,.0f}B".replace("-", "−"),
                 help="The signed change in the federal balance in the final year, where "
                      "negative is worse. It reconciles exactly to the fiscal summary "
                      "table below.")
    c2[1].caption(grounding_mod.ground(final["fed_deficit_B"], "fed_deficit_flow"))
    c2[2].metric("State shortfall (final yr)", f"${final['state_gap_B']:,.0f}B",
                 help="What states must close that year, before any rate hikes and cuts; "
                      "the state section below shows what closing it means.")
    c2[2].caption(grounding_mod.ground(final["state_gap_B"], "state_flow"))
    c2[3].metric("Real GDP effect", f"{100 * (final['productivity_index'] - 1):+.1f}%",
                 help="The productivity dividend: real output against the baseline. In "
                      "severe scenarios this is large and positive while the fiscal "
                      "picture collapses, as the abundance arrives as profit and lower "
                      "prices, not as taxed wages.")
    c2[3].caption("real output vs the no-AI baseline")

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
            st.caption("Anchors from `docs/PRESET_EVIDENCE.md`, with every number verified"
                       " against the cited paper; the verbatim quotes and URLs live in "
                       "`docs/research/preset-evidence-raw.json`.")
            for _fld, _src in _preset.provenance.items():
                _val = getattr(_pp, _fld, None)
                st.markdown(f"- **{_fld}**{f' = `{_val:g}`' if isinstance(_val, float) else ''} — {_src}")

    left, right = st.columns(2)
    with left:
        st.subheader("Where the workforce goes")
        # Employed is ~90% of the area — a pale fill lets the distress bands carry the color
        _wf_colors = ["#c9d7e4", "#d9a441", "#b3554d", "#5b7c99", "#7d6ca3", "#8f2a1d", "#b9b2a6"]
        show_chart(ts_chart(res, ["employed_M", "on_ui_M", "exhausted_M", "reabsorbed_M",
                                  "exited_M", "induced_M", "retired_M"],
                            "millions of workers", kind="area", stack=True, height=300,
                            colors=_wf_colors),
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
        show_chart(ts_chart(res, ["induced_M"], "millions of workers", kind="area"),
                   "Jobs lost because displaced households stopped spending and states cut budgets. "
                   "The stock tracks the standing income withdrawal — stimulus (UBI, raises) visibly "
                   "re-employs these workers.")
        st.subheader("Wages of the still-employed")
        _wage_cols = ["W_survivor"] + (["W_reab"] if v2p.reab_wage_baumol or v2p.reab_wage_crowding
                                       else [])
        show_chart(ts_chart(res, _wage_cols, "wage index (1.0 = baseline)", y_zero=False),
                   "The wage index of workers who keep their jobs: raises funded from the survivor "
                   "share push it up; labor-market slack (substitution) pulls it down."
                   + (" The re-employed line is the Baumol-vs-crowding tug of war on service wages."
                      if len(_wage_cols) > 1 else ""))
        show_chart(ts_chart(res, ["survivor_gain_fed_B", "survivor_wage_cost_B"], "$ billions / year"),
                   "The same channel in dollars: what the raises cost firms vs the extra federal tax "
                   "they generate — the one mechanism that rebuilds the labor tax base.")

    if v2p.ubi_annual > 0 and final["ubi_required_rate"] > 1.0:   # v2p, not the slider: overlays add UBI too
        st.warning(f"A \\${v2p.ubi_annual:,.0f}/yr UBI requires a {final['ubi_required_rate']:.0%} average tax rate on the eroded base by the final year, and a required rate above 100% means the UBI cannot be funded from this base at all.")


with states_rest:
    _stbl = m.state_table
    _tax_base = float(_stbl["taxable_base_B"].sum())
    _implied = 100.0 * final["state_gap_B"] / _tax_base if _tax_base > 0 else 0.0
    if final["state_gap_B"] > 1:
        st.markdown(f"Closing the final-year gap with taxes alone would mean raising state taxes roughly {_implied:,.1f}% on everyone still working. That is what a \\${final['state_gap_B']:,.0f}B shortfall means against a \\${_tax_base:,.0f}B remaining wage base, and {int(final['n_states_capped'])} of 51 states hit the rate-hike cap under the current response.")
    _sv1, _sv2 = st.columns([1, 3])
    state_view = _sv1.radio("View", ["Map", "Table"], horizontal=True, label_visibility="collapsed")
    if state_view == "Map":
        # binned threshold scale on the state's OWN revenue at stake — a small state losing
        # 8% of its receipts reads dark even though its $B loss is a rounding error next to
        # California's. Below 0 (a net gain) is the single green bin.
        _loss_scale = alt.Scale(type="threshold", domain=[0.0, 1.0, 2.5, 5.0, 10.0],
                                range=["#5b7c99", "#fbe6df", "#f2b8a4", "#e08165",
                                       "#c65540", "#8c2f28"])
        st.altair_chart(charts_mod.state_choropleth(
            _stbl, "revenue_loss_pct", "Revenue lost (% of the state's own tax receipts)",
            tooltip=[("revenue_loss_pct", "Revenue lost (% of state receipts)", ",.1f"),
                     ("net_B", "Net position ($B, − = surplus)", ",.1f"),
                     ("shortfall_B", "Shortfall to close ($B)", ",.1f"),
                     ("rate_hike_B", "Closed by rate hikes ($B)", ",.1f"),
                     ("spending_cut_B", "Closed by spending cuts ($B)", ",.1f"),
                     ("implied_rate_hike_pct", "Implied rate hike (%)", ",.1f")],
            neg_color=POS, pos_color=NEG, scale=_loss_scale),
            width='stretch', theme=None)
        st.caption("Final-year loss as a share of each state's own tax revenue — the "
                   "measure of how hard the shock hits that state's budget, not how big "
                   "the state is. Hover any state for the dollar figures: its net "
                   "position, the shortfall, how the chosen response closes it, and the "
                   "implied rate hike on its remaining workers. Green states come out "
                   "ahead. (Map shapes load from a CDN, so if the map is blank, switch to "
                   "Table. DC is on the map but easier to find in the Table.)")
    else:
        _st_disp = (_stbl.sort_values("shortfall_B", ascending=False).reset_index(drop=True)
                    .drop(columns="taxable_base_B")
                    .rename(columns={
                        "state": "State", "net_B": "Net position ($B, − = surplus)",
                        "revenue_loss_pct": "Revenue lost (% of state receipts)",
                        "shortfall_B": "Shortfall ($B)", "rate_hike_B": "Rate hikes ($B)",
                        "spending_cut_B": "Spending cuts ($B)",
                        "implied_rate_hike_pct": "Implied rate hike (% of base)",
                        "at_cap": "Hit rate cap"}))
        st.dataframe(_st_disp.style.format({c: "{:,.1f}" for c in _st_disp.columns
                                            if c not in ("State", "Hit rate cap")}),
                     width='stretch', hide_index=True, height=420)
        st.caption("A state 'hits the cap' when the rate increase it needs exceeds the "
                   "feasibility ceiling, and the remainder becomes forced spending cuts. "
                   "Negative net positions are states whose survivor-wage gains outweigh "
                   "their losses.")
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
    _detail = res.round(4)
    _detail.insert(0, "year", (start_year + _detail["period"]).astype(int))
    st.dataframe(_detail.style.format("{:,.2f}", subset=[c for c in _detail.columns
                                                         if c not in ("year", "period")]),
                 width='stretch')
    st.caption("Every column the model produces, per year: the source data behind every "
               "chart and table on this page. Columns ending in _B are billions of "
               "dollars; _M, millions of workers.")
    st.download_button("Download full detail CSV", _detail.to_csv(index=False).encode("utf-8"),
                       "run-detail.csv", "text/csv")
else:
    fs_units = fs2.radio("Units", ["$B", "% of projected federal revenue (CBO)"], horizontal=True,
                         help="The CBO view divides each year by that same year's "
                              "projected total federal revenue (February 2026 baseline), "
                              "answering how big the shock is against the money the "
                              "government actually expects to have.")
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
              .map(lambda v: "color: #8c2f28" if isinstance(v, float) and v < -0.05 else
                             ("color: #5b7c99" if isinstance(v, float) and v > 0.05 else ""),
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
    st.download_button("Download summary CSV", summary_mod.to_csv_bytes(fs_df), "fiscal-summary.csv", "text/csv")

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
    "robotics_base": "Robot build-out growth (base)",
    "adoption_end": "How much feasible work is automated",
    "ui_weeks": "UI benefit duration",
    "reabsorption_rate": "Re-employment rate",
    "reemployment_haircut": "Re-employment wage cut",
    "reab_wage_baumol": "Re-employed wage: Baumol pull",
    "reab_wage_crowding": "Re-employed wage: crowding",
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
        st.caption("**Settings changed — updating the sensitivity analysis in a few "
                   "seconds…** (showing the previous configuration meanwhile)")
    st.altair_chart(chart, width='stretch', theme=None)
    st.caption(f"Each bar shows how strongly one assumption drives the final-year deficit, across {n_draws} model runs that jitter every live assumption ±15% around your settings; red means raising it worsens the deficit, blue means it improves it. Across those runs the final-year deficit increase stays between \\${entry['p10']:,.0f}B and \\${entry['p90']:,.0f}B (P10-P90). That band measures robustness to mis-calibrated assumptions within this scenario — the honest uncertainty about the future is the spread across the scenario presets themselves.")


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
            st.caption("Sensitivity analysis starts a few seconds after you stop moving "
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
