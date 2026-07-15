"""Precompute the app's always-on sensitivity tornado for every preset (+ the Custom defaults).

Writes data/app_precomputed/mc_tornado.json — one entry per config, keyed by the canonical config
repr (fiscal_model.app_params.cfg_key), so the live app can serve a preset's tornado instantly and
only ever computes for modified settings. Deterministic bytes: fixed seed, insertion-ordered keys,
no timestamps — running twice must produce identical files (tests/test_app_precomputed.py pins the
key-matching; re-run this script whenever a preset or CUSTOM_DEFAULTS changes).

  .venv/bin/python scripts/precompute_app_mc.py          # ~10 min (10 configs x N=200)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_model import app_params as ap
from fiscal_model import loaders, mc, presets, reabsorption
from fiscal_model.dynamics import precompute_worker_deltas
from fiscal_model.kernel import KernelParams
from fiscal_model.transfers import TransferLookup

OUT = Path(__file__).resolve().parent.parent / "data" / "app_precomputed"
N, SPREAD, SEED = 200, 0.15, 0


def app_configs() -> dict:
    """key -> canonical V2Params for every selectbox choice (Custom = the app's first-load state)."""
    cfgs = {"custom": ap.canon(ap.build_v2_params(
        ap.ui_from_defaults(dict(ap.CUSTOM_DEFAULTS), rung=1)))}
    for key, p in presets.PRESETS.items():
        ui = ap.ui_from_defaults(ap.preset_widget_defaults(p), rung=1, preset=p)
        cfgs[key] = ap.canon(ap.build_v2_params(ui))
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
    assert reabsorption.engine_artifacts_exist(), "precompute needs the rung-1 artifacts"
    data = loaders.load_all(validate=False)
    deltas = precompute_worker_deltas(data, TransferLookup(), KernelParams())
    entries = []
    for key, base in app_configs().items():
        print(f"{key}…", flush=True)
        ctx = mc.ScenarioContext(data, deltas, base)
        r = mc.run_mc(ctx, n=N, spread=SPREAD, seed=SEED)
        entries.append({"key": key, "cfg_repr": ap.cfg_key(base), **pack(r)})
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
