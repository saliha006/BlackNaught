"""Event envelope shared by ingest, simulator and agent (frozen into contracts/events.schema.json)."""
import hashlib
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .schemas import Label

Source = Literal["ukpn", "npg", "ssen", "elexon", "ioda", "sim", "accra_replay", "neso_replay", "agent"]


class _Payload(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Heartbeat(_Payload):
    kind: Literal["heartbeat"] = "heartbeat"
    sensor_id: str
    cell_l1: str
    v_pu: float | None = None


class LastGasp(_Payload):
    kind: Literal["last_gasp"] = "last_gasp"
    sensor_id: str
    cell_l1: str


class DnoFault(_Payload):
    kind: Literal["dno_fault"] = "dno_fault"
    source_ref: str
    status: Literal["active", "restored", "vanished", "planned"]
    postcodes: list[str]


class FreqReading(_Payload):
    kind: Literal["freq_reading"] = "freq_reading"
    grid: str = "gb"
    hz: float


class SmsReply(_Payload):
    kind: Literal["sms_reply"] = "sms_reply"
    patient_ref: str
    code: Literal["1", "2"]


class IodaSignal(_Payload):
    kind: Literal["ioda_signal"] = "ioda_signal"
    region: str
    datasource: str
    value: float


class SheddingStage(_Payload):
    kind: Literal["shedding_stage"] = "shedding_stage"
    grid: str
    stage: int = Field(ge=0, le=16)


class SourceStateChange(_Payload):
    kind: Literal["source_state"] = "source_state"
    source: str
    status: Literal["ok", "stale", "down", "degraded"]


Payload = Annotated[
    Heartbeat | LastGasp | DnoFault | FreqReading | SmsReply | IodaSignal | SheddingStage | SourceStateChange,
    Field(discriminator="kind"),
]


class Event(BaseModel):
    event_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    source: Source
    observed_at: datetime
    received_at: datetime
    label: Label
    payload: Payload


def event_id(*parts: str) -> str:
    """Deterministic id, so re-polls and replays are idempotent."""
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]
