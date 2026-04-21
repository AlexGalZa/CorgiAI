# Setup Guide

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| **Node.js** | 20+ | `node -v` |
| **Python** | 3.12+ | `python --version` |
| **Docker Desktop** | Latest | `docker --version` |
| **Git** | Latest | `git --version` |

## Quick Start (Recommended)

```powershell
# 1. Clone the repo
git clone https://github.com/corgi-insure/corgi.git
cd corgi

# 2. Copy environment files
copy api\.env.example api\.env
copy admin\.env.example admin\.env
copy portal\.env.example portal\.env.local

# 3. Run the setup script (installs deps, starts DB, runs migrations, seeds data)
.\start.ps1 -setup
```

This single command:
1. Checks all prerequisites
2. Installs Node dependencies for portal and admin
3. Creates a Python virtual environment and installs pip packages
4. Starts PostgreSQL and Redis via Docker
5. Runs Django migrations
6. Seeds coverage form definitions
7. Creates test user accounts
8. Launches all three services

### Selective Start

```powershell
.\start.ps1 -api       # API only
.\start.ps1 -portal    # Portal only
.\start.ps1 -admin     # Admin only
.\start.ps1 -docker    # Full stack via Docker Compose
```

## Running with Docker (Full Stack)

If you want everything containerized:

```powershell
# Copy env files first (see Quick Start step 2)
docker compose up
```

This starts:
- **PostgreSQL 17** on port `5432`
- **Redis 7** on port `6379`
- **API** (Django) on port `8000`
- **Portal** (Next.js) on port `3000`
- **Admin** (Vite + React) on port `3001`

To tear down:
```powershell
docker compose down       # stop services
docker compose down -v    # stop + delete volumes (fresh DB)
```

## Running without Docker (Manual)

### 1. Database & Cache

Start just the infrastructure via Docker:

```powershell
docker compose up -d db redis
```

This starts:
- **PostgreSQL 17** on port `5432` (db: `corgi`, user: `corgi_admin`, password: `Corg1Secure2026x`)
- **Redis 7** on port `6379`

### 2. API (Django)

```powershell
cd api
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt    # includes django-q2, django-ratelimit, fpdf2

# Copy environment file (if not already done)
copy .env.example .env

# Run migrations
python manage.py migrate

# Seed form definitions
python manage.py seed_forms

# Seed platform config (limits, carriers, coverage types, fee rates)
python manage.py seed_platform_config

# Create a superuser
python manage.py createsuperuser
# Suggested: email=admin@corgi.com, password=corgi123

# Start the dev server
python manage.py runserver 0.0.0.0:8000

# In a separate terminal — start background workers (renewal reminders, async tasks)
python manage.py qcluster
```

API runs on [http://localhost:8000](http://localhost:8000).
Django admin at [http://localhost:8000/admin/](http://localhost:8000/admin/).

> **Background workers:** `qcluster` (django-q2) processes scheduled tasks like `send_renewal_reminders`. It requires Redis to be running.

### 3. Portal (Next.js)

```powershell
# One-time: activate pnpm via Node's corepack (ships with Node 20+)
corepack enable
corepack prepare pnpm@9.15.0 --activate

cd portal
pnpm install

# Copy environment file (if not already done)
copy .env.example .env.local

pnpm run dev
```

Runs on [http://localhost:3000](http://localhost:3000).

### 4. Admin Dashboard (Vite + React)

```powershell
cd admin
pnpm install

# Copy environment file (if not already done)
copy .env.example .env

pnpm run dev -- --port 3001
```

Runs on [http://localhost:3001](http://localhost:3001).

## Test Accounts & URLs

| Service | URL | Notes |
|---------|-----|-------|
| Portal | http://localhost:3000 | Customer-facing app |
| Admin | http://localhost:3001 | Internal dashboard |
| API | http://localhost:8000 | Django REST API |
| Django Admin | http://localhost:8000/admin/ | Database admin UI |

### Test Accounts

The seed script (`start.ps1 -setup` or `python manage.py seed_forms`) creates these accounts. All passwords are `corgi123`.

| Email | Role | Access |
|-------|------|--------|
| `admin@corgi.com` | `admin` | Full access — all admin endpoints, Django admin |
| `ae@corgi.com` | `ae` | Account Executive — quotes, policies, clients |
| `ae_underwriting@corgi.com` | `ae_underwriting` | AE + underwriting — approve quotes, endorsements |
| `bdr@corgi.com` | `bdr` | Business Development Rep — leads, pipeline |
| `finance@corgi.com` | `finance` | Finance — billing, commissions, reports |
| `broker@corgi.com` | `broker` | Broker — scoped to assigned organizations |
| `policyholder@corgi.com` | `policyholder` | Customer portal — quotes, policies, claims |
| `sergio@corgi.com` | `policyholder` | Customer portal (additional test account) |

**Staff accounts** (admin, ae, ae_underwriting, bdr, finance, broker) use password login at `POST /api/v1/users/login`.
**Customer accounts** (policyholder) use email OTP login. OTP codes are printed to the Django console in dev mode — no email service needed.

You can also create users manually:
```powershell
python manage.py createsuperuser
```

## Environment Variables

### API (`api/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | — | Django secret key |
| `DJANGO_DEBUG` | `True` | Debug mode |
| `DATABASE_HOST` | `localhost` | PostgreSQL host |
| `DATABASE_PORT` | `5432` | PostgreSQL port |
| `DATABASE_NAME` | `corgi` | Database name |
| `DATABASE_USER` | `corgi_admin` | Database user |
| `DATABASE_PASSWORD` | `Corg1Secure2026x` | Database password |
| `REDIS_URL` | `redis://localhost:6379/1` | Redis connection URL |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed hosts |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:3001` | CORS origins |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:3000,http://localhost:3001` | CSRF trusted origins |
| `JWT_SECRET_KEY` | — | JWT signing key |
| `CORGI_PORTAL_URL` | `http://localhost:3000` | Portal URL for email links |
| `STRIPE_SECRET_KEY` | — | Stripe secret key (optional) |
| `STRIPE_WEBHOOK_SECRET` | — | Stripe webhook signing secret |
| `RESEND_API_KEY` | — | Resend email API key (optional) |
| `S3_ACCESS_KEY_ID` | — | AWS S3 access key |
| `S3_SECRET_ACCESS_KEY` | — | AWS S3 secret key |
| `S3_BUCKET_NAME` | — | S3 bucket name |
| `OPENAI_API_KEY` | — | OpenAI key (AI classification) |
| `ANTHROPIC_API_KEY` | — | Anthropic key (AI classification) |
| `SENTRY_DSN` | — | Sentry error tracking DSN |
| `SKYVERN_API_KEY` | — | Skyvern automation key |
| `HUBSPOT_ACCESS_TOKEN` | — | HubSpot private app token (CRM sync) |
| `HUBSPOT_PIPELINE_ID` | `default` | HubSpot deal pipeline ID |
| `HUBSPOT_WEBHOOK_SECRET` | — | HubSpot webhook client secret |
| `HUBSPOT_STAGE_ACTIVE` | `closedwon` | HubSpot deal stage for active policies |
| `HUBSPOT_STAGE_CANCELLED` | `closedlost` | HubSpot deal stage for cancelled policies |

### Portal (`portal/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API base URL |
| `NEXT_PUBLIC_STRIPE_KEY` | — | Stripe publishable key |
| `NEXT_PUBLIC_SENTRY_DSN` | — | Sentry DSN |

### Admin (`admin/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | API base URL |
| `VITE_SENTRY_DSN` | — | Sentry DSN |

## Common Commands

| Command | Description |
|---------|-------------|
| `python manage.py migrate` | Run database migrations |
| `python manage.py makemigrations` | Create new migrations |
| `python manage.py seed_forms` | Seed/update coverage form definitions |
| `python manage.py createsuperuser` | Create a Django superuser |
| `python manage.py shell` | Django interactive shell |
| `python manage.py runserver` | Start API dev server |
| `pnpm run dev` (in portal/) | Start portal dev server |
| `pnpm run dev -- --port 3001` (in admin/) | Start admin dev server |
| `pnpm run build` (in portal/ or admin/) | Production build |
| `docker compose up` | Start all services |
| `docker compose up -d db redis` | Start infra only |
| `docker compose down` | Stop all services |
| `docker compose down -v` | Stop + delete volumes |
| `python manage.py qcluster` | Start django-q2 background workers |
| `python manage.py send_renewal_reminders` | Send renewal reminder emails (also runs via qcluster) |

## Troubleshooting

### Port Already in Use

```powershell
# Find what's using a port (e.g., 5432)
netstat -ano | findstr :5432

# Kill the process by PID
taskkill /PID <pid> /F
```

Common ports: PostgreSQL (5432), Redis (6379), API (8000), Portal (3000), Admin (3001).

### Database Connection Failed

Make sure Docker is running and the PostgreSQL container is healthy:
```powershell
docker compose ps
docker compose up -d db
```

If you get authentication errors, check that your `api/.env` credentials match `docker-compose.yml`:
- DB: `corgi`, User: `corgi_admin`, Password: `Corg1Secure2026x`

To reset the database completely:
```powershell
docker compose down -v   # removes the volume
docker compose up -d db  # fresh database
cd api && python manage.py migrate && python manage.py seed_forms
```

### Redis Connection Failed

```powershell
docker compose up -d redis
```

Redis is used for rate limiting and caching. The API will still start without it but rate limiting won't work.

### CORS Errors

Make sure `CORS_ALLOWED_ORIGINS` in `api/.env` includes both frontend URLs:
```
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

### CSP (Content Security Policy) Errors

The API sets security headers via `SecurityHeadersMiddleware`. In development, these are relaxed. If you see CSP errors, check `common/middleware.py`.

### OTP Codes Not Arriving

In development, OTP codes are printed to the Django console instead of being emailed. Look for the 6-digit code in the terminal running `python manage.py runserver`.

## Migration Squashing

If fresh deploys are slow due to many migrations:

```bash
# Squash quote migrations
python manage.py squashmigrations quotes 0001 0054

# Squash policy migrations
python manage.py squashmigrations policies 0001 0028

# Squash user migrations
python manage.py squashmigrations users 0001 0015
```

After squashing, test with a fresh database before committing.

### Stripe Not Configured

Stripe is optional for local development. Without `STRIPE_SECRET_KEY`:
- Quote creation and rating work normally
- Checkout URL generation will fail
- Promo code validation will be skipped
- The billing page will show an empty state
