#!/usr/bin/env bash
# Deploy Hermes pilot to your server. Run from repo root on your local machine.
# Usage: ./scripts/deploy_pilot.sh
# Requires: .env file with secrets (never commit .env)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing .env — copy .env.example to .env and fill in values first."
  exit 1
fi

# shellcheck disable=SC1091
source .env

: "${DEPLOY_HOST:?Set DEPLOY_HOST in .env}"
: "${DEPLOY_USER:?Set DEPLOY_USER in .env}"
: "${PUBLIC_DOMAIN:?Set PUBLIC_DOMAIN in .env}"

REMOTE_DIR="${DEPLOY_REMOTE_DIR:-/home/${DEPLOY_USER}/hermes-pilot}"

echo "==> Syncing project to ${DEPLOY_USER}@${DEPLOY_HOST}:${REMOTE_DIR}"
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" "mkdir -p ${REMOTE_DIR}"

rsync -avz --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude 'data' \
  --exclude '.env' \
  "${ROOT}/" "${DEPLOY_USER}@${DEPLOY_HOST}:${REMOTE_DIR}/"

echo "==> Uploading .env (secrets)"
scp "${ROOT}/.env" "${DEPLOY_USER}@${DEPLOY_HOST}:${REMOTE_DIR}/.env"

echo "==> Starting Docker Compose on remote"
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" bash -s <<REMOTE
set -euo pipefail
cd "${REMOTE_DIR}/infra"
docker compose -f docker-compose.pilot.yml pull || true
docker compose -f docker-compose.pilot.yml up -d --build
docker compose -f docker-compose.pilot.yml ps
REMOTE

echo ""
echo "Pilot deployed. Open: https://${PUBLIC_DOMAIN}"
echo "Health check: https://${PUBLIC_DOMAIN}/health"
