#!/bin/bash
# Checks that the rendered stack keeps the signer's boundary (decisions 2026-10-18: no published port, a private
# internal network shared only with app and the agent, each with its own token) and that db keeps its data volume.
# Usage, on the VM from the repo root: bash infra/test-compose.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
docker compose -f infra/docker-compose.yml config --format json | python3 -c '
import json, sys

config = json.load(sys.stdin)
services, app, agent = config["services"], config["services"]["app"], config["services"]["agent"]
checks = {
    "signer publishes no port": not services["signer"].get("ports"),
    "signer is only on the signing network": set(services["signer"]["networks"]) == {"signing"},
    "the signing network is internal": config["networks"]["signing"].get("internal") is True,
    "only app and the agent join the signer there": {n for n, s in services.items() if "signing" in s.get("networks", {})} == {"app", "agent", "signer"},
    "app has the signer URL": app["environment"].get("BN_SIGNER_URL") == "http://signer:8100",
    "app has its token": any(s["source"] == "signer_token_app" for s in app["secrets"]),
    "the agent signs with its own token, not the app token": {s["source"] for s in agent["secrets"]} == {"db_agent_pw", "signer_token_agent"},
    "the agent publishes no port": not agent.get("ports"),
    "granite publishes no port": not services["granite"].get("ports"),
    "granite is only on the writing network": set(services["granite"]["networks"]) == {"writing"},
    "the writing network is internal": config["networks"]["writing"].get("internal") is True,
    "only the agent joins granite there": {n for n, s in services.items() if "writing" in s.get("networks", {})} == {"agent", "granite"},
    "granite loads only the pinned model": len(services["granite"]["environment"]["BN_GRANITE_SHA256"]) == 64,
    "app waits for a healthy signer": app["depends_on"]["signer"]["condition"] == "service_healthy",
    "db keeps its data volume": any(v.get("source") == "pgdata" for v in services["db"]["volumes"]),
    "edge publishes only 8443": [str(p["published"]) for p in services["edge"]["ports"]] == ["8443"],
    "app is still reachable only from the VM itself": all(p.get("host_ip") == "127.0.0.1" for p in app["ports"]),
}
for name, ok in checks.items():
    print(("PASS  " if ok else "FAIL  ") + name)
sys.exit(0 if all(checks.values()) else 1)
'
