"""The signer, driven over HTTP the way the app and the agent call it."""
import base64
import http.client
import json
import subprocess
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import signer

PAYLOAD = b'{"at":"2026-10-18T05:00:00+00:00","head":"ab12","seq":500}'


def make_key(path: Path, algorithm: str = "ML-DSA-65") -> Path:
    subprocess.run(["openssl", "genpkey", "-algorithm", algorithm, "-out", str(path)], check=True, capture_output=True)
    return path


@pytest.fixture
def secrets(tmp_path: Path) -> Path:
    make_key(tmp_path / "signer_key")
    (tmp_path / "signer_token_app").write_text("app-token\n")
    (tmp_path / "signer_token_agent").write_text("agent-token\n")
    return tmp_path


@pytest.fixture
def service(secrets: Path, tmp_path_factory: pytest.TempPathFactory) -> signer.Signer:
    return signer.Signer(secrets / "signer_key", secrets, tmp_path_factory.mktemp("work"))


@pytest.fixture
def url(service: signer.Signer):
    server = signer.serve(service, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def call(url: str, path: str, body: dict | bytes | None = None, authorization: str | None = None) -> tuple[int, dict]:
    if isinstance(body, dict):
        body = json.dumps(body).encode()
    request = urllib.request.Request(url + path, data=body, method="GET" if body is None else "POST")
    if authorization is not None:
        request.add_header("Authorization", authorization)
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def sign(url: str, payload: bytes = PAYLOAD, token: str = "app-token") -> tuple[int, dict]:
    return call(url, "/sign", {"purpose": "audit_checkpoint", "payload_b64": b64(payload)}, f"Bearer {token}")


def verify(url: str, payload: bytes, sig_b64: str) -> bool:
    status, body = call(url, "/verify", {"payload_b64": b64(payload), "sig_b64": sig_b64})
    assert status == 200
    return body["ok"]


def raw_post(url: str, path: str, headers: dict[str, str]) -> int:
    host, port = url.removeprefix("http://").split(":")
    conn = http.client.HTTPConnection(host, int(port), timeout=10)
    conn.putrequest("POST", path)
    for name, value in headers.items():
        conn.putheader(name, value)
    conn.endheaders()
    return conn.getresponse().status


def test_health_names_the_algorithm_and_key(url, service):
    assert call(url, "/health") == (200, {"status": "ok", "alg": "ML-DSA-65", "key_id": service.key_id})


def test_a_signature_comes_back_in_the_contract_shape_and_verifies(url, service):
    status, body = sign(url)
    assert status == 200
    assert set(body) == {"alg", "key_id", "sig_b64"}
    assert (body["alg"], body["key_id"]) == ("ML-DSA-65", service.key_id)
    assert len(base64.b64decode(body["sig_b64"])) == 3309  # the FIPS 204 signature size for ML-DSA-65
    assert verify(url, PAYLOAD, body["sig_b64"]) is True


@pytest.mark.parametrize("changed", [PAYLOAD + b" ", PAYLOAD.replace(b"500", b"501")], ids=["appended", "edited"])
def test_a_changed_payload_no_longer_verifies(url, changed):
    assert verify(url, changed, sign(url)[1]["sig_b64"]) is False


def test_a_signature_from_another_key_does_not_verify(url, tmp_path):
    (tmp_path / "msg").write_bytes(PAYLOAD)
    other = subprocess.run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(make_key(tmp_path / "other.pem")),
                            "-in", str(tmp_path / "msg")], check=True, capture_output=True).stdout
    assert verify(url, PAYLOAD, b64(other)) is False


def test_a_garbled_signature_is_invalid_not_an_error(url):
    assert verify(url, PAYLOAD, b64(b"not a signature")) is False


def test_anyone_with_the_public_key_can_check_a_signature_without_the_service(url, secrets, tmp_path):
    public = subprocess.run(["openssl", "pkey", "-in", str(secrets / "signer_key"), "-pubout"],
                            check=True, capture_output=True).stdout
    (tmp_path / "public.pem").write_bytes(public)
    (tmp_path / "msg").write_bytes(PAYLOAD)
    (tmp_path / "sig").write_bytes(base64.b64decode(sign(url)[1]["sig_b64"]))
    checked = subprocess.run(["openssl", "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", str(tmp_path / "public.pem"),
                              "-sigfile", str(tmp_path / "sig"), "-in", str(tmp_path / "msg")], capture_output=True)
    assert checked.returncode == 0


@pytest.mark.parametrize("authorization", [None, "Bearer wrong", "Bearer ", "Basic app-token"],
                         ids=["none", "unknown", "empty", "not-bearer"])
def test_sign_refuses_without_a_known_token(url, authorization):
    body = {"purpose": "audit_checkpoint", "payload_b64": b64(PAYLOAD)}
    assert call(url, "/sign", body, authorization)[0] == 401


def test_each_caller_signs_with_its_own_token(url):
    assert sign(url, token="app-token")[0] == 200
    assert sign(url, token="agent-token")[0] == 200


def test_verify_needs_no_token(url):
    status, body = call(url, "/verify", {"payload_b64": b64(PAYLOAD), "sig_b64": sign(url)[1]["sig_b64"]})
    assert (status, body) == (200, {"ok": True})


@pytest.mark.parametrize("body", [
    pytest.param(b"not json", id="not-json"),
    pytest.param(b"[1, 2]", id="not-an-object"),
    pytest.param({"payload_b64": b64(PAYLOAD)}, id="no-purpose"),
    pytest.param({"purpose": "x" * 65, "payload_b64": b64(PAYLOAD)}, id="purpose-too-long"),
    pytest.param({"purpose": "audit_checkpoint", "payload_b64": "not base64!"}, id="bad-base64"),
    pytest.param({"purpose": "audit_checkpoint", "payload_b64": ""}, id="empty-payload"),
])
def test_sign_rejects_a_bad_body(url, body):
    assert call(url, "/sign", body, "Bearer app-token")[0] == 400


def test_an_oversized_body_is_refused_before_it_is_read(url):
    assert raw_post(url, "/verify", {"Content-Length": str(signer.MAX_BODY + 1)}) == 413


def test_a_body_without_a_length_is_refused(url):
    assert raw_post(url, "/verify", {}) == 411


@pytest.mark.parametrize("body", [None, {}], ids=["GET", "POST"])
def test_unknown_paths_are_404(url, body):
    assert call(url, "/nope", body)[0] == 404


def test_key_id_comes_from_the_key_so_it_survives_a_restart(secrets, tmp_path_factory):
    first = signer.Signer(secrets / "signer_key", secrets, tmp_path_factory.mktemp("first"))
    second = signer.Signer(secrets / "signer_key", secrets, tmp_path_factory.mktemp("second"))
    assert first.key_id == second.key_id
    assert len(first.key_id) == 16


def test_startup_refuses_a_missing_or_non_ml_dsa_key(secrets, tmp_path):
    with pytest.raises(SystemExit):
        signer.Signer(tmp_path / "absent", secrets, tmp_path)
    with pytest.raises(SystemExit):
        signer.Signer(make_key(tmp_path / "ed25519.pem", "ED25519"), secrets, tmp_path)


def test_startup_refuses_when_no_caller_has_a_token(secrets, tmp_path):
    tokens = tmp_path / "tokens"
    tokens.mkdir()
    (tokens / "signer_token_app").write_text("\n")
    with pytest.raises(SystemExit):
        signer.Signer(secrets / "signer_key", tokens, tmp_path)


def test_a_vanished_key_is_a_server_error_not_a_signature(url, service):
    service.key.unlink()
    assert sign(url)[0] == 500


def test_a_broken_verify_setup_is_a_server_error_not_an_invalid_signature(url, service):
    sig_b64 = sign(url)[1]["sig_b64"]
    service.public_key.unlink()
    assert call(url, "/verify", {"payload_b64": b64(PAYLOAD), "sig_b64": sig_b64})[0] == 500
