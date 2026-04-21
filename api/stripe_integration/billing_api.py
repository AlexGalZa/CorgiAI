"""
Billing API endpoints — invoice history, downloads, and billing portal.

Endpoint: GET /api/v1/billing/invoices
  Returns a paginated list of Stripe invoices for the authenticated customer's
  subscriptions. Includes PDF download URL for each invoice.

Endpoint: GET /api/v1/billing/portal
  Returns a Stripe Billing Portal URL for self-serve subscription management.
"""

import logging
from datetime import datetime, timezone as dt_timezone
from typing import Optional

import stripe
from django.http import HttpRequest, JsonResponse
from ninja import Router

from organizations.service import OrganizationService
from policies.models import Policy
from stripe_integration.service import StripeService
from users.auth import JWTAuth

logger = logging.getLogger(__name__)

router = Router(tags=["Billing"])


@router.get("/invoices", auth=JWTAuth())
def list_invoices(
    request: HttpRequest,
    limit: int = 25,
    starting_after: Optional[str] = None,
) -> JsonResponse:
    """List Stripe invoices for the authenticated customer.

    Retrieves all invoices from Stripe for the organization's Stripe customer ID,
    formatted with Corgi-friendly field names. Each invoice includes a direct
    PDF download link hosted by Stripe.

    Args:
        request: Authenticated HTTP request.
        limit: Max invoices to return (1-100, default 25).
        starting_after: Stripe invoice ID for cursor-based pagination.

    Returns:
        JSON with ``invoices`` list, ``has_more``, and ``total_count``.
    """
    user = request.auth
    limit = max(1, min(limit, 100))

    org_id = OrganizationService.get_active_org_id(user)

    # Find the Stripe customer ID from any active or past policy
    policies = (
        Policy.objects.filter(
            quote__organization_id=org_id,
            stripe_customer_id__isnull=False,
        )
        .exclude(stripe_customer_id="")
        .order_by("-created_at")
    )

    stripe_customer_id = None
    for policy in policies:
        if policy.stripe_customer_id:
            stripe_customer_id = policy.stripe_customer_id
            break

    if not stripe_customer_id:
        # Try to find by user email
        try:
            client = StripeService.get_client()
            customers = client.Customer.list(email=user.email, limit=1)
            if customers.data:
                stripe_customer_id = customers.data[0].id
        except Exception as exc:
            logger.warning(
                "Could not look up Stripe customer for %s: %s", user.email, exc
            )

    if not stripe_customer_id:
        return JsonResponse(
            {
                "invoices": [],
                "has_more": False,
                "total_count": 0,
                "message": "No billing account found.",
            }
        )

    try:
        client = StripeService.get_client()

        list_kwargs = {
            "customer": stripe_customer_id,
            "limit": limit,
            "expand": ["data.payment_intent"],
        }
        if starting_after:
            list_kwargs["starting_after"] = starting_after

        stripe_invoices = client.Invoice.list(**list_kwargs)

        invoices = []
        for inv in stripe_invoices.data:
            # Parse timestamps
            period_start = inv.get("period_start")
            period_end = inv.get("period_end")
            created = inv.get("created")

            invoices.append(
                {
                    "id": inv.get("id"),
                    "number": inv.get("number"),
                    "status": inv.get(
                        "status"
                    ),  # draft, open, paid, void, uncollectible
                    "amount_due": inv.get("amount_due", 0) / 100,
                    "amount_paid": inv.get("amount_paid", 0) / 100,
                    "amount_remaining": inv.get("amount_remaining", 0) / 100,
                    "currency": (inv.get("currency") or "usd").upper(),
                    "description": inv.get("description")
                    or _build_invoice_description(inv),
                    "created_at": (
                        datetime.fromtimestamp(created, tz=dt_timezone.utc).isoformat()
                        if created
                        else None
                    ),
                    "period_start": (
                        datetime.fromtimestamp(
                            period_start, tz=dt_timezone.utc
                        ).isoformat()
                        if period_start
                        else None
                    ),
                    "period_end": (
                        datetime.fromtimestamp(
                            period_end, tz=dt_timezone.utc
                        ).isoformat()
                        if period_end
                        else None
                    ),
                    "due_date": (
                        datetime.fromtimestamp(
                            inv["due_date"], tz=dt_timezone.utc
                        ).isoformat()
                        if inv.get("due_date")
                        else None
                    ),
                    "paid_at": (
                        datetime.fromtimestamp(
                            inv["status_transitions"]["paid_at"],
                            tz=dt_timezone.utc,
                        ).isoformat()
                        if inv.get("status_transitions", {}).get("paid_at")
                        else None
                    ),
                    "pdf_url": inv.get("invoice_pdf"),
                    "hosted_url": inv.get("hosted_invoice_url"),
                    "subscription_id": inv.get("subscription"),
                    "payment_intent_id": (
                        inv["payment_intent"]["id"]
                        if isinstance(inv.get("payment_intent"), dict)
                        else inv.get("payment_intent")
                    ),
                    "line_items": _format_line_items(inv),
                }
            )

        return JsonResponse(
            {
                "invoices": invoices,
                "has_more": stripe_invoices.has_more,
                "total_count": len(invoices),
                "stripe_customer_id": stripe_customer_id,
            }
        )

    except stripe.error.InvalidRequestError as exc:
        logger.warning(
            "Stripe error listing invoices for customer %s: %s", stripe_customer_id, exc
        )
        return JsonResponse(
            {"error": "Could not retrieve invoices from Stripe."}, status=400
        )
    except Exception as exc:
        logger.exception("Unexpected error listing invoices: %s", exc)
        return JsonResponse({"error": str(exc)}, status=500)


@router.get("/invoices/{invoice_id}", auth=JWTAuth())
def get_invoice(request: HttpRequest, invoice_id: str) -> JsonResponse:
    """Retrieve a single Stripe invoice by ID.

    Args:
        request: Authenticated HTTP request.
        invoice_id: Stripe invoice ID (starts with ``in_``).

    Returns:
        JSON invoice object with ``pdf_url`` for PDF download.
    """
    user = request.auth
    org_id = OrganizationService.get_active_org_id(user)

    try:
        client = StripeService.get_client()
        inv = client.Invoice.retrieve(invoice_id, expand=["payment_intent"])

        # Security: verify this invoice belongs to the user's customer
        customer_id = inv.get("customer")
        has_policy = Policy.objects.filter(
            quote__organization_id=org_id,
            stripe_customer_id=customer_id,
        ).exists()

        if not has_policy:
            # Also check by user email
            customers = client.Customer.list(email=user.email, limit=1)
            if not customers.data or customers.data[0].id != customer_id:
                return JsonResponse({"error": "Invoice not found."}, status=404)

        created = inv.get("created")
        period_start = inv.get("period_start")
        period_end = inv.get("period_end")

        return JsonResponse(
            {
                "id": inv.get("id"),
                "number": inv.get("number"),
                "status": inv.get("status"),
                "amount_due": inv.get("amount_due", 0) / 100,
                "amount_paid": inv.get("amount_paid", 0) / 100,
                "currency": (inv.get("currency") or "usd").upper(),
                "description": inv.get("description")
                or _build_invoice_description(inv),
                "created_at": (
                    datetime.fromtimestamp(created, tz=dt_timezone.utc).isoformat()
                    if created
                    else None
                ),
                "period_start": (
                    datetime.fromtimestamp(period_start, tz=dt_timezone.utc).isoformat()
                    if period_start
                    else None
                ),
                "period_end": (
                    datetime.fromtimestamp(period_end, tz=dt_timezone.utc).isoformat()
                    if period_end
                    else None
                ),
                "paid_at": (
                    datetime.fromtimestamp(
                        inv["status_transitions"]["paid_at"], tz=dt_timezone.utc
                    ).isoformat()
                    if inv.get("status_transitions", {}).get("paid_at")
                    else None
                ),
                "pdf_url": inv.get("invoice_pdf"),
                "hosted_url": inv.get("hosted_invoice_url"),
                "subscription_id": inv.get("subscription"),
                "line_items": _format_line_items(inv),
            }
        )

    except stripe.error.InvalidRequestError:
        return JsonResponse({"error": "Invoice not found."}, status=404)
    except Exception as exc:
        logger.exception("Error retrieving invoice %s: %s", invoice_id, exc)
        return JsonResponse({"error": str(exc)}, status=500)


def _build_invoice_description(inv: dict) -> str:
    """Build a human-readable description from invoice line items."""
    lines = inv.get("lines", {}).get("data", [])
    if not lines:
        return "Invoice"

    descriptions = []
    for line in lines[:3]:  # Show first 3 lines
        desc = line.get("description") or line.get("plan", {}).get("nickname", "")
        if desc:
            descriptions.append(desc)

    if descriptions:
        return " · ".join(descriptions)
    return "Invoice"


def _format_line_items(inv: dict) -> list:
    """Format Stripe invoice line items into a clean list."""
    lines = inv.get("lines", {}).get("data", [])
    result = []
    for line in lines:
        period = line.get("period", {})
        result.append(
            {
                "description": line.get("description", ""),
                "amount": line.get("amount", 0) / 100,
                "currency": (line.get("currency") or "usd").upper(),
                "period_start": (
                    datetime.fromtimestamp(
                        period["start"], tz=dt_timezone.utc
                    ).isoformat()
                    if period.get("start")
                    else None
                ),
                "period_end": (
                    datetime.fromtimestamp(
                        period["end"], tz=dt_timezone.utc
                    ).isoformat()
                    if period.get("end")
                    else None
                ),
                "quantity": line.get("quantity", 1),
                "type": line.get("type", ""),  # "subscription" or "invoiceitem"
            }
        )
    return result
