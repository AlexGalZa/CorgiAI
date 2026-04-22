# AIB Integration Design
**Date:** 2026-04-21
**Status:** Approved

## Goal

Integrate the AI Insurance Broker ("Trudy") into the Corgi portal quoting flow. Trudy lives as a sidebar chat panel inside each quote form step. She leads the conversation on new quotes, reacts on return visits, and auto-fills form fields in real-time as the client chats. Everything runs in one codebase, one database (Corgi PostgreSQL), one deployment.

The standalone FastAPI `aib/` service is retired entirely.

---

## What the client experiences

- Client lands on any quote step (public, no login required)
- Trudy panel opens on the right side of the form
- On a **new quote**: Trudy greets the client and asks the first question for that step in plain English
- On a **return visit**: Trudy is quiet and available — the client types if they want help
- As the client replies, form fields fill in automatically (green flash on each field as it's populated)
- If the client logs in or signs up mid-flow, the conversation is preserved and linked to their account
- When a quote is created, the session is linked to the quote — Trudy's conversation is part of the quote record

---

## Architecture

Three components:

1. **`api/aib/` (Django app)** — Trudy's brain. Handles Claude API calls, session management, field extraction. New Django app in the existing `api/` backend.
2. **`TrudyPanel` + `useTrudy` (Next.js portal)** — The chat widget. Sidebar component on each quote step. Hook manages session state and form auto-fill.
3. **Corgi PostgreSQL** — Two new tables (`aib_session`, `aib_message`) linked to existing `Quote` and `User` models.

---

## Data Models

### `AibSession`
| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `session_token` | string (unique) | For guest continuity — stored in browser `localStorage` |
| `user` | FK → User (nullable) | Linked when client logs in |
| `quote` | FK → Quote (nullable) | Linked when quote is created |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### `AibMessage`
| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `session` | FK → AibSession | |
| `role` | string | `user` or `assistant` |
| `content` | text | Message text |
| `extracted_fields` | JSONField | Fields extracted from this message, e.g. `{"company_name": "Acme"}` |
| `created_at` | datetime | |

---

## API Endpoints

All under `/api/aib/`. No auth required on session creation or messaging — guest access is intentional.

Guest requests authenticate by passing `session_token` in the `X-AIB-Token` request header. Logged-in requests use the standard Corgi JWT (`Authorization: Bearer ...`). Either is accepted on the GET and POST messages endpoints.

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/aib/sessions/` | None | Create session. Returns `session_id` + `session_token`. |
| `GET` | `/api/aib/sessions/{id}/` | `X-AIB-Token` or JWT | Fetch session + full message history. |
| `POST` | `/api/aib/sessions/{id}/messages/` | `X-AIB-Token` or JWT | Send message. Returns reply + `extracted_fields`. |
| `POST` | `/api/aib/sessions/{id}/claim/` | JWT (logged-in) | Link guest session to authenticated user. |

### Message response shape
```json
{
  "message": "Got it — 15 employees at Acme SaaS. What's your annual revenue?",
  "extracted_fields": {
    "company_name": "Acme SaaS",
    "num_employees": 15
  }
}
```

---

## Django App Structure (`api/aib/`)

```
api/aib/
├── __init__.py
├── apps.py
├── models.py          # AibSession, AibMessage
├── api.py             # django-ninja router (4 endpoints)
├── service.py         # Claude API wrapper (ported from aib/app/services/anthropic_client.py)
├── extraction.py      # Field extraction logic (ported from aib/app/services/extraction.py)
├── prompts.py         # System prompt + per-step prompts (ported from aib/app/prompts/)
└── migrations/
```

Prompts are scoped per quote step — the system prompt changes based on which step the client is on (company info, coverage selection, claims history, etc.).

---

## Portal Changes (`portal/`)

### `TrudyPanel` component
- Fixed-width sidebar (right side, all 7 quote steps)
- Displays conversation messages (Trudy + client bubbles)
- Text input at the bottom
- New quote: Trudy opens with a step-specific greeting
- Return visit: Trudy is quiet until the client types
- Green highlight flash on form fields as they're auto-filled

### `useTrudy` hook
- Creates or restores session on mount (checks `localStorage` for `session_token`)
- Sends messages to `/api/aib/sessions/{id}/messages/`
- On each response, loops through `extracted_fields` → calls `setValue()` on the React Hook Form context
- On login/sign-up: calls `/api/aib/sessions/{id}/claim/` to link session to the user account

### Quote step layout
Each of the 7 quote steps gets a two-column layout:
- Left (flex-2): existing form content (unchanged)
- Right (flex-1): `TrudyPanel`

The `TrudyPanel` receives the current step name so it can use the right system prompt. Steps and their Trudy focus:

| Step | Route | Trudy focus |
|---|---|---|
| Get Started | `/quote/get-started` | Coverage type selection |
| Company Info | `/quote/[n]/company` | Name, EIN, employees, revenue |
| Business Address | `/quote/[n]/coverage-intro` | Location details |
| Coverage Questions | `/quote/[n]/[coverageSlug]` | Coverage-specific risk questions |
| Claims History | `/quote/[n]/claims-history` | Past claims and loss history |
| Products | `/quote/[n]/products` | Explaining coverage options and limits |
| Summary | `/quote/[n]/summary` | Review and confirmation |

### Field name mapping
`extracted_fields` keys match the React Hook Form field names used in the quote form (e.g. `company_name`, `num_employees`, `annual_revenue`). A mapping constant in `useTrudy` translates any Claude-returned key variations to the canonical form field name.

---

## Session Continuity (Guest → Logged-in)

1. Guest starts chatting → `AibSession` created, `session_token` stored in `localStorage`
2. Guest logs in or signs up → portal calls `/claim/` with the token → `session.user` linked
3. Quote created → `session.quote` linked → Trudy's conversation attached to the quote record
4. Page refresh → portal reads `session_token` from `localStorage` → `GET /sessions/{id}/` restores full history

---

## What Gets Retired

- `aib/` FastAPI service — entire directory can be archived or removed after migration
- `aib/client/` React SPA — replaced by `TrudyPanel` in the portal
- Separate AIB database (if one existed) — all data lives in Corgi PostgreSQL

---

## Out of Scope

- Trudy in the admin dashboard
- Trudy on the policy management or billing pages
- Streaming responses (can be added later — start with request/response)
- Voice input
