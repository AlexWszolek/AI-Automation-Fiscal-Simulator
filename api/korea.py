"""/api/korea/run — the Korea sibling of ScenarioService.

Lazy: the Korea data pools (3 exposure-variant datasets + contexts + the deltas table)
build on the FIRST Korea request, not at startup — the US service's boot path is untouched.
Warm requests are ~30ms (one 40-year run per exposure variant + projections), cached by
config repr (LRU 16) like the US service.

Runs and tornados do NOT share a lock. A live tornado is a 150-draw MC — several seconds
on the production box — and while it held the single service lock every slider move
issued behind it waited for it (the ">1s per lever" the org reported). Each path now owns
its pools (contexts are built per pool, the deltas table is shared read-only), so a run
only ever waits for another run. Queued tornado requests that a newer one has superseded
return without computing: the page only shows the latest anyway.
"""
from __future__ import annotations

import json
import threading
from collections import OrderedDict

from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                           korea_mc_tornado, sanitize_korea_config)

SUPERSEDED = {"superseded": True}


class KoreaScenarioService:
    def __init__(self):
        self.run_lock = threading.Lock()
        self.mc_lock = threading.Lock()
        self.cache_lock = threading.Lock()
        self._deltas = None
        self.run_pools: dict | None = None
        self.mc_pools: dict | None = None
        self.payloads: OrderedDict[str, dict] = OrderedDict()
        self.mc_ticket = 0                      # the newest tornado request's number

    def _deltas_table(self):
        # the deltas table is read-only once built; both pools share it. Built under the
        # cache lock so two first-requests never double-build it.
        with self.cache_lock:
            if self._deltas is None:
                from fiscal_model.korea_assembly import build_korea_deltas
                self._deltas = build_korea_deltas()
            return self._deltas

    def _pools(self, which: str) -> dict:
        # called under the owning path's lock: the first request on a path pays ~1s
        attr = f"{which}_pools"
        if getattr(self, attr) is None:
            setattr(self, attr, {"data_pool": {}, "deltas": self._deltas_table(),
                                 "ctx_pool": {}})
        return getattr(self, attr)

    def _cached(self, rep: str):
        with self.cache_lock:
            hit = self.payloads.get(rep)
            if hit is not None:
                self.payloads.move_to_end(rep)
            return hit

    def _remember(self, rep: str, value: dict) -> None:
        with self.cache_lock:
            self.payloads[rep] = value
            while len(self.payloads) > 16:
                self.payloads.popitem(last=False)

    def tornado(self, body: dict, n: int) -> dict:
        cfg = sanitize_korea_config(body)
        rep = "tornado:" + str(n) + ":" + json.dumps(cfg, sort_keys=True)
        hit = self._cached(rep)
        if hit is not None:
            return hit
        with self.cache_lock:
            self.mc_ticket += 1
            mine = self.mc_ticket
        with self.mc_lock:
            if self.mc_ticket != mine:          # a newer request queued behind us
                return SUPERSEDED
            hit = self._cached(rep)
            if hit is not None:
                return hit
            pools = self._pools("mc")
            out = korea_mc_tornado(cfg, n=n, **pools)
            self._prune(pools)
        self._remember(rep, out)
        return out

    @staticmethod
    def _prune(pools: dict) -> None:
        # contexts key on (exposure, demography variant, tax mults) — the mult axis is
        # combinatorial, so keep an LRU-ish bound (insertion-ordered dict, oldest out)
        while len(pools["ctx_pool"]) > 12:
            pools["ctx_pool"].pop(next(iter(pools["ctx_pool"])))

    def run(self, body: dict) -> dict:
        cfg = sanitize_korea_config(body)
        rep = json.dumps(cfg, sort_keys=True)
        hit = self._cached(rep)
        if hit is not None:
            return hit
        with self.run_lock:
            hit = self._cached(rep)
            if hit is not None:
                return hit
            pools = self._pools("run")
            payload = build_korea_scenario_payload(cfg, **pools)
            self._prune(pools)
        self._remember(rep, payload)
        return payload
