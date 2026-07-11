"""Deterministic report artifact builder — every figure, table, and citable number in the report.

Stages (composable via --stage; default = all):
  compute     per-preset MC (N draws, seeded) -> parquet/CSVs + overlay recovery runs
  validation  Windfall 3x2 grid, RAND-S3 replication, Acemoglu GDP check
  render      PNGs from the cached CSVs (re-runs without the model)
Outputs land in docs/report/artifacts/; manifest.json (written last, atomically) is the DRIFT
FIREWALL: the report prose may cite numbers ONLY through {{n:...}} placeholders resolved against
it, so text and model can never disagree silently.

Usage:
  .venv/bin/python scripts/report_artifacts.py                    # full build (~35-45 min)
  .venv/bin/python scripts/report_artifacts.py --n 50             # smoke (~3 min)
  .venv/bin/python scripts/report_artifacts.py --preset ai-2027   # one preset
  .venv/bin/python scripts/report_artifacts.py --stage render     # re-render PNGs only
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from fiscal_model import charts, government, loaders, mc, presets, reabsorption, summary
from fiscal_model.dynamics import precompute_worker_deltas
from fiscal_model.kernel import KernelParams
from fiscal_model.levers_v2 import DEFAULTS_SHIPPED
from fiscal_model.transfers import TransferLookup

SEED, N_DRAWS, SPREAD = 0, 1000, 0.15
ART = Path(__file__).resolve().parent.parent / "docs" / "report" / "artifacts"
FAN_METRICS = (("fed_deficit_B", "fan_deficit", "federal deficit Δ ($B)"),
               ("fed_debt_B", "fan_debt", "federal debt Δ cumulative ($B)"),
               ("employment_drop_pct", "fan_employment", "employment drop (%)"))


@dataclass
class Env:
    data: loaders.FiscalData
    deltas: pd.DataFrame
    ledger: government.RevenueLedger


def load_env() -> Env:
    print("loading data + caches…")
    data = loaders.load_all(validate=False)
    deltas = precompute_worker_deltas(data, TransferLookup(), KernelParams())
    return Env(data, deltas, government.RevenueLedger(data))


# --------------------------------------------------------------------------- helpers / metrics
def net_fiscal(res: pd.DataFrame) -> pd.Series:
    return -res["fed_deficit_B"]                       # summary.py sign convention


def cum10(series: pd.Series) -> float:
    return float(series.iloc[:10].sum())               # truncated at min(10, n) for comparability


def cum10_total_revenue_pct(res: pd.DataFrame, ledger) -> float:
    """The Windfall comparison metric: 10y average total (fed + pre-close state) revenue change as
    % of baseline. State side is revenue-only and PRE-close (they model no balanced-budget close)."""
    fed_delta = res["fed_revenue_B"] - ledger.fed_revenue0
    state_delta = (-res["inc_state_loss_B"] - res["cons_state_loss_B"]
                   + res["survivor_gain_state_B"])
    n = min(10, len(res))
    return float(100.0 * (fed_delta.iloc[:n].sum() + state_delta.iloc[:n].sum())
                 / (n * (ledger.fed_revenue0 + ledger.state_revenue0)))


def u_proxy_pct(res: pd.DataFrame) -> pd.Series:
    """RAND-comparable unemployment proxy: employment_drop_pct counts the reabsorbed as
    non-employed forever; on_ui+exhausted+induced over the baseline workforce recovers."""
    return 100.0 * (res["on_ui_M"] + res["exhausted_M"] + res["induced_M"]) / res["population_M"]


def pcts_of(df: pd.DataFrame, col: str) -> dict:
    final = df[df["period"] == df["period"].max()]
    return {f"p{int(p)}": round(float(np.percentile(final[col], p)), 2) for p in mc.PCTS}


# --------------------------------------------------------------------------- per-preset stage
def build_preset(env: Env, key: str, n: int, spread: float, seed: int) -> tuple[dict, mc.ScenarioContext]:
    p = presets.PRESETS[key]
    base = presets.to_params(p)
    out = ART / "presets" / key
    out.mkdir(parents=True, exist_ok=True)
    ctx = mc.ScenarioContext(env.data, env.deltas, base)
    t0 = time.perf_counter()
    r = mc.run_mc(ctx, n=n, spread=spread, seed=seed,
                  progress=lambda i, tot: print(f"\r  {key}: draw {i}/{tot}", end="", flush=True))
    print(f"  ({time.perf_counter() - t0:.0f}s)")

    r.draws.to_parquet(out / "draws.parquet", index=False)
    r.paths.to_parquet(out / "paths.parquet", index=False)
    r.percentiles.to_csv(out / "percentiles.csv", index=False)
    r.base_run.to_csv(out / "base_run.csv", index=False)
    for grouping in ("tax", "channel"):
        summary.build_fiscal_summary(r.base_run, env.ledger, grouping, "busd").to_csv(
            out / f"summary_{grouping}.csv", index=False)

    figures = {}
    for metric, fname, y_title in FAN_METRICS:
        charts.save_png(charts.fan_chart(r.percentiles, r.base_run, metric, y_title, title=p.name),
                        out / f"{fname}.png")
        figures[fname] = f"presets/{key}/{fname}.png"
    charts.save_png(charts.tornado_chart(r.tornado, "final_fed_deficit_B", title=p.name),
                    out / "tornado_deficit.png")
    figures["tornado_deficit"] = f"presets/{key}/tornado_deficit.png"

    fin = r.base_run.iloc[-1]
    top = r.tornado.query("target == 'final_fed_deficit_B'").head(5)
    frag = {
        "name": p.name, "blurb": p.blurb, "n_periods": int(base.n_periods),
        "adoption_start": p.adoption_start, "adoption_end": p.adoption_end,
        "final": {
            "employment_drop_pct": round(float(fin["employment_drop_pct"]), 1),
            "fed_deficit_delta_B": round(float(fin["fed_deficit_B"]), 1),
            "net_fiscal_impact_B": round(float(-fin["fed_deficit_B"]), 1),
            "fed_deficit_abs_B": round(float(fin["fed_deficit_abs_B"]), 1),
            "fed_deficit_abs_pct_gdp": round(float(fin["fed_deficit_abs_pct_gdp"]), 1),
            "fed_debt_B": round(float(fin["fed_debt_B"]), 1),
            "state_gap_B": round(float(fin["state_gap_B"]), 1),
            "fed_revenue_B": round(float(fin["fed_revenue_B"]), 1),
            "n_states_capped": int(fin["n_states_capped"]),
            "induced_M": round(float(fin["induced_M"]), 2),
            "productivity_gain_pct": round(100.0 * (float(fin["productivity_index"]) - 1.0), 2),
        },
        "cumulative": {
            "net_fiscal_impact_B": round(float(net_fiscal(r.base_run).sum()), 1),
            "cum10_net_fiscal_impact_B": round(cum10(net_fiscal(r.base_run)), 1),
            "cum10_pct_of_baseline_fed_revenue": round(
                cum10(net_fiscal(r.base_run)) / (min(10, len(r.base_run)) * env.ledger.fed_revenue0)
                * 100.0, 2),
            "state_gap_B": round(float(r.base_run["state_gap_B"].sum()), 1),
            "cum10y_total_revenue_pct": round(cum10_total_revenue_pct(r.base_run, env.ledger), 2),
        },
        "mc": {
            "final_fed_deficit_B": pcts_of(r.paths, "fed_deficit_B"),
            "final_employment_drop_pct": pcts_of(r.paths, "employment_drop_pct"),
            "top_deficit_levers": [{"lever": t.lever, "spearman": round(float(t.spearman), 2)}
                                   for t in top.itertuples()],
        },
        "figures": figures,
    }
    return frag, ctx


# --------------------------------------------------------------------------- overlays stage
def build_overlays(env: Env, key: str, ctx: mc.ScenarioContext, base_run: pd.DataFrame) -> dict:
    base = presets.to_params(presets.PRESETS[key])
    cum_gap = float(base_run["fed_deficit_B"].sum())
    frag = {}
    for ok in presets.OVERLAYS:
        v2p, notes = presets.apply_overlays(base, [ok])
        res = ctx.run(v2p)
        rec = base_run["fed_deficit_B"].to_numpy() - res["fed_deficit_B"].to_numpy()
        if ok in ("cw-robot-tax", "grt-robot-tax"):
            instrument = float(res["automation_tax_B"].sum())
        elif ok == "ubi":
            instrument = -float((res["ubi_outlay_B"] - res["ubi_recapture_B"]).sum())  # net COST
        else:
            instrument = float((res["compute_pool_tax_B"] - base_run["compute_pool_tax_B"]).sum())
        frag[ok] = {
            "final_recovery_B": round(float(rec[-1]), 1),
            "cum_recovery_B": round(float(rec.sum()), 1),
            # the ratio is meaningless when the base gap is ~zero (acemoglu runs a slight surplus)
            "pct_of_cum_gap": (round(100.0 * float(rec.sum()) / cum_gap, 1)
                               if cum_gap > 100.0 else None),
            "cum_instrument_B": round(instrument, 1),
            "note": notes[0],
        }
    return frag


# --------------------------------------------------------------------------- validation stage
WINDFALL_SCEN = {
    "low": dict(reemployment_haircut=0.20, _adoption_end=0.20),
    "medium": dict(),
    "high": dict(reemployment_haircut=0.40, _adoption_end=0.80),
}
# Their allocation of displaced wages (firms/consumers/residual). High capture 45/45/10 == the
# preset verbatim. Low capture 15/15/70: auto_cost=0.70 shrinks net saving to 30% of the saved
# bill; the preset's 0.5/0.5 split then yields firms 15% / consumers 15% EXACTLY, and the 70%
# residual leaks offshore untaxed (their foreign/absorbed share).
WINDFALL_CAPTURE = {"high": dict(), "low": dict(auto_cost=0.70, offshore_share=0.70)}
WINDFALL_TARGETS = {("low", "high"): 0.2, ("medium", "high"): -2.8, ("high", "high"): -7.3,
                    ("low", "low"): -1.8, ("medium", "low"): -7.7, ("high", "low"): -15.3}


def build_validation(env: Env) -> dict:
    out = ART / "validation"
    out.mkdir(parents=True, exist_ok=True)
    wf_base = presets.to_params(presets.PRESETS["windfall-medium"])
    ctx = mc.ScenarioContext(env.data, env.deltas, wf_base)
    grid = []
    for scen, sd in WINDFALL_SCEN.items():
        for cap, cd in WINDFALL_CAPTURE.items():
            over = {k: v for k, v in {**sd, **cd}.items() if not k.startswith("_")}
            end = sd.get("_adoption_end")
            if end is not None:
                over["adoption_path"] = list(np.linspace(0.05, end, wf_base.n_periods))
            res = ctx.run(replace(wf_base, **over))
            grid.append({"scenario": scen, "capture": cap,
                         "model_pct": round(cum10_total_revenue_pct(res, env.ledger), 2),
                         "target_pct": WINDFALL_TARGETS[(scen, cap)]})
    pd.DataFrame(grid).to_csv(out / "windfall_grid.csv", index=False)

    # ---- RAND S3: one-shot ~10% displacement (flat path, cog-only), at-cost pricing ----------
    rand_common = dict(
        cognitive_feasibility=0.85, physical_feasibility=0.0, robotics_lag=0.0,
        reabsorption_rate=0.20, lfp_exit_rate=0.0, attrition_rate=0.0,
        retained_profit_share=0.0, price_reduction_share=1.0, survivor_gains_share=0.0,
        auto_cost=0.05, price_passthrough=1.0, productivity_passthrough=0.55,
        demand_multiplier=0.30, survivor_elasticity=0.0, baseline_growth_rate=0.04,
        automation_tax_rate=0.0, n_periods=10,
        reabsorption_rung=wf_base.reabsorption_rung,
    )

    def rand_v2p(x: float):
        return replace(DEFAULTS_SHIPPED, **rand_common, adoption_path=[float(x)] * 10)

    rand_ctx = mc.ScenarioContext(env.data, env.deltas, rand_v2p(0.3))
    # displacement is linear in the flat level (clip never binds for g,x<=1): probe + rescale
    probe = rand_ctx.run(rand_v2p(0.3))["employment_drop_pct"].iloc[0]
    x_star = 0.3 * 10.0 / float(probe)
    res = rand_ctx.run(rand_v2p(x_star))
    drop0 = float(res["employment_drop_pct"].iloc[0])
    if abs(drop0 - 10.0) > 0.05:                       # fall back to bisection if nonlinearity bit
        lo, hi = 0.5 * x_star, min(1.0, 2.0 * x_star)
        for _ in range(20):
            mid = (lo + hi) / 2
            d = float(rand_ctx.run(rand_v2p(mid))["employment_drop_pct"].iloc[0])
            lo, hi = (mid, hi) if d < 10.0 else (lo, mid)
        x_star = (lo + hi) / 2
        res = rand_ctx.run(rand_v2p(x_star))
    u = u_proxy_pct(res)
    fed_rev_pct = 100.0 * (float(res["fed_revenue_B"].iloc[-1]) - env.ledger.fed_revenue0) \
        / env.ledger.fed_revenue0
    # bridging number: RAND's loss flows through nominal-GDP deflation (FRB/US); our nominal
    # columns are price-invariant by the A2 rule — scale revenue by our modeled P (unit-elastic).
    fed_rev_pct_nominal = 100.0 * (float(res["fed_revenue_B"].iloc[-1]
                                         * res["price_level"].iloc[-1])
                                   - env.ledger.fed_revenue0) / env.ledger.fed_revenue0
    pd.DataFrame({"period": res["period"], "u_proxy_pct": u,
                  "employment_drop_pct": res["employment_drop_pct"],
                  "fed_revenue_B": res["fed_revenue_B"],
                  "price_level": res["price_level"]}).to_csv(out / "rand_s3_path.csv", index=False)

    return {
        "windfall": {"grid": grid,
                     "caveat": "their base is an average OECD country (46% labor, VAT); ours is "
                               "the labor-skewed US federal+state base — magnitudes are not "
                               "directly comparable, sign and ordering are"},
        "rand_s3": {"solved_flat_adoption": round(float(x_star), 4),
                    "u_proxy_y0_pct": round(float(u.iloc[0]), 1),
                    "u_proxy_y5_pct": round(float(u.iloc[5]), 1),
                    "fed_rev_pct_y10": round(fed_rev_pct, 1),
                    "fed_rev_pct_y10_nominal_adj": round(fed_rev_pct_nominal, 1),
                    "price_level_y10": round(float(res["price_level"].iloc[-1]), 3),
                    "target_pct": -25.0},
    }


# --------------------------------------------------------------------------- comparison stage
def build_comparison(manifest_presets: dict) -> dict:
    out = ART / "comparison"
    out.mkdir(parents=True, exist_ok=True)
    rows = pd.DataFrame([{"preset": v["name"],
                          "p10": v["mc"]["final_fed_deficit_B"]["p10"],
                          "p50": v["mc"]["final_fed_deficit_B"]["p50"],
                          "p90": v["mc"]["final_fed_deficit_B"]["p90"]}
                         for v in manifest_presets.values()])
    rows.to_csv(out / "final_outcomes.csv", index=False)
    charts.save_png(charts.final_outcome_dotplot(rows), out / "final_outcome_dotplot.png")
    return {"figures": {"final_outcome_dotplot": "comparison/final_outcome_dotplot.png"}}


def build_recovery_matrix(manifest_overlays: dict, names: dict) -> None:
    out = ART / "overlays"
    out.mkdir(parents=True, exist_ok=True)
    rows = [{"preset": names[pk], "preset_key": pk, "overlay": presets.OVERLAYS[ok].name,
             "overlay_key": ok, **{k: v for k, v in d.items() if k != "note"}}
            for pk, per in manifest_overlays.items() for ok, d in per.items()]
    pd.DataFrame(rows).to_csv(out / "recovery_matrix.csv", index=False)


# --------------------------------------------------------------------------- render-only stage
def render_from_cache() -> None:
    """Re-render every PNG from the committed CSVs — no model, ~30s."""
    for key, p in presets.PRESETS.items():
        out = ART / "presets" / key
        if not (out / "percentiles.csv").exists():
            print(f"  skip {key} (no cached CSVs)")
            continue
        pct = pd.read_csv(out / "percentiles.csv")
        base_run = pd.read_csv(out / "base_run.csv")
        for metric, fname, y_title in FAN_METRICS:
            charts.save_png(charts.fan_chart(pct, base_run, metric, y_title, title=p.name),
                            out / f"{fname}.png")
    comp = ART / "comparison" / "final_outcomes.csv"
    if comp.exists():
        charts.save_png(charts.final_outcome_dotplot(pd.read_csv(comp)),
                        ART / "comparison" / "final_outcome_dotplot.png")


# --------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=N_DRAWS)
    ap.add_argument("--spread", type=float, default=SPREAD)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--preset", choices=list(presets.PRESETS), default=None)
    ap.add_argument("--stage", choices=["all", "compute", "validation", "render"], default="all")
    args = ap.parse_args()

    charts.enable_print_theme()
    if args.stage == "render":
        render_from_cache()
        print("re-rendered from cache")
        return

    env = load_env()
    if not reabsorption.engine_artifacts_exist():
        sys.exit("reabsorption artifacts absent — the report requires rung 1 (README Setup)")

    manifest_path = ART / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest.setdefault("presets", {})
    manifest.setdefault("overlays", {})

    keys = [args.preset] if args.preset else list(presets.PRESETS)
    failures = []
    if args.stage in ("all", "compute"):
        for key in keys:
            try:
                frag, ctx = build_preset(env, key, args.n, args.spread, args.seed)
                base_run = pd.read_csv(ART / "presets" / key / "base_run.csv")
                manifest["presets"][key] = frag
                manifest["overlays"][key] = build_overlays(env, key, ctx, base_run)
            except AssertionError as e:
                failures.append((key, str(e)))
                print(f"\n  !! {key} FAILED: {e}")
        if args.preset is None and len(manifest["presets"]) == len(presets.PRESETS):
            manifest["comparison"] = build_comparison(manifest["presets"])
            build_recovery_matrix(manifest["overlays"],
                                  {k: v["name"] for k, v in manifest["presets"].items()})

    if args.stage in ("all", "validation"):
        manifest["validation"] = build_validation(env)
        manifest["validation"]["acemoglu_gdp"] = {
            "y10_gdp_gain_pct": manifest["presets"]["acemoglu-modest"]["final"]
            ["productivity_gain_pct"] if "acemoglu-modest" in manifest["presets"] else None,
            "target_upper_bound_pct": 1.1,
        }

    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                         text=True, cwd=ART.parents[2]).stdout.strip()
    manifest.update({
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "git_sha": sha,
        "config": {"n": args.n, "spread": args.spread, "seed": args.seed},
        "baselines": {"fed_revenue0_B": round(env.ledger.fed_revenue0, 1),
                      "state_revenue0_B": round(env.ledger.state_revenue0, 1),
                      "fed_deficit0_B": government.BASELINE_FED_DEFICIT_BUSD,
                      "combined_revenue0_B": round(env.ledger.fed_revenue0
                                                   + env.ledger.state_revenue0, 1)},
    })
    # Foreign fragments ("screening" belongs to scripts/global_screening.py) are re-read at write
    # time — this build loaded the manifest ~an hour ago and must not clobber a concurrent update.
    if manifest_path.exists():
        fresh = json.loads(manifest_path.read_text())
        for k in ("screening",):
            if k in fresh:
                manifest[k] = fresh[k]
    tmp = manifest_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=1))
    tmp.rename(manifest_path)
    print(f"manifest → {manifest_path}")
    if failures:
        sys.exit(f"{len(failures)} preset(s) failed: {[k for k, _ in failures]}")


if __name__ == "__main__":
    main()
