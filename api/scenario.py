"""/api/run — sanitize a request through the URL codec, then build the ScenarioPayload.

The request body is {"preset", "overlays", "levers"} with lever keys = the UI grid / URL-param
names. Sanitization IS `parse_query_config`: the body is flattened to a query-param dict and run
through the same clamp/snap/drop-junk path that protects shared URLs — a hand-crafted request
can never 500 the model. Responses are cached by cfg_repr (LRU 16) so slider back-and-forth is
instant; the payload itself comes from fiscal_model.webpayload — the same function that wrote
the committed static bundles, so static ≡ live by construction (pinned in tests/test_api.py).
"""
from __future__ import annotations

import threading
from collections import OrderedDict

from fiscal_model import webpayload
from fiscal_model.app_params import parse_query_config


def sanitize(body: dict) -> dict:
    qp: dict[str, str] = {}
    preset = body.get("preset")
    if isinstance(preset, str):
        qp["preset"] = preset
    overlays = body.get("overlays") or []
    if isinstance(overlays, list) and overlays:
        qp["ov"] = ",".join(str(k) for k in overlays)
    levers = body.get("levers") or {}
    if isinstance(levers, dict):
        for k, v in levers.items():
            if v is True:
                qp[str(k)] = "1"
            elif v is False:
                qp[str(k)] = "0"
            else:
                qp[str(k)] = f"{v:g}" if isinstance(v, float) else str(v)
    return parse_query_config(qp)


class ScenarioService:
    def __init__(self, data, deltas):
        self.data, self.deltas = data, deltas
        self.lock = threading.Lock()
        self.ctx_cache: dict = {}                       # overlay-readout contexts (shared)
        self.payloads: OrderedDict[str, dict] = OrderedDict()     # cfg_repr -> payload (LRU 16)

    def run(self, body: dict) -> dict:
        cfg = sanitize(body)
        rep = webpayload.cfg_repr_for(cfg)
        with self.lock:
            hit = self.payloads.get(rep)
            if hit is not None:
                self.payloads.move_to_end(rep)
                return hit
        payload = webpayload.build_scenario_payload(self.data, self.deltas, cfg,
                                                    ctx_cache=self.ctx_cache)
        with self.lock:
            self.payloads[rep] = payload
            while len(self.payloads) > 16:
                self.payloads.popitem(last=False)
            while len(self.ctx_cache) > 4:              # bound the readout contexts too
                self.ctx_cache.pop(next(iter(self.ctx_cache)))
        return payload
