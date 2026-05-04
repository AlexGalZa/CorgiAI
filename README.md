# 🐕 Corgi Insurance Platform

Commercial insurance for startups — get quoted in minutes, not weeks.

Corgi is a full-stack insurtech platform that lets technology companies buy commercial insurance online with instant pricing, powered by a custom rating engine and automated underwriting workflows.

## Monorepo Structure

```
corgi/
├── portal/          → Customer-facing app (Next.js 16)
├── admin/           → Shepherd: internal ops dashboard for the closing team (React 19 + Vite)
├── api/             → Backend API (Django 5.1 + django-ninja)
├── deploy/          → Deploy assets (compose overrides, scripts)
├── docs/            → Documentation
├── e2e/             → Playwright end-to-end tests
├── .github/         → CI/CD workflows
├── docker-compose.yml
└── start.ps1        → One-command local startup script
```

> **About `admin/`:** this is **Shepherd** — the internal sales-acceleration tool for the team that closes Corgi deals. It is not a customer-facing surface. A full rename of the directory to `shepherd/` is planned in a follow-up PR.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Portal** | Next.js 16, React 19, Tailwind CSS 4, TanStack Query, Zustand, Zod |
| **Admin** | React 19, Vite, Tailwind CSS 4, TanStack Query + Table, Recharts, Lucide, React Hook Form |
| **API** | Django 5.1, django-ninja, django-unfold (admin UI), django-auditlog |
| **Database** | PostgreSQL 14 |
| **Cache** | Redis 7 |
| **Payments** | Stripe (Checkout, Subscriptions, Billing Portal) |
| **Email** | Resend |
| **Storage** | AWS S3 |
| **AI** | OpenAI (business classification) |
| **Automation** | Skyvern (brokered carrier quoting) |
| **Monitoring** | Sentry |

## Quick Start

```powershell
.\start.ps1 -setup
```

This installs all dependencies, starts Docker services (PostgreSQL + Redis), runs migrations, seeds test data, and launches all three services.

### Manual Setup

See [docs/SETUP.md](docs/SETUP.md) for step-by-step instructions.

### Test Accounts

| Email | Password | Role | Access |
|-------|----------|------|--------|
| `sergio@corgi.com` | `corgi123` | Customer | Portal only |
| `admin@corgi.com` | `corgi123` | Admin | Full admin + Django |
| `ae@corgi.com` | `corgi123` | Account Executive | Operations |
| `aeu@corgi.com` | `corgi123` | AE + Underwriting | Operations + overrides |
| `bdr@corgi.com` | `corgi123` | BDR | Pipeline view |
| `finance@corgi.com` | `corgi123` | Finance | Payments + commissions |
| `broker@corgi.com` | `corgi123` | Broker | Own referrals only |
| `123` | `corgi123` | Superuser | Everything |

> Staff accounts use password login. Customer accounts use email OTP (codes printed to API console in dev).
> Staff accounts are blocked from the customer portal. Customer accounts are blocked from admin.

### URLs

| Service | URL |
|---------|-----|
| Portal | [http://localhost:3000](http://localhost:3000) |
| API | [http://localhost:8000](http://localhost:8000) |
| Admin Dashboard | [http://localhost:3001](http://localhost:3001) |
| Django Admin | [http://localhost:8000/admin/](http://localhost:8000/admin/) |
| API Docs (External) | [http://localhost:8000/api/external/v1/docs](http://localhost:8000/api/external/v1/docs) |

## Deployment

The repo previously listed eight one-click deploy buttons (Railway, Render, Koyeb, Northflank, Netlify, Cloudflare Pages, Surge, GitHub Pages). None pointed at a configured production deployment. Those have been removed in favor of one supported path per surface.

| Surface | Target | Notes |
|---------|--------|-------|
| **Portal** (customer-facing) | Vercel | Configured via `vercel.json`, root directory `portal/`. Set `NEXT_PUBLIC_API_URL`. |
| **Shepherd** (internal, `admin/`) | TBD — Railway or Render with team auth | Must be auth-gated; not for public access. Set `VITE_API_URL`. |
| **API** (Django) | Docker — Railway/Render/Fly with managed Postgres + Redis | See `docker-compose.yml` and `Dockerfile`. |

### Local development (Docker)

```powershell
git clone https://github.com/AlexGalZa/CorgiAI.git
cd CorgiAI
docker compose up -d
```

Services start at:
- Portal: `http://localhost:3000`
- API: `http://localhost:8000`
- Shepherd (admin): `http://localhost:3001`

### Environment Variables

All deployments need these set for the API:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_NAME` | ✅ | PostgreSQL database name |
| `DATABASE_USER` | ✅ | PostgreSQL user |
| `DATABASE_PASSWORD` | ✅ | PostgreSQL password |
| `DATABASE_HOST` | ✅ | PostgreSQL host |
| `DJANGO_SECRET_KEY` | ✅ | Django secret key |
| `JWT_SECRET_KEY` | ✅ | JWT signing key |
| `STRIPE_SECRET_KEY` | For payments | Stripe API key |
| `RESEND_API_KEY` | For emails | Resend API key |
| `OPENAI_API_KEY` | For AI features | OpenAI API key |
| `HUBSPOT_ACCESS_TOKEN` | For CRM sync | HubSpot private app token |
| `HUBSPOT_PIPELINE_ID` | For CRM sync | HubSpot deal pipeline ID |
| `HUBSPOT_WEBHOOK_SECRET` | For CRM sync | HubSpot webhook client secret |

Frontends need:
| Variable | Service | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | Portal | API base URL |
| `VITE_API_URL` | Admin | API base URL |

## Documentation

- [Setup Guide](docs/SETUP.md) — prerequisites, installation, environment variables
- [Architecture](docs/ARCHITECTURE.md) — system design, data flow, app structure
- [API Reference](docs/API.md) — all endpoints with request/response examples
- [Deployment](docs/DEPLOYMENT.md) — Docker, CI/CD, cloud deployment
- [Tech Stack](docs/STACK.md) — detailed technology choices and rationale
