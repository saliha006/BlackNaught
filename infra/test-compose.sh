#!/bin/bash
# Checks that the rendered stack keeps the signer's boundary (decisions 2026-10-18: no published port, a private
# internal network shared only with app, app given the URL and its token) and that db keeps its data volume.
# Usage, on the VM from the repo root: bash infra/test-compose.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
docker compose -f infra/docker-compose.yml config --format json | python3 -c '
import json, sys

config = json.load(sys.stdin)
services, app = config["services"], config["services"]["app"]
checks = {
    "signer publishes no port": not services["signer"].get("ports"),
    "signer is only on the signing network": set(services["signer"]["networks"]) == {"signing"},
    "the signing network is internal": config["networks"]["signing"].get("internal") is True,
    "only app joins the signer there": {n for n, s in services.items() if "signing" in s.get("networks", {})} == {"app", "signer"},
    "app has the signer URL": app["environment"].get("BN_SIGNER_URL") == "http://signer:8100",
    "app has its token": any(s["source"] == "signer_token_app" for s in app["secrets"]),
    "app waits for a healthy signer": app["depends_on"]["signer"]["condition"] == "service_healthy",
    "db keeps its data volume": any(v.get("source") == "pgdata" for v in services["db"]["volumes"]),
}
for name, ok in checks.items():
    print(("PASS  " if ok else "FAIL  ") + name)
sys.exit(0 if all(checks.values()) else 1)
'
