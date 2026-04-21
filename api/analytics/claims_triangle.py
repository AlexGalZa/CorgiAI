"""
Claims Development Triangle (V3 #46)

Standard actuarial loss development triangle showing how paid and incurred
losses develop over time by accident year and development period.

Usage:
    from analytics.claims_triangle import get_claims_triangle
    data = get_claims_triangle()
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Sum
from django.db.models.functions import ExtractYear
from django.utils import timezone


def get_claims_triangle() -> dict[str, Any]:
    """
    Build the standard actuarial claims development triangle.

    The triangle is keyed by:
        - Accident Year (year of incident_date)
        - Development Period (calendar year of claim_report_date or current year)

    For each cell we compute:
        - paid_loss: cumulative paid losses up to that development year
        - incurred_loss: paid_loss + case_reserve_loss (total incurred)

    Returns:
        {
            "accident_years": [2022, 2023, 2024, 2025],
            "development_periods": [0, 1, 2, 3],   # years since accident year
            "paid_triangle": {
                2022: {0: 12000.0, 1: 45000.0, 2: 60000.0, 3: 65000.0},
                ...
            },
            "incurred_triangle": { ... },
            "development_factors": {   # link ratios paid_n+1 / paid_n
                "paid": { "0_to_1": 3.75, ... },
                "incurred": { ... }
            },
            "summary": {
                "total_paid": 182000.0,
                "total_incurred": 210000.0,
                "open_claims": 14,
                "closed_claims": 82,
            }
        }
    """
    from claims.models import Claim

    now = timezone.now()
    current_year = now.year

    # Pull all non-deleted claims with valid dates
    claims_qs = (
        Claim.objects.filter(is_deleted=False, incident_date__isnull=False)
        .annotate(
            accident_year=ExtractYear("incident_date"),
            dev_year=ExtractYear("claim_report_date"),
        )
        .values("accident_year", "dev_year", "paid_loss", "case_reserve_loss", "status")
    )

    # Build raw accumulation by (accident_year, development_period)
    # development_period = dev_year - accident_year (0-based)
    accident_years: set[int] = set()
    raw: dict[tuple[int, int], dict] = {}

    for row in claims_qs:
        ay = row["accident_year"]
        dy = (
            row["dev_year"] or current_year
        )  # if no report date yet, assume current year
        dev_period = max(0, dy - ay)

        accident_years.add(ay)

        key = (ay, dev_period)
        if key not in raw:
            raw[key] = {"paid": Decimal("0"), "reserve": Decimal("0"), "count": 0}

        raw[key]["paid"] += row["paid_loss"] or Decimal("0")
        raw[key]["reserve"] += row["case_reserve_loss"] or Decimal("0")
        raw[key]["count"] += 1

    if not accident_years:
        return _empty_triangle()

    sorted_years = sorted(accident_years)
    max_dev = current_year - min(sorted_years)
    dev_periods = list(range(0, max_dev + 1))

    # Build cumulative triangles
    paid_triangle: dict[int, dict[int, float]] = {}
    incurred_triangle: dict[int, dict[int, float]] = {}

    for ay in sorted_years:
        paid_cum = Decimal("0")
        incurred_cum = Decimal("0")
        paid_triangle[ay] = {}
        incurred_triangle[ay] = {}

        max_dev_for_ay = current_year - ay

        for dp in range(0, max_dev_for_ay + 1):
            key = (ay, dp)
            cell = raw.get(key, {"paid": Decimal("0"), "reserve": Decimal("0")})
            paid_cum += cell["paid"]
            incurred_cum += cell["paid"] + cell["reserve"]

            paid_triangle[ay][dp] = float(paid_cum)
            incurred_triangle[ay][dp] = float(incurred_cum)

    # Compute age-to-age development factors (link ratios)
    paid_factors: dict[str, float | None] = {}
    incurred_factors: dict[str, float | None] = {}

    for dp in dev_periods[:-1]:
        paid_nums = []
        incurred_nums = []

        for ay in sorted_years:
            p_curr = paid_triangle[ay].get(dp)
            p_next = paid_triangle[ay].get(dp + 1)
            i_curr = incurred_triangle[ay].get(dp)
            i_next = incurred_triangle[ay].get(dp + 1)

            if p_curr and p_next and p_curr > 0:
                paid_nums.append((p_curr, p_next))
            if i_curr and i_next and i_curr > 0:
                incurred_nums.append((i_curr, i_next))

        label = f"{dp}_to_{dp + 1}"

        if paid_nums:
            sum_curr = sum(c for c, n in paid_nums)
            sum_next = sum(n for c, n in paid_nums)
            paid_factors[label] = round(sum_next / sum_curr, 4) if sum_curr else None
        else:
            paid_factors[label] = None

        if incurred_nums:
            sum_curr = sum(c for c, n in incurred_nums)
            sum_next = sum(n for c, n in incurred_nums)
            incurred_factors[label] = (
                round(sum_next / sum_curr, 4) if sum_curr else None
            )
        else:
            incurred_factors[label] = None

    # Summary stats
    from django.db.models import Count, Q

    agg = Claim.objects.filter(is_deleted=False).aggregate(
        total_paid=Sum("paid_loss"),
        total_reserve=Sum("case_reserve_loss"),
        open_claims=Count(
            "id", filter=Q(status__in=["submitted", "under_review", "approved"])
        ),
        closed_claims=Count("id", filter=Q(status__in=["denied", "closed"])),
    )

    total_paid = float(agg["total_paid"] or 0)
    total_incurred = float((agg["total_paid"] or 0) + (agg["total_reserve"] or 0))

    return {
        "accident_years": sorted_years,
        "development_periods": dev_periods,
        "paid_triangle": paid_triangle,
        "incurred_triangle": incurred_triangle,
        "development_factors": {
            "paid": paid_factors,
            "incurred": incurred_factors,
        },
        "summary": {
            "total_paid": total_paid,
            "total_incurred": total_incurred,
            "open_claims": agg["open_claims"] or 0,
            "closed_claims": agg["closed_claims"] or 0,
        },
        "generated_at": now.isoformat(),
    }


def _empty_triangle() -> dict[str, Any]:
    """Return an empty triangle structure when no data exists."""
    return {
        "accident_years": [],
        "development_periods": [],
        "paid_triangle": {},
        "incurred_triangle": {},
        "development_factors": {"paid": {}, "incurred": {}},
        "summary": {
            "total_paid": 0.0,
            "total_incurred": 0.0,
            "open_claims": 0,
            "closed_claims": 0,
        },
        "generated_at": timezone.now().isoformat(),
    }
