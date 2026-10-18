"""API response contracts (frozen into contracts/openapi.yaml)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# BASELINE = a statistical stand-in from real history (e.g. climatology) until the real model replaces it
Label = Literal["LIVE", "SIMULATED", "REPLAY", "TRANSFERRED", "BASELINE"]
Scale = Literal["home", "street", "area", "region", "system", "brownout", "unresolved"]


class Health(BaseModel):
    ok: bool
    db: bool
    writer_lag: int
    model: str
    uptime_s: int


class SourceState(BaseModel):
    source: str
    status: Literal["ok", "stale", "down", "degraded"]
    interval_s: int
    staleness_s: int | None
    records_last: int | None
    consecutive_failures: int
    label: Label


class SourcesHealth(BaseModel):
    at: datetime
    sources: list[SourceState]


class Outage(BaseModel):
    id: int
    source: str
    label: Label
    status: Literal["active", "restored", "vanished", "planned"]
    started_at: datetime
    restored_at: datetime | None
    elapsed_h: float
    customers: int | None
    priority_customers: int | None
    scale: Scale
    cell_l1: str | None
    centroid: tuple[float, float] | None
    postcode_count: int


class GridStress(BaseModel):
    grid: str
    hz: float | None
    measured_at: datetime | None
    state: Literal["NORMAL", "STRESSED", "EMERGENCY", "SPLIT_SUSPECTED", "UNKNOWN"]
    seconds_to_next_rung: float | None
    label: Label


class Cell(BaseModel):
    cell_id: str
    level: int = Field(ge=1, le=3)
    bounds: list[tuple[float, float]]
    patients: int | Literal["suppressed"]
    outage_scale: Scale | None
    risk_tomorrow: float | None


class AreaRisk(BaseModel):
    district: str
    p_ge_k: float
    expected: float
    label: Label


class RemainingHours(BaseModel):
    q50: float
    q75: float
    q90: float


class TriageItem(BaseModel):
    rank: int
    patient_ref: str
    outage_id: int
    scale: Scale
    device: str
    reserve_left_h: float
    remaining_h: RemainingHours
    q_used: Literal["q50", "q75", "q90"]
    harm: float
    escalate: bool
    why: list[str]
    decision_id: str | None


class ModelInfo(BaseModel):
    id: str
    sha256: str
    label: str


class Triage(BaseModel):
    tick_at: datetime
    model: ModelInfo
    items: list[TriageItem]
    next_cursor: int | None


class Approval(BaseModel):
    approve: bool
    note: str = Field(default="", max_length=500)


class DecisionState(BaseModel):
    decision_id: str
    state: Literal["auto_done", "awaiting_approval", "approved", "rejected", "exported", "expired"]
    audit_seq: int | None


class AgentDecision(BaseModel):
    id: str
    tool: str
    state: str
    created_at: datetime
    args_summary: str
    rationale: list[str]


class HorizonGrade(BaseModel):
    h: int
    model_id: str
    source: str
    brier: float | None
    n: int
    n_censored: int
    bound: tuple[float, float] | None


class Grades(BaseModel):
    by_horizon: list[HorizonGrade]
    trend: list[dict[str, float | str]]


class Login(BaseModel):
    login: str = Field(min_length=1, max_length=64)
    passphrase: str = Field(min_length=1, max_length=256)


class LoginResult(BaseModel):
    role: Literal["operator", "household"]


class Reserve(BaseModel):
    device: str
    ends_at: datetime | None
    hours_left: float | None


class VoltagePoint(BaseModel):
    t: datetime
    pu: float


class GridContext(BaseModel):
    hz: float | None
    note: str


class RiskLayer(BaseModel):
    layer: Literal["home", "area", "grid"]
    value: str | None
    horizon: str
    source: str
    updated: datetime | None


class Risk(BaseModel):
    level: Literal["low", "elevated", "high", "unknown"]
    reason: str
    layers: list[RiskLayer]


class MyHome(BaseModel):
    household: str
    label: Label
    power: Literal["on", "off", "unknown"]
    since: datetime | None
    reserve: Reserve
    voltage: list[VoltagePoint]
    bands: dict[str, float]
    next_action: str
    grid_context: GridContext
    risk: Risk


class CheckpointStatus(BaseModel):
    seq: int
    sig_ok: bool | None
    head_matches: bool


class AuditVerify(BaseModel):
    ok: bool
    rows: int
    first_bad_seq: int | None
    reason: str | None
    last_checkpoint: CheckpointStatus | None
    took_ms: int
