# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENTS                                       │
│  Portal (Next.js)    Admin Dashboard (React)    External Partners    │
│  localhost:3000       localhost:3001              API Key Auth        │
└──────────┬────────────────┬──────────────────────────┬──────────────┘
           │ JWT Auth       │ JWT Auth (staff)          │ API Key Auth
           ▼                ▼                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DJANGO 5.1 + DJANGO-NINJA                        │
│                                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  Quotes   │ │ Policies │ │  Claims  │ │  Certs   │ │   Orgs   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│       │             │            │             │             │        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  Forms   │ │  Admin   │ │ Brokered │ │  Stripe  │ │ External │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│       │             │            │             │             │        │
│  ┌────▼─────────────▼────────────▼─────────────▼─────────────▼────┐  │
│  │                    SERVICE LAYER                                │  │
│  │  QuoteService · PolicyService · ClaimService · CertService     │  │
│  │  RatingService · StripeService · EmailService · S3Service      │  │
│  │  DocumentsGeneratorService · BrokeredService · AIService       │  │
│  │  FormService · OrganizationService · UserService               │  │
│  │  HubSpotSyncService                                            │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─────────────────────────────┐  ┌──────────────────────────────┐  │
│  │      RATING ENGINE          │  │    DJANGO UNFOLD ADMIN        │  │
│  │  rules.py → definitions     │  │  Underwriter workstation      │  │
│  │  service.py → calculate()   │  │  Quote approval, endorsements │  │
│  │  constants.py → tax rates   │  │  Custom products, reporting   │  │
│  └─────────────────────────────┘  └──────────────────────────────┘  │
└──────────────┬──────────────────────────────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼          ▼          ▼
 PostgreSQL   AWS S3    Stripe    Resend     OpenAI    Skyvern   HubSpot
 (data)       (files)   (pay)    (email)     (AI)     (auto)     (CRM)
```

## Component Status

### Portal (Next.js 16) ✅

| Feature | Status |
|---------|--------|
| Auth (email OTP + JWT) | ✅ |
| Dashboard (policies, claims, quotes overview) | ✅ |
| Multi-step quoting flow (7 sections) | ✅ |
| Dynamic coverage questionnaires (Form Builder) | ✅ |
| Coverage selection & packaging | ✅ |
| Quote summary with instant/review split | ✅ |
| Stripe checkout (annual + monthly) | ✅ |
| Certificate management (create, preview, download) | ✅ |
| Claims filing with attachments | ✅ |
| Billing & payment management | ✅ |
| Document center | ✅ |
| Organization management (invites, roles) | ✅ |
| Multi-org support with org switcher | ✅ |
| Dark mode with theme toggle | ✅ |
| PWA support (installable, offline) | ✅ |
| Keyboard shortcuts | ✅ |
| Custom components (Select, DatePicker, HelpTooltip) | ✅ |
| Welcome wizard | ✅ |
| Notification center | ✅ |
| NPS survey | ✅ |
| Mobile responsiveness | ✅ |

### Admin Dashboard (React 19 + Vite) ✅

| Feature | Status |
|---------|--------|
| RBAC with permissions.ts role matrix (7 roles) | ✅ |
| Role-based dashboards (Ops, Finance, BDR, Broker) | ✅ |
| Analytics (pipeline, premium, coverage, claims, loss ratio) | ✅ |
| Quote management (list, detail, approve, recalculate, simulate) | ✅ |
| Policy management (list, detail, endorse, cancel, reactivate) | ✅ |
| Claims management (list, detail, status workflow) | ✅ |
| Brokered requests pipeline (kanban + table views) | ✅ |
| Certificate management | ✅ |
| Commissions page (finance + admin) | ✅ |
| Payment tracking | ✅ |
| Organization management | ✅ |
| Producer management | ✅ |
| User management with impersonation (TTL-limited) | ✅ |
| Audit log viewer | ✅ |
| Reports & exports (CSV export, bulk actions) | ✅ |
| Command palette (Ctrl+K) | ✅ |
| StaffNotifications, UserTimeline, CustomerContextSidebar | ✅ |
| FormBuilder version history | ✅ |
| Impersonation banner | ✅ |

### API (Django 5.1) ✅

| Feature | Status |
|---------|--------|
| JWT authentication with email OTP | ✅ |
| Quote lifecycle (draft → submit → rate → checkout) | ✅ |
| Rating engine (8 coverage types) | ✅ |
| Policy creation from Stripe webhooks | ✅ |
| Policy endorsements (modify, add, remove, backdate) | ✅ |
| Policy cancellation with prorated Stripe refund | ✅ |
| Claims CRUD with file attachments | ✅ |
| Custom certificate generation (PDF) | ✅ |
| Multi-tenant organizations with roles | ✅ |
| Form Builder system (dynamic questionnaires) | ✅ |
| Admin API (split into 5 modules: helpers, analytics, quote_actions, policy_actions, crud) | ✅ |
| RBAC enforcement (7 roles, 42 endpoints) | ✅ |
| SoftDeleteModel mixin (Quote, Policy, Claim) | ✅ |
| Background jobs via django-q2 (renewal reminders) | ✅ |
| Consolidated COI generation (PDF) | ✅ |
| Document ZIP download | ✅ |
| Billing frequency switch | ✅ |
| Invoice PDF generation | ✅ |
| Analytics event tracking | ✅ |
| Account lockout (5 attempts, 30min) | ✅ |
| Webhook authentication | ✅ |
| Correlation IDs in requests | ✅ |
| External partner API with API key auth | ✅ |
| Brokered coverage automation (Skyvern) | ✅ |
| Stripe integration (checkout, subscriptions, billing portal) | ✅ |
| Email notifications (Resend) | ✅ |
| S3 document storage | ✅ |
| AI business classification (OpenAI) | ✅ |
| Audit logging | ✅ |
| Rate limiting | ✅ |
| HubSpot CRM sync (Contact, Company, Deal — push + pull) | ✅ |
| Login event tracking (IP, user agent, method, success/fail) | ✅ |
| PlatformConfig (DB-driven option lists via Django admin) | ✅ |
| Quote binding endpoint | ✅ |
| NAICS code autocomplete | ✅ |

## Core Data Flow

### Quote → Rating → Payment → Policy

```
Customer selects coverages
        │
        ▼
POST /api/v1/quotes/draft
  ├─ Creates Company + Address (blank)
  ├─ Creates Quote (status: draft)
  └─ Returns quote_number
        │
        ▼
PATCH /api/v1/quotes/{number}/step  (repeated per form section)
  ├─ Saves company info, coverage questionnaires, claims history
  └─ Auto-save as user progresses
        │
        ▼
POST /api/v1/quotes/  (final submission)
  ├─ Validates all form data
  ├─ Runs RatingService.calculate() per coverage
  ├─ Tier 1 (instant): → quoted with premium
  ├─ Tier 2/3 (brokered): → needs_review
  └─ Triggers Skyvern for Workers' Comp
        │
        ▼
POST /api/v1/quotes/{number}/checkout
  ├─ Creates Stripe Checkout Session
  ├─ Annual: one-time payment
  └─ Monthly: subscription (×1.111 surcharge ÷12)
        │
        ▼
Stripe webhook → checkout.session.completed
  ├─ Creates Policy per coverage
  ├─ Creates PolicyTransaction + StateAllocation + Cession
  ├─ Generates PDF documents (policy + COI)
  ├─ Uploads to S3
  └─ Sends welcome email
```

## Database Schema

### Core Models

**Quote** (`quotes/models.py`)
- `quote_number`, `status` (draft/submitted/quoted/needs_review/purchased/declined)
- `company` → Company, `user` → User, `organization` → Organization
- `coverages` (JSON list), `coverage_data` (JSON questionnaire answers)
- `limits_retentions` (JSON), `claims_history` (JSON)
- `quote_amount` (Decimal), `rating_result` (JSON breakdown)
- `billing_frequency`, `promo_code`, `form_data_snapshot` (JSON)
- `completed_steps` (JSON), `current_step`, `parent_quote`
- `lead_source` (how the lead was acquired), `assigned_ae` → User (assigned Account Executive)
- Inherits `SoftDeleteModel` — `deleted_at`, `is_deleted`

**Company** (`quotes/models.py`)
- `entity_legal_name`, `organization_type`, `is_for_profit`
- `last_12_months_revenue`, `projected_next_12_months_revenue`
- `business_description`, `business_start_date`
- `is_technology_company`, `federal_ein`
- `full_time_employees`, `part_time_employees`, `estimated_payroll`
- `business_address` → Address

**Policy** (`policies/models.py`) — inherits `SoftDeleteModel`
- `policy_number`, `coi_number`, `status` (active/cancelled/expired)
- `coverage_type`, `premium`, `billing_frequency`
- `effective_date`, `expiration_date`
- `carrier`, `carrier_policy_number`
- `monthly_premium`, `per_occurrence_limit`, `aggregate_limit`, `retention`
- `quote` → Quote, `organization` → Organization

**PolicyTransaction** (`policies/models.py`)
- `transaction_type` (new/endorsement/cancellation/renewal)
- `gross_written_premium`, `accounting_date`

**Claim** (`claims/models.py`) — inherits `SoftDeleteModel`
- `claim_number`, `status` (submitted/under_review/approved/denied/closed)
- `policy` → Policy, `organization` → Organization
- `description`, `claim_report_date`, `date_of_loss`
- `case_reserve_loss`, `case_reserve_lae`, `paid_loss`, `paid_lae`
- `resolution_summary`, `resolved_at`

**CustomCertificate** (`certificates/models.py`)
- `coi_number`, `holder_name`, `holder_address` fields
- `is_additional_insured`, `endorsements` (JSON)
- `status` (active/revoked), `s3_key`

**Organization** (`organizations/models.py`)
- `name`, `is_personal`
- Billing address fields (`billing_street`, `billing_city`, `billing_state`, `billing_zip`)
- Members via `OrganizationMember` (role: owner/editor/viewer)
- Invites via `OrganizationInvite` (code, max_uses, expires_at)

**User** (`users/models.py`)
- `email`, `first_name`, `last_name`, `phone`
- `is_staff`, `role` (admin/ae/ae_underwriting/bdr/finance/broker/policyholder)
- `active_organization` → Organization
- `failed_login_attempts`, `locked_until` (account lockout fields)
- Related: `ImpersonationLog`, `EmailLoginCode`, `UserDocument`

**FormDefinition** (`forms/models.py`)
- `name`, `slug`, `version`, `coverage_type`
- `fields` (JSON), `conditional_logic` (JSON)
- `rating_field_mappings` (JSON), `is_active`

### Supporting Models

- **Payment** (`policies/models.py`) — Stripe payment records
- **StateAllocation** (`policies/models.py`) — premium allocated by state
- **Cession** (`policies/models.py`) — reinsurance cession records (28.3% of GWP)
- **PolicyRenewal** (`policies/models.py`) — renewal tracking
- **CustomProduct** (`quotes/models.py`) — underwriter-priced coverages
- **UnderwriterOverride** (`quotes/models.py`) — manual premium overrides
- **ReferralPartner** (`quotes/models.py`) — referral tracking
- **BrokeredQuoteRequest** (`brokered/models.py`) — Skyvern automation tracking
- **Producer** (`producers/models.py`) — insurance producer records
- **APIKey** (`api_keys/models.py`) — external API authentication
- **AuditLogEntry** (`common/models.py`) — audit trail
- **Notification** (`common/models.py`) — system notifications

## API Endpoints

### Internal API (`/api/v1/`)

#### Users
| Method | Path | Description |
|--------|------|-------------|
| POST | `/users/register` | Create account |
| POST | `/users/request-login-code` | Send OTP email |
| POST | `/users/verify-login-code` | Verify OTP, get JWT |
| POST | `/users/login` | Password login (staff) |
| POST | `/users/refresh` | Refresh JWT tokens |
| GET | `/users/me` | Current user profile |
| GET | `/users/documents` | User's documents |
| GET | `/users/documents/{id}/download` | Document download URL |
| POST | `/users/impersonate/{user_id}` | Start impersonation (admin) |
| POST | `/users/stop-impersonation` | Stop impersonation |

#### Quotes
| Method | Path | Description |
|--------|------|-------------|
| POST | `/quotes/draft` | Create draft quote |
| PATCH | `/quotes/{number}/step` | Save form step |
| POST | `/quotes/` | Submit & rate quote |
| PATCH | `/quotes/{number}/` | Update & re-rate |
| GET | `/quotes/me` | List user's quotes |
| GET | `/quotes/{number}` | Get quote details |
| GET | `/quotes/{number}/form-data` | Get full form data |
| POST | `/quotes/{number}/checkout` | Generate Stripe checkout URL |
| POST | `/quotes/{number}/move` | Move quote to another org |

#### Policies
| Method | Path | Description |
|--------|------|-------------|
| GET | `/policies/me` | List user's policies |
| GET | `/policies/{number}/coi` | Download COI |
| GET | `/policies/recommendations` | Coverage recommendations |
| GET | `/policies/billing` | Billing overview |
| POST | `/policies/billing/portal` | Stripe billing portal URL |

#### Claims
| Method | Path | Description |
|--------|------|-------------|
| POST | `/claims/` | File a claim (multipart) |
| GET | `/claims/me` | List user's claims |
| GET | `/claims/{number}` | Claim details |

#### Certificates
| Method | Path | Description |
|--------|------|-------------|
| POST | `/certificates/custom` | Create custom certificate |
| POST | `/certificates/custom/preview` | Preview PDF (no save) |
| GET | `/certificates/custom` | List certificates (paginated) |
| GET | `/certificates/custom/{id}` | Get certificate |
| DELETE | `/certificates/custom/{id}` | Revoke certificate |
| GET | `/certificates/custom/{id}/download` | Download PDF |
| GET | `/certificates/available-cois` | List available COI numbers |

#### Organizations
| Method | Path | Description |
|--------|------|-------------|
| GET | `/organizations/invite-preview` | Preview invite (no auth) |
| GET | `/organizations/list` | List user's organizations |
| GET | `/organizations/me` | Active org details + members |
| POST | `/organizations/` | Create organization |
| POST | `/organizations/join` | Join via invite code |
| POST | `/organizations/invites` | Create invite |
| POST | `/organizations/invites/{id}/resend` | Resend invite email |
| DELETE | `/organizations/invites/{id}` | Revoke invite |
| PATCH | `/organizations/members/{id}` | Update member role |
| DELETE | `/organizations/members/{id}` | Remove member |
| POST | `/organizations/leave` | Leave organization |

#### Forms (Public)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/forms/{coverage_type}` | Get active form definition |
| POST | `/forms/{coverage_type}/validate` | Validate form submission |
| POST | `/forms/{coverage_type}/visible-fields` | Get visible fields for conditional logic |

#### Brokered
| Method | Path | Description |
|--------|------|-------------|
| POST | `/brokered/{quote}/workers-compensation/callback` | Skyvern WC callback |
| POST | `/brokered/skyvern-callback/` | Skyvern run status callback |

#### Stripe
| Method | Path | Description |
|--------|------|-------------|
| POST | `/stripe/webhook` | Stripe webhook handler |

### Admin API (`/api/v1/admin/`)

All endpoints require staff-level JWT authentication.

#### Analytics
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/analytics/pipeline` | Quote pipeline status counts |
| GET | `/admin/analytics/premium-by-carrier` | Premium aggregated by carrier |
| GET | `/admin/analytics/coverage-breakdown` | Coverage type counts + premium |
| GET | `/admin/analytics/policy-stats` | Active policy count, total/avg premium |
| GET | `/admin/analytics/claims-summary` | Claims by status, reserves, paid |
| GET | `/admin/analytics/action-items` | Blockers, expiring, pending items |
| GET | `/admin/analytics/monthly-premium` | Monthly premium time series (12mo) |
| GET | `/admin/analytics/loss-ratio` | Loss ratio calculation |

#### Quote Actions
| Method | Path | Description |
|--------|------|-------------|
| POST | `/admin/quotes/{id}/recalculate` | Re-run rating engine |
| POST | `/admin/quotes/{id}/approve` | Approve quote + optional email |
| POST | `/admin/quotes/{id}/duplicate` | Clone a quote |
| POST | `/admin/quotes/{id}/simulate` | What-if pricing simulation |

#### Policy Actions
| Method | Path | Description |
|--------|------|-------------|
| POST | `/admin/policies/{id}/endorse` | Midterm endorsement |
| POST | `/admin/policies/{id}/cancel` | Cancel with Stripe refund |
| POST | `/admin/policies/{id}/reactivate` | Reactivate cancelled policy |

#### Audit Log
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/audit-log` | Paginated, filterable audit entries |

#### Forms CRUD
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/forms` | List all form definitions |
| GET | `/admin/forms/{id}` | Get form definition |
| POST | `/admin/forms` | Create form definition |
| PUT | `/admin/forms/{id}` | Update form definition |
| DELETE | `/admin/forms/{id}` | Deactivate form definition |
| POST | `/admin/forms/{id}/duplicate` | Duplicate with new version |

### External API (`/api/external/v1/`)

API key authenticated (`Authorization: Bearer cg_live_...`). Full documentation at `/api/external/v1/docs`.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/invites/{token}/redeem` | Redeem API key invite |
| POST | `/quotes` | Create a quote |
| GET | `/quotes` | List quotes |
| GET | `/quotes/{identifier}` | Get quote details |

## Form Builder System

The Form Builder (`forms/` app) provides dynamic, database-driven questionnaires for each coverage type.

**How it works:**
1. `FormDefinition` records store fields, validation rules, and conditional logic as JSON
2. The portal fetches the active form via `GET /api/v1/forms/{coverage_type}`
3. Conditional logic engine shows/hides fields based on user answers
4. `rating_field_mappings` connect form field keys to rating engine parameters
5. Forms are versioned — multiple versions can exist, only one is active per coverage type

**Management commands:**
- `python manage.py seed_forms` — Seeds/updates all 8 coverage form definitions

## Auth Flow

```
1. User enters email
        │
        ▼
2. POST /users/request-login-code
   → Creates EmailLoginCode (6-digit, 10min expiry)
   → Sends via Resend (or prints to console in dev)
        │
        ▼
3. POST /users/verify-login-code  { email, code }
   → Validates code + expiry
   → Returns { user, tokens: { access, refresh } }
        │
        ▼
4. Frontend stores tokens, sends on every request:
   Authorization: Bearer <access_token>
   X-Organization-Id: <org_id>
        │
        ▼
5. Token refresh: POST /users/refresh { refresh_token }
   → Returns new access + refresh tokens
```

Staff users can also use password login via `POST /users/login`.

## Monorepo Structure (Actual Files)

```
corgi/
├── portal/                    # Next.js 16 customer portal
│   ├── src/app/
│   │   ├── (auth)/            # Login, register, verify-code
│   │   ├── (dashboard)/       # Main dashboard, billing, certificates, claims,
│   │   │                      # documents, organization, quotes
│   │   └── quote/             # Multi-step quoting flow
│   │       └── [quoteNumber]/ # Company info, coverage questionnaires,
│   │                          # claims history, products, summary
│   ├── package.json
│   └── .env.local
│
├── admin/                     # React 19 + Vite ops dashboard
│   ├── src/
│   │   ├── pages/             # 17 pages (Dashboard, Quotes, Policies, Claims,
│   │   │                      # BrokeredRequests, Certificates, Payments,
│   │   │                      # Organizations, Producers, Users, Reports, etc.)
│   │   ├── components/        # brokerage, certificates, claims, dashboards,
│   │   │                      # layout, organizations, payments, producers, ui, users
│   │   ├── hooks/             # useAnalytics, useAuditLog, useBrokeredRequests,
│   │   │                      # useCertificates, useClaims, usePayments, etc.
│   │   └── stores/            # State management
│   ├── package.json
│   └── .env
│
├── api/                       # Django 5.1 + django-ninja
│   ├── config/                # settings.py, urls.py, dashboard.py
│   ├── quotes/                # Quote management + rating
│   ├── policies/              # Policy lifecycle
│   ├── claims/                # Claims CRUD
│   ├── certificates/          # Custom COI generation
│   ├── organizations/         # Multi-tenancy
│   ├── users/                 # Auth + profiles
│   ├── forms/                 # Form Builder
│   ├── admin_api/             # Staff API (5 modules: helpers, analytics, quote_actions, policy_actions, crud)
│   ├── rating/                # Premium calculation engine
│   ├── brokered/              # Skyvern automation
│   ├── external_api/          # Partner API
│   ├── stripe_integration/    # Payment processing
│   ├── emails/                # Transactional emails
│   ├── s3/                    # File storage
│   ├── pdf/                   # PDF utilities
│   ├── documents_generator/   # Policy document generation
│   ├── ai/                    # OpenAI classification
│   ├── common/                # Shared models, middleware, utils
│   ├── producers/             # Producer management
│   ├── api_keys/              # External API key management
│   ├── requirements.txt
│   └── manage.py
│
├── docs/                      # Documentation
├── infra/                     # Infrastructure configs
├── .github/workflows/         # CI (lint.yml, ci.yml) + Deploy (deploy.yml)
├── docker-compose.yml         # Local dev: PostgreSQL + Redis + API + Portal + Admin
└── start.ps1                  # One-command startup
```

## RBAC Architecture

Role-based access control is enforced across all 42 API endpoints.

**Role constants** (defined in `common/constants.py`):
```python
ROLE_ADMIN = "admin"
ROLE_AE = "ae"
ROLE_AE_UNDERWRITING = "ae_underwriting"
ROLE_BDR = "bdr"
ROLE_FINANCE = "finance"
ROLE_BROKER = "broker"
ROLE_POLICYHOLDER = "policyholder"
```

**Key helpers** (in `admin_api/helpers.py`):
- `_require_role(*roles)` — Decorator that checks the user's role and returns 403 if not authorized
- `_scope_queryset_by_role(queryset, user)` — Filters querysets so brokers only see their assigned orgs, AEs see their pipeline, etc.

The admin dashboard reads the role from the JWT and uses `permissions.ts` to show/hide UI based on the role matrix.

## SoftDeleteModel

The `SoftDeleteModel` mixin (in `common/models.py`) adds soft-delete to Quote, Policy, and Claim:
- Adds `deleted_at` (nullable datetime) and `is_deleted` (boolean) fields
- Overrides `delete()` to set `deleted_at` instead of removing the row
- Provides `objects` manager that excludes deleted records by default
- `all_with_deleted` manager includes soft-deleted records for admin use

## Background Jobs (django-q2)

Background task processing via django-q2 with Redis as the broker.

**Management commands:**
- `python manage.py qcluster` — Start the worker process
- `python manage.py send_renewal_reminders` — Send renewal emails (30/60/90 day windows)

**Scheduled tasks:**
- Renewal reminders — runs daily via qcluster schedule
- Future: policy expiration checks, report generation

## DocumentStorage

The `DocumentStorage` class (in `s3/service.py` or `common/storage.py`) provides S3 with local filesystem fallback:
- In production: uploads to S3, returns presigned URLs with configurable TTL
- In development (no S3 keys): falls back to local `media/` directory
- Used by: COI generation, policy documents, claim attachments, certificate PDFs

## Correlation IDs

Every API request gets a unique correlation ID (via middleware). This ID is:
- Included in all log entries for the request
- Returned in the `X-Correlation-Id` response header
- Stored on audit log entries for traceability

## Portal Coverage Page Architecture

The coverage page (`portal/src/components/coverage/`) is split into 9 components:

| Component | Purpose |
|-----------|---------|
| `CoverageOverview.tsx` | Main coverage dashboard layout |
| `CoverageCard.tsx` | Individual coverage type card |
| `CoverageDetails.tsx` | Expanded coverage details view |
| `CoverageLimits.tsx` | Limits and retention display |
| `CoverageDocuments.tsx` | Policy documents for a coverage |
| `CoverageActions.tsx` | Actions (endorse, renew, certificate) |
| `CoverageStatus.tsx` | Status badge and indicators |
| `CoverageComparison.tsx` | Side-by-side coverage comparison |
| `CoverageSummary.tsx` | Aggregate coverage summary |

## Coverage Tier System

### Tier 1 — Instant (rated by Corgi engine)
`commercial-general-liability`, `directors-and-officers`, `technology-errors-and-omissions`, `cyber-liability`, `fiduciary-liability`, `hired-and-non-owned-auto`, `media-liability`, `employment-practices-liability`

### Tier 2 — Brokered with Form
`custom-commercial-auto`, `custom-crime`, `custom-kidnap-ransom`, `custom-med-malpractice`

### Tier 3 — Brokered Intent-Only
`custom-workers-comp`, `custom-bop`, `custom-umbrella`, `custom-excess-liability`

Mixed quotes support partial checkout — instant coverages can be purchased while brokered ones await underwriter review.

## Rating Pipeline

```
Base Premium (revenue × base rate)
  → Limit Factor
  → Retention Factor
  → Risk Multipliers (industry, hazard, AI classification)
  → Split Limit Discount
  → Underwriter Adjustment (if override exists)
  → State Tax (0.5%–5% by state)
  → Stripe Processing Fee (×1.029)
  = Final Premium
```

## Key Constants

| Constant | Value |
|----------|-------|
| Carrier | Technology Risk Retention Group, Inc. |
| Admin Fee Rate | 22% of GWP |
| Reinsurance Cession Rate | 28.3% |
| Attachment Point | $250,000 |
| Monthly Billing Multiplier | ×1.111 |
| Stripe Processing Fee | ×1.029 |
