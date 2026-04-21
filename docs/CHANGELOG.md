# Changelog

All notable changes to the Corgi Insurance Platform.

## [2026-03-31] — Platform Sprint Day

**151 files changed, +14,027 lines, -3,600 lines across 45 commits.**

---

### Portal (Customer-Facing)

#### Coverage Dashboard
- KPI shows active policy count (not summed limits)
- Occurrence ≥ aggregate validation with auto-filtering dropdowns
- Signature field ("Type your full name") on endorsement disclaimer
- Premium delta display with prorated charge + payment confirmation step
- Recommended coverage section moved above active policies
- "File a Claim" removed from policy cards (dedicated Claims page only)
- Coverage tooltips: hover any coverage label → plain English explanation
- "What's Covered" tab on policy detail modal: covered perils, exclusions, limits per type
- Coverage page refactored: 1,245 → 202 lines, split into 9 components

#### Billing
- Section reorder: Plan → History → Method
- Annual upsell card for monthly users ("Save 10%")
- Stripe buttons wired: switch frequency, retry payment, update billing address
- Invoice PDF downloads via Stripe API endpoint
- Billing address section with update placeholder
- Failed payment retry button on payment history

#### Claims
- Active claims view with expandable inline detail cards
- Status badges: Received (blue), Under Review (amber), Paid (green), Denied (red)
- Read-only claim view ("cannot be edited after submission")
- Human-readable policy labels in claim form dropdown
- "File a Claim" hidden when user has no active policies

#### Certificates
- Removed misleading "Certificates Issued" count and "Last Issued" date
- "Download Current Certificate" button (wired to consolidated COI endpoint with PDF support)
- COI consolidation: groups policies by COI, brokered shows Insurer A/B

#### Documents
- "Download Coverage Folder" button → zip download from S3
- Claim documents grouped under "Loss Run Reports"
- Inline PDF preview in iframe modal

#### Quotes
- In-progress quote banner: "Continue Quote" when draft exists
- Quote draft auto-save to localStorage with resume/discard
- Plan comparison modal: feature matrix across 5 coverage types
- Coverage selection persistence through flow

#### Organization
- Member invite modal (email + role)
- Inline role editing + member removal (owner only)
- Billing address fields (model + UI)

#### Auth & UX
- Staff-only password login (policyholders blocked from admin)
- Quick login accounts fixed (portal + admin)
- Email verification on signup (added then disabled per request)
- Welcome onboarding wizard: 4-step overlay, skip option, localStorage persistence
- Notification center: bell icon with badge, portal dropdown, mark as read
- NPS satisfaction survey: 60s delay, 5 emoji ratings, 30-day cooldown

#### Dark Mode
- Full dark mode with CSS variable system
- Theme toggle (sun/moon) in header + all auth pages
- 70+ hardcoded color replacements across all pages
- Tailwind 4 `@theme inline` → runtime `var()` references + `.dark` overrides
- `html.dark` + `body` nuclear overrides for guaranteed bg switch

#### Mobile & Responsive
- Sidebar: slide-in overlay on mobile with backdrop
- Header: hamburger menu, centered logo, search hidden on mobile
- Modals: slide up from bottom, full-width on mobile
- Coverage: KPI grid 1→2→4 columns, cards stack vertically
- Billing: stats stack, payment history → card layout on mobile
- Certificates: table → cards on mobile

#### Accessibility
- ARIA attributes on sidebar nav, modals, org dropdown
- Focus trap + Escape key close on modals
- `focus-visible` ring styles on all button variants
- `aria-invalid` + `aria-describedby` on input error states
- `sr-only` labels on icon-only buttons
- Skip-to-content link

#### Other
- Custom Select component (Portal-rendered, keyboard nav, replaces ALL native `<select>`)
- Custom DatePicker component (calendar panel, replaces ALL `<input type="date">`)
- Portal-based tooltips (no clipping by overflow parents)
- Page transitions (fadeInUp on route change)
- Keyboard shortcuts: ⌘K for search, g+key navigation
- PWA manifest + mobile meta tags
- Analytics event tracking (quote started, claim filed, certificate downloaded, theme changed)
- Page titles via `usePageTitle` hook on all dashboard pages
- Empty states: dashed borders, muted icons, no colored backgrounds

---

### Admin Dashboard (Internal Ops)

#### RBAC & Security
- `_require_role()` on all 42 admin API endpoints with 6 role groups
- Impersonation restricted to admin-only
- Broker data scoping: sees only their referral partner's data
- Nav items hidden per role (BDR, Finance, Broker each see appropriate items)
- CommandPalette search filtered by role
- Staff-only login enforced (API + frontend)
- Superadmin (`is_superuser`) gets full admin nav regardless of role field
- Finance notifications filtered: only payments/expiring (no quote reviews)

#### Dashboards
- Broker Dashboard: referral stats, referral link, client tables, activity feed, charts
- Finance Dashboard: written premium, outstanding payments, collection rate, loss ratio
- BDR Dashboard: pipeline view, demo counts, conversion rate
- Operations Dashboard (Admin/AE): full overview with all metrics

#### New Features
- Commissions page: summary cards, filterable table, producer/date filters (finance + admin nav)
- Quote detail: customer context sidebar (company info, other quotes, policies, claims)
- Staff notifications: bell icon with badge, action items polling every 60s
- Form Builder: version history, view/restore old versions
- UserTimeline: real implementation merging audit log + quotes + policies
- Impersonation banner: amber top bar, "Return to your account" button
- Bulk actions on Quotes: checkbox select, batch status change, CSV export
- ExportAllButton component on Policies, Claims, Payments
- Per-object audit trail: collapsible Activity Log on QuoteDetail + PolicyDetail

#### Reports
- Claims summary section with stat cards
- All existing analytics enhanced with caching

#### Monitoring
- Sentry dynamic imports (auto-activate when installed)
- Slack/Telegram notification stubs

---

### API (Backend)

#### Auth & Security
- Staff-only password login endpoint
- Account lockout: 5 failed attempts → 30 min lock
- Password policy: min 8 chars + common password validator
- Impersonation tokens: 15 min TTL (was 1hr/7d)
- Brokered webhook auth: X-Webhook-Secret verification
- SQL Explorer: superuser-only access
- S3 presigned URLs: 5 min expiry (was 1hr)
- Request body limits: 10MB max
- Correlation ID middleware (X-Correlation-ID header + JSON logs)

#### New Endpoints
- `GET /certificates/consolidated` — grouped COI data with `?format=pdf` support
- `GET /users/documents/download-all` — zip download of all org documents
- `POST /stripe/switch-billing-frequency` — monthly↔annual with 10% discount
- `GET /stripe/invoice/{id}/pdf` — Stripe invoice PDF URL
- `POST /users/analytics` — receive frontend analytics events

#### Models & Data
- Organization: billing address (5 fields)
- Quote: `lead_source`, `assigned_ae` FK
- User: `failed_login_attempts`, `locked_until` (account lockout)
- SoftDeleteModel mixin on Quote, Policy, Claim (`is_deleted`, `deleted_at`)
- Certificate: `unique_together(user, org, coi_number, holder_name)`
- Data integrity: Quote amount ≥ 0, valid status transitions, Policy dates validation
- Database indexes on 9 hot fields across Policy, Claim, Certificate, User

#### Architecture
- `admin_api/api.py` split: 2,103 → 29 lines → `helpers.py`, `analytics.py`, `quote_actions.py`, `policy_actions.py`, `crud.py`
- Role-scoped querysets: broker users see only their referral data
- N+1 fixes: `select_related` on 4 list endpoints
- API response caching: 60s on analytics, 5min on form definitions
- Background jobs: django-q2 with ORM broker, async email/PDF tasks
- Structured JSON logging in production, human-readable in dev
- Enhanced health check: timed checks for DB, S3, Stripe, Resend, workers

#### Email Templates (3 new)
- `payment_failed_customer.html` — customer-facing with Stripe billing portal link
- `payment_reminder.html` — payment due reminder
- `policy_expiring.html` — coverage expiration notice

#### Other
- COI PDF generation (`certificates/pdf.py`)
- DocumentStorage class: S3 with local `media/` fallback
- `send_renewal_reminders` management command (60/30/7 day tiers)
- Rate limiting configured (django-ratelimit + cache backend)
- Seed data: role accounts with personal orgs, fixed `generate_policy_number`

#### Tests
- 59 total tests across 3 files
- `test_critical_flows.py` (14): auth, quotes, policies, claims, admin access
- `test_expanded.py` (17): rating, lifecycle, certificates, orgs, RBAC, webhooks
- `test_additional.py` (25+): soft delete, rate limiting, lockout, COI, email, middleware, integrity

---

### Infrastructure

#### Config & Deploy
- `.env.example` for all 3 services
- `.gitignore` updated
- `docker-compose.yml` unified (all 5 services)
- `render.yaml`, `vercel.json`, `netlify.toml`, `railway.toml`
- One-click deploy buttons in README (Railway, Render, Vercel, Netlify, Cloudflare, Koyeb, Northflank)
- `start.ps1`: migration error handling, auto role seeding, correct DB creds

#### Docs
- `docs/SETUP.md` rewritten: prerequisites, Docker/manual setup, troubleshooting, migration squashing
- `docs/CHANGELOG.md` (this file)

#### CI/CD
- `.github/workflows/lint.yml`: TypeScript checks (portal + admin) + Ruff (API)

#### Scripts
- `api/scripts/backup_db.sh` + `backup_db.ps1` — database backup with 30-day retention
- `api/seed_roles.py` — creates all role accounts with personal orgs

#### Database
- Canonical credentials: `corgi_admin` / `Corg1Secure2026x` / database `corgi`
- Local PostgreSQL 17 service must be stopped for Docker (port 5432 conflict)

---

### Post-Deploy Checklist

```bash
# 1. Install new Python dependencies
cd api && pip install -r requirements.txt

# 2. Run all pending migrations
python manage.py migrate

# 3. Seed role accounts (if fresh DB)
python manage.py shell -c "exec(open('seed_roles.py').read())"

# 4. Start background workers
python manage.py qcluster

# 5. Test renewal reminders (dry run)
python manage.py send_renewal_reminders --dry-run

# 6. Push to remote
git push
```
