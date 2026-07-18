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
    for preset in configs:
        for ovs in subsets:
            cfg = {"preset": preset, "overlays": ovs, "levers": {}}
            payload = webpayload.build_scenario_payload(data, deltas, cfg, ctx_cache=ctx_cache)
            _dump(payload, WEB_DATA / "scenarios" / f"{webpayload.slug(cfg)}.json")
            n += 1
    print(f"{n} scenario bundles")

    # tornado: re-key the committed precompute by slug (pristine configs only)
    src = json.loads((ROOT / "data" / "app_precomputed" / "mc_tornado.json").read_text())
    by_repr = {e["cfg_repr"]: e for e in src["entries"]}
    out = {}
    for preset in configs:
        cfg = {"preset": preset, "overlays": [], "levers": {}}
        rep = webpayload.cfg_repr_for(cfg)
        e = by_repr.get(rep)
        assert e is not None, f"precomputed tornado missing for {preset or 'custom'} — " \
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
    if not args.grid_only:
        emit_scenarios()


if __name__ == "__main__":
    main()
