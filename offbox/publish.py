"""Publishes the VM's signed audit checkpoints off the box, to the `audit-checkpoints` branch on GitHub (Ahmed).

The audit chain lives in Postgres on the VM, so whoever holds root there could rewrite it. Once a signed head is on
GitHub, a chain rewritten behind it stops matching that head. The VM never holds GitHub credentials, so this runs
somewhere else: every 10 minutes as a GitHub Action (.github/workflows/audit-checkpoints.yml), so it keeps going with
nobody at a laptop. It reads the new signed checkpoints from the public GET /api/audit/checkpoints, rebuilds each
signed payload from its fields, checks the ML-DSA-65 signature here against the pinned contracts/signer_pub.pem, and
commits one JSON line per new checkpoint. Nothing new is published while the server's own chain check fails.

Needs OpenSSL 3.5 (ML-DSA) and a checkout of the audit-checkpoints branch:
    python offbox/publish.py --once --repo <branch checkout>
    python offbox/publish.py          # every 10 minutes, into ../BlackNaught-checkpoints
"""
import argparse
import hashlib
import json
import logging
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "alerting"))
from relay import BASE_URL, PUBLIC_KEY, verify  # noqa: E402  (one signature check for the alerts and the audit)

REPO = ROOT.parent / "BlackNaught-checkpoints"  # the laptop's worktree on the audit-checkpoints branch
LOG = "checkpoints.jsonl"
EVERY_S = 600
BATCH = 100
HEX = frozenset("0123456789abcdef")

log = logging.getLogger("offbox")

Checkpoints = Callable[[int], list[dict]]
Status = Callable[[], dict]


def canonical(obj: dict) -> str:
    # backend/app/audit.py's encoding, so the bytes checked here are the bytes the signer signed
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def payload(seq: int, head: str, at: datetime) -> bytes:
    """What the signer signed for a checkpoint: backend/app/audit.py's checkpoint_payload, byte for byte."""
    return canonical({"seq": seq, "head": head, "at": at.isoformat()}).encode()


def key_id(public_key: Path) -> str:
    # the signer names its key by the first 16 hex of its public PEM's SHA-256 (signer/signer.py); a Windows checkout
    # can turn that PEM's line ends into CRLF, which mustn't change its name
    return hashlib.sha256(public_key.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:16]


def signed_at(row: dict) -> datetime:
    return datetime.fromisoformat(row["at"])


def refusal(row: dict, pinned: str, public_key: Path) -> str | None:
    """Why a checkpoint row can't be published, or None when it can."""
    head = row["head"]
    if len(head) != 64 or not set(head) <= HEX:
        return "its head isn't a SHA-256 in hex"
    if row["alg"] != "ML-DSA-65" or row["key_id"] != pinned:
        return f"it's signed by {row['alg']} key {row['key_id']}, not the pinned {pinned}"
    # the signature is checked over bytes rebuilt from the fields, so a payload that says something else can't pass
    signed = payload(row["seq"], head, signed_at(row))
    if row["payload"].encode() != signed:
        return "its payload doesn't match its seq, head and time"
    if not verify(signed, row["sig_b64"], public_key):
        return "its signature doesn't verify"
    return None


class Publisher:
    def __init__(self, checkpoints: Checkpoints, status: Status, repo: Path = REPO, public_key: Path = PUBLIC_KEY):
        self.checkpoints = checkpoints
        self.status = status
        self.repo = repo
        self.public_key = public_key
        self.pinned = key_id(public_key)

    def committed(self) -> str:
        """The log as last committed. Lines a failed run left uncommitted don't count as published."""
        done = subprocess.run(["git", "-C", str(self.repo), "show", f"HEAD:{LOG}"], capture_output=True, text=True,
                              encoding="utf-8", timeout=60)
        return done.stdout if done.returncode == 0 else ""

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True, timeout=120)

    def publish(self, now: datetime | None = None) -> int:
        """Commits and pushes every new signed checkpoint; returns how many were published."""
        state = self.status()
        if not state["ok"]:
            log.error("the server's chain check fails (%s at seq %s); anchoring nothing new",
                      state["reason"], state["first_bad_seq"])
            return 0
        published_at = (now or datetime.now(UTC)).isoformat()
        so_far = self.committed()
        lines = so_far.splitlines()
        records = []
        for row in self.checkpoints(json.loads(lines[-1])["seq"] if lines else 0):
            why = refusal(row, self.pinned, self.public_key)
            if why:
                # stop here rather than skip it: anchoring later heads would quietly paper over this one
                log.error("refused checkpoint %s: %s", row["seq"], why)
                break
            records.append({"seq": row["seq"], "head": row["head"], "at": signed_at(row).isoformat(), "alg": row["alg"],
                            "key_id": row["key_id"], "sig_b64": row["sig_b64"], "chain_rows": state["rows"],
                            "published_at": published_at})
        if not records:
            return 0
        (self.repo / LOG).write_text(so_far + "".join(canonical(r) + "\n" for r in records), encoding="utf-8",
                                     newline="\n")
        first, last = records[0]["seq"], records[-1]["seq"]
        self.git("add", LOG)
        self.git("commit", "-q", "-m", f"Publish audit checkpoint {last}" if first == last
                 else f"Publish audit checkpoints {first} to {last}")
        self.git("push", "-q", "origin", "HEAD")
        log.info("published %d signed checkpoint(s), seq %d to %d", len(records), first, last)
        return len(records)


def get(path: str) -> object:
    with urllib.request.urlopen(BASE_URL + path, timeout=60) as resp:
        return json.load(resp)


def api_checkpoints(after: int) -> list[dict]:
    return get(f"/api/audit/checkpoints?after={after}&limit={BATCH}")


def api_status() -> dict:
    return get("/api/audit/verify")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--once", action="store_true", help="publish what's new, then exit")
    parser.add_argument("--repo", type=Path, default=REPO, help="the audit-checkpoints worktree")
    args = parser.parse_args()
    publisher = Publisher(api_checkpoints, api_status, args.repo)
    while True:
        try:
            publisher.publish()
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            if args.once:
                raise
            # the VM, the network or GitHub dropping out isn't fatal: what's unpublished is picked up next round
            log.warning("publish failed, retrying in %d s: %s", EVERY_S, exc)
        if args.once:
            return
        time.sleep(EVERY_S)


if __name__ == "__main__":
    main()
