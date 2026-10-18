import base64
import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "alerting"), str(ROOT / "backend")]

import relay  # noqa: E402
from app import cap  # noqa: E402  (Sali's builder, so the relay reads the XML the server really sends)

XML = cap.build("d-1", "exercise@blacknaught.invalid", "operator", [(51.54, -0.09), (51.55, -0.08), (51.53, -0.07)],
                "N1", severe=True, confirmed=True, headline="Power cut in N1").encode()


@pytest.fixture(scope="module")
def key(tmp_path_factory) -> tuple[Path, Path]:
    d = tmp_path_factory.mktemp("keys")
    private, public = d / "key.pem", d / "pub.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ML-DSA-65", "-out", str(private)], check=True)
    subprocess.run(["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)], check=True)
    return private, public


def sign(private: Path, payload: bytes, tmp_path: Path) -> str:
    message, sig = tmp_path / "message", tmp_path / "sig"
    message.write_bytes(payload)
    subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(private), "-rawin", "-in", str(message),
                    "-out", str(sig)], check=True)
    return base64.b64encode(sig.read_bytes()).decode()


class Phone:
    def __init__(self):
        self.alerts: list[relay.Alert] = []

    def broadcast(self, alert: relay.Alert) -> None:
        self.alerts.append(alert)


def server(cap_alerts: dict[str, tuple[bytes, str | None]]) -> relay.Fetch:
    """A fake API: the decision list plus each CAP alert with its signature header (None = unsigned)."""
    decisions = [{"id": i, "tool": "draft_cap_alert", "state": "approved"} for i in cap_alerts]
    decisions += [{"id": "e-1", "tool": "escalate", "state": "approved"},
                  {"id": "d-9", "tool": "draft_cap_alert", "state": "awaiting_approval"}]

    def fetch(path: str) -> tuple[bytes, dict[str, str]]:
        if path.startswith("/api/agent/decisions"):
            return json.dumps(decisions).encode(), {}
        xml, sig = cap_alerts[path.rsplit("/", 1)[1]]
        return xml, {"x-signature-ml-dsa-65": sig} if sig else {}

    return fetch


def test_parse_reads_the_alert_the_server_builds():
    alert = relay.parse(XML)
    assert alert == relay.Alert("blacknaught-d-1", "Exercise", "Power cut in N1", "Power is off in N1.",
                                cap.DEFAULT_INSTRUCTION, "N1")


def test_only_the_exact_signed_bytes_verify(key, tmp_path):
    private, public = key
    sig = sign(private, XML, tmp_path)
    assert relay.verify(XML, sig, public)
    assert not relay.verify(XML.replace(b"Power cut in N1", b"Power cut in N2"), sig, public)
    assert not relay.verify(XML, "not base64!", public)


def test_a_broken_check_is_an_error_not_a_quiet_no(key, tmp_path):
    with pytest.raises(RuntimeError, match="could not check"):
        relay.verify(XML, sign(key[0], XML, tmp_path), tmp_path / "missing.pem")


def test_an_approved_signed_alert_goes_out_once_even_across_a_restart(key, tmp_path):
    private, public = key
    phone, sent = Phone(), tmp_path / "sent"
    fetch = server({"d-1": (XML, sign(private, XML, tmp_path))})
    assert relay.Relay(fetch, phone, sent, public).poll() == 1
    assert [a.headline for a in phone.alerts] == ["Power cut in N1"]  # the escalation and the unapproved draft stay
    assert relay.Relay(fetch, phone, sent, public).poll() == 0
    assert len(phone.alerts) == 1


def test_an_unsigned_or_tampered_alert_never_reaches_the_phone(key, tmp_path):
    private, public = key
    tampered = XML.replace(b"Power cut in N1", b"Power cut in N2")
    phone = Phone()
    r = relay.Relay(server({"u-1": (XML, None), "t-1": (tampered, sign(private, XML, tmp_path))}), phone,
                    tmp_path / "sent", public)
    assert r.poll() == 0 and r.poll() == 0  # refused once, not re-fetched every poll
    assert not phone.alerts and r.refused == {"u-1", "t-1"}
    assert not (tmp_path / "sent").exists()


def test_the_phone_command_keeps_hostile_alert_text_as_one_argument():
    calls = []
    phone = relay.AdbPhone("adb", run=lambda argv, **_: calls.append(argv))
    phone.broadcast(relay.Alert("blacknaught-1", "Exercise", "Cut'; reboot; echo '", "Off.", "Check on them.", "N1"))
    [argv] = calls
    assert argv[:2] == ["adb", "shell"]
    wake, post = argv[2].split(" && ", 1)
    assert wake == "input keyevent KEYCODE_WAKEUP"
    assert shlex.split(post) == ["cmd", "notification", "post", "-S", "bigtext", "-t", "EXERCISE: Cut'; reboot; echo '",
                                 "blacknaught-1", "N1. Off. Check on them."]
