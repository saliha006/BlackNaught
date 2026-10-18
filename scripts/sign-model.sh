#!/bin/bash
# One-off, on the VM (Ahmed): sign a model release, so the NNPA shadow scorer loads only what was signed.
# It signs as the agent, whose token stays in its file, and writes <model>.sig.json next to the model.
# Usage, from the repo root of the deploy copy:
#   bash scripts/sign-model.sh ~/models/m2_hazard.keras ~/shared/nate-runs/models/m2_metrics.json
set -euo pipefail
model=$(readlink -f "$1")
metrics=$(readlink -f "$2")
cd "$(git rev-parse --show-toplevel)"
# the signer is reachable only on the internal signing network, so this runs a throwaway app container on it
docker run --rm --network bn-backend_signing \
  -v "$PWD/backend:/srv:ro" -w /srv \
  -v "$model:/release/$(basename "$model"):ro" -v "$metrics:/release/metrics.json:ro" \
  -v "$PWD/secrets/signer_token_agent:/run/secrets/signer_token_agent:ro" \
  -e BN_SECRETS_DIR=/run/secrets -e BN_SIGNER_URL=http://signer:8100 \
  --entrypoint /opt/venv/bin/python bn-app:latest \
  -m app.nnpa --sign "/release/$(basename "$model")" /release/metrics.json </dev/null > "$model.sig.json.tmp"
mv "$model.sig.json.tmp" "$model.sig.json"
echo "signed $(basename "$model") -> $model.sig.json"
