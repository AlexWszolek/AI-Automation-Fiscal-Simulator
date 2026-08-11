"""Generate the static Korea scenario bundles — one ScenarioPayload per Korea preset at
default levers, plus the precomputed tornado (n=400, seed 0), from the SAME functions the
API serves, so static ≡ live by construction (parity-tested). Regenerate after any Korea
model change:

    .venv/bin/python scripts/gen_korea_scenarios.py

Writes web/public/data/korea/scenarios/<preset>.json and korea/tornado/<preset>.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_model.korea_assembly import build_korea_deltas
from fiscal_model.korea_scenarios import KOREA_PRESETS
from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                           korea_mc_tornado, sanitize_korea_config)

KOREA_DATA = Path(__file__).resolve().parent.parent / "web" / "public" / "data" / "korea"
OUT = KOREA_DATA / "scenarios"
TORNADO_OUT = KOREA_DATA / "tornado"
TORNADO_N = 400          # the precomputed fidelity; live custom requests default to 150


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    TORNADO_OUT.mkdir(parents=True, exist_ok=True)
    pools = {"data_pool": {}, "deltas": build_korea_deltas(), "ctx_pool": {}}
    for key in KOREA_PRESETS:
        payload = build_korea_scenario_payload(sanitize_korea_config({"preset": key}),
                                               **pools)
        path = OUT / f"{key}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=None,
                                   separators=(",", ":")), encoding="utf-8")
        tor = korea_mc_tornado(sanitize_korea_config({"preset": key}), n=TORNADO_N, **pools)
        tpath = TORNADO_OUT / f"{key}.json"
        tpath.write_text(json.dumps(tor, ensure_ascii=False, indent=None,
                                    separators=(",", ":")), encoding="utf-8")
        print(f"wrote {path} ({path.stat().st_size // 1024} KB) "
              f"+ tornado ({tpath.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
