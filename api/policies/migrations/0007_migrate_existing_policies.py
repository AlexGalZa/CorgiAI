# Generated manually for policy refactor: migrate existing policies to 1 coverage = 1 policy

from decimal import Decimal, InvalidOperation
from django.db import migrations


COVERAGE_CODES = {
    "commercial-general-liability": "CG",
    "cyber-liability": "CY",
    "directors-and-officers": "DO",
    "employment-practices-liability": "EP",
    "fiduciary-liability": "FI",
    "hired-and-non-owned-auto": "HA",
    "media-liability": "ML",
    "technology-errors-and-omissions": "TE",
    "representations-warranties": "RW",
}


def migrate_policies_forward(apps, schema_editor):
    """
    Migrate existing policies to the new 1 coverage = 1 policy structure.
    For each existing policy:
    1. Generate a COI number for the purchase
    2. Update the first coverage on the existing policy
    3. Create new policies for remaining coverages
    """
    Policy = apps.get_model("policies", "Policy")
    PolicySequence = apps.get_model("policies", "PolicySequence")
    COISequence = apps.get_model("policies", "COISequence")

    # Process policies in order of purchased_at to maintain chronological sequences
    for old_policy in Policy.objects.select_related(
        "quote", "quote__company", "quote__company__business_address"
    ).order_by("purchased_at"):
        quote = old_policy.quote

        # Skip if no coverages (shouldn't happen, but safety check)
        if not quote.coverages:
            continue

        # Skip if already migrated (has coverage_type set)
        if old_policy.coverage_type:
            continue

        company = quote.company
        address = company.business_address if company else None
        state = address.state if address else "CA"  # Default to CA if no address
        effective_date = old_policy.effective_date
        year = effective_date.year % 100

        # Generate COI number for this purchase
        coi_seq, _ = COISequence.objects.get_or_create(
            state=state, year=year, defaults={"last_sequence": 0}
        )
        coi_seq.last_sequence += 1
        coi_seq.save()
        coi_number = f"COI-{state}-{year:02d}-{coi_seq.last_sequence:06d}"

        # Get premium breakdown from rating_result
        breakdown = (
            quote.rating_result.get("breakdown", {}) if quote.rating_result else {}
        )
        limits_retentions = quote.limits_retentions or {}

        # Update first coverage on existing policy
        first_coverage = quote.coverages[0]
        lob_code = COVERAGE_CODES.get(first_coverage, "XX")

        # Generate new policy number for first coverage
        seq, _ = PolicySequence.objects.get_or_create(
            lob_code=lob_code, state=state, year=year, defaults={"last_sequence": 0}
        )
        seq.last_sequence += 1
        seq.save()

        # Get premium for first coverage
        first_premium_data = breakdown.get(first_coverage, {})
        first_premium = (
            Decimal(str(first_premium_data.get("premium", 0)))
            if first_premium_data
            else Decimal("0")
        )

        # Get limits for first coverage
        first_limits = limits_retentions.get(first_coverage, {})

        # Update the existing policy
        old_policy.coverage_type = first_coverage
        old_policy.coi_number = coi_number
        old_policy.limits_retentions = first_limits
        old_policy.policy_number = (
            f"{lob_code}-{state}-{year:02d}-{seq.last_sequence:06d}-01"
        )

        # If we have breakdown, update premium to be coverage-specific
        if first_premium > 0:
            old_policy.premium = first_premium

            # Recalculate monthly premium if applicable
            if old_policy.monthly_premium and quote.quote_amount:
                try:
                    proportion = first_premium / Decimal(str(quote.quote_amount))
                    old_policy.monthly_premium = old_policy.monthly_premium * proportion
                except (ZeroDivisionError, InvalidOperation):
                    pass

        old_policy.save()

        # Create new policies for remaining coverages
        for coverage in quote.coverages[1:]:
            lob_code = COVERAGE_CODES.get(coverage, "XX")
            seq, _ = PolicySequence.objects.get_or_create(
                lob_code=lob_code, state=state, year=year, defaults={"last_sequence": 0}
            )
            seq.last_sequence += 1
            seq.save()

            # Get premium and limits for this coverage
            coverage_premium_data = breakdown.get(coverage, {})
            coverage_premium = (
                Decimal(str(coverage_premium_data.get("premium", 0)))
                if coverage_premium_data
                else Decimal("0")
            )
            coverage_limits = limits_retentions.get(coverage, {})

            # Calculate proportional monthly premium
            monthly = None
            if (
                old_policy.monthly_premium
                and quote.quote_amount
                and coverage_premium > 0
            ):
                try:
                    proportion = coverage_premium / Decimal(str(quote.quote_amount))
                    monthly = old_policy.monthly_premium * proportion
                except (ZeroDivisionError, InvalidOperation):
                    pass

            Policy.objects.create(
                quote=quote,
                coverage_type=coverage,
                coi_number=coi_number,
                limits_retentions=coverage_limits,
                policy_number=f"{lob_code}-{state}-{year:02d}-{seq.last_sequence:06d}-01",
                premium=coverage_premium
                if coverage_premium > 0
                else old_policy.premium,
                effective_date=old_policy.effective_date,
                expiration_date=old_policy.expiration_date,
                purchased_at=old_policy.purchased_at,
                status=old_policy.status,
                billing_frequency=old_policy.billing_frequency,
                monthly_premium=monthly,
                stripe_payment_intent_id=old_policy.stripe_payment_intent_id,
                stripe_subscription_id=old_policy.stripe_subscription_id,
                stripe_customer_id=old_policy.stripe_customer_id,
            )


def migrate_policies_reverse(apps, schema_editor):
    """
    Reverse the migration by deleting newly created policies
    and clearing the new fields on original policies.
    """
    Policy = apps.get_model("policies", "Policy")

    # Group policies by quote and coi_number
    # Keep the oldest policy per quote (the original), delete the rest
    processed_quotes = set()

    for policy in Policy.objects.order_by("created_at"):
        quote_id = policy.quote_id
        if quote_id in processed_quotes:
            # This is a newly created policy from migration, delete it
            policy.delete()
        else:
            # This is the original policy, clear new fields
            processed_quotes.add(quote_id)
            policy.coverage_type = ""
            policy.coi_number = None
            policy.limits_retentions = {}
            # Keep the original policy_number as-is
            policy.save()


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0006_policy_coverage_type_and_sequences"),
    ]

    operations = [
        migrations.RunPython(
            migrate_policies_forward,
            migrate_policies_reverse,
        ),
    ]
