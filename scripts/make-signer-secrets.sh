#!/bin/bash
# One-off, on the VM: makes the signer's ML-DSA-65 key and its per-caller tokens in secrets/, next to the stack's other
# secrets. It never overwrites a file, because a new key would stop every earlier audit checkpoint from verifying.
# Needs the signer image first: docker build --target signer -t bn-signer signer/
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
umask 077
mkdir -p secrets
if [ -e secrets/signer_key ]; then
  echo "secrets/signer_key exists; kept"
else
  # The host's OpenSSL is 3.0, which has no ML-DSA, so the image's OpenSSL 3.5 makes the key.
  docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/secrets:/out" bn-signer \
    openssl genpkey -algorithm ML-DSA-65 -out /out/signer_key
  chmod 600 secrets/signer_key
  echo "made secrets/signer_key"
fi
for caller in app agent; do
  token="secrets/signer_token_$caller"
  if [ -e "$token" ]; then
    echo "$token exists; kept"
  else
    openssl rand -hex 32 > "$token"
    echo "made $token"
  fi
done
