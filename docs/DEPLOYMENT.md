# Deployment

## One-Click Deploy

The repo includes config files for one-click deployment:

| Platform | Config File | What it deploys |
|----------|-------------|-----------------|
| Railway | `railway.toml` | API + PostgreSQL + Redis |
| Render | `render.yaml` | API + Portal + Admin + DB |
| Vercel | `vercel.json` | Portal and Admin frontends |
| Netlify | `netlify.toml` | Portal and Admin frontends |

Check each file for the latest deploy configuration.

## Docker Setup

The project includes three Dockerfiles and a `docker-compose.yml` for local development.

### Dockerfiles

**`api/Dockerfile`** — Django API
- Python 3.12 base image
- Installs requirements.txt
- Runs via `entrypoint.sh` (migrations + gunicorn)

**`portal/Dockerfile`** — Next.js Portal
- Node.js base with multi-stage build
- Build arg: `NEXT_PUBLIC_API_URL`
- Runs `next start` on port 3000

**`admin/Dockerfile`** — React Admin Dashboard
- Multi-stage: Node build → nginx static serve
- Build arg: `VITE_API_URL`
- Serves built assets via nginx on port 80
- Config: `admin/nginx.conf`

### Local Development with Docker Compose

```powershell
# Start everything
docker-compose up -d

# Start only infrastructure (DB + Redis)
docker-compose up -d db redis

# Rebuild after code changes
docker-compose up -d --build

# View logs
docker-compose logs -f api

# Stop everything
docker-compose down
```

**Services in `docker-compose.yml`:**

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `db` | postgres:14-alpine | 5432 | PostgreSQL database |
| `redis` | redis:7-alpine | 6379 | Cache + rate limiting |
| `api` | ./api (build) | 8000 | Django API |
| `portal` | ./portal (build) | 3000 | Next.js portal |
| `admin` | ./admin (build) | 3001→80 | React admin dashboard |

Volume: `pgdata` for persistent PostgreSQL data.

**Docker DB credentials:** `corgi_admin` / `Corg1Secure2026x` / database `corgi`.

## CI/CD Pipelines

### GitHub Actions

**`.github/workflows/lint.yml`** — Linting
- Triggered on push/PR
- Runs ESLint, Prettier, and type checks for portal and admin
- Runs `ruff` and `mypy` for the API

**`.github/workflows/ci.yml`** — Continuous Integration
- Triggered on push/PR to main
- Runs 59 tests across 3 test files (quotes, policies, admin_api)
- Runs linting and type checks for portal and admin
- Builds Docker images to verify they compile

**`.github/workflows/deploy.yml`** — Deployment
- Triggered on push to main (after CI passes)
- Deploys portal and admin to Vercel
- Deploys API to AWS ECS

## Production Deployment

### Portal + Admin → Vercel

Both frontend apps deploy to Vercel:

```bash
# Portal
cd portal
vercel --prod

# Admin
cd admin
vercel --prod
```

**Environment variables to set in Vercel:**
- Portal: `NEXT_PUBLIC_API_URL` → production API URL
- Admin: `VITE_API_URL` → production API URL

### API → AWS ECS

The API runs as a Docker container on AWS ECS (Fargate):

1. Build and push image to ECR
2. Update ECS task definition
3. Deploy new task revision

**Required AWS resources:**
- ECS Cluster + Service + Task Definition
- ECR Repository
- RDS PostgreSQL instance
- ElastiCache Redis
- Application Load Balancer
- S3 bucket for documents
- Secrets Manager for environment variables

### Production Environment Variables

**API (ECS Task Definition / Secrets Manager):**

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Strong random secret |
| `DJANGO_DEBUG` | `False` |
| `DATABASE_HOST` | RDS endpoint |
| `DATABASE_PORT` | `5432` |
| `DATABASE_NAME` | Production DB name |
| `DATABASE_USER` | Production DB user |
| `DATABASE_PASSWORD` | Production DB password |
| `REDIS_URL` | ElastiCache endpoint |
| `ALLOWED_HOSTS` | Production domain(s) |
| `CORS_ALLOWED_ORIGINS` | Production frontend URLs |
| `CSRF_TRUSTED_ORIGINS` | Production frontend URLs |
| `STRIPE_SECRET_KEY` | Stripe live secret key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `RESEND_API_KEY` | Resend API key |
| `AWS_ACCESS_KEY_ID` | S3 access key |
| `AWS_SECRET_ACCESS_KEY` | S3 secret key |
| `AWS_STORAGE_BUCKET_NAME` | S3 bucket name |
| `OPENAI_API_KEY` | OpenAI API key |
| `SENTRY_DSN` | Sentry DSN |
| `SKYVERN_API_KEY` | Skyvern API key |

**Portal (Vercel):**

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Production API URL (e.g., `https://api.corgi.insure`) |

**Admin (Vercel):**

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Production API URL |

## Health Check

The API exposes a health endpoint:

```
GET /health/
→ { "status": "ok" }
```

Used by Docker healthchecks and ALB target group health checks.

## Post-Deploy Checklist

After deploying a new version:

1. **Run migrations:** `python manage.py migrate`
2. **Seed form definitions:** `python manage.py seed_forms`
3. **Start background workers:** `python manage.py qcluster` (ensure it's running as a process/service)
4. **Verify health:** `curl https://api.corgi.insure/health/`
5. **Check Stripe webhooks:** Ensure the webhook endpoint is configured and receiving events
6. **Verify CORS:** Confirm `CORS_ALLOWED_ORIGINS` includes all frontend domains
7. **Run renewal reminders:** `python manage.py send_renewal_reminders` (or verify qcluster schedule)
