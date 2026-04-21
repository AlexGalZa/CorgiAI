"""
Pay-as-You-Go invoice helpers (Trello H7).

Provides a thin wrapper around Stripe's Invoice / InvoiceItem API that
produces a *send_invoice* style invoice customers can pay via the
hosted Stripe payment page — no stored card on file required.

This is used for midterm endorsements (e.g. limit increases) where the
customer has no payment method available for an off-session charge. The
caller receives the finalized Invoice object — specifically the
``hosted_invoice_url`` attribute — and is expected to surface that URL
to the customer (email / portal link).

The actual "apply the change" step is performed asynchronously from
:func:`webhooks.service.WebhookService.handle_invoice_paid` once Stripe
confirms the invoice has been paid. Metadata dispatched via
``metadata['type'] == 'endorsement'`` drives that branch.
"""

import logging
from typing import Optional

import stripe

from stripe_integration.service import StripeService

logger = logging.getLogger(__name__)


def create_pay_as_you_go_invoice(
    customer_id: str,
    line_items: list[dict],
    metadata: Optional[dict] = None,
    due_days: int = 14,
) -> stripe.Invoice:
    """Create, finalize, and send a pay-as-you-go Stripe invoice.

    The invoice is created with ``collection_method='send_invoice'`` so it
    does not attempt to charge a card on file — the customer pays via the
    hosted invoice URL.

    Args:
        customer_id: Stripe customer id to bill.
        line_items: List of dicts shaped as
            ``{'amount_cents': int, 'description': str, 'metadata': dict}``.
        metadata: Invoice-level metadata. The H7 contract uses:
            ``{'type': 'endorsement', 'policy_id': str, 'coverage': str,
              'new_limit': str, 'reason': str}``.
        due_days: Number of days until the invoice is due (default 14).

    Returns:
        The finalized ``stripe.Invoice`` object — callers typically read
        ``hosted_invoice_url`` from it to present a payment link to the
        customer.
    """
    client = StripeService.get_client()

    invoice = client.Invoice.create(
        customer=customer_id,
        collection_method="send_invoice",
        days_until_due=due_days,
        metadata=metadata or {},
        auto_advance=False,
    )

    for item in line_items:
        client.InvoiceItem.create(
            customer=customer_id,
            invoice=invoice.id,
            amount=item["amount_cents"],
            currency="usd",
            description=item.get("description", ""),
            metadata=item.get("metadata", {}),
        )

    invoice = client.Invoice.finalize_invoice(invoice.id)
    client.Invoice.send_invoice(invoice.id)

    logger.info(
        "Pay-as-you-go invoice %s created for customer %s (type=%s, due=%sd)",
        invoice.id,
        customer_id,
        (metadata or {}).get("type", "unspecified"),
        due_days,
    )
    return invoice
