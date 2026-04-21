"""
Revenue attribution by lead source.

Aggregates bound-policy revenue back to the acquisition-channel fields captured
on the originating quote (``utm_source``, ``utm_campaign``, ``landing_page_url``).

Public helper:

* ``revenue_by_source(start_date, end_date, group_by='utm_source')`` -- returns
  a list of ``{group_key, policies_bound, gross_premium}`` rows, one per
  distinct group value, for policies purchased within the inclusive window.

Rules:

* Counts a policy as "bound" when ``Policy.status == 'active'`` AND
  ``purchased_at`` falls within [start_date, end_date].
* Quotes with empty attribution on the grouping field are bucketed under
  ``'(none)'`` so finance can see the size of the un-attributed pool.
* ``gross_premium`` is the sum of ``Policy.premium``. Monetary values are
  returned as floats rounded to 2 decimals.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum

_TWO_PLACES = Decimal("0.01")
_ALLOWED_GROUP_BY = {"utm_source", "utm_campaign", "landing_page_url"}
_UNATTRIBUTED_LABEL = "(none)"


def _to_float(value: Decimal | None) -> float:
    if value is None:
        return 0.0
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return float(value.quantize(_TWO_PLACES))


def revenue_by_source(
    start_date: date,
    end_date: date,
    group_by: str = "utm_source",
) -> list[dict[str, Any]]:
    """Return bound-policy counts and gross premium grouped by an attribution field.

    Args:
        start_date: Inclusive start of the purchase window.
        end_date: Inclusive end of the purchase window.
        group_by: One of ``utm_source``, ``utm_campaign``, ``landing_page_url``.

    Returns:
        A list of ``{group_key, policies_bound, gross_premium}`` dicts,
        sorted by ``gross_premium`` descending.
    """
    if group_by not in _ALLOWED_GROUP_BY:
        raise ValueError(
            f"group_by must be one of {sorted(_ALLOWED_GROUP_BY)} (got '{group_by}')"
        )

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    from policies.models import Policy

    quote_field = f"quote__{group_by}"

    qs = (
        Policy.objects.filter(
            status="active",
            purchased_at__date__gte=start_date,
            purchased_at__date__lte=end_date,
        )
        .values(quote_field)
        .annotate(
            policies_bound=Count("id"),
            gross_premium=Sum("premium"),
        )
    )

    rows: list[dict[str, Any]] = []
    for row in qs:
        raw_key = row.get(quote_field) or ""
        group_key = raw_key if raw_key else _UNATTRIBUTED_LABEL
        rows.append(
            {
                "group_key": group_key,
                "policies_bound": int(row["policies_bound"] or 0),
                "gross_premium": _to_float(row["gross_premium"]),
            }
        )

    rows.sort(key=lambda r: r["gross_premium"], reverse=True)
    return rows
