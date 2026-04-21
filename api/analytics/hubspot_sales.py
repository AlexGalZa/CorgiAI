"""
HubSpot External Sales Analytics (H11).

Pulls close rate and no-show rate from HubSpot CRM:

    close_rate    = deals_won / (deals_won + deals_lost)
    no_show_rate  = no_show_meetings / scheduled_meetings

Close rate is computed from Deal objects by scanning for deals whose
``closedate`` falls within the requested window and categorising them
by the canonical HubSpot stage labels ``closedwon`` / ``closedlost``.
Additionally, ``closed_won_date`` and ``closed_lost_date`` properties
are read when present for a more precise timestamp.

No-show rate is computed from Meeting engagement outcomes when the
Meeting API is accessible; otherwise it is returned as ``None`` and a
TODO is emitted in the returned dict.

All HubSpot API calls paginate via ``hubspot-api-client``. Calls are
wrapped in try/except so an outage or missing token returns a safe
empty payload instead of raising — this is a read-only dashboard.

Settings:
    HUBSPOT_ACCESS_TOKEN — canonical private app access token.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from typing import Any, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from hubspot import HubSpot

    HUBSPOT_AVAILABLE = True
except ImportError:
    HUBSPOT_AVAILABLE = False


# ─── Constants ────────────────────────────────────────────────────────────────

# HubSpot default stage identifiers (these are the built-in IDs/labels used by
# every portal on the default pipeline). Custom portals can override these via
# HUBSPOT_STAGE_* settings — we check settings first, falling back to defaults.
DEFAULT_STAGE_WON = "closedwon"
DEFAULT_STAGE_LOST = "closedlost"

# Deal properties we request from HubSpot
DEAL_PROPERTIES = [
    "dealname",
    "dealstage",
    "pipeline",
    "amount",
    "hubspot_owner_id",
    "closedate",
    "closed_won_date",
    "closed_lost_date",
    "createdate",
    # Non-standard but commonly used — harmless if missing
    "product",
    "line_of_business",
]

# Page size for the HubSpot search API (max 100)
PAGE_SIZE = 100

# Safety cap on total deals iterated per call to avoid runaway pagination
MAX_DEALS = 10_000
MAX_MEETINGS = 10_000


# ─── Public API ───────────────────────────────────────────────────────────────


def fetch_sales_metrics(
    start_date: date,
    end_date: date,
    owner_id: Optional[str] = None,
    product: Optional[str] = None,
) -> dict[str, Any]:
    """Fetch close rate + no-show rate for the given window.

    Args:
        start_date: Inclusive lower bound for deal close date / meeting start.
        end_date:   Inclusive upper bound.
        owner_id:   Optional HubSpot owner id to scope results to a single rep.
        product:    Optional product / line-of-business filter.

    Returns:
        Dict with:
            close_rate:          float in [0, 1] or None
            no_show_rate:        float in [0, 1] or None
            total_deals:         int
            deals_won:           int
            deals_lost:          int
            deals_open:          int
            scheduled_meetings:  int
            no_show_meetings:    int
            total_won_amount:    float
            currency:            str
            start:               ISO date string
            end:                 ISO date string
            owner_id:            echoed filter
            product:             echoed filter
            warnings:            list[str]
    """
    warnings: list[str] = []

    client = _get_client()
    if client is None:
        warnings.append("HubSpot client unavailable — returning empty metrics")
        return _empty_result(start_date, end_date, owner_id, product, warnings)

    try:
        deal_stats = _fetch_deal_stats(
            client,
            start_date,
            end_date,
            owner_id=owner_id,
            product=product,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("HubSpot deal fetch failed: %s", exc)
        warnings.append(f"deal_fetch_error: {exc}")
        deal_stats = {
            "total_deals": 0,
            "deals_won": 0,
            "deals_lost": 0,
            "deals_open": 0,
            "total_won_amount": 0.0,
        }

    try:
        meeting_stats = _fetch_meeting_stats(
            client,
            start_date,
            end_date,
            owner_id=owner_id,
        )
    except Exception as exc:
        # TODO: Meeting engagements API is not always accessible with a
        # standard private app. If this raises, fall back to null no_show_rate.
        logger.info("HubSpot meeting fetch failed (returning null): %s", exc)
        warnings.append("no_show_unavailable: meeting engagements API not accessible")
        meeting_stats = {
            "scheduled_meetings": 0,
            "no_show_meetings": 0,
            "available": False,
        }

    won = deal_stats["deals_won"]
    lost = deal_stats["deals_lost"]
    decided = won + lost
    close_rate: Optional[float] = round(won / decided, 4) if decided else None

    no_show_rate: Optional[float] = None
    if meeting_stats.get("available") and meeting_stats["scheduled_meetings"]:
        no_show_rate = round(
            meeting_stats["no_show_meetings"] / meeting_stats["scheduled_meetings"],
            4,
        )

    return {
        "close_rate": close_rate,
        "no_show_rate": no_show_rate,
        "total_deals": deal_stats["total_deals"],
        "deals_won": won,
        "deals_lost": lost,
        "deals_open": deal_stats["deals_open"],
        "scheduled_meetings": meeting_stats["scheduled_meetings"],
        "no_show_meetings": meeting_stats["no_show_meetings"],
        "total_won_amount": deal_stats["total_won_amount"],
        "currency": "USD",
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "owner_id": owner_id,
        "product": product,
        "warnings": warnings,
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_client() -> Optional["HubSpot"]:
    if not HUBSPOT_AVAILABLE:
        return None
    token = getattr(settings, "HUBSPOT_ACCESS_TOKEN", None)
    if not token:
        return None
    return HubSpot(access_token=token)


def _stage_won() -> str:
    return (
        getattr(settings, "HUBSPOT_STAGE_ACTIVE", DEFAULT_STAGE_WON)
        or DEFAULT_STAGE_WON
    )


def _stage_lost() -> str:
    return (
        getattr(settings, "HUBSPOT_STAGE_CANCELLED", DEFAULT_STAGE_LOST)
        or DEFAULT_STAGE_LOST
    )


def _to_epoch_ms(d: date, end_of_day: bool = False) -> int:
    """Convert a date to millisecond epoch — HubSpot filter format."""
    t = time.max if end_of_day else time.min
    dt = datetime.combine(d, t, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _empty_result(
    start_date: date,
    end_date: date,
    owner_id: Optional[str],
    product: Optional[str],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "close_rate": None,
        "no_show_rate": None,
        "total_deals": 0,
        "deals_won": 0,
        "deals_lost": 0,
        "deals_open": 0,
        "scheduled_meetings": 0,
        "no_show_meetings": 0,
        "total_won_amount": 0.0,
        "currency": "USD",
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "owner_id": owner_id,
        "product": product,
        "warnings": warnings,
    }


def _fetch_deal_stats(
    client: "HubSpot",
    start_date: date,
    end_date: date,
    owner_id: Optional[str] = None,
    product: Optional[str] = None,
) -> dict[str, Any]:
    """Use the deals search API to pull deals whose closedate falls in window."""
    start_ms = _to_epoch_ms(start_date, end_of_day=False)
    end_ms = _to_epoch_ms(end_date, end_of_day=True)

    filters: list[dict[str, Any]] = [
        {"propertyName": "closedate", "operator": "GTE", "value": str(start_ms)},
        {"propertyName": "closedate", "operator": "LTE", "value": str(end_ms)},
    ]
    if owner_id:
        filters.append(
            {
                "propertyName": "hubspot_owner_id",
                "operator": "EQ",
                "value": str(owner_id),
            }
        )
    if product:
        # Try a partial match on the product / line_of_business property.
        filters.append(
            {
                "propertyName": "product",
                "operator": "CONTAINS_TOKEN",
                "value": product,
            }
        )

    total_deals = 0
    deals_won = 0
    deals_lost = 0
    deals_open = 0
    total_won_amount = 0.0

    stage_won = _stage_won()
    stage_lost = _stage_lost()

    after: Optional[str] = None
    while total_deals < MAX_DEALS:
        request = {
            "filterGroups": [{"filters": filters}],
            "properties": DEAL_PROPERTIES,
            "limit": PAGE_SIZE,
            "sorts": [{"propertyName": "closedate", "direction": "DESCENDING"}],
        }
        if after:
            request["after"] = after

        response = client.crm.deals.search_api.do_search(
            public_object_search_request=request,
        )

        results = getattr(response, "results", []) or []
        for deal in results:
            props = getattr(deal, "properties", {}) or {}
            stage = (props.get("dealstage") or "").lower()

            total_deals += 1
            if stage == stage_won:
                deals_won += 1
                amount_raw = props.get("amount") or "0"
                try:
                    total_won_amount += float(amount_raw)
                except (TypeError, ValueError):
                    pass
            elif stage == stage_lost:
                deals_lost += 1
            else:
                deals_open += 1

        paging = getattr(response, "paging", None)
        next_page = getattr(paging, "next", None) if paging else None
        after = getattr(next_page, "after", None) if next_page else None
        if not after:
            break

    return {
        "total_deals": total_deals,
        "deals_won": deals_won,
        "deals_lost": deals_lost,
        "deals_open": deals_open,
        "total_won_amount": total_won_amount,
    }


def _fetch_meeting_stats(
    client: "HubSpot",
    start_date: date,
    end_date: date,
    owner_id: Optional[str] = None,
) -> dict[str, Any]:
    """Count scheduled / no-show meetings using the Engagements API.

    HubSpot's default Meeting engagement uses the ``hs_meeting_outcome``
    property with values like ``COMPLETED``, ``NO_SHOW``, ``RESCHEDULED``,
    ``CANCELED``. We count anything with a non-empty outcome plus meetings
    whose start time is in the past as "scheduled", and any whose outcome
    is ``NO_SHOW`` as no-shows.
    """
    start_ms = _to_epoch_ms(start_date, end_of_day=False)
    end_ms = _to_epoch_ms(end_date, end_of_day=True)

    filters: list[dict[str, Any]] = [
        {
            "propertyName": "hs_meeting_start_time",
            "operator": "GTE",
            "value": str(start_ms),
        },
        {
            "propertyName": "hs_meeting_start_time",
            "operator": "LTE",
            "value": str(end_ms),
        },
    ]
    if owner_id:
        filters.append(
            {
                "propertyName": "hubspot_owner_id",
                "operator": "EQ",
                "value": str(owner_id),
            }
        )

    scheduled = 0
    no_show = 0

    after: Optional[str] = None
    while scheduled < MAX_MEETINGS:
        request = {
            "filterGroups": [{"filters": filters}],
            "properties": [
                "hs_meeting_title",
                "hs_meeting_start_time",
                "hs_meeting_end_time",
                "hs_meeting_outcome",
                "hubspot_owner_id",
            ],
            "limit": PAGE_SIZE,
            "sorts": [
                {"propertyName": "hs_meeting_start_time", "direction": "DESCENDING"},
            ],
        }
        if after:
            request["after"] = after

        # Meetings live under crm.objects with the "meetings" object type.
        response = client.crm.objects.search_api.do_search(
            object_type="meetings",
            public_object_search_request=request,
        )

        results = getattr(response, "results", []) or []
        for meeting in results:
            props = getattr(meeting, "properties", {}) or {}
            outcome = (props.get("hs_meeting_outcome") or "").upper()

            scheduled += 1
            if outcome == "NO_SHOW":
                no_show += 1

        paging = getattr(response, "paging", None)
        next_page = getattr(paging, "next", None) if paging else None
        after = getattr(next_page, "after", None) if next_page else None
        if not after:
            break

    return {
        "scheduled_meetings": scheduled,
        "no_show_meetings": no_show,
        "available": True,
    }
