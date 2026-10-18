"""FastAPI app. Endpoints not yet backed by live data serve the frozen fixtures."""
import json
import os
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import uuid

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from sse_starlette.sse import EventSourceResponse

from . import arearisk, audit, auth, cells as grid, decisions, home, schemas, sse, stress
from .weatherrisk import WeatherRisk
from .grading import summarise
from .config import read_secret, settings
from .db import Db
from .timeparse import LONDON

# Footprint size by customers affected, until the combiner (Ahmed, F3) writes the classified scale.
STREET_MAX_CUSTOMERS = 100
AREA_MAX_CUSTOMERS = 2000


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.started_at = datetime.now(UTC)
    app.state.api_db = Db("bn_api")
    app.state.runtime = None
    app.state.login_limiter = auth.RateLimiter()
    app.state.risk_model = json.loads(settings().risk_model_path.read_text())
    # Without the M8 artifact the endpoint simply stays on the climatology baseline
    weather_path = settings().weather_model_path
    app.state.weather_risk = WeatherRisk(weather_path) if weather_path.exists() else None
    app.state.http = httpx.AsyncClient()
    app.state.bidx_key = bytes.fromhex(read_secret("bidx_key"))
    if os.environ.get("BN_WORKERS") == "1":
        from .runtime import Runtime

        app.state.runtime = Runtime()
        app.state.runtime.start()
    yield
    if app.state.runtime is not None:
        await app.state.runtime.stop()
    await app.state.http.aclose()
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
        "model": runtime.scorer.model.model_id if runtime else "none",
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


def _at_level(cell_l1: str, level: int) -> str:
    for _ in range(level - 1):
        cell_l1 = grid.parent(cell_l1)
    return cell_l1


@app.get("/api/cells", response_model=list[schemas.Cell])
async def cells(request: Request, level: int = Query(default=1, ge=1, le=3)):
    """Whole published map at one level. No bbox or point query on purpose: overlapping windows are a
    differencing attack, and the map is small enough to send whole."""
    db = request.app.state.api_db
    published = {r["cell_id"]: r["patients"] for r in
                 await db.rows("SELECT cell_id, patients FROM v_cells_published WHERE level = :l", l=level)}
    worst: dict[str, int] = {}
    for r in await db.rows("SELECT cell_l1, customers FROM v_outage_cells"):
        cell = _at_level(r["cell_l1"], level)
        worst[cell] = max(worst.get(cell, 0), r["customers"] or 0)
    return [{
        "cell_id": cell,
        "level": level,
        "bounds": grid.bounds(cell),
        "patients": "suppressed" if cell in published and published[cell] is None else published.get(cell, 0),
        "outage_scale": footprint_scale(worst[cell]) if cell in worst else None,
        "risk_tomorrow": None,
    } for cell in sorted(published.keys() | worst.keys())]


@app.get("/api/areas/risk", response_model=list[schemas.AreaRisk])
async def areas_risk(request: Request, day: date | None = Query(default=None, alias="date")):
    """Tomorrow (UK) by default. M8 on the live weather forecast (LIVE); the climatology baseline when it can't run."""
    day = day or (datetime.now(LONDON) + timedelta(days=1)).date()
    weather = request.app.state.weather_risk
    if weather is not None:
        forecast = await weather.area_risk(request.app.state.http, day)
        if forecast:
            return [{**r, "label": "LIVE"} for r in forecast]
    return [{**r, "label": "BASELINE"} for r in arearisk.area_risk(request.app.state.risk_model, day)]


@app.get("/api/triage", response_model=schemas.Triage)
async def triage(request: Request, limit: int = Query(default=50, ge=1, le=200),
                 cursor: int = Query(default=0, ge=0)):
    rows = await request.app.state.api_db.rows(
        "SELECT * FROM v_triage_latest WHERE rank > :cursor ORDER BY rank LIMIT :limit", cursor=cursor, limit=limit + 1
    )
    # Ahmed's agent files one escalate decision per patient and fault; link the newest so the row can be approved in place
    linked = {(d["patient"], d["outage_id"]): str(d["decision_id"]) for d in await request.app.state.api_db.rows(
        "SELECT decision_id, args->>'patient' AS patient, CAST(args->>'outage_id' AS int) AS outage_id"
        " FROM v_decisions WHERE tool = 'escalate' ORDER BY created_at")}
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
        "decision_id": linked.get((r["patient_ref"], r["outage_id"])),
    } for r in rows[:limit]]
    return {
        "tick_at": rows[0]["tick_at"] if rows else datetime.now(UTC),
        "model": {"id": model.model_id, "sha256": model.sha256, "label": model.label} if model
        else {"id": rows[0]["model_id"] if rows else "none", "sha256": "", "label": "UNKNOWN"},
        "items": items,
        "next_cursor": rows[limit - 1]["rank"] if len(rows) > limit else None,
    }


async def _principal(request: Request, role: str) -> auth.Principal:
    principal = await auth.resolve(request.app.state.api_db, request.cookies.get(auth.COOKIE))
    if principal is None:
        raise HTTPException(401, "login required")
    if principal.role != role:
        raise HTTPException(403, f"{role} only")
    return principal


async def operator(request: Request) -> auth.Principal:
    return await _principal(request, "operator")


async def household(request: Request) -> auth.Principal:
    return await _principal(request, "household")


@app.post("/api/decisions/{decision_id}/approve", response_model=schemas.DecisionState)
async def approve(request: Request, decision_id: uuid.UUID, body: schemas.Approval,
                  who: auth.Principal = Depends(operator)):
    db = request.app.state.api_db
    state, seq = await decisions.approve(db, str(decision_id), body.approve, who.login, body.note)
    if state is None:
        raise HTTPException(409, "decision is not awaiting approval")
    if state == "approved":
        runtime = request.app.state.runtime
        await decisions.export_cap(db, str(decision_id), who.login, runtime.signer if runtime else None)
    return {"decision_id": str(decision_id), "state": state, "audit_seq": seq}


@app.get("/api/agent/decisions", response_model=list[schemas.AgentDecision])
async def agent_decisions(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    rows = await request.app.state.api_db.rows(
        "SELECT decision_id, tool, state, created_at, args, rationale FROM v_decisions"
        " ORDER BY created_at DESC LIMIT :limit", limit=limit)
    return [{
        "id": str(r["decision_id"]),
        "tool": r["tool"],
        "state": r["state"],
        "created_at": r["created_at"],
        "args_summary": json.dumps(r["args"], sort_keys=True)[:200],
        "rationale": r["rationale"] or [],
    } for r in rows]


@app.get("/api/agent/grades", response_model=schemas.Grades)
async def agent_grades(request: Request):
    rows = await request.app.state.api_db.rows(
        "SELECT horizon_h, model_id, source, brier, censored, p_still_off, graded_at FROM v_grades"
    )
    return summarise(rows)


@app.get("/api/alerts/cap/{decision_id}", responses={200: {"content": {"application/cap+xml": {}}}})
async def cap_alert(request: Request, decision_id: uuid.UUID):
    db = request.app.state.api_db
    stored = await db.rows("SELECT xml, sig_b64 FROM v_cap_alert WHERE decision_id = :id", id=str(decision_id))
    if stored:
        headers = {"X-Signature-ML-DSA-65": stored[0]["sig_b64"]} if stored[0]["sig_b64"] else {}
        return Response(stored[0]["xml"], media_type="application/cap+xml", headers=headers)
    exists = await db.rows("SELECT state FROM v_decisions WHERE decision_id = :id AND tool = 'draft_cap_alert'",
                           id=str(decision_id))
    if exists:
        raise HTTPException(403, "CAP alert is not approved")
    raise HTTPException(404, "no CAP alert for this decision")


@app.post("/api/auth/login", response_model=schemas.LoginResult)
async def login(request: Request, response: Response, body: schemas.Login):
    client = request.client.host if request.client else "unknown"
    if not request.app.state.login_limiter.allow(client):
        raise HTTPException(429, "too many login attempts", headers={"Retry-After": "60"})
    db = request.app.state.api_db
    result = await auth.login(db, body.login, body.passphrase)
    await audit.append(db, "login", body.login, None, {"ok": result is not None, "client": client})
    if result is None:
        raise HTTPException(401, "invalid credentials")
    principal, token = result
    response.set_cookie(auth.COOKIE, token, httponly=True, samesite="strict", path="/api",
                        secure=request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https")
    return {"role": principal.role}


@app.post("/api/auth/logout", status_code=204)
async def logout(request: Request):
    await auth.logout(request.app.state.api_db, request.cookies.get(auth.COOKIE))
    response = Response(status_code=204)
    response.delete_cookie(auth.COOKIE, path="/api")
    return response


@app.get("/api/me/home", response_model=schemas.MyHome)
async def me_home(request: Request, who: auth.Principal = Depends(household)):
    """No id parameter on purpose: the household comes from the session, so one home can't ask for another."""
    body = await home.view(request.app.state.api_db, who.login, request.app.state.bidx_key)
    if body is None:
        raise HTTPException(404, "no register entry for this household")
    return body


@app.get("/stream")
async def stream(request: Request, last_event_id: int | None = Header(default=None)):
    runtime = request.app.state.runtime
    if runtime is None:
        raise HTTPException(503, "live workers are not running")
    try:
        client, backlog = runtime.broadcaster.subscribe(last_event_id)
    except sse.TooManyClients:
        raise HTTPException(503, "too many live viewers", headers={"Retry-After": "10"})
    # X-Accel-Buffering stops nginx holding events back in its proxy buffer
    return EventSourceResponse(runtime.broadcaster.stream(client, backlog), ping=15, send_timeout=10,
                               headers={"X-Accel-Buffering": "no"})


@app.get("/api/audit/verify", response_model=schemas.AuditVerify)
async def audit_verify(request: Request):
    runtime = request.app.state.runtime
    return await audit.verify(request.app.state.api_db, runtime.signer if runtime else None)


@app.get("/api/audit/checkpoints", response_model=list[schemas.SignedCheckpoint])
async def audit_checkpoints(request: Request, after: int = Query(default=0, ge=0),
                            limit: int = Query(default=100, ge=1, le=500)):
    """Signed checkpoints with the exact bytes the signer signed, so anyone can check them against
    contracts/signer_pub.pem without trusting this server. Unsigned ones are left out."""
    rows = await request.app.state.api_db.rows(
        "SELECT seq, head, at, alg, key_id, sig_b64 FROM v_audit_checkpoint"
        " WHERE seq > :after AND sig_b64 IS NOT NULL ORDER BY seq LIMIT :limit", after=after, limit=limit)
    return [{**r, "head": bytes(r["head"]).hex(),
             "payload": audit.checkpoint_payload(r["seq"], bytes(r["head"]), r["at"]).decode()} for r in rows]
