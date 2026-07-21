"""Precompute the app's always-on sensitivity tornado for every preset × policy-response cart.

Writes data/app_precomputed/mc_tornado.json — one entry per pristine config (10 presets/custom
× 12 valid overlay subsets = 120), keyed by the canonical config repr (fiscal_model.app_params
.cfg_key), so the live app serves any preset+overlay tornado instantly and only ever computes
for slider-modified settings. Every base derives via webpayload.resolve_config — the exact
function the API worker uses (api/jobs.py) — so the cfg_repr keys match by construction.
Deterministic bytes: fixed seed, insertion-ordered keys, no timestamps — running twice must
produce identical files (tests/test_app_precomputed.py pins the key set and key-matching;
re-run this script whenever a preset, overlay, or CUSTOM_DEFAULTS changes).

  .venv/bin/python scripts/precompute_app_mc.py --workers 8    # ~20 min (120 configs × N=200)
  .venv/bin/python scripts/precompute_app_mc.py                # serial, ~2h
"""
from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_model import app_params as ap
from fiscal_model import loaders, mc, mc_pool, presets, reabsorption, webpayload
from fiscal_model.dynamics import precompute_worker_deltas
from fiscal_model.kernel import KernelParams
from fiscal_model.transfers import TransferLookup

OUT = Path(__file__).resolve().parent.parent / "data" / "app_precomputed"
N, SPREAD, SEED = 200, 0.15, 0


def app_configs() -> dict:
    """slug -> canonical V2Params for every pristine preset × valid overlay subset (the same
    enumeration scripts/gen_web_bundle.py uses; both robot taxes together is invalid)."""
    ov_keys = list(presets.OVERLAYS)
    subsets = [list(c) for r in range(len(ov_keys) + 1) for c in combinations(ov_keys, r)
               if not {"cw-robot-tax", "grt-robot-tax"} <= set(c)]
    cfgs = {}
    for preset in [None] + list(presets.PRESETS):
        for ovs in subsets:
            cfg = {"preset": preset, "overlays": ovs, "levers": {}}
            cfgs[webpayload.slug(cfg)] = ap.canon(webpayload.resolve_config(cfg)["v2p"])
    return cfgs


def pack(r: mc.MCResult) -> dict:
    finals = r.paths[r.paths["period"] == r.paths["period"].max()]["fed_deficit_B"]
    tor = r.tornado.query("target == 'final_fed_deficit_B'")
    return {
        "tornado": [{"lever": t.lever, "spearman": round(float(t.spearman), 4)}
                    for t in tor.itertuples()],
        "p10": round(float(finals.quantile(0.10)), 1),
        "p50": round(float(finals.quantile(0.50)), 1),
        "p90": round(float(finals.quantile(0.90)), 1),
        "base_final": round(float(r.base_run["fed_deficit_B"].iloc[-1]), 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=1,
                        help="draw-level process parallelism (mc_pool; 1 = serial)")
    args = parser.parse_args()
    assert reabsorption.engine_artifacts_exist(), "precompute needs the rung-1 artifacts"
    data = loaders.load_all(validate=False)
    deltas = precompute_worker_deltas(data, TransferLookup(), KernelParams())
    configs = app_configs()
    executor = mc_pool.make_executor(args.workers) if args.workers > 1 else None
    entries = []
    try:
        for i, (key, base) in enumerate(configs.items()):
            print(f"[{i + 1}/{len(configs)}] {key}…", flush=True)
            ctx = mc.ScenarioContext(data, deltas, base)
            r = mc_pool.run_mc_pooled(ctx, n=N, spread=SPREAD, seed=SEED,
                                      workers=args.workers, executor=executor)
            entries.append({"key": key, "cfg_repr": ap.cfg_key(base), **pack(r)})
    finally:
        if executor is not None:
            executor.shutdown()
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {"n": N, "spread": SPREAD, "seed": SEED, "entries": entries}
    (OUT / "mc_tornado.json").write_text(json.dumps(payload, indent=1))
    # human-diffable mirror (the JSON's cfg_repr strings are unwieldy in review)
    with open(OUT / "mc_tornado.csv", "w") as f:
        f.write("key,p10,p50,p90,base_final,top_lever,top_rho\n")
        for e in entries:
            top = e["tornado"][0]
            f.write(f"{e['key']},{e['p10']},{e['p50']},{e['p90']},{e['base_final']},"
                    f"{top['lever']},{top['spearman']}\n")
    print(f"wrote {OUT / 'mc_tornado.json'} ({len(entries)} entries)")


if __name__ == "__main__":
    main()
