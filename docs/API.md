# API Reference

## Base URL

```
http://localhost:8000/api/v1/
```

## Authentication

### JWT Bearer Tokens

All internal API endpoints require a JWT access token:

```
Authorization: Bearer <access_token>
```

### Organization Context

Most endpoints are org-scoped. Pass the active organization ID:

```
X-Organization-Id: <org_id>
```

### Obtaining Tokens

**Register:**
```http
POST /api/v1/users/register
Content-Type: application/json

{
  "email": "user@company.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "company_name": "Acme Corp"
}
```

Response:
```json
{
  "user": {
    "id": 1,
    "email": "user@company.com",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "tokens": {
    "access": "eyJ...",
    "refresh": "eyJ..."
  }
}
```

**Email OTP Login:**
```http
POST /api/v1/users/request-login-code
Content-Type: application/json

{ "email": "user@company.com" }
```

```http
POST /api/v1/users/verify-login-code
Content-Type: application/json

{
  "email": "user@company.com",
  "code": "123456"
}
```

**Token Refresh:**
```http
POST /api/v1/users/refresh
Content-Type: application/json

{ "refresh_token": "eyJ..." }
```

### Staff Password Login

Staff accounts (admin, ae, ae_underwriting, bdr, finance, broker) authenticate via password:

```http
POST /api/v1/users/login
Content-Type: application/json

{ "email": "admin@corgi.com", "password": "corgi123" }
```

**Account lockout:** After 5 failed login attempts, the account is locked for 30 minutes. The lockout fields (`failed_login_attempts`, `locked_until`) are on the User model.

### Rate Limits (Auth Endpoints)

| Endpoint | Limit |
|----------|-------|
| `POST /users/register` | 5/hour |
| `POST /users/request-login-code` | 10/hour |
| `POST /users/verify-login-code` | 10/hour |
| `POST /users/login` | 50/hour (dev) |

## RBAC (Role-Based Access Control)

All 42 API endpoints enforce role-based access. There are 7 roles:

| Role | Constant | Access |
|------|----------|--------|
| `admin` | `ROLE_ADMIN` | Full access to all endpoints |
| `ae` | `ROLE_AE` | Quotes, policies, clients, pipeline |
| `ae_underwriting` | `ROLE_AE_UNDERWRITING` | AE access + quote approval, endorsements, rating |
| `bdr` | `ROLE_BDR` | Leads, pipeline, limited quote access |
| `finance` | `ROLE_FINANCE` | Billing, commissions, payments, reports |
| `broker` | `ROLE_BROKER` | Scoped to assigned organizations only |
| `policyholder` | `ROLE_POLICYHOLDER` | Portal endpoints — own quotes, policies, claims |

**Endpoint groups by role:**

| Endpoint Group | Roles Allowed |
|---------------|---------------|
| Admin analytics | admin, ae, ae_underwriting, bdr, finance |
| Quote actions (approve, recalculate) | admin, ae_underwriting |
| Policy actions (endorse, cancel) | admin, ae_underwriting |
| Audit log | admin |
| Forms CRUD | admin |
| User management | admin |
| Billing/Commissions | admin, finance |
| Brokered pipeline | admin, ae, ae_underwriting, broker |
| Portal endpoints (quotes/me, policies/me) | All authenticated users |

Roles are enforced via `_require_role()` decorator and data is scoped via `_scope_queryset_by_role()` helper in the admin API.

## Error Format

All error responses follow this structure:

```json
{
  "success": false,
  "message": "Human-readable error description",
  "data": null
}
```

Common HTTP status codes:
- `400` — Validation error or bad request
- `401` — Authentication required or invalid token
- `403` — Insufficient permissions (e.g., not staff)
- `404` — Resource not found
- `429` — Rate limited
- `500` — Server error

## Public Endpoints

### Users

#### `POST /users/register`
Create a new account. Returns user info and JWT tokens. Rate limited: 5/hour.

#### `POST /users/request-login-code`
Send a 6-digit OTP to the user's email. Rate limited: 10/hour. Always returns success (doesn't reveal if email exists).

#### `POST /users/verify-login-code`
Verify OTP code and receive JWT tokens. Rate limited: 10/hour.

#### `POST /users/login`
Password-based login (for staff/dev accounts).

```json
{ "email": "admin@corgi.com", "password": "admin123" }
```

#### `POST /users/refresh`
Exchange a valid refresh token for new access + refresh tokens.

#### `GET /users/me`
Returns the authenticated user's profile.

```json
{
  "success": true,
  "message": "User retrieved successfully",
  "data": {
    "id": 1,
    "email": "user@company.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "is_staff": false,
    "active_organization_id": 1
  }
}
```

#### `GET /users/documents`
List all documents (policy docs, certificates, endorsements, receipts) for the active organization.

#### `GET /users/documents/{id}/download`
Get a presigned S3 URL for downloading a document. S3 URLs expire after a configurable TTL.

#### `GET /users/documents/download-all`
Download all documents for the active organization as a ZIP archive.

```http
GET /api/v1/users/documents/download-all
Authorization: Bearer <token>
X-Organization-Id: 1
```

Returns: ZIP file containing all policy documents, COIs, endorsements, and receipts.

#### `POST /users/impersonate/{user_id}`
Start impersonating another user (admin only). Returns tokens scoped to the target user.

#### `POST /users/stop-impersonation`
End impersonation session and return to admin's own tokens.

### Quotes

#### `POST /quotes/draft`
Create a new draft quote.

```json
{
  "coverages": ["technology-errors-and-omissions", "cyber-liability"],
  "selected_package": "essential"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "quote_number": "Q-100234",
    "status": "draft",
    "completed_steps": [],
    "current_step": null
  }
}
```

#### `PATCH /quotes/{quote_number}/step`
Save a single form step (auto-save).

```json
{
  "step_id": "company-info",
  "data": {
    "entity_legal_name": "Acme Corp",
    "organization_type": "llc"
  },
  "next_step": "financial-details"
}
```

#### `POST /quotes/`
Submit a completed quote for rating. Multipart form data with JSON `data` field + optional file uploads (`financial_files`, `transaction_files`, `claim_files`).

#### `PATCH /quotes/{quote_number}/`
Update an existing quote and re-run the rating engine.

#### `GET /quotes/me`
List all non-purchased quotes for the current organization.

#### `GET /quotes/{quote_number}`
Get detailed quote info with pricing breakdown.

```json
{
  "success": true,
  "data": {
    "quote_number": "Q-100234",
    "status": "quoted",
    "quote_amount": "12500.00",
    "rating_result": {
      "coverages": {
        "technology-errors-and-omissions": {
          "premium": 8500.00,
          "status": "quoted"
        }
      }
    }
  }
}
```

#### `GET /quotes/{quote_number}/form-data`
Get the full form data snapshot for resuming or reviewing a quote.

#### `POST /quotes/{quote_number}/checkout`
Generate a Stripe checkout URL.

```json
{
  "billing_frequency": "annual",
  "effective_date": "2026-04-01",
  "success_url": "https://app.corgi.insure/dashboard",
  "cancel_url": "https://app.corgi.insure/quotes"
}
```

#### `POST /quotes/{quote_number}/move`
Move a quote to a different organization.

```json
{ "organization_id": 5 }
```

### Policies

#### `GET /policies/me`
List all active policies for the current organization.

#### `GET /policies/{policy_number}/coi`
Get presigned S3 URL for the policy's Certificate of Insurance PDF.

#### `GET /policies/consolidated-coi`
Get a consolidated Certificate of Insurance covering all active policies for the organization.

Query params:
- `format=pdf` — Returns PDF bytes directly instead of JSON

```http
GET /api/v1/policies/consolidated-coi?format=pdf
Authorization: Bearer <token>
X-Organization-Id: 1
```

#### `GET /policies/recommendations`
Get up to 2 recommended coverage types the user doesn't have yet.

#### `GET /policies/billing`
Get billing overview: payment method, active plans, payment history.

#### `POST /policies/billing/portal`
Generate a Stripe billing portal URL for managing payment methods.

#### `POST /policies/billing/switch-frequency`
Switch billing frequency between annual and monthly for an active policy.

```json
{
  "policy_number": "TEO-NY-26-000001-01",
  "new_frequency": "monthly"
}
```

#### `GET /policies/{policy_number}/invoice`
Generate and download an invoice PDF for a policy.

Query params:
- `format=pdf` — Returns PDF bytes directly

### Claims

#### `POST /claims/`
File a claim. Multipart form data with JSON `data` field + optional `attachments`.

```json
{
  "policy_number": "TEO-NY-26-000001-01",
  "contact_name": "Jane Doe",
  "contact_email": "jane@acme.com",
  "contact_phone": "555-1234",
  "description": "Data breach incident on March 15",
  "date_of_loss": "2026-03-15"
}
```

#### `GET /claims/me`
List all claims for the current organization.

#### `GET /claims/{claim_number}`
Get detailed claim information.

### Certificates

#### `POST /certificates/custom`
Create a custom certificate with holder info and endorsements.

```json
{
  "coi_number": "COI-001234",
  "holder_name": "Landlord LLC",
  "holder_street_address": "123 Main St",
  "holder_city": "New York",
  "holder_state": "NY",
  "holder_zip": "10001",
  "is_additional_insured": true,
  "endorsements": ["additional-insured", "waiver-of-subrogation"]
}
```

#### `POST /certificates/custom/preview`
Generate a PDF preview without saving. Returns PDF bytes.

#### `GET /certificates/custom`
List custom certificates with pagination and search.

Query params: `search`, `page`, `page_size`

#### `GET /certificates/custom/{id}`
Get a single custom certificate.

#### `DELETE /certificates/custom/{id}`
Revoke a custom certificate.

#### `GET /certificates/custom/{id}/download`
Get presigned S3 download URL for the certificate PDF.

#### `GET /certificates/available-cois`
List COI numbers available for certificate generation.

### Organizations

#### `GET /organizations/invite-preview?code=ABC123`
Preview invite details (no auth required). Shows org name before joining.

#### `GET /organizations/list`
List all organizations the user belongs to.

#### `GET /organizations/me`
Get active organization details including members and pending invites.

#### `POST /organizations/`
Create a new organization. Caller becomes owner.

```json
{ "name": "Acme Corp" }
```

#### `POST /organizations/join`
Join an organization via invite code.

```json
{ "code": "ABC123" }
```

#### `POST /organizations/invites`
Create an invite link.

```json
{
  "default_role": "editor",
  "max_uses": 5,
  "expires_at": "2026-04-30T00:00:00Z",
  "email": "newuser@acme.com"
}
```

#### `POST /organizations/invites/{id}/resend`
Resend invite email.

#### `DELETE /organizations/invites/{id}`
Revoke an invite.

#### `PATCH /organizations/members/{user_id}`
Update a member's role. Owner only.

```json
{ "role": "viewer" }
```

#### `DELETE /organizations/members/{user_id}`
Remove a member. Owner only.

#### `POST /organizations/leave`
Leave the active organization.

### Forms (Public, no auth)

#### `GET /forms/{coverage_type}`
Get the active form definition for a coverage type.

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Cyber Liability Questionnaire",
    "slug": "cyber-liability",
    "version": 1,
    "coverage_type": "cyber-liability",
    "fields": [...],
    "conditional_logic": {...}
  }
}
```

#### `POST /forms/{coverage_type}/validate`
Validate form data against the active definition.

```json
{ "data": { "employee_band": "under_25", "sensitive_record_count": "under_10k" } }
```

#### `POST /forms/{coverage_type}/visible-fields`
Compute visible fields based on current form data (for conditional show/hide).

## Admin Endpoints

All require `Authorization: Bearer <token>` from a staff user.

### Analytics

#### `GET /admin/analytics/pipeline`
Quote counts by status (draft, submitted, quoted, needs_review, purchased, declined).

#### `GET /admin/analytics/premium-by-carrier`
Total written premium and policy count grouped by carrier.

#### `GET /admin/analytics/coverage-breakdown`
Active policy counts and premium totals per coverage type.

#### `GET /admin/analytics/policy-stats`
Summary: active policy count, total premium, average premium.

#### `GET /admin/analytics/claims-summary`
Claims by status with total reserves and total paid amounts.

#### `GET /admin/analytics/action-items`
Items needing attention: quotes needing review, expiring policies (30 days), open claims, overdue payments.

#### `GET /admin/analytics/monthly-premium`
Monthly written premium time series for the last 12 months.

#### `GET /admin/analytics/loss-ratio`
Overall loss ratio: paid losses / earned premium.

#### `POST /admin/analytics/events`
Track analytics events from the admin dashboard or portal.

```json
{
  "event_type": "page_view",
  "metadata": { "page": "/quotes", "duration_ms": 3200 }
}
```

### Quote Actions

#### `POST /admin/quotes/{id}/recalculate`
Re-run the rating engine. Optional overrides:

```json
{
  "coverages": ["cyber-liability"],
  "revenue": 5000000,
  "state": "CA"
}
```

#### `POST /admin/quotes/{id}/approve`
Approve a quote (sets status to `quoted`). Optionally send email.

```json
{
  "send_email": true,
  "effective_date": "2026-04-01"
}
```

#### `POST /admin/quotes/{id}/duplicate`
Clone a quote. The copy starts in `draft` status.

#### `POST /admin/quotes/{id}/simulate`
What-if pricing without saving. Returns simulated premium and per-coverage breakdown.

### Policy Actions

#### `POST /admin/policies/{id}/endorse`
Midterm endorsement. Supported actions:

- `modify_limits` — Change limits/retentions, recalculate premium
- `add_coverage` — Add a new coverage line
- `remove_coverage` — Remove coverage with prorated refund
- `backdate` — Backdate effective date (max 30 days)

```json
{
  "action": "modify_limits",
  "new_limits": { "aggregate_limit": 2000000 },
  "new_premium": "15000.00",
  "reason": "Client requested higher limits"
}
```

#### `POST /admin/policies/{id}/cancel`
Cancel with prorated Stripe refund.

```json
{ "reason": "Customer requested cancellation" }
```

#### `POST /admin/policies/{id}/reactivate`
Reactivate a cancelled monthly policy. Creates new Stripe subscription and charges gap premium.

```json
{ "reactivation_date": "2026-03-28" }
```

### Audit Log

#### `GET /admin/audit-log`
Paginated, filterable audit log.

Query params: `limit`, `offset`, `user_id`, `model_name`, `action`, `from_date`, `to_date`

### Forms CRUD

#### `GET /admin/forms`
List all form definitions.

#### `GET /admin/forms/{id}`
Get a form definition by ID.

#### `POST /admin/forms`
Create a new form definition.

#### `PUT /admin/forms/{id}`
Update a form definition.

#### `DELETE /admin/forms/{id}`
Soft-delete (deactivate) a form definition.

#### `POST /admin/forms/{id}/duplicate`
Duplicate a form with incremented version. New copy starts inactive.

## External API

Base URL: `http://localhost:8000/api/external/v1/`

Authentication: `Authorization: Bearer cg_live_...`

Interactive docs: [http://localhost:8000/api/external/v1/docs](http://localhost:8000/api/external/v1/docs)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/invites/{token}/redeem` | Redeem invite, receive API key |
| POST | `/quotes` | Create a quote with full company + coverage data |
| GET | `/quotes` | List quotes (`limit`, `offset` pagination) |
| GET | `/quotes/{identifier}` | Get quote by number or ID |

See the interactive Scalar docs for full request/response schemas, coverage fields, and questionnaire options.
