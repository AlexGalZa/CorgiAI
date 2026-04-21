"""
Regulatory Reporting Exports (V3 #47)

Generates state-by-state premium, policy count, and loss data in
standard regulatory format (CSV) for filing with state insurance departments.

Standard format columns (based on NAIC annual statement schedule):
    state, quarter, policy_count, written_premium, earned_premium,
    paid_losses, incurred_losses, loss_ratio

Usage:
    from analytics.regulatory import get_regulatory_report, export_regulatory_csv
    data = get_regulatory_report(state="CA", quarter="2025-Q1")
    csv_content = export_regulatory_csv(state="CA", quarter="2025-Q1")
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum

# Standard US states supported
SUPPORTED_STATES = [
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
]


# Available quarters: last 8 quarters (2 years)
def _get_available_quarters() -> list[str]:
    from django.utils import timezone

    now = timezone.now()
    quarters = []
    year = now.year
    q = (now.month - 1) // 3 + 1
    for _ in range(8):
        quarters.append(f"{year}-Q{q}")
        q -= 1
        if q == 0:
            q = 4
            year -= 1
    return quarters


SUPPORTED_QUARTERS = _get_available_quarters()


def _parse_quarter(quarter: str) -> tuple[int, int] | None:
    """Parse 'YYYY-QN' into (year, quarter_number). Returns None if invalid."""
    try:
        year_str, q_str = quarter.split("-Q")
        return int(year_str), int(q_str)
    except (ValueError, AttributeError):
        return None


def get_regulatory_report(
    state: str | None = None,
    quarter: str | None = None,
) -> dict[str, Any]:
    """
    Generate regulatory report data for a given state and/or quarter.

    Returns a list of rows suitable for the NAIC annual statement schedule.

    Args:
        state: 2-letter US state code (e.g. "CA"). None = all states.
        quarter: Quarter string "YYYY-QN" (e.g. "2025-Q1"). None = all quarters.

    Returns:
        Dict with rows (list of dicts), totals, and applied filters.
    """
    from policies.models import Policy, EarnedPremiumRecord
    from claims.models import Claim

    # --- Base Policy queryset ---
    policy_qs = Policy.objects.filter(
        status__in=["active", "expired", "cancelled"],
        principal_state__isnull=False,
    ).exclude(principal_state="")

    if state:
        policy_qs = policy_qs.filter(principal_state=state.upper())

    if quarter:
        parsed = _parse_quarter(quarter)
        if parsed:
            year, q = parsed
            # Quarter start/end months
            q_start_month = (q - 1) * 3 + 1
            q_end_month = q * 3
            policy_qs = policy_qs.filter(
                effective_date__year=year,
                effective_date__month__gte=q_start_month,
                effective_date__month__lte=q_end_month,
            )

    # Aggregate by state
    state_rows = (
        policy_qs.values("principal_state")
        .annotate(
            policy_count=Count("id", distinct=True),
            written_premium=Sum("premium"),
        )
        .order_by("principal_state")
    )

    # Pull earned premium by state (via policy join)
    earned_map: dict[str, Decimal] = {}
    earned_qs = (
        EarnedPremiumRecord.objects.select_related("policy")
        .filter(policy__principal_state__isnull=False)
        .exclude(policy__principal_state="")
    )
    if state:
        earned_qs = earned_qs.filter(policy__principal_state=state.upper())
    if quarter and parsed:
        year, q = parsed
        q_start_month = (q - 1) * 3 + 1
        q_end_month = q * 3
        earned_qs = earned_qs.filter(
            period_start__year=year,
            period_start__month__gte=q_start_month,
            period_start__month__lte=q_end_month,
        )
    for row in earned_qs.values("policy__principal_state").annotate(
        total_earned=Sum("earned_amount")
    ):
        earned_map[row["policy__principal_state"]] = row["total_earned"] or Decimal("0")

    # Pull losses by state (via policy join)
    paid_loss_map: dict[str, Decimal] = {}
    incurred_loss_map: dict[str, Decimal] = {}
    claim_qs = (
        Claim.objects.filter(is_deleted=False)
        .select_related("policy")
        .filter(policy__principal_state__isnull=False)
        .exclude(policy__principal_state="")
    )
    if state:
        claim_qs = claim_qs.filter(policy__principal_state=state.upper())
    if quarter and parsed:
        year, q = parsed
        q_start_month = (q - 1) * 3 + 1
        q_end_month = q * 3
        claim_qs = claim_qs.filter(
            claim_report_date__year=year,
            claim_report_date__month__gte=q_start_month,
            claim_report_date__month__lte=q_end_month,
        )
    for row in claim_qs.values("policy__principal_state").annotate(
        paid=Sum("paid_loss"),
        reserve=Sum("case_reserve_loss"),
    ):
        st = row["policy__principal_state"]
        paid = row["paid"] or Decimal("0")
        reserve = row["reserve"] or Decimal("0")
        paid_loss_map[st] = paid
        incurred_loss_map[st] = paid + reserve

    # Build output rows
    rows = []
    for row in state_rows:
        st = row["principal_state"]
        written = float(row["written_premium"] or 0)
        earned = float(earned_map.get(st, Decimal("0")))
        paid_loss = float(paid_loss_map.get(st, Decimal("0")))
        incurred_loss = float(incurred_loss_map.get(st, Decimal("0")))
        loss_ratio = round(incurred_loss / earned * 100, 1) if earned > 0 else None

        rows.append(
            {
                "state": st,
                "quarter": quarter or "ALL",
                "policy_count": row["policy_count"],
                "written_premium": written,
                "earned_premium": earned,
                "paid_losses": paid_loss,
                "incurred_losses": incurred_loss,
                "loss_ratio_pct": loss_ratio,
            }
        )

    # Grand totals
    totals = {
        "policy_count": sum(r["policy_count"] for r in rows),
        "written_premium": sum(r["written_premium"] for r in rows),
        "earned_premium": sum(r["earned_premium"] for r in rows),
        "paid_losses": sum(r["paid_losses"] for r in rows),
        "incurred_losses": sum(r["incurred_losses"] for r in rows),
    }
    ep = totals["earned_premium"]
    totals["loss_ratio_pct"] = (
        round(totals["incurred_losses"] / ep * 100, 1) if ep > 0 else None
    )

    return {
        "rows": rows,
        "totals": totals,
        "filters": {"state": state, "quarter": quarter},
    }


def export_regulatory_csv(
    state: str | None = None,
    quarter: str | None = None,
) -> str:
    """
    Export regulatory report as CSV string.

    Columns: state, quarter, policy_count, written_premium, earned_premium,
             paid_losses, incurred_losses, loss_ratio_pct
    """
    report = get_regulatory_report(state=state, quarter=quarter)

    output = io.StringIO()
    fieldnames = [
        "state",
        "quarter",
        "policy_count",
        "written_premium",
        "earned_premium",
        "paid_losses",
        "incurred_losses",
        "loss_ratio_pct",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for row in report["rows"]:
        writer.writerow({k: row[k] for k in fieldnames})

    # Add totals row
    totals = report["totals"]
    writer.writerow(
        {
            "state": "TOTAL",
            "quarter": quarter or "ALL",
            "policy_count": totals["policy_count"],
            "written_premium": totals["written_premium"],
            "earned_premium": totals["earned_premium"],
            "paid_losses": totals["paid_losses"],
            "incurred_losses": totals["incurred_losses"],
            "loss_ratio_pct": totals["loss_ratio_pct"],
        }
    )

    return output.getvalue()
