"""CAP 1.2 public alert for an area outage with vulnerable people inside (PRD F15).

The agent drafts it, a human approves it, and the authority's own channel (cell broadcast, sirens, apps) sends it;
we never broadcast. Built once on approval and never regenerated. status is always Exercise: the patients behind
it are synthetic. The area is the convex hull of the fault's postcodes; no patient location or count goes in.
"""
from datetime import UTC, datetime, timedelta
from xml.etree import ElementTree as ET

from . import timeparse

NS = "urn:oasis:names:tc:emergency:cap:1.2"
EXPIRES_AFTER = timedelta(hours=6)
CIRCLE_RADIUS_KM = 1.0
DEFAULT_HEADLINE = "Power cut: check on neighbours who rely on medical equipment"
DEFAULT_INSTRUCTION = ("If someone near you relies on oxygen or a ventilator, check they have switched to their "
                       "backup. Call 999 if anyone is struggling to breathe.")


def convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Andrew's monotone chain; returns the hull counter-clockwise without repeating the first point."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _area(area: ET.Element, points: list[tuple[float, float]]) -> None:
    hull = convex_hull(points)
    if len(hull) >= 3:
        ring = hull + [hull[0]]  # CAP polygons must be closed: first pair repeated last
        ET.SubElement(area, f"{{{NS}}}polygon").text = " ".join(f"{lat:.5f},{lon:.5f}" for lat, lon in ring)
    else:
        lat = sum(p[0] for p in points) / len(points)
        lon = sum(p[1] for p in points) / len(points)
        ET.SubElement(area, f"{{{NS}}}circle").text = f"{lat:.5f},{lon:.5f} {CIRCLE_RADIUS_KM}"


def build(decision_id: str, sender: str, approver: str, points: list[tuple[float, float]], area_desc: str,
          severe: bool, confirmed: bool, headline: str | None = None, description: str | None = None,
          instruction: str | None = None, sent: datetime | None = None) -> str:
    if not points:
        raise ValueError("a CAP alert needs at least one location")
    sent = sent or datetime.now(UTC)
    ET.register_namespace("", NS)
    alert = ET.Element(f"{{{NS}}}alert")

    def add(parent: ET.Element, tag: str, text: str) -> ET.Element:
        el = ET.SubElement(parent, f"{{{NS}}}{tag}")
        el.text = text
        return el

    add(alert, "identifier", f"blacknaught-{decision_id}")
    add(alert, "sender", sender)
    add(alert, "sent", timeparse.cap(sent))
    add(alert, "status", "Exercise")
    add(alert, "msgType", "Alert")
    add(alert, "scope", "Public")
    add(alert, "note", f"Drafted by the Blacknaught agent, approved by {approver}. Patients are SIMULATED.")
    info = ET.SubElement(alert, f"{{{NS}}}info")
    add(info, "language", "en-GB")
    add(info, "category", "Infra")
    add(info, "category", "Health")
    add(info, "event", "Power cut affecting electricity-dependent residents")
    add(info, "urgency", "Expected")
    add(info, "severity", "Severe" if severe else "Moderate")
    add(info, "certainty", "Observed" if confirmed else "Likely")
    add(info, "expires", timeparse.cap(sent + EXPIRES_AFTER))
    add(info, "senderName", "Blacknaught decision service (exercise)")
    add(info, "headline", (headline or DEFAULT_HEADLINE)[:140])
    add(info, "description", description or f"Power is off in {area_desc}.")
    add(info, "instruction", instruction or DEFAULT_INSTRUCTION)
    area = ET.SubElement(info, f"{{{NS}}}area")
    add(area, "areaDesc", area_desc)
    _area(area, points)
    return ET.tostring(alert, encoding="unicode", xml_declaration=True)


def area_desc(postcodes: list[str]) -> str:
    """Outward codes only ('N1 3LD' → 'N1'): enough to recognise the area, too coarse to point at a home."""
    return ", ".join(sorted({p.split()[0] for p in postcodes})) or "the affected area"
