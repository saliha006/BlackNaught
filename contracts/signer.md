# Signer contract (`http://signer:8100`)

The ML-DSA-65 signing service. Its private key never leaves the `signer` container: callers send bytes and get a
signature back. Background: `BLACKNAUGHT.md` §B12.

**Decisions (Ahmed, 2026-10-18):**
- The key is a file in `secrets/` like the stack's other secrets, made once by `scripts/make-signer-secrets.sh`, which
  never overwrites it.
- `/sign` needs a per-caller token, and the signer is on a private network shared only with `app` and the agent.
- `/verify` needs no token, because checking a signature can't forge one.

## `POST /sign`
Header: `Authorization: Bearer <token>`, where `<token>` is the contents of the caller's `secrets/signer_token_<caller>`
(`app` or `agent`).

```json
{"purpose": "audit_checkpoint", "payload_b64": "<the bytes to sign, base64>"}
```
→ `200`
```json
{"alg": "ML-DSA-65", "key_id": "<16 hex>", "sig_b64": "<3309-byte signature, base64>"}
```
- `purpose` is 1–64 characters. It's logged with each signature but **isn't part of what's signed**.
- `key_id` is the first 16 hex characters of the SHA-256 of the public key in PEM form, so it stays the same across
  restarts.

## `POST /verify` (no token)
```json
{"payload_b64": "...", "sig_b64": "..."}
```
→ `200` `{"ok": true}` or `{"ok": false}`. A garbled signature is `false`, not an error.

## `GET /health`
→ `200` `{"status": "ok", "alg": "ML-DSA-65", "key_id": "<16 hex>"}`

## Errors
All are JSON: `{"error": "..."}`.

| Status | When |
|---|---|
| 400 | Body isn't a JSON object, or a field is missing, malformed or empty |
| 401 | `/sign` without a known token |
| 404 | Unknown path |
| 411 | No `Content-Length` |
| 413 | Body over 1 MiB |
| 500 | OpenSSL failed for a reason other than a bad signature (details in the signer's log) |

## Checking a signature without the service
The public key is published as `contracts/signer_pub.pem` (key_id `bda7ac1f8fd6c9d2`). Any OpenSSL 3.5 can check a
signature with it: the signer image's, or Git Bash's on Windows. The VM host's is 3.0, which has no ML-DSA.
```bash
openssl pkeyutl -verify -rawin -pubin -inkey contracts/signer_pub.pem -sigfile sig.bin -in payload.bin
```
