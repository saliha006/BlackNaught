"""NNPA shadow scoring (Ahmed, brief task 13): Nate's Keras hazard model (M2) on the Telum NNPA, beside the live KM.

The live duration model stays Nate's KM curve (it beat M2 on UKPN), so this never touches triage. Every minute it
scores one batch, every active outage plus every at-risk patient × outage pair triage ranked last, with a single
graph-mode model.predict that zDNN sends to the NNPA. Outage-level predictions go into `prediction` through the live
scorer's own logging under their own model_id, so the grader scores M2 next to KM on the same outages. The model
loads only if the signer confirms its release signature and the file still has the signed SHA-256.

Runs as its own process, `python -m app.nnpa` (the `nnpa` service in infra/nnpa.yml), as role bn_agent.
    python -m app.nnpa --dry-run             # score one batch, print the summary, write nothing
    python -m app.nnpa --sign MODEL METRICS  # sign a release (scripts/sign-model.sh runs this)
"""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import numpy as np

from . import audit
from .config import read_secret, settings
from .db import Db
from .harm import assess
from .triage import Scorer

log = logging.getLogger("nnpa")

MODEL_ID = "m2-hazard-nnpa-shadow"
TICK_S = 60
MAX_REMAINING_H = 720.0  # the KM stand-in's quantile ceiling
QUANTILES = (0.5, 0.75, 0.9)
GRID_H = np.arange(0.0, MAX_REMAINING_H + 0.05, 0.05)  # 3-minute steps for the quantile search
MIN_SURVIVAL = 1e-9

# the same outages Scorer._at_risk ranks, and the pairs it ranked on its last tick
OUTAGES = ("SELECT outage_id, started_at, customers, feeder FROM outage"
           " WHERE status = 'active' AND cardinality(postcodes) > 0")
PAIRS = """
SELECT t.outage_id, t.escalate, (t.why->>'reserve_left_h')::float8 AS reserve_left_h, p.severity, p.other_backup
FROM triage_snapshot t JOIN patient p USING (patient_id)
WHERE t.tick_at = (SELECT max(tick_at) FROM triage_snapshot)
"""


def survival_at(tail: np.ndarray, t: np.ndarray) -> np.ndarray:
    """S(t) per row from S at whole hours 0..24: linear in between, and past 24 h the last hourly hazard persists
    (the same tail rule as harm.expected_excess)."""
    t = np.broadcast_to(t, (tail.shape[0], t.shape[-1]))
    last, prev = tail[:, 24:25], tail[:, 23:24]
    keep = np.divide(last, prev, out=np.zeros_like(last), where=prev > 0)
    inside = np.clip(t, 0.0, 24.0)
    lo = np.minimum(np.floor(inside).astype(int), 23)
    s_lo, s_hi = np.take_along_axis(tail, lo, axis=1), np.take_along_axis(tail, lo + 1, axis=1)
    within = s_lo + (s_hi - s_lo) * (inside - lo)
    return np.where(t <= 24.0, within, last * keep ** np.maximum(t - 24.0, 0.0))


def predictions(probs: np.ndarray, elapsed_h: np.ndarray) -> list[dict[str, Any]]:
    """The model's classes (power back in hour k; the last one is 24 h or more) → contracts/model.md's predict() shape,
    conditional on each outage having lasted elapsed_h already."""
    tail = np.cumsum(probs[:, ::-1], axis=1)[:, ::-1]  # S(k) = P(still off at hour k), k = 0..24
    e = elapsed_h[:, None]
    now = np.maximum(survival_at(tail, e), MIN_SURVIVAL)
    surv = np.minimum.accumulate(np.clip(survival_at(tail, e + np.arange(1, 25)) / now, 0.0, 1.0), axis=1)
    grid = survival_at(tail, e + GRID_H) / now
    out = []
    for i in range(len(probs)):
        quantiles = {}
        for q in QUANTILES:
            reached = grid[i] <= 1 - q
            remaining = float(GRID_H[np.argmax(reached)]) if reached.any() else MAX_REMAINING_H
            quantiles[f"q{int(q * 100)}"] = round(remaining, 2)
        out.append({"quantiles": quantiles, "surv": [round(float(s), 6) for s in surv[i]]})
    return out


def manifest(model: Path, customers_median: float) -> bytes:
    """What a model release signs: the file's SHA-256 and the one number the model needs beside its weights."""
    return audit.canonical({"file": model.name, "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
                            "customers_median": customers_median}).encode()


def release_path(model: Path) -> Path:
    return model.with_name(model.name + ".sig.json")


async def verified(signer: audit.HttpSigner, model: Path) -> dict[str, Any] | None:
    """The release record if the signer confirms its signature over this exact file, else None (and why, logged)."""
    path = release_path(model)
    if not path.exists():
        log.error("refusing %s: it has no release signature (%s)", model.name, path.name)
        return None
    release = json.loads(path.read_text())
    actual = hashlib.sha256(model.read_bytes()).hexdigest()
    if actual != release["sha256"]:
        log.error("refusing %s: its SHA-256 is %s, not the signed %s", model.name, actual, release["sha256"])
        return None
    try:
        ok = await signer.verify(manifest(model, release["customers_median"]), release["sig_b64"])
    except httpx.HTTPError as exc:
        # no check, no load: an unverified model must not score anything
        log.error("refusing %s: the signer couldn't check it (%s)", model.name, exc)
        return None
    if not ok:
        log.error("refusing %s: the signer rejects its release signature", model.name)
        return None
    return release


class Shadow:
    def __init__(self, db: Db, predict: Callable[[np.ndarray], np.ndarray],
                 features: Callable[[list[dict[str, Any]]], np.ndarray], sha256: str):
        self.db = db
        self.predict = predict
        self.features = features
        # the attributes Scorer._log_predictions reads, so M2's rows are logged exactly like KM's
        self.model = SimpleNamespace(model_id=MODEL_ID, sha256=sha256)
        self.last_logged: dict[int, datetime] = {}

    async def tick(self, now: datetime, dry_run: bool = False) -> dict[str, Any]:
        outages = await self.db.rows(OUTAGES)
        if not outages:
            return {"rows": 0}
        by_id = {o["outage_id"]: o for o in outages}
        pairs = [p for p in await self.db.rows(PAIRS) if p["outage_id"] in by_id]
        rows = outages + [by_id[p["outage_id"]] for p in pairs]
        elapsed = np.array([max(0.0, (now - r["started_at"]).total_seconds() / 3600) for r in rows])
        start = time.perf_counter()
        probs = self.predict(self.features(rows))
        predict_ms = (time.perf_counter() - start) * 1000
        scored = predictions(np.asarray(probs, dtype=np.float64), elapsed)
        per_outage = {o["outage_id"]: scored[i] for i, o in enumerate(outages)}
        m2_escalates = sum(assess(s["quantiles"], s["surv"], p["reserve_left_h"], p["severity"],
                                  p["other_backup"]).escalate for p, s in zip(pairs, scored[len(outages):]))
        summary = {"rows": len(rows), "outages": len(outages), "pairs": len(pairs), "predict_ms": round(predict_ms, 1),
                   "escalate_m2": m2_escalates, "escalate_km": sum(p["escalate"] for p in pairs)}
        if not dry_run:
            await Scorer._log_predictions(self, now, {i: float(e) for i, e in zip(by_id, elapsed)}, per_outage)
        log.info("shadow batch %s", summary)
        return summary

    async def run(self) -> None:
        while True:
            try:
                await self.tick(datetime.now(UTC))
            except Exception:
                # one bad batch must not stop the shadow; it never feeds triage, so nothing waits on it
                log.exception("nnpa shadow tick failed")
            await asyncio.sleep(TICK_S)


def keras_predict(model_path: Path) -> Callable[[np.ndarray], np.ndarray]:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import keras  # only this process loads TensorFlow, and only after the signature checked out

    model = keras.saving.load_model(str(model_path), compile=False)
    return lambda x: model.predict(x, batch_size=max(len(x), 1), verbose=0)


def m2_features(customers_median: float) -> Callable[[list[dict[str, Any]]], np.ndarray]:
    """Nate's own feature mapping (contracts/model.md, option A1), so the shadow scores what M2 was trained on."""
    import pandas as pd
    from ml.m2 import features
    from ml.m2_serve import voltage_of

    def build(rows: list[dict[str, Any]]) -> np.ndarray:
        table = pd.DataFrame({"start": [pd.Timestamp(r["started_at"]) for r in rows],
                              "customers": [r["customers"] for r in rows],
                              "voltage": [voltage_of(r["feeder"]) for r in rows]})
        return features(table, customers_median).to_numpy("float32")

    return build


async def sign(model: Path, metrics: Path) -> dict[str, Any]:
    customers_median = float(json.loads(metrics.read_text())["customers_median"])
    async with httpx.AsyncClient(timeout=30) as client:
        signer = audit.HttpSigner(client, settings().signer_url, read_secret("signer_token_agent"))
        signed = await signer.sign(manifest(model, customers_median), "model_release")
    return {"file": model.name, "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
            "customers_median": customers_median, "alg": signed["alg"], "key_id": signed["key_id"],
            "sig_b64": signed["sig_b64"]}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="score one batch, print the summary, write nothing")
    parser.add_argument("--sign", nargs=2, metavar=("MODEL", "METRICS"), help="sign a model release, print it")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    if args.sign:
        print(json.dumps(await sign(Path(args.sign[0]), Path(args.sign[1]))))
        return
    model = Path(os.environ["BN_NNPA_MODEL"])
    async with httpx.AsyncClient(timeout=10) as client:
        release = await verified(audit.HttpSigner(client, settings().signer_url, ""), model)  # /verify needs no token
    if release is None:
        if args.dry_run:
            raise SystemExit(1)
        # stay up and say why instead of crash-looping under restart: unless-stopped
        await asyncio.Event().wait()
    shadow = Shadow(Db("bn_agent"), keras_predict(model), m2_features(release["customers_median"]), release["sha256"])
    log.info("loaded %s (sha256 %s, signed by key %s)", model.name, release["sha256"][:12], release["key_id"])
    if args.dry_run:
        print(json.dumps(await shadow.tick(datetime.now(UTC), dry_run=True)))
        return
    await shadow.run()


if __name__ == "__main__":
    asyncio.run(main())
