"""
Admin views for analytics reports.
These are registered on the Django admin site as custom views.
"""

from django.contrib.admin import site as admin_site
from django.shortcuts import render


def earned_premium_admin_view(request):
    """Admin report page for earned premium (GAAP revenue recognition)."""
    from analytics.reports import get_earned_premium_report

    month = request.GET.get("month", "")
    carrier = request.GET.get("carrier", "")
    coverage_type = request.GET.get("coverage_type", "")

    report = get_earned_premium_report(
        month=month or None,
        carrier=carrier or None,
        coverage_type=coverage_type or None,
    )

    context = {
        **admin_site.each_context(request),
        "title": "Earned Premium Report",
        "report": report,
        "month": month,
        "carrier": carrier,
        "coverage_type": coverage_type,
    }
    return render(request, "admin/analytics/earned_premium_report.html", context)
