# Internal API Reference

All internal endpoints use JWT authentication via `Authorization: Bearer <token>` header.  
Organization context is set via `X-Organization-Id` header (falls back to personal org).

Base URL: `/api/v1/`

**RBAC:** All 42 endpoints enforce role-based access control. 7 roles: `admin`, `ae`, `ae_underwriting`, `bdr`, `finance`, `broker`, `policyholder`. Admin endpoints use `_require_role()` decorator; data is scoped via `_scope_queryset_by_role()`.

**Account lockout:** After 5 failed login attempts, the account is locked for 30 minutes.

**Rate limits:** Auth endpoints are rate-limited (register: 5/hr, OTP: 10/hr, password login: 50/hr in dev).

---

## Users (`/api/v1/users/`)

### `POST /users/register`
Create a new account. No auth required. Rate limited: 5/hour.

**Request:** `{ email, password, first_name, last_name, company_name?, phone_number?, invite_code? }`  
**Response:** `{ user: { id, email, first_name, last_name }, tokens: { access, refresh } }`

### `POST /users/request-login-code`
Send a 6-digit OTP to email. No auth required. Rate limited: 10/hour.

**Request:** `{ email }`  
**Response:** `{ success, message }`

### `POST /users/verify-login-code`
Verify OTP and get tokens. No auth required. Rate limited: 10/hour.

**Request:** `{ email, code }`  
**Response:** `{ user, tokens }`

### `POST /users/refresh`
Refresh access token. No auth required.

**Request:** `{ refresh_token }`  
**Response:** `{ access, refresh }`

### `GET /users/me`
Get current user profile.

**Response:** `{ success, data: { id, email, first_name, last_name, ... } }`

### `GET /users/documents`
List all documents for current user's active org.

**Response:** `{ success, data: [{ id, title, category, s3_url, policy_numbers, ... }] }`

### `GET /users/documents/{document_id}/download`
Get presigned S3 download URL for a document (URLs have configurable TTL).

**Response:** `{ success, data: { url, filename } }`

### `GET /users/documents/download-all`
Download all documents for the active organization as a ZIP archive.

**Response:** ZIP file binary

### `POST /users/impersonate/{user_id}`
Start impersonating another user (admin only).

**Response:** `{ user, tokens }`

### `POST /users/stop-impersonation`
Stop impersonation and return to admin account.

**Response:** `{ success, data: { user, tokens } }`

---

## Quotes (`/api/v1/quotes/`)

### `POST /quotes/draft`
Create a new draft quote with selected coverages.

**Request:** `{ coverages: string[], selected_package?: string }`  
**Response:** `{ success, data: { quote_number, status, completed_steps, current_step } }`

### `PATCH /quotes/{quote_number}/step`
Save a single form step (auto-save as user progresses).

**Request:** `{ step_id: string, data: object, next_step?: string }`  
**Response:** `{ success, data: { quote_number, completed_steps } }`

### `POST /quotes/`
Submit a completed quote for rating. Multipart form: JSON data + file uploads.

**Request (multipart):** `data` (JSON string), `financial_files`, `transaction_files`, `claim_files`  
**Response:** `{ success, data: { quote_number, status, quote_amount, rating_result } }`

### `PATCH /quotes/{quote_number}/`
Update and re-rate an existing quote.

**Request:** Same schema as create  
**Response:** Same as create

### `GET /quotes/me`
List all non-purchased quotes for current org.

**Response:** `{ success, data: [{ id, quote_number, status, coverages, quote_amount, created_at, current_step }] }`

### `GET /quotes/{quote_number}`
Get quote details with pricing breakdown.

**Response:** `{ success, data: { quote_number, status, coverages, quote_amount, monthly_amount, custom_products, rating_result, monthly_breakdown, ... } }`

### `GET /quotes/{quote_number}/form-data`
Get full form data for resuming a quote (includes pricing, promo, split coverage info).

**Response:** `{ success, data: { quote_number, form_data, completed_steps, current_step, rating_result, instant_coverages, review_coverages, discount_percentage, ... } }`

### `POST /quotes/{quote_number}/checkout`
Generate a Stripe checkout URL.

**Request:** `{ billing_frequency: "annual"|"monthly", effective_date?, coverages?: string[], success_url?, cancel_url? }`  
**Response:** `{ success, data: { checkout_url } }`

### `POST /quotes/{quote_number}/move`
Move a quote to a different organization.

**Request:** `{ organization_id: number }`  
**Response:** `{ success }`

---

## Policies (`/api/v1/policies/`)

### `GET /policies/me`
List all policies for current org.

**Response:** `{ success, data: [{ policy_number, coverage_type, status, premium, effective_date, expiration_date, carrier, ... }] }`

### `GET /policies/{policy_number}/coi`
Get COI download URL for a policy.

**Response:** `{ success, data: { url, filename } }`

### `GET /policies/recommendations`
Get recommended additional coverages based on current policies.

**Response:** `{ success, data: [{ slug, name, description, reason }] }`

### `GET /policies/billing`
Get billing overview (active policies, payment history, next payment).

**Response:** `{ success, data: { policies, payments, stripe_customer_id, ... } }`

### `POST /policies/billing/portal`
Generate Stripe billing portal URL for managing payment methods.

**Response:** `{ success, data: { url } }`

### `GET /policies/consolidated-coi`
Get a consolidated COI covering all active policies. Add `?format=pdf` for PDF bytes.

**Response:** `{ success, data: { url } }` or PDF binary

### `POST /policies/billing/switch-frequency`
Switch billing frequency between annual and monthly.

**Request:** `{ policy_number, new_frequency: "annual"|"monthly" }`

### `GET /policies/{policy_number}/invoice`
Generate invoice PDF. Add `?format=pdf` for PDF bytes.

---

## Claims (`/api/v1/claims/`)

### `POST /claims/`
File a new claim. Multipart form: JSON data + file attachments.

**Request (multipart):** `data` (JSON string with policy_number, first_name, last_name, email, phone_number, description), `attachments`  
**Response:** `{ success, data: { claim_number, status, ... } }`

### `GET /claims/me`
List all claims for current org.

**Response:** `{ success, data: [{ claim_number, policy_number, status, description, created_at }] }`

### `GET /claims/{claim_number}`
Get claim details.

**Response:** `{ success, data: { claim_number, policy, status, description, documents, ... } }`

---

## Certificates (`/api/v1/certificates/`)

### `POST /certificates/custom`
Create a custom certificate with holder info and endorsements.

**Request:** `{ coi_number, holder_name, holder_street_address, holder_city, holder_state, holder_zip, is_additional_insured, endorsements: string[], ... }`  
**Response:** `{ success, data: { id, custom_coi_number, holder_name, document_url, ... } }`

### `POST /certificates/custom/preview`
Generate a PDF preview without saving.

**Request:** Same as create  
**Response:** PDF binary (inline)

### `GET /certificates/custom`
List all custom certificates for current org.

**Response:** `{ success, data: [{ id, custom_coi_number, holder_name, created_at, ... }] }`

### `GET /certificates/custom/{certificate_id}`
Get certificate details.

### `GET /certificates/custom/{certificate_id}/download`
Get presigned download URL for certificate PDF.

### `GET /certificates/available-cois`
List COI numbers available for certificate generation (from active policies).

**Response:** `{ success, data: [{ coi_number, policies: [{ policy_number, coverage_type }] }] }`

---

## Organizations (`/api/v1/organizations/`)

### `GET /organizations/list`
List all organizations the user belongs to.

**Response:** `{ success, data: [{ id, name, role, is_personal }] }`

### `GET /organizations/me`
Get details of the active organization (members, invites).

**Response:** `{ success, data: { id, name, members: [...], invites: [...] } }`

### `POST /organizations/`
Create a new organization.

**Request:** `{ name }`  
**Response:** `{ success, data: { id, name, members, ... } }`

### `POST /organizations/join`
Join an organization via invite code.

**Request:** `{ code }`  
**Response:** `{ success, data: { org details } }`

### `POST /organizations/invites`
Create an invite link (owner only).

**Request:** `{ default_role: "editor"|"viewer", max_uses?, expires_at?, email? }`  
**Response:** `{ success, data: { id, code, default_role, max_uses, use_count, expires_at } }`

### `POST /organizations/invites/{invite_id}/resend`
Resend invite email.

**Request:** `{ email }`

### `DELETE /organizations/invites/{invite_id}`
Revoke an invite.

### `PATCH /organizations/members/{user_id}`
Update a member's role (owner only).

**Request:** `{ role: "editor"|"viewer" }`

### `DELETE /organizations/members/{user_id}`
Remove a member from the organization.

### `POST /organizations/leave`
Leave the active organization.

### `GET /organizations/invite-preview?code=XXXXX`
Preview invite details (org name). No auth required.

---

## Analytics Events

### `POST /admin/analytics/events`
Track analytics events from admin or portal.

**Request:** `{ event_type: string, metadata: object }`  
**Response:** `{ success }`

---

## Stripe (`/api/v1/stripe/`)

### `POST /stripe/webhook/`
Stripe webhook endpoint. No auth — verified by Stripe signature.

Handles: `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `customer.subscription.deleted`

---

## Brokered (`/api/v1/brokered/`)

### `POST /brokered/{quote_number}/workers-compensation/callback`
Skyvern callback for workers' comp automation. No auth.

**Request:** `{ status, premium_amount?, decline_reason?, quote_url? }`

### `POST /brokered/workers-compensation/run-status`
Skyvern run status webhook. No auth.

**Request:** `{ run_id, status }`

---

## External API (`/api/external/v1/`)

Separate API for partners. Uses API key auth: `Authorization: Bearer cg_live_...`

### `POST /api/external/v1/quotes`
Create and rate a quote.

### `GET /api/external/v1/quotes`
List all quotes. Supports `limit` and `offset` pagination.

### `GET /api/external/v1/quotes/{identifier}`
Get quote by quote_number or ID.

### `POST /api/external/v1/invites/{token}/redeem`
Redeem an API key invite token. No auth.

Full documentation at `/api/external/v1/docs` (Scalar UI).
