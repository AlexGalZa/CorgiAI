# Backend Setup Guide

## Prerequisites

- **Python 3.12+**
- **PostgreSQL 14+** (or Docker for local DB)
- **Docker Desktop** (for local PostgreSQL + Redis)
- **pip** or **pipenv**

## Quick Start

### 1. Database

```bash
# Option A: Docker (recommended)
docker compose up -d db redis   # PostgreSQL on 5432, Redis on 6379
# DB: corgi, User: corgi_admin, Password: Corg1Secure2026x

# Option B: Local PostgreSQL
createdb corgi
```

### 2. Python Environment

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Variables

The `.env` file is pre-configured for local development. No changes needed to get started.

Key variables (all optional for local dev):

| Variable | Purpose | Required locally? |
|----------|---------|-------------------|
| `DJANGO_SECRET_KEY` | Django secret | ✅ (has default) |
| `DATABASE_*` | PostgreSQL connection | ✅ (has defaults) |
| `JWT_SECRET_KEY` | JWT signing | ✅ (has default) |
| `STRIPE_SECRET_KEY` | Payments | ❌ (checkout won't work) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhooks | ❌ |
| `S3_ACCESS_KEY_ID` | File uploads | ❌ (uploads won't work) |
| `RESEND_API_KEY` | Transactional emails | ❌ (emails won't send) |
| `OPENAI_API_KEY` | AI classification | ❌ (AI features disabled) |
| `SKYVERN_API_KEY` | WC automation | ❌ |
| `SENTRY_DSN` | Error tracking | ❌ |

### 4. Migrate & Run

```bash
python manage.py migrate
python manage.py seed_forms         # seed coverage form definitions
python manage.py createsuperuser    # follow prompts (use corgi123 as password)
python manage.py runserver

# In a separate terminal — start background workers
python manage.py qcluster
```

- **API**: http://localhost:8000/api/v1/
- **Admin Panel**: http://localhost:8000/admin/
- **External API Docs**: http://localhost:8000/api/external/v1/docs
- **Health Check**: http://localhost:8000/health/

### Test Accounts

All passwords are `corgi123`:

| Email | Role | Access |
|-------|------|--------|
| `admin@corgi.com` | `admin` | Full access |
| `ae@corgi.com` | `ae` | Account Executive |
| `ae_underwriting@corgi.com` | `ae_underwriting` | AE + Underwriting |
| `bdr@corgi.com` | `bdr` | Business Development |
| `finance@corgi.com` | `finance` | Finance |
| `broker@corgi.com` | `broker` | Broker (scoped) |
| `policyholder@corgi.com` | `policyholder` | Customer portal |
| `sergio@corgi.com` | `policyholder` | Customer portal |

## Running Tests

```bash
python manage.py test                    # all tests
python manage.py test quotes.tests       # specific app
python manage.py test --verbosity=2      # verbose output
```

## Common Commands

```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Open Django shell
python manage.py shell

# Start background workers (django-q2)
python manage.py qcluster

# Send renewal reminder emails
python manage.py send_renewal_reminders

# Backfill cessions (reinsurance records)
python manage.py backfill_cessions --dry-run
python manage.py backfill_cessions

# Collect static files (for production)
python manage.py collectstatic
```

## Admin Panel Access

1. Create a superuser: `python manage.py createsuperuser`
2. Go to http://localhost:8000/admin/
3. Login with your superuser credentials

### Key Admin Workflows

- **Quotes** → View/approve quotes, add custom products, simulate rating
- **Policies** → Manage endorsements, cancellations, premium reports
- **Claims** → Review and manage claims
- **Users** → Manage users, upload documents
- **API Keys** → Create external API keys for partners

## Project Structure

```
backend/
├── ai/                 # AI classification (OpenAI)
├── api_keys/           # External API key management
├── brokered/           # Brokered coverage automation (Skyvern)
├── certificates/       # Custom certificate generation
├── claims/             # Claims management
├── common/             # Shared utilities, base models, constants
├── config/             # Django settings, URLs, WSGI
├── documents_generator/# PDF policy document generation
├── emails/             # Transactional email service (Resend)
├── external_api/       # External partner API
├── organizations/      # Multi-tenant org management
├── pdf/                # PDF manipulation utilities
├── policies/           # Policy lifecycle management
├── producers/          # Producer/agent management
├── quotes/             # Quote creation, rating, checkout
├── rating/             # Premium calculation engine
├── s3/                 # AWS S3 file storage
├── scripts/            # Management commands
├── skyvern/            # Skyvern browser automation client
├── stripe_integration/ # Stripe payments
├── templates/          # Email, PDF, admin templates
├── users/              # User auth, documents
└── webhooks/           # Webhook processing
```
