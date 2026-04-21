"""
Brokered pipeline background tasks.

`alert_stuck_brokered_deals` identifies brokered deals whose status has sat in a
"brokering" state (``BrokeredQuoteRequest.status == 'brokering'`` or
``Policy.status == 'brokering'`` when that value is supported) longer than a
configurable threshold and emails a single consolidated summary to the
recipients declared in the ``BROKERED_STUCK_ALERT_RECIPIENTS`` environment
variable (comma-separated).

The task is idempotent: it only reads rows and sends at most one email per
invocation. Running it twice in one day just produces two identical emails —
it does not mutate any rows.

Usage (manual):
    from brokered.tasks import alert_stuck_brokered_deals
    alert_stuck_brokered_deals(threshold_days=3)

A django-q2 schedule entry in settings.py is intentionally NOT added here;
that is tracked as a follow-up.
"""

from __future__ import annotations

import logging
import os
from datetime import timedelta
from typing import Iterable, List

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


# The pipeline status that represents "still out to market / being brokered".
# BrokeredQuoteRequest exposes this as one of its PIPELINE_STATUS_CHOICES.
# If the Policy model gains a 'brokering' status later we also sweep that.
_BROKERING_STATUS = "brokering"


def _resolve_recipients() -> List[str]:
    """Parse the BROKERED_STUCK_ALERT_RECIPIENTS env var (comma-separated)."""
    raw = os.environ.get("BROKERED_STUCK_ALERT_RECIPIENTS", "") or ""
    if not raw:
        # Fallback to Django settings if the env var is empty.
        settings_val = getattr(settings, "BROKERED_STUCK_ALERT_RECIPIENTS", None)
        if isinstance(settings_val, (list, tuple)):
            return [str(e).strip() for e in settings_val if str(e).strip()]
        raw = str(settings_val or "")
    return [e.strip() for e in raw.split(",") if e.strip()]


def _days_stuck(obj) -> int:
    """Best-effort "days stuck" for a brokered record.

    NOTE: Neither ``BrokeredQuoteRequest`` nor ``Policy`` currently records a
    dedicated ``status_changed_at`` timestamp. We therefore fall back to
    ``updated_at`` (bumped on every save, which in practice tracks the most
    recent mutation including status transitions) and finally to
    ``created_at``. TODO(H10): once a ``status_history`` or
    ``status_changed_at`` field exists, use that instead for a true
    "entered brokering at" measurement.
    """
    now = timezone.now()
    anchor = getattr(obj, "updated_at", None) or getattr(obj, "created_at", None)
    if anchor is None:
        return 0
    delta = now - anchor
    return max(delta.days, 0)


def _collect_brokered_quote_requests(cutoff) -> list:
    from brokered.models import BrokeredQuoteRequest

    qs = BrokeredQuoteRequest.objects.filter(
        status=_BROKERING_STATUS, updated_at__lte=cutoff
    ).order_by("updated_at")
    return list(qs)


def _collect_policies(cutoff) -> list:
    """Sweep Policy rows with status='brokering' if the model supports it."""
    try:
        from policies.models import Policy
    except Exception:  # pragma: no cover - defensive
        return []

    # Discover if Policy.status accepts 'brokering'. If not, skip silently.
    try:
        field = Policy._meta.get_field("status")
        choices = {c[0] for c in (field.choices or [])}
    except Exception:
        return []

    if _BROKERING_STATUS not in choices:
        return []

    qs = Policy.objects.filter(
        status=_BROKERING_STATUS, updated_at__lte=cutoff
    ).order_by("updated_at")
    return list(qs)


def _to_row(obj) -> dict:
    """Normalise a BrokeredQuoteRequest or Policy into a template row."""
    days = _days_stuck(obj)
    policy_number = (
        getattr(obj, "policy_number", None)
        or getattr(getattr(obj, "quote", None), "quote_number", None)
        or f"#{obj.pk}"
    )
    company_name = (
        getattr(obj, "company_name", "")
        or getattr(getattr(obj, "organization", None), "name", "")
        or getattr(getattr(obj, "quote", None), "company_name", "")
        or ""
    )
    return {
        "id": obj.pk,
        "kind": obj.__class__.__name__,
        "policy_number": policy_number,
        "company_name": company_name or "—",
        "days_stuck": days,
        "status": getattr(obj, "status", ""),
        "assigned_to": str(getattr(obj, "assigned_to", "") or "—"),
    }


def alert_stuck_brokered_deals(threshold_days: int = 3) -> dict:
    """Send one consolidated alert for deals stuck in brokering.

    Args:
        threshold_days: Minimum days the deal must have been sitting in
            ``status='brokering'`` to qualify. Defaults to 3.

    Returns:
        Summary dict ({'stuck': N, 'sent': bool, 'recipients': [...]})
        suitable for logging and monitoring.
    """
    from emails.schemas import SendEmailInput
    from emails.service import EmailService

    recipients = _resolve_recipients()
    if not recipients:
        logger.warning(
            "alert_stuck_brokered_deals: BROKERED_STUCK_ALERT_RECIPIENTS is empty; skipping send."
        )
        return {"stuck": 0, "sent": False, "recipients": []}

    cutoff = timezone.now() - timedelta(days=threshold_days)

    stuck: Iterable = _collect_brokered_quote_requests(cutoff) + _collect_policies(
        cutoff
    )
    rows = [_to_row(obj) for obj in stuck]
    # Sort most-stuck first so the email leads with the worst offenders.
    rows.sort(key=lambda r: (-r["days_stuck"], r["policy_number"]))

    if not rows:
        logger.info(
            "alert_stuck_brokered_deals: no deals stuck >= %s days; skipping email.",
            threshold_days,
        )
        return {"stuck": 0, "sent": False, "recipients": recipients}

    context = {
        "threshold_days": threshold_days,
        "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "deals": rows,
        "total": len(rows),
    }
    html = render_to_string("emails/brokered_stuck_alert.html", context)

    subject = (
        f"[Corgi] {len(rows)} deal(s) stuck in brokering >= {threshold_days} day(s)"
    )
    from_email = getattr(
        settings,
        "HELLO_CORGI_EMAIL",
        getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@corgi.insure"),
    )

    try:
        EmailService.send(
            SendEmailInput(
                to=recipients,
                subject=subject,
                html=html,
                from_email=from_email,
            )
        )
    except Exception as exc:
        logger.error(
            "alert_stuck_brokered_deals: failed to send alert (%s deals) to %s: %s",
            len(rows),
            recipients,
            exc,
            exc_info=True,
        )
        raise

    logger.info(
        "alert_stuck_brokered_deals: sent alert for %s deals to %s.",
        len(rows),
        recipients,
    )
    return {"stuck": len(rows), "sent": True, "recipients": recipients}
