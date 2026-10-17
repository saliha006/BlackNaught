"""Parse each DNO feed into one normalised outage shape. Field names verified against live responses."""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .. import timeparse
from ..cells import cell_id
from ..geocode import normalise

UKPN_URL = "https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/ukpn-live-faults/records"
NPG_URL = "https://northernpowergrid.opendatasoft.com/api/explore/v2.1/catalog/datasets/live-power-cuts-data/records"
SSEN_URL = "https://ssen-powertrack-api.opcld.com/gridiview/reporter/info/livefaults"
ELEXON_URL = "https://data.elexon.co.uk/bmrs/api/v1/system/frequency"
UKPN_RESTORED_STATUS = 5
EARLIEST_PLAUSIBLE_YEAR = 2000


@dataclass
class Outage:
    source: str
    source_ref: str
    status: str
    started_at: datetime
    restored_at: datetime | None = None
    restored_explicit: bool = False
    customers: int | None = None
    priority_customers: int | None = None
    postcodes: list[str] = field(default_factory=list)
    lat: float | None = None
    lon: float | None = None
    feeder: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def cell_l1(self) -> str | None:
        return None if self.lat is None or self.lon is None else cell_id(self.lat, self.lon)

    @property
    def content_hash(self) -> bytes:
        """Changes when anything grading or triage depends on changes."""
        key = [self.status, self.restored_at, self.customers, self.priority_customers, sorted(self.postcodes)]
        return hashlib.sha256(json.dumps(key, default=str).encode()).digest()


def _plausible(at: datetime) -> datetime:
    """UKPN's 'Multiple' umbrella records carry .NET's DateTime.MinValue (0001-01-01) as their start."""
    if at.year < EARLIEST_PLAUSIBLE_YEAR:
        raise ValueError(f"placeholder timestamp {at.isoformat()}")
    return at


def _postcodes(values: list[str]) -> list[str]:
    return sorted({p for p in (normalise(v) for v in values) if p})


def parse_ukpn(records: list[dict[str, Any]]) -> list[Outage]:
    out = []
    for r in records:
        restored = r["statusid"] == UKPN_RESTORED_STATUS or r["powercuttype"] == "Restored"
        status = "restored" if restored else "planned" if r["powercuttype"] == "Planned" else "active"
        point = r.get("geopoint") or {}
        out.append(Outage(
            source="ukpn",
            source_ref=r["incidentreference"],
            status=status,
            started_at=_plausible(timeparse.uk_local(r["creationdatetime"])),
            restored_at=timeparse.uk_local(r["restoreddatetime"]) if r.get("restoreddatetime") else None,
            restored_explicit=restored and bool(r.get("restoreddatetime")),
            customers=r.get("nocustomeraffected"),
            postcodes=_postcodes((r.get("fullpostcodedata") or "").split(";")),
            lat=point.get("lat"),
            lon=point.get("lon"),
            raw=r,
        ))
    return out


def parse_npg(records: list[dict[str, Any]]) -> list[Outage]:
    """NPg sends one row per affected postcode area, so rows are merged by `reference`.

    The feed has no restore timestamp: an incident leaving the feed becomes 'vanished', never 'restored'.
    """
    merged: dict[str, Outage] = {}
    for r in records:
        planned = "planned" in (r.get("natureofoutage") or "").lower()
        current = merged.get(r["reference"])
        if current is None:
            current = merged[r["reference"]] = Outage(
                source="npg",
                source_ref=r["reference"],
                status="planned" if planned else "active",
                started_at=timeparse.uk_wall_clock(r["loggedtime"]),
                customers=0,
                lat=r.get("lat"),
                lon=r.get("lng"),
                feeder={"type": r.get("type")},
                raw={"rows": []},
            )
        # about half the rows carry only a predicted count until the DNO confirms customers off supply
        current.customers += r.get("totalconfirmedpowercut") or r.get("totalpredictedpowercut") or 0
        current.postcodes = _postcodes(current.postcodes + list(r.get("postcode") or []))
        current.started_at = min(current.started_at, timeparse.uk_wall_clock(r["loggedtime"]))
        current.raw["rows"].append(r)
    return list(merged.values())


def parse_ssen(document: dict[str, Any]) -> list[Outage]:
    """SSEN marks `resolved` but gives no restore time; `updated` is an approximation."""
    out = []
    for r in document.get("Faults", []):
        resolved = bool(r.get("resolved"))
        out.append(Outage(
            source="ssen",
            source_ref=r["reference"],
            status="restored" if resolved else "active",
            started_at=timeparse.iso(r["loggedAt"]),
            restored_at=timeparse.iso(r["updated"]) if resolved else None,
            restored_explicit=False,
            customers=r.get("affectedCustomerCount"),
            priority_customers=r.get("priorityCustomerCount"),
            postcodes=_postcodes(r.get("affectedAreas") or []),
            lat=r.get("latitude"),
            lon=r.get("longitude"),
            feeder={k: r.get(k) for k in ("primaryNrn", "hvFeederNrn", "lvFeederNrn", "txNrn", "type")},
            raw=r,
        ))
    return out


def parse_elexon(document: dict[str, Any]) -> list[tuple[datetime, float]]:
    return [(timeparse.iso(d["measurementTime"]), float(d["frequency"])) for d in document.get("data", [])]
