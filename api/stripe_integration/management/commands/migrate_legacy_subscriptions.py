"""
Migrate existing clients to the new Stripe product structure (Trello card 2.2).

Old-structure subscriptions were created against a single Stripe product named
``insurance policy - <policy_number>`` with one line item. The new structure
creates one Stripe product per coverage type and attaches one subscription
item per coverage.

This management command walks active Stripe subscriptions and, for each
subscription whose single item references a legacy product:

    1. Resolves the list of coverage slugs via
       ``infer_coverage_for_legacy_product`` (Trello card 4.8, already merged).
    2. Looks up the new-structure Stripe product for each coverage. The
       ``products.ProductConfiguration`` Django model does not persist a
       ``stripe_product_id``, so we fall back to a Stripe-side lookup by
       product name / metadata ``coverage`` key.
    3. Atomically swaps the single legacy item for one new item per coverage
       via ``stripe.Subscription.modify`` with ``proration_behavior='none'``.
    4. After every subscription attached to a given legacy product has been
       migrated, archives the legacy product (``active=False``).

The command is idempotent:

  * Subscriptions whose items no longer point at a legacy product are skipped.
  * Legacy products that are already archived (``active=False``) are ignored.
  * Coverages that already appear on the subscription are not re-added.

Usage::

    python manage.py migrate_legacy_subscriptions
    python manage.py migrate_legacy_subscriptions --dry-run
    python manage.py migrate_legacy_subscriptions --batch-size 25

No Django models are created or mutated — all durable state lives in Stripe.
Per the spec, a follow-up card will introduce a ``LegacyMigrationLog`` table;
for now every action is emitted via ``logger`` and ``self.stdout``.
"""

from __future__ import annotations

import logging
from typing import Iterable

from django.core.management.base import BaseCommand

from stripe_integration.legacy import (
    LEGACY_NAME_PREFIX,
    UNKNOWN_COVERAGE,
    infer_coverage_for_legacy_product,
)
from stripe_integration.service import StripeService


logger = logging.getLogger(__name__)


def _attr(obj, key, default=None):
    """Read ``key`` from a Stripe object or a plain dict."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _is_legacy_product(product) -> bool:
    """True if ``product`` is an un-archived legacy Stripe product."""
    if product is None:
        return False
    name = _attr(product, "name", "") or ""
    if not name.lower().startswith(LEGACY_NAME_PREFIX):
        return False
    # Archived products shouldn't be re-processed.
    active = _attr(product, "active", True)
    return bool(active)


def _coverage_of_subscription_item(item) -> str | None:
    """Extract the coverage slug already attached to a subscription item."""
    price = _attr(item, "price", {}) or {}
    product = _attr(price, "product", {}) or {}
    metadata = _attr(product, "metadata", {}) or {}
    if isinstance(metadata, dict):
        return metadata.get("coverage")
    return getattr(metadata, "coverage", None)


class Command(BaseCommand):
    help = (
        "Migrate active Stripe subscriptions from the legacy single-product "
        "structure to the new per-coverage structure. Safe to re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Log planned Stripe mutations without making any API writes.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help="Stripe list page size for subscriptions (default: 10).",
        )

    # ------------------------------------------------------------------
    # Stripe helpers
    # ------------------------------------------------------------------

    def _iter_active_subscriptions(self, batch_size: int) -> Iterable:
        """Yield every active Stripe subscription with product expanded."""
        client = StripeService.get_client()
        subs = client.Subscription.list(
            status="active",
            limit=batch_size,
            expand=["data.items.data.price.product"],
        )
        iterator = getattr(subs, "auto_paging_iter", None)
        if callable(iterator):
            yield from iterator()
        else:
            yield from subs.data

    def _find_new_product_id_for_coverage(self, coverage: str) -> str | None:
        """Resolve the new-structure Stripe product ID for a coverage slug.

        The Django ``ProductConfiguration`` model does not store a
        ``stripe_product_id`` field (see ``api/products/models.py``), so we
        cannot look up the new product from Django. Instead we query Stripe
        directly — first by metadata (``coverage=<slug>``), falling back to
        a display-name match derived from the configuration row.
        """
        if not coverage or coverage == UNKNOWN_COVERAGE:
            return None

        client = StripeService.get_client()

        # Primary: Stripe search by metadata. Requires Stripe Search enabled.
        try:
            query = f"active:'true' AND metadata['coverage']:'{coverage}'"
            result = client.Product.search(query=query, limit=1)
            data = getattr(result, "data", None) or []
            if data:
                return _attr(data[0], "id")
        except Exception as exc:  # pragma: no cover - network/stripe
            logger.debug(
                "Product.search failed for coverage=%s (%s); falling back to list.",
                coverage,
                exc,
            )

        # Fallback A: Django-side display-name lookup (no stripe_product_id field).
        display_candidates: list[str] = []
        try:
            from products.models import ProductConfiguration  # noqa: WPS433

            cfg = ProductConfiguration.objects.filter(
                coverage_type=coverage, is_active=True
            ).first()
            if cfg and cfg.display_name:
                display_candidates.append(cfg.display_name)
        except Exception as exc:  # pragma: no cover - Django not configured
            logger.debug("ProductConfiguration lookup failed: %s", exc)

        # Fallback B: scan active Stripe products and match by metadata or name.
        try:
            products = client.Product.list(active=True, limit=100)
        except Exception as exc:  # pragma: no cover - network/stripe
            logger.warning(
                "Could not list Stripe products while resolving coverage %s: %s",
                coverage,
                exc,
            )
            return None

        iterator = getattr(products, "auto_paging_iter", None)
        source = iterator() if callable(iterator) else products.data
        for product in source:
            meta = _attr(product, "metadata", {}) or {}
            meta_cov = meta.get("coverage") if isinstance(meta, dict) else None
            if meta_cov == coverage:
                return _attr(product, "id")
            name = _attr(product, "name", "") or ""
            if name in display_candidates:
                return _attr(product, "id")
            # Last-resort name heuristic: slugify.
            slug = name.strip().lower().replace(" ", "-")
            if slug == coverage:
                return _attr(product, "id")
        return None

    def _default_price_for_product(self, product_id: str) -> str | None:
        """Return a usable recurring price ID for a given product."""
        client = StripeService.get_client()

        product = client.Product.retrieve(product_id)
        default_price = _attr(product, "default_price", None)
        if isinstance(default_price, str):
            return default_price
        if default_price is not None:
            return _attr(default_price, "id")

        prices = client.Price.list(product=product_id, active=True, limit=1)
        data = getattr(prices, "data", []) or []
        if data:
            return _attr(data[0], "id")
        return None

    # ------------------------------------------------------------------
    # Core handler
    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        batch_size: int = options["batch_size"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY-RUN mode - no Stripe mutations will be performed.\n"
                )
            )

        legacy_products_seen: set[str] = set()
        legacy_products_still_in_use: set[str] = set()

        migrated = 0
        skipped = 0
        errors = 0

        for subscription in self._iter_active_subscriptions(batch_size):
            sub_id = _attr(subscription, "id")
            items = _attr(subscription, "items", {}) or {}
            item_data = _attr(items, "data", []) or []

            if len(item_data) != 1:
                # Spec targets subs with a single legacy line item.
                skipped += 1
                continue

            item = item_data[0]
            price = _attr(item, "price", {}) or {}
            product = _attr(price, "product", {}) or {}

            if not _is_legacy_product(product):
                skipped += 1
                continue

            legacy_product_id = _attr(product, "id")
            legacy_products_seen.add(legacy_product_id)

            try:
                migrated_ok = self._migrate_subscription(
                    subscription=subscription,
                    legacy_item=item,
                    legacy_product=product,
                    dry_run=dry_run,
                )
                if migrated_ok:
                    migrated += 1
                else:
                    skipped += 1
                    # Migration aborted (e.g. couldn't resolve coverages) —
                    # leave the legacy product active.
                    legacy_products_still_in_use.add(legacy_product_id)
            except Exception as exc:
                errors += 1
                legacy_products_still_in_use.add(legacy_product_id)
                logger.exception(
                    "Failed migrating subscription %s (legacy product %s): %s",
                    sub_id,
                    legacy_product_id,
                    exc,
                )
                self.stdout.write(
                    self.style.ERROR(f"  ERROR migrating {sub_id}: {exc}")
                )

        # Archive legacy products whose subscriptions were all migrated.
        archive_candidates = legacy_products_seen - legacy_products_still_in_use
        archived = 0
        for product_id in sorted(archive_candidates):
            try:
                if self._archive_legacy_product(product_id, dry_run=dry_run):
                    archived += 1
            except Exception as exc:
                errors += 1
                logger.exception(
                    "Failed to archive legacy product %s: %s",
                    product_id,
                    exc,
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. migrated={migrated} skipped={skipped} "
                f"archived={archived} errors={errors} "
                f"legacy_products_seen={len(legacy_products_seen)}"
            )
        )

    # ------------------------------------------------------------------
    # Per-subscription migration
    # ------------------------------------------------------------------

    def _migrate_subscription(
        self,
        *,
        subscription,
        legacy_item,
        legacy_product,
        dry_run: bool,
    ) -> bool:
        """Swap the legacy item for one new item per coverage.

        Returns ``True`` if the subscription was (or would be) migrated,
        ``False`` if it had to be skipped (e.g. unresolved coverages).
        """
        sub_id = _attr(subscription, "id")
        legacy_item_id = _attr(legacy_item, "id")
        legacy_product_id = _attr(legacy_product, "id")
        legacy_product_name = _attr(legacy_product, "name", "") or ""

        coverages = infer_coverage_for_legacy_product(legacy_product)
        coverages = [c for c in coverages if c and c != UNKNOWN_COVERAGE]
        if not coverages:
            logger.warning(
                "Skipping subscription %s: no coverages inferred for legacy product %s (%s).",
                sub_id,
                legacy_product_id,
                legacy_product_name,
            )
            self.stdout.write(
                self.style.WARNING(
                    f"  SKIP {sub_id}: no coverages inferred for {legacy_product_id} ({legacy_product_name!r})."
                )
            )
            return False

        # Resolve new-structure product + price for every coverage up-front so
        # we fail the whole swap atomically if any coverage is missing.
        resolved: list[tuple[str, str, str]] = []  # (coverage, product_id, price_id)
        for coverage in coverages:
            new_product_id = self._find_new_product_id_for_coverage(coverage)
            if not new_product_id:
                logger.warning(
                    "Skipping subscription %s: no new Stripe product found for coverage=%s.",
                    sub_id,
                    coverage,
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP {sub_id}: no new product for coverage={coverage}."
                    )
                )
                return False

            price_id = self._default_price_for_product(new_product_id)
            if not price_id:
                logger.warning(
                    "Skipping subscription %s: no active price on product %s (coverage=%s).",
                    sub_id,
                    new_product_id,
                    coverage,
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP {sub_id}: no price on {new_product_id} (coverage={coverage})."
                    )
                )
                return False

            resolved.append((coverage, new_product_id, price_id))

        # Build the items payload: delete legacy item + add one per coverage.
        items_payload: list[dict] = [{"id": legacy_item_id, "deleted": True}]
        for _coverage, _product_id, price_id in resolved:
            items_payload.append({"price": price_id, "quantity": 1})

        log_summary = ", ".join(f"{cov}->{pid}" for cov, pid, _ in resolved)
        if dry_run:
            logger.info(
                "[dry-run] Would migrate subscription %s: drop item %s (legacy product %s) and attach [%s].",
                sub_id,
                legacy_item_id,
                legacy_product_id,
                log_summary,
            )
            self.stdout.write(
                f"  DRY-RUN {sub_id}: drop {legacy_item_id} (legacy={legacy_product_id}) -> add [{log_summary}]"
            )
            return True

        client = StripeService.get_client()
        client.Subscription.modify(
            sub_id,
            items=items_payload,
            proration_behavior="none",
        )
        logger.info(
            "Migrated subscription %s: dropped legacy item %s (product %s); attached [%s].",
            sub_id,
            legacy_item_id,
            legacy_product_id,
            log_summary,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"  OK {sub_id}: dropped {legacy_item_id} -> added [{log_summary}]"
            )
        )
        return True

    # ------------------------------------------------------------------
    # Legacy product archival
    # ------------------------------------------------------------------

    def _archive_legacy_product(self, product_id: str, *, dry_run: bool) -> bool:
        """Archive a legacy Stripe product. Returns True when action was taken."""
        client = StripeService.get_client()

        try:
            product = client.Product.retrieve(product_id)
        except Exception as exc:  # pragma: no cover - network/stripe
            logger.warning(
                "Could not retrieve legacy product %s for archival: %s",
                product_id,
                exc,
            )
            return False

        if not _attr(product, "active", True):
            # Already archived — idempotent no-op.
            return False

        if dry_run:
            logger.info("[dry-run] Would archive legacy Stripe product %s.", product_id)
            self.stdout.write(f"  DRY-RUN archive legacy product {product_id}")
            return True

        client.Product.modify(product_id, active=False)
        logger.info("Archived legacy Stripe product %s.", product_id)
        self.stdout.write(self.style.SUCCESS(f"  ARCHIVED legacy product {product_id}"))
        return True
