"""
Stripe service layer wrapping the Stripe Python SDK.

Provides a unified interface for all Stripe operations used by the
Corgi Insurance platform: customer management, checkout sessions,
subscriptions, one-time charges, refunds, invoices, and billing portal.

All methods are static and initialise the Stripe API key lazily from
Django settings.
"""

import logging
from typing import Optional

import stripe
from django.conf import settings

from stripe_integration.schemas import (
    CreateDirectSubscriptionInput,
    CreateMultiLineCheckoutInput,
    CreateMultiLineSubscriptionCheckoutInput,
    CreateOneTimeCheckoutInput,
    CreateProductInput,
    CreateRecurringPriceInput,
    CreateSubscriptionCheckoutInput,
    GetOrCreateCustomerInput,
    LineItemInput,
    ProrationBehavior,
    RecurringLineItemInput,
)

logger = logging.getLogger(__name__)


class StripeService:
    @staticmethod
    def _init_client():
        stripe.api_key = settings.STRIPE_SECRET_KEY

    @staticmethod
    def get_client():
        StripeService._init_client()
        return stripe

    @staticmethod
    def verify_webhook(payload: bytes, sig_header: str):
        StripeService._init_client()
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )

    @staticmethod
    def get_or_create_customer(input: GetOrCreateCustomerInput):
        client = StripeService.get_client()

        existing_customers = client.Customer.list(email=input.email, limit=1)
        if existing_customers.data:
            return existing_customers.data[0]

        return client.Customer.create(
            email=input.email, name=input.name, metadata=input.metadata or {}
        )

    @staticmethod
    def get_promotion_code(code: str):
        if not code:
            return None

        client = StripeService.get_client()
        try:
            promotion_codes = client.PromotionCode.list(code=code, active=True, limit=1)
            if not promotion_codes.data:
                return None

            promo = promotion_codes.data[0]
            coupon_id = (
                getattr(promo.promotion, "coupon", None)
                if hasattr(promo, "promotion")
                else None
            )

            if not coupon_id:
                return None

            coupon = client.Coupon.retrieve(coupon_id)
            return type(
                "PromoWithCoupon",
                (),
                {"id": promo.id, "code": promo.code, "coupon": coupon},
            )()
        except Exception as e:
            logger.warning(f"Failed to look up promo code '{code}': {e}")
            return None

    @staticmethod
    def build_line_item(input: LineItemInput) -> dict:
        return {
            "price_data": {
                "currency": "usd",
                "unit_amount": input.amount_cents,
                "product_data": {
                    "name": input.name,
                    "metadata": input.metadata or {},
                },
            },
            "quantity": 1,
        }

    @staticmethod
    def create_product(input: CreateProductInput):
        client = StripeService.get_client()
        metadata = dict(input.metadata or {})
        # We already tag ``carrier`` on Stripe Products when relevant; extend
        # the same pattern for ``brokered`` so the BROKERED variants created
        # by ``products.management.commands.create_brokered_variants`` are
        # discoverable in Stripe via metadata filters.
        if getattr(input, "brokered", False):
            metadata["brokered"] = "true"
        return client.Product.create(
            name=input.name,
            metadata=metadata,
        )

    @staticmethod
    def create_recurring_price(input: CreateRecurringPriceInput):
        client = StripeService.get_client()
        return client.Price.create(
            unit_amount=input.unit_amount,
            currency=input.currency,
            recurring={
                "interval": input.interval,
                "interval_count": input.interval_count,
            },
            product=input.product_id,
            metadata=input.metadata or {},
        )

    @staticmethod
    def _build_fee_line_items(
        fees_breakdown: dict, recurring: bool = False
    ) -> list[dict]:
        """Convert a ``calculate_fees`` result into Stripe line items.

        Only used for brokered policies where the caller opts in. Skips
        zero-value entries so the Stripe Checkout UI stays clean.
        """
        items: list[dict] = []
        recurring_block = (
            {"interval": "month", "interval_count": 1} if recurring else None
        )

        def _item(name: str, amount_cents: int) -> dict:
            price_data: dict = {
                "currency": "usd",
                "unit_amount": amount_cents,
                "product_data": {"name": name},
            }
            if recurring_block:
                price_data["recurring"] = recurring_block
            return {"price_data": price_data, "quantity": 1}

        processor = int(fees_breakdown.get("processor_fee_cents") or 0)
        tax = int(fees_breakdown.get("tax_cents") or 0)

        if processor > 0:
            items.append(_item("Processing Fee", processor))
        if tax > 0:
            items.append(_item("State Tax", tax))

        return items

    @staticmethod
    def create_one_time_checkout(
        input: CreateOneTimeCheckoutInput,
        fees_breakdown: Optional[dict] = None,
    ) -> str:
        client = StripeService.get_client()

        line_items = [
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": input.amount_cents,
                    "product_data": {
                        "name": input.product_name,
                        "metadata": input.product_metadata or {},
                    },
                },
                "quantity": 1,
            }
        ]
        if fees_breakdown:
            line_items.extend(
                StripeService._build_fee_line_items(fees_breakdown, recurring=False)
            )

        checkout_params = {
            "customer": input.customer_id,
            "customer_creation": "always" if not input.customer_id else None,
            "mode": "payment",
            "payment_intent_data": {
                "setup_future_usage": "off_session",
            },
            "line_items": line_items,
            "success_url": input.success_url,
            "cancel_url": input.cancel_url,
            "metadata": input.metadata or {},
        }
        checkout_params = {k: v for k, v in checkout_params.items() if v is not None}

        if input.promotion_code_id:
            checkout_params["discounts"] = [{"promotion_code": input.promotion_code_id}]

        checkout_session = client.checkout.Session.create(**checkout_params)
        return checkout_session.url

    @staticmethod
    def create_multi_line_checkout(
        input: CreateMultiLineCheckoutInput,
        fees_breakdown: Optional[dict] = None,
    ) -> str:
        client = StripeService.get_client()

        line_items = list(input.line_items)
        if fees_breakdown:
            line_items.extend(
                StripeService._build_fee_line_items(fees_breakdown, recurring=False)
            )

        checkout_params = {
            "customer": input.customer_id,
            "customer_creation": "always" if not input.customer_id else None,
            "mode": "payment",
            "payment_intent_data": {
                "setup_future_usage": "off_session",
            },
            "line_items": line_items,
            "success_url": input.success_url,
            "cancel_url": input.cancel_url,
            "metadata": input.metadata or {},
        }
        checkout_params = {k: v for k, v in checkout_params.items() if v is not None}

        checkout_session = client.checkout.Session.create(**checkout_params)
        return checkout_session.url

    @staticmethod
    def create_subscription_checkout(
        input: CreateSubscriptionCheckoutInput,
        fees_breakdown: Optional[dict] = None,
    ) -> str:
        client = StripeService.get_client()

        product = StripeService.create_product(
            CreateProductInput(name=input.product_name, metadata=input.product_metadata)
        )

        price = StripeService.create_recurring_price(
            CreateRecurringPriceInput(
                product_id=product.id,
                unit_amount=input.amount_cents,
                currency="usd",
                interval=input.interval,
                interval_count=input.interval_count,
                metadata=input.price_metadata,
            )
        )

        line_items = [{"price": price.id, "quantity": 1}]
        if fees_breakdown:
            line_items.extend(
                StripeService._build_fee_line_items(fees_breakdown, recurring=True)
            )

        subscription_data = {"metadata": input.subscription_metadata or {}}

        if input.trial_end:
            subscription_data["trial_end"] = input.trial_end

        checkout_params = {
            "customer": input.customer_id,
            "mode": "subscription",
            "line_items": line_items,
            "success_url": input.success_url,
            "cancel_url": input.cancel_url,
            "metadata": input.metadata or {},
            "subscription_data": subscription_data,
        }

        if input.promotion_code_id:
            checkout_params["discounts"] = [{"promotion_code": input.promotion_code_id}]

        checkout_session = client.checkout.Session.create(**checkout_params)
        return checkout_session.url

    @staticmethod
    def create_multi_line_subscription_checkout(
        input: CreateMultiLineSubscriptionCheckoutInput,
        fees_breakdown: Optional[dict] = None,
    ) -> str:
        client = StripeService.get_client()

        line_items = []
        for item in input.line_items:
            product = StripeService.create_product(
                CreateProductInput(name=item.name, metadata=item.metadata)
            )

            price = StripeService.create_recurring_price(
                CreateRecurringPriceInput(
                    product_id=product.id,
                    unit_amount=item.amount_cents,
                    currency="usd",
                    interval=item.interval,
                    interval_count=item.interval_count,
                    metadata=item.metadata,
                )
            )

            line_items.append({"price": price.id, "quantity": 1})

        if fees_breakdown:
            line_items.extend(
                StripeService._build_fee_line_items(fees_breakdown, recurring=True)
            )

        subscription_data = {"metadata": input.subscription_metadata or {}}

        if input.trial_end:
            subscription_data["trial_end"] = input.trial_end

        checkout_params = {
            "customer": input.customer_id,
            "mode": "subscription",
            "line_items": line_items,
            "success_url": input.success_url,
            "cancel_url": input.cancel_url,
            "metadata": input.metadata or {},
            "subscription_data": subscription_data,
        }

        checkout_session = client.checkout.Session.create(**checkout_params)
        return checkout_session.url

    @staticmethod
    def add_subscription_items(
        subscription_id: str,
        items: list[RecurringLineItemInput],
        proration_behavior: ProrationBehavior = ProrationBehavior.CREATE_PRORATIONS,
    ) -> list:
        client = StripeService.get_client()
        created_items = []

        for item in items:
            product = StripeService.create_product(
                CreateProductInput(name=item.name, metadata=item.metadata or {})
            )

            price = StripeService.create_recurring_price(
                CreateRecurringPriceInput(
                    product_id=product.id,
                    unit_amount=item.amount_cents,
                    currency="usd",
                    interval=item.interval,
                    interval_count=item.interval_count,
                    metadata=item.metadata or {},
                )
            )

            subscription_item = client.SubscriptionItem.create(
                subscription=subscription_id,
                price=price.id,
                quantity=1,
                proration_behavior=proration_behavior.value,
            )
            created_items.append(subscription_item)

        return created_items

    @staticmethod
    def remove_subscription_item(subscription_id: str, coverage_type: str):
        client = StripeService.get_client()
        subscription = client.Subscription.retrieve(
            subscription_id, expand=["items.data.price.product"]
        )

        target_item = None
        if coverage_type:
            for item in subscription["items"]["data"]:
                product = item["price"]["product"]
                metadata = (
                    product.get("metadata", {}) if isinstance(product, dict) else {}
                )
                if metadata.get("coverage") == coverage_type:
                    target_item = item
                    break

        if not target_item:
            raise ValueError(
                f"No subscription item matching coverage '{coverage_type}' found."
            )

        client.SubscriptionItem.delete(
            target_item["id"],
            proration_behavior="create_prorations",
        )

    @staticmethod
    def remove_subscription_item_by_product_id(subscription_id: str, product_id: str):
        client = StripeService.get_client()
        subscription = client.Subscription.retrieve(
            subscription_id, expand=["items.data.price.product"]
        )

        target_item = None
        for item in subscription["items"]["data"]:
            product = item["price"]["product"]
            metadata = product.get("metadata", {}) if isinstance(product, dict) else {}
            if metadata.get("product_id") == product_id:
                target_item = item
                break

        if not target_item:
            raise ValueError(
                f"No subscription item matching product_id '{product_id}' found."
            )

        client.SubscriptionItem.delete(
            target_item["id"],
            proration_behavior="create_prorations",
        )

    @staticmethod
    def create_one_time_charge(
        customer_id: str, amount_cents: int, description: str, metadata: dict = None
    ):
        client = StripeService.get_client()

        payment_methods = client.PaymentMethod.list(customer=customer_id, limit=1)
        if not payment_methods.data:
            raise ValueError("No payment method on file for this customer.")

        payment_method = payment_methods.data[0]

        payment_intent = client.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            customer=customer_id,
            payment_method=payment_method.id,
            off_session=True,
            confirm=True,
            description=description,
            metadata=metadata or {},
        )
        return payment_intent

    @staticmethod
    def cancel_subscription(subscription_id: str):
        client = StripeService.get_client()
        client.Subscription.cancel(subscription_id)

    @staticmethod
    def create_refund(payment_intent_id: str, amount_cents: int) -> stripe.Refund:
        client = StripeService.get_client()
        return client.Refund.create(
            payment_intent=payment_intent_id,
            amount=amount_cents,
        )

    @staticmethod
    def update_subscription_price(
        subscription_id: str, new_amount_cents: int, coverage_type: str = None
    ):
        client = StripeService.get_client()
        subscription = client.Subscription.retrieve(
            subscription_id, expand=["items.data.price.product"]
        )

        old_item = None
        if coverage_type:
            for item in subscription["items"]["data"]:
                product = item["price"]["product"]
                metadata = (
                    product.get("metadata", {}) if isinstance(product, dict) else {}
                )
                if metadata.get("coverage") == coverage_type:
                    old_item = item
                    break
        if not old_item:
            if len(subscription["items"]["data"]) == 1:
                old_item = subscription["items"]["data"][0]
            else:
                raise ValueError(
                    f"No subscription item matching coverage '{coverage_type}' found."
                )
        old_price = old_item["price"]

        new_price = client.Price.create(
            unit_amount=new_amount_cents,
            currency="usd",
            recurring={
                "interval": old_price["recurring"]["interval"],
                "interval_count": old_price["recurring"]["interval_count"],
            },
            product=old_price["product"],
        )

        client.Subscription.modify(
            subscription_id,
            items=[
                {
                    "id": old_item["id"],
                    "price": new_price.id,
                }
            ],
            proration_behavior="create_prorations",
        )

    @staticmethod
    def create_billing_portal_session(customer_id: str, return_url: str) -> str:
        client = StripeService.get_client()

        configuration = client.billing_portal.Configuration.create(
            business_profile={
                "headline": "Manage your billing",
            },
            features={
                "subscription_cancel": {"enabled": False},
                "subscription_update": {"enabled": False},
                "payment_method_update": {"enabled": True},
                "invoice_history": {"enabled": True},
            },
        )

        session = client.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
            configuration=configuration.id,
        )
        return session.url

    @staticmethod
    def get_customer_invoices(customer_id: str, limit: int = 10) -> list:
        client = StripeService.get_client()
        invoices = client.Invoice.list(customer=customer_id, limit=limit)
        return invoices.data

    @staticmethod
    def get_customer_charges(customer_id: str, limit: int = 10) -> list:
        client = StripeService.get_client()
        charges = client.Charge.list(customer=customer_id, limit=limit)
        return charges.data

    @staticmethod
    def create_and_send_invoice(
        customer_id: str,
        line_items: list[dict],
        description: str = None,
        metadata: dict = None,
        days_until_due: int = 1,
    ) -> stripe.Invoice:
        client = StripeService.get_client()

        invoice = client.Invoice.create(
            customer=customer_id,
            collection_method="send_invoice",
            days_until_due=days_until_due,
            description=description,
            metadata=metadata or {},
            auto_advance=False,
        )

        for item in line_items:
            client.InvoiceItem.create(
                customer=customer_id,
                invoice=invoice.id,
                amount=item["amount_cents"],
                currency="usd",
                description=item["description"],
                metadata=item.get("metadata", {}),
            )

        invoice = client.Invoice.finalize_invoice(invoice.id)
        client.Invoice.send_invoice(invoice.id)

        return invoice

    @staticmethod
    def get_customer_default_payment_method(customer_id: str):
        client = StripeService.get_client()
        customer = client.Customer.retrieve(customer_id)
        pm = customer.invoice_settings.default_payment_method
        if pm:
            return pm
        payment_methods = client.PaymentMethod.list(
            customer=customer_id, type="card", limit=1
        )
        if payment_methods.data:
            return payment_methods.data[0].id
        return None

    @staticmethod
    def create_direct_subscription(input: CreateDirectSubscriptionInput):
        client = StripeService.get_client()

        payment_method = StripeService.get_customer_default_payment_method(
            input.customer_id
        )
        if not payment_method:
            raise ValueError("Customer has no payment method on file")

        line_items = []
        for item in input.line_items:
            product = StripeService.create_product(
                CreateProductInput(name=item.name, metadata=item.metadata)
            )
            price = StripeService.create_recurring_price(
                CreateRecurringPriceInput(
                    product_id=product.id,
                    unit_amount=item.amount_cents,
                    currency="usd",
                    interval=item.interval,
                    interval_count=item.interval_count,
                    metadata=item.metadata,
                )
            )
            line_items.append({"price": price.id, "quantity": 1})

        subscription = client.Subscription.create(
            customer=input.customer_id,
            items=line_items,
            default_payment_method=payment_method,
            billing_cycle_anchor=input.billing_cycle_anchor,
            proration_behavior="none",
            metadata=input.subscription_metadata or {},
        )
        return subscription

    @staticmethod
    def create_one_time_invoice(customer_id: str, amount_cents: int, description: str):
        client = StripeService.get_client()
        client.InvoiceItem.create(
            customer=customer_id,
            amount=amount_cents,
            currency="usd",
            description=description,
        )
        invoice = client.Invoice.create(
            customer=customer_id,
            auto_advance=True,
        )
        return invoice
