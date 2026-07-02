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
CADDY_HTTP_BIND="${CADDY_HTTP_BIND:-80}"
CADDY_HTTPS_BIND="${CADDY_HTTPS_BIND:-443}"
PILOT_API_BIND="${PILOT_API_BIND:-127.0.0.1:18000}"

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

echo "==> Remote port preflight"
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" bash -s <<REMOTE
set -euo pipefail
echo "Requested binds:"
echo "  CADDY_HTTP_BIND=${CADDY_HTTP_BIND}"
echo "  CADDY_HTTPS_BIND=${CADDY_HTTPS_BIND}"
echo "  PILOT_API_BIND=${PILOT_API_BIND}"
echo ""
echo "Current listeners on 80/443/18000 (if any):"
ss -ltnp '( sport = :80 or sport = :443 or sport = :18000 )' 2>/dev/null || true
REMOTE

echo "==> Starting Docker Compose on remote"
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" bash -s <<REMOTE
set -euo pipefail
cd "${REMOTE_DIR}/infra"
docker compose --env-file ../.env -f docker-compose.pilot.yml pull || true
if ! docker compose --env-file ../.env -f docker-compose.pilot.yml up -d --build; then
  echo ""
  echo "Docker Compose failed."
  echo "If 80/443 are already in use, either:"
  echo "  1) stop the existing service using those ports, or"
  echo "  2) keep your existing reverse proxy and set in .env:"
  echo "     CADDY_HTTP_BIND=8080"
  echo "     CADDY_HTTPS_BIND=8443"
  echo "     PILOT_API_BIND=127.0.0.1:18000"
  echo "Then proxy ${PUBLIC_DOMAIN} to http://127.0.0.1:8080 on the host."
  echo ""
  echo "If Caddy reports PUBLIC_DOMAIN is blank, ensure compose is started with:"
  echo "  docker compose --env-file ../.env -f docker-compose.pilot.yml up -d --build"
  exit 1
fi
docker compose --env-file ../.env -f docker-compose.pilot.yml ps
REMOTE

echo ""
echo "Pilot deployed. Open: https://${PUBLIC_DOMAIN}"
echo "Health check: https://${PUBLIC_DOMAIN}/health"
