"""The household's own view: power state, its own reserve clock and the next thing to do. Never an ETA.

Patients get actions and their own reserve clock instead of a restoration time (PRD §4): an ETA invites false
reassurance. Matching to live faults uses the postcode blind index, so the register is never decrypted here.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

from .crypto import blind_index
from .db import Db

BROWNOUT_PU = 0.9

ACTIONS = {
    "o2_concentrator": "Switch to your oxygen cylinder now. Reply 2 if you need help.",
    "ventilator": "Your ventilator is running on its battery. Reply 2 if you need help.",
    "o2_cylinder": "Check your cylinder gauge and reply 2 if it's below a quarter.",
}
DEFAULT_ACTION = "Reply 2 if you need help."


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
    freq = await db.rows("SELECT hz FROM v_freq_latest WHERE grid = 'gb'")
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
    }
