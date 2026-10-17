"""FastAPI app. Endpoints not yet backed by live data serve the frozen fixtures."""
import json
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response

from . import schemas, stress
from .grading import summarise
from .config import settings
from .db import Db

# Footprint size by customers affected, until the combiner (Ahmed, F3) writes the classified scale.
STREET_MAX_CUSTOMERS = 100
AREA_MAX_CUSTOMERS = 2000


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.started_at = datetime.now(UTC)
    app.state.api_db = Db("bn_api")
    app.state.runtime = None
    if os.environ.get("BN_WORKERS") == "1":
        from .runtime import Runtime

        app.state.runtime = Runtime()
        app.state.runtime.start()
    yield
    if app.state.runtime is not None:
        await app.state.runtime.stop()
    app.state.api_db.close()


app = FastAPI(title="Blacknaught API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json",
              lifespan=lifespan)


@lru_cache
def fixture(name: str) -> Any:
    path: Path = settings().fixtures_dir / "api" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/health", response_model=schemas.Health)
async def health(request: Request):
    runtime = request.app.state.runtime
    db_ok = (await request.app.state.api_db.run("SELECT 1"))[0][0] == 1
    return {
        "ok": db_ok,
        "db": db_ok,
        "writer_lag": runtime.writer.lag if runtime else 0,
        "model": "none",
        "uptime_s": int((datetime.now(UTC) - request.app.state.started_at).total_seconds()),
    }


@app.get("/api/sources/health", response_model=schemas.SourcesHealth)
def sources_health(request: Request):
    now = datetime.now(UTC)
    runtime = request.app.state.runtime
    return {"at": now, "sources": [h.as_dict(now) for h in runtime.health.values()] if runtime else []}


def footprint_scale(customers: int | None) -> str:
    if customers is None:
        return "unresolved"
    if customers <= STREET_MAX_CUSTOMERS:
        return "street"
    return "area" if customers <= AREA_MAX_CUSTOMERS else "region"


@app.get("/api/outages", response_model=list[schemas.Outage])
async def outages(request: Request,
                  status: str | None = Query(default=None, pattern="^(active|restored|vanished|planned)$"),
                  limit: int = Query(default=500, ge=1, le=2000)):
    rows = await request.app.state.api_db.rows(
        "SELECT * FROM v_outage_public WHERE (CAST(:status AS text) IS NULL OR status = :status)"
        " ORDER BY started_at DESC LIMIT :limit",
        status=status, limit=limit,
    )
    now = datetime.now(UTC)
    return [{
        "id": r["outage_id"],
        "source": r["source"],
        "label": r["label"],
        "status": r["status"],
        "started_at": r["started_at"],
        "restored_at": r["restored_at"],
        "elapsed_h": round(((r["restored_at"] or now) - r["started_at"]).total_seconds() / 3600, 2),
        "customers": r["customers"],
        "priority_customers": r["priority_customers"],
        "scale": footprint_scale(r["customers"]),
        "cell_l1": r["cell_l1"],
        "centroid": (r["lat"], r["lon"]) if r["lat"] is not None else None,
        "postcode_count": len(r["postcodes"]),
    } for r in rows]


@app.get("/api/grids/{grid}/stress", response_model=schemas.GridStress)
async def grid_stress(request: Request, grid: str):
    if grid != "gb":
        raise HTTPException(404, "unknown grid")
    rows = await request.app.state.api_db.rows("SELECT measured_at, hz FROM v_freq_latest WHERE grid = :g", g=grid)
    hz = float(rows[0]["hz"]) if rows else None
    return {
        "grid": grid,
        "hz": hz,
        "measured_at": rows[0]["measured_at"] if rows else None,
        "state": stress.state(hz),
        "seconds_to_next_rung": None,
        "label": "LIVE",
    }


@app.get("/api/cells", response_model=list[schemas.Cell])
def cells(level: int = Query(default=1, ge=1, le=3)):
    return [c for c in fixture("cells") if c["level"] == level]


@app.get("/api/areas/risk", response_model=list[schemas.AreaRisk])
def areas_risk():
    return fixture("areas_risk")


@app.get("/api/triage", response_model=schemas.Triage)
async def triage(request: Request, limit: int = Query(default=50, ge=1, le=200),
                 cursor: int = Query(default=0, ge=0)):
    rows = await request.app.state.api_db.rows(
        "SELECT * FROM v_triage_latest WHERE rank > :cursor ORDER BY rank LIMIT :limit", cursor=cursor, limit=limit + 1
    )
    runtime = request.app.state.runtime
    model = runtime.scorer.model if runtime else None
    items = [{
        "rank": r["rank"],
        "patient_ref": r["patient_ref"],
        "outage_id": r["outage_id"],
        "scale": footprint_scale(r["customers"]),
        "device": r["device"],
        "reserve_left_h": r["why"]["reserve_left_h"],
        "remaining_h": r["why"]["remaining_h"],
        "q_used": r["q_used"],
        "harm": r["harm"],
        "escalate": r["escalate"],
        "why": r["why"]["reasons"],
        "decision_id": None,
    } for r in rows[:limit]]
    return {
        "tick_at": rows[0]["tick_at"] if rows else datetime.now(UTC),
        "model": {"id": model.model_id, "sha256": model.sha256, "label": model.label} if model
        else {"id": rows[0]["model_id"] if rows else "none", "sha256": "", "label": "UNKNOWN"},
        "items": items,
        "next_cursor": rows[limit - 1]["rank"] if len(rows) > limit else None,
    }


@app.post("/api/decisions/{decision_id}/approve", response_model=schemas.DecisionState)
def approve(decision_id: str, body: schemas.Approval):
    return {**fixture("decision_state"), "decision_id": decision_id, "state": "approved" if body.approve else "rejected"}


@app.get("/api/agent/decisions", response_model=list[schemas.AgentDecision])
def agent_decisions():
    return fixture("agent_decisions")


@app.get("/api/agent/grades", response_model=schemas.Grades)
async def agent_grades(request: Request):
    rows = await request.app.state.api_db.rows(
        "SELECT horizon_h, model_id, source, brier, censored, p_still_off, graded_at FROM v_grades"
    )
    return summarise(rows)


@app.get("/api/alerts/cap/{decision_id}", responses={200: {"content": {"application/cap+xml": {}}}})
def cap_alert(decision_id: str):
    raise HTTPException(404, "no approved CAP alert for this decision")


@app.post("/api/auth/login", response_model=schemas.LoginResult)
def login(body: schemas.Login):
    raise HTTPException(401, "invalid credentials")


@app.post("/api/auth/logout", status_code=204)
def logout():
    return Response(status_code=204)


@app.get("/api/me/home", response_model=schemas.MyHome)
def me_home():
    return fixture("me_home")


@app.get("/api/audit/verify", response_model=schemas.AuditVerify)
def audit_verify():
    return fixture("audit_verify")
