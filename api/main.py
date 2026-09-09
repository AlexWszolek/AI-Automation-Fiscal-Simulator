"""The compute service: static presets need no server; this exists for custom slider values and
modified-config tornados. Run behind nginx/caddy with /api proxied here; the front end only ever
calls relative /api paths.

Dev:   .venv/bin/uvicorn api.main:app --port 8000
Tests: create_app(backend=(data, deltas)) skips the ~5s data load.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.jobs import TornadoJobs                          # noqa: E402
from api.korea import KoreaScenarioService                # noqa: E402
from api.scenario import ScenarioService, sanitize        # noqa: E402

# Tester feedback lands here as JSON lines — server-local, gitignored (may contain contact
# info). Module-level so tests can monkeypatch the path.
FEEDBACK_PATH = ROOT / "data" / "feedback" / "feedback.jsonl"
FEEDBACK_COOLDOWN_S = 30.0        # per-client; in-memory, resets on restart — spam brake, not auth
# FISCAL_KOREA_ONLY=1: the Korea package (scripts/package_korea.py) ships without the US
# model's data, so the US backend is not loaded and the US routes answer 503. The Korea
# routes are untouched — they build their own pools on first request either way.
KOREA_ONLY = os.environ.get("FISCAL_KOREA_ONLY") == "1"


def _load_backend():
    from fiscal_model import loaders
    from fiscal_model.dynamics import precompute_worker_deltas
    from fiscal_model.kernel import KernelParams
    from fiscal_model.transfers import TransferLookup
    data = loaders.load_all(validate=False)
    deltas = precompute_worker_deltas(data, TransferLookup(), KernelParams())
    return data, deltas


def _tornado_n(body: dict, lo: int, hi: int, default: int = 150) -> int:
    """Draw count from a request body, lo..hi else the default. json.loads accepts 1e400,
    NaN and Infinity, and int() of those raises INSIDE a guard expression — a 500 from
    valid JSON — so the conversion is fenced."""
    try:
        n = int(body.get("n"))
    except (TypeError, ValueError, OverflowError):
        return default
    return n if lo <= n <= hi else default


def _client_id(request: Request) -> str:
    """The feedback cooldown's key. Behind the reverse proxy request.client is loopback and
    the LAST X-Forwarded-For hop is the address the proxy itself appended; every earlier
    hop — and the whole header when there is no proxy — is client-supplied, and keying on
    it let a sender mint a fresh cooldown per request."""
    host = request.client.host if request.client else "unknown"
    if host in ("127.0.0.1", "::1", "localhost"):
        hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",")
                if h.strip()]
        if hops:
            return hops[-1]
    return host


def _git_sha() -> str:
    # a packaged checkout has no .git: the packager writes the source commit to VERSION
    version = ROOT / "VERSION"
    if version.exists():
        return version.read_text(encoding="utf-8").strip() or "unknown"
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, timeout=5).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def create_app(backend=None) -> FastAPI:
    state: dict = {"ready": False}

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if backend is None and KOREA_ONLY:
            state["scenarios"] = state["jobs"] = None
        else:
            data, deltas = backend if backend is not None else _load_backend()
            state["scenarios"] = ScenarioService(data, deltas)
            state["jobs"] = TornadoJobs(data, deltas)
        state["korea"] = KoreaScenarioService()           # lazy: builds on first request
        state["sha"] = _git_sha()
        state["ready"] = True
        yield

    app = FastAPI(title="AI Automation Fiscal Simulator API",
                  docs_url=None, redoc_url=None, lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict:
        from fiscal_model.presets import PRESETS
        from fiscal_model.korea_cells import PAYM39_CSV
        # korea_data: the gitignored tidy tables bootstrap step 7 builds; without them
        # every /api/korea/* request 500s while this endpoint used to say "ok"
        return {"status": "ok", "model_loaded": state["ready"],
                "mode": "korea" if state.get("scenarios") is None and state["ready"] else "full",
                "korea_data": PAYM39_CSV.exists(),
                "presets": len(PRESETS) + 1, "version": state.get("sha", "unknown")}

    def _us(key: str):
        svc = state.get(key)
        if svc is None:
            raise HTTPException(503, "the US model is not loaded on this service")
        return svc

    @app.post("/api/run")
    def run(body: dict) -> dict:
        return _us("scenarios").run(body)

    @app.post("/api/korea/run")
    def korea_run(body: dict) -> dict:
        return state["korea"].run(body)

    @app.post("/api/korea/tornado")
    def korea_tornado(body: dict) -> dict:
        out = state["korea"].tornado(body, _tornado_n(body, 50, 400))
        if out.get("superseded"):
            # a newer tornado request arrived while this one waited; the page shows only
            # the latest, so this one is not worth the seconds of MC
            raise HTTPException(status_code=409, detail="superseded by a newer request")
        if out.get("busy"):
            raise HTTPException(status_code=429, detail="tornado queue is full; retry shortly")
        return out

    @app.post("/api/tornado")
    def tornado(body: dict) -> dict:
        return _us("jobs").submit(sanitize(body), n=_tornado_n(body, 4, 300))

    @app.get("/api/tornado/{job_id}")
    def tornado_status(job_id: str) -> dict:
        j = _us("jobs").status(job_id)
        if j is None:
            raise HTTPException(404, "unknown job")
        return j

    feedback_last: dict[str, float] = {}      # client -> last-accepted timestamp (cooldown)

    @app.post("/api/feedback")
    def feedback(body: dict, request: Request) -> dict:
        msg = str(body.get("message", "")).strip()
        if not msg:
            raise HTTPException(422, "empty message")
        if len(msg) > 5000:
            raise HTTPException(413, "message too long (5,000 characters max)")
        client = _client_id(request)
        now = time.monotonic()
        if len(feedback_last) > 1000:             # bounded: expired entries are dropped
            for k in [k for k in list(feedback_last) if now - feedback_last.get(k, now) > FEEDBACK_COOLDOWN_S]:
                feedback_last.pop(k, None)
        if now - feedback_last.get(client, -FEEDBACK_COOLDOWN_S) < FEEDBACK_COOLDOWN_S:
            raise HTTPException(429, "please wait a moment before sending more feedback")
        feedback_last[client] = now
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "message": msg,
               "contact": str(body.get("contact", "")).strip()[:200],
               "url": str(body.get("url", ""))[:600],       # the share-URL encodes the config
               "version": state.get("sha", "unknown")}
        FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        with FEEDBACK_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return {"ok": True}

    return app


app = create_app()
