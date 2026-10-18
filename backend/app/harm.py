"""Expected harm-hours and the escalation rule (PRD §5, §6 F5).

harm = severity × P(no other backup) × E[max(0, T_remaining − r)], where r is the reserve the patient has left.
Caution follows clinical criticality, never the region (PRD §5): no backup — no second power source and the
reserve nearly empty — → q90; reserve > 2 × q50 → q50; otherwise q75.
"""
import math
from dataclasses import dataclass

TAIL_CAP_H = 72.0             # keeps the expected excess finite for near-zero hazards
OTHER_BACKUP_FACTOR = 0.2     # P(no other backup) when the household has a second source
NEARLY_EMPTY_H = 2.0          # PRD §5 "cylinder nearly empty"


def expected_excess(surv: list[float], reserve_h: float) -> float:
    """∫_r^∞ S(u) du over hourly conditional survival S(1..24), with a geometric tail after 24 h."""
    points = [1.0] + list(surv)
    total = 0.0
    for h in range(len(points) - 1):
        start, end = max(h, reserve_h), h + 1
        if end <= start:
            continue
        s_start = points[h] + (points[h + 1] - points[h]) * (start - h)
        total += (s_start + points[h + 1]) / 2 * (end - start)
    last, prev = points[-1], points[-2]
    if last > 0 and prev > 0:
        # beyond 24 h assume the last hourly hazard persists: ∫ S·(1−h)^t dt = S / −ln(1−h)
        keep = last / prev
        tail = TAIL_CAP_H if keep >= 1 else last / -math.log(keep)
        if reserve_h > len(surv):
            tail *= keep ** (reserve_h - len(surv))
        total += min(tail, TAIL_CAP_H)
    return min(total, TAIL_CAP_H)


@dataclass(frozen=True)
class Assessment:
    q_used: str
    q_hours: float
    harm: float
    escalate: bool
    why: list[str]


def assess(quantiles: dict[str, float], surv: list[float], reserve_left_h: float, severity: int,
           other_backup: bool, sms_power_back: bool = False) -> Assessment:
    if not other_backup and reserve_left_h < NEARLY_EMPTY_H:
        q_used, why = "q90", [f"no backup, reserve {reserve_left_h:.1f} h → q90"]
    elif reserve_left_h > 2 * quantiles["q50"]:
        q_used, why = "q50", [f"reserve {reserve_left_h:.1f} h > 2 × q50 → q50"]
    else:
        q_used, why = "q75", [f"reserve {reserve_left_h:.1f} h not ample → q75"]
    q_hours = quantiles[q_used]
    harm = severity * (OTHER_BACKUP_FACTOR if other_backup else 1.0) * expected_excess(surv, reserve_left_h)
    escalate = q_hours > reserve_left_h
    why.append(f"{q_used} {q_hours:.1f} h {'>' if escalate else '≤'} reserve {reserve_left_h:.1f} h")
    # an SMS "power back" can be spoofed or sent by a child: it never stands a no-backup patient down
    if sms_power_back and not other_backup:
        why.append("SMS says power back; ignored for a no-backup patient")
    elif sms_power_back and escalate:
        escalate = False
        why.append("SMS says power back; backup present → stood down")
    return Assessment(q_used, q_hours, round(harm, 3), escalate, why)
