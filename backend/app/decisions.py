"""Decisions the agent makes. Tools that reach people at scale wait for a human; everything is audited.

Ahmed's agent calls create(); the control room approves through POST /api/decisions/{id}/approve.
"""
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from . import audit
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
