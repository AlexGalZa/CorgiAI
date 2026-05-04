"""Shepherd pipeline endpoints.

Provides the closing team with a single sortable list of open quotes,
each annotated with a next-best-action recommendation and a v0
closeability score, plus a one-click POST endpoint to send a templated
follow-up email through the existing EmailService + Resend integration.

This module is intentionally narrow — it does not yet join HubSpot deal
state. That comes in a follow-up PR once the manual one-click flow is
proven in use by the team.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.http import HttpRequest
from django.template.loader import render_to_string
from django.utils import timezone

from admin_api.helpers import (
    OPERATIONS_ROLES,
    WRITE_ROLES,
    _require_role,
    _scope_queryset_by_role,
)
from admin_api.schemas import (
    PipelineFollowUpResponse,
    PipelineListResponse,
    PipelineRow,
)
from common.schemas import ApiResponseSchema
from users.auth import JWTAuth

logger = logging.getLogger(__name__)

# v0 quote-expiry window: industry-standard quotes are valid 30 days from quoted_at.
QUOTE_EXPIRY_DAYS = 30

# Statuses worth surfacing to the closing team. Excludes purchased and declined.
OPEN_PIPELINE_STATUSES = ("draft", "submitted", "needs_review", "quoted")


def _compute_row(quote, now) -> PipelineRow:
    """Annotate a Quote with closeability score + next-best-action.

    All time math is in whole days against ``now``. The score is intentionally
    simple — the team can validate the ranking before we invest in anything
    smarter.
    """
    days_since_update = (now - quote.updated_at).days
    days_until_expiry: int | None = None
    if quote.status == "quoted" and quote.quoted_at is not None:
        elapsed = (now - quote.quoted_at).days
        days_until_expiry = max(QUOTE_EXPIRY_DAYS - elapsed, 0)

    next_action: str
    if quote.status == "quoted":
        if days_until_expiry is not None and days_until_expiry <= 7:
            next_action = "send_expiry_warning"
        elif days_since_update >= 3:
            next_action = "send_followup"
        else:
            next_action = "none"
    elif quote.status == "needs_review":
        next_action = "review_underwriting"
    elif quote.status == "submitted":
        next_action = "awaiting_rating" if days_since_update < 1 else "send_followup"
    elif quote.status == "draft":
        next_action = "send_followup" if days_since_update >= 7 else "none"
    else:
        next_action = "none"

    score = _closeability_score(
        status=quote.status,
        amount=quote.quote_amount,
        days_since_update=days_since_update,
        days_until_expiry=days_until_expiry,
    )

    company = quote.company
    user = quote.user

    return PipelineRow(
        quote_id=quote.pk,
        quote_number=quote.quote_number,
        company_name=getattr(company, "entity_legal_name", "") or "(no company)",
        customer_email=getattr(user, "email", "") if user else "",
        customer_name=_full_name(user),
        status=quote.status,
        premium=quote.quote_amount,
        billing_frequency=quote.billing_frequency,
        days_since_update=days_since_update,
        days_until_expiry=days_until_expiry,
        next_action=next_action,
        closeability_score=score,
        updated_at=quote.updated_at,
        quoted_at=quote.quoted_at,
    )


def _full_name(user) -> str:
    if user is None:
        return ""
    first = getattr(user, "first_name", "") or ""
    last = getattr(user, "last_name", "") or ""
    return f"{first} {last}".strip() or getattr(user, "email", "")


def _closeability_score(
    *,
    status: str,
    amount: Decimal | None,
    days_since_update: int,
    days_until_expiry: int | None,
) -> int:
    """v0 ranking heuristic. Higher = closer to closing."""
    if status == "quoted":
        base = 100
    elif status == "needs_review":
        base = 70
    elif status == "submitted":
        base = 60
    elif status == "draft":
        base = 30
    else:
        base = 10

    # Premium magnitude bumps priority (log-ish).
    if amount and amount > 0:
        try:
            amount_int = int(amount)
        except (TypeError, ValueError):
            amount_int = 0
        if amount_int >= 50_000:
            base += 25
        elif amount_int >= 10_000:
            base += 15
        elif amount_int >= 2_500:
            base += 5

    # Stale deals lose priority (cap at -30).
    base -= min(days_since_update * 2, 30)

    # Expiring quotes get an urgency boost.
    if days_until_expiry is not None and days_until_expiry <= 14:
        base += (15 - days_until_expiry)

    return max(base, 0)


def register_pipeline_routes(router) -> None:
    """Register Shepherd pipeline endpoints on the admin router."""

    @router.get(
        "/pipeline",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="List close-able deals with next-best-action ranking",
    )
    def list_pipeline(request: HttpRequest) -> tuple[int, dict[str, Any]]:
        """Return open quotes annotated with a closeability score and a
        next-best-action recommendation. Sorted by score descending."""
        _require_role(request, OPERATIONS_ROLES, "list_pipeline")

        from quotes.models import Quote

        qs = (
            Quote.objects.filter(status__in=OPEN_PIPELINE_STATUSES)
            .select_related("company", "user")
            .order_by("-updated_at")
        )
        qs = _scope_queryset_by_role(qs, request.auth, "quotes")

        now = timezone.now()
        rows = [_compute_row(q, now) for q in qs[:200]]
        rows.sort(key=lambda r: r.closeability_score, reverse=True)

        payload = PipelineListResponse(items=rows, total=len(rows))
        return 200, {
            "success": True,
            "message": f"{len(rows)} open deal(s)",
            "data": payload.dict(),
        }

    @router.post(
        "/pipeline/{quote_id}/follow-up",
        auth=JWTAuth(),
        response={200: ApiResponseSchema, 404: ApiResponseSchema, 409: ApiResponseSchema},
        summary="Send a templated follow-up email to the customer on a quote",
    )
    def send_follow_up(
        request: HttpRequest, quote_id: int
    ) -> tuple[int, dict[str, Any]]:
        """Render the quote-followup template and send via EmailService.

        Bumps ``updated_at`` on the quote so the row drops to the bottom of
        the next pipeline pull (the closer just touched it). Returns the
        recipient address and rendered subject for UI confirmation.
        """
        _require_role(request, WRITE_ROLES, "send_follow_up")

        from django.conf import settings
        from emails.schemas import SendEmailInput
        from emails.service import EmailService
        from quotes.models import Quote

        try:
            quote = Quote.objects.select_related("company", "user").get(pk=quote_id)
        except Quote.DoesNotExist:
            return 404, {"success": False, "message": "Quote not found", "data": None}

        recipient = getattr(quote.user, "email", None) if quote.user else None
        if not recipient:
            return 409, {
                "success": False,
                "message": "Quote has no customer email on file",
                "data": None,
            }

        company_name = (
            getattr(quote.company, "entity_legal_name", "") or "your company"
        )
        customer_name = _full_name(quote.user) or recipient
        portal_url = getattr(settings, "CORGI_PORTAL_URL", "https://corgi.insure")

        context = {
            "customer_name": customer_name,
            "company_name": company_name,
            "quote_number": quote.quote_number,
            "premium": quote.quote_amount,
            "billing_frequency": quote.billing_frequency,
            "quoted_at": quote.quoted_at,
            "portal_url": portal_url,
        }
        html = render_to_string("emails/quote_followup.html", context)
        subject = f"Following up on your Corgi quote {quote.quote_number}"

        from_email = getattr(
            settings,
            "HELLO_CORGI_EMAIL",
            getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@corgi.insure"),
        )

        try:
            EmailService.send(
                SendEmailInput(
                    to=[recipient],
                    subject=subject,
                    html=html,
                    from_email=from_email,
                )
            )
        except Exception as exc:
            logger.warning(
                "send_follow_up: EmailService.send failed for quote=%s: %s",
                quote.quote_number,
                exc,
            )
            return 200, {
                "success": False,
                "message": "Email send failed; not marked as touched",
                "data": None,
            }

        # Bump updated_at so this deal demotes in the next pipeline pull.
        quote.save(update_fields=["updated_at"])

        result = PipelineFollowUpResponse(
            quote_number=quote.quote_number,
            sent_to=recipient,
            subject=subject,
        )
        return 200, {
            "success": True,
            "message": "Follow-up sent",
            "data": result.dict(),
        }
