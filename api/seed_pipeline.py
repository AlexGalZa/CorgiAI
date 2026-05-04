"""
Seed varied test quotes for Shepherd /pipeline UI verification.

Creates ~15 quotes spread across statuses (draft/submitted/needs_review/quoted)
and ages so the closeability score and next-best-action enum render meaningful
output on the pipeline screen.

Run from /app inside the api container:
    python manage.py shell -c "exec(open('seed_pipeline.py').read())"
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from datetime import timedelta  # noqa: E402
from decimal import Decimal  # noqa: E402

from django.utils import timezone  # noqa: E402

from quotes.models import Quote  # noqa: E402
from tests.factories import (  # noqa: E402
    create_test_user,
    create_personal_org,
    create_test_company,
)


def _ensure_user(email: str, first: str, last: str, company: str):
    from users.models import User

    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        return create_test_user(
            email=email,
            first_name=first,
            last_name=last,
            company_name=company,
        )


def _make_quote(
    *,
    company_name: str,
    customer_email: str,
    customer_first: str,
    customer_last: str,
    status: str,
    days_old: int,
    days_since_update: int,
    days_since_quoted: int | None = None,
    premium: Decimal | None = None,
    coverages: list[str] | None = None,
    billing_frequency: str = "annual",
):
    user = _ensure_user(customer_email, customer_first, customer_last, company_name)
    membership = user.organization_memberships.first()
    if membership is None:
        org = create_personal_org(user)
    else:
        org = membership.organization

    company = create_test_company(entity_legal_name=company_name)

    quote = create_test_quote_for_seed(
        user=user,
        org=org,
        company=company,
        status=status,
        coverages=coverages or ["commercial-general-liability", "cyber-liability"],
        billing_frequency=billing_frequency,
        quote_amount=premium,
    )

    now = timezone.now()
    created = now - timedelta(days=days_old)
    updated = now - timedelta(days=days_since_update)
    Quote.objects.filter(pk=quote.pk).update(
        created_at=created,
        updated_at=updated,
        quoted_at=(now - timedelta(days=days_since_quoted)) if days_since_quoted is not None else None,
    )
    return Quote.objects.get(pk=quote.pk)


def create_test_quote_for_seed(
    *, user, org, company, status, coverages, billing_frequency, quote_amount
):
    """Local helper that doesn't depend on factories.create_test_quote signature."""
    return Quote.objects.create(
        user=user,
        organization=org,
        company=company,
        status=status,
        coverages=coverages,
        available_coverages=coverages,
        coverage_data={},
        limits_retentions={c: {"aggregate_limit": 1_000_000} for c in coverages},
        quote_amount=quote_amount,
        billing_frequency=billing_frequency,
        form_data_snapshot={"coverages": coverages},
        completed_steps=["welcome", "package-selection"],
        current_step="products",
    )


SEED_DEFINITIONS = [
    # --- Fresh quotes (sent today, premium known) ---
    dict(
        company_name="Helio Robotics",
        customer_email="founder@helio.example",
        customer_first="Maya",
        customer_last="Tran",
        status="quoted",
        days_old=1,
        days_since_update=1,
        days_since_quoted=1,
        premium=Decimal("18450.00"),
    ),
    dict(
        company_name="Northwind Labs",
        customer_email="ceo@northwind.example",
        customer_first="Diego",
        customer_last="Alvarez",
        status="quoted",
        days_old=2,
        days_since_update=2,
        days_since_quoted=2,
        premium=Decimal("4220.00"),
    ),
    # --- Stale quoted - prime follow-up candidates ---
    dict(
        company_name="Pillar Health Systems",
        customer_email="cto@pillarhealth.example",
        customer_first="Priya",
        customer_last="Shah",
        status="quoted",
        days_old=18,
        days_since_update=12,
        days_since_quoted=12,
        premium=Decimal("62300.00"),
    ),
    dict(
        company_name="Alpine Freight",
        customer_email="ops@alpinefreight.example",
        customer_first="Erik",
        customer_last="Nilsen",
        status="quoted",
        days_old=22,
        days_since_update=15,
        days_since_quoted=15,
        premium=Decimal("9100.00"),
    ),
    # --- Expiring in <= 7 days ---
    dict(
        company_name="Quanta Bio",
        customer_email="finance@quantabio.example",
        customer_first="Aiko",
        customer_last="Tanaka",
        status="quoted",
        days_old=27,
        days_since_update=14,
        days_since_quoted=25,
        premium=Decimal("31200.00"),
    ),
    dict(
        company_name="Mason & Roe LLP",
        customer_email="partner@masonroe.example",
        customer_first="Jordan",
        customer_last="Mason",
        status="quoted",
        days_old=29,
        days_since_update=8,
        days_since_quoted=29,
        premium=Decimal("14800.00"),
    ),
    # --- needs_review ---
    dict(
        company_name="Polaris Logistics",
        customer_email="cfo@polarislog.example",
        customer_first="Wendy",
        customer_last="Okafor",
        status="needs_review",
        days_old=4,
        days_since_update=2,
        premium=None,
    ),
    dict(
        company_name="Hollow Pine Studios",
        customer_email="founder@hollowpine.example",
        customer_first="Ravi",
        customer_last="Patel",
        status="needs_review",
        days_old=8,
        days_since_update=5,
        premium=None,
    ),
    # --- submitted (awaiting rating or follow-up) ---
    dict(
        company_name="Rivet & Foam Co.",
        customer_email="ops@rivetfoam.example",
        customer_first="Sky",
        customer_last="Lin",
        status="submitted",
        days_old=0,
        days_since_update=0,
        premium=None,
    ),
    dict(
        company_name="Bright Cove Apps",
        customer_email="dev@brightcove.example",
        customer_first="Cam",
        customer_last="Holland",
        status="submitted",
        days_old=3,
        days_since_update=3,
        premium=None,
    ),
    # --- draft (mostly inert; only stale ones get a follow-up) ---
    dict(
        company_name="Tideline Beverages",
        customer_email="hi@tideline.example",
        customer_first="Lena",
        customer_last="Park",
        status="draft",
        days_old=2,
        days_since_update=2,
        premium=None,
    ),
    dict(
        company_name="Otter & Anvil",
        customer_email="founder@otteranvil.example",
        customer_first="Sam",
        customer_last="Bryce",
        status="draft",
        days_old=12,
        days_since_update=10,
        premium=None,
    ),
    dict(
        company_name="Halcyon Power",
        customer_email="energy@halcyon.example",
        customer_first="Noor",
        customer_last="Reyes",
        status="draft",
        days_old=20,
        days_since_update=20,
        premium=None,
    ),
]


def main():
    created = 0
    for defn in SEED_DEFINITIONS:
        _make_quote(**defn)
        created += 1

    print(f"Seeded {created} quotes for /pipeline.")
    counts = (
        Quote.objects.values("status").order_by("status")
    )
    from collections import Counter

    by_status = Counter(q["status"] for q in counts)
    for status in ("draft", "submitted", "needs_review", "quoted"):
        print(f"  {status:>14}: {by_status.get(status, 0)}")


main()
