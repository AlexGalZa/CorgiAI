# API v2 Planning Document

**Status:** Draft  
**Target:** Q3 2026  
**Deprecation of v1:** 2027-01-01  
**Sunset of v1:** 2027-07-01

---

## Overview

API v2 is a planned major version that introduces breaking changes to improve
consistency, reduce ambiguity, and better support the partner ecosystem
(Zapier, Make, n8n integrations).

v1 will continue to receive security patches and critical bug fixes until the
**Sunset date**. No new features will be added to v1 after the v2 GA launch.

---

## Breaking Changes in v2

### 1. Unified Response Envelope

**v1 (inconsistent):**
```json
{ "success": true, "message": "...", "data": { ... } }
{ "quote_number": "...", "status": "..." }  // some endpoints skip envelope
```

**v2 (enforced):**
```json
{
  "ok": true,
  "data": { ... },
  "meta": { "request_id": "...", "version": "2" },
  "error": null
}
```

All error responses:
```json
{
  "ok": false,
  "data": null,
  "meta": { "request_id": "...", "version": "2" },
  "error": { "code": "QUOTE_NOT_FOUND", "message": "...", "details": {} }
}
```

### 2. Pagination Model Change

**v1:** `limit` + `offset`  
**v2:** cursor-based pagination via `next_cursor` / `prev_cursor` tokens

Reason: offset pagination becomes unreliable on large datasets with frequent inserts.

### 3. Date/Time Field Naming

**v1:** Mix of `created_at`, `createdAt`, `date_created`  
**v2:** All datetimes use `snake_case` ISO 8601 with timezone: `created_at`, `updated_at`, `purchased_at`

### 4. Quote Status Vocabulary

**v1:** `submitted`, `needs_review`, `quoted`, `purchased`, `declined`  
**v2:** `pending`, `under_review`, `priced`, `bound`, `declined`

Reason: `purchased` is ambiguous (policy purchase ≠ policy bind). `bound` is standard insurance terminology.

### 5. Coverage Slug Normalization

**v1:** `technology-errors-and-omissions`  
**v2:** Shorter canonical slugs: `tech-eo`, `cyber`, `do`, `cgl`, `epl`, `fiduciary`, `hnoa`, `media`

Full mapping:
| v1 Slug | v2 Slug |
|---------|---------|
| `technology-errors-and-omissions` | `tech-eo` |
| `cyber-liability` | `cyber` |
| `directors-and-officers` | `do` |
| `commercial-general-liability` | `cgl` |
| `employment-practices-liability` | `epl` |
| `fiduciary-liability` | `fiduciary` |
| `hired-and-non-owned-auto` | `hnoa` |
| `media-liability` | `media` |

### 6. Removed Endpoints

- `POST /invites/{token}/redeem` → Moved to `/auth/invite/redeem` (non-breaking path change)
- `GET /quotes/{identifier}` identifier fallback → v2 requires numeric ID only; quote_number lookup via `GET /quotes?quote_number=CQ-...`

### 7. Webhook Payload Shape

**v1:** Ad-hoc per-event structure  
**v2:** Standardized envelope:
```json
{
  "event": "quote.created",
  "api_version": "2",
  "created_at": "2026-03-31T12:00:00Z",
  "data": { ... }
}
```

### 8. Error Code Standardization

**v2** will introduce machine-readable error codes:
```
INVALID_INPUT, QUOTE_NOT_FOUND, POLICY_NOT_FOUND, AUTH_REQUIRED,
INVALID_API_KEY, COVERAGE_NOT_AVAILABLE, RATING_ENGINE_ERROR,
WEBHOOK_ALREADY_EXISTS, RATE_LIMIT_EXCEEDED
```

---

## New Features in v2

1. **Batch quote creation** — `POST /quotes/batch` — submit up to 10 quotes in one request
2. **Quote amendment** — `PATCH /quotes/{id}` — update a draft quote's company data or coverages
3. **Policy endorsement via API** — `POST /policies/{id}/endorse`
4. **Claims API** — `POST /claims`, `GET /claims`, `GET /claims/{id}`
5. **Document retrieval** — `GET /policies/{id}/documents` — download COI, declarations page
6. **Webhook replay** — `POST /webhooks/deliveries/{id}/replay` — re-trigger a past delivery

---

## Migration Timeline

| Date | Milestone |
|------|-----------|
| Q2 2026 | v2 alpha available in sandbox |
| Q3 2026 | v2 GA launch |
| Q3 2026 | v1 enters maintenance mode (security patches only) |
| 2027-01-01 | v1 deprecated — `Sunset` header added to all v1 responses |
| 2027-07-01 | v1 sunset — endpoints return 410 Gone |

---

## Version Negotiation

Clients can request a specific version via:
1. **URL prefix** (primary): `/api/external/v2/quotes`
2. **Header** (secondary): `API-Version: 2`

When no version is specified, the server defaults to v1 (for backward compatibility).
After the v1 sunset date, unversioned requests return 410 with a migration guide.

---

## SDK Updates

Partner SDKs (Python, Node, Ruby) will be updated to v2. v1 SDKs will be tagged `legacy`
and receive only security backports.

---

## Questions / Open Items

- [ ] Should v2 support OAuth 2.0 in addition to API key auth?
- [ ] Rate limits: keep per-org flat limit or introduce per-endpoint tiers?
- [ ] Do we support webhooks v2 event schema for existing v1 subscribers on opt-in basis?
- [ ] GraphQL exploration for complex querying (not in v2 scope but worth tracking)
