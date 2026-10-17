"""Synthetic register on real fault footprints: python -m app.seed [--per-outage N] [--two-houses OUTAGE_ID]

Patients are fictional (Marist ToU §9 forbids real health data on the VM, and the table CHECK enforces it).
Phone numbers come from Ofcom's 07700 900000–900999 range, reserved for drama, so none can reach a real person.
Backup figures follow PRD §2: cylinders ~8–20 h, modern ventilator batteries ~15 h, older ~6 h, IPS 1–3 h.
"""
import argparse
import random
import uuid
from typing import Any

import pg8000.native

from .cells import cell_id
from .config import read_secret
from .crypto import blind_index, encrypt
from .db import connect

DEVICES: list[tuple[str, float, tuple[float, float], int]] = [
    # device, share, reserve hours range, severity
    ("o2_concentrator", 0.45, (0.0, 3.0), 5),   # no battery: reserve is cylinder or IPS backup
    ("o2_cylinder", 0.25, (8.0, 20.0), 4),
    ("ventilator", 0.15, (6.0, 15.0), 5),
    ("suction", 0.10, (1.0, 4.0), 3),
    ("powered_bed", 0.05, (0.0, 0.0), 2),
]


def keys() -> tuple[bytes, bytes]:
    return bytes.fromhex(read_secret("dek")), bytes.fromhex(read_secret("bidx_key"))


def fake_contact(rng: random.Random) -> str:
    return f"+44 7700 900{rng.randrange(1000):03d}"


def patient_row(rng: random.Random, postcode: str, lat: float, lon: float, dek: bytes, bidx: bytes,
                device: str | None = None, reserve_h: float | None = None,
                other_backup: bool | None = None) -> dict[str, Any]:
    if device is None:
        device, _, span, severity = rng.choices(DEVICES, weights=[d[1] for d in DEVICES])[0]
    else:
        _, _, span, severity = next(d for d in DEVICES if d[0] == device)
    patient_id = uuid.uuid4()
    return {
        "id": str(patient_id),
        "household": str(uuid.uuid4()),
        "cell": cell_id(lat, lon),
        "bidx": blind_index(bidx, postcode),
        "contact": encrypt(dek, fake_contact(rng).encode(), patient_id.bytes),
        "device": device,
        "reserve": round(rng.uniform(*span), 1) if reserve_h is None else reserve_h,
        "backup": rng.random() < 0.2 if other_backup is None else other_backup,
        "severity": severity,
    }


INSERT = """
INSERT INTO bn.patient (patient_id, household_id, cell_l1, postcode_bidx, contact_ct, device, reserve_h,
  other_backup, severity)
VALUES (CAST(:id AS uuid), CAST(:household AS uuid), :cell, :bidx, :contact, :device, :reserve, :backup, :severity)
"""


def footprints(conn: pg8000.native.Connection, limit: int) -> list[tuple[int, str, float, float]]:
    """(outage_id, postcode, lat, lon) for active real faults, using geocoded postcodes."""
    return conn.run(
        "SELECT o.outage_id, g.postcode, g.lat, g.lon FROM bn.outage o"
        " JOIN bn.postcode_geo g ON g.postcode = ANY(o.postcodes) AND g.valid"
        " WHERE o.status = 'active' ORDER BY o.outage_id, g.postcode LIMIT :limit",
        limit=limit,
    )


def seed(conn: pg8000.native.Connection, per_outage: int, two_houses: int | None, rng: random.Random) -> int:
    dek, bidx = keys()
    rows: list[dict[str, Any]] = []
    by_outage: dict[int, list[tuple[str, float, float]]] = {}
    for outage_id, postcode, lat, lon in footprints(conn, 5000):
        by_outage.setdefault(outage_id, []).append((postcode, lat, lon))
    for outage_id, places in by_outage.items():
        for k in range(per_outage):
            postcode, lat, lon = places[k % len(places)]
            rows.append(patient_row(rng, postcode, lat, lon, dek, bidx))
    if two_houses is not None:
        postcode, lat, lon = by_outage[two_houses][0]
        # the demo centrepiece: same fault, a 4 h cylinder that runs out vs a 15 h ventilator battery
        rows.append(patient_row(rng, postcode, lat, lon, dek, bidx, "o2_concentrator", 4.0, False))
        rows.append(patient_row(rng, postcode, lat, lon, dek, bidx, "ventilator", 15.0, False))
    for row in rows:
        conn.run(INSERT, **row)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-outage", type=int, default=15)  # ≥ 15 per demo cell so k≥11 cells aren't all hidden
    parser.add_argument("--two-houses", type=int)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--database")
    args = parser.parse_args()
    conn = connect("bn_migrator", args.database)
    try:
        conn.run("SET ROLE bn_owner")
        print("patients:", seed(conn, args.per_outage, args.two_houses, random.Random(args.seed)))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
