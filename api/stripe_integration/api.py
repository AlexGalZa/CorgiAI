"""
Stripe webhook endpoint for processing payment events.

Handles Stripe events for the full payment lifecycle:
- ``checkout.session.completed``: Creates policies after successful payment.
- ``invoice.paid``: Records monthly subscription payments.
- ``invoice.payment_failed``: Marks policies as past-due.
- ``customer.subscription.updated``: Syncs Policy.status / expiration to Stripe.
- ``customer.subscription.deleted``: Cancels policies for non-payment.
- ``charge.succeeded``: Stamps PolicyTransaction.stripe_payout_id for finance.

This endpoint does NOT require JWT auth — it is verified via Stripe's
webhook signature (``STRIPE_WEBHOOK_SECRET``).
"""

import stripe
from django.http import HttpRequest, HttpResponse, JsonResponse
from ninja import Router

from stripe_integration.fees import calculate_fees
from stripe_integration.service import StripeService
from webhooks.service import WebhookService
from users.auth import JWTAuth

router = Router(tags=["Stripe"])


@router.get("/fees-preview")
def fees_preview(
    request: HttpRequest,
    amount: int,
    payment_method: str = "card",
    state: str | None = None,
) -> JsonResponse:
    """Return the processor-fee and tax breakdown for a brokered policy.

    Query params:
        amount: Pre-fee premium amount in cents.
        payment_method: ``'card'`` (default) or ``'ach'``.
        state: Two-letter US state code for tax lookup.

    Returns:
        JSON with ``processor_fee_cents``, ``tax_cents``, ``total_cents``.
    """
    try:
        breakdown = calculate_fees(
            amount_cents=int(amount),
            payment_method=payment_method,
            state=state,
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(breakdown)


@router.post("/webhook/")
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    """Receive and process Stripe webhook events.

    Verifies the webhook signature against the configured secret,
    then dispatches to the appropriate handler based on event type.

    Handled events:
        - ``checkout.session.completed`` (payment or subscription mode)
        - ``invoice.paid``
        - ``invoice.payment_failed``
        - ``customer.subscription.updated``
        - ``customer.subscription.deleted``

    Args:
        request: Raw HTTP request from Stripe with signature header.

    Returns:
        200 on success, 400 if signature verification fails.
    """
    payload: bytes = request.body
    sig_header: str | None = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = StripeService.verify_webhook(payload, sig_header)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    event_type: str = event["type"]

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        mode: str = session["mode"]

        if mode == "subscription":
            # Monthly billing: create policies with subscription IDs
            WebhookService.handle_subscription_created(session)
        else:
            # Annual billing: create policies with one-time payment
            WebhookService.handle_successful_payment(session)

    elif event_type == "invoice.paid":
        # Monthly recurring payment or gap premium invoice
        invoice = event["data"]["object"]
        WebhookService.handle_invoice_paid(invoice)

    elif event_type == "invoice.payment_failed":
        # Monthly payment failed — mark policies as past-due
        invoice = event["data"]["object"]
        WebhookService.handle_invoice_payment_failed(invoice)

    elif event_type == "customer.subscription.updated":
        # Subscription status / period changed — reconcile Policy state
        subscription = event["data"]["object"]
        WebhookService.handle_subscription_updated(subscription)

    elif event_type == "customer.subscription.deleted":
        # Subscription fully cancelled — cancel all linked policies
        subscription = event["data"]["object"]
        WebhookService.handle_subscription_cancelled(subscription)

    elif event_type == "charge.succeeded":
        # Charge settled — stamp the payout ID on matching PolicyTransactions
        # so finance can trace money from policy to bank deposit (card 2.1).
        charge = event["data"]["object"]
        WebhookService.handle_charge_succeeded(charge)

    return HttpResponse(status=200)


@router.post("/switch-billing-frequency", auth=JWTAuth())
def switch_billing_frequency(request: HttpRequest) -> JsonResponse:
    """Switch billing frequency between annual and monthly for all active policies.

    Accepts JSON body ``{ "frequency": "annual" | "monthly" }``.

    * **monthly → annual**: Cancels existing subscription, charges annual premium
      with a 10% discount via a one-time charge, and updates policies.
    * **annual → monthly**: Creates a new monthly Stripe subscription for the
      remaining policy period and updates policies.

    Returns:
        JSON with a Stripe-hosted URL (checkout or billing portal) when a
        redirect is needed, or a confirmation message.
    """
    import json
    import math
    from decimal import Decimal
    from datetime import date as _date

    from organizations.service import OrganizationService
    from policies.models import Policy
    from stripe_integration.schemas import (
        RecurringLineItemInput,
        CreateDirectSubscriptionInput,
    )

    user = request.auth
    body = json.loads(request.body)
    target_frequency = body.get("frequency")

    if target_frequency not in ("annual", "monthly"):
        return JsonResponse(
            {"success": False, "message": "frequency must be 'annual' or 'monthly'"},
            status=400,
        )

    org_id = OrganizationService.get_active_org_id(user)

    active_policies = list(
        Policy.objects.filter(
            quote__organization_id=org_id,
            status="active",
        ).select_related("quote__company")
    )

    if not active_policies:
        return JsonResponse(
            {"success": False, "message": "No active policies found"},
            status=404,
        )

    current_frequency = active_policies[0].billing_frequency
    if current_frequency == target_frequency:
        return JsonResponse(
            {
                "success": False,
                "message": f"Policies are already billed {target_frequency}ly",
            },
            status=400,
        )

    # Determine Stripe customer
    stripe_customer_id = None
    for p in active_policies:
        if p.stripe_customer_id:
            stripe_customer_id = p.stripe_customer_id
            break

    if not stripe_customer_id:
        # Try to find via user email
        from stripe_integration.schemas import GetOrCreateCustomerInput

        customer = StripeService.get_or_create_customer(
            GetOrCreateCustomerInput(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip() or user.email,
                metadata={"organization_id": str(org_id)},
            )
        )
        stripe_customer_id = customer.id

    try:
        if target_frequency == "annual":
            # Monthly → Annual: 10% discount on total annual premium
            total_annual_cents = 0
            for p in active_policies:
                annual_premium = int(p.premium * 100)  # premium is the annual amount
                total_annual_cents += annual_premium

            # Apply 10% discount
            discount_rate = Decimal("0.10")
            discounted_cents = int(total_annual_cents * (1 - float(discount_rate)))

            # Cancel existing subscriptions
            cancelled_subs: set[str] = set()
            for p in active_policies:
                if (
                    p.stripe_subscription_id
                    and p.stripe_subscription_id not in cancelled_subs
                ):
                    try:
                        StripeService.cancel_subscription(p.stripe_subscription_id)
                        cancelled_subs.add(p.stripe_subscription_id)
                    except Exception:
                        pass  # Subscription may already be cancelled

            # Create one-time charge for discounted annual premium
            description = (
                f"Annual premium (10% discount applied) — "
                f"{len(active_policies)} polic{'y' if len(active_policies) == 1 else 'ies'}"
            )
            payment_intent = StripeService.create_one_time_charge(
                customer_id=stripe_customer_id,
                amount_cents=discounted_cents,
                description=description,
                metadata={
                    "organization_id": str(org_id),
                    "billing_switch": "monthly_to_annual",
                    "policy_count": str(len(active_policies)),
                },
            )

            # Update all policies
            for p in active_policies:
                p.billing_frequency = "annual"
                p.stripe_subscription_id = None
                p.stripe_payment_intent_id = payment_intent.id
                p.save(
                    update_fields=[
                        "billing_frequency",
                        "stripe_subscription_id",
                        "stripe_payment_intent_id",
                    ]
                )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Switched to annual billing with 10% discount",
                    "data": {
                        "frequency": "annual",
                        "amount_charged_cents": discounted_cents,
                        "discount_percent": 10,
                        "payment_intent_id": payment_intent.id,
                    },
                }
            )

        else:
            # Annual → Monthly: create monthly subscription
            today = _date.today()
            line_items: list[RecurringLineItemInput] = []

            for p in active_policies:
                # Calculate monthly premium from the annual
                if p.monthly_premium:
                    monthly_cents = int(p.monthly_premium * 100)
                else:
                    monthly_cents = int(math.ceil(float(p.premium) / 12 * 100))

                coverage_display = p.coverage_type.replace("-", " ").title()
                line_items.append(
                    RecurringLineItemInput(
                        name=f"{coverage_display} — Monthly",
                        amount_cents=monthly_cents,
                        interval="month",
                        interval_count=1,
                        metadata={
                            "policy_id": str(p.id),
                            "policy_number": p.policy_number,
                            "coverage": p.coverage_type,
                            "organization_id": str(org_id),
                            "billing_switch": "annual_to_monthly",
                        },
                    )
                )

            # Use billing_cycle_anchor for 1st of next month
            from datetime import datetime

            if today.month == 12:
                next_month = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month = today.replace(month=today.month + 1, day=1)
            anchor_ts = int(
                datetime.combine(next_month, datetime.min.time()).timestamp()
            )

            subscription = StripeService.create_direct_subscription(
                CreateDirectSubscriptionInput(
                    customer_id=stripe_customer_id,
                    line_items=line_items,
                    billing_cycle_anchor=anchor_ts,
                    subscription_metadata={
                        "organization_id": str(org_id),
                        "billing_switch": "annual_to_monthly",
                    },
                )
            )

            # Update all policies
            for p in active_policies:
                if p.monthly_premium:
                    monthly_val = p.monthly_premium
                else:
                    monthly_val = Decimal(
                        str(math.ceil(float(p.premium) / 12 * 100) / 100)
                    )

                p.billing_frequency = "monthly"
                p.monthly_premium = monthly_val
                p.stripe_subscription_id = subscription.id
                p.stripe_customer_id = stripe_customer_id
                p.save(
                    update_fields=[
                        "billing_frequency",
                        "monthly_premium",
                        "stripe_subscription_id",
                        "stripe_customer_id",
                    ]
                )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Switched to monthly billing",
                    "data": {
                        "frequency": "monthly",
                        "subscription_id": subscription.id,
                    },
                }
            )

    except ValueError as exc:
        return JsonResponse(
            {"success": False, "message": str(exc)},
            status=400,
        )
    except Exception as exc:
        import traceback

        traceback.print_exc()
        return JsonResponse(
            {"success": False, "message": f"Billing switch failed: {str(exc)}"},
            status=500,
        )


@router.get("/invoice/{payment_id}/pdf", auth=JWTAuth())
def get_invoice_pdf(request: HttpRequest, payment_id: str) -> JsonResponse:
    """Retrieve the PDF URL for a Stripe invoice.

    Looks up the invoice by payment intent ID or invoice ID and returns
    the hosted invoice PDF URL.

    Args:
        request: Authenticated HTTP request.
        payment_id: Stripe payment intent ID or invoice ID.

    Returns:
        JSON with ``invoice_pdf_url`` on success, 404 if not found.
    """
    try:
        client = StripeService.get_client()

        # Try as invoice ID first (starts with 'in_')
        if payment_id.startswith("in_"):
            invoice = client.Invoice.retrieve(payment_id)
        else:
            # Try as payment intent ID — look up the invoice via the payment intent
            payment_intent = client.PaymentIntent.retrieve(payment_id)
            invoice_id = payment_intent.get("invoice")
            if not invoice_id:
                # Try to find invoice by charge
                charges = payment_intent.get("charges", {}).get("data", [])
                if not charges:
                    charges_list = client.Charge.list(
                        payment_intent=payment_id, limit=1
                    )
                    charges = charges_list.data
                for charge in charges:
                    if charge.get("invoice"):
                        invoice_id = charge["invoice"]
                        break

            if not invoice_id:
                return JsonResponse(
                    {"error": "No invoice found for this payment"},
                    status=404,
                )
            invoice = client.Invoice.retrieve(invoice_id)

        pdf_url = invoice.get("invoice_pdf")
        if not pdf_url:
            return JsonResponse(
                {"error": "Invoice PDF not available"},
                status=404,
            )

        return JsonResponse({"invoice_pdf_url": pdf_url})

    except stripe.error.InvalidRequestError:
        return JsonResponse(
            {"error": "Invoice not found"},
            status=404,
        )
    except Exception as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=500,
        )


@router.get("/invoice/{payment_id}/url", auth=JWTAuth())
def get_invoice_url(request: HttpRequest, payment_id: str) -> JsonResponse:
    """Retrieve the hosted invoice URL for a Stripe invoice.

    Looks up the invoice by payment intent ID or invoice ID and returns
    the Stripe-hosted invoice URL (the customer-facing invoice page which
    also offers PDF download).

    Args:
        request: Authenticated HTTP request.
        payment_id: Stripe payment intent ID or invoice ID.

    Returns:
        JSON with ``hosted_invoice_url`` on success, 404 if not found.
    """
    try:
        client = StripeService.get_client()

        # Try as invoice ID first (starts with 'in_')
        if payment_id.startswith("in_"):
            invoice = client.Invoice.retrieve(payment_id)
        else:
            # Try as payment intent ID — look up the invoice via the payment intent
            payment_intent = client.PaymentIntent.retrieve(payment_id)
            invoice_id = payment_intent.get("invoice")
            if not invoice_id:
                # Try to find invoice by charge
                charges = payment_intent.get("charges", {}).get("data", [])
                if not charges:
                    charges_list = client.Charge.list(
                        payment_intent=payment_id, limit=1
                    )
                    charges = charges_list.data
                for charge in charges:
                    if charge.get("invoice"):
                        invoice_id = charge["invoice"]
                        break

            if not invoice_id:
                return JsonResponse(
                    {"error": "No invoice found for this payment"},
                    status=404,
                )
            invoice = client.Invoice.retrieve(invoice_id)

        hosted_url = invoice.get("hosted_invoice_url")
        if not hosted_url:
            return JsonResponse(
                {"error": "Hosted invoice URL not available"},
                status=404,
            )

        return JsonResponse({"hosted_invoice_url": hosted_url})

    except stripe.error.InvalidRequestError:
        return JsonResponse(
            {"error": "Invoice not found"},
            status=404,
        )
    except Exception as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=500,
        )
