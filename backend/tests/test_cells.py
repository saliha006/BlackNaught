import random
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app import cellpub, suppression
from app.cells import cell_id, parent
from app.ingest import feeds, store
from app.main import app
from app.seed import keys, patient_row

NOW = datetime(2026, 10, 17, 23, 0, tzinfo=UTC)


def random_tree(rng):
    """L1 counts spread over a few L2/L3 parents, biased towards the small numbers that need hiding."""
    l1 = {}
    for _ in range(rng.randint(1, 40)):
        cell = f"L1:{rng.randint(5100, 5112)}:{rng.randint(-10, 2)}"
        l1[cell] = rng.choice([0, 1, 2, 3, 5, 8, 10, 11, 12, 15, 25, 40])
    return l1


def recoverable_children(l1, published):
    """Children an attacker could pin to 1–10 by subtracting published siblings from a published parent."""
    counts = suppression.counts_by_level(l1)
    bad = []
    for child_prefix in ("L1:", "L2:"):
        families = {}
        for c in counts:
            if c.startswith(child_prefix):
                families.setdefault(parent(c), []).append(c)
        for up, kids in families.items():
            if published[up] is None:
                continue
            hidden = [k for k in kids if published[k] is None]
            remainder = counts[up] - sum(counts[k] for k in kids if published[k] is not None)
            if len(hidden) == 1 and 0 < remainder < suppression.K:
                bad.append(hidden[0])
            if hidden and 0 < remainder < suppression.K:
                bad.append(up)
    return bad


def test_property_no_small_count_is_ever_published_or_derivable():
    rng = random.Random(2026)
    for _ in range(500):
        l1 = random_tree(rng)
        published = suppression.publish(l1)
        assert all(v is None or v == 0 or v >= suppression.K for v in published.values())
        assert recoverable_children(l1, published) == []


def test_banding_and_zero():
    published = suppression.publish({"L1:0:0": 0, "L1:0:1": 23, "L1:0:2": 11})
    assert published["L1:0:0"] == 0 and published["L1:0:1"] == 25 and published["L1:0:2"] == 11


def test_lone_small_cell_drags_a_sibling_into_hiding():
    published = suppression.publish({"L1:0:0": 3, "L1:0:1": 40, "L1:0:2": 12})
    assert published["L1:0:0"] is None and published["L1:0:2"] is None  # 12 hidden to protect the 3
    assert published["L1:0:1"] == 40


def test_parent_hidden_when_no_sibling_can_cover():
    published = suppression.publish({"L1:0:0": 4})
    assert published["L1:0:0"] is None and published["L2:0:0"] is None


@pytest.mark.anyio
async def test_publish_and_serve(db_factory, superuser):
    superuser.run("TRUNCATE outage, outage_version, patient, cell_snapshot RESTART IDENTITY CASCADE")
    dek, bidx = keys()
    rng = random.Random(4)
    dense = (51.5450, -0.0890)
    sparse = (51.5650, -0.0890)
    for lat, lon, n in ((*dense, 15), (*sparse, 2)):
        for _ in range(n):
            superuser.run("INSERT INTO patient (patient_id, household_id, cell_l1, postcode_bidx, contact_ct, device,"
                          " reserve_h, other_backup, severity) VALUES (CAST(:id AS uuid), CAST(:household AS uuid),"
                          " :cell, :bidx, :contact, :device, :reserve, :backup, :severity)",
                          **patient_row(rng, "N1 3LD", lat, lon, dek, bidx))
    await store.sync(db_factory("bn_ingest"), "ukpn", [feeds.Outage(
        "ukpn", "A", "active", NOW - timedelta(hours=1), customers=40, lat=dense[0], lon=dense[1])], NOW)
    agent = db_factory("bn_agent")
    assert await cellpub.publish_once(agent, NOW) > 0
    await cellpub.publish_once(agent, NOW + timedelta(hours=3))  # old snapshot pruned
    assert superuser.run("SELECT count(DISTINCT published_at) FROM cell_snapshot")[0][0] == 1
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            l1 = {x["cell_id"]: x for x in (await c.get("/api/cells?level=1")).json()}
            l3 = (await c.get("/api/cells?level=3")).json()
    assert l1[cell_id(*dense)]["patients"] == 15 and l1[cell_id(*dense)]["outage_scale"] == "street"
    assert l1[cell_id(*sparse)]["patients"] == "suppressed"
    assert len(l1[cell_id(*dense)]["bounds"]) == 5
    assert all(x["level"] == 3 for x in l3)
