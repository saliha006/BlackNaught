"""FastAPI app. Endpoints not yet backed by live data serve the frozen fixtures, labelled as such."""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Response

from . import schemas
from .config import settings

app = FastAPI(title="Blacknaught API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")


@lru_cache
def fixture(name: str) -> Any:
    path: Path = settings().fixtures_dir / "api" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/health", response_model=schemas.Health)
def health():
    return fixture("health")


@app.get("/api/sources/health", response_model=schemas.SourcesHealth)
def sources_health():
    return fixture("sources_health")


@app.get("/api/outages", response_model=list[schemas.Outage])
def outages(status: str | None = Query(default=None, pattern="^(active|restored|vanished|planned)$")):
    items = fixture("outages")
    return [o for o in items if status is None or o["status"] == status]


@app.get("/api/grids/{grid}/stress", response_model=schemas.GridStress)
def grid_stress(grid: str):
    if grid != "gb":
        raise HTTPException(404, "unknown grid")
    return fixture("grid_stress_gb")


@app.get("/api/cells", response_model=list[schemas.Cell])
def cells(level: int = Query(default=1, ge=1, le=3)):
    return [c for c in fixture("cells") if c["level"] == level]


@app.get("/api/areas/risk", response_model=list[schemas.AreaRisk])
def areas_risk():
    return fixture("areas_risk")


@app.get("/api/triage", response_model=schemas.Triage)
def triage(limit: int = Query(default=50, ge=1, le=200)):
    snapshot = dict(fixture("triage"))
    snapshot["items"] = snapshot["items"][:limit]
    return snapshot


@app.post("/api/decisions/{decision_id}/approve", response_model=schemas.DecisionState)
def approve(decision_id: str, body: schemas.Approval):
    return {**fixture("decision_state"), "decision_id": decision_id, "state": "approved" if body.approve else "rejected"}


@app.get("/api/agent/decisions", response_model=list[schemas.AgentDecision])
def agent_decisions():
    return fixture("agent_decisions")


@app.get("/api/agent/grades", response_model=schemas.Grades)
def agent_grades():
    return fixture("agent_grades")


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
