"""
Inbound email webhook handling (H20).

PROVIDER NOTE
-------------
As of this commit, Resend has announced but not fully released a
first-class inbound-email product. Depending on the account tier, the
two realistic integration paths are:

1. Resend Inbound (when GA) posts a JSON body that looks roughly like::

        {
          "type": "email.inbound",
          "data": {
            "thread_id": "abc123",
            "from": "customer@example.com",
            "to": ["sales@corgi.insure"],
            "subject": "Re: your quote",
            "text": "...",
            "html": "...",
            "received_at": "2026-04-18T14:30:00Z"
          }
        }

2. Otherwise we front the MX with a dedicated inbound provider
   (SendGrid Inbound Parse, Postmark, CloudMailin, AWS SES→SNS) and
   translate its payload to the shape in
   :class:`InboundEmailPayload`.

This module deliberately keeps the parser and the handler logic
separate from the HTTP layer so we can swap providers by rewriting
only ``parse_inbound_payload``. The HTTP endpoint itself lives in
``emails.api`` so it is auto-discovered alongside every other Ninja
router. If/when Resend Inbound ships, only ``parse_inbound_payload``
needs to change.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─── Parsed payload ──────────────────────────────────────────────────────────


@dataclass
class InboundEmailPayload:
    """Provider-agnostic representation of a single inbound email event."""

    thread_id: str
    from_address: str
    subject: str = ""
    snippet: str = ""
    received_at: Optional[datetime] = None
    to_addresses: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def parse_inbound_payload(body: dict[str, Any]) -> InboundEmailPayload:
    """Normalize a provider webhook body into an :class:`InboundEmailPayload`.

    Supports the Resend Inbound shape documented at the top of this
    module. Falls back to best-effort parsing of the common
    ``from``/``to``/``subject``/``text`` fields that most inbound
    providers share.
    """
    data = body.get("data") if isinstance(body.get("data"), dict) else body

    thread_id = (
        data.get("thread_id")
        or data.get("threadId")
        or data.get("message_id")
        or data.get("messageId")
        or ""
    )
    from_address = data.get("from") or data.get("sender") or ""
    # Some providers nest `from` as {"email": "...", "name": "..."}
    if isinstance(from_address, dict):
        from_address = from_address.get("email", "") or ""

    to_raw = data.get("to") or data.get("recipient") or []
    if isinstance(to_raw, str):
        to_addresses = [to_raw]
    elif isinstance(to_raw, list):
        to_addresses = [
            item.get("email", "") if isinstance(item, dict) else str(item)
            for item in to_raw
        ]
    else:
        to_addresses = []

    subject = data.get("subject") or ""
    snippet = data.get("text") or data.get("snippet") or data.get("body_plain") or ""

    received_raw = (
        data.get("received_at") or data.get("createdAt") or data.get("timestamp")
    )
    received_at: Optional[datetime] = None
    if isinstance(received_raw, str):
        try:
            # Support "Z" suffix (Python <3.11 compat).
            received_at = datetime.fromisoformat(received_raw.replace("Z", "+00:00"))
        except ValueError:
            received_at = None
    elif isinstance(received_raw, (int, float)):
        try:
            received_at = datetime.fromtimestamp(received_raw, tz=timezone.utc)
        except (ValueError, OSError):
            received_at = None

    return InboundEmailPayload(
        thread_id=thread_id,
        from_address=from_address,
        subject=subject,
        snippet=snippet,
        received_at=received_at,
        to_addresses=to_addresses,
        raw=body,
    )


# ─── Handler ─────────────────────────────────────────────────────────────────


def handle_inbound_email(payload: InboundEmailPayload) -> Optional[int]:
    """Upsert an EmailContext for the thread and notify the salesperson.

    Returns the EmailContext id on success, ``None`` if the payload is
    unusable (e.g. no thread_id).
    """
    from emails.models import EmailContext
    from emails.schemas import SendEmailInput
    from emails.service import EmailService

    if not payload.thread_id:
        logger.warning("handle_inbound_email: missing thread_id in payload")
        return None

    # Upsert by thread_id so subsequent replies extend the rolling window
    # rather than stacking up N rows per thread.
    context, _created = EmailContext.objects.get_or_create(
        thread_id=payload.thread_id,
    )
    context.append_message(
        sender=payload.from_address,
        snippet=payload.snippet,
        received_at=payload.received_at or timezone.now(),
    )
    context.save()

    # Notify the salesperson who owns the thread, if one is linked.
    salesperson = context.salesperson
    if salesperson is None or not getattr(salesperson, "email", None):
        logger.info(
            "handle_inbound_email: thread %s has no assigned salesperson; context stored, notification skipped.",
            payload.thread_id,
        )
        return context.pk

    frontend_url = getattr(settings, "FRONTEND_URL", "").rstrip("/")
    thread_url = f"{frontend_url}/inbox/{payload.thread_id}" if frontend_url else ""

    html = render_to_string(
        "emails/inbound_reply_notification.html",
        {
            "salesperson_first_name": getattr(salesperson, "first_name", "") or "",
            "thread_id": payload.thread_id,
            "last_messages": context.last_messages or [],
            "thread_url": thread_url,
            "policy_number": getattr(context.policy, "policy_number", "")
            if context.policy_id
            else "",
        },
    )

    try:
        EmailService.send(
            SendEmailInput(
                to=[salesperson.email],
                subject=f"New customer reply — {payload.subject or payload.thread_id}",
                html=html,
                from_email=getattr(
                    settings, "HELLO_CORGI_EMAIL", "Corgi <hello@corgi.insure>"
                ),
            ),
            sent_by=None,
        )
    except Exception:
        logger.exception(
            "handle_inbound_email: failed to send notification for thread %s",
            payload.thread_id,
        )

    return context.pk
