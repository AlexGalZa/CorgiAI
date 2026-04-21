#!/usr/bin/env bash
# Prune unused Docker images, stopped containers, and BuildKit cache older
# than the retention window. Named volumes (DB state, pnpm cache) are kept.
#
# Run as root (systemd timer) or via sudo. Logs to /var/log/docker-prune.log.
#
# Override retention via env: DOCKER_PRUNE_RETENTION=336h (14 days), etc.
set -euo pipefail

RETENTION="${DOCKER_PRUNE_RETENTION:-168h}"   # 7 days default
LOG="${DOCKER_PRUNE_LOG:-/var/log/docker-prune.log}"

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*" | tee -a "$LOG"; }

log "Starting Docker prune (retention=$RETENTION)"
log "Disk before:"
df -h / | tee -a "$LOG"

log "Pruning unused images older than $RETENTION"
docker image prune -af --filter "until=$RETENTION" 2>&1 | tee -a "$LOG"

log "Pruning stopped containers older than $RETENTION"
docker container prune -f --filter "until=$RETENTION" 2>&1 | tee -a "$LOG"

log "Pruning BuildKit cache older than $RETENTION"
docker builder prune -af --filter "until=$RETENTION" 2>&1 | tee -a "$LOG"

log "Pruning dangling networks"
docker network prune -f --filter "until=$RETENTION" 2>&1 | tee -a "$LOG"

log "Disk after:"
df -h / | tee -a "$LOG"
log "Prune complete"
