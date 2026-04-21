"""
Dashboard callback for django-unfold admin.

Provides KPI metrics, pipeline data, and recent activity
for the admin dashboard template at templates/admin/index.html.
"""

from django.db.models import Sum, Count
from django.utils import timezone


def dashboard_callback(request, context):
    """Populate dashboard context with key metrics and pipeline data."""
    from policies.models import Policy, Payment
    from claims.models import Claim
    from quotes.models import Quote
    from common.models import AuditLogEntry

    now = timezone.now()

    # ── KPI Cards ──
    active_policies = Policy.objects.filter(status="active").count()
    open_claims = Claim.objects.exclude(status__in=["closed", "denied"]).count()
    Quote.objects.filter(status="needs_review").count()

    total_premium = (
        Policy.objects.filter(status="active").aggregate(total=Sum("premium"))["total"]
        or 0
    )

    monthly_collected = (
        Payment.objects.filter(
            paid_at__year=now.year,
            paid_at__month=now.month,
            status="paid",
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    context["kpi"] = [
        {
            "title": "Active Policies",
            "metric": f"{active_policies:,}",
            "footer": "Currently in force",
        },
        {
            "title": "Total Premium",
            "metric": f"${total_premium:,.0f}",
            "footer": "Annual written premium",
        },
        {
            "title": "Open Claims",
            "metric": f"{open_claims:,}",
            "footer": "Pending resolution",
        },
        {
            "title": "Collected This Month",
            "metric": f"${monthly_collected:,.0f}",
            "footer": now.strftime("%B %Y"),
        },
    ]

    # ── Quote Pipeline ──
    pipeline_qs = (
        Quote.objects.values("status").annotate(count=Count("id")).order_by("status")
    )
    pipeline_map = {row["status"]: row["count"] for row in pipeline_qs}
    total_quotes = sum(pipeline_map.values()) or 1  # avoid division by zero

    status_config = [
        ("draft", "Draft", "bg-gray-400", "bg-gray-300"),
        ("submitted", "Submitted", "bg-blue-400", "bg-blue-400"),
        ("needs_review", "Needs Review", "bg-yellow-400", "bg-yellow-400"),
        ("quoted", "Quoted", "bg-purple-400", "bg-purple-400"),
        ("purchased", "Purchased", "bg-green-400", "bg-green-500"),
        ("declined", "Declined", "bg-red-400", "bg-red-400"),
    ]

    context["pipeline"] = [
        {
            "label": label,
            "count": pipeline_map.get(status, 0),
            "percent": round((pipeline_map.get(status, 0) / total_quotes) * 100),
            "color": dot_color,
            "bar_color": bar_color,
        }
        for status, label, dot_color, bar_color in status_config
    ]

    # ── Recent Activity ──
    context["recent_activity"] = AuditLogEntry.objects.select_related("user").order_by(
        "-timestamp"
    )[:8]

    return context
