"""Process-parallel run_mc — the same numbers, more cores.

Determinism by construction: `mc.sample_draws(base, n, spread, seed)` generates the FULL draw
list from one RNG stream, so every worker regenerates the identical list and runs only its
assigned row range through `mc._run_rows` (global indices — same invariant-check cadence as the
serial run); the parent reassembles the rows in global order and finalizes with `mc._finalize`,
the very code the serial path uses. Pooled ≡ serial bit-for-bit is pinned in tests/test_mc.py.

Two bootstrap modes, one worker function:
- fork (Linux server): `make_executor(workers, data, deltas)` must be called EAGERLY from the
  main thread right after the data load — never lazily from a job thread (forking a threaded
  process can inherit foreign locks mid-acquire). Workers inherit data/deltas copy-on-write.
- spawn (macOS / the precompute script): each worker loads the data itself once (~5s),
  amortized over the worker's lifetime; nothing heavy is pickled.

The draws are coarse-grained and independent — this is the whole parallelism story for the
tornado (no GPU: each draw is a sequential 10-21 period simulation of small numpy ops).
"""
from __future__ import annotations

import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

from . import mc
from .levers_v2 import V2Params

# ---- worker-process state (module globals, populated by an initializer) -----------------------
_DATA = None
_DELTAS = None
_CTX = None            # (context_key, ScenarioContext) — jobs arrive one config at a time


def _init_inherit(data, deltas) -> None:
    """fork initializer: adopt the parent's already-loaded objects (COW pages, no pickling)."""
    global _DATA, _DELTAS
    _DATA, _DELTAS = data, deltas


def _init_load() -> None:
    """spawn initializer: load once per worker (~5s), then serve chunks for its lifetime."""
    global _DATA, _DELTAS
    import pandas as pd

    from . import loaders
    from .dynamics import DELTA_CACHE
    _DATA = loaders.load_all(validate=False)
    _DELTAS = pd.read_parquet(DELTA_CACHE)


def _context_for(base: V2Params) -> mc.ScenarioContext:
    global _CTX
    key = mc.context_key(base)
    if _CTX is None or _CTX[0] != key:
        _CTX = (key, mc.ScenarioContext(_DATA, _DELTAS, base))
    return _CTX[1]


def _run_chunk(base: V2Params, n: int, spread: float, seed: int, start: int, stop: int,
               baseline_M: float, invariant_every: int):
    """Worker task: regenerate the full deterministic draw list, run rows [start, stop)."""
    ctx = _context_for(base)
    draws = mc.sample_draws(base, n, spread, seed)
    rows, path_frames = mc._run_rows(ctx, draws, range(start, stop), n, baseline_M,
                                     invariant_every, progress=None)
    return start, rows, path_frames


# ---- parent side ------------------------------------------------------------------------------
def make_executor(workers: int, data=None, deltas=None) -> ProcessPoolExecutor:
    """fork-inherit when on Linux with the data in hand; spawn-load everywhere else."""
    if data is not None and sys.platform == "linux":
        return ProcessPoolExecutor(workers, mp_context=mp.get_context("fork"),
                                   initializer=_init_inherit, initargs=(data, deltas))
    return ProcessPoolExecutor(workers, mp_context=mp.get_context("spawn"),
                               initializer=_init_load)


def run_mc_pooled(context: mc.ScenarioContext, n: int = 300, spread: float = 0.15, seed: int = 0,
                  *, workers: int = 1, executor: ProcessPoolExecutor | None = None,
                  progress=None, chunk: int = 5, invariant_every: int = 20,
                  on_partial=None, partial_every: int = 40) -> mc.MCResult:
    """run_mc across processes. workers<=1 with no executor → the serial reference path.
    Pass a long-lived `executor` (the API's) or let this create/tear down a spawn pool.
    `on_partial(partial_result, n_done)` fires as done crosses partial_every multiples — the
    partial covers whichever chunks completed (iid draws: any subset is a valid sample); the
    FINAL result is unaffected (same rows reassembled in global order)."""
    if executor is None and workers <= 1:
        return mc.run_mc(context, n=n, spread=spread, seed=seed, progress=progress,
                         invariant_every=invariant_every,
                         on_partial=on_partial, partial_every=partial_every)
    base = context.base
    base_run = context.run(base)                       # the parent's context serves the base run
    baseline_M = float(base_run["population_M"].iloc[0])

    own = executor is None
    ex = executor if executor is not None else make_executor(workers)
    try:
        bounds = [(s, min(s + chunk, n)) for s in range(0, n, chunk)]
        futures = [ex.submit(_run_chunk, base, n, spread, seed, s, e, baseline_M, invariant_every)
                   for s, e in bounds]
        done, parts = 0, []
        next_partial = partial_every
        for f in as_completed(futures):
            start, rows, path_frames = f.result()      # worker failures re-raise here, draw pinned
            parts.append((start, rows, path_frames))
            done += len(rows)
            if progress:
                progress(done, n)
            if on_partial and done >= next_partial and done < n:
                sofar = sorted(parts, key=lambda t: t[0])
                on_partial(mc._finalize([r for _, rs, _ in sofar for r in rs],
                                        [p for _, _, ps in sofar for p in ps], base_run), done)
                next_partial = done + partial_every
        parts.sort(key=lambda t: t[0])                 # global draw order — bit-parity requires it
        rows = [r for _, rs, _ in parts for r in rs]
        path_frames = [p for _, _, ps in parts for p in ps]
        return mc._finalize(rows, path_frames, base_run)
    finally:
        if own:
            ex.shutdown()
