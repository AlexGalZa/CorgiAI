"""
Background tasks powered by django-q2.

Usage:
    from django_q.tasks import async_task
    async_task('common.tasks.send_email_async', template, context, to_email)

Start the worker cluster:
    python manage.py qcluster
"""

import logging
import time
from datetime import datetime, timedelta, timezone as dt_timezone

from django.db.models import F, Q

logger = logging.getLogger(__name__)


def send_email_async(template: str, context: dict, to_email: str):
    """Send an email in the background via django-q worker."""
    from emails.service import EmailService
    from emails.schemas import SendEmailInput

    logger.info("Sending async email: template=%s to=%s", template, to_email)
    EmailService.send(SendEmailInput(to=to_email, template=template, context=context))


def generate_pdf_async(document_type: str, object_id: int):
    """Background PDF generation."""
    logger.info("PDF generation queued: %s #%s", document_type, object_id)
    if document_type == "coi":
        from certificates.service import CertificateService
        from certificates.pdf import generate_coi_pdf

        data = CertificateService.generate_consolidated_coi_by_org(object_id)
        return generate_coi_pdf(data)
    # Add more document types as needed
    logger.warning("Unknown document type for PDF generation: %s", document_type)


# ─────────────────────────────────────────────────────────────────────────────
# Stripe reconciliation
# ─────────────────────────────────────────────────────────────────────────────

# Stripe subscription status → Policy.status (mirrors WebhookService map)
_STRIPE_STATUS_TO_POLICY_STATUS = {
    "active": "active",
    "trialing": "active",
    "past_due": "past_due",
    "unpaid": "past_due",
    "incomplete": "past_due",
    "incomplete_expired": "cancelled",
    "canceled": "cancelled",
}

# Small delay between Stripe API calls to stay well under the default
# 100 req/sec live-mode limit and the stricter 25 req/sec test-mode limit.
_RECONCILE_PER_CALL_SLEEP_SECONDS = 0.1

# Cap per-run work so a single scheduled task can't stall the worker for
# hours if a backlog accumulates. Anything not hit this pass will be
# picked up on the next 15-minute tick. 200 rows at 0.1s/call is ~20s
# of Stripe time, which fits inside one tick with plenty of headroom.
_RECONCILE_MAX_POLICIES_PER_RUN = 200


def reconcile_stripe_state(lookback_minutes: int = 60) -> dict:
    """Reconcile Django policy state with Stripe for active subscriptions.

    Intended to be scheduled every 15 minutes as a safety net in case a
    ``customer.subscription.*`` webhook is dropped or processed out of
    order.

    Scope:
        Every policy with a ``stripe_subscription_id`` is eligible. We
        order by ``last_reconciled_at`` (nulls first) and take the first
        200 rows — so brand-new policies and the oldest-reconciled rows
        get scanned first, and the scheduler round-robins the full
        subscription set over time. ``lookback_minutes`` is retained for
        backwards compatibility but no longer constrains the scope.

    Corrections applied (same rules as the webhook handler):
        * ``Policy.status`` ↔ Stripe subscription status.
        * ``Policy.expiration_date`` advances to ``current_period_end``
          when Stripe reports a later date (never rolls backward).

    Stamping:
        Every row inspected gets ``last_reconciled_at`` set to
        ``timezone.now()`` regardless of whether drift was detected. That
        is the scheduler's cursor — without the stamp the oldest rows
        would be scanned every tick forever.

    Drift is logged. If the ``PolicyTransaction`` model exposes a
    ``'reconciliation'`` transaction type, a row is recorded per drift
    event; otherwise we just log a warning.

    Rate limiting:
        Sleeps briefly between Stripe API calls to respect quotas.

    Returns:
        A summary dict with counts (``scanned``, ``drift``, ``errors``,
        ``skipped``) suitable for logging / monitoring.
    """
    from django.utils import timezone
    from policies.models import Policy, PolicyTransaction
    from stripe_integration.service import StripeService

    # Does PolicyTransaction expose a 'reconciliation' type?
    tx_choices = {c[0] for c in PolicyTransaction.TRANSACTION_TYPE_CHOICES}
    has_reconciliation_type = "reconciliation" in tx_choices

    stripe = StripeService.get_client()

    qs = Policy.objects.filter(
        ~Q(stripe_subscription_id="") & ~Q(stripe_subscription_id__isnull=True)
    ).order_by(F("last_reconciled_at").asc(nulls_first=True))[
        :_RECONCILE_MAX_POLICIES_PER_RUN
    ]

    scanned = 0
    drift_count = 0
    errors = 0
    skipped = 0
    # Cache subscription lookups so multiple policies sharing a subscription
    # only cost one Stripe call per run.
    sub_cache: dict[str, dict] = {}

    for policy in qs:
        scanned += 1
        sub_id = policy.stripe_subscription_id
        now = timezone.now()

        try:
            subscription = sub_cache.get(sub_id)
            if subscription is None:
                subscription = stripe.Subscription.retrieve(sub_id)
                sub_cache[sub_id] = subscription
                time.sleep(_RECONCILE_PER_CALL_SLEEP_SECONDS)
        except Exception as exc:
            errors += 1
            logger.warning(
                "reconcile_stripe_state: failed to fetch subscription %s for policy %s: %s",
                sub_id,
                policy.policy_number,
                exc,
            )
            # Stamp even on fetch error so the cursor advances and we do
            # not retry the same broken subscription every 15 minutes.
            Policy.objects.filter(id=policy.id).update(last_reconciled_at=now)
            continue

        stripe_status = (
            subscription.get("status")
            if isinstance(subscription, dict)
            else getattr(subscription, "status", None)
        )
        target_status = _STRIPE_STATUS_TO_POLICY_STATUS.get(stripe_status)

        current_period_end_ts = (
            subscription.get("current_period_end")
            if isinstance(subscription, dict)
            else getattr(subscription, "current_period_end", None)
        )
        new_expiration = None
        if current_period_end_ts:
            try:
                new_expiration = datetime.fromtimestamp(
                    current_period_end_ts, tz=dt_timezone.utc
                ).date()
            except (TypeError, ValueError, OSError):
                new_expiration = None

        update_fields: list[str] = []
        drift_notes: list[str] = []

        if target_status and policy.status != target_status:
            drift_notes.append(f"status {policy.status!r} -> {target_status!r}")
            policy.status = target_status
            update_fields.append("status")

        if new_expiration and new_expiration > policy.expiration_date:
            drift_notes.append(
                f"expiration_date {policy.expiration_date} -> {new_expiration}"
            )
            policy.expiration_date = new_expiration
            update_fields.append("expiration_date")

        if not update_fields:
            skipped += 1
            # Always stamp so the scheduler cursor advances on clean scans.
            Policy.objects.filter(id=policy.id).update(last_reconciled_at=now)
            continue

        drift_count += 1
        drift_desc = "; ".join(drift_notes)
        logger.info(
            "reconcile_stripe_state: policy %s drift corrected: %s (subscription=%s, stripe_status=%s)",
            policy.policy_number,
            drift_desc,
            sub_id,
            stripe_status,
        )
        policy.last_reconciled_at = now
        update_fields.append("last_reconciled_at")
        try:
            # Include updated_at so the auto_now field advances and this
            # policy isn't re-scanned on the next 15-minute run.
            policy.save(
                update_fields=update_fields + ["updated_at"],
                skip_validation=True,
            )
        except Exception as exc:
            errors += 1
            logger.exception(
                "reconcile_stripe_state: failed to save policy %s: %s",
                policy.policy_number,
                exc,
            )
            # Even if the save failed, advance the cursor so we don't
            # hammer a broken row every tick.
            Policy.objects.filter(id=policy.id).update(last_reconciled_at=now)
            continue

        # Audit trail — if the model supports it, otherwise just log-warn.
        if has_reconciliation_type:
            try:
                today = timezone.now().date()
                PolicyTransaction.objects.create(
                    policy=policy,
                    transaction_type="reconciliation",
                    effective_date=today,
                    accounting_date=today,
                    gross_written_premium=0,
                    description=(
                        f"Stripe reconciliation: {drift_desc} (subscription={sub_id}, stripe_status={stripe_status})"
                    ),
                )
            except Exception as exc:
                logger.exception(
                    "reconcile_stripe_state: failed to record PolicyTransaction for policy %s: %s",
                    policy.policy_number,
                    exc,
                )
        else:
            logger.warning(
                "reconcile_stripe_state: PolicyTransaction has no "
                "'reconciliation' type; drift on policy %s only logged "
                "(drift=%s)",
                policy.policy_number,
                drift_desc,
            )

    summary = {
        "scanned": scanned,
        "drift": drift_count,
        "errors": errors,
        "skipped": skipped,
        "lookback_minutes": lookback_minutes,
    }
    logger.info("reconcile_stripe_state complete: %s", summary)
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# Daily revenue-split export (Card 3.2)
# ─────────────────────────────────────────────────────────────────────────────

_REVENUE_SPLIT_CSV_COLUMNS = [
    "transaction_id",
    "policy_number",
    "is_brokered",
    "accounting_date",
    "gross_written_premium",
    "tax_amount",
    "corgi_admin",
    "techrrg",
    "corgire",
    "dane",
    "admin_fee",
    "computed_at",
]


def daily_revenue_split_export() -> dict:
    """Compute and export the previous day's revenue splits.

    Iterates every ``PolicyTransaction`` with ``accounting_date``
    equal to yesterday, runs it through
    ``stripe_integration.revenue_service.revenue_split``, persists a
    ``RevenueSplit`` row, and uploads a consolidated CSV to S3 at
    ``corgi-finance/daily-splits/YYYY-MM-DD.csv``.

    Treasury (Mercury/Meow) wire routing is still stubbed inside
    ``revenue_service`` — see card 3.2 follow-ups.

    Returns:
        Summary dict: ``{processed, errors, s3_key, report_date}``.
    """
    import csv
    import io

    from django.utils import timezone

    from policies.models import PolicyTransaction, RevenueSplit
    from stripe_integration.revenue_service import revenue_split

    report_date = (timezone.now() - timedelta(days=1)).date()
    s3_key = f"corgi-finance/daily-splits/{report_date.isoformat()}.csv"

    qs = (
        PolicyTransaction.objects.select_related("policy")
        .filter(accounting_date=report_date)
        .order_by("id")
    )

    processed = 0
    errors = 0
    rows: list[dict] = []

    for tx in qs:
        try:
            buckets = revenue_split(tx, tx.policy)
            split = RevenueSplit.objects.create(
                transaction=tx,
                corgi_admin=buckets["corgi_admin"],
                techrrg=buckets["techrrg"],
                corgire=buckets["corgire"],
                dane=buckets["dane"],
                admin_fee=buckets["admin_fee"],
            )
            rows.append(
                {
                    "transaction_id": tx.pk,
                    "policy_number": tx.policy.policy_number,
                    "is_brokered": tx.policy.is_brokered,
                    "accounting_date": tx.accounting_date.isoformat(),
                    "gross_written_premium": str(tx.gross_written_premium),
                    "tax_amount": str(tx.tax_amount or 0),
                    "corgi_admin": str(split.corgi_admin),
                    "techrrg": str(split.techrrg),
                    "corgire": str(split.corgire),
                    "dane": str(split.dane),
                    "admin_fee": str(split.admin_fee),
                    "computed_at": split.computed_at.isoformat(),
                }
            )
            processed += 1
        except Exception as exc:
            errors += 1
            logger.exception(
                "daily_revenue_split_export: failed on transaction %s: %s",
                tx.pk,
                exc,
            )

    # Emit the CSV to S3 even if the day was empty — finance expects a
    # header-only file as a "we ran, nothing to report" signal.
    try:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=_REVENUE_SPLIT_CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        _upload_daily_split_csv(s3_key, buffer.getvalue())
    except Exception as exc:
        errors += 1
        logger.exception(
            "daily_revenue_split_export: failed to upload %s: %s",
            s3_key,
            exc,
        )

    summary = {
        "processed": processed,
        "errors": errors,
        "s3_key": s3_key,
        "report_date": report_date.isoformat(),
    }
    logger.info("daily_revenue_split_export complete: %s", summary)
    return summary


def _upload_daily_split_csv(s3_key: str, csv_body: str) -> None:
    """Push the rendered CSV to S3 using the shared S3 client."""
    from django.conf import settings

    from s3.service import S3Service

    client = S3Service.get_client()
    client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=s3_key,
        Body=csv_body.encode("utf-8"),
        ContentType="text/csv",
    )
    logger.info("daily_revenue_split_export: uploaded %s", s3_key)
