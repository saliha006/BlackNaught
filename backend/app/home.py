"""The household's own view: power state, its own reserve clock and the next thing to do. Never an ETA.

Patients get actions and their own reserve clock instead of a restoration time (PRD §4): an ETA invites false
reassurance. Matching to live faults uses the postcode blind index, so the register is never decrypted here.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

from . import stress
from .crypto import blind_index
from .db import Db

BROWNOUT_PU = 0.9

ACTIONS = {
    "o2_concentrator": "Switch to your oxygen cylinder now. Reply 2 if you need help.",
    "ventilator": "Your ventilator is running on its battery. Reply 2 if you need help.",
    "o2_cylinder": "Check your cylinder gauge and reply 2 if it's below a quarter.",
}
DEFAULT_ACTION = "Reply 2 if you need help."
# Elexon publishes every 15 s and we poll every 30 s, so anything older means the feed has stopped
GRID_STALE = timedelta(minutes=5)


def area_band(risk: list[dict], district: str | None) -> str | None:
    """'high' for the top third of districts by tomorrow's fault risk; relative, so it holds when M8 replaces the baseline."""
    ranked = sorted(risk, key=lambda r: r["p_ge_k"], reverse=True)
    position = next((i for i, r in enumerate(ranked) if r["district"] == district), None)
    if position is None:
        return None
    return "high" if position < len(ranked) / 3 else "normal"


def headline(home: str | None, area: str | None, grid: str | None) -> tuple[str, str]:
    """Worst signal wins (option C). A missing layer can raise nothing, but it also stops us claiming 'low'."""
    if home == "elevated":
        return "high", "this home's sensor pattern is flagged for the next 30 min"
    if grid == "EMERGENCY":
        return "high", "grid frequency is in the emergency band"
    if area == "high":
        return "elevated", "your area is in the top third for fault risk tomorrow"
    if grid == "STRESSED":
        return "elevated", "grid frequency is outside normal limits"
    if None in (home, area, grid):
        return "unknown", "not every layer has data, so we can't call it low"
    return "low", "no layer is raising a flag"


def risk(grid_state: str | None, grid_at: datetime | None, area: str | None) -> dict[str, Any]:
    # the home-sensor model isn't served yet (Nate), and the area model covers ENWL districts only, which no
    # demo household is in; both stay None ("no data") rather than defaulting to a reassuring value
    home = None
    level, reason = headline(home, area, grid_state)
    return {"level": level, "reason": reason, "layers": [
        {"layer": "home", "value": home, "horizon": "next 30 min", "source": "home-sensor model", "updated": None},
        {"layer": "area", "value": area, "horizon": "tomorrow", "source": "ENWL fault climatology", "updated": None},
        {"layer": "grid", "value": grid_state, "horizon": "now", "source": "Elexon frequency", "updated": grid_at},
    ]}


async def view(db: Db, login: str, bidx_key: bytes, now: datetime | None = None) -> dict[str, Any] | None:
    now = now or datetime.now(UTC)
    patients = await db.rows("SELECT device, reserve_h, other_backup, postcode_bidx FROM me_home_patients(:l)", l=login)
    if not patients:
        return None
    patient = patients[0]
    off_since = None
    for o in await db.rows("SELECT started_at, postcodes FROM v_outage_public WHERE status = 'active'"):
        if any(blind_index(bidx_key, p) == bytes(patient["postcode_bidx"]) for p in o["postcodes"]):
            off_since = o["started_at"] if off_since is None else min(off_since, o["started_at"])
    freq = await db.rows("SELECT hz, measured_at FROM v_freq_latest WHERE grid = 'gb'")
    fresh = bool(freq) and now - freq[0]["measured_at"] <= GRID_STALE
    grid_state = stress.state(float(freq[0]["hz"])) if fresh else None
    reserve_h = float(patient["reserve_h"])
    if off_since is None:
        reserve = {"device": patient["device"], "ends_at": None, "hours_left": reserve_h}
        action = "Power is on. Keep your backup charged."
    else:
        ends_at = off_since + timedelta(hours=reserve_h)
        reserve = {"device": patient["device"], "ends_at": ends_at,
                   "hours_left": round(max(0.0, (ends_at - now).total_seconds() / 3600), 1)}
        action = ACTIONS.get(patient["device"], DEFAULT_ACTION)
    return {
        "household": login,
        "label": "SIMULATED",
        "power": "off" if off_since else "on",
        "since": off_since,
        "reserve": reserve,
        # no sensor stream reaches this household until the simulator (Ahmed, F2) feeds it
        "voltage": [],
        "bands": {"brownout_pu": BROWNOUT_PU},
        "next_action": action,
        "grid_context": {"hz": float(freq[0]["hz"]) if freq else None, "note": "grid health: the same for everyone"},
        "risk": risk(grid_state, freq[0]["measured_at"] if fresh else None, area=None),
    }
