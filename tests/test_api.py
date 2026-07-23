"""API contract gate — the compute service must agree with the committed static bundles
(static ≡ live, the anti-drift guarantee), survive junk requests, and run tornado jobs.

Uses fastapi.testclient over create_app(backend=...) with the session data fixture, so no
double data load. The TestClient context manager runs the lifespan (model wiring)."""
import json
from pathlib import Path

import pandas as pd
import pytest

from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model import reabsorption

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = ROOT / "web" / "public" / "data" / "scenarios"


@pytest.fixture(scope="module")
def client(data):
    if not DELTA_CACHE.exists() or not reabsorption.engine_artifacts_exist():
        pytest.skip("build artifacts not present")
    from fastapi.testclient import TestClient
    from api.main import create_app
    deltas = pd.read_parquet(DELTA_CACHE)
    with TestClient(create_app(backend=(data, deltas))) as c:
        yield c


def test_health(client):
    r = client.get("/api/health").json()
    assert r["status"] == "ok" and r["model_loaded"] and r["presets"] == 13


def test_static_equals_live_for_pristine_presets(client):
    """THE gate: /api/run of a pristine config must equal its committed bundle exactly —
    both sides are webpayload.build_scenario_payload, so drift means a stale bundle."""
    for slug, body in [("acemoglu-modest", {"preset": "acemoglu-modest"}),
                       ("custom", {}),
                       ("agi-5y~ubi", {"preset": "agi-5y", "overlays": ["ubi"]}),
                       # multi-overlay: covers the combined-readout reuse of the main run
                       ("agi-5y~cw-robot-tax+compute-parity",
                        {"preset": "agi-5y", "overlays": ["cw-robot-tax", "compute-parity"]}),
                       # Baumol preset: covers the per-period _interp_rows wage-dynamics path
                       # (≤1 ulp vs np.interp — invisible at the payload's 4-decimal rounding)
                       ("karger-rapid~swf+fed-vat",
                        {"preset": "karger-rapid", "overlays": ["swf", "fed-vat"]})]:
        bundle = json.loads((SCENARIOS / f"{slug}.json").read_text())
        live = client.post("/api/run", json=body).json()
        assert live == bundle, f"{slug}: live response drifted from the committed bundle — " \
                               "re-run scripts/gen_web_bundle.py"


def test_pooled_context_matches_fresh_model(client, data):
    """The service reuses a ScenarioContext pool across requests; a lever-modified config
    served through the pool must be bit-identical to a fresh DynamicModelV2 build."""
    from api.scenario import sanitize
    from fiscal_model import webpayload
    body = {"preset": "agi-5y", "levers": {"cog": 0.55, "reab": 0.02}}
    client.post("/api/run", json={"preset": "agi-5y"})       # warms the pool for this shape
    pooled = client.post("/api/run", json=body).json()       # served via the warm pool
    deltas = pd.read_parquet(DELTA_CACHE)
    fresh = webpayload.build_scenario_payload(data, deltas, sanitize(body))          # no pool
    assert pooled == json.loads(json.dumps(fresh))


def test_junk_request_never_500s(client):
    r = client.post("/api/run", json={"preset": "nope", "overlays": ["bogus", "ubi"],
                                      "levers": {"cog": 99, "demand": -5, "banana": "phone",
                                                 "ubi": "not-a-number"}})
    assert r.status_code == 200
    cfg = r.json()["config"]
    assert cfg["preset"] is None and cfg["overlays"] == ["ubi"]
    assert cfg["levers"]["cog"] == 1.0 and cfg["levers"]["demand"] == 0.0    # clamped to the grid
    assert "banana" not in cfg["levers"] and "ubi" not in cfg["levers"]      # junk dropped


def test_overlay_readouts_reconcile(client):
    p = client.post("/api/run", json={"preset": "agi-5y", "overlays": ["cw-robot-tax"]}).json()
    (ro,) = p["overlay_readouts"]
    base = client.post("/api/run", json={"preset": "agi-5y"}).json()
    assert abs(ro["gap_B"] - base["final"]["fed_deficit_B"]) < 0.01
    assert ro["recovered_B"] != 0


def test_tornado_precomputed_is_instant(client):
    r = client.post("/api/tornado", json={"preset": "windfall-medium"}).json()
    assert r["status"] == "done" and r["result"]["n"] == 200
    assert r["result"]["p10"] <= r["result"]["p50"] <= r["result"]["p90"]


def test_tornado_overlay_cart_is_instant(client):
    """Ticking a policy response must NOT trigger a live job — the precompute covers every
    pristine preset × overlay cart (the most common interaction on the site)."""
    for body in ({"preset": "agi-5y", "overlays": ["ubi"]},
                 {"preset": "acemoglu-modest", "overlays": ["cw-robot-tax", "compute-parity"]}):
        r = client.post("/api/tornado", json=body).json()
        assert r["status"] == "done" and r["result"]["n"] == 200, body


def test_tornado_job_partial_surfaces(client, monkeypatch):
    """While a job refines, the status endpoint carries a labeled partial entry (progressive
    display); the final result supersedes it and the partial key disappears."""
    import api.jobs as jobs_mod
    monkeypatch.setattr(jobs_mod, "TORNADO_PARTIAL_EVERY", 4)
    body = {"preset": "brynjolfsson-augment", "levers": {"reab": 0.02}, "n": 12}
    r = client.post("/api/tornado", json=body).json()
    assert r["status"] in ("queued", "running")
    import time
    partials, s = [], None
    for _ in range(1200):
        s = client.get(f"/api/tornado/{r['job_id']}").json()
        if "partial" in s:
            partials.append(s["partial"]["n"])
        if s["status"] in ("done", "error"):
            break
        time.sleep(0.05)
    assert s["status"] == "done", s
    assert partials and all(4 <= p < 12 for p in partials)    # refining entries appeared
    assert "partial" not in s and s["result"]["n"] == 12      # superseded on completion


def test_tornado_job_lifecycle(client):
    """A modified config runs through the worker (tiny N to keep the suite fast)."""
    body = {"preset": "acemoglu-modest", "levers": {"cog": 0.5}, "n": 6}
    r = client.post("/api/tornado", json=body).json()
    assert r["status"] in ("queued", "running")
    job_id = r["job_id"]
    import time
    for _ in range(600):
        s = client.get(f"/api/tornado/{job_id}").json()
        if s["status"] in ("done", "error"):
            break
        time.sleep(0.1)
    assert s["status"] == "done", s
    assert s["result"]["n"] == 6 and len(s["result"]["tornado"]) > 5
    # resubmitting the same config is now an instant cache hit
    again = client.post("/api/tornado", json=body).json()
    assert again["status"] == "done"
    assert client.get("/api/tornado/does-not-exist").status_code == 404
