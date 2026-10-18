"""Decisions the agent makes. Tools that reach people at scale wait for a human; everything is audited.

Ahmed's agent calls create(); the control room approves through POST /api/decisions/{id}/approve.
"""
import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from . import audit, cap
from .config import settings
from .db import Db

NEEDS_APPROVAL = frozenset({"escalate", "draft_cap_alert", "bulk_sms"})


async def create(db: Db, tool: str, args: dict[str, Any], rationale: list[str]) -> tuple[str, str]:
    """Returns (decision_id, state). Escalations, CAP alerts and bulk SMS start as awaiting_approval."""
    decision_id = str(uuid.uuid4())
    state = "awaiting_approval" if tool in NEEDS_APPROVAL else "auto_done"
    now = datetime.now(UTC)
    await db.run(
        "INSERT INTO decision (decision_id, created_at, tool, args, state, rationale)"
        " VALUES (CAST(:id AS uuid), :at, :tool, CAST(:args AS jsonb), :state, CAST(:why AS jsonb))",
        id=decision_id, at=now, tool=tool, args=json.dumps(args), state=state, why=json.dumps(rationale),
    )
    seq = await audit.append(db, "decision", "agent", decision_id,
                             {"tool": tool, "args": args, "state": state, "rationale": rationale}, now)
    await db.run("UPDATE decision SET audit_seq = :s WHERE decision_id = CAST(:id AS uuid)", s=seq, id=decision_id)
    return decision_id, state


async def approve(db: Db, decision_id: str, approve_it: bool, approver: str, note: str) -> tuple[str | None, int]:
    """Returns (new_state, audit_seq); new_state is None when the decision wasn't awaiting approval."""
    rows = await db.run("SELECT approve_decision(CAST(:id AS uuid), :ok, :who)", id=decision_id, ok=approve_it,
                        who=approver)
    state = rows[0][0] if rows else None
    seq = await audit.append(db, "approval", approver, decision_id,
                             {"approve": approve_it, "note": note, "result": state or "not_awaiting_approval"})
    return state, seq


async def export_cap(db: Db, decision_id: str, approver: str, signer: audit.HttpSigner | None) -> str | None:
    """Build, sign and store the CAP XML for an approved draft_cap_alert. Returns the identifier, or None if the
    decision isn't an approved CAP draft."""
    rows = await db.rows("SELECT tool, state, args FROM v_decisions WHERE decision_id = CAST(:id AS uuid)",
                         id=decision_id)
    if not rows or rows[0]["tool"] != "draft_cap_alert" or rows[0]["state"] != "approved":
        return None
    args = rows[0]["args"]
    outage = (await db.rows("SELECT source, postcodes, lat, lon FROM v_outage_public WHERE outage_id = :o",
                            o=args["outage_id"]))[0]
    geo = await db.rows("SELECT lat, lon FROM v_postcode_geo WHERE postcode = ANY(:p)", p=outage["postcodes"])
    points = [(g["lat"], g["lon"]) for g in geo] or [(outage["lat"], outage["lon"])]
    severity = await db.rows("SELECT severe FROM v_outage_severity WHERE outage_id = :o", o=args["outage_id"])
    xml = cap.build(decision_id, settings().cap_sender, approver, points, cap.area_desc(outage["postcodes"]),
                    severe=bool(severity and severity[0]["severe"]), confirmed=outage["source"] in ("ukpn", "npg", "ssen"),
                    headline=args.get("headline"), description=args.get("description"),
                    instruction=args.get("instruction"))
    sig = (await signer.sign(xml.encode(), "cap_alert"))["sig_b64"] if signer is not None else None
    identifier = f"blacknaught-{decision_id}"
    await db.run("SELECT cap_store(CAST(:id AS uuid), :ident, :xml, :sig)", id=decision_id, ident=identifier,
                 xml=xml, sig=sig)
    await audit.append(db, "cap_export", approver, decision_id,
                       {"identifier": identifier, "signed": sig is not None, "sha256": hashlib.sha256(xml.encode()).hexdigest()})
    return identifier
