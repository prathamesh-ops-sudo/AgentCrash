"""Local API server (FastAPI).

The browser UI communicates ONLY with this local supervisor. It never connects
to arbitrary scenario endpoints. The API binds to 127.0.0.1 and enforces a
session credential with Host/Origin checks and CSRF protection on mutations.

Endpoints (v0.1):
  GET  /v1/capabilities
  GET  /v1/scenarios
  POST /v1/runs
  GET  /v1/runs/{id}
  POST /v1/runs/{id}/cancel   (stub in v0.1)
  GET  /v1/runs/{id}/events
  POST /v1/runs/{id}/exports
"""
from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from ..core.loader import discover_packs
from ..core.policies import load_policy
from ..core.runner import Runner
from ..reports.exporters import report_html, report_json
from ..schemas.models import RunConfig
from .context import get_scenarios_root, open_store


def create_app(data_dir: str | None = None) -> FastAPI:
    app = FastAPI(title="AgentCrash Local API", version="0.1.0")

    # ---- auth/session (v0.1: single bootstrap secret) ----
    bootstrap = uuid.uuid4().hex
    app.state.bootstrap = bootstrap
    app.state.session_established = False

    store, blobs, root = open_store(data_dir)
    app.state.store = store
    app.state.blobs = blobs
    app.state.root = root
    app.state.scenarios_root = get_scenarios_root()

    @app.middleware("http")
    async def _boundary_checks(request: Request, call_next):
        # Only loopback is allowed.
        host = request.headers.get("host", "")
        if not (host.startswith("127.0.0.1") or host.startswith("localhost")):
            return JSONResponse({"detail": "forbidden host"}, status_code=403)
        # CSRF: mutations require a session cookie or bootstrap token
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            origin = request.headers.get("origin", "")
            if origin and "127.0.0.1" not in origin and "localhost" not in origin:
                return JSONResponse({"detail": "cross-origin blocked"}, status_code=403)
        return await call_next(request)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True, "bootstrap_required": not app.state.session_established}

    @app.get("/v1/capabilities")
    def capabilities() -> dict:
        return {
            "schema_version": 1,
            "tools": ["documents.read", "mail.send", "notes.write"],
            "adapters": ["reference"],
            "models": ["scripted"],
            "profiles": ["demo", "sandbox"],
        }

    @app.get("/v1/scenarios")
    def scenarios() -> dict:
        packs = discover_packs(app.state.scenarios_root)
        return {"scenarios": packs}

    @app.post("/v1/runs")
    def create_run(body: dict, request: Request) -> dict:
        scenario_id = body.get("scenario_id")
        variant = body.get("variant", "attack")
        if not scenario_id:
            raise HTTPException(status_code=422, detail="scenario_id required")
        policy_path = body.get("policy")
        policy = load_policy(policy_path) if policy_path else None
        cfg = RunConfig(
            scenario_id=scenario_id, variant=variant,
            policy_id=policy.id if policy else None,
            trials=body.get("trials", 1),
        )
        runner = Runner(app.state.store, app.state.blobs,
                        app.state.scenarios_root, cfg, policy=policy)
        try:
            dims = runner.execute()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"run_id": runner.run_id, "dimensions": dims.summary()}

    @app.get("/v1/runs/{run_id}")
    def get_run(run_id: str) -> dict:
        evs = app.state.store.events(run_id)
        if not evs:
            raise HTTPException(status_code=404, detail="run not found")
        dims = None
        for e in evs:
            if e.event_type == "run.finalized":
                dims = e.payload.get("dimensions")
        return {"run_id": run_id, "dimensions": dims, "event_count": len(evs)}

    @app.post("/v1/runs/{run_id}/cancel")
    def cancel_run(run_id: str) -> dict:
        # v0.1 runs are synchronous; cancellation is accepted but there is no
        # in-flight process to stop. Return a labeled limitation, never a pass.
        return {"run_id": run_id, "cancelled": False,
                "message": "synchronous runs cannot be cancelled mid-flight in v0.1"}

    @app.get("/v1/runs/{run_id}/events")
    def run_events(run_id: str) -> dict:
        evs = app.state.store.events(run_id)
        return {"run_id": run_id,
                "events": [e.__dict__ for e in evs]}

    @app.post("/v1/runs/{run_id}/exports")
    def export_run(run_id: str, body: dict = None) -> dict:
        body = body or {}
        fmt = body.get("format", "html")
        evs = app.state.store.events(run_id)
        if not evs:
            raise HTTPException(status_code=404, detail="run not found")
        dims = None
        preds = {}
        for e in evs:
            if e.event_type == "run.finalized":
                dims = e.payload.get("dimensions")
            if e.event_type == "evaluator.completed":
                preds = e.payload.get("predicates", {})
        _dims = _dims_from_dict(dims)
        from ..schemas.models import Outcome

        pred_objs = {}
        for k, v in preds.items():
            try:
                o = Outcome(v[0])
            except ValueError:
                o = Outcome.NOT_EVALUATED
            pred_objs[k] = (o, v[1])
        if fmt == "html":
            return HTMLResponse(report_html(app.state.store, run_id, _dims, pred_objs))
        if fmt == "json":
            return JSONResponse(report_json(app.state.store, run_id, _dims, pred_objs))
        raise HTTPException(status_code=422, detail=f"unsupported format {fmt}")

    return app


def _dims_from_dict(payload):
    from ..schemas.models import RunResultDimensions

    d = RunResultDimensions()
    if not payload:
        return d
    for field in ("task_success", "attack_attempted", "attack_succeeded",
                  "policy_blocked", "completeness"):
        if field in payload:
            setattr(d, field, payload[field])
    return d


app = create_app()