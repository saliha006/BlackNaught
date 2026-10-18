"""ML-DSA-65 signer, the only place Blacknaught's signing key exists (contract: contracts/signer.md).

The app and the agent send bytes and get a signature back, so neither ever holds the key. OpenSSL 3.5's command does
the cryptography: ML-DSA isn't in Python's standard library, and it's the same command anyone can use to check a
signature against our public key.
"""
import base64
import hashlib
import hmac
import json
import os
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ALG = "ML-DSA-65"
KEY = Path("/run/secrets/signer_key")
TOKEN_DIR = Path("/run/secrets")
PORT = 8100
MAX_BODY = 1 << 20  # checkpoints and CAP XML are a few KB, so anything near this is a mistake
OPENSSL_TIMEOUT_S = 10


class SignerError(Exception):
    """OpenSSL failed for a reason other than a bad signature."""


class ClientError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def log(**fields: object) -> None:
    print(json.dumps({"at": datetime.now(UTC).isoformat(), **fields}), flush=True)


def openssl(*args: str, data: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["openssl", *args], input=data, capture_output=True, timeout=OPENSSL_TIMEOUT_S)


class Signer:
    def __init__(self, key: Path, token_dir: Path, workdir: Path):
        public = openssl("pkey", "-in", str(key), "-pubout")
        if public.returncode != 0:
            raise SystemExit(f"signer: can't read a private key at {key}")
        described = openssl("pkey", "-pubin", "-noout", "-text_pub", data=public.stdout)
        if not described.stdout.startswith(f"{ALG} Public-Key".encode()):
            raise SystemExit(f"signer: the key at {key} isn't {ALG}")
        self.tokens = {path.name.removeprefix("signer_token_"): token
                       for path in token_dir.glob("signer_token_*") if (token := path.read_bytes().strip())}
        if not self.tokens:
            raise SystemExit(f"signer: no signer_token_<caller> files in {token_dir}")
        self.key = key
        self.workdir = workdir
        self.public_key = workdir / "public.pem"
        self.public_key.write_bytes(public.stdout)
        # Checkpoints store key_id, so it has to come from the key itself and survive restarts.
        self.key_id = hashlib.sha256(public.stdout).hexdigest()[:16]

    def caller(self, authorization: str) -> str | None:
        scheme, _, presented = authorization.partition(" ")
        if scheme != "Bearer":
            return None
        for name, token in self.tokens.items():
            if hmac.compare_digest(token, presented.encode()):
                return name
        return None

    @contextmanager
    def _file(self, content: bytes) -> Iterator[str]:
        fd, path = tempfile.mkstemp(dir=self.workdir)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            yield path
        finally:
            os.unlink(path)

    def _pkeyutl(self, message: bytes, *args: str) -> subprocess.CompletedProcess[bytes]:
        # ML-DSA is one-shot: OpenSSL needs the message size up front, which it can't get from a pipe.
        with self._file(message) as path:
            return openssl("pkeyutl", *args, "-rawin", "-in", path)

    def sign(self, payload: bytes) -> bytes:
        done = self._pkeyutl(payload, "-sign", "-inkey", str(self.key))
        if done.returncode != 0:
            raise SignerError(done.stderr.decode(errors="replace"))
        return done.stdout

    def verify(self, payload: bytes, signature: bytes) -> bool:
        with self._file(signature) as sig_path:
            done = self._pkeyutl(payload, "-verify", "-pubin", "-inkey", str(self.public_key), "-sigfile", sig_path)
        if done.returncode == 0:
            return True
        if b"Signature Verification Failure" in done.stdout:
            return False
        raise SignerError(done.stderr.decode(errors="replace"))


def base64_field(body: dict, name: str) -> bytes:
    try:
        decoded = base64.b64decode(body.get(name), validate=True)
    except (TypeError, ValueError):
        decoded = b""
    # OpenSSL can't sign or verify an empty message, so empty is refused along with the malformed cases.
    if not decoded:
        raise ClientError(400, f"{name} must be non-empty base64")
    return decoded


class Handler(BaseHTTPRequestHandler):
    signer: Signer

    def do_GET(self) -> None:
        if self.path == "/health":
            self.reply(200, {"status": "ok", "alg": ALG, "key_id": self.signer.key_id})
        else:
            self.reply(404, {"error": "not found"})

    def do_POST(self) -> None:
        routes = {"/sign": self.sign, "/verify": self.verify}
        try:
            if self.path not in routes:
                raise ClientError(404, "not found")
            self.reply(200, routes[self.path]())
        except ClientError as e:
            self.reply(e.status, {"error": str(e)})
        except (SignerError, subprocess.TimeoutExpired) as e:
            log(event="openssl_failed", path=self.path, detail=str(e)[:500])
            self.reply(500, {"error": "signer failed; see its log"})

    def sign(self) -> dict[str, str]:
        caller = self.signer.caller(self.headers.get("Authorization", ""))
        if caller is None:
            raise ClientError(401, "missing or unknown token")
        body = self.json_body()
        purpose = body.get("purpose")
        if not isinstance(purpose, str) or not 0 < len(purpose) <= 64:
            raise ClientError(400, "purpose must be a string of 1-64 characters")
        payload = base64_field(body, "payload_b64")
        signature = self.signer.sign(payload)
        log(event="signed", caller=caller, purpose=purpose, payload_sha256=hashlib.sha256(payload).hexdigest())
        return {"alg": ALG, "key_id": self.signer.key_id, "sig_b64": base64.b64encode(signature).decode()}

    def verify(self) -> dict[str, bool]:
        body = self.json_body()
        return {"ok": self.signer.verify(base64_field(body, "payload_b64"), base64_field(body, "sig_b64"))}

    def json_body(self) -> dict:
        try:
            length = int(self.headers["Content-Length"])
        except (TypeError, ValueError):
            raise ClientError(411, "Content-Length required") from None
        if length > MAX_BODY:
            raise ClientError(413, "body over 1 MiB")
        try:
            body = json.loads(self.rfile.read(max(length, 0)))
        except ValueError:
            raise ClientError(400, "body must be JSON") from None
        if not isinstance(body, dict):
            raise ClientError(400, "body must be a JSON object")
        return body

    def reply(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(signer: Signer, host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), type("SignerHandler", (Handler,), {"signer": signer}))


def main() -> None:
    signer = Signer(KEY, TOKEN_DIR, Path(tempfile.mkdtemp(prefix="signer-")))
    server = serve(signer, "0.0.0.0", PORT)
    log(event="ready", alg=ALG, key_id=signer.key_id, callers=sorted(signer.tokens))
    server.serve_forever()


if __name__ == "__main__":
    main()
