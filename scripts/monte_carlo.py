"""Headless Monte Carlo runner — the reproducible artifact behind the report's uncertainty figures.

Runs N locally-perturbed draws around a base configuration (see fiscal_model/mc.py for the sampling
rules) and writes: draws.parquet (lever values + final headlines per draw), paths.parquet (long
draw × period paths), summary.json (config + percentiles + tornados + runtime), and self-contained
HTML fan/tornado charts (altair — no extra deps needed for HTML export).

Examples:
  .venv/bin/python scripts/monte_carlo.py --n 2000 --spread 0.15 --seed 0
  .venv/bin/python scripts/monte_carlo.py --preset shipped --set ubi_annual=12000 --set demand_multiplier=0.6
  .venv/bin/python scripts/monte_carlo.py --preset ai-2027 --overlay cw-robot-tax --n 500
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # project root -> import fiscal_model

import numpy as np
from fiscal_model import loaders, mc, presets, reabsorption
from fiscal_model.dynamics import precompute_worker_deltas
from fiscal_model.kernel import KernelParams
from fiscal_model.levers_v2 import DEFAULTS_SHIPPED, DEFAULTS_V1REDUCTION
from fiscal_model.transfers import TransferLookup

SCEN = dict(cognitive_feasibility=0.85, physical_feasibility=0.25)


def parse_set(kv: str):
    k, v = kv.split("=", 1)
    return k, (v if k in ("state_response", "denominator", "exposure_mapping") else float(v))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--spread", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--periods", type=int, default=None,
                    help="horizon (default: the preset's native horizon; 10 for shipped/reduction)")
    ap.add_argument("--preset", choices=["shipped", "reduction", *presets.PRESETS], default="shipped")
    ap.add_argument("--overlay", action="append", default=[], choices=list(presets.OVERLAYS),
                    help="policy overlay applied after --set (repeatable; derives from the final "
                         "auto_cost/retained, so --set auto_cost=… affects the robot-tax rate)")
    ap.add_argument("--rung", type=int, choices=[0, 1], default=None,
                    help="reabsorption rung (default: 1 if the engine artifacts exist)")
    ap.add_argument("--set", action="append", default=[], metavar="LEVER=VALUE",
                    help="override a base lever (repeatable)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    rung = args.rung if args.rung is not None else (1 if reabsorption.engine_artifacts_exist() else 0)
    overrides = dict(parse_set(kv) for kv in getattr(args, "set"))
    if "ui_weeks" in overrides:
        overrides["ui_weeks"] = int(overrides["ui_weeks"])
    if args.preset in presets.PRESETS:
        # named preset: its own scenario + horizon — no SCEN/adoption stomp
        base = presets.to_params(presets.PRESETS[args.preset], n_periods=args.periods)
        base = replace(base, reabsorption_rung=rung, **overrides)
    else:
        periods = args.periods if args.periods is not None else 10
        base = DEFAULTS_SHIPPED if args.preset == "shipped" else DEFAULTS_V1REDUCTION
        base = replace(base, **SCEN, n_periods=periods,
                       adoption_path=list(np.linspace(0.1, 0.9, periods)),
                       reabsorption_rung=rung, **overrides)
    base, overlay_notes = presets.apply_overlays(base, args.overlay)
    for note in overlay_notes:
        print("overlay:", note)

    out = args.out or Path("data/mc_runs") / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)

    print("loading data + caches…")
    data = loaders.load_all(validate=False)
    deltas = precompute_worker_deltas(data, TransferLookup(), KernelParams())
    print(f"building context (rung {rung})…")
    ctx = mc.ScenarioContext(data, deltas, base)

    t0 = time.perf_counter()
    res = mc.run_mc(ctx, n=args.n, spread=args.spread, seed=args.seed,
                    progress=lambda i, n: print(f"\r  draw {i}/{n}", end="", flush=True))
    runtime = time.perf_counter() - t0
    print(f"\n{args.n} draws in {runtime:.0f}s ({runtime / args.n:.3f}s/draw)")

    res.draws.to_parquet(out / "draws.parquet", index=False)
    res.paths.to_parquet(out / "paths.parquet", index=False)
    (out / "summary.json").write_text(json.dumps({
        "base": {f: (v if not isinstance(v, (list, tuple)) else list(v))
                 for f, v in vars(base).items()},
        "preset": args.preset, "overlays": args.overlay, "overlay_notes": overlay_notes,
        "n": args.n, "spread": args.spread, "seed": args.seed, "runtime_s": round(runtime, 1),
        "percentiles": res.percentiles.to_dict(orient="records"),
        "tornado": res.tornado.to_dict(orient="records"),
    }, indent=1, default=str))

    from fiscal_model import charts
    charts.enable_print_theme()
    for mcol, fname in (("fed_deficit_B", "fan_deficit"), ("fed_debt_B", "fan_debt"),
                        ("employment_drop_pct", "fan_employment")):
        charts.fan_chart(res.percentiles, res.base_run, mcol, title=mcol,
                         width=640, height=360).save(str(out / f"{fname}.html"))
    for target, fname in (("final_fed_deficit_B", "tornado_deficit"),
                          ("final_employment_drop_pct", "tornado_employment")):
        charts.tornado_chart(res.tornado, target).save(str(out / f"{fname}.html"))

    top = res.tornado.query("target == 'final_fed_deficit_B'").head(5)
    print(f"artifacts → {out}")
    print("top deficit drivers:", ", ".join(f"{r.lever} (ρ={r.spearman:+.2f})" for r in top.itertuples()))


if __name__ == "__main__":
    main()
