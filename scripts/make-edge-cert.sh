#!/bin/bash
# One-off, on the VM: a self-signed certificate for the edge until a trusted one replaces it (decision 2026-10-18:
# self-signed now, Let's Encrypt for 148-100-78-95.sslip.io as the upgrade). It never overwrites, so a trusted
# certificate dropped in its place later stays put.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
umask 077
mkdir -p secrets
if [ -e secrets/edge_cert.pem ]; then
  echo "secrets/edge_cert.pem exists; kept"
  exit 0
fi
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 30 \
  -subj "/CN=148-100-78-95.sslip.io" \
  -addext "subjectAltName=DNS:148-100-78-95.sslip.io,IP:148.100.78.95" \
  -keyout secrets/edge_key.pem -out secrets/edge_cert.pem
echo "made secrets/edge_cert.pem + edge_key.pem (self-signed, 30 days)"
