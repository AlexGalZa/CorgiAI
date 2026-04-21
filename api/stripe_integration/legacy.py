"""
Legacy Stripe Product Coverage Type Lookup (Trello card 4.8).

Old Stripe products were created with names like
``insurance policy - <policy_number>`` and no explicit coverage metadata.
This module provides helpers to infer the coverage list for such legacy
products so a follow-up migration card can backfill their metadata.

Nothing in this module mutates Django models. The public surface is:

- ``infer_coverage_for_legacy_product(stripe_product) -> list[str]``
- ``list_legacy_products(limit=100) -> Iterator[tuple[Product, list[str]]]``
- ``migrate_legacy_metadata(dry_run=True)`` — logs (or applies) the
  backfill of ``coverage_types`` metadata for every legacy product.
"""

from __future__ import annotations

import logging
import re
from typing import Iterator

from stripe_integration.service import StripeService


logger = logging.getLogger(__name__)


LEGACY_NAME_PREFIX = "insurance policy - "
LEGACY_NAME_REGEX = re.compile(
    r"^insurance policy - (?P<policy_number>[A-Z0-9\-]+)$",
    re.IGNORECASE,
)

UNKNOWN_COVERAGE = "unknown"


def _split_metadata_values(raw: str) -> list[str]:
    """Split a space-comma-separated metadata value into clean tokens."""
    if not raw:
        return []
    # Accept commas, spaces, or any mix thereof as separators.
    tokens = re.split(r"[\s,]+", str(raw).strip())
    return [t for t in (tok.strip() for tok in tokens) if t]


def _get_metadata(stripe_product) -> dict:
    """Extract a plain dict of metadata from a Stripe Product object."""
    meta = getattr(stripe_product, "metadata", None)
    if meta is None and isinstance(stripe_product, dict):
        meta = stripe_product.get("metadata")
    if meta is None:
        return {}
    # stripe.StripeObject supports both attribute and dict-style access; coerce.
    try:
        return dict(meta)
    except Exception:
        return {k: meta[k] for k in meta}  # type: ignore[index]


def _get_product_attr(stripe_product, key: str, default=None):
    """Read an attribute from a Stripe Product (object or dict)."""
    if isinstance(stripe_product, dict):
        return stripe_product.get(key, default)
    return getattr(stripe_product, key, default)


def _infer_from_metadata(metadata: dict) -> list[str]:
    """Heuristic 1: metadata already carries carrier/coverage_types."""
    coverages: list[str] = []

    coverage_types = metadata.get("coverage_types")
    if coverage_types:
        coverages.extend(_split_metadata_values(coverage_types))

    # Carrier metadata alone does not reveal coverages, but per the spec we
    # treat either key as "already tagged". If only carrier is present we
    # fall back to a synthetic slug derived from the carrier name so callers
    # can still detect "already classified" products.
    carrier = metadata.get("carrier")
    if carrier and not coverages:
        coverages.append(f"carrier:{carrier}".strip().lower().replace(" ", "-"))

    return coverages


def _infer_from_policy_model(name: str) -> list[str]:
    """Heuristic 2: parse the product name and look up Policy rows."""
    if not name:
        return []

    match = LEGACY_NAME_REGEX.match(name.strip())
    if not match:
        return []

    policy_number = match.group("policy_number")

    try:
        # Imported lazily so this module is importable in contexts where
        # Django apps are not yet configured (e.g. unit-testing helpers).
        from policies.models import Policy  # noqa: WPS433
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Could not import Policy model for legacy lookup: %s", exc)
        return []

    coverages = (
        Policy.objects.filter(policy_number=policy_number)
        .values_list("coverage_type", flat=True)
        .distinct()
    )
    # Drop falsy values and preserve insertion order while de-duping.
    seen: set[str] = set()
    ordered: list[str] = []
    for cov in coverages:
        if cov and cov not in seen:
            seen.add(cov)
            ordered.append(cov)
    return ordered


def _infer_from_subscriptions(product_id: str) -> list[str]:
    """Heuristic 3: scan active Stripe subscriptions attached to a product."""
    if not product_id:
        return []

    client = StripeService.get_client()
    coverages: list[str] = []
    seen: set[str] = set()

    try:
        prices = client.Price.list(product=product_id, active=True, limit=100)
    except Exception as exc:  # pragma: no cover - network/stripe
        logger.warning(
            "Price.list failed while inferring coverage for %s: %s",
            product_id,
            exc,
        )
        return []

    for price in getattr(prices, "auto_paging_iter", lambda: prices.data)():
        price_id = price["id"] if isinstance(price, dict) else price.id
        try:
            subs = client.Subscription.list(
                price=price_id,
                status="active",
                expand=["data.items.data.price.product"],
                limit=100,
            )
        except Exception as exc:  # pragma: no cover - network/stripe
            logger.warning("Subscription.list failed for price %s: %s", price_id, exc)
            continue

        for sub in getattr(subs, "auto_paging_iter", lambda: subs.data)():
            items = (
                sub["items"]["data"] if isinstance(sub, dict) else sub["items"]["data"]
            )
            for item in items:
                meta = {}
                if isinstance(item, dict):
                    meta = item.get("metadata") or {}
                else:
                    meta = getattr(item, "metadata", {}) or {}
                coverage = meta.get("coverage") if meta else None
                if coverage:
                    for cov in _split_metadata_values(coverage):
                        if cov not in seen:
                            seen.add(cov)
                            coverages.append(cov)

    return coverages


def infer_coverage_for_legacy_product(stripe_product) -> list[str]:
    """Infer the coverage slug list for a legacy Stripe product.

    Applies, in order: metadata lookup, policy-number regex plus Django
    lookup, and finally a scan of active subscriptions. Returns
    ``['unknown']`` if no heuristic produced results.
    """
    metadata = _get_metadata(stripe_product)
    product_id = _get_product_attr(stripe_product, "id", "") or ""
    name = _get_product_attr(stripe_product, "name", "") or ""

    coverages = _infer_from_metadata(metadata)
    if coverages:
        return coverages

    coverages = _infer_from_policy_model(name)
    if coverages:
        return coverages

    coverages = _infer_from_subscriptions(product_id)
    if coverages:
        return coverages

    logger.warning(
        "Could not infer coverage for legacy Stripe product id=%s name=%r",
        product_id,
        name,
    )
    return [UNKNOWN_COVERAGE]


def list_legacy_products(limit: int = 100) -> Iterator[tuple[object, list[str]]]:
    """Yield ``(product, inferred_coverages)`` for every legacy product.

    Uses ``stripe.Product.list`` with auto-pagination and filters to
    products whose name begins with ``insurance policy - `` (case
    insensitive).
    """
    client = StripeService.get_client()
    products = client.Product.list(limit=limit)

    iterator = getattr(products, "auto_paging_iter", None)
    source = iterator() if callable(iterator) else products.data

    for product in source:
        name = _get_product_attr(product, "name", "") or ""
        if not name.lower().startswith(LEGACY_NAME_PREFIX):
            continue
        coverages = infer_coverage_for_legacy_product(product)
        yield product, coverages


def migrate_legacy_metadata(dry_run: bool = True) -> list[dict]:
    """Backfill ``coverage_types`` metadata for every legacy product.

    In ``dry_run`` mode (the default) this function only logs what would
    change. Returns a list of change records so callers can inspect the
    outcome programmatically.
    """
    client = StripeService.get_client()
    changes: list[dict] = []

    for product, coverages in list_legacy_products():
        product_id = _get_product_attr(product, "id", "") or ""
        name = _get_product_attr(product, "name", "") or ""
        existing = _get_metadata(product)

        joined = ",".join(coverages)
        new_metadata = {**existing, "coverage_types": joined}

        record = {
            "product_id": product_id,
            "name": name,
            "coverages": list(coverages),
            "existing_metadata": dict(existing),
            "new_metadata": new_metadata,
            "dry_run": dry_run,
        }
        changes.append(record)

        if dry_run:
            logger.info(
                "[dry-run] Would set coverage_types=%r on product %s (%s)",
                joined,
                product_id,
                name,
            )
            continue

        try:
            client.Product.modify(product_id, metadata=new_metadata)
            logger.info(
                "Set coverage_types=%r on product %s (%s)",
                joined,
                product_id,
                name,
            )
        except Exception as exc:  # pragma: no cover - network/stripe
            logger.exception(
                "Failed to update coverage_types on product %s: %s",
                product_id,
                exc,
            )
            record["error"] = str(exc)

    return changes
