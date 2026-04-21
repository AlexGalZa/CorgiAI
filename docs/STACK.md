# Tech Stack

## Frontend — Portal

| Technology | Version | Purpose |
|-----------|---------|---------|
| Next.js | 16 | React framework with App Router |
| React | 19 | UI library |
| Tailwind CSS | 4 | Utility-first styling |
| TanStack Query | 5 | Server state management + caching |
| Zustand | 5 | Client state management |
| React Hook Form | 7 | Form handling |
| Zod | 4 | Schema validation |
| clsx | 2 | Conditional classnames |

**Portal capabilities:** PWA support (installable, offline-capable), dark mode with theme toggle, keyboard shortcuts, mobile responsive.

**Custom components:** `CustomSelect` (accessible dropdown), `DatePicker` (date input with calendar), `HelpTooltip` (contextual help).

## Frontend — Admin Dashboard

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 19 | UI library |
| Vite | — | Build tool + dev server |
| Tailwind CSS | 4 | Styling |
| TanStack Query | 5 | Data fetching + caching |
| TanStack Table | 8 | Headless table with sorting, filtering, pagination |
| Recharts | — | Charts and data visualization |
| Lucide React | — | Icon library |
| React Hook Form | 7 | Form handling |
| @hookform/resolvers | 5 | Zod integration for form validation |
| Axios | 1 | HTTP client |
| @dnd-kit | 6 | Drag-and-drop (kanban boards) |
| class-variance-authority | — | Component variant styling |

## Backend — API

| Technology | Version | Purpose |
|-----------|---------|---------|
| Django | 5.1 | Web framework |
| django-ninja | — | Fast API layer (Pydantic schemas, OpenAPI docs) |
| django-unfold | — | Modern admin UI theme |
| django-auditlog | — | Automatic model change tracking |
| django-cors-headers | — | CORS handling |
| django-explorer | — | SQL query tool in admin |
| whitenoise | — | Static file serving |
| gunicorn | — | Production WSGI server |
| psycopg2 | — | PostgreSQL adapter |
| PyJWT | — | JWT token handling |
| stripe | — | Stripe Python SDK |
| boto3 | — | AWS S3 SDK |
| openai | — | OpenAI API client |
| resend | — | Transactional email |
| sentry-sdk | — | Error monitoring |
| python-dotenv | — | Environment variable loading |
| reportlab / pdfrw | — | PDF generation and form filling |
| django-q2 | — | Background job processing (renewal reminders, async tasks) |
| django-ratelimit | — | Request rate limiting (auth endpoints, API) |
| fpdf2 | — | COI PDF generation (consolidated COI, invoice PDF) |
| hubspot-api-client | 8+ | HubSpot CRM sync (contacts, companies, deals) |

## Infrastructure

| Technology | Purpose |
|-----------|---------|
| PostgreSQL 14 | Primary database |
| Redis 7 | Caching + rate limiting |
| Docker + Docker Compose | Local development environment |
| GitHub Actions | CI/CD pipelines (lint.yml, ci.yml, deploy.yml) |
| AWS ECS (Fargate) | API hosting |
| Vercel | Frontend hosting (portal + admin) |
| AWS S3 | Document and file storage |

## Testing

| Technology | Purpose |
|-----------|---------|
| Django TestCase | API unit/integration tests (59 tests across 3 files) |
| Playwright | E2E browser testing for portal flows |
| Vitest | Admin dashboard component/unit tests |

## External Services

| Service | Purpose |
|---------|---------|
| Stripe | Payments (Checkout, Subscriptions, Billing Portal) |
| Resend | Transactional email delivery |
| OpenAI | Business description → industry classification |
| Skyvern | Browser automation for brokered carrier quoting |
| Sentry | Error tracking and performance monitoring |
| HubSpot | CRM sync — contacts, companies, deals (push + pull via webhooks) |
