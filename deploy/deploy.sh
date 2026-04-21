#!/usr/bin/env bash
# =============================================================================
# Corgi Insurance — Blue-Green Deployment Script
# =============================================================================
# Usage:
#   ./deploy/deploy.sh [--slot blue|green] [--image corgi-api:1.2.3]
#   ./deploy/deploy.sh --help
#
# What it does:
#   1. Determine target slot (blue or green — the one NOT currently active)
#   2. Build (or pull) the new image
#   3. Start the new slot container with the new image
#   4. Wait for the health check to pass
#   5. Switch nginx upstream to the new slot (zero-downtime reload)
#   6. Drain the old slot (optional, waits for in-flight requests)
#   7. Stop the old slot container
#   8. On any failure, rolls back to the old slot
#
# Environment variables (can be in .env):
#   CORGI_IMAGE         - Docker image name:tag to deploy (default: build from local Dockerfile)
#   HEALTH_URL          - URL to poll for health check (default: http://localhost/health/)
#   HEALTH_RETRIES      - Number of health check attempts (default: 20)
#   HEALTH_INTERVAL     - Seconds between attempts (default: 5)
#   DRAIN_WAIT          - Seconds to wait for old slot to drain (default: 10)
#   COMPOSE_FILE        - docker-compose file (default: deploy/docker-compose.blue-green.yml)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Defaults ─────────────────────────────────────────────────────────────────
COMPOSE_FILE="${COMPOSE_FILE:-${SCRIPT_DIR}/docker-compose.blue-green.yml}"
HEALTH_URL="${HEALTH_URL:-http://localhost/health/}"
HEALTH_RETRIES="${HEALTH_RETRIES:-20}"
HEALTH_INTERVAL="${HEALTH_INTERVAL:-5}"
DRAIN_WAIT="${DRAIN_WAIT:-10}"
REQUESTED_SLOT=""
CORGI_IMAGE="${CORGI_IMAGE:-}"
BUILD_LOCAL=false

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

log()     { echo -e "${BLUE}[deploy]${NC} $*"; }
success() { echo -e "${GREEN}[deploy]${NC} ✓ $*"; }
warn()    { echo -e "${YELLOW}[deploy]${NC} ⚠ $*"; }
error()   { echo -e "${RED}[deploy]${NC} ✗ $*" >&2; }

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --slot)     REQUESTED_SLOT="$2"; shift 2 ;;
    --image)    CORGI_IMAGE="$2"; shift 2 ;;
    --build)    BUILD_LOCAL=true; shift ;;
    --help|-h)
      sed -n '2,30p' "$0"
      exit 0
      ;;
    *) error "Unknown argument: $1"; exit 1 ;;
  esac
done

# ── Load .env if present ──────────────────────────────────────────────────────
if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  source "${REPO_ROOT}/.env"
  set +a
fi

DC="docker compose -f ${COMPOSE_FILE}"

# ── Determine current active slot ─────────────────────────────────────────────
current_slot() {
  if [[ -f "${SCRIPT_DIR}/nginx-active" ]]; then
    grep -oE '(blue|green)' "${SCRIPT_DIR}/nginx-active" | head -1
  else
    echo "blue"  # default: assume blue is active initially
  fi
}

opposite_slot() {
  [[ "$1" == "blue" ]] && echo "green" || echo "blue"
}

CURRENT=$(current_slot)
if [[ -n "$REQUESTED_SLOT" ]]; then
  TARGET="$REQUESTED_SLOT"
else
  TARGET=$(opposite_slot "$CURRENT")
fi

log "Current active slot: ${CURRENT}"
log "Deploying to slot:   ${TARGET}"

# ── Rollback helper ───────────────────────────────────────────────────────────
rollback() {
  error "Deployment failed! Rolling back to slot: ${CURRENT}"
  switch_to_slot "$CURRENT"
  $DC up -d "api-${CURRENT}"
  error "Rollback complete. Exiting."
  exit 1
}
trap rollback ERR

# ── Build or tag image ────────────────────────────────────────────────────────
if [[ "$BUILD_LOCAL" == true ]] || [[ -z "$CORGI_IMAGE" ]]; then
  log "Building Docker image from ${REPO_ROOT}..."
  TAG="corgi-api:$(git -C "${REPO_ROOT}" rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)"
  docker build -t "$TAG" "${REPO_ROOT}"
  export CORGI_IMAGE="$TAG"
  success "Built image: ${CORGI_IMAGE}"
else
  log "Pulling image: ${CORGI_IMAGE}"
  docker pull "${CORGI_IMAGE}" || warn "Could not pull image — using local cache"
fi

export CORGI_IMAGE

# ── Start the new slot ────────────────────────────────────────────────────────
log "Starting api-${TARGET} with image ${CORGI_IMAGE}..."
$DC up -d "api-${TARGET}"

# ── Wait for health check ─────────────────────────────────────────────────────
wait_healthy() {
  local slot="$1"
  local container
  container="$($DC ps -q "api-${slot}" 2>/dev/null | head -1)"

  log "Waiting for api-${slot} to become healthy (up to $((HEALTH_RETRIES * HEALTH_INTERVAL))s)..."
  for i in $(seq 1 "$HEALTH_RETRIES"); do
    status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
    if [[ "$status" == "healthy" ]]; then
      success "api-${slot} is healthy"
      return 0
    fi
    log "  Attempt ${i}/${HEALTH_RETRIES}: status=${status}"
    sleep "$HEALTH_INTERVAL"
  done

  error "api-${slot} did not become healthy in time"
  return 1
}

wait_healthy "$TARGET"

# ── Switch nginx upstream ─────────────────────────────────────────────────────
switch_to_slot() {
  local slot="$1"
  log "Switching nginx upstream to: ${slot}"
  cp "${SCRIPT_DIR}/nginx-active.${slot}" "${SCRIPT_DIR}/nginx-active"
  $DC exec nginx nginx -s reload
  success "nginx now pointing to: ${slot}"
}

switch_to_slot "$TARGET"

# ── Verify traffic is flowing to new slot ────────────────────────────────────
log "Verifying health after traffic switch..."
for i in $(seq 1 5); do
  if curl -sf "${HEALTH_URL}" > /dev/null 2>&1; then
    success "Health check passed via nginx (${HEALTH_URL})"
    break
  fi
  if [[ $i -eq 5 ]]; then
    error "Health check failed after traffic switch"
    exit 1  # triggers rollback via ERR trap
  fi
  sleep 3
done

# ── Drain old slot ────────────────────────────────────────────────────────────
if [[ "$DRAIN_WAIT" -gt 0 ]]; then
  log "Draining old slot api-${CURRENT} (waiting ${DRAIN_WAIT}s for in-flight requests)..."
  sleep "$DRAIN_WAIT"
fi

# ── Stop old slot ─────────────────────────────────────────────────────────────
log "Stopping old slot: api-${CURRENT}"
$DC stop "api-${CURRENT}"
success "Old slot api-${CURRENT} stopped"

# ── Done ──────────────────────────────────────────────────────────────────────
trap - ERR  # clear rollback trap

success "Deployment complete!"
log ""
log "  Active slot:  ${TARGET}"
log "  Image:        ${CORGI_IMAGE}"
log "  Old slot:     ${CURRENT} (stopped, ready for next deploy)"
log ""
log "To roll back manually: ./deploy/deploy.sh --slot ${CURRENT}"
