import base64
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "offbox"))

import publish  # noqa: E402

SIGNED_AT = datetime(2026, 10, 18, 6, 5, 0, 123456, tzinfo=UTC)
OK = {"ok": True, "rows": 296, "first_bad_seq": None, "reason": None}


@pytest.fixture(scope="module")
def key(tmp_path_factory) -> tuple[Path, Path]:
    d = tmp_path_factory.mktemp("keys")
    private, public = d / "key.pem", d / "pub.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ML-DSA-65", "-out", str(private)], check=True)
    subprocess.run(["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)], check=True)
    return private, public


def sign(private: Path, data: bytes, tmp_path: Path) -> str:
    message, sig = tmp_path / "message", tmp_path / "sig"
    message.write_bytes(data)
    subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(private), "-rawin", "-in", str(message),
                    "-out", str(sig)], check=True)
    return base64.b64encode(sig.read_bytes()).decode()


def checkpoint(seq: int, key, tmp_path: Path, signed: bytes | None = None, **change) -> dict:
    """A row as the VM returns it, signed the way the signer signs a checkpoint (or over `signed` instead)."""
    private, public = key
    at_us = (SIGNED_AT - publish.EPOCH) // timedelta(microseconds=1) + seq
    head = hashlib.sha256(str(seq).encode()).hexdigest()
    row = {"seq": seq, "head": head, "at_us": at_us, "alg": "ML-DSA-65", "key_id": publish.key_id(public)}
    row["sig_b64"] = sign(private, signed or publish.payload(seq, head, publish.signed_at(row)), tmp_path)
    return {**row, **change}


@pytest.fixture
def branch(tmp_path) -> tuple[Path, Path]:
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "audit-checkpoints", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "audit-checkpoints", str(work)], check=True)
    for setting in (("user.name", "Test"), ("user.email", "test@example.invalid"), ("commit.gpgsign", "false")):
        subprocess.run(["git", "-C", str(work), "config", *setting], check=True)
    subprocess.run(["git", "-C", str(work), "remote", "add", "origin", str(remote)], check=True)
    return work, remote


def pushed(remote: Path) -> list[str]:
    done = subprocess.run(["git", "-C", str(remote), "log", "--format=%s", "audit-checkpoints"],
                          capture_output=True, text=True)
    return done.stdout.splitlines() if done.returncode == 0 else []


def source(rows: list[dict]) -> publish.Checkpoints:
    return lambda after: [r for r in rows if r["seq"] > after]


def test_the_signed_bytes_are_the_backends_checkpoint_payload():
    assert publish.payload(7, "ab" * 32, SIGNED_AT) == (
        b'{"at":"2026-10-18T06:05:00.123456+00:00","head":"' + b"ab" * 32 + b'","seq":7}')


def test_a_windows_line_ending_does_not_rename_the_key(key, tmp_path):
    lf, crlf = tmp_path / "lf.pem", tmp_path / "crlf.pem"
    lf.write_bytes(key[1].read_bytes().replace(b"\r\n", b"\n"))  # Windows' openssl itself writes CRLF
    crlf.write_bytes(lf.read_bytes().replace(b"\n", b"\r\n"))
    assert publish.key_id(crlf) == publish.key_id(lf) == hashlib.sha256(lf.read_bytes()).hexdigest()[:16]


def test_a_new_signed_checkpoint_is_published_once(key, tmp_path, branch):
    work, remote = branch
    publisher = publish.Publisher(source([checkpoint(1, key, tmp_path)]), lambda: OK, work, key[1])
    assert publisher.publish() == 1
    [line] = (work / publish.LOG).read_text().splitlines()
    record = json.loads(line)
    assert record["seq"] == 1 and record["at"] == "2026-10-18T06:05:00.123457+00:00" and record["chain_rows"] == 296
    assert line == publish.canonical(record)
    assert pushed(remote) == ["Publish audit checkpoint 1"]
    assert publisher.publish() == 0 and pushed(remote) == ["Publish audit checkpoint 1"]


def test_new_checkpoints_since_the_last_run_go_out_in_one_commit(key, tmp_path, branch):
    work, remote = branch
    rows = [checkpoint(seq, key, tmp_path) for seq in (1, 2, 3)]
    assert publish.Publisher(source(rows[:1]), lambda: OK, work, key[1]).publish() == 1
    assert publish.Publisher(source(rows), lambda: OK, work, key[1]).publish() == 2  # a restart reads the branch
    assert pushed(remote) == ["Publish audit checkpoints 2 to 3", "Publish audit checkpoint 1"]


def test_a_bad_signature_stops_publishing_at_that_checkpoint(key, tmp_path, branch):
    work, remote = branch
    forged = checkpoint(2, key, tmp_path, signed=b"something else")
    rows = [checkpoint(1, key, tmp_path), forged, checkpoint(3, key, tmp_path)]
    assert publish.Publisher(source(rows), lambda: OK, work, key[1]).publish() == 1
    assert [json.loads(x)["seq"] for x in (work / publish.LOG).read_text().splitlines()] == [1]


@pytest.mark.parametrize("change", [{"key_id": "0123456789abcdef"}, {"alg": "ML-DSA-44"}, {"head": "zz" * 32},
                                    {"head": "ab" * 31}])
def test_a_foreign_key_or_a_malformed_head_is_refused(key, tmp_path, branch, change):
    work, remote = branch
    assert publish.Publisher(source([checkpoint(1, key, tmp_path, **change)]), lambda: OK, work, key[1]).publish() == 0
    assert not pushed(remote)


def test_nothing_is_anchored_while_the_servers_chain_check_fails(key, tmp_path, branch):
    work, remote = branch
    broken = {**OK, "ok": False, "first_bad_seq": 12, "reason": "hash_mismatch"}
    assert publish.Publisher(source([checkpoint(1, key, tmp_path)]), lambda: broken, work, key[1]).publish() == 0
    assert not (work / publish.LOG).exists() and not pushed(remote)


def test_a_line_left_by_a_failed_commit_is_not_taken_as_published(key, tmp_path, branch):
    work, remote = branch
    (work / publish.LOG).write_text(json.dumps({"seq": 5}) + "\n")  # written, never committed
    assert publish.Publisher(source([checkpoint(1, key, tmp_path)]), lambda: OK, work, key[1]).publish() == 1
    assert [json.loads(x)["seq"] for x in (work / publish.LOG).read_text().splitlines()] == [1]
