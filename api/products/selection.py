"""
Product variant selection.

Given a requested coverage type, a limit (in dollars), and an explicit
``is_brokered`` signal, resolve the correct ProductConfiguration row.

Routing rules (Trello 1.1):
  * Limits above $5M ALWAYS route to the brokered variant, regardless of
    the caller's ``is_brokered`` hint — this is the >5M brokered rule.
  * When the caller explicitly asks for a brokered variant (``is_brokered``
    is True), we return the brokered sibling.
  * Otherwise we return the direct (non-brokered) configuration.

If a brokered variant has not yet been provisioned for a coverage type,
we fall back to the direct product so quoting never breaks; the caller
can still detect this by inspecting ``is_brokered_variant`` on the result.
"""

from __future__ import annotations

from typing import Optional

from .models import ProductConfiguration


# Aggregate limit threshold (in dollars) above which quotes must be brokered.
BROKERED_LIMIT_THRESHOLD_USD = 5_000_000


def _needs_brokered_routing(limit: Optional[int], is_brokered: bool) -> bool:
    """Return True if this request must go to the brokered variant."""
    if is_brokered:
        return True
    if limit is not None and limit > BROKERED_LIMIT_THRESHOLD_USD:
        return True
    return False


def select_product_variant(
    coverage: str,
    limit: Optional[int] = None,
    is_brokered: bool = False,
) -> Optional[ProductConfiguration]:
    """
    Select the correct ProductConfiguration for a quote request.

    Args:
        coverage: coverage type slug of the *direct* product
            (e.g. ``"commercial-general-liability"``). Brokered siblings are
            looked up via ``parent_variant`` / ``brokered_children``, not by
            passing their own slug in.
        limit: requested aggregate limit in dollars. Limits greater than
            ``BROKERED_LIMIT_THRESHOLD_USD`` are always routed to the
            brokered variant.
        is_brokered: explicit brokered hint from the caller.

    Returns:
        The best-matching active ProductConfiguration, or ``None`` if no
        direct product exists for ``coverage``.
    """
    direct = ProductConfiguration.objects.filter(
        coverage_type=coverage, is_brokered_variant=False
    ).first()
    if direct is None:
        # If the caller handed us a brokered slug directly, just return it.
        return ProductConfiguration.objects.filter(coverage_type=coverage).first()

    if not _needs_brokered_routing(limit, is_brokered):
        return direct

    brokered = ProductConfiguration.objects.filter(
        parent_variant=direct, is_brokered_variant=True, is_active=True
    ).first()
    if brokered is not None:
        return brokered

    # Fallback: no brokered sibling provisioned yet -> keep quoting working
    # on the direct product. Callers can still see is_brokered_variant=False.
    return direct
