"""
Analytics API router (public-service endpoints).

Currently exposes a single read-only endpoint for the
External Sales Analytics Dashboard (H11):

    GET /api/v1/analytics/sales-metrics
        ?start=YYYY-MM-DD
        &end=YYYY-MM-DD
        &owner=<hubspot_owner_id>
        &product=<product_slug>

Access is restricted to finance/admin roles via JWTAuth.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

from django.http import HttpRequest
from ninja import Router

from admin_api.helpers import FINANCE_ROLES, _require_role
from common.schemas import ApiResponseSchema
from users.auth import JWTAuth

router = Router(tags=["Analytics"])


@router.get(
    "/sales-metrics",
    auth=JWTAuth(),
    response={200: ApiResponseSchema},
    summary="External sales metrics from HubSpot (close rate + no-show rate)",
)
def sales_metrics(
    request: HttpRequest,
    start: Optional[str] = None,
    end: Optional[str] = None,
    owner: Optional[str] = None,
    product: Optional[str] = None,
) -> tuple[int, dict[str, Any]]:
    """Return close rate and no-show rate pulled from HubSpot.

    Query params are optional; defaults to the trailing 30 days.
    """
    _require_role(request, FINANCE_ROLES, "view_external_sales_metrics")

    from analytics.hubspot_sales import fetch_sales_metrics

    today = date.today()
    try:
        end_date = date.fromisoformat(end) if end else today
    except ValueError:
        end_date = today
    try:
        start_date = (
            date.fromisoformat(start) if start else end_date - timedelta(days=30)
        )
    except ValueError:
        start_date = end_date - timedelta(days=30)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    data = fetch_sales_metrics(
        start_date=start_date,
        end_date=end_date,
        owner_id=owner or None,
        product=product or None,
    )
    return 200, {"success": True, "message": "Sales metrics", "data": data}


def _parse_window(start: Optional[str], end: Optional[str]) -> tuple[date, date]:
    """Parse ``start`` / ``end`` query params into an inclusive window.

    Defaults to the trailing 30 days when absent or malformed.
    """
    today = date.today()
    try:
        end_date = date.fromisoformat(end) if end else today
    except ValueError:
        end_date = today
    try:
        start_date = (
            date.fromisoformat(start) if start else end_date - timedelta(days=30)
        )
    except ValueError:
        start_date = end_date - timedelta(days=30)
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


@router.get(
    "/arr",
    auth=JWTAuth(),
    response={200: ApiResponseSchema},
    summary="Annualized Recurring Revenue snapshot from active policies",
)
def arr(
    request: HttpRequest,
    at: Optional[str] = None,
) -> tuple[int, dict[str, Any]]:
    """ARR = sum of annual-billed premium + (monthly_premium * 12) across active policies."""
    _require_role(request, FINANCE_ROLES, "view_arr")

    from analytics.arr import compute_arr

    try:
        at_date = date.fromisoformat(at) if at else None
    except ValueError:
        at_date = None

    data = compute_arr(at_date=at_date)
    return 200, {"success": True, "message": "ARR snapshot", "data": data}


@router.get(
    "/operating-revenue",
    auth=JWTAuth(),
    response={200: ApiResponseSchema},
    summary="Operating revenue (GWP minus refunds) in a date window",
)
def operating_revenue(
    request: HttpRequest,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> tuple[int, dict[str, Any]]:
    """Sum of PolicyTransaction GWP in [start, end] minus Payment refunds in the same window."""
    _require_role(request, FINANCE_ROLES, "view_operating_revenue")

    from analytics.arr import compute_operating_revenue

    start_date, end_date = _parse_window(start, end)
    data = compute_operating_revenue(start_date=start_date, end_date=end_date)
    return 200, {"success": True, "message": "Operating revenue", "data": data}


@router.get(
    "/brokered-direct-split",
    auth=JWTAuth(),
    response={200: ApiResponseSchema},
    summary="Brokered vs direct revenue breakdown",
)
def brokered_direct_split(
    request: HttpRequest,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> tuple[int, dict[str, Any]]:
    """Split GWP in [start, end] between brokered and direct policies."""
    _require_role(request, FINANCE_ROLES, "view_brokered_direct_split")

    from analytics.arr import compute_brokered_direct_split

    start_date, end_date = _parse_window(start, end)
    data = compute_brokered_direct_split(start_date=start_date, end_date=end_date)
    return 200, {"success": True, "message": "Brokered vs direct split", "data": data}


# ── Internal sales-rep performance (H21) ─────────────────────────────
# Access gate: finance + admin (same as other analytics endpoints) so sales
# leadership can consume without exposing rep-level scorecards broadly.


@router.get(
    "/ae-performance",
    auth=JWTAuth(),
    response={200: ApiResponseSchema},
    summary="Per-AE performance scorecard (policies bound, GWP, close rate, pipeline)",
)
def ae_performance(
    request: HttpRequest,
    start: Optional[str] = None,
    end: Optional[str] = None,
    producer_id: Optional[int] = None,
) -> tuple[int, dict[str, Any]]:
    _require_role(request, FINANCE_ROLES, "view_ae_performance")

    from analytics.ae_performance import ae_metrics

    start_date, end_date = _parse_window(start, end)
    data = ae_metrics(
        start_date=start_date,
        end_date=end_date,
        producer_id=producer_id,
    )
    return 200, {"success": True, "message": "AE performance", "data": data}


@router.get(
    "/bdr-performance",
    auth=JWTAuth(),
    response={200: ApiResponseSchema},
    summary="Per-BDR performance scorecard (sourced pipeline + handoffs)",
)
def bdr_performance(
    request: HttpRequest,
    start: Optional[str] = None,
    end: Optional[str] = None,
    producer_id: Optional[int] = None,
) -> tuple[int, dict[str, Any]]:
    _require_role(request, FINANCE_ROLES, "view_bdr_performance")

    from analytics.ae_performance import bdr_metrics

    start_date, end_date = _parse_window(start, end)
    data = bdr_metrics(
        start_date=start_date,
        end_date=end_date,
        producer_id=producer_id,
    )
    return 200, {"success": True, "message": "BDR performance", "data": data}


@router.get(
    "/revenue-attribution",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 400: ApiResponseSchema},
    summary="Revenue attribution grouped by UTM source / campaign / landing page",
)
def revenue_attribution(
    request: HttpRequest,
    start: Optional[str] = None,
    end: Optional[str] = None,
    group_by: str = "utm_source",
) -> tuple[int, dict[str, Any]]:
    """Return policies bound + gross premium aggregated by lead-source field.

    Only policies with ``status='active'`` and ``purchased_at`` in the
    inclusive ``[start, end]`` window are counted. Quotes with an empty
    value on the grouping field are bucketed under ``'(none)'``.
    """
    _require_role(request, FINANCE_ROLES, "view_revenue_attribution")

    from analytics.attribution import revenue_by_source

    start_date, end_date = _parse_window(start, end)
    try:
        rows = revenue_by_source(
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
        )
    except ValueError as exc:
        return 400, {"success": False, "message": str(exc), "data": None}

    payload = {
        "group_by": group_by,
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "rows": rows,
        "currency": "USD",
    }
    return 200, {"success": True, "message": "Revenue attribution", "data": payload}


# ── Entity ROI / Burn / Runway (Team ROI card) ─────────────────────────

_VALID_ENTITIES = {"corgi_admin", "techrrg", "corgire", "dane"}


def _require_entity(entity: Optional[str]) -> str:
    from ninja.errors import HttpError

    if not entity or entity not in _VALID_ENTITIES:
        raise HttpError(
            400,
            f"entity is required and must be one of: {', '.join(sorted(_VALID_ENTITIES))}",
        )
    return entity


@router.get(
    "/entity-roi",
    auth=JWTAuth(),
    response={200: ApiResponseSchema},
    summary="Per-entity ROI for an inclusive date window",
)
def entity_roi(
    request: HttpRequest,
    entity: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> tuple[int, dict[str, Any]]:
    """ROI = (revenue − expenses) / expenses for one legal entity."""
    _require_role(request, FINANCE_ROLES, "view_entity_roi")
    entity_key = _require_entity(entity)

    from analytics.entity_finance import compute_entity_roi

    start_date, end_date = _parse_window(start, end)
    data = compute_entity_roi(
        entity=entity_key,
        start_date=start_date,
        end_date=end_date,
    )
    return 200, {"success": True, "message": "Entity ROI", "data": data}


@router.get(
    "/entity-burn",
    auth=JWTAuth(),
    response={200: ApiResponseSchema},
    summary="Trailing 30-day burn rate for one entity",
)
def entity_burn(
    request: HttpRequest,
    entity: Optional[str] = None,
) -> tuple[int, dict[str, Any]]:
    """Net cash outflow in the trailing 30 days for one legal entity."""
    _require_role(request, FINANCE_ROLES, "view_entity_burn")
    entity_key = _require_entity(entity)

    from analytics.entity_finance import compute_entity_burn

    data = compute_entity_burn(entity=entity_key)
    return 200, {"success": True, "message": "Entity burn", "data": data}


@router.get(
    "/entity-runway",
    auth=JWTAuth(),
    response={200: ApiResponseSchema},
    summary="Months of runway at current burn for one entity",
)
def entity_runway(
    request: HttpRequest,
    entity: Optional[str] = None,
    cash_balance: Optional[int] = None,
) -> tuple[int, dict[str, Any]]:
    """``cash_balance`` is cents; returns months until the balance hits zero."""
    from ninja.errors import HttpError

    _require_role(request, FINANCE_ROLES, "view_entity_runway")
    entity_key = _require_entity(entity)

    if cash_balance is None or cash_balance < 0:
        raise HttpError(400, "cash_balance (cents, non-negative integer) is required")

    from analytics.entity_finance import compute_entity_runway

    data = compute_entity_runway(
        entity=entity_key,
        cash_balance_cents=int(cash_balance),
    )
    return 200, {"success": True, "message": "Entity runway", "data": data}
