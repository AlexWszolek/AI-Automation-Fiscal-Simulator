"""/api/korea/run — the Korea sibling of ScenarioService.

Lazy: the Korea data pools (3 exposure-variant datasets + contexts + the deltas table)
build on the FIRST Korea request, not at startup — the US service's boot path is untouched.
Warm requests are ~30ms (one 40-year run per exposure variant + projections), cached by
config repr (LRU 16) like the US service.
"""
from __future__ import annotations

import json
import threading
from collections import OrderedDict

from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                           korea_mc_tornado, sanitize_korea_config)


class KoreaScenarioService:
    def __init__(self):
        self.lock = threading.Lock()
        self.pools: dict | None = None
        self.payloads: OrderedDict[str, dict] = OrderedDict()

    def _ensure_pools(self) -> dict:
        # built under the request lock: the first Korea request pays ~1s, concurrent
        # first-requests wait rather than double-building
        if self.pools is None:
            from fiscal_model.korea_assembly import build_korea_deltas
            self.pools = {"data_pool": {}, "deltas": build_korea_deltas(),
                          "ctx_pool": {}}
        return self.pools

    def tornado(self, body: dict, n: int) -> dict:
        cfg = sanitize_korea_config(body)
        rep = "tornado:" + str(n) + ":" + json.dumps(cfg, sort_keys=True)
        with self.lock:
            hit = self.payloads.get(rep)
            if hit is not None:
                self.payloads.move_to_end(rep)
                return hit
            pools = self._ensure_pools()
            out = korea_mc_tornado(cfg, n=n, **pools)
            self.payloads[rep] = out
            while len(self.payloads) > 16:
                self.payloads.popitem(last=False)
        return out

    def run(self, body: dict) -> dict:
        cfg = sanitize_korea_config(body)
        rep = json.dumps(cfg, sort_keys=True)
        with self.lock:
            hit = self.payloads.get(rep)
            if hit is not None:
                self.payloads.move_to_end(rep)
                return hit
            pools = self._ensure_pools()
            payload = build_korea_scenario_payload(cfg, **pools)
            self.payloads[rep] = payload
            while len(self.payloads) > 16:
                self.payloads.popitem(last=False)
        return payload
