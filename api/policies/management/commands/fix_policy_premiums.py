import time
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import stripe
from django.conf import settings
from django.core.management.base import BaseCommand

from policies.models import Payment, Policy


TWO_PLACES = Decimal("0.01")

COVERAGE_MAP = {
    "commercial general liability": "commercial-general-liability",
    "cyber liability": "cyber-liability",
    "technology errors & omissions": "technology-errors-and-omissions",
    "tech professional liability": "technology-errors-and-omissions",  # legacy name
    "tech e&o": "technology-errors-and-omissions",
    "directors & officers liability": "directors-and-officers",
    "directors and officers liability": "directors-and-officers",
    "employment practices liability": "employment-practices-liability",
    "media liability": "media-liability",
    "fiduciary liability": "fiduciary-liability",
    "hired & non-owned auto": "hired-and-non-owned-auto",
    "crime / fidelity": "crime-fidelity",
    "harassment prevention": "harassment-prevention",
}

# Products in Stripe subscriptions that are NOT RRG coverages.
# These should be excluded from the proportional split total.
NON_RRG_PRODUCT_KEYWORDS = [
    "worker",
    "compensation",
    "commercial property",
    "bop",
    "cgl excess",
    "excess",
]


class Command(BaseCommand):
    help = "Fix policy premiums and payments using Stripe as the source of truth."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Preview changes without saving"
        )
        parser.add_argument(
            "--month", type=int, required=True, help="Month to fix (1-12)"
        )
        parser.add_argument("--year", type=int, required=True, help="Year to fix")
        parser.add_argument(
            "--stripe-key", type=str, help="Stripe secret key (defaults to settings)"
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        month = options["month"]
        year = options["year"]
        stripe.api_key = options["stripe_key"] or settings.STRIPE_SECRET_KEY

        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year, 12, 31)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        policies = (
            Policy.objects.filter(
                is_brokered=False,
                effective_date__lte=last_day,
                expiration_date__gte=first_day,
            )
            .select_related("quote")
            .order_by("stripe_subscription_id", "policy_number")
        )

        sub_cache = {}
        fixed_count = 0
        payment_fixed_count = 0
        skipped = []

        for policy in policies:
            result = self._get_expected_amounts(policy, sub_cache)
            if result is None:
                skipped.append(policy.policy_number)
                continue

            expected_premium, expected_monthly, source = result

            premium_changed = policy.premium != expected_premium
            monthly_changed = (
                policy.billing_frequency == "monthly"
                and policy.monthly_premium != expected_monthly
            )

            if not premium_changed and not monthly_changed:
                payments_to_fix = self._get_payment_fixes(
                    policy, expected_premium, expected_monthly
                )
                if not payments_to_fix:
                    continue

            self.stdout.write(
                f"{policy.policy_number} ({policy.billing_frequency}) [{source}]:"
            )

            if premium_changed:
                self.stdout.write(f"  premium ${policy.premium} -> ${expected_premium}")
            if monthly_changed:
                self.stdout.write(
                    f"  monthly ${policy.monthly_premium} -> ${expected_monthly}"
                )

            if not dry_run:
                update_fields = []
                if premium_changed:
                    policy.premium = expected_premium
                    update_fields.append("premium")
                if monthly_changed:
                    policy.monthly_premium = expected_monthly
                    update_fields.append("monthly_premium")
                if update_fields:
                    policy.save(update_fields=update_fields)

            payments_to_fix = self._get_payment_fixes(
                policy, expected_premium, expected_monthly
            )
            for payment, new_amount in payments_to_fix:
                self.stdout.write(
                    f"  Payment {payment.id} ({payment.paid_at}): ${payment.amount} -> ${new_amount}"
                )
                if not dry_run:
                    payment.amount = new_amount
                    payment.save(update_fields=["amount"])
                payment_fixed_count += 1

            fixed_count += 1

        action = "Would fix" if dry_run else "Fixed"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{action} {fixed_count} policies, {payment_fixed_count} payments"
            )
        )
        if skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {len(skipped)} policies (no Stripe data or rating breakdown)"
                )
            )

    def _get_expected_amounts(self, policy, sub_cache):
        if policy.billing_frequency == "monthly" and policy.stripe_subscription_id:
            return self._from_stripe_subscription(policy, sub_cache)
        elif policy.billing_frequency == "annual" and policy.stripe_payment_intent_id:
            return self._from_stripe_payment_intent(policy, sub_cache)
        elif policy.billing_frequency == "annual":
            return self._from_rating_proportional_annual(policy)
        return None

    def _from_stripe_subscription(self, policy, sub_cache):
        sub_id = policy.stripe_subscription_id
        if sub_id not in sub_cache:
            try:
                sub = stripe.Subscription.retrieve(
                    sub_id, expand=["items.data.price.product"]
                )
                sub_cache[sub_id] = sub
                time.sleep(0.05)
            except Exception:
                sub_cache[sub_id] = None

        sub = sub_cache.get(sub_id)
        if not sub:
            return None

        items = sub["items"]["data"]

        for item in items:
            product = item["price"]["product"]
            name = product["name"].lower() if isinstance(product, dict) else ""
            mapped = COVERAGE_MAP.get(name, "")
            if mapped == policy.coverage_type:
                stripe_monthly = Decimal(str(item["price"]["unit_amount"])) / 100
                stripe_annual = (stripe_monthly * 12).quantize(
                    TWO_PLACES, rounding=ROUND_HALF_UP
                )
                return stripe_annual, stripe_monthly, "stripe-per-coverage"

        # Only include RRG-related line items in the total.
        # Exclude non-RRG products (Worker's Comp, Commercial Property, etc.)
        rrg_monthly_cents = 0
        for item in items:
            product = item["price"]["product"]
            name = product["name"].lower() if isinstance(product, dict) else ""
            if self._is_non_rrg_product(name):
                continue
            rrg_monthly_cents += item["price"]["unit_amount"]

        if rrg_monthly_cents <= 0:
            return None

        total_monthly = Decimal(str(rrg_monthly_cents)) / 100

        return self._split_proportional(policy, total_monthly, "stripe-proportional")

    @staticmethod
    def _is_non_rrg_product(name):
        """Check if a Stripe product name is a non-RRG coverage."""
        name_lower = name.lower()
        return any(kw in name_lower for kw in NON_RRG_PRODUCT_KEYWORDS)

    def _from_stripe_payment_intent(self, policy, cache):
        """For annual policies: fetch the Stripe PaymentIntent and split
        the actual charge proportionally across coverages."""
        pi_id = policy.stripe_payment_intent_id
        cache_key = f"pi_{pi_id}"
        if cache_key not in cache:
            try:
                pi = stripe.PaymentIntent.retrieve(pi_id)
                cache[cache_key] = pi
                time.sleep(0.05)
            except Exception:
                cache[cache_key] = None

        pi = cache.get(cache_key)
        if not pi:
            return None

        # Use the amount actually received (in cents)
        total_cents = pi.get("amount_received") or pi.get("amount", 0)
        if total_cents <= 0:
            return None
        total_amount = Decimal(str(total_cents)) / 100

        return self._split_proportional_annual(policy, total_amount, "stripe-annual")

    def _split_proportional_annual(self, policy, total_amount, source):
        """Split an annual Stripe charge proportionally across all coverages
        in the same quote (both brokered and non-brokered) using rating
        breakdown ratios, then return this policy's share."""
        try:
            rating_result = policy.quote.rating_result
            if not rating_result or not isinstance(rating_result, dict):
                return None
            breakdown = rating_result.get("breakdown", {})
            if not breakdown:
                return None
        except (AttributeError, TypeError):
            return None

        # Include ALL policies in the quote (brokered + non-brokered)
        # because the Stripe charge covers everything in the checkout.
        all_policies = Policy.objects.filter(quote=policy.quote)

        total_rated = Decimal("0")
        coverage_rated = {}
        for p in all_policies:
            cd = breakdown.get(p.coverage_type, {})
            if not isinstance(cd, dict):
                continue
            rated = cd.get("premium")
            if rated is not None and rated > 0:
                rated = Decimal(str(rated))
                coverage_rated[p.coverage_type] = rated
                total_rated += rated

        if total_rated <= 0 or policy.coverage_type not in coverage_rated:
            return None

        ratio = coverage_rated[policy.coverage_type] / total_rated
        expected_premium = (total_amount * ratio).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )

        return expected_premium, None, source

    def _split_proportional(self, policy, total_monthly, source):
        try:
            rating_result = policy.quote.rating_result
            if not rating_result or not isinstance(rating_result, dict):
                return None
            breakdown = rating_result.get("breakdown", {})
            if not breakdown:
                return None
        except (AttributeError, TypeError):
            return None

        all_policies = Policy.objects.filter(
            quote=policy.quote,
            is_brokered=False,
        )

        total_rated = Decimal("0")
        coverage_rated = {}
        for p in all_policies:
            cd = breakdown.get(p.coverage_type, {})
            if not isinstance(cd, dict):
                continue
            rated = cd.get("premium")
            if rated is not None and rated > 0:
                rated = Decimal(str(rated))
                coverage_rated[p.coverage_type] = rated
                total_rated += rated

        if total_rated <= 0 or policy.coverage_type not in coverage_rated:
            return None

        ratio = coverage_rated[policy.coverage_type] / total_rated
        coverage_monthly = (total_monthly * ratio).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        coverage_annual = (coverage_monthly * 12).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )

        return coverage_annual, coverage_monthly, source

    def _from_rating_proportional_annual(self, policy):
        try:
            rating_result = policy.quote.rating_result
            if not rating_result or not isinstance(rating_result, dict):
                return None
            breakdown = rating_result.get("breakdown", {})
            coverage_data = breakdown.get(policy.coverage_type, {})
            if not isinstance(coverage_data, dict):
                return None
            rated_premium = coverage_data.get("premium")
            if rated_premium is None:
                return None
        except (AttributeError, TypeError):
            return None

        rated_premium = Decimal(str(rated_premium))
        if rated_premium <= 0:
            return None

        if policy.discount_percentage:
            discount = Decimal(str(policy.discount_percentage)) / Decimal("100")
            rated_premium = (rated_premium * (1 - discount)).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP
            )

        if policy.premium == rated_premium:
            return None

        return rated_premium, None, "rating-annual"

    def _get_payment_fixes(self, policy, expected_premium, expected_monthly):
        fixes = []
        payments = Payment.objects.filter(policy=policy, status="paid")
        for payment in payments:
            if policy.billing_frequency == "monthly":
                expected = expected_monthly
            else:
                expected = expected_premium
            if expected and payment.amount != expected:
                fixes.append((payment, expected))
        return fixes
