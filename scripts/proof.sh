#!/bin/bash
# Evidence that Blacknaught runs (and trains) on LinuxONE. Run on the VM: bash ~/BlackNaught/scripts/proof.sh
# Writes evidence/*.txt (committed for judges) and prints everything, for a one-take terminal screenshot.
# Never prints secrets: no tokens, passwords or keys are read here.
set -uo pipefail
cd "$(dirname "$0")/.."
OUT=evidence
mkdir -p "$OUT"
COMPOSE="sudo docker compose -f backend/compose.backend.yml"
STACK="sudo docker compose -f infra/docker-compose.yml"  # the live stack: backend plus signer, edge, agent, Granite
RUN="$COMPOSE run --rm --no-deps -e BN_WORKERS=0 app"

section() { echo; echo "=== $1 ($(date -u +%FT%TZ)) ==="; }

{
  section "Platform"
  hostname; uname -m; grep PRETTY_NAME /etc/os-release
  lscpu | grep -E "Architecture|Byte Order|Machine type|Model name|Hypervisor|CPU\(s\):"
  echo "NNPA flag: $(grep -ow nnpa /proc/cpuinfo | head -1 || echo absent)"
  free -h | head -2; df -h / | tail -1
} | tee "$OUT/01_platform.txt"

{
  section "Containers (all s390x)"
  $STACK ps
  for img in bn-app:latest bn-signer:latest bn-edge:latest postgres:17 \
             registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest; do
    echo "$img → $(sudo docker image inspect -f '{{.Architecture}}' "$img")"
  done
} | tee "$OUT/02_containers.txt"

{
  section "Training on LinuxONE: outage-duration model (Kaplan–Meier) on 312,936 ENWL outages"
  $RUN sh -c 'uname -m; time python -m app.survival /data/raw/enwl_unplanned-outages.csv /tmp/km.json' 2>&1 | grep -v -iE "creat"
  section "Training on LinuxONE: district fault-risk climatology on ENWL 1997–2026"
  $RUN sh -c 'uname -m; time python -m app.arearisk /data/raw/enwl_unplanned-outages.csv /tmp/clim.json' 2>&1 | grep -v -iE "creat"
  section "Training data on the VM"
  ls -lh ~/data/raw/*.csv; cat ~/data/raw/SHA256SUMS
} | tee "$OUT/03_training.txt"

{
  section "Test suite on s390x"
  $RUN pytest -o addopts="" -p no:cacheprovider --cov=app 2>&1 | grep -E "passed|failed|TOTAL"
} | tee "$OUT/04_tests.txt"

{
  section "Live service"
  curl -s localhost:8000/api/health; echo
  curl -s localhost:8000/api/sources/health | python3 -c "import json,sys; [print(s['source'], s['status'], s['records_last']) for s in json.load(sys.stdin)['sources']]"
  curl -s "localhost:8000/api/triage?limit=200" | python3 -c "import json,sys; d=json.load(sys.stdin); print('triage:', len(d['items']), 'ranked,', sum(i['escalate'] for i in d['items']), 'escalate, model', d['model']['id'])"
  curl -s localhost:8000/api/agent/grades | python3 -c "import json,sys; d=json.load(sys.stdin); print('grades:', [(g['source'], g['h'], g['n'], g['brier']) for g in d['by_horizon']])"
} | tee "$OUT/05_live.txt"

{
  section "Security"
  echo "Audit chain:"; curl -s localhost:8000/api/audit/verify; echo
  echo "Approve without login → $(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{"approve":true}' localhost:8000/api/decisions/00000000-0000-4000-8000-000000000000/approve)"
  echo "AES-256-GCM via libcrypto (CPACF): NIST vectors"
  $RUN pytest -o addopts="" -p no:cacheprovider tests/test_crypto_seed.py -k known_answers 2>&1 | grep -E "passed|failed"
  echo "Database roles (least privilege):"
  sudo docker exec bn-backend-db-1 psql -U postgres -d blacknaught -c "\du" | grep bn_
  echo "Firewall:"; sudo iptables -L INPUT -n | head -6
} | tee "$OUT/06_security.txt"

{
  section "Platform: stack boundaries, signer, post-quantum edge, agent, Granite"
  bash infra/test-compose.sh
  echo "Signer: $(sudo docker exec bn-backend-signer-1 python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8100/health').read().decode())")"
  # the host's OpenSSL is 3.0, which has no ML-KEM, so the client is the signer image's OpenSSL 3.5 (no key in it)
  echo "Edge, offered only the hybrid post-quantum group:"
  echo | sudo docker run --rm -i --network host --entrypoint openssl bn-signer:latest s_client -connect 127.0.0.1:8443 \
    -servername 148-100-78-95.sslip.io -groups X25519MLKEM768 -verify_return_error 2>/dev/null \
    | grep -E "Negotiated TLS1.3 group|Verify return code|issuer="
  echo "Agent decisions by tool and state:"
  curl -s "localhost:8000/api/agent/decisions?limit=500" | python3 -c "import collections, json, sys; print(dict(collections.Counter((d['tool'], d['state']) for d in json.load(sys.stdin))))"
  echo "Signed agent tool calls in the audit chain: $(sudo docker exec bn-backend-db-1 psql -U postgres -d blacknaught -tAc "SELECT count(*) FROM bn.audit_log WHERE kind = 'tool_call_signature'")"
  echo "Granite, from inside the agent's network: $(sudo docker exec bn-backend-agent-1 /opt/venv/bin/python -c "import urllib.request; print(urllib.request.urlopen('http://granite:8200/health', timeout=5).read().decode())")"
} | tee "$OUT/12_platform.txt"
