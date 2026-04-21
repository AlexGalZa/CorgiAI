"""
Quote action endpoints for the Admin API.

Provides recalculate, approve, duplicate, and simulate operations on quotes.
"""

from decimal import Decimal
from typing import Any

from django.http import HttpRequest
from django.utils import timezone

from admin_api.helpers import WRITE_ROLES, _require_role
from admin_api.schemas import (
    ApproveRequest,
    ApproveResponse,
    DuplicateResponse,
    RecalculateRequest,
    RecalculateResponse,
    SimulateRequest,
    SimulateResponse,
)
from common.schemas import ApiResponseSchema
from users.auth import JWTAuth

import logging

logger = logging.getLogger(__name__)


def register_quote_action_routes(router):
    """Register all quote action endpoints on the given router."""

    @router.post(
        "/quotes/{quote_id}/recalculate",
        auth=JWTAuth(),
        response={200: ApiResponseSchema, 404: ApiResponseSchema},
        summary="Re-run the rating engine on a quote",
    )
    def recalculate_quote(
        request: HttpRequest, quote_id: int, data: RecalculateRequest
    ) -> tuple[int, dict[str, Any]]:
        """Re-run the premium rating engine for a quote.

        Optionally override coverages, revenue, or state before recalculating.
        """
        _require_role(request, WRITE_ROLES, "recalculate_quote")

        from quotes.models import Quote
        from quotes.service import QuoteService

        try:
            quote = Quote.objects.get(pk=quote_id)
        except Quote.DoesNotExist:
            return 404, {"success": False, "message": "Quote not found", "data": None}

        # Apply overrides if provided
        if data.coverages:
            quote.coverages = data.coverages
        if data.revenue is not None:
            quote.company.last_12_months_revenue = data.revenue
            quote.company.save(update_fields=["last_12_months_revenue"])
        if data.state:
            quote.company.business_address.state = data.state
            quote.company.business_address.save(update_fields=["state"])

        QuoteService.process_quote_rating(quote, send_needs_review_email=False)

        quote.refresh_from_db()

        result = RecalculateResponse(
            quote_number=quote.quote_number,
            status=quote.status,
            total_premium=quote.quote_amount,
            breakdown=quote.rating_result,
        )
        return 200, {
            "success": True,
            "message": "Quote recalculated",
            "data": result.dict(),
        }

    @router.post(
        "/quotes/{quote_id}/approve",
        auth=JWTAuth(),
        response={200: ApiResponseSchema, 404: ApiResponseSchema},
        summary="Approve a quote and optionally send email",
    )
    def approve_quote(
        request: HttpRequest, quote_id: int, data: ApproveRequest
    ) -> tuple[int, dict[str, Any]]:
        """Approve a quote, setting its status to 'quoted', and optionally
        trigger the quote-ready email to the customer.
        """
        _require_role(request, WRITE_ROLES, "approve_quote")

        from quotes.models import Quote
        from quotes.service import QuoteService

        try:
            quote = Quote.objects.get(pk=quote_id)
        except Quote.DoesNotExist:
            return 404, {"success": False, "message": "Quote not found", "data": None}

        quote.status = "quoted"
        quote.quoted_at = timezone.now()
        quote.save(update_fields=["status", "quoted_at"])

        if data.send_email and quote.user:
            try:
                QuoteService.send_quote_ready_email(
                    quote, effective_date=data.effective_date
                )
            except Exception as e:
                logger.warning(
                    f"Failed to send quote-ready email for {quote.quote_number}: {e}"
                )

        result = ApproveResponse(
            quote_number=quote.quote_number,
            status=quote.status,
            message=f"Quote approved{' and email sent' if data.send_email else ''}",
        )
        return 200, {
            "success": True,
            "message": "Quote approved",
            "data": result.dict(),
        }

    @router.post(
        "/quotes/{quote_id}/duplicate",
        auth=JWTAuth(),
        response={200: ApiResponseSchema, 404: ApiResponseSchema},
        summary="Clone a quote",
    )
    def duplicate_quote(
        request: HttpRequest, quote_id: int
    ) -> tuple[int, dict[str, Any]]:
        """Create a copy of an existing quote with a new quote number."""
        _require_role(request, WRITE_ROLES, "duplicate_quote")

        from django.db import transaction
        from quotes.models import Quote

        try:
            original = Quote.objects.select_related(
                "company", "company__business_address"
            ).get(pk=quote_id)
        except Quote.DoesNotExist:
            return 404, {"success": False, "message": "Quote not found", "data": None}

        with transaction.atomic():
            new_quote = Quote.objects.create(
                company=original.company,
                user=original.user,
                organization=original.organization,
                status="draft",
                coverages=original.coverages,
                available_coverages=original.available_coverages,
                coverage_data=original.coverage_data,
                limits_retentions=original.limits_retentions,
                claims_history=original.claims_history,
                billing_frequency=original.billing_frequency,
                promo_code=original.promo_code,
                form_data_snapshot=original.form_data_snapshot,
                initial_ai_classifications=original.initial_ai_classifications,
                completed_steps=original.completed_steps,
                current_step=original.current_step,
                referral_partner=original.referral_partner,
                parent_quote=original,
            )

        result = DuplicateResponse(
            original_quote_number=original.quote_number,
            new_quote_number=new_quote.quote_number,
        )
        return 200, {
            "success": True,
            "message": "Quote duplicated",
            "data": result.dict(),
        }

    @router.post(
        "/quotes/{quote_id}/simulate",
        auth=JWTAuth(),
        response={200: ApiResponseSchema, 404: ApiResponseSchema},
        summary="Run the rating simulator without persisting",
    )
    def simulate_quote(
        request: HttpRequest, quote_id: int, data: SimulateRequest
    ) -> tuple[int, dict[str, Any]]:
        """Run the rating engine with hypothetical overrides.

        Does NOT persist any changes to the quote.
        """
        _require_role(request, WRITE_ROLES, "simulate_quote")

        from quotes.models import Quote
        from quotes.service import QuoteService

        try:
            quote = Quote.objects.select_related(
                "company", "company__business_address"
            ).get(pk=quote_id)
        except Quote.DoesNotExist:
            return 404, {"success": False, "message": "Quote not found", "data": None}

        overrides = data.dict(exclude_none=True)
        simulation = QuoteService.simulate_rating(quote, overrides)

        result = SimulateResponse(
            total_premium=Decimal(str(simulation["total_premium"])),
            coverages=simulation["coverages"],
        )
        return 200, {
            "success": True,
            "message": "Simulation result",
            "data": result.dict(),
        }
