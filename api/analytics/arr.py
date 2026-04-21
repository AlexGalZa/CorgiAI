"""
Finance metrics for the Admin Dashboard (Trello cards H8 + H9).

Three pure-compute helpers used by ``analytics.api``:

* ``compute_arr(at_date=None)`` -- Annualized Recurring Revenue snapshot based on
  currently-active policies. Monthly-billed policies contribute
  ``monthly_premium * 12`` (falling back to ``premium`` when ``monthly_premium``
  is missing). Annually-billed policies contribute ``premium`` as-is.

* ``compute_operating_revenue(start_date, end_date)`` -- Operating Revenue in a
  window. Sum of ``PolicyTransaction.gross_written_premium`` whose
  ``accounting_date`` falls in the inclusive window, minus refunds on
  ``Payment`` rows refunded in the window.

* ``compute_brokered_direct_split(start_date, end_date)`` -- Brokered vs direct
  revenue breakdown for the same window. Returns
  ``{brokered, direct, total, brokered_pct, direct_pct, start, end}``.

All amounts are returned as floats (JSON-friendly) and rounded to 2 decimals.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from django.db.models import Sum, Q

_TWO_PLACES = Decimal("0.01")


def _to_float(value: Optional[Decimal]) -> float:
    if value is None:
        return 0.0
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return float(value.quantize(_TWO_PLACES))


def compute_arr(at_date: Optional[date] = None) -> dict[str, Any]:
    """Annualized Recurring Revenue from currently-active policies.

    Formula:
        annual policy    -> premium
        monthly policy   -> (monthly_premium or premium/12) * 12

    ``at_date`` is currently informational -- we use live policy status rather
    than a historical reconstruction. Included in the response so callers can
    label a snapshot.
    """
    from policies.models import Policy

    snapshot_date = at_date or date.today()

    active = Policy.objects.filter(status="active")

    annual_qs = active.filter(billing_frequency="annual")
    monthly_qs = active.filter(billing_frequency="monthly")

    annual_total = annual_qs.aggregate(total=Sum("premium"))["total"] or Decimal("0")

    monthly_arr = Decimal("0")
    for row in monthly_qs.values("premium", "monthly_premium"):
        monthly = row["monthly_premium"]
        if monthly is None or monthly == 0:
            premium = row["premium"] or Decimal("0")
            monthly_arr += premium
        else:
            monthly_arr += Decimal(monthly) * 12

    arr = annual_total + monthly_arr

    return {
        "arr": _to_float(arr),
        "annual_contribution": _to_float(annual_total),
        "monthly_contribution": _to_float(monthly_arr),
        "active_policy_count": active.count(),
        "monthly_policy_count": monthly_qs.count(),
        "annual_policy_count": annual_qs.count(),
        "as_of": snapshot_date.isoformat(),
        "currency": "USD",
    }


def compute_operating_revenue(start_date: date, end_date: date) -> dict[str, Any]:
    """Operating Revenue in an inclusive date window.

    = sum(PolicyTransaction.gross_written_premium WHERE accounting_date in [start, end])
      - sum(Payment.refund_amount WHERE refunded_at in [start, end])
    """
    from policies.models import Payment, PolicyTransaction

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    gwp = PolicyTransaction.objects.filter(
        accounting_date__gte=start_date,
        accounting_date__lte=end_date,
    ).aggregate(total=Sum("gross_written_premium"))["total"] or Decimal("0")

    refunds = Payment.objects.filter(
        refunded_at__date__gte=start_date,
        refunded_at__date__lte=end_date,
        refund_amount__isnull=False,
    ).aggregate(total=Sum("refund_amount"))["total"] or Decimal("0")

    operating_revenue = gwp - refunds

    return {
        "operating_revenue": _to_float(operating_revenue),
        "gross_written_premium": _to_float(gwp),
        "refunds": _to_float(refunds),
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "currency": "USD",
    }


def compute_brokered_direct_split(start_date: date, end_date: date) -> dict[str, Any]:
    """Brokered vs direct revenue breakdown by ``PolicyTransaction.accounting_date``.

    Direct = transactions on policies with ``is_brokered=False``.
    Brokered = transactions on policies with ``is_brokered=True``.
    """
    from policies.models import PolicyTransaction

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    window = Q(accounting_date__gte=start_date, accounting_date__lte=end_date)

    brokered = PolicyTransaction.objects.filter(
        window, policy__is_brokered=True
    ).aggregate(total=Sum("gross_written_premium"))["total"] or Decimal("0")
    direct = PolicyTransaction.objects.filter(
        window, policy__is_brokered=False
    ).aggregate(total=Sum("gross_written_premium"))["total"] or Decimal("0")

    total = brokered + direct
    brokered_pct = float(brokered / total) if total else 0.0
    direct_pct = float(direct / total) if total else 0.0

    return {
        "brokered": _to_float(brokered),
        "direct": _to_float(direct),
        "total": _to_float(total),
        "brokered_pct": round(brokered_pct, 4),
        "direct_pct": round(direct_pct, 4),
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "currency": "USD",
    }
