"""
Per-entity finance metrics for the Entity ROI / Burn / Runway dashboard.

Each legal entity that appears in the revenue-split flow chart
(``corgi_admin``, ``techrrg``, ``corgire``, ``dane``) can be evaluated
along three dimensions:

* ``compute_entity_roi(entity, start_date, end_date)``
    Returns ``{entity, revenue, expenses, roi_pct, ...}`` for an inclusive
    date window. Revenue is the sum of the entity's bucket on
    ``RevenueSplit`` rows whose parent ``PolicyTransaction.accounting_date``
    falls in the window. Expenses sum ``EntityExpense`` rows on
    ``incurred_at``. ``roi_pct = (revenue - expenses) / expenses`` when
    expenses > 0, otherwise ``None`` (undefined).

* ``compute_entity_burn(entity, at_month=None)``
    Trailing 30-day net cash outflow ending on ``at_month`` (defaults to
    today). Returned as a positive number when net outflow is positive,
    negative when the entity was cashflow-positive in the window.

* ``compute_entity_runway(entity, cash_balance_cents)``
    Months until ``cash_balance_cents`` is exhausted at the current burn
    rate. Returns ``None`` when burn is <= 0 (infinite runway).

All amounts returned as floats rounded to 2 decimals so the JSON payload
is easy to consume from the admin dashboard.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

from django.db.models import Sum

_TWO_PLACES = Decimal("0.01")

ENTITY_FIELDS = {
    "corgi_admin": "corgi_admin",
    "techrrg": "techrrg",
    "corgire": "corgire",
    "dane": "dane",
}


def _to_float(value: Optional[Decimal]) -> float:
    if value is None:
        return 0.0
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return float(value.quantize(_TWO_PLACES))


def _validate_entity(entity: str) -> str:
    if entity not in ENTITY_FIELDS:
        raise ValueError(
            f"Unknown entity '{entity}'. Expected one of: {', '.join(ENTITY_FIELDS)}"
        )
    return entity


def _entity_revenue(entity: str, start_date: date, end_date: date) -> Decimal:
    """Sum the entity's bucket on RevenueSplit within the accounting window."""
    from policies.models import RevenueSplit

    field = ENTITY_FIELDS[entity]
    total = RevenueSplit.objects.filter(
        transaction__accounting_date__gte=start_date,
        transaction__accounting_date__lte=end_date,
    ).aggregate(total=Sum(field))["total"]
    return total or Decimal("0")


def _entity_expenses(entity: str, start_date: date, end_date: date) -> Decimal:
    """Sum EntityExpense rows incurred in the inclusive window."""
    from policies.models import EntityExpense

    total = EntityExpense.objects.filter(
        entity=entity,
        incurred_at__gte=start_date,
        incurred_at__lte=end_date,
    ).aggregate(total=Sum("amount"))["total"]
    return total or Decimal("0")


def compute_entity_roi(
    entity: str,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """ROI for ``entity`` across an inclusive date window.

    ``roi_pct = (revenue - expenses) / expenses``. When expenses are zero,
    ROI is undefined and returned as ``None`` so the UI can render a dash
    instead of ``inf``.
    """
    _validate_entity(entity)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    revenue = _entity_revenue(entity, start_date, end_date)
    expenses = _entity_expenses(entity, start_date, end_date)

    net = revenue - expenses
    roi_pct: Optional[float]
    if expenses > 0:
        roi_pct = float((net / expenses).quantize(Decimal("0.0001")))
    else:
        roi_pct = None

    return {
        "entity": entity,
        "revenue": _to_float(revenue),
        "expenses": _to_float(expenses),
        "net": _to_float(net),
        "roi_pct": roi_pct,
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "currency": "USD",
    }


def compute_entity_burn(
    entity: str,
    at_month: Optional[date] = None,
) -> dict[str, Any]:
    """Trailing 30-day burn (net cash outflow) for ``entity``.

    Positive values mean the entity spent more than it earned in the
    trailing 30 days. Negative values mean the entity was net
    cashflow-positive.
    """
    _validate_entity(entity)

    end_date = at_month or date.today()
    start_date = end_date - timedelta(days=30)

    revenue = _entity_revenue(entity, start_date, end_date)
    expenses = _entity_expenses(entity, start_date, end_date)
    burn = expenses - revenue

    return {
        "entity": entity,
        "revenue": _to_float(revenue),
        "expenses": _to_float(expenses),
        "burn": _to_float(burn),
        "window_days": 30,
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "currency": "USD",
    }


def compute_entity_runway(
    entity: str,
    cash_balance_cents: int,
) -> dict[str, Any]:
    """Months of runway at current trailing-30-day burn.

    ``cash_balance_cents`` is the bank balance in cents so the wire is
    integer-only. Returned ``runway_months`` is ``None`` when burn is
    zero or negative (infinite runway); otherwise
    ``cash_balance / monthly_burn`` rounded to one decimal.
    """
    _validate_entity(entity)

    burn_data = compute_entity_burn(entity)
    monthly_burn = Decimal(str(burn_data["burn"]))  # already a 30-day window
    cash_balance = Decimal(cash_balance_cents) / Decimal(100)

    runway_months: Optional[float]
    if monthly_burn > 0:
        runway_months = float((cash_balance / monthly_burn).quantize(Decimal("0.1")))
    else:
        runway_months = None

    return {
        "entity": entity,
        "cash_balance": _to_float(cash_balance),
        "monthly_burn": _to_float(monthly_burn),
        "runway_months": runway_months,
        "as_of": burn_data["end"],
        "currency": "USD",
    }
