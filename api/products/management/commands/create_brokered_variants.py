"""
Idempotent one-off command to create BROKERED ProductConfiguration variants.

For every active direct ProductConfiguration (``is_brokered_variant=False``),
this command:

  1. Ensures a sibling row exists with ``coverage_type = "<slug>_brokered"``,
     ``is_brokered_variant=True``, and ``parent_variant`` pointing back at
     the direct row.
  2. Creates a Stripe Product with ``metadata={"brokered": "true", ...}``
     via :pyclass:`stripe_integration.service.StripeService.create_product`.

The command is safe to run repeatedly: existing DB siblings are reused and
Stripe product creation is only attempted for brand-new siblings.

Usage::

    python manage.py create_brokered_variants            # real run
    python manage.py create_brokered_variants --dry-run  # no writes
    python manage.py create_brokered_variants --skip-stripe  # DB-only
"""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import ProductConfiguration

logger = logging.getLogger(__name__)


BROKERED_SLUG_SUFFIX = "_brokered"


def _brokered_slug(direct_slug: str) -> str:
    if direct_slug.endswith(BROKERED_SLUG_SUFFIX):
        return direct_slug
    return f"{direct_slug}{BROKERED_SLUG_SUFFIX}"


def _brokered_display_name(direct_name: str) -> str:
    suffix = " (Brokered)"
    if direct_name.endswith(suffix):
        return direct_name
    return f"{direct_name}{suffix}"


class Command(BaseCommand):
    help = (
        "Create BROKERED ProductConfiguration siblings for every direct "
        "product, and mirror each into Stripe with brokered=true metadata. "
        "Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing to the database or Stripe.",
        )
        parser.add_argument(
            "--skip-stripe",
            action="store_true",
            help="Create DB siblings only; do not call Stripe.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        skip_stripe: bool = options["skip_stripe"]

        direct_qs = ProductConfiguration.objects.filter(is_brokered_variant=False)
        created = 0
        existed = 0
        stripe_created = 0

        for direct in direct_qs:
            brokered_slug = _brokered_slug(direct.coverage_type)

            existing = ProductConfiguration.objects.filter(
                coverage_type=brokered_slug
            ).first()

            if existing is not None:
                existed += 1
                # Heal parent link if a previous partial run left it blank.
                if (
                    existing.parent_variant_id != direct.id
                    or not existing.is_brokered_variant
                ):
                    if not dry_run:
                        existing.parent_variant = direct
                        existing.is_brokered_variant = True
                        existing.save(
                            update_fields=["parent_variant", "is_brokered_variant"]
                        )
                    self.stdout.write(
                        f"  repaired brokered link: {existing.coverage_type} -> {direct.coverage_type}"
                    )
                continue

            self.stdout.write(
                f"+ creating brokered variant: {brokered_slug} (parent={direct.coverage_type})"
            )

            if dry_run:
                created += 1
                continue

            with transaction.atomic():
                sibling = ProductConfiguration.objects.create(
                    coverage_type=brokered_slug,
                    display_name=_brokered_display_name(direct.display_name),
                    description=direct.description,
                    is_active=direct.is_active,
                    min_limit=direct.min_limit,
                    max_limit=direct.max_limit,
                    available_retentions=list(direct.available_retentions or []),
                    rating_tier="tier2_brokered_form",
                    requires_review=True,
                    admin_notes=(
                        f"Auto-generated brokered variant of {direct.coverage_type}."
                    ),
                    is_brokered_variant=True,
                    parent_variant=direct,
                )
            created += 1

            if skip_stripe:
                continue

            try:
                # Imported lazily so `--skip-stripe` / DB-only environments
                # (e.g. unit tests without stripe configured) still work.
                from stripe_integration.schemas import CreateProductInput
                from stripe_integration.service import StripeService

                StripeService.create_product(
                    CreateProductInput(
                        name=sibling.display_name,
                        metadata={
                            "coverage": sibling.coverage_type,
                            "parent_coverage": direct.coverage_type,
                            "product_configuration_id": str(sibling.id),
                        },
                        brokered=True,
                    )
                )
                stripe_created += 1
            except Exception as exc:  # pragma: no cover - network-dependent
                logger.exception(
                    "Failed to create Stripe product for brokered variant %s: %s",
                    sibling.coverage_type,
                    exc,
                )
                self.stderr.write(
                    self.style.WARNING(
                        f"  WARN: Stripe product create failed for {sibling.coverage_type}: {exc}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. created={created} existed={existed} stripe_created={stripe_created} "
                f"dry_run={dry_run} skip_stripe={skip_stripe}"
            )
        )
