#!/usr/bin/env bash
# Install the docker-prune systemd timer on any Dokploy host.
# Run once, as root (or via sudo), from the server:
#
#   sudo bash deploy/maintenance/install.sh
#
# Idempotent — safe to re-run.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "Run as root: sudo bash $0" >&2
    exit 1
fi

install -m 0755 "$HERE/docker-prune.sh" /usr/local/bin/docker-prune.sh
install -m 0644 "$HERE/docker-prune.service" /etc/systemd/system/docker-prune.service
install -m 0644 "$HERE/docker-prune.timer"   /etc/systemd/system/docker-prune.timer

systemctl daemon-reload
systemctl enable --now docker-prune.timer

echo
echo "Installed. Next run:"
systemctl list-timers docker-prune.timer --no-pager
echo
echo "Run on demand:   sudo systemctl start docker-prune.service"
echo "Check log:       tail -f /var/log/docker-prune.log"
