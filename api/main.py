"""The compute service: static presets need no server; this exists for custom slider values and
modified-config tornados. Run behind nginx/caddy with /api proxied here; the front end only ever
calls relative /api paths.

Dev:   .venv/bin/uvicorn api.main:app --port 8000
Tests: create_app(backend=(data, deltas)) skips the ~5s data load.
"""
from __future__ import annotations

import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.jobs import TornadoJobs                          # noqa: E402
from api.scenario import ScenarioService, sanitize        # noqa: E402


def _load_backend():
    from fiscal_model import loaders
    from fiscal_model.dynamics import precompute_worker_deltas
    from fiscal_model.kernel import KernelParams
    from fiscal_model.transfers import TransferLookup
    data = loaders.load_all(validate=False)
    deltas = precompute_worker_deltas(data, TransferLookup(), KernelParams())
    return data, deltas


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, timeout=5).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def create_app(backend=None) -> FastAPI:
    state: dict = {"ready": False}

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        data, deltas = backend if backend is not None else _load_backend()
        state["scenarios"] = ScenarioService(data, deltas)
        state["jobs"] = TornadoJobs(data, deltas)
        state["sha"] = _git_sha()
        state["ready"] = True
        yield

    app = FastAPI(title="AI Automation Fiscal Simulator API",
                  docs_url=None, redoc_url=None, lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict:
        from fiscal_model.presets import PRESETS
        return {"status": "ok", "model_loaded": state["ready"],
                "presets": len(PRESETS) + 1, "version": state.get("sha", "unknown")}

    @app.post("/api/run")
    def run(body: dict) -> dict:
        return state["scenarios"].run(body)

    @app.post("/api/tornado")
    def tornado(body: dict) -> dict:
        n = body.get("n")
        n = int(n) if isinstance(n, (int, float)) and 4 <= int(n) <= 300 else 150
        return state["jobs"].submit(sanitize(body), n=n)

    @app.get("/api/tornado/{job_id}")
    def tornado_status(job_id: str) -> dict:
        j = state["jobs"].status(job_id)
        if j is None:
            raise HTTPException(404, "unknown job")
        return j

    return app


app = create_app()
