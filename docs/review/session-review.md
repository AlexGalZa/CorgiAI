# Corgi Insurance — Session Code Review

Reviewer: `code-reviewer` (Opus 4.7, 1M)
Date: 2026-04-18
Scope: 10 targeted merges on `master` (most recent ~45 commits).

Legend: ✅ OK · ⚠ Issue (severity: **LOW / MED / HIGH / CRITICAL**).

---

## 1. `feat/1.1-brokered-stripe-variants` (95369d6)

Files reviewed:
- `api/products/selection.py`
- `api/products/management/commands/create_brokered_variants.py`
- `api/products/migrations/0004_brokered_variants.py`
- `api/stripe_integration/service.py` (`create_product`)

### ⚠ MED — Routing helper accepts `limit` in dollars but callers may pass cents
`api/products/selection.py:27-36` — `BROKERED_LIMIT_THRESHOLD_USD = 5_000_000` with the check `limit > 5_000_000`. Elsewhere in the codebase (`Policy.aggregate_limit`, `ProductConfiguration.max_limit`, Stripe `amount_cents`) mix dollars and cents. The helper has no unit assertion or docstring example showing a concrete value. If any caller accidentally passes a cents-denominated number (e.g. 100000000 for $1M), it will be *incorrectly* routed to brokered. Suggest: rename parameter to `limit_usd`, add a runtime `assert limit < 1_000_000_000` sanity bound, or take `Decimal` + an explicit unit.

### ⚠ LOW — Fallback clause returns any match when no direct row exists
`api/products/selection.py:66-72` — When `direct is None`, the code returns `ProductConfiguration.objects.filter(coverage_type=coverage).first()` with no `is_active=True` filter. A deactivated brokered-only row (no direct sibling) will still be returned. Suggest adding `is_active=True`.

### ⚠ LOW — `admin_notes` hard-coded; idempotency re-write loses prior edits
`api/products/management/commands/create_brokered_variants.py:88-97` — "repair" branch only heals `parent_variant` and `is_brokered_variant`; if a user edited `admin_notes`, `rating_tier`, or `requires_review` on the sibling they remain untouched — which is correct — but the command does not report the drift. Consider adding a warning when the existing sibling's `rating_tier != 'tier2_brokered_form'`.

### ✅ OK
- Migration (0004) is schema-only; idempotent command correctly guarded with `transaction.atomic()` and graceful Stripe failure path.
- `StripeService.create_product` stamps `brokered='true'` only when `input.brokered`, matching the existing `carrier` pattern.

---

## 2. `feat/1.3 Always-Synced Webhook + Reconcile` (via `ce98b29` / `api/common/tasks.py`)

Files reviewed:
- `api/webhooks/service.py` (`handle_subscription_updated`, `handle_invoice_paid`, `handle_invoice_payment_failed`)
- `api/common/tasks.py` (`reconcile_stripe_state`)

### ⚠ HIGH — Reconciler can miss drift because it filters on `updated_at >= cutoff` — but never catches policies that have *not* been touched in `lookback_minutes`
`api/common/tasks.py:105-111` — The scope query says: "only policies touched in the last N minutes." But the main failure mode the task is supposed to backstop is a webhook that was **dropped**. A dropped `customer.subscription.updated` webhook means Django *was never touched*, so `updated_at` stays old → those policies fall out of the window and are **never reconciled**. The docstring's claim that "a policy touched in the previous run is still in-window next run" is true but irrelevant to the "dropped webhook" scenario that justifies the task.

Fix: broaden the scope — e.g. filter on `status in ('active','past_due','pending_cancellation')` with a separate "last_reconciled_at" cursor, or reconcile the oldest N policies each run regardless of `updated_at`.

### ⚠ MED — Reconciler rate-limit uses `time.sleep()` in a Django-Q worker; blocks the cluster thread for up to 50s (500 policies × 0.1s)
`api/common/tasks.py:57-62, 130` — Acceptable for one task per 15 min, but synchronously holds a worker slot and will fall behind if `_RECONCILE_MAX_POLICIES_PER_RUN` is raised. Prefer scheduled batching or the Stripe SDK's built-in retry/backoff.

### ⚠ LOW — Status map diverges between `WebhookService.SUBSCRIPTION_STATUS_MAP` and `common.tasks._STRIPE_STATUS_TO_POLICY_STATUS`
Two copies, both identical today. They can (and will) drift. Extract to one module-level constant in `stripe_integration`.

### ⚠ LOW — `handle_subscription_updated` maps `incomplete` → `past_due`
`api/webhooks/service.py:477-485` — `incomplete` means the initial payment for a *new* subscription never succeeded. Mapping to `past_due` on the first billing cycle may produce a customer-visible "past_due" on a policy that was never actually active.

### ✅ OK
- Reconciler correctly caches subscription lookups per-run, records a `PolicyTransaction` audit row when the `reconciliation` type exists, and logs with a sensible summary.
- Expiration-date logic is monotonic (never rolls back).

---

## 3. `feat/2.1-stripe-payout-ids` (5e3dcb8)

Files reviewed:
- `api/policies/migrations/0037_policytransaction_stripe_payout_id.py`
- `api/webhooks/service.py` (`handle_charge_succeeded`, `_extract_payout_id`)
- Backfill command (`backfill_stripe_payouts.py`) listed in diff.

### ✅ OK
- Migration is additive, `null=True, blank=True, db_index=True` — safe.
- Fan-out update (`PolicyTransaction.objects.filter(policy__in=policies).update(...)`) correctly handles bundled coverage.
- `_extract_payout_id` falls back to `balance_transaction.payout` when the top-level `charge.payout` is still null at event-time.

### ⚠ LOW — Silent skip when payout not yet attached
`api/webhooks/service.py:921-927` — When the payout id isn't yet set, the handler returns silently relying on the backfill command. Any miss here means finance sees a policy with no payout id. Recommend tracking a per-charge `stripe_payout_missing` metric so stuck charges are surfaced.

### ⚠ MED — Stamps payout id on *all* historical `PolicyTransaction` rows for that policy
`api/webhooks/service.py:939-940` — `PolicyTransaction.objects.filter(policy__in=policies).update(stripe_payout_id=payout_id)` will overwrite payout_ids on older transactions (endorsements, reinstatements) that were settled in earlier payouts. Constrain by transaction_type or filter rows where `stripe_payout_id IS NULL`, so an old endorsement's payout id isn't clobbered by a later charge.

---

## 4. `feat/3.2-revenue-split` (ed32ca0)

Files reviewed:
- `api/policies/migrations/0038_revenuesplit.py`
- `api/stripe_integration/revenue_service.py`
- `api/common/tasks.py` (`daily_revenue_split_export`)
- `api/policies/models.py:1119-1199` (`RevenueSplit`)

### ✅ Split rates sum to 1.000
`api/stripe_integration/revenue_service.py:37-40` — 0.220 + 0.467 + 0.283 + 0.030 = 1.000. Confirm against finance's flow chart once.

### ⚠ HIGH — `revenue_split` uses `gross_written_premium` AND may fall back to `amount` / `premium`, which yield different bases
`api/stripe_integration/revenue_service.py:80-85` — Attribute fallback order is `gross_written_premium → amount → premium`. A `PolicyTransaction` exposes `gross_written_premium`; the `Policy` exposes `premium`. If an accidental caller passes a `Policy` directly, the split runs against the annual premium as if it were a single transaction, producing double/triple-counted bucket totals. Restrict the first argument's type or raise when `gross_written_premium` is missing.

### ⚠ MED — Rounding drift: each bucket is rounded independently with HALF_UP; splits may sum to more/less than the input by up to 2¢
`api/stripe_integration/revenue_service.py:118-125` — Finance reconciliation will see 1–2 cent mismatches per transaction. Reserve one bucket (e.g. `corgi_admin`) as the remainder: compute three buckets, round, then `corgi_admin = premium - (sum of others)`.

### ⚠ MED — Daily export is not idempotent
`api/common/tasks.py:260-352` — If the task runs twice for the same `report_date` (retry, manual re-run), duplicate `RevenueSplit` rows are created for each transaction (no unique constraint, no upsert). Add `unique_together = [('transaction', 'computed_at_date')]` or `get_or_create`/`update_or_create` on `(transaction,)`.

### ⚠ LOW — S3 object is not versioned or date-suffixed for re-runs
`corgi-finance/daily-splits/YYYY-MM-DD.csv` will be silently overwritten on re-run, destroying evidence of the prior export. Add `YYYY-MM-DD__{uuid}.csv` or enable S3 bucket versioning.

### ⚠ LOW — Brokered policies route 100% to `corgi_admin` — finance flow-chart says this is the brokerage fee only, not gross premium
`api/stripe_integration/revenue_service.py:110-117` — Assumes the full `gross_written_premium` *is* the retained brokerage fee. If Stripe charges the customer the full premium (including the carrier's portion), this bucket will be inflated. Verify the field contract — if `gross_written_premium` is the retained fee only, the code is correct; otherwise it's a CRITICAL accounting error.

### ✅ OK
- Migration depends on `0037_policytransaction_stripe_payout_id` — correct ordering after the reorder commit `8ad1356`.
- CSV upload writes a header-only file on empty days — good signal for "we ran".

---

## 5. 3.3 — AE payment-failed email (commit b51958a, inside H1 merge series)

Files reviewed:
- `api/webhooks/service.py:799-867`

### ⚠ MED — Per-policy AE lookup inside `for policy in policies` runs N+1 queries and sends N emails for bundled policies
`api/webhooks/service.py:809-822` — A bundled purchase with 4 coverages produces 4 separate AE emails (often to the same AE, with near-identical bodies). Recommend grouping by AE and sending one email per AE with a policy list — matches the existing customer-email pattern in lines 748-795.

### ⚠ LOW — `ae.name.split(' ', 1)[0]` yields whole-name first-names for single-token producers
`api/webhooks/service.py:832` — Works but brittle. Prefer a dedicated `first_name` column on `Producer` so templates don't guess.

### ⚠ LOW — Exception importing `PolicyProducer` is swallowed silently
`api/webhooks/service.py:800-803` — A failed import leaves `PolicyProducer = None` and the code just logs. In practice this module is always importable; if it isn't, you want to know loudly.

### ✅ OK
- Idempotency (already-sent check via `Payment.filter(..., status='failed').exists()` upstream at line 702) blocks repeat emails on Stripe retries.
- Only emails when AE is assigned AND has an email on file — correct per the card.

---

## 6. `feat/3.6-commission-cadence` (0862f68)

Files reviewed:
- `api/producers/signals.py`
- `api/producers/apps.py`
- `api/producers/management/commands/calculate_monthly_commissions.py`
- `api/producers/migrations/0004_commissionpayout_reversal_and_period.py`

### ⚠ HIGH — Signal reversal uses `qs.update(...)` which bypasses any overridden `save()` — **and bypasses auditlog**
`api/producers/signals.py:67-76` — `producers/apps.py:14` registers `CommissionPayout` with `auditlog`, which hooks `post_save`/`post_delete`, not bulk `.update()`. So reversing a payout via policy cancellation leaves **no audit trail**. Either iterate and call `.save()`, or write an explicit `LogEntry` per reversal.

### ⚠ MED — Signal only reacts to `status == 'cancelled'`, not to `pending_cancellation` or `expired`
`api/producers/signals.py:57-60` — 5.1's cancel flow sets `status='pending_cancellation'` via `.save(update_fields=['status', 'updated_at'], skip_validation=True)` (see `policies/api.py:1001`). That doesn't trip reversal — only the webhook-driven final `'cancelled'` transition does. Confirm timing: if a customer cancels mid-month and the webhook arrives in the next calendar month, the monthly commission job may have already paid out for that window before reversal kicks in.

### ⚠ MED — `pre_save` handler fires on *every* Policy save — measurable overhead
`api/producers/signals.py:34-44` — Each Policy save does an extra `only('status').get(pk=...)` query. On hot paths (rating, reconciliation bulk update) this doubles DB round trips. Consider storing pre-state via `Policy.refresh_from_db()` or django-model-utils' `FieldTracker` — or gate on `update_fields` containing `'status'`.

### ⚠ LOW — Monthly command `select_for_update` inside a `for` loop over `assignments.iterator()` means one Postgres row-lock per row; long runs can block concurrent writes
`calculate_monthly_commissions.py:197-208` — The inner `transaction.atomic()` limits the lock window, but confirm the streaming cursor isn't participating in a long-lived transaction.

### ⚠ LOW — Default commission rate hardcoded at 10% in code
`calculate_monthly_commissions.py:52` — Should live in Django settings or a Producer-level field.

### ✅ OK
- Migration (0004) adds `reversal_reason`, `reversed_at`, `period_start`, `period_end` as nullable — backward safe.
- `_days_active` handles missing dates and out-of-range windows correctly.

---

## 7. `feat/5.1-cancel-flow` (138416d)

Files reviewed:
- `api/policies/api.py:869-1056` (`cancel_policy`)
- `api/policies/models.py` (`pending_cancellation` status)

### ⚠ HIGH — `cancel_at_ts` uses `datetime.time.min` in UTC — off-by-one-day for customers west of UTC on the effective date
`api/policies/api.py:970-974` — A customer in PST requesting cancellation on 2026-04-20 gets `cancel_at_ts = 2026-04-20T00:00:00Z`, which is 2026-04-19 17:00 local time — **cancellation fires one day early**. Use the customer's/company's timezone (or end-of-day UTC via `time.max`) to guarantee the cancellation never fires before the selected date.

### ⚠ MED — Stripe failure rolls back nothing, but emits 400 after we've already validated state
If Stripe.Subscription.modify raises for a non-network reason (e.g. sub already cancelled), we 400 — but the webhook never fires, so the policy sits in its prior status forever. The order is OK (`policy.save()` runs *after* Stripe modify, so partial state is avoided) — consider catching the specific `stripe.InvalidRequestError` for "already cancelled" and setting `pending_cancellation` optimistically.

### ⚠ LOW — Records `CoverageModificationRequest` with `reason_text[:2000]` — reason field is arbitrary customer text
`api/policies/api.py:1005-1015` — Subsequent Django-admin rendering of this string is safe (Django auto-escapes), but if the text is piped into any external email/CSV without escaping, XSS/CSV-injection is possible. Low risk today, worth flagging.

### ✅ OK
- Correct two-phase state machine (`pending_cancellation` now, `cancelled` via webhook on the effective date) — prevents premature policy doc regeneration.
- Effective-date validation rejects past dates and post-expiration dates.
- Confirmation email failures don't roll back the Stripe schedule.

---

## 8. `feat/5.2-share-link` (d1144d9)

Files reviewed:
- `api/document_management/api.py` (`create_share_link`, `public_share_view`)
- `api/document_management/models.py` (`ShareLink`)
- `api/document_management/migrations/0002_add_sharelink.py`
- `portal/src/app/share/[token]/page.tsx`
- URL registration: `api/config/urls.py:611`

### ⚠ MED — Share token is a random opaque string, **not HMAC-signed** — revocation table is the only enforcement mechanism
`api/document_management/api.py:273-283` — `secrets.token_urlsafe(48)[:64]`. Unguessable (~384 bits), but:

1. If the `document_share_links` table is dropped/corrupted, every issued token *immediately* grants access (no signature fallback).
2. No way to revoke all tokens without DB access — no "token version" counter.

Consider signing with `TimestampSigner` (as done for reinstatement in `policies/api.py:444-465`) so expiry is embedded and offline-verifiable.

### ⚠ MED — Public endpoint does not rate-limit token guessing
`api/document_management/api.py:330-393` (`public_share_view`) — 384-bit tokens are unguessable, but a misconfigured bot/scraper with the wrong token can hammer the endpoint (one DB lookup + one S3 presign per hit). Add django-ratelimit on this path keyed by IP.

### ⚠ LOW — `resource_id` on the `ShareLink` is a `BigIntegerField` with NO foreign key
`api/document_management/models.py:161-164` — Intentional polymorphic design. `_resolve_share_resource` filters by type so cross-type reads are blocked at resolve-time; the `(resource_type, resource_id)` index is present — ✅.

### ⚠ LOW — `?json=1` branch returns the **signed S3 URL in the JSON response body** — if the portal page logs it to analytics/Sentry, the short-lived URL leaks
`api/document_management/api.py:377-391` — 5-min URL; low blast radius but worth calling out that frontend logging must scrub `download_url`.

### ⚠ LOW — `expires_in_days` cap is 90; cert share expiring in 90 days is long for PII
`api/document_management/api.py:24` — Consider 30-day default/cap for claim docs (which include loss-history PII).

### ✅ OK
- Token generation uses `secrets.token_urlsafe` (CSPRNG).
- Ownership check on create via `_resolve_share_resource(..., user=request.auth)` limits creation to the org-owner of the resource.
- `public_share_view` returns 410 on revoked/expired — correct.
- S3 presign expiration is 300s — tight.

---

## 9. `feat/H1-hubspot-bidirectional-sync` (617b2e0)

Files reviewed:
- `api/hubspot_sync/webhooks.py`
- `api/hubspot_sync/signals.py`
- `api/hubspot_sync/service.py`
- `api/hubspot_sync/models.py`

### ⚠ HIGH — `verify_hubspot_signature` returns **True when no secret is configured**
`api/hubspot_sync/webhooks.py:60-63` — "Dev mode — accept unsigned requests." In a misconfigured production deploy (env var missing), **any unauthenticated caller can mutate Policy.status, User.first_name, etc.** via the webhook. Fix: return `False` unless `settings.DEBUG` is explicitly on, or require `HUBSPOT_WEBHOOK_SECRET` to be set before the router registers.

### ⚠ HIGH — `_upsert_deal` writes `policy.status` via `.update(**updates)` without bumping `updated_at` → the 15-minute Stripe reconciler will *not* pick up drift introduced by a HubSpot webhook
`api/hubspot_sync/webhooks.py:217-218` — `Policy.objects.filter(pk=policy.pk).update(**updates)`. `auto_now` only refreshes with `.save()`. Since `reconcile_stripe_state` filters on `updated_at__gte=cutoff`, a HubSpot-driven status change that disagrees with Stripe will **never** be reconciled back. Compose with finding #2 — reinforces the need to fix the reconciler scope.

### ⚠ HIGH — Anti-loop guard is thread-local; won't cover async django-q workers
`api/hubspot_sync/signals.py:34` — The guard is set in the webhook request thread, but outbound syncs queue via `sync_policy_task.delay(...)` (signals.py:86). The django-q worker runs in a *different thread/process* and **will not see** the guard — so it will execute the outbound sync and HubSpot will echo it back. The `_is_hubspot_writeback` check at line 82 only bypasses writeback of the `hubspot_*_id` field itself, **not** the `status` updates the webhook performs. This is a real infinite-loop risk.

Suggested fix: add a DB-backed "sync token" (e.g. `Policy.last_hubspot_sync_hash`) that the outbound task compares to current-field hash before pushing; skip if equal.

### ⚠ MED — Dead-letter `HubSpotSyncFailure` has no `max_retries` / cap; retry worker isn't in this diff
`api/hubspot_sync/models.py:91-152` — The model comment says "cap in the worker, not here" but the worker isn't shipped in this merge. Unbounded retries if an external issue persists. Recommend adding a `status` column and archiving after N attempts.

### ⚠ LOW — `_upsert_company` is a no-op that logs
`api/hubspot_sync/webhooks.py:229-239` — Fine as a placeholder but surprises callers who expect org metadata sync. Consider documenting this in the docstring explicitly.

### ⚠ LOW — `build_absolute_uri()` in signature verification is untrusted
`api/hubspot_sync/webhooks.py:76` — Depends on `Host` header. Behind a proxy with misconfigured `USE_X_FORWARDED_HOST`, an attacker can control the signed material. Verify `ALLOWED_HOSTS` and `USE_X_FORWARDED_HOST` are correctly configured in production.

### ✅ OK
- `hmac.compare_digest` used — timing-safe.
- Failed events write to `HubSpotSyncFailure` and always 200 — correct HubSpot contract.
- Event handlers are idempotent (object-id keyed) with email fallback.

---

## 10. `feat/H7-pay-as-you-go-invoice` (a95c5c7)

Files reviewed:
- `api/policies/api.py:1180-1447` (`create_endorsement_invoice`)
- `api/stripe_integration/invoices.py` (`create_pay_as_you_go_invoice`)
- `api/webhooks/service.py:288-376` (`_apply_endorsement_from_invoice`)

### ⚠ MED — Partial-commit hazard between Payment insert and `endorse_modify_limits`
`api/webhooks/service.py:329-375` — Order: (1) check "already processed", (2) call `endorse_modify_limits`, (3) insert `Payment`. If step 2 succeeds but the process dies before step 3, a retry will re-apply the endorsement (step 1 checks Payment rows). Wrap steps 2–3 in a single `transaction.atomic()` so "applied" and "payment recorded" are committed together.

### ⚠ MED — Premium delta uses `RatingService._get_limit_factor` (a private method)
`api/policies/api.py:1331-1332` — Reaching into a `_`-prefixed API from a sibling module is a refactor hazard. Promote to a public method on RatingService.

### ⚠ MED — Floats used in proration math
`api/policies/api.py:1366` — `int(round(float(prorated_delta) * 100))`. `prorated_delta` is already a `Decimal`; round via `Decimal` ops to avoid float error on large cents-to-dollars conversions: `int((prorated_delta * 100).quantize(Decimal('1')))`.

### ⚠ LOW — `reason_text[:200]` truncation happens silently
`api/policies/api.py:1380` — Truncates to 200 chars for Stripe metadata; customer never sees the truncation. Log a warning when truncation happens.

### ⚠ LOW — Double-charging protection relies on `Payment.filter(stripe_invoice_id=... ,status='paid').exists()`
`api/webhooks/service.py:329-331` — Good-enough idempotency; noted for completeness.

### ✅ OK
- `is_brokered` gate correctly blocks pay-as-you-go for brokered policies (line 1285-1290).
- Rejects coverage mismatch and prohibits endorsement of non-active policies.
- Invoice metadata contract (documented in `_apply_endorsement_from_invoice` docstring) is explicit and complete.
- Email send failure doesn't block the response — correct.

---

# Summary — findings by severity

| # | Severity | File | Summary |
|---|----------|------|---------|
| 1 | **HIGH** | `api/hubspot_sync/webhooks.py:60-63` | Webhook signature verification silently passes when `HUBSPOT_WEBHOOK_SECRET` is unset — unauthenticated mutation vector in misconfigured prod. |
| 2 | **HIGH** | `api/hubspot_sync/signals.py:34` + `webhooks.py:217` | Thread-local anti-loop guard doesn't cover django-q workers; `.update()` on Policy.status doesn't bump `updated_at` → outbound sync echo + Stripe reconciler blindspot. |
| 3 | **HIGH** | `api/common/tasks.py:105-111` | Stripe reconciler scope filter on `updated_at` misses the dropped-webhook case it's supposed to backstop. |
| 4 | **HIGH** | `api/policies/api.py:970-974` | Cancel `cancel_at_ts` uses UTC midnight — fires one day early for west-of-UTC customers. |
| 5 | **HIGH** | `api/producers/signals.py:67-76` | Commission reversal via `qs.update()` bypasses auditlog — no audit trail on policy-cancellation-driven clawbacks. |
| 6 | **HIGH** | `api/stripe_integration/revenue_service.py:80-85` | Revenue split attribute fallback may double-count if called with a `Policy` instead of `PolicyTransaction`. |
| 7 | MED | `api/document_management/api.py:273-283` | Share token not HMAC-signed; DB is the only revocation/expiry enforcement. |
| 8 | MED | `api/webhooks/service.py:939-940` | Stripe payout handler over-writes payout id on historical PolicyTransactions. |
| 9 | MED | `api/stripe_integration/revenue_service.py:118-125` | Bucket rounding drift (up to 2¢ per transaction). |
| 10 | MED | `api/common/tasks.py:260-352` | Daily revenue-split export not idempotent — duplicate rows on retry. |
| 11 | MED | `api/webhooks/service.py:809-867` | AE payment-failed email fanout: N emails per bundled policy instead of 1 grouped. |
| 12 | MED | `api/webhooks/service.py:329-375` | PAYG endorsement apply + Payment insert not in one transaction. |
| 13 | MED | `api/hubspot_sync/models.py:91-152` | Dead-letter table has no retry cap / worker isn't shipped in this merge. |
| 14 | MED | `api/producers/signals.py:34-44` | `pre_save` handler doubles DB round-trips on every Policy save. |
| 15 | MED | `api/products/selection.py:27-36` | `limit` param has no unit enforcement (dollars vs cents). |
| 16 | LOW | various | Audit trail gaps, hardcoded rates, logging of short-lived URLs, single-token-name handling, etc. |

Top-3 highest-severity findings sent separately via SendMessage to `team-lead`.
