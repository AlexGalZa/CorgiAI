# Corgi Insurance — Blue-Green Deployment

Zero-downtime deployment using two identical API containers (blue/green) behind nginx.

## Overview

```
                 ┌──────────────────────────────────┐
Internet ──────▶ │  nginx (:80/:443)                 │
                 │  upstream: api-active             │
                 └──────────┬──────────────┬─────────┘
                            │              │
                    ┌───────▼───────┐ ┌────▼──────────┐
                    │  api-blue     │ │  api-green     │
                    │  (active)     │ │  (standby)     │
                    └───────────────┘ └────────────────┘
                            │              │
                    ┌───────▼──────────────▼─────────┐
                    │  PostgreSQL + Redis (shared)    │
                    └─────────────────────────────────┘
```

On each deploy:
1. New image is built/pulled
2. The **standby** slot is updated with the new image
3. nginx upstream switches to the new slot (instant, zero-downtime)
4. The old slot is drained and stopped (available for rollback)

## Quick Start

```bash
# First time: create nginx-active symlink
cp deploy/nginx-active.blue deploy/nginx-active

# Start the full stack
docker compose -f deploy/docker-compose.blue-green.yml up -d

# Deploy a new version (auto-detects which slot to use)
./deploy/deploy.sh --image corgi-api:1.2.3

# Build locally and deploy
./deploy/deploy.sh --build

# Force a specific slot
./deploy/deploy.sh --slot green --image corgi-api:1.2.3

# Manual rollback
./deploy/deploy.sh --slot blue
```

## Files

| File | Description |
|------|-------------|
| `docker-compose.blue-green.yml` | Two-slot stack with nginx |
| `nginx.conf` | Nginx config with upstream switching |
| `nginx-active.blue` | Upstream config pointing to blue |
| `nginx-active.green` | Upstream config pointing to green |
| `nginx-active` | Symlink managed by deploy.sh (current active) |
| `deploy.sh` | Zero-downtime deploy script |

## Environment Variables

Copy `.env.example` to `.env` and set:

```
POSTGRES_PASSWORD=...
CORGI_IMAGE=corgi-api:latest        # Default image
HEALTH_URL=http://localhost/health/ # Health check endpoint
HEALTH_RETRIES=20                   # Attempts before giving up
HEALTH_INTERVAL=5                   # Seconds between attempts
DRAIN_WAIT=10                       # Seconds to drain old slot
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

## Health Check

The deploy script polls `/health/` on the new container before switching traffic.
The health endpoint is defined in `api/config/urls.py` and checks DB, Redis, S3, and Stripe.

## Rollback

Rollback is automatic on deploy failure. For manual rollback:

```bash
./deploy/deploy.sh --slot blue   # or green
```

This re-activates the stopped slot (which still has the old image) and switches nginx.
