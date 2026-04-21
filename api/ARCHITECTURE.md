# Backend Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENTS                                       │
│   Next.js Portal (app.corgi.insure)    External Partners (API)       │
└──────────────┬──────────────────────────────────┬───────────────────┘
               │ JWT Auth                         │ API Key Auth
               ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DJANGO + DJANGO-NINJA                            │
│                                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  Quotes   │ │ Policies │ │  Claims  │ │  Certs   │ │   Orgs   │  │
│  │  /api/v1/ │ │ /api/v1/ │ │ /api/v1/ │ │ /api/v1/ │ │ /api/v1/ │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│       │             │            │             │             │        │
│  ┌────▼─────────────▼────────────▼─────────────▼─────────────▼────┐  │
│  │                    SERVICE LAYER                                │  │
│  │  QuoteService · PolicyService · ClaimService · CertService     │  │
│  │  RatingService · StripeService · EmailService · S3Service      │  │
│  │  DocumentsGeneratorService · BrokeredService · AIService       │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─────────────────────────────┐  ┌──────────────────────────────┐  │
│  │      RATING ENGINE          │  │       DJANGO ADMIN            │  │
│  │  rules.py → definitions     │  │  Underwriter workstation      │  │
│  │  service.py → calculate()   │  │  Quote approval, endorsements │  │
│  │  constants.py → tax rates   │  │  Custom products, reporting   │  │
│  └─────────────────────────────┘  └──────────────────────────────┘  │
└──────────────┬──────────────────────────────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼          ▼          ▼
 PostgreSQL   AWS S3    Stripe    Resend     OpenAI    Skyvern
 (data)       (files)   (pay)    (email)     (AI)     (auto)
```

## Core Data Flow

### 1. Quote Creation → Rating → Payment → Policy

```
Customer fills form
        │
        ▼
QuoteService.create_quote()
  ├─ Creates/updates Company + Address
  ├─ Creates Quote (status: submitted)
  ├─ Triggers BrokeredService for WC if selected
  └─ Returns quote_number
        │
        ▼
QuoteService.process_quote_rating()
  ├─ For each coverage:
  │   ├─ Tier 1 (instant): RatingService.calculate()
  │   ├─ Tier 2/3 (brokered): → needs_review
  │   └─ Check UnderwriterOverrides
  ├─ If all pass → status: quoted, quote_amount set
  └─ If any fail → status: needs_review, email sent
        │
        ▼
QuoteService.create_checkout_url()
  ├─ PolicyService.create_payment_link()
  │   ├─ Builds Stripe line items per coverage
  │   ├─ Annual: one-time Stripe Checkout
  │   └─ Monthly: subscription Stripe Checkout
  └─ Returns Stripe URL
        │
        ▼
Customer pays on Stripe
        │
        ▼
Stripe webhook → webhooks/service.py
  ├─ checkout.session.completed
  │   ├─ PolicyService.handle_checkout_completed()
  │   ├─ Creates Policy per coverage
  │   ├─ Creates PolicyTransaction (new business)
  │   ├─ Creates StateAllocation
  │   ├─ Creates Cession (non-brokered only)
  │   ├─ Creates Payment record
  │   ├─ Generates PDF documents (policy + COI)
  │   ├─ Uploads to S3
  │   ├─ Creates UserDocument records
  │   └─ Sends welcome email with docs
  └─ invoice.paid (monthly billing)
      └─ Creates Payment record
```

## Django Apps

### `quotes/` — Quote Management
The central app. Handles quote creation, step-by-step form saving, rating orchestration, and checkout.

| File | Purpose |
|------|---------|
| `models.py` | Quote (+ `lead_source`, `assigned_ae`), Company, Address, CustomProduct, UnderwriterOverride, ReferralPartner |
| `service.py` | QuoteService — create, save steps, rate, checkout, split for partial purchase |
| `api.py` | Internal API endpoints for the portal |
| `admin.py` | Underwriter workstation (approve, simulate, custom products) |
| `constants.py` | Coverage type mappings, form field keys |
| `schemas.py` | Pydantic schemas for rating results, API I/O |

### `rating/` — Premium Calculation Engine
Pure calculation logic. No database access.

| File | Purpose |
|------|---------|
| `service.py` | `RatingService.calculate()` — the main entry point |
| `rules.py` | Coverage definitions (base rates, factors, limits) |
| `constants.py` | State tax rates, multipliers, fee rates |
| `schemas.py` | CalculationResult, CalculationContext |

**Rating Pipeline:**
```
Base Premium (revenue × base rate)
  → Limit Factor (from limit tables)
  → Retention Factor (from retention tables)
  → Risk Multipliers (industry, hazard class, AI from questionnaire)
  → Split Limit Discount (if per_occ < aggregate)
  → Underwriter Adjustment (multiplier from override)
  → State Tax (state-specific rate, 0.5%–5%)
  → Stripe Processing Fee (×1.029)
  = Final Premium (stored in rating_result)
```

### `policies/` — Policy Lifecycle
Manages policies from creation through endorsements to expiration.

| File | Purpose |
|------|---------|
| `models.py` | Policy, Payment, PolicyTransaction, StateAllocation, Cession |
| `service.py` | PolicyService — create from checkout, endorsements, cancellations, renewals |
| `admin.py` | Policy management (endorse, cancel, reports, send documents) |
| `sequences.py` | Policy number generation (format: `XX-ST-YY-NNNNNN-01`) |

**Endorsement types** (admin-only, all prorated):
- Modify limits → recalculate premium, Stripe charge/refund delta
- Add coverage → new policy, Stripe charge prorated
- Remove coverage → Stripe refund prorated, policy cancelled

### `claims/` — Claims Management
Simple CRUD with status workflow.

| File | Purpose |
|------|---------|
| `models.py` | Claim, ClaimDocument |
| `service.py` | ClaimService — file claim, list claims |
| `api.py` | Internal claim filing endpoints |

**Status flow:** `submitted → under_review → approved/denied → closed`

### `certificates/` — Certificate of Insurance
Generates custom COI documents with holder information and endorsements.

| File | Purpose |
|------|---------|
| `models.py` | CustomCertificate with endorsement types |
| `service.py` | CertificateService — create, regenerate PDFs |
| `api.py` | CRUD endpoints |

### `organizations/` — Multi-Tenancy
All data is org-scoped. Every user gets a personal org on registration.

| File | Purpose |
|------|---------|
| `models.py` | Organization (+ billing address fields), OrganizationMember, OrganizationInvite |
| `service.py` | OrganizationService — role checks, active org, invites |
| `api.py` | Org management, member invites |

**Roles:** `owner` (full control) → `editor` (create/edit) → `viewer` (read only)

### `users/` — Authentication
JWT-based auth with email OTP login, password login (staff), and account lockout.

| File | Purpose |
|------|---------|
| `models.py` | User (+ lockout fields: `failed_login_attempts`, `locked_until`), ImpersonationLog, PasswordResetCode, EmailLoginCode, UserDocument |
| `service.py` | UserService — register, login, OTP, password reset, lockout enforcement |
| `auth.py` | JWT token creation/verification, auth middleware |
| `api.py` | Auth endpoints (register, login, verify, refresh) |

**Account lockout:** 5 failed attempts → 30 minute lockout. Tracked on User model.
**Impersonation TTL:** Impersonation sessions expire after a configurable duration.

### `stripe_integration/` — Payments
Wraps the Stripe API for checkout sessions, subscriptions, and webhooks.

| File | Purpose |
|------|---------|
| `service.py` | StripeService — create checkouts, manage subscriptions, promo codes |
| `api.py` | Webhook endpoint, billing portal |

### `rating/` — Premium Calculation
Pure math engine. Takes company data + questionnaire answers → premium.

### `documents_generator/` — PDF Generation
Assembles policy documents from PDF templates by filling form fields.

| File | Purpose |
|------|---------|
| `service.py` | DocumentsGeneratorService — generate policy bundles, COIs, questionnaire text |
| `constants.py` | Template file paths, coverage → PDF mapping |
| `questionnaire_labels.py` | Human-readable labels for form fields |

### `brokered/` — Brokered Coverage Automation
Handles non-instant coverages that need external carrier quotes.

| File | Purpose |
|------|---------|
| `models.py` | BrokeredQuoteRequest |
| `service.py` | BrokeredService — trigger Skyvern automation, handle callbacks |
| `api.py` | Webhook endpoint for Skyvern callbacks |

**Workers' Comp flow:**
```
Customer selects WC → BrokeredService.trigger_workers_compensation()
  → Skyvern Cloud runs Pie Insurance portal automation
  → Callback to /api/v1/brokered/skyvern-callback/
  → Creates CustomProduct + UnderwriterOverride
  → Re-rates quote → status may become "quoted"
```

### `external_api/` — Partner API
Separate NinjaAPI instance with API key auth. Partners can create quotes and retrieve results.

| File | Purpose |
|------|---------|
| `api.py` | External endpoints (create quote, list quotes, get quote) |
| `auth.py` | API key authentication |
| `schemas.py` | External-facing Pydantic schemas |

### `ai/` — AI Classification
Uses OpenAI to classify business descriptions into industry groups and hazard classes.

### `emails/` — Email Service
Sends transactional emails via Resend API.

**Emails sent:**
| Trigger | Template |
|---------|----------|
| User registers | `welcome.html` |
| Login OTP requested | `login_otp.html` |
| Password reset | `password_reset.html` |
| Quote rated successfully | `quote_ready.html` |
| Quote needs review | `needs_review.html` (to Corgi team) |
| Claim submitted | `claim_submitted.html` |
| Payment failed | `payment_failed.html` |
| Policy cancelled | `policy_cancelled.html` |
| Org invite | `org_invite.html` |

### `s3/` — File Storage (DocumentStorage)
AWS S3 wrapper with local filesystem fallback (`DocumentStorage` class).

- **Production:** Uploads to S3, returns presigned URLs with configurable TTL
- **Development (no S3 keys):** Falls back to local `media/` directory
- Used by COI generation, policy documents, claim attachments, certificate PDFs
- **Webhook auth:** Stripe webhooks are verified by signature before processing

### `pdf/` — PDF Utilities
Low-level PDF manipulation (merge, fill form fields).

### `admin_api/` — Staff API (5 Modules)

The admin API is split into 5 modules for maintainability:

| Module | Purpose |
|--------|---------|
| `helpers.py` | RBAC helpers: `_require_role(*roles)`, `_scope_queryset_by_role(qs, user)` |
| `analytics.py` | Analytics endpoints: pipeline, premium, coverage, claims, loss ratio, monthly premium, events |
| `quote_actions.py` | Quote actions: approve, recalculate, simulate, duplicate |
| `policy_actions.py` | Policy actions: endorse, cancel, reactivate |
| `crud.py` | Forms CRUD, audit log, user management |

**RBAC enforcement:** Every admin endpoint uses `_require_role()` to check the staff user's role. `_scope_queryset_by_role()` filters data so brokers see only their assigned orgs, AEs see their pipeline, etc.

**7 roles:** `admin`, `ae`, `ae_underwriting`, `bdr`, `finance`, `broker`, `policyholder`

### `common/` — Shared Code
Base models (`TimestampedModel`, `BaseDocument`, `SoftDeleteModel`), state choices, constants, exceptions, utilities.

**SoftDeleteModel mixin:** Applied to Quote, Policy, and Claim. Adds `deleted_at` and `is_deleted` fields. `delete()` sets `deleted_at` instead of removing rows. Default manager excludes deleted records; `all_with_deleted` includes them.

**Correlation IDs:** Middleware assigns a unique correlation ID to each request, included in logs and the `X-Correlation-Id` response header.

**Key constants** (`common/constants.py`):
| Constant | Value |
|----------|-------|
| `TECHRRG_CARRIER` | "Technology Risk Retention Group, Inc." |
| `ADMIN_FEE_RATE` | 0.22 (22% of GWP) |
| `DEFAULT_CEDED_PREMIUM_RATE` | 0.2830 (28.3% reinsurance) |
| `DEFAULT_ATTACHMENT_POINT` | $250,000 |
| `MONTHLY_BILLING_MULTIPLIER` | 1.111 |
| `STRIPE_PROCESSING_FEE_MULTIPLIER` | 1.029 |

## Coverage Tier System

### Tier 1 — Instant (rated by Corgi engine)
Slugs: `commercial-general-liability`, `directors-and-officers`, `technology-errors-and-omissions`, `cyber-liability`, `fiduciary-liability`, `hired-and-non-owned-auto`, `media-liability`, `employment-practices-liability`

- Rated synchronously by `RatingService.calculate()`
- Premium includes state tax + Stripe fee
- Promo discounts applied at checkout
- Monthly surcharge: ×1.111 then ÷12
- Reinsurance cession created (28.3%)

### Tier 2 — Brokered with Form
Slugs: `custom-commercial-auto`, `custom-crime`, `custom-kidnap-ransom`, `custom-med-malpractice`

- Extra questionnaire steps in the form
- Goes to `needs_review` status
- Underwriter creates `CustomProduct` with price + limits
- Auto-creates `UnderwriterOverride` → re-rates → may become `quoted`

### Tier 3 — Brokered Intent-Only
Slugs: `custom-workers-comp`, `custom-bop`, `custom-umbrella`, `custom-excess-liability`

- No extra form, just coverage selection
- Same underwriter flow as Tier 2
- Workers' Comp has Skyvern automation (Pie Insurance)

### Mixed Quotes
A single quote can contain all tiers. The summary page shows:
- **"Instant quote" card** — Tier 1 + fulfilled Tier 2/3 coverages
- **"Underwriting Review" card** — pending Tier 2/3 coverages

Partial checkout uses `split_quote_for_partial_checkout()` to create a child quote for purchasable coverages while the original stays in `needs_review`.

## Premium Calculation Details

### What's included in `Quote.quote_amount`
✅ State tax, ✅ Stripe fee (2.9%), ❌ Promo discount, ❌ Custom products, ❌ Monthly surcharge

### What's included in `Policy.premium`
- **RRG policies**: Rating premium after promo discount (includes tax + Stripe fee)
- **Brokered policies**: Exactly `CustomProduct.price` (no tax, no Stripe fee, no promo)

### Billing Amounts
- **Annual**: `policy.premium` (one payment)
- **Monthly**: `(annual_after_promo × 1.111) / 12` per month for RRG; `CustomProduct.price / 12` for brokered

## Authentication

### Internal API (Portal)
- JWT tokens in `Authorization: Bearer <token>` header
- Access token: 1 hour lifetime
- Refresh token: 7 days lifetime
- `X-Organization-Id` header sets active org context

### External API (Partners)
- API keys with `Bearer cg_live_...` format
- Keys are hashed (SHA-256) in the database
- Scoped to an organization

## Background Jobs (django-q2)

Background task processing uses django-q2 with Redis as the broker.

**Start the worker:** `python manage.py qcluster`

**Management commands:**
- `python manage.py send_renewal_reminders` — sends renewal reminder emails at 30/60/90 day windows
- `python manage.py qcluster` — runs the worker process for scheduled/async tasks

**Scheduled tasks (via qcluster):**
- Renewal reminders — daily
- Future: policy expiration checks, report generation

## Common Gotchas

1. **Company deduplication**: Companies are matched by `federal_ein` first, then `entity_legal_name`. Same EIN = same company, even across orgs.

2. **AI classifications are cached**: `Quote.initial_ai_classifications` stores first-run AI results. Subsequent re-ratings use cached values to ensure consistency.

3. **Promo codes are Stripe objects**: The backend validates promo codes against Stripe, not a local table. No Stripe key = no promo validation.

4. **Policy numbers are deterministic**: Format `XX-ST-YY-NNNNNN-01` where XX = coverage prefix, ST = state, YY = year. Sequence is auto-incremented per prefix.

5. **Partial checkout creates child quotes**: `split_quote_for_partial_checkout()` clones the quote, moves instant coverages to the child, and leaves review coverages on the parent. Custom products move to the child.

6. **Monthly surcharge is NOT in quote_amount**: The 11.1% surcharge is calculated at checkout time, not stored in the quote.

7. **State tax varies by state**: From 0.5% (Illinois) to 5% (New Jersey, Ohio). Rates in `rating/constants.py`.

8. **Cessions only for non-brokered**: Reinsurance cession records (28.3% of GWP) are only created for Tier 1 policies.

9. **SQL Explorer is restricted**: Django Explorer (SQL query tool) is limited to admin role only for security.

10. **S3 URLs have TTL**: Presigned S3 download URLs expire after a configurable time. Don't cache them long-term.
