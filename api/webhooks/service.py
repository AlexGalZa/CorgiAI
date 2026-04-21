"""
Webhook service handling Stripe payment events.

Processes the core payment lifecycle events dispatched from the Stripe
webhook endpoint. Creates policies, records payments, handles subscription
creation, payment failures, and cancellations.

Handled events:
- ``checkout.session.completed`` (one-time and subscription modes)
- ``invoice.paid`` (monthly recurring and gap invoices)
- ``invoice.payment_failed`` (marks policies as past_due)
- ``customer.subscription.updated`` (syncs Policy.status / expiration to Stripe)
- ``customer.subscription.deleted`` (cancels policies, sends notifications)
- ``charge.succeeded`` (populates PolicyTransaction.stripe_payout_id once the
  charge settles into a Stripe payout — finance money-tracing per card 2.1).
"""

import logging
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from emails.schemas import SendEmailInput
from emails.service import EmailService
from policies.models import Policy, Payment, PolicyTransaction
from policies.sequences import generate_coi_number
from policies.service import PolicyService
from quotes.models import Quote
from quotes.service import QuoteService
from rating.service import RatingService
from common.utils import stripe_get
from stripe_integration.models import DunningRecord
from stripe_integration.service import StripeService

logger = logging.getLogger(__name__)


class WebhookService:
    @staticmethod
    def handle_successful_payment(session):
        metadata = stripe_get(session, "metadata") or {}
        quote_id = stripe_get(metadata, "quote_id")
        if not quote_id:
            logger.error("No quote_id in session metadata")
            return

        try:
            quote = Quote.objects.get(id=quote_id)
        except Quote.DoesNotExist:
            logger.error(f"Quote {quote_id} not found")
            return

        partial_coverages_str = stripe_get(metadata, "partial_coverages")
        if partial_coverages_str is not None:
            partial_coverages = (
                partial_coverages_str.split(",") if partial_coverages_str else []
            )
            quote = QuoteService.split_quote_for_partial_checkout(
                quote, partial_coverages
            )

        if quote.policies.exists():
            logger.info(f"Quote {quote.quote_number} already has policies")
            return

        effective_date_str = stripe_get(metadata, "effective_date")
        if effective_date_str:
            try:
                effective_date = date.fromisoformat(effective_date_str)
            except ValueError:
                effective_date = date.today()
        else:
            effective_date = date.today()
        expiration_date = effective_date + timedelta(days=365)

        state = quote.company.business_address.state
        purchased_at = timezone.now()
        coi_number = generate_coi_number(state, effective_date)
        breakdown = (
            quote.rating_result.get("breakdown", {}) if quote.rating_result else {}
        )

        promo = (
            StripeService.get_promotion_code(quote.promo_code)
            if quote.promo_code
            else None
        )
        discount_pct = (
            Decimal(str(promo.coupon.percent_off))
            if promo and promo.coupon and promo.coupon.percent_off
            else None
        )
        regulatory_fields = PolicyService.build_regulatory_fields(
            quote, "annual", effective_date, expiration_date
        )

        custom_product_types = set(
            quote.custom_products.values_list("product_type", flat=True)
        )

        policies = []
        quote_carrier = PolicyService.get_carrier_for_quote(quote)
        for coverage in quote.coverages:
            if coverage in custom_product_types:
                continue
            coverage_premium_data = breakdown.get(coverage, {})
            coverage_premium = (
                Decimal(str(coverage_premium_data.get("premium", 0)))
                if coverage_premium_data
                else Decimal("0")
            )

            if coverage_premium == 0 and quote.quote_amount:
                coverage_premium = Decimal(str(quote.quote_amount)) / len(
                    quote.coverages
                )

            if promo:
                coverage_premium = Decimal(
                    str(
                        RatingService.apply_promo_discount(
                            float(coverage_premium), promo
                        )
                    )
                )

            coverage_limits = quote.limits_retentions.get(coverage, {})

            policy = Policy.objects.create(
                quote=quote,
                coverage_type=coverage,
                coi_number=coi_number,
                limits_retentions=coverage_limits,
                premium=coverage_premium,
                promo_code=quote.promo_code,
                discount_percentage=discount_pct,
                effective_date=effective_date,
                expiration_date=expiration_date,
                purchased_at=purchased_at,
                stripe_payment_intent_id=stripe_get(session, "payment_intent"),
                stripe_customer_id=stripe_get(session, "customer"),
                status="active",
                carrier=quote_carrier,
                **regulatory_fields,
            )
            PolicyService.create_transaction_and_allocation(policy)
            policies.append(policy)

        for custom_product in quote.custom_products.all():
            custom_premium = Decimal(str(custom_product.price))
            brokered_policy = Policy.objects.create(
                quote=quote,
                coverage_type=custom_product.product_type,
                coi_number=coi_number,
                limits_retentions={
                    "aggregate_limit": custom_product.aggregate_limit,
                    "per_occurrence_limit": custom_product.per_occurrence_limit,
                    "retention": custom_product.retention,
                },
                premium=custom_premium,
                effective_date=effective_date,
                expiration_date=expiration_date,
                purchased_at=purchased_at,
                stripe_payment_intent_id=stripe_get(session, "payment_intent"),
                stripe_customer_id=stripe_get(session, "customer"),
                status="active",
                is_brokered=True,
                carrier=custom_product.carrier or "",
                **regulatory_fields,
            )
            PolicyService.create_transaction_and_allocation(brokered_policy)
            policies.append(brokered_policy)

        quote.status = "purchased"
        quote.save()

        payment_intent_id = stripe_get(session, "payment_intent")
        for policy in policies:
            Payment.objects.create(
                policy=policy,
                stripe_invoice_id=payment_intent_id,
                amount=policy.premium,
                status="paid",
                paid_at=purchased_at,
            )

        PolicyService.generate_documents_and_send_email(policies, coi_number)

    @staticmethod
    def handle_subscription_created(session):
        metadata = stripe_get(session, "metadata") or {}
        quote_id = stripe_get(metadata, "quote_id")
        if not quote_id:
            logger.error("No quote_id in subscription session metadata")
            return

        try:
            quote = Quote.objects.get(id=quote_id)
        except Quote.DoesNotExist:
            logger.error(f"Quote {quote_id} not found for subscription")
            return

        partial_coverages_str = stripe_get(metadata, "partial_coverages")
        if partial_coverages_str is not None:
            partial_coverages = (
                partial_coverages_str.split(",") if partial_coverages_str else []
            )
            quote = QuoteService.split_quote_for_partial_checkout(
                quote, partial_coverages
            )

        if quote.policies.exists():
            logger.info(f"Quote {quote.quote_number} already has policies")
            return

        subscription_id = stripe_get(session, "subscription")
        customer_id = stripe_get(session, "customer")

        effective_date_str = stripe_get(metadata, "effective_date")
        if effective_date_str:
            try:
                effective_date = date.fromisoformat(effective_date_str)
            except ValueError:
                effective_date = date.today()
        else:
            effective_date = date.today()
        expiration_date = effective_date + timedelta(days=365)

        state = quote.company.business_address.state
        purchased_at = timezone.now()
        coi_number = generate_coi_number(state, effective_date)
        breakdown = (
            quote.rating_result.get("breakdown", {}) if quote.rating_result else {}
        )

        promo = (
            StripeService.get_promotion_code(quote.promo_code)
            if quote.promo_code
            else None
        )
        discount_pct = (
            Decimal(str(promo.coupon.percent_off))
            if promo and promo.coupon and promo.coupon.percent_off
            else None
        )
        regulatory_fields = PolicyService.build_regulatory_fields(
            quote, "monthly", effective_date, expiration_date
        )

        custom_product_types = set(
            quote.custom_products.values_list("product_type", flat=True)
        )

        policies = []
        quote_carrier = PolicyService.get_carrier_for_quote(quote)
        for coverage in quote.coverages:
            if coverage in custom_product_types:
                continue
            coverage_premium_data = breakdown.get(coverage, {})
            base_premium = (
                Decimal(str(coverage_premium_data.get("premium", 0)))
                if coverage_premium_data
                else Decimal("0")
            )

            if base_premium == 0 and quote.quote_amount:
                base_premium = Decimal(str(quote.quote_amount)) / len(quote.coverages)

            if promo:
                base_premium = Decimal(
                    str(RatingService.apply_promo_discount(float(base_premium), promo))
                )

            amounts = RatingService.calculate_billing_amounts(base_premium, "monthly")
            coverage_premium = amounts["annual"]
            monthly_premium = amounts["monthly"]
            coverage_limits = quote.limits_retentions.get(coverage, {})

            policy = Policy.objects.create(
                quote=quote,
                coverage_type=coverage,
                coi_number=coi_number,
                limits_retentions=coverage_limits,
                premium=coverage_premium,
                monthly_premium=monthly_premium,
                promo_code=quote.promo_code,
                discount_percentage=discount_pct,
                billing_frequency="monthly",
                effective_date=effective_date,
                expiration_date=expiration_date,
                purchased_at=purchased_at,
                stripe_subscription_id=subscription_id,
                stripe_customer_id=customer_id,
                status="active",
                carrier=quote_carrier,
                **regulatory_fields,
            )
            PolicyService.create_transaction_and_allocation(policy)
            policies.append(policy)

        for custom_product in quote.custom_products.all():
            brokered_premium = Decimal(str(custom_product.price))
            brokered_monthly = brokered_premium / 12
            brokered_policy = Policy.objects.create(
                quote=quote,
                coverage_type=custom_product.product_type,
                coi_number=coi_number,
                limits_retentions={
                    "aggregate_limit": custom_product.aggregate_limit,
                    "per_occurrence_limit": custom_product.per_occurrence_limit,
                    "retention": custom_product.retention,
                },
                premium=brokered_premium,
                monthly_premium=brokered_monthly,
                billing_frequency="monthly",
                effective_date=effective_date,
                expiration_date=expiration_date,
                purchased_at=purchased_at,
                stripe_subscription_id=subscription_id,
                stripe_customer_id=customer_id,
                status="active",
                is_brokered=True,
                carrier=custom_product.carrier or "",
                **regulatory_fields,
            )
            PolicyService.create_transaction_and_allocation(brokered_policy)
            policies.append(brokered_policy)

        quote.status = "purchased"
        quote.save()

        PolicyService.generate_documents_and_send_email(policies, coi_number)

    @staticmethod
    def _apply_endorsement_from_invoice(invoice, invoice_id: str):
        """Apply a limit-increase endorsement (H7) once the customer has paid.

        Dispatched from :meth:`handle_invoice_paid` when
        ``invoice.metadata['type'] == 'endorsement'``. Looks up the referenced
        Policy, re-uses :meth:`PolicyService.endorse_modify_limits` to bump
        the aggregate limit and regenerate COI documents.

        Invoice metadata contract (set by
        ``POST /policies/{id}/endorsement-invoice``):
            type: 'endorsement'
            policy_id: str  — Policy pk
            coverage: str   — Policy.coverage_type
            current_limit: str
            new_limit: str
            new_premium: str
            old_premium: str
            prorated_delta: str
            reason: str
        """
        metadata = stripe_get(invoice, "metadata") or {}
        policy_id = stripe_get(metadata, "policy_id")
        new_limit_raw = stripe_get(metadata, "new_limit")
        new_premium_raw = stripe_get(metadata, "new_premium")
        reason = stripe_get(metadata, "reason") or "Pay-as-you-go endorsement"

        if not (policy_id and new_limit_raw and new_premium_raw):
            logger.error(
                f"Endorsement invoice {invoice_id} missing required metadata "
                f"(policy_id={policy_id!r}, new_limit={new_limit_raw!r}, "
                f"new_premium={new_premium_raw!r})"
            )
            return

        try:
            policy = Policy.objects.get(pk=int(policy_id), is_deleted=False)
        except (Policy.DoesNotExist, ValueError):
            logger.error(
                f"Endorsement invoice {invoice_id}: Policy {policy_id} not found"
            )
            return

        if Payment.objects.filter(stripe_invoice_id=invoice_id, status="paid").exists():
            logger.info(f"Endorsement invoice {invoice_id} already processed")
            return

        try:
            new_limit = int(new_limit_raw)
            new_premium = Decimal(str(new_premium_raw))
        except (TypeError, ValueError) as e:
            logger.error(
                f"Endorsement invoice {invoice_id} has malformed metadata: {e}"
            )
            return

        # Build new limits dict — preserve retention / per-occurrence layers
        # from the existing policy and overwrite only the aggregate limit.
        new_limits = dict(policy.limits_retentions or {})
        new_limits["aggregate_limit"] = new_limit
        if "per_occurrence_limit" in new_limits:
            # Keep per-occurrence in lockstep with aggregate if they were equal
            if new_limits.get("per_occurrence_limit") == (
                policy.limits_retentions or {}
            ).get("aggregate_limit"):
                new_limits["per_occurrence_limit"] = new_limit

        try:
            PolicyService.endorse_modify_limits(
                policy=policy,
                new_limits=new_limits,
                new_premium=new_premium,
                admin_reason=f"Pay-as-you-go endorsement (invoice {invoice_id}): {reason}",
            )
        except Exception as e:
            logger.exception(
                f"Failed to apply endorsement for policy {policy.policy_number} from invoice {invoice_id}: {e}"
            )
            return

        amount_cents = stripe_get(invoice, "amount_paid", 0)
        Payment.objects.create(
            policy=policy,
            stripe_invoice_id=invoice_id,
            amount=Decimal(str(amount_cents)) / Decimal("100"),
            status="paid",
            paid_at=timezone.now(),
        )
        logger.info(
            f"Endorsement applied to policy {policy.policy_number}: "
            f"aggregate_limit -> {new_limit:,}, new premium ${new_premium} "
            f"(invoice {invoice_id})"
        )

    @staticmethod
    def handle_invoice_paid(invoice):
        invoice_id = stripe_get(invoice, "id")
        status_transitions = stripe_get(invoice, "status_transitions") or {}
        paid_at_timestamp = stripe_get(status_transitions, "paid_at")
        paid_at = (
            datetime.fromtimestamp(paid_at_timestamp, tz=dt_timezone.utc)
            if paid_at_timestamp
            else timezone.now()
        )

        # H7: pay-as-you-go endorsement invoices — applied only after payment.
        invoice_metadata = stripe_get(invoice, "metadata") or {}
        if stripe_get(invoice_metadata, "type") == "endorsement":
            WebhookService._apply_endorsement_from_invoice(invoice, invoice_id)
            return

        pending_payments = Payment.objects.filter(
            stripe_invoice_id=invoice_id, status="pending"
        )
        if pending_payments.exists():
            pending_payments.update(status="paid", paid_at=paid_at)
            logger.info(
                f"Invoice {invoice_id}: updated {pending_payments.count()} pending payment(s) to paid"
            )
            return

        if Payment.objects.filter(stripe_invoice_id=invoice_id, status="paid").exists():
            logger.info(f"Invoice {invoice_id} already processed")
            return

        subscription_id = stripe_get(invoice, "subscription")
        status = stripe_get(invoice, "status", "paid")

        if subscription_id:
            policies = Policy.objects.filter(stripe_subscription_id=subscription_id)
            if not policies.exists():
                logger.warning(f"No policies found for subscription {subscription_id}")
                return

            for policy in policies:
                Payment.objects.create(
                    policy=policy,
                    stripe_invoice_id=invoice_id,
                    amount=policy.monthly_premium or Decimal("0"),
                    status=status,
                    paid_at=paid_at,
                )
                update_fields = ["paid_to_date"]
                if policy.paid_to_date:
                    policy.paid_to_date += relativedelta(months=1)
                if policy.status == "past_due":
                    policy.status = "active"
                    update_fields.append("status")
                    logger.info(
                        f"Policy {policy.policy_number} recovered from past_due to active"
                    )

                    # Resolve any active dunning records
                    now_ts = timezone.now()
                    DunningRecord.objects.filter(
                        policy=policy,
                        status="active",
                    ).update(
                        status="resolved",
                        resolved_at=now_ts,
                        next_retry_at=None,
                    )
                    logger.info(
                        f"Dunning records resolved for policy {policy.policy_number}"
                    )

                policy.save(update_fields=update_fields)

            policy_numbers = [p.policy_number for p in policies]
            logger.info(
                f"Monthly payment recorded for policies: {', '.join(policy_numbers)}"
            )
        else:
            metadata = stripe_get(invoice, "metadata") or {}
            quote_number = stripe_get(metadata, "quote_number")
            if not quote_number:
                logger.info(
                    f"Invoice {invoice_id} has no subscription or quote_number, skipping"
                )
                return

            try:
                quote = Quote.objects.get(quote_number=quote_number)
            except Quote.DoesNotExist:
                logger.warning(
                    f"Quote {quote_number} not found for invoice {invoice_id}"
                )
                return

            policies = quote.policies.filter(
                is_brokered=True, billing_frequency="annual"
            )
            if not policies.exists():
                logger.warning(
                    f"No annual brokered policies found for quote {quote_number}"
                )
                return

            total_amount = stripe_get(invoice, "amount_paid", 0) / 100
            per_policy_amount = Decimal(str(total_amount)) / policies.count()

            for policy in policies:
                if Payment.objects.filter(
                    policy=policy, stripe_invoice_id=invoice_id
                ).exists():
                    continue
                Payment.objects.create(
                    policy=policy,
                    stripe_invoice_id=invoice_id,
                    amount=per_policy_amount,
                    status=status,
                    paid_at=paid_at,
                )

            policy_numbers = [p.policy_number for p in policies]
            logger.info(
                f"Annual brokered payment recorded for policies: {', '.join(policy_numbers)}"
            )

    # Map Stripe subscription statuses → Policy.status values
    SUBSCRIPTION_STATUS_MAP = {
        "active": "active",
        "trialing": "active",
        "past_due": "past_due",
        "unpaid": "past_due",
        "incomplete": "past_due",
        "incomplete_expired": "cancelled",
        "canceled": "cancelled",
    }

    @staticmethod
    def handle_subscription_updated(subscription):
        """Sync Policy status and expiration from a Stripe subscription update.

        Fired whenever a ``customer.subscription.updated`` event arrives.
        Looks up all policies linked to the subscription and reconciles:

        * ``Policy.status`` — mapped from ``subscription.status`` via
          :attr:`WebhookService.SUBSCRIPTION_STATUS_MAP`.
        * ``Policy.expiration_date`` — advanced to ``current_period_end``
          if Stripe reports a date later than what Django currently holds
          (e.g. after a renewal extension). Never rolls backward.

        Any drift between Django state and Stripe state is logged.
        """
        subscription_id = stripe_get(subscription, "id")
        if not subscription_id:
            logger.error("customer.subscription.updated event missing id")
            return

        policies = list(Policy.objects.filter(stripe_subscription_id=subscription_id))
        if not policies:
            logger.warning(
                f"No policies found for updated subscription {subscription_id}"
            )
            return

        stripe_status = stripe_get(subscription, "status")
        target_status = WebhookService.SUBSCRIPTION_STATUS_MAP.get(stripe_status)
        if stripe_status and not target_status:
            logger.warning(
                f"Unmapped Stripe subscription status '{stripe_status}' for "
                f"subscription {subscription_id} — leaving Policy.status untouched"
            )

        current_period_end_ts = stripe_get(subscription, "current_period_end")
        new_expiration = None
        if current_period_end_ts:
            try:
                new_expiration = datetime.fromtimestamp(
                    current_period_end_ts, tz=dt_timezone.utc
                ).date()
            except (TypeError, ValueError, OSError):
                logger.warning(
                    f"Invalid current_period_end={current_period_end_ts!r} on subscription {subscription_id}"
                )
                new_expiration = None

        for policy in policies:
            update_fields: list[str] = []

            if target_status and policy.status != target_status:
                logger.info(
                    f"Policy {policy.policy_number}: status drift "
                    f"{policy.status!r} -> {target_status!r} (stripe_status="
                    f"{stripe_status!r}, subscription={subscription_id})"
                )
                policy.status = target_status
                update_fields.append("status")

            # Only extend expiration forward (renewals), never roll back.
            if new_expiration and policy.expiration_date != new_expiration:
                if new_expiration > policy.expiration_date:
                    logger.info(
                        f"Policy {policy.policy_number}: expiration_date drift "
                        f"{policy.expiration_date} -> {new_expiration} "
                        f"(subscription={subscription_id})"
                    )
                    policy.expiration_date = new_expiration
                    update_fields.append("expiration_date")
                else:
                    logger.info(
                        f"Policy {policy.policy_number}: Stripe period_end "
                        f"{new_expiration} earlier than current expiration "
                        f"{policy.expiration_date}; not rolling back"
                    )

            if update_fields:
                policy.save(update_fields=update_fields, skip_validation=True)
            else:
                logger.debug(
                    f"Policy {policy.policy_number}: no drift vs subscription {subscription_id}"
                )

    @staticmethod
    def handle_subscription_cancelled(subscription):
        subscription_id = stripe_get(subscription, "id")
        policies = list(
            Policy.objects.select_related(
                "quote__user", "quote__company", "quote__company__business_address"
            ).filter(stripe_subscription_id=subscription_id)
        )

        if not policies:
            logger.warning(
                f"No policies found for cancelled subscription {subscription_id}"
            )
            return

        policies_to_cancel = [p for p in policies if p.status != "cancelled"]

        if not policies_to_cancel:
            logger.info(
                f"All policies for subscription {subscription_id} already cancelled, skipping"
            )
            return

        coi_number = policies_to_cancel[0].coi_number

        for policy in policies_to_cancel:
            policy.status = "cancelled"
            policy.expiration_date = date.today()
            policy.save(update_fields=["status", "expiration_date"])
            logger.info(
                f"Policy {policy.policy_number} cancelled due to subscription cancellation"
            )

            PolicyService.create_cancellation_transaction_for_nonpayment(policy)

        if coi_number:
            remaining_siblings = list(
                Policy.objects.filter(coi_number=coi_number, status="active")
            )
            if remaining_siblings:
                PolicyService._regenerate_coi_documents(remaining_siblings, coi_number)

        # Detect voluntary vs non-voluntary cancellation. Stripe surfaces this
        # via `cancellation_details.reason`. Non-voluntary (payment_failed) gets
        # the reinstatement flow; voluntary cancellations do not.
        cancellation_details = stripe_get(subscription, "cancellation_details") or {}
        cancellation_reason = stripe_get(cancellation_details, "reason") or ""
        is_non_voluntary = cancellation_reason in ("payment_failed", "")

        try:
            first_policy = policies_to_cancel[0]
            user = first_policy.quote.user
            company_name = (
                first_policy.quote.company.entity_legal_name
                if first_policy.quote.company
                else ""
            )
            coverage_types = [p.coverage_type for p in policies_to_cancel]
            policy_numbers = ", ".join(p.policy_number for p in policies_to_cancel)

            html = render_to_string(
                "emails/policy_cancelled.html",
                {
                    "contact_name": user.get_full_name() or user.email,
                    "company_name": company_name,
                    "policy_numbers": policy_numbers,
                    "coverages": coverage_types,
                    "effective_date": first_policy.effective_date,
                    "expiration_date": first_policy.expiration_date,
                },
            )

            EmailService.send(
                SendEmailInput(
                    to=[user.email],
                    subject=f"Policy Cancellation Notice: {policy_numbers}",
                    html=html,
                    from_email=settings.HELLO_CORGI_EMAIL,
                )
            )

            EmailService.send(
                SendEmailInput(
                    to=[settings.CORGI_NOTIFICATION_EMAIL],
                    subject=f"Policy Cancelled (Non-Payment): {policy_numbers}",
                    html=html,
                    from_email=settings.HELLO_CORGI_EMAIL,
                )
            )
        except Exception as e:
            logger.exception(f"Failed to send cancellation email: {e}")

        # Fire reinstatement email for non-voluntary (payment-failure) cancellations.
        # Gives the customer a one-click deep link back to the self-serve reinstate page.
        if is_non_voluntary:
            try:
                from policies.api import generate_reinstatement_token

                first_policy = policies_to_cancel[0]
                user = first_policy.quote.user
                company_name = (
                    first_policy.quote.company.entity_legal_name
                    if first_policy.quote.company
                    else ""
                )
                coverage_types = [p.coverage_type for p in policies_to_cancel]
                policy_numbers = ", ".join(p.policy_number for p in policies_to_cancel)

                token = generate_reinstatement_token(first_policy.pk)
                reinstate_url = f"{settings.PORTAL_BASE_URL}/reinstate/{token}"

                reinstate_html = render_to_string(
                    "emails/policy_reinstatement.html",
                    {
                        "contact_name": user.get_full_name() or user.email,
                        "company_name": company_name,
                        "policy_numbers": policy_numbers,
                        "coverages": coverage_types,
                        "effective_date": first_policy.effective_date,
                        "expiration_date": first_policy.expiration_date,
                        "reinstate_url": reinstate_url,
                    },
                )

                EmailService.send(
                    SendEmailInput(
                        to=[user.email],
                        subject=f"Reinstate your policy: {policy_numbers}",
                        html=reinstate_html,
                        from_email=settings.HELLO_CORGI_EMAIL,
                    )
                )
                logger.info(
                    f"Reinstatement email sent to {user.email} for policies {policy_numbers}"
                )
            except Exception as e:
                logger.exception(f"Failed to send reinstatement email: {e}")

    @staticmethod
    def handle_invoice_payment_failed(invoice):
        subscription_id = stripe_get(invoice, "subscription")
        if not subscription_id:
            logger.info(
                f"Invoice {stripe_get(invoice, 'id')} payment failed but has no subscription, skipping"
            )
            return

        policies = Policy.objects.select_related(
            "quote__user", "quote__company"
        ).filter(stripe_subscription_id=subscription_id)
        if not policies.exists():
            logger.warning(
                f"No policies found for subscription {subscription_id} (payment failed)"
            )
            return

        invoice_id = stripe_get(invoice, "id")
        amount_due = stripe_get(invoice, "amount_due", 0) / 100

        if Payment.objects.filter(
            stripe_invoice_id=invoice_id, status="failed"
        ).exists():
            return

        now = timezone.now()
        for policy in policies:
            Payment.objects.create(
                policy=policy,
                stripe_invoice_id=invoice_id,
                amount=policy.monthly_premium or Decimal(str(amount_due)),
                status="failed",
                paid_at=now,
            )
            if policy.status == "active":
                policy.status = "past_due"
                policy.save(update_fields=["status"])
                logger.info(
                    f"Policy {policy.policy_number} marked as past_due due to failed payment"
                )

            # Create or update DunningRecord for this policy
            existing_dunning = DunningRecord.objects.filter(
                policy=policy,
                status="active",
            ).first()

            if not existing_dunning:
                # First failure — create a new dunning record and schedule day-1 retry
                dunning = DunningRecord(
                    policy=policy,
                    attempt_count=1,
                    first_failed_at=now,
                    stripe_invoice_id=invoice_id,
                    stripe_subscription_id=subscription_id,
                )
                dunning.schedule_next_retry()
                dunning.save()
                logger.info(
                    f"DunningRecord created for policy {policy.policy_number}, next retry at {dunning.next_retry_at}"
                )
            else:
                # Update existing record with latest invoice
                existing_dunning.stripe_invoice_id = invoice_id
                existing_dunning.save(update_fields=["stripe_invoice_id"])
                logger.info(
                    f"DunningRecord {existing_dunning.pk} updated with new invoice {invoice_id}"
                )

        try:
            first_policy = policies[0]
            customer_email = first_policy.quote.user.email
            company_name = (
                first_policy.quote.company.entity_legal_name
                if first_policy.quote.company
                else "Unknown"
            )
            coverage_types = ", ".join(p.coverage_type for p in policies)
            policy_numbers = ", ".join(p.policy_number for p in policies)

            html = render_to_string(
                "emails/payment_failed.html",
                {
                    "policy_numbers": policy_numbers,
                    "customer_email": customer_email,
                    "company_name": company_name,
                    "coverage_types": coverage_types,
                    "amount_due": f"{amount_due:,.2f}",
                    "admin_url": f"{settings.PORTAL_BASE_URL}/admin/policies/policy/{first_policy.id}/change/",
                },
            )

            EmailService.send(
                SendEmailInput(
                    to=[settings.CORGI_NOTIFICATION_EMAIL],
                    subject=f"Payment Failed: {policy_numbers}",
                    html=html,
                    from_email=settings.HELLO_CORGI_EMAIL,
                )
            )

            # Send customer-facing payment failed email
            user = first_policy.quote.user
            billing_portal_url = (
                StripeService.create_billing_portal_session(
                    first_policy.stripe_customer_id,
                    return_url=f"{settings.PORTAL_BASE_URL}/billing",
                )
                if first_policy.stripe_customer_id
                else f"{settings.PORTAL_BASE_URL}/billing"
            )

            customer_html = render_to_string(
                "emails/payment_failed_customer.html",
                {
                    "first_name": user.first_name or user.get_full_name() or "there",
                    "amount": f"{amount_due:,.2f}",
                    "policy_number": policy_numbers,
                    "coverage_type": coverage_types,
                    "billing_portal_url": billing_portal_url,
                },
            )

            EmailService.send(
                SendEmailInput(
                    to=[customer_email],
                    subject=f"Action Required: Payment Failed for Policy {policy_numbers}",
                    html=customer_html,
                    from_email=settings.HELLO_CORGI_EMAIL,
                )
            )
            logger.info(
                f"Payment failed notification sent to customer {customer_email} for policies {policy_numbers}"
            )
        except Exception as e:
            logger.exception(f"Failed to send payment failed notification: {e}")

        # Notify the Account Executive assigned to each affected policy.
        # PolicyProducer links Policy -> Producer (producer_type='ae').
        # If no AE is assigned we log and skip, per Trello card 3.3.
        try:
            from producers.models import PolicyProducer
        except Exception:
            PolicyProducer = None
            logger.exception(
                "Could not import PolicyProducer; skipping AE notifications"
            )

        if PolicyProducer is not None:
            hosted_invoice_url = stripe_get(invoice, "hosted_invoice_url") or ""
            invoice_number = stripe_get(invoice, "number") or invoice_id

            for policy in policies:
                try:
                    ae_assignment = (
                        PolicyProducer.objects.select_related("producer")
                        .filter(
                            policy=policy,
                            producer__producer_type="ae",
                            producer__is_active=True,
                        )
                        .first()
                    )
                    if not ae_assignment:
                        logger.warning(
                            f"No AE assigned to policy {policy.policy_number}; skipping AE payment-failed notification"
                        )
                        continue

                    ae = ae_assignment.producer
                    if not ae.email:
                        logger.warning(
                            f"AE {ae.name} for policy {policy.policy_number} has no email on file; "
                            f"skipping AE payment-failed notification"
                        )
                        continue

                    ae_first_name = ae.name.split(" ", 1)[0] if ae.name else "there"
                    company_name_for_policy = (
                        policy.quote.company.entity_legal_name
                        if policy.quote and policy.quote.company
                        else "Unknown"
                    )
                    customer_email_for_policy = (
                        policy.quote.user.email
                        if policy.quote and policy.quote.user
                        else ""
                    )
                    policy_amount_due = policy.monthly_premium or Decimal(
                        str(amount_due)
                    )

                    ae_html = render_to_string(
                        "emails/ae_payment_failed.html",
                        {
                            "ae_first_name": ae_first_name,
                            "policy_number": policy.policy_number,
                            "company_name": company_name_for_policy,
                            "customer_email": customer_email_for_policy,
                            "amount_due": f"{policy_amount_due:,.2f}",
                            "invoice_url": hosted_invoice_url,
                            "invoice_number": invoice_number,
                        },
                    )

                    EmailService.send(
                        SendEmailInput(
                            to=[ae.email],
                            subject=f"Customer Payment Failed: {policy.policy_number} ({company_name_for_policy})",
                            html=ae_html,
                            from_email=settings.HELLO_CORGI_EMAIL,
                        )
                    )
                    logger.info(
                        f"AE payment-failed notification sent to {ae.email} for policy {policy.policy_number}"
                    )
                except Exception as e:
                    logger.exception(
                        f"Failed to send AE payment-failed notification for policy "
                        f"{getattr(policy, 'policy_number', '?')}: {e}"
                    )

    @staticmethod
    def _extract_payout_id(charge) -> str | None:
        """Pull the payout ID off a Stripe charge event.

        A Stripe charge may surface its payout in two places:

        1. ``charge.payout`` — set once the charge's funds have been grouped
           into a payout. May be null immediately after ``charge.succeeded``
           if the payout hasn't been created yet.
        2. ``charge.balance_transaction.payout`` — present when the balance
           transaction has been expanded. This is the canonical source once
           the payout is known.

        Returns the payout ID string, or ``None`` if neither location has
        it (the backfill command will eventually populate it later).
        """
        payout_id = stripe_get(charge, "payout")
        if payout_id:
            return payout_id

        balance_txn = stripe_get(charge, "balance_transaction")
        if isinstance(balance_txn, dict):
            nested = stripe_get(balance_txn, "payout")
            if nested:
                return nested

        return None

    @staticmethod
    def handle_charge_succeeded(charge):
        """Record the Stripe payout ID on matching PolicyTransaction rows.

        Triggered by ``charge.succeeded`` events. Locates every
        ``PolicyTransaction`` whose policy was paid via ``charge.payment_intent``
        and stamps ``stripe_payout_id`` so finance can trace money from a
        policy to the Stripe bank deposit that settled it.

        A single charge may fan out to multiple policy transactions when the
        customer purchased bundled coverages on one payment intent — update
        every matching row, not just one.

        Refs Trello card 2.1.
        """
        charge_id = stripe_get(charge, "id") or "<unknown>"
        payment_intent_id = stripe_get(charge, "payment_intent")
        if not payment_intent_id:
            logger.info(
                f"charge.succeeded {charge_id}: no payment_intent on charge, skipping payout attribution"
            )
            return

        payout_id = WebhookService._extract_payout_id(charge)
        if not payout_id:
            logger.info(
                f"charge.succeeded {charge_id}: charge has no payout yet "
                f"(payment_intent={payment_intent_id}); backfill will catch it"
            )
            return

        policies = list(
            Policy.objects.filter(stripe_payment_intent_id=payment_intent_id)
        )
        if not policies:
            logger.warning(
                f"charge.succeeded {charge_id}: no policies linked to payment_intent {payment_intent_id}"
            )
            return

        transactions = PolicyTransaction.objects.filter(policy__in=policies)
        updated = transactions.update(stripe_payout_id=payout_id)
        logger.info(
            f"charge.succeeded {charge_id}: stamped payout {payout_id} on "
            f"{updated} PolicyTransaction row(s) across "
            f"{len(policies)} policy/policies (payment_intent={payment_intent_id})"
        )
