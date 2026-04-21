# 🐕 Corgi Insurance Platform

Commercial insurance for startups — get quoted in minutes, not weeks.

Corgi is a full-stack insurtech platform that lets technology companies buy commercial insurance online with instant pricing, powered by a custom rating engine and automated underwriting workflows.

## Monorepo Structure

```
corgi/
├── portal/          → Customer-facing app (Next.js 16)
├── admin/           → Internal ops dashboard (React 19 + Vite)
├── api/             → Backend API (Django 5.1 + django-ninja)
├── docs/            → Documentation
├── infra/           → Infrastructure configs
├── .github/         → CI/CD workflows
├── docker-compose.yml
└── start.ps1        → One-command startup script
```

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

## ⚡ One-Click Deployments

### Full Stack (API + Portal + Admin)

Deploy the entire platform with one click. These support Docker or multi-service apps:

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/corgi?referralCode=corgi)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/corgi-insure/corgi)
[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?type=docker&image=ghcr.io/corgi-insure/corgi&name=corgi)
[![Deploy on Northflank](https://northflank.com/button.svg)](https://app.northflank.com/s/account/templates/new?r=https://github.com/corgi-insure/corgi)

| Platform | What You Get | Free Tier |
|----------|-------------|-----------|
| [Railway](https://railway.app) | Full Docker Compose deploy (API + DB + Redis) | $5/mo credit |
| [Render](https://render.com) | 3 services + managed Postgres | 512MB RAM, spins down after 15m |
| [Koyeb](https://koyeb.com) | Docker deploy with global edge | 1 free Nano (512MB), 24/7 uptime |
| [Northflank](https://northflank.com) | 2 free services + 1 cron job | Permanent free tier |

### Portal Only (Static/SSR Frontend)

Deploy just the customer portal (`/portal`) — connects to your API wherever it's hosted:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/corgi-insure/corgi&root-directory=portal&env=NEXT_PUBLIC_API_URL)
[![Deploy to Netlify](https://www.netlify.com/img/deploy/button.svg)](https://app.netlify.com/start/deploy?repository=https://github.com/corgi-insure/corgi&base=portal)
[![Deploy to Cloudflare Pages](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/corgi-insure/corgi&projectName=corgi-portal&rootDirectory=portal)

| Platform | Free Tier | Notes |
|----------|-----------|-------|
| [Vercel](https://vercel.com) | 100GB bandwidth, unlimited repos | Best for Next.js — zero config |
| [Netlify](https://netlify.com) | 100GB bandwidth, 300 build mins/mo | Edge functions included |
| [Cloudflare Pages](https://pages.cloudflare.com) | Unlimited bandwidth & sites | Fastest global CDN |

### Admin Dashboard Only (Static SPA)

Deploy just the ops dashboard (`/admin`) — lightweight Vite React app:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/corgi-insure/corgi&root-directory=admin&env=VITE_API_URL)
[![Deploy to Surge](https://img.shields.io/badge/deploy-surge.sh-333?style=for-the-badge)](https://surge.sh)
[![Deploy to GitHub Pages](https://img.shields.io/badge/deploy-GitHub%20Pages-222?style=for-the-badge&logo=github)](https://pages.github.com)

| Platform | Free Tier | Notes |
|----------|-----------|-------|
| [Vercel](https://vercel.com) | 100GB bandwidth | Works great for Vite apps |
| [Surge.sh](https://surge.sh) | Unlimited sites, custom domains | Static only, instant deploys |
| [GitHub Pages](https://pages.github.com) | Free for public repos | Static only, via GitHub Actions |
| [Kinsta](https://kinsta.com) | 100 static sites free | Global CDN included |

### API Only (Django Backend)

Deploy just the backend (`/api`) with a database:

| Platform | Deploy | Free Tier |
|----------|--------|-----------|
| [Railway](https://railway.app) | [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/corgi-api) | $5/mo credit, managed Postgres |
| [Render](https://render.com) | [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy) | Free Postgres (90 days), 512MB RAM |
| [Koyeb](https://koyeb.com) | Docker | 1 Nano instance free |
| [Back4App](https://back4app.com) | Containers | 250MB storage, 10k req |
| [Adaptable.io](https://adaptable.io) | Zero-config | Free for Node/Python + Postgres |
| [Supabase](https://supabase.com) | DB only | 500MB Postgres, use with any host |

### Docker Self-Host

Run everywhere with Docker Compose:

```bash
git clone https://github.com/corgi-insure/corgi.git
cd corgi
docker compose up -d
```

Services start at:
- Portal: `http://localhost:3000`
- API: `http://localhost:8000`
- Admin: `http://localhost:3001`

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
