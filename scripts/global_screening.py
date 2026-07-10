"""Global LHS screening sweep — what matters ANYWHERE in the lever space, not just near a preset.

Three deliverables (report §7.9 + the app's uncertainty framing):
  1. a GLOBAL tornado — Spearman ρ + binned η² of every sampled lever vs the final-year federal
     deficit, on two panels (uncertainty vs policy dims, per mc.GLOBAL_RANGES tags);
  2. a REGIME map — where the federal balance flips sign / worsens by 0–1 / 1–3 / >3% of GDP,
     with states-capped as a separate boolean axis;
  3. a systematic CORNER SWEEP — every point passes the full C1–C8 invariant battery plus an
     oscillation screen, and a dedicated n_periods=20 batch concentrated in the limit-cycle
     corner regression-guards the demand-controller allocation fix (the 10-year main sweep has
     no power there: the cycle needed t≈17).

Artifacts → docs/report/artifacts/screening/ (results parquet gitignored; tornado/regime CSVs +
PNGs committed); a "screening" fragment is merged into manifest.json (atomically, touching only
that key) so report prose resolves {{n:screening.*}} / {{fig:screening.figures.*}}.

Usage:
  .venv/bin/python scripts/global_screening.py                # full: n=10,000 (~45 min)
  .venv/bin/python scripts/global_screening.py --smoke        # n=200 + cycle batch 50 (~2 min)
  .venv/bin/python scripts/global_screening.py --n 2000 --seed 1
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from fiscal_model import charts, loaders, mc, reabsorption
from fiscal_model.dynamics import precompute_worker_deltas
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.invariants import assert_all_invariants
from fiscal_model.kernel import KernelParams
from fiscal_model.levers_v2 import DEFAULTS_SHIPPED
from fiscal_model.transfers import TransferLookup

ART = Path(__file__).resolve().parent.parent / "docs" / "report" / "artifacts"
SCR = ART / "screening"
N_MAIN, N_CYCLE, SEED = 10_000, 400, 0

# The template: shipped structure (rung 1), 10y horizon, a placeholder path (every draw replaces
# it). FIXED — not the first draw — so ctx.base is stable across seeds and recorded once.
TEMPLATE = replace(DEFAULTS_SHIPPED, n_periods=10, adoption_path=list(np.linspace(0.05, 0.5, 10)))

# The limit-cycle corner (the artifact the 2026-07-08 audit fixed): near-total automation, hot
# demand feedback, cold re-employment — at a 20-year horizon so the endgame is actually reached.
CYCLE_OVERRIDES = {"adoption_end": (0.7, 1.0), "demand_multiplier": (1.0, 2.0),
                   "reabsorption_rate": (0.0, 0.2)}

FINAL_COLS = ["fed_deficit_B", "fed_debt_B", "fed_deficit_pct_gdp", "fed_deficit_abs_pct_gdp",
              "employment_drop_pct", "state_gap_B", "W_survivor", "induced_M", "fed_revenue_B",
              "productivity_index", "price_level", "reabsorbed_M", "exited_M"]
REGIME_ORDER = ["improves", "worsens 0–1% GDP", "worsens 1–3% GDP", "worsens >3% GDP"]
REGIME_COLORS = ["#4e937a", "#d9a441", "#b3554d", "#7d2e28"]   # app palette teal/amber/red/dark-red


def alternation_count(signed: np.ndarray, threshold_M: float) -> int:
    """Sign alternations of a signed series where BOTH legs exceed the mass threshold.

    The FLAG metric is employment period-diffs (the visible pathology: the audit's limit cycle
    swung employment ±12M per period → ~T−2 alternations; a genuine one-way trough-and-recovery
    scores exactly 1; flag ≥ 2). `induced_pending_M` is recorded too but NOT flagged on: the
    controller legitimately rings once when its target peaks (a small over-release then a
    correction, decaying amplitude) while employment never reverses."""
    big = signed[np.abs(signed) > threshold_M]
    if len(big) < 2:
        return 0
    s = np.sign(big)
    return int(np.sum(s[1:] != s[:-1]))


def eta_squared(x: pd.Series, y: pd.Series, bins: int = 20) -> tuple[float, float]:
    """Binned correlation ratio (first-order Sobol proxy): Var(bin means)/Var(y) over ~equal-count
    bins of x. Catches any-shape main effects; high η² with low |ρ| flags non-monotonicity (the
    conditionally-activated levers — robotics_lag, spillover, recapture — show attenuated ρ).

    Returns (raw, debiased): raw η² has an upward null bias of (k−1)/(n−1) — 0.10 at n=200, 0.002
    at n=10,000 — so flags/comparisons use the debiased value max(0, (η²−null)/(1−null))."""
    b = pd.qcut(x, bins, duplicates="drop")
    k = b.nunique()
    if k < 2 or y.var(ddof=0) == 0:
        return 0.0, 0.0
    g = y.groupby(b, observed=True)
    ss_between = float((g.size() * (g.mean() - y.mean()) ** 2).sum())
    e2 = ss_between / (y.var(ddof=0) * len(y))
    null = (k - 1) / (len(y) - 1)
    return e2, max(0.0, (e2 - null) / (1.0 - null))


def run_sweep(data, deltas, base, n: int, seed: int, label: str,
              range_overrides: dict | None = None) -> pd.DataFrame:
    """One LHS batch through ONE ScenarioContext: invariants on EVERY point (1.6ms — 0.6% of the
    259ms run), a 3-draw fresh-vs-context bit-equality spot check, oscillation count recorded."""
    ctx = mc.ScenarioContext(data, deltas, base)
    draws, samples = mc.lhs_draws(base, n, seed, range_overrides)
    baseline_M, thresh = None, None
    rows = []
    t0 = time.time()
    for i, v2p in enumerate(draws):
        try:
            res = ctx.run(v2p)
            if baseline_M is None:
                baseline_M = float(res["population_M"].iloc[0])
                thresh = 5e-4 * baseline_M          # ~0.05% of the baseline workforce (~80k)
            assert_all_invariants(res, v2p, baseline_M)
            if i < 3:                               # standing guard: the template must not leak
                fresh = DynamicModelV2(data, deltas, v2p).run()
                for c in res.columns:
                    if res[c].dtype.kind == "f":
                        assert np.array_equal(fresh[c].to_numpy(), res[c].to_numpy()), \
                            f"context deviates from fresh construction on {c!r}"
        except (AssertionError, ValueError) as e:   # fail loud, pinned for reproduction
            raise AssertionError(
                f"{label} draw {i} (seed {seed}) failed: {e}\nlevers: {samples.iloc[i].to_dict()}"
            ) from e
        rec = {c: float(res[c].iloc[-1]) for c in FINAL_COLS}
        rec.update({
            "cum_net_fiscal_B": -float(res["fed_deficit_B"].sum()),
            "cum_rate_hike_B": float(res["state_rate_hike_B"].sum()),
            "cum_spending_cut_B": float(res["state_spending_cut_B"].sum()),
            "max_states_capped": int(res["n_states_capped"].max()),
            "alternations": alternation_count(np.diff(res["employed_M"].to_numpy()), thresh),
            "pending_alternations": alternation_count(res["induced_pending_M"].to_numpy(), thresh),
        })
        rows.append(rec)
        if (i + 1) % 250 == 0 or i + 1 == n:
            rate = (time.time() - t0) / (i + 1)
            print(f"  [{label}] {i + 1}/{n}  ({rate:.2f}s/run, ~{rate * (n - i - 1) / 60:.0f} min left)")
    return pd.concat([samples.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def classify(results: pd.DataFrame) -> pd.Series:
    """Fiscal regime from the final-year deficit DELTA as % of GDP (growth-robust — a $B band
    puts ~86% of the global space in one class)."""
    d = results["fed_deficit_pct_gdp"]
    return pd.Series(np.select([d <= 0, d <= 1.0, d <= 3.0],
                               REGIME_ORDER[:3], REGIME_ORDER[3]), index=results.index)


def build_tornado(results: pd.DataFrame) -> pd.DataFrame:
    """Spearman + η² per sampled dim vs the final deficit; the descriptive columns (realized tax
    rate, simplex remainder) are excluded — they inherit other dims' ranks by construction."""
    y = results["fed_deficit_B"]
    rows = []
    for dim, (_lo, _hi, tag) in mc.GLOBAL_RANGES.items():
        x = results[dim]
        # Pearson-on-ranks == Spearman, without the scipy dependency Series.corr would pull in
        rho = float(x.rank().corr(y.rank())) if x.nunique() > 1 else 0.0
        e2, e2_adj = eta_squared(x, y)
        rows.append({"lever": dim, "tag": tag, "spearman": rho, "eta2": round(e2, 4),
                     "eta2_debiased": round(e2_adj, 4),
                     "nonmonotone_flag": bool(e2_adj > 0.05 and abs(rho) < 0.10),
                     "target": "final_fed_deficit_B"})
    return (pd.DataFrame(rows).assign(abs_rho=lambda t: t.spearman.abs())
            .sort_values("abs_rho", ascending=False).drop(columns="abs_rho")
            .reset_index(drop=True))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=N_MAIN)
    ap.add_argument("--n-cycle", type=int, default=N_CYCLE)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--smoke", action="store_true", help="n=200 main + 50 cycle quick pass")
    args = ap.parse_args()
    if args.smoke:
        args.n, args.n_cycle = 200, 50

    if not reabsorption.engine_artifacts_exist():
        sys.exit("reabsorption artifacts absent — the screening requires rung 1 (README Setup)")
    print("loading data + caches…")
    data = loaders.load_all(validate=False)
    deltas = precompute_worker_deltas(data, TransferLookup(), KernelParams())
    SCR.mkdir(parents=True, exist_ok=True)
    charts.enable_print_theme()

    # ---- main sweep (10y horizon, full global space) ----
    print(f"main sweep: n={args.n}, seed={args.seed}")
    results = run_sweep(data, deltas, TEMPLATE, args.n, args.seed, "main")
    results["regime"] = classify(results)
    results["capped_anywhere"] = results["max_states_capped"] > 0
    osc_flagged = int((results["alternations"] >= 2).sum())

    # ---- dedicated limit-cycle regression batch (20y horizon, cycle corner) ----
    print(f"cycle-corner batch: n={args.n_cycle} at n_periods=20")
    base20 = replace(TEMPLATE, n_periods=20, adoption_path=list(np.linspace(0.05, 0.5, 20)))
    cycle = run_sweep(data, deltas, base20, args.n_cycle, args.seed + 1, "cycle",
                      range_overrides=CYCLE_OVERRIDES)
    cycle_max_alt = int(cycle["alternations"].max())
    assert cycle_max_alt < 2, \
        f"limit-cycle regression: {int((cycle['alternations'] >= 2).sum())} draws oscillate " \
        f"(max alternations {cycle_max_alt}) — the allocation-key fix regressed"

    # ---- analysis ----
    tornado = build_tornado(results)
    regime_tbl = (results.groupby("regime", observed=True).size()
                  .reindex(REGIME_ORDER, fill_value=0).rename("count").to_frame())
    regime_tbl["pct"] = 100 * regime_tbl["count"] / len(results)
    print(regime_tbl)

    # ---- artifacts ----
    results.to_parquet(SCR / "results.parquet")                       # gitignored (full re-map source)
    cycle.to_parquet(SCR / "cycle_batch.parquet")
    tornado.to_csv(SCR / "tornado.csv", index=False, float_format="%.5g")
    regime_tbl.reset_index().to_csv(SCR / "regimes.csv", index=False, float_format="%.5g")

    for tag in ("uncertainty", "policy"):
        panel = tornado[tornado.tag == tag]
        charts.save_png(
            charts.tornado_chart(panel, "final_fed_deficit_B",
                                 title=f"Global drivers of the final-year federal deficit — {tag}",
                                 top=len(panel), pos_color="#b3554d", neg_color="#4e937a"),
            SCR / f"global_tornado_{tag}.png")
    top2 = tornado[tornado.tag == "uncertainty"]["lever"].head(2).tolist()
    charts.save_png(
        charts.regime_scatter(results, top2[0], top2[1], top2[0], top2[1],
                              order=REGIME_ORDER, colors=REGIME_COLORS),
        SCR / "regime_scatter.png")

    # ---- manifest fragment (atomic; touch ONLY the "screening" key — the top-level "config"
    #      belongs to report_artifacts.py) ----
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                         text=True, cwd=ART.parents[2]).stdout.strip()
    pcts = results["fed_deficit_B"].quantile([.05, .25, .50, .75, .95])
    top = lambda tag: [{"lever": r.lever, "spearman": round(r.spearman, 3), "eta2": r.eta2}
                       for r in tornado[tornado.tag == tag].head(5).itertuples()]
    frag = {
        "config": {"n": args.n, "n_cycle": args.n_cycle, "seed": args.seed, "sampler": "lhs",
                   "n_dims": len(mc.GLOBAL_RANGES), "n_periods": 10,
                   "generated": time.strftime("%Y-%m-%d %H:%M"), "git_sha": sha},
        "regimes": {
            "improves_pct": round(float(regime_tbl.loc[REGIME_ORDER[0], "pct"]), 1),
            "band_0_1_pct": round(float(regime_tbl.loc[REGIME_ORDER[1], "pct"]), 1),
            "band_1_3_pct": round(float(regime_tbl.loc[REGIME_ORDER[2], "pct"]), 1),
            "band_gt3_pct": round(float(regime_tbl.loc[REGIME_ORDER[3], "pct"]), 1),
            "capped_anywhere_pct": round(100 * float(results["capped_anywhere"].mean()), 1),
        },
        "checks": {"invariant_failures": 0,                # the sweep raises on the first failure
                   "oscillation_flagged": osc_flagged,
                   "cycle_batch_max_alternations": cycle_max_alt},
        "deficit_delta_final_B": {f"p{int(q * 100)}": round(float(v), 0)
                                  for q, v in pcts.items()},
        "top_drivers": {"uncertainty": top("uncertainty"), "policy": top("policy")},
        "figures": {"global_tornado_uncertainty": "screening/global_tornado_uncertainty.png",
                    "global_tornado_policy": "screening/global_tornado_policy.png",
                    "regime_scatter": "screening/regime_scatter.png"},
    }
    (SCR / "fragment.json").write_text(json.dumps(frag, indent=1))   # standalone copy (re-mergeable)
    manifest_path = ART / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest["screening"] = frag
    tmp = manifest_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=1))
    tmp.rename(manifest_path)
    print(f"screening fragment → {manifest_path}")
    if osc_flagged:
        print(f"WARNING: {osc_flagged} main-sweep draws flagged for oscillation — inspect "
              f"results.parquet (alternations ≥ 2)")


if __name__ == "__main__":
    main()
