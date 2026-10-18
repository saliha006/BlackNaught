"""Relays operator-approved CAP alerts to a public-alert channel (Ahmed).

Blacknaught drafts standard CAP 1.2 alerts that a government alerting service can broadcast; in the demo an Android
phone over ADB stands in for that channel. The relay only polls outward over TLS, and an alert reaches the channel
only if its ML-DSA-65 signature verifies against the signer's pinned public key (contracts/signer_pub.pem).

Run it on the laptop the phone is plugged into, from Git Bash (its openssl is 3.5, which knows ML-DSA):
    python alerting/relay.py              # polls every 10 s; each newly approved alert goes out once
    python alerting/relay.py --send <id>  # pushes one approved alert now, e.g. for a retake
"""
import argparse
import base64
import binascii
import json
import logging
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

BASE_URL = "https://148-100-78-95.sslip.io:8443"
PUBLIC_KEY = Path(__file__).resolve().parent.parent / "contracts" / "signer_pub.pem"
SENT = Path(__file__).resolve().parent / ".sent"  # decision ids already broadcast, one per line
POLL_S = 10
NS = {"c": "urn:oasis:names:tc:emergency:cap:1.2"}

log = logging.getLogger("relay")

Fetch = Callable[[str], tuple[bytes, dict[str, str]]]


@dataclass(frozen=True)
class Alert:
    identifier: str
    status: str
    headline: str
    description: str
    instruction: str
    area: str


def parse(xml: bytes) -> Alert:
    root = ET.fromstring(xml)
    info = root.find("c:info", NS)
    return Alert(root.findtext("c:identifier", "", NS), root.findtext("c:status", "", NS),
                 info.findtext("c:headline", "", NS), info.findtext("c:description", "", NS),
                 info.findtext("c:instruction", "", NS), info.findtext("c:area/c:areaDesc", "", NS))


def verify(xml: bytes, sig_b64: str, public_key: Path = PUBLIC_KEY) -> bool:
    """True only if openssl confirms the ML-DSA-65 signature over exactly these bytes."""
    try:
        signature = base64.b64decode(sig_b64, validate=True)
    except binascii.Error:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        message, sig_file = Path(tmp, "alert.xml"), Path(tmp, "alert.sig")
        message.write_bytes(xml)
        sig_file.write_bytes(signature)
        done = subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key), "-rawin",
                               "-in", str(message), "-sigfile", str(sig_file)], capture_output=True, timeout=30)
    if done.returncode == 0:
        return True
    if b"Signature Verification Failure" in done.stdout:
        return False
    raise RuntimeError(f"openssl could not check the signature: {done.stderr.decode(errors='replace').strip()[:300]}")


class Channel(Protocol):
    """Where an approved, verified alert goes. A government alerting service takes the phone's place here."""

    def broadcast(self, alert: Alert) -> None: ...


class AdbPhone:
    """The demo's stand-in channel: wakes a USB-connected Android phone and posts the alert as a notification."""

    def __init__(self, adb: str, run: Callable[..., object] = subprocess.run):
        self.adb = adb
        self.run = run

    def broadcast(self, alert: Alert) -> None:
        title = ("EXERCISE: " if alert.status == "Exercise" else "") + alert.headline
        post = ["cmd", "notification", "post", "-S", "bigtext", "-t", title, alert.identifier,
                f"{alert.area}. {alert.description} {alert.instruction}"]
        # adb joins its arguments into one line for the phone's shell, so the alert text is quoted for that shell
        self.run([self.adb, "shell", "input keyevent KEYCODE_WAKEUP && " + shlex.join(post)],
                 check=True, capture_output=True, timeout=20)


class Relay:
    def __init__(self, fetch: Fetch, channel: Channel, sent: Path = SENT, public_key: Path = PUBLIC_KEY):
        self.fetch = fetch
        self.channel = channel
        self.sent_path = sent
        self.public_key = public_key
        self.sent = set(sent.read_text().split()) if sent.exists() else set()
        self.refused: set[str] = set()

    def approved(self) -> list[str]:
        body, _ = self.fetch("/api/agent/decisions?limit=500")
        return [d["id"] for d in json.loads(body)
                if d["tool"] == "draft_cap_alert" and d["state"] in ("approved", "exported")]

    def send(self, decision_id: str) -> bool:
        """Broadcasts one approved alert. Returns False, and sends nothing, if its signature is missing or wrong."""
        xml, headers = self.fetch(f"/api/alerts/cap/{decision_id}")
        sig = headers.get("x-signature-ml-dsa-65")
        if not sig or not verify(xml, sig, self.public_key):
            log.error("refused %s: %s", decision_id, "it is unsigned" if not sig else "its signature does not verify")
            self.refused.add(decision_id)
            return False
        alert = parse(xml)
        self.channel.broadcast(alert)
        with self.sent_path.open("a") as f:
            f.write(decision_id + "\n")
        self.sent.add(decision_id)
        log.info("broadcast %s for %s (ML-DSA-65 signature verified)", alert.identifier, alert.area)
        return True

    def poll(self) -> int:
        due = [d for d in self.approved() if d not in self.sent and d not in self.refused]
        return sum(self.send(d) for d in due)


def fetch(path: str) -> tuple[bytes, dict[str, str]]:
    with urllib.request.urlopen(BASE_URL + path, timeout=15) as resp:
        return resp.read(), {k.lower(): v for k, v in resp.headers.items()}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--send", metavar="DECISION_ID", help="push this approved alert now, then exit")
    parser.add_argument("--adb", default=shutil.which("adb")
                        or str(Path.home() / "AppData/Local/Android/Sdk/platform-tools/adb.exe"))
    args = parser.parse_args()
    if shutil.which("openssl") is None:
        sys.exit("relay: openssl 3.5 isn't on PATH; run it from Git Bash")
    relay = Relay(fetch, AdbPhone(args.adb))
    if args.send:
        sys.exit(0 if relay.send(args.send) else 1)
    log.info("relaying approved alerts from %s to the phone", BASE_URL)
    while True:
        try:
            relay.poll()
        except (OSError, subprocess.SubprocessError) as exc:
            # the network or the phone dropping out isn't fatal: nothing was marked sent, so the next poll retries
            log.warning("poll failed, retrying in %d s: %s", POLL_S, exc)
        time.sleep(POLL_S)


if __name__ == "__main__":
    main()
