import base64
import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import numpy as np
import pytest

from app import audit, survival
from app.ingest import feeds, store
from app.nnpa import MODEL_ID, Shadow, manifest, predictions, release_path, verified
from app.seed import INSERT, keys, patient_row
from app.triage import Scorer

NOW = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)
KM = survival.load(Path("/srv/models/km_enwl.json"))


def one_hot(k: int) -> np.ndarray:
    probs = np.zeros((1, 25))
    probs[0, k] = 1.0
    return probs


# --- the hazard classes as the contract's survival ----------------------------------------------

def test_power_back_in_hour_two_reads_as_still_off_at_two_hours_and_back_by_three():
    [pred] = predictions(one_hot(2), np.array([0.0]))
    assert pred["surv"][:3] == [1.0, 1.0, 0.0]
    assert pred["quantiles"]["q50"] == pytest.approx(2.5, abs=0.06)
    assert pred["quantiles"]["q90"] == pytest.approx(2.9, abs=0.06)


def test_survival_is_conditional_on_the_time_already_off_and_never_rises():
    probs = np.random.default_rng(1).dirichlet(np.ones(25), size=5)
    for pred in predictions(probs, np.array([0.0, 1.5, 6.0, 23.0, 30.0])):
        s, q = pred["surv"], pred["quantiles"]
        assert all(0 <= v <= 1 for v in s) and all(a >= b for a, b in zip(s, s[1:]))
        assert q["q50"] <= q["q75"] <= q["q90"]
    [halfway] = predictions(one_hot(2), np.array([2.5]))  # half the outages of this kind are back by now
    assert halfway["surv"][0] == 0.0


def test_past_a_day_the_last_hourly_hazard_carries_on():
    probs = np.zeros((1, 25))
    probs[0, 23] = probs[0, 24] = 0.5  # S(23) = 1, S(24) = 0.5, so each later hour keeps half
    [pred] = predictions(probs, np.array([24.0]))
    assert pred["surv"][:2] == [pytest.approx(0.5), pytest.approx(0.25)]


# --- the release signature ---------------------------------------------------------------------

def signer(answer: bool | Exception, seen: list | None = None) -> audit.HttpSigner:
    def handler(request: httpx.Request) -> httpx.Response:
        if isinstance(answer, Exception):
            raise answer
        assert request.url.path == "/verify" and "authorization" not in request.headers
        if seen is not None:
            seen.append(base64.b64decode(json.loads(request.content)["payload_b64"]))
        return httpx.Response(200, json={"ok": answer})

    return audit.HttpSigner(httpx.AsyncClient(transport=httpx.MockTransport(handler)), "http://signer:8100", "")


@pytest.fixture
def model(tmp_path) -> Path:
    path = tmp_path / "m2_hazard.keras"
    path.write_bytes(b"the model's weights")
    release_path(path).write_text(json.dumps({
        "file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "customers_median": 10.0,
        "alg": "ML-DSA-65", "key_id": "test", "sig_b64": base64.b64encode(b"signature").decode()}))
    return path


@pytest.mark.anyio
async def test_a_model_loads_only_once_the_signer_confirms_its_exact_hash(model):
    seen = []
    release = await verified(signer(True, seen), model)
    assert release["customers_median"] == 10.0
    assert seen == [manifest(model, 10.0)] and hashlib.sha256(model.read_bytes()).hexdigest().encode() in seen[0]


@pytest.mark.anyio
async def test_a_wrong_signature_or_an_unreachable_signer_refuses_the_model(model):
    assert await verified(signer(False), model) is None
    assert await verified(signer(httpx.ConnectError("signer unreachable")), model) is None


@pytest.mark.anyio
async def test_a_changed_or_unsigned_file_is_refused_even_if_the_signer_would_say_yes(model):
    model.write_bytes(b"tampered weights")
    assert await verified(signer(True), model) is None
    release_path(model).unlink()
    assert await verified(signer(True), model) is None


# --- one shadow batch against the database -----------------------------------------------------

@pytest.fixture
async def ranked(db_factory, superuser):
    superuser.run("TRUNCATE outage, outage_version, patient, prediction, grade, triage_snapshot RESTART IDENTITY CASCADE")
    fault = feeds.Outage("ukpn", "INCD-N", "active", NOW - timedelta(hours=1), postcodes=["N1 3LD"], lat=51.54, lon=-0.09)
    await store.sync(db_factory("bn_ingest"), "ukpn", [fault], NOW)
    dek, bidx = keys()
    rng = random.Random(3)
    for device, reserve, backup in (("o2_concentrator", 0.5, False), ("ventilator", 12.0, False)):
        superuser.run(INSERT, **patient_row(rng, "N1 3LD", 51.54, -0.09, dek, bidx, device, reserve, backup))
    db = db_factory("bn_agent")
    assert await Scorer(db, KM, bidx).tick(NOW) == 2
    return db


def shadow(db, batches: list) -> Shadow:
    def predict(x: np.ndarray) -> np.ndarray:
        batches.append(x.shape)
        return np.tile(one_hot(2), (len(x), 1))  # every outage back in its third hour

    return Shadow(db, predict, lambda rows: np.zeros((len(rows), 9), dtype=np.float32), "abc123")


@pytest.mark.anyio
async def test_one_batch_scores_every_outage_and_pair_and_never_touches_triage(ranked, superuser):
    batches = []
    snapshot = superuser.run("SELECT count(*) FROM triage_snapshot")[0][0]
    summary = await shadow(ranked, batches).tick(NOW)
    assert batches == [(3, 9)]  # one predict: the outage, then its two at-risk patients
    assert (summary["outages"], summary["pairs"], summary["escalate_m2"]) == (1, 2, 1)
    logged = superuser.run("SELECT horizon_h, p_still_off, model_sha256 FROM prediction WHERE model_id = :m"
                           " ORDER BY horizon_h", m=MODEL_ID)
    assert logged == [[2, 0.0, "abc123"], [4, 0.0, "abc123"]]
    assert superuser.run("SELECT count(*) FROM triage_snapshot")[0][0] == snapshot


@pytest.mark.anyio
async def test_a_dry_run_scores_but_writes_nothing(ranked, superuser):
    summary = await shadow(ranked, []).tick(NOW, dry_run=True)
    assert summary["rows"] == 3
    assert superuser.run("SELECT count(*) FROM prediction WHERE model_id = :m", m=MODEL_ID)[0][0] == 0
