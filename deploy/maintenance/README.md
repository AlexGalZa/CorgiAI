# Docker prune — weekly server-side cleanup

Reclaims disk on any Dokploy host by removing images, containers, and
BuildKit cache older than the retention window. Keeps named volumes
(Postgres, pnpm build cache) intact.

## Install (once, on the server)

SSH into the host, then:

```bash
cd /path/to/corgi          # wherever the repo lives on the server
sudo bash deploy/maintenance/install.sh
```

The installer copies the script to `/usr/local/bin/`, registers a systemd
service + weekly timer (Sun 03:00 local, ±30min jitter), and enables it.

## What it does

Runs `docker image prune -af --filter until=168h` +
`docker container prune -f --filter until=168h` +
`docker builder prune -af --filter until=168h` +
`docker network prune -f --filter until=168h`.

Logs to `/var/log/docker-prune.log` with disk-free before/after.

## Adjust retention

Default is 7 days (`168h`). Change via systemd drop-in:

```bash
sudo systemctl edit docker-prune.service
# add:
# [Service]
# Environment="DOCKER_PRUNE_RETENTION=336h"   # 14 days
```

## Run on demand

```bash
sudo systemctl start docker-prune.service
journalctl -u docker-prune.service -f
```

## Uninstall

```bash
sudo systemctl disable --now docker-prune.timer
sudo rm /etc/systemd/system/docker-prune.{service,timer}
sudo rm /usr/local/bin/docker-prune.sh
sudo systemctl daemon-reload
```
