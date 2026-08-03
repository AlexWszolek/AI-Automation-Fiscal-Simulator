"""Paired policy screening — instrument potency and the value of information.

The committed §7.14 global sweep (scripts/global_screening.py) samples policy dims uniformly
alongside uncertainty dims. That is the right design for "what matters ANYWHERE", but it makes
three questions unanswerable, because policy variance swamps the picture (in that sweep the policy
dims carry 79% of total outcome variance, `ubi_annual` alone 63%):

  1. How robust is the fiscal hole ITSELF, with no automation-side instrument and no UBI?
  2. At what RATE does an instrument close it — the ladder, not a binary?
  3. Which empirical uncertainty actually drives the outcome once policy is held still?

This script answers them by sampling the 19 uncertainty dims exactly as §7.14 does and PINNING the
7 policy dims to a named regime. Same seed + same dims dict => identical LHS permutations across
regimes, so draws are PAIRED: arm-to-arm differences are per-world treatment effects rather than
distribution shifts, and "how much of the hole does this instrument close" is a per-world ratio
instead of a comparison of two marginal medians.

A caution the results make concrete: `automation_tax_frac` is a fraction of the capacity bound
retained·(1−auto_cost), so `retained_profit_share` IS the automation tax base. In any sweep where
the automation tax is live, retained_profit_share scores as a top "uncertainty" driver purely
through that coupling — it is exactly 0.000 in every arm here that has no automation tax, and
climbs to 0.222 at frac=1.0. Rank uncertainty drivers on a policy-pinned arm, never on a sweep
with policy live.

Usage:
  .venv/bin/python scripts/policy_sweep.py                    # n=5,000 × 7 arms (~70 min)
  .venv/bin/python scripts/policy_sweep.py --n 150 --smoke    # ~1 min
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from fiscal_model import loaders, mc
from fiscal_model.dynamics import precompute_worker_deltas
from fiscal_model.invariants import assert_all_invariants
from fiscal_model.kernel import KernelParams
from fiscal_model.levers_v2 import DEFAULTS_SHIPPED
from fiscal_model.transfers import TransferLookup

OUT = Path(__file__).resolve().parent.parent / "docs" / "research" / "policy-sweep"
N_MAIN, SEED = 5_000, 0

# Same template as scripts/global_screening.py, so the two sweeps are directly comparable.
TEMPLATE = replace(DEFAULTS_SHIPPED, n_periods=10, adoption_path=list(np.linspace(0.05, 0.5, 10)))
D = DEFAULTS_SHIPPED


def _regime(compute: float, auto_frac: float) -> dict:
    """Everything except the two automation-side instruments held at the shipped baseline.

    ubi_annual is pinned at 0 in every arm on purpose: a UBI is an OUTLAY whose size is a political
    choice spanning $0-7.8T gross, and letting it vary would once again drown the instrument
    question it has nothing to do with."""
    return {"compute_effective_rate": compute, "automation_tax_frac": auto_frac,
            "ubi_annual": 0.0, "ubi_recapture_rate": D.ubi_recapture_rate,
            "interest_rate": D.interest_rate, "state_cut_share": D.state_cut_share,
            "state_rate_hike_cap": D.state_rate_hike_cap}


REGIMES = {
    "no-instruments": _regime(0.00, 0.00),   # the counterfactual hole
    "status-quo":     _regime(0.10, 0.00),   # DEFAULTS_SHIPPED: the 10% compute tax already booked
    "compute-20":     _regime(0.20, 0.00),
    "compute-40":     _regime(0.40, 0.00),   # top of the §7.14 sampled range
    "auto-25":        _regime(0.10, 0.25),
    "auto-50":        _regime(0.10, 0.50),
    "max-revenue":    _regime(0.40, 1.00),   # UPPER BOUND, not a proposal: frac=1.0 taxes away all
}                                            # retained automation profit net of cost

FINAL_COLS = ["fed_deficit_B", "fed_debt_B", "fed_deficit_abs_pct_gdp", "employment_drop_pct",
              "state_gap_B", "induced_M", "fed_revenue_B", "productivity_index", "price_level",
              "reabsorbed_M", "exited_M"]
UNCERTAINTY = [d for d, (_lo, _hi, tag) in mc.GLOBAL_RANGES.items() if tag == "uncertainty"]


def run_regime(ctx, name: str, pins: dict, n: int, seed: int, check: bool) -> pd.DataFrame:
    draws, samples = mc.lhs_draws(TEMPLATE, n, seed=seed,
                                  range_overrides={d: (v, v) for d, v in pins.items()})
    out, t0, baseline_M = [], time.perf_counter(), None
    for i, v2p in enumerate(draws):
        res = ctx.run(v2p)
        if baseline_M is None:
            baseline_M = float(res["population_M"].iloc[0])
        if check:
            assert_all_invariants(res, v2p, baseline_M)
        fin = res.iloc[-1]
        row = {c: float(fin[c]) for c in FINAL_COLS if c in res.columns}
        row["cum_net_fiscal_B"] = float(-res["fed_deficit_B"].sum())
        out.append(row)
        if (i + 1) % 500 == 0:
            rate = (i + 1) / (time.perf_counter() - t0)
            print(f"  {name}: {i+1}/{n}  ({rate:.1f}/s, eta {(n-i-1)/rate/60:.1f} min)", flush=True)
    df = pd.concat([samples[UNCERTAINTY].reset_index(drop=True), pd.DataFrame(out)], axis=1)
    df["regime"], df["draw"] = name, np.arange(n)
    print(f"  {name}: done in {(time.perf_counter()-t0)/60:.1f} min", flush=True)
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=N_MAIN)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--smoke", action="store_true", help="skip the C1-C8 battery for a quick pass")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    print("loading model data …", flush=True)
    data = loaders.load_all(validate=False)
    deltas = precompute_worker_deltas(data, TransferLookup(), KernelParams())
    ctx = mc.ScenarioContext(data, deltas, TEMPLATE)

    frames = [run_regime(ctx, name, pins, args.n, args.seed, not args.smoke)
              for name, pins in REGIMES.items()]
    all_df = pd.concat(frames, ignore_index=True)
    all_df.to_parquet(args.out / "policy_sweep.parquet", index=False)
    (args.out / "meta.json").write_text(json.dumps(
        {"n": args.n, "seed": args.seed, "invariants_checked": not args.smoke,
         "regimes": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in REGIMES.items()}},
        indent=1))
    print(f"\nwrote {args.out/'policy_sweep.parquet'}  ({len(all_df):,} rows)")
    print("analyse with: .venv/bin/python scripts/policy_sweep_report.py")


if __name__ == "__main__":
    main()
