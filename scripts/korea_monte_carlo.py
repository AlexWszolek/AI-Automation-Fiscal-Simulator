"""Headless Korea Monte Carlo — the reproducible artifact behind the Korea uncertainty
numbers. Joint draws over model levers × wage-linked shares × the exposure read, demography
frozen (rationale in fiscal_model/korea_mc.py).

Writes docs/research/korea-slides-pack/mc-summary.json (committed: config, percentiles,
tornado, base row) and, with --out, draws.parquet for deeper analysis.

    .venv/bin/python scripts/korea_monte_carlo.py --n 400 --spread 0.15 --seed 0
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_model.korea_mc import run_korea_mc

OUT = (Path(__file__).resolve().parent.parent
       / "docs" / "research" / "korea-slides-pack" / "mc-summary.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--spread", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--preset", default="korea-central")
    ap.add_argument("--out", type=Path, default=None,
                    help="optional directory for draws.parquet")
    a = ap.parse_args()

    t0 = time.time()
    r = run_korea_mc(n=a.n, spread=a.spread, seed=a.seed, preset=a.preset,
                     progress=lambda i, n: print(f"\r{i}/{n}", end="", flush=True))
    dt = time.time() - t0
    print(f"\n{a.n} draws in {dt:.1f}s")

    summary = {
        "config": {"n": a.n, "spread": a.spread, "seed": a.seed, "preset": a.preset,
                   "demography": "FROZEN (published medium variant)",
                   "runtime_s": round(dt, 1)},
        "base": {k: round(v, 4) for k, v in r.base.items()},
        "percentiles": {
            h: {f"p{int(row.pct)}": round(float(row.value), 4)
                for row in r.percentiles[r.percentiles.headline == h].itertuples()}
            for h in r.percentiles["headline"].unique()},
        "tornado": {
            h: [{"input": row.input, "spearman": round(float(row.spearman), 4)}
                for row in r.tornado[r.tornado.headline == h].head(10).itertuples()]
            for h in r.tornado["headline"].unique()},
    }
    OUT.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        r.draws.to_parquet(a.out / "draws.parquet")
        print(f"wrote {a.out / 'draws.parquet'}")


if __name__ == "__main__":
    main()
