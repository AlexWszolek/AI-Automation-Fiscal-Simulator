"""Tornado jobs — one worker thread, a queue, and two small LRUs.

The sensitivity tornado for a MODIFIED config costs ~40s (N=150 seeded draws through the MC fast
path), so it runs as a background job the front end polls at 1s. Pristine configs never reach the
worker: their entries come straight from the committed precompute artifact (the same repr-exact
match the Streamlit app uses). Results are cached by cfg_repr (LRU 32) and duplicate submissions
of an in-flight config return the existing job id.
"""
from __future__ import annotations

import json
import threading
import uuid
from collections import OrderedDict
from pathlib import Path
from queue import Queue

from fiscal_model import mc as mc_mod
from fiscal_model import webpayload
from fiscal_model.app_params import canon

TORNADO_N, TORNADO_SPREAD, TORNADO_SEED = 150, 0.15, 0
_PRECOMP = Path(__file__).resolve().parent.parent / "data" / "app_precomputed" / "mc_tornado.json"


def _entry_from_result(r, n: int) -> dict:
    finals = r.paths[r.paths["period"] == r.paths["period"].max()]["fed_deficit_B"]
    tor = r.tornado.query("target == 'final_fed_deficit_B'")
    return {
        "tornado": [{"lever": t.lever, "spearman": float(t.spearman)} for t in tor.itertuples()],
        "p10": float(finals.quantile(0.10)), "p50": float(finals.quantile(0.50)),
        "p90": float(finals.quantile(0.90)), "n": n,
    }


class TornadoJobs:
    def __init__(self, data, deltas):
        self.data, self.deltas = data, deltas
        self.lock = threading.Lock()
        self.queue: Queue = Queue()
        self.jobs: dict[str, dict] = {}                  # job_id -> {status, done, total, result?}
        self.by_repr: dict[str, str] = {}                # cfg_repr -> live job_id (dedupe)
        self.results: OrderedDict[str, dict] = OrderedDict()      # cfg_repr -> entry (LRU 32)
        self.contexts: OrderedDict[str, mc_mod.ScenarioContext] = OrderedDict()   # LRU 4
        try:
            payload = json.loads(_PRECOMP.read_text())
            self.precomputed = {e["cfg_repr"]: {"tornado": e["tornado"], "p10": e["p10"],
                                                "p50": e["p50"], "p90": e["p90"],
                                                "n": payload["n"]}
                                for e in payload["entries"]}
        except FileNotFoundError:
            self.precomputed = {}
        threading.Thread(target=self._worker, daemon=True, name="tornado-worker").start()

    # ------------------------------------------------------------------ public
    def submit(self, cfg: dict, n: int = TORNADO_N) -> dict:
        rep = webpayload.cfg_repr_for(cfg)
        hit = self.precomputed.get(rep)
        if hit is None:
            with self.lock:
                hit = self.results.get(rep)
        if hit is not None:
            job_id = f"cached-{uuid.uuid4().hex[:8]}"
            return {"job_id": job_id, "status": "done", "result": hit}
        with self.lock:
            live = self.by_repr.get(rep)
            if live is not None and self.jobs[live]["status"] in ("queued", "running"):
                j = self.jobs[live]
                return {"job_id": live, "status": j["status"], "done": j["done"], "total": j["total"]}
            job_id = uuid.uuid4().hex[:12]
            self.jobs[job_id] = {"status": "queued", "done": 0, "total": n, "cfg_repr": rep}
            self.by_repr[rep] = job_id
        self.queue.put((job_id, cfg, rep, n))
        return {"job_id": job_id, "status": "queued", "done": 0, "total": n}

    def status(self, job_id: str) -> dict | None:
        with self.lock:
            j = self.jobs.get(job_id)
            return dict(j) if j is not None else None

    # ------------------------------------------------------------------ worker
    def _context_for(self, base) -> mc_mod.ScenarioContext:
        key = webpayload.cfg_key(base)
        ctx = self.contexts.get(key)
        if ctx is None:
            ctx = mc_mod.ScenarioContext(self.data, self.deltas, base)
            self.contexts[key] = ctx
            while len(self.contexts) > 4:
                self.contexts.popitem(last=False)
        else:
            self.contexts.move_to_end(key)
        return ctx

    def _worker(self) -> None:
        while True:
            job_id, cfg, rep, n = self.queue.get()
            try:
                job = self.jobs[job_id]
                job["status"] = "running"
                base = canon(webpayload.resolve_config(cfg)["v2p"])
                ctx = self._context_for(base)

                def progress(i: int, total: int) -> None:
                    job["done"], job["total"] = i, total

                r = mc_mod.run_mc(ctx, n=n, spread=TORNADO_SPREAD, seed=TORNADO_SEED,
                                  progress=progress)
                entry = _entry_from_result(r, n)
                with self.lock:
                    job.update(status="done", done=n, total=n, result=entry)
                    self.results[rep] = entry
                    while len(self.results) > 32:
                        self.results.popitem(last=False)
            except Exception as e:                       # fail the job, never the worker
                with self.lock:
                    self.jobs[job_id].update(status="error", message=str(e))
