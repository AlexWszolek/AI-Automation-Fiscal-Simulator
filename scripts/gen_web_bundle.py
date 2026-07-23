"""Generate the web front end's Python-derived artifacts — the zero-drift set.

Everything the TS side needs to know about the model's UI surface is GENERATED here from
fiscal_model.app_params / presets, never hand-maintained:

  web/src/gen/grid.json           UI_GRID + CUSTOM_DEFAULTS + per-preset widget defaults +
                                  preset/overlay metadata (incl. provenance text)
  web/src/gen/codec_vectors.json  golden parse/encode vectors for the TS port of the URL codec —
                                  every case is produced by CALLING the Python codec, so the TS
                                  implementation is pinned to the real behavior, not to a spec

Stage 2 (added with fiscal_model/webpayload.py) also emits the static scenario bundles:

  web/public/data/scenarios/<slug>.json   full ScenarioPayload per config × overlay subset
  web/public/data/tornado.json            slug-keyed tornado entries re-keyed from
                                          data/app_precomputed/mc_tornado.json

Deterministic by construction (no timestamps, sorted keys) — tests/test_web_gen.py regenerates
in-memory and asserts equality with the committed files, the test_app_precomputed pattern.

Run:  .venv/bin/python scripts/gen_web_bundle.py [--grid-only]
"""
from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fiscal_model import app_params as ap                       # noqa: E402
from fiscal_model import presets as presets_mod                 # noqa: E402

WEB_GEN = ROOT / "web" / "src" / "gen"
WEB_DATA = ROOT / "web" / "public" / "data"


# ------------------------------------------------------------------ grid.json
def build_grid() -> dict:
    grid = {}
    for key, (lo, hi, step, typ) in ap.UI_GRID.items():
        if typ is bool:
            grid[key] = {"type": "bool"}
        elif typ is str:
            grid[key] = {"type": "enum", "values": list(lo)}
        else:
            grid[key] = {"type": "int" if typ is int else "float",
                         "lo": lo, "hi": hi, "step": step}

    def defaults_json(d: dict) -> dict:
        return {k: (bool(v) if isinstance(v, bool) else v) for k, v in d.items()}

    presets = []
    for key, p in presets_mod.PRESETS.items():
        v2p = presets_mod.to_params(p)
        prov = {}
        for fld, src in p.provenance.items():
            val = getattr(v2p, fld, None)
            prov[fld] = {"text": src,
                         "value": f"{val:g}" if isinstance(val, float) else None}
        presets.append({
            "key": key, "name": p.name, "blurb": p.blurb,
            "start_year": p.start_year, "n_periods": v2p.n_periods,
            "adoption_start": p.adoption_start, "adoption_end": p.adoption_end,
            "adoption_reach_year": p.adoption_reach_year,
            "defaults": defaults_json(ap.preset_widget_defaults(p)),
            "override_fields": sorted(set(p.overrides) | {"adoption_path"}),
            "provenance": prov,
        })

    overlays = [{"key": k, "name": o.name, "blurb": o.blurb}
                for k, o in presets_mod.OVERLAYS.items()]

    return {"grid": grid,
            "custom_defaults": defaults_json(dict(ap.CUSTOM_DEFAULTS)),
            "presets": presets,
            "overlays": overlays,
            "start_year_custom": 2026}


# ------------------------------------------------------------------ codec_vectors.json
def build_codec_vectors() -> dict:
    """Golden vectors by CALLING the Python codec — the TS port must reproduce every one."""
    parse_cases = []

    def parse_case(qp: dict):
        parse_cases.append({"qp": {k: str(v) for k, v in qp.items()},
                            "expect": ap.parse_query_config({k: str(v) for k, v in qp.items()})})

    # per-key: on-grid, off-grid (snap), below-lo, above-hi, garbage
    for key, (lo, hi, step, typ) in ap.UI_GRID.items():
        if typ is bool:
            for raw in ("1", "0", "true", "banana"):
                parse_case({key: raw})
        elif typ is str:
            parse_case({key: lo[0]})
            parse_case({key: "not-a-value"})
        else:
            mid = lo + (hi - lo) / 2
            k = round((mid - lo) / step)
            on_grid = lo + k * step
            parse_case({key: f"{on_grid:.10g}"})
            parse_case({key: f"{on_grid + step * 0.37:.10g}"})     # off-grid → snap
            parse_case({key: f"{lo - abs(hi) - 1}"})               # below → clamp
            parse_case({key: f"{hi + abs(hi) + 1}"})               # above → clamp
            parse_case({key: "garbage"})
    # presets / overlays / junk keys / dual robot tax
    parse_case({"preset": "agi-5y", "ov": "ubi,compute-parity", "cog": "0.9"})
    parse_case({"preset": "nope", "ov": "ubi,bogus,cw-robot-tax,grt-robot-tax",
                "unknown_key": "1", "cog": "banana"})
    parse_case({"preset": "ai2040-plan-a"})
    parse_case({"ov": "grt-robot-tax"})
    parse_case({"cog": "0.837", "demand": "99", "ubi": "-5", "rate_cap": "0.1499",
                "state_resp": "raise_rates"})

    encode_cases = []

    def encode_case(preset_key, overlays, current, pristine):
        encode_cases.append({
            "preset": preset_key, "overlays": overlays,
            "current": current, "pristine": pristine,
            "expect": ap.encode_query_config(preset_key, overlays, current, pristine)})

    for key, p in presets_mod.PRESETS.items():
        pristine = ap.preset_widget_defaults(p)
        encode_case(key, [], dict(pristine), dict(pristine))                 # pristine → preset only
        cur = dict(pristine, cog=min(1.0, round(pristine["cog"] + 0.1, 10)))
        encode_case(key, ["ubi"], cur, dict(pristine))                       # one diff + overlay
        echo = dict(pristine, cog=pristine["cog"] + 1e-12)                   # JS-double echo → no param
        encode_case(key, [], echo, dict(pristine))
    cd = dict(ap.CUSTOM_DEFAULTS)
    encode_case(None, [], dict(cd, ubi=12_000, unbounded=True, demand=1.0), dict(cd))
    encode_case(None, ["cw-robot-tax"], dict(cd, rob_base=1.5, reab_baumol=0.4), dict(cd))

    return {"parse": parse_cases, "encode": encode_cases}


# ------------------------------------------------------------------ column-guide.csv
# Every per-year output column: variable, plain meaning, units. Downloaded alongside the
# detail CSV so no export leaves the site unexplained. _B = billions of dollars/year unless
# marked cumulative; _M = millions of workers; every value is a CHANGE vs the no-AI baseline
# unless marked absolute/level.
COLUMN_GUIDE = [
    ("period", "Period", "Simulation year index (0 = the scenario's start year)", "integer"),
    ("adoption", "Adoption ceiling", "Cumulative adoption ceiling in force that year (share of feasible work)", "0-1"),
    ("employed_M", "Employed", "Still employed at their original job and wage", "millions"),
    ("on_ui_M", "On UI", "Displaced, drawing unemployment insurance", "millions"),
    ("exhausted_M", "Exhausted UI", "Displaced, UI exhausted, no benefits", "millions"),
    ("reabsorbed_M", "Re-employed", "Re-employed at the lower service wage", "millions"),
    ("exited_M", "Exited to SSDI", "Left the labor force onto SSDI", "millions"),
    ("induced_M", "Demand layoffs", "Laid off by the demand shortfall (second round)", "millions"),
    ("retired_M", "Retired", "Retired via natural attrition (fiscally neutral)", "millions"),
    ("population_M", "Modeled population", "Sum of the seven worker states = the 154.0M modeled baseline", "millions"),
    ("max_cell_resid_M", "Conservation residual", "Largest per-cell conservation residual (should be ~0)", "millions"),
    ("employment_drop_pct", "Employment decline %", "Decline in original-wage employment vs the modeled baseline", "%"),
    ("revenue_lost_B", "Labor taxes lost", "Labor-tax revenue lost (income + payroll, fed + state)", "$B/yr"),
    ("revenue_lost_pct", "Labor taxes lost %", "Same, as a share of baseline labor-tax revenue", "%"),
    ("transfers_added_B", "Transfers added", "New transfer outlays incl. UI (fed + state)", "$B/yr"),
    ("inc_fed_loss_B", "Fed income tax lost", "Federal individual income tax lost", "$B/yr"),
    ("payroll_fed_loss_B", "Payroll tax lost", "Federal payroll (FICA) tax lost", "$B/yr"),
    ("inc_state_loss_B", "State income tax lost", "State income tax lost", "$B/yr"),
    ("cons_state_loss_B", "State consumption tax lost", "State consumption tax lost", "$B/yr"),
    ("transfer_fed_B", "Fed transfers", "Federal means-tested transfer outlays added", "$B/yr"),
    ("transfer_state_B", "State transfers", "State means-tested transfer outlays added", "$B/yr"),
    ("ui_outlay_fed_B", "UI benefits paid", "Unemployment-insurance benefits paid", "$B/yr"),
    ("ui_tax_fed_B", "Tax on UI benefits", "Income tax collected on those UI benefits", "$B/yr"),
    ("ssdi_outlay_B", "SSDI outlays", "SSDI outlays on labor-force leavers", "$B/yr"),
    ("ubi_outlay_B", "UBI outlay (gross)", "Gross UBI outlay", "$B/yr"),
    ("ubi_recapture_B", "UBI recaptured", "UBI recaptured (income-tax clawback + benefit crowd-out)", "$B/yr"),
    ("ubi_required_rate", "UBI self-funding rate", "Average tax rate on the eroded base a self-funding UBI would need", "fraction"),
    ("automation_tax_B", "Robot tax", "Robot-tax revenue on the automated compensation bill", "$B/yr"),
    ("saved_bill_B", "Automated comp bill", "Compensation bill of all automated jobs (cumulative stock)", "$B/yr"),
    ("automation_spend_B", "Compute & automation spend", "Of that, spent on compute & automation inputs", "$B/yr"),
    ("net_saving_B", "Net saving", "Saved bill net of automation spend", "$B/yr"),
    ("retained_profit_B", "Kept as profit", "Net saving kept as corporate profit", "$B/yr"),
    ("price_reduction_B", "Price cuts", "Net saving passed to consumers as lower prices", "$B/yr"),
    ("survivor_gains_B", "Routed to raises", "Net saving routed to raises for remaining staff", "$B/yr"),
    ("corp_offset_B", "Corporate recapture", "Corporate/capital tax recovered on retained profit", "$B/yr"),
    ("compute_pool_tax_B", "Compute-pool tax", "Tax collected on the compute-capital pool", "$B/yr"),
    ("offshore_leak_B", "Offshore leak", "Compute spending leaked offshore untaxed (0 at shipped)", "$B/yr"),
    ("W_survivor", "Survivor wage index", "Wage index of the still-employed (1.0 = baseline)", "index"),
    ("W_survivor_mech", "Survivor wage (funded part)", "Its mechanical (funded-raise) component", "index"),
    ("W_reab", "Re-employed wage index", "Wage index of the re-employed (Baumol vs crowding; 1.0 = baseline)", "index"),
    ("refuge_capacity", "Refuge capacity", "Un-automated share of the low-exposure refuge (scales re-employment)", "0-1"),
    ("survivor_gain_fed_B", "Fed tax from raises", "Extra federal tax from survivor raises", "$B/yr"),
    ("survivor_gain_state_B", "State tax from raises", "Extra state tax from survivor raises", "$B/yr"),
    ("survivor_wage_cost_B", "Cost of raises", "What the standing raises cost firms", "$B/yr"),
    ("survivor_overflow_profit_B", "Raise overflow → profit", "Raises above the ceiling spilled to profit", "$B/yr"),
    ("survivor_overflow_price_B", "Raise overflow → prices", "Raises above the ceiling spilled to prices", "$B/yr"),
    ("survivor_overflow_corp_tax_B", "Tax on overflow profit", "Corporate tax recovered on the profit spill", "$B/yr"),
    ("survivor_market_frac", "Market wage response", "Market wage response applied this year (elasticity x slack)", "fraction"),
    ("survivor_slack_prev", "Prior-year slack", "Last year's labor-market slack (the market response input)", "fraction"),
    ("income_surcharge_fed_B", "Income surcharge (fed)", "Baseline revenue from the income-tax multiplier (federal)", "$B/yr"),
    ("income_surcharge_state_B", "Income surcharge (state)", "Baseline revenue from the income-tax multiplier (state)", "$B/yr"),
    ("corp_surcharge_fed_B", "Capital surcharge (fed)", "Baseline revenue from the capital-tax multiplier (federal)", "$B/yr"),
    ("corp_surcharge_state_B", "Capital surcharge (state)", "Baseline revenue from the capital-tax multiplier (state)", "$B/yr"),
    ("excise_surcharge_fed_B", "Excise surcharge (fed)", "Baseline revenue from the consumption-tax multiplier (federal)", "$B/yr"),
    ("cons_surcharge_state_B", "Consumption surcharge (state)", "Baseline revenue from the consumption-tax multiplier (state)", "$B/yr"),
    ("fed_deficit_B", "Deficit change", "Change in the federal deficit (positive = worse)", "$B/yr"),
    ("fed_debt_B", "Debt change (cum.)", "Accumulated new federal debt incl. interest", "$B, cumulative"),
    ("fed_deficit_real_B", "Deficit change (real)", "Deficit change deflated by the price level", "$B/yr, real"),
    ("fed_debt_real_B", "Debt change (real)", "Debt change deflated by the price level", "$B, real"),
    ("fed_deficit_pct_gdp", "Deficit change % GDP", "Deficit change as a share of GDP", "%"),
    ("fed_debt_pct_gdp", "Debt change % GDP", "Debt change as a share of GDP", "%"),
    ("headline_deficit", "Headline deficit", "The deficit change in the app's chosen display unit", "$B or %"),
    ("fed_revenue_B", "Federal revenue (level)", "ABSOLUTE federal revenue (baseline + all changes)", "$B/yr, level"),
    ("fed_deficit_abs_B", "Federal deficit (level)", "ABSOLUTE federal deficit (baseline + shock)", "$B/yr, level"),
    ("fed_deficit_abs_pct_gdp", "Deficit % GDP (level)", "Absolute deficit as a share of trend-grown GDP", "%"),
    ("price_level", "Price level", "Price index (1.0 = baseline; price cuts deflate it)", "index"),
    ("productivity_index", "Real output index", "Real output index (1.0 = baseline)", "index"),
    ("state_net_total_B", "State net loss", "Combined state revenue loss net of gains (positive = loss)", "$B/yr"),
    ("state_gap_B", "State shortfall", "Shortfall states must close that year, pre-response", "$B/yr"),
    ("state_gap_cum_B", "State shortfall (cum.)", "That shortfall accumulated over the run", "$B, cumulative"),
    ("state_gap_pct_gdp", "State shortfall % GDP", "The shortfall as a share of GDP", "%"),
    ("state_rate_hike_B", "Closed by rate hikes", "Closed by state tax-rate increases", "$B/yr"),
    ("state_spending_cut_B", "Closed by spending cuts", "Closed by state spending cuts (incl. forced at the cap)", "$B/yr"),
    ("state_close_residual_B", "Close residual", "Unclosed remainder (should be ~0)", "$B/yr"),
    ("n_states_capped", "States at rate cap", "States that hit the rate-hike cap", "count"),
    ("state_balanced", "All states balanced", "All 51 states balanced within tolerance", "bool"),
    ("state_fiscal_position_B", "State revenue (level)", "ABSOLUTE state+local revenue position", "$B/yr, level"),
    ("induced_pending_M", "Queued demand flow", "Demand-driven employment flow queued for next year (signed)", "millions"),
    ("swf_revenue_B", "SWF profit share", "Sovereign-wealth-fund equity share of after-corporate-tax automation profit (overlay)", "$B/yr"),
    ("fed_vat_B", "Federal VAT", "Federal VAT revenue on a 2/3-of-value-added consumption base, eroding with the standing income withdrawal (overlay)", "$B/yr"),
    ("standing_withdrawal_B", "Standing withdrawal", "The standing demand withdrawal the induced stock tracks", "$B, level"),
]


def emit_column_guide() -> None:
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["column", "short_name", "meaning", "units"])
    for row in COLUMN_GUIDE:
        w.writerow(row)
    path = WEB_DATA / "column-guide.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue())
    print(f"wrote {path.relative_to(ROOT)}")
    names = {col: short for col, short, _m, _u in COLUMN_GUIDE}
    _dump(names, WEB_GEN / "column_names.json")


# ------------------------------------------------------------------ writers
def _dump(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, allow_nan=False) + "\n")
    print(f"wrote {path.relative_to(ROOT)}")


def emit_scenarios() -> None:
    """Stage 2: static ScenarioPayload bundles + slug-keyed tornado. Requires build artifacts."""
    from fiscal_model import loaders, mc, webpayload
    from fiscal_model.dynamics import precompute_worker_deltas
    from fiscal_model.kernel import KernelParams
    from fiscal_model.transfers import TransferLookup

    data = loaders.load_all(validate=False)
    deltas = precompute_worker_deltas(data, TransferLookup(), KernelParams())

    configs = [None] + list(presets_mod.PRESETS)                 # None = custom defaults
    ov_keys = list(presets_mod.OVERLAYS)
    subsets = [list(c) for r in range(len(ov_keys) + 1) for c in combinations(ov_keys, r)
               if not {"cw-robot-tax", "grt-robot-tax"} <= set(c)]
    n = 0
    ctx_cache: dict[str, mc.ScenarioContext] = {}
    pool: dict = {}
    for preset in configs:
        for ovs in subsets:
            cfg = {"preset": preset, "overlays": ovs, "levers": {}}
            payload = webpayload.build_scenario_payload(data, deltas, cfg, ctx_cache=ctx_cache,
                                                        pool=pool)
            _dump(payload, WEB_DATA / "scenarios" / f"{webpayload.slug(cfg)}.json")
            n += 1
    print(f"{n} scenario bundles")

    # tornado: re-key the committed precompute by slug (every pristine preset × overlay cart)
    src = json.loads((ROOT / "data" / "app_precomputed" / "mc_tornado.json").read_text())
    by_repr = {e["cfg_repr"]: e for e in src["entries"]}
    out = {}
    for preset in configs:
        for ovs in subsets:
            cfg = {"preset": preset, "overlays": ovs, "levers": {}}
            rep = webpayload.cfg_repr_for(cfg)
            e = by_repr.get(rep)
            assert e is not None, f"precomputed tornado missing for {webpayload.slug(cfg)} — " \
                                  "re-run scripts/precompute_app_mc.py"
            out[webpayload.slug(cfg)] = {"tornado": e["tornado"], "p10": e["p10"], "p50": e["p50"],
                                         "p90": e["p90"], "n": src["n"]}
    _dump(out, WEB_DATA / "tornado.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid-only", action="store_true",
                        help="emit grid.json + codec_vectors.json only (no model runs)")
    args = parser.parse_args()
    _dump(build_grid(), WEB_GEN / "grid.json")
    _dump(build_codec_vectors(), WEB_GEN / "codec_vectors.json")
    emit_column_guide()
    if not args.grid_only:
        emit_scenarios()


if __name__ == "__main__":
    main()
