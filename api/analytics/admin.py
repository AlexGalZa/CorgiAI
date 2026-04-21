"""
Django admin registrations and extra URL patterns for the analytics app.
"""

from django.contrib import admin
from django.urls import path
from django.shortcuts import render


def register_analytics_admin_urls(admin_site):
    """Return extra URL patterns for the analytics admin views."""
    from analytics.admin_views import earned_premium_admin_view

    def _pipeline_velocity_view(request):
        from analytics.pipeline import get_pipeline_velocity

        context = {
            **admin_site.each_context(request),
            "title": "Sales Pipeline Velocity",
            "data": get_pipeline_velocity(),
        }
        return render(request, "admin/analytics/pipeline_velocity.html", context)

    def _retention_view(request):
        from analytics.retention import get_retention_report

        context = {
            **admin_site.each_context(request),
            "title": "Customer Retention & Churn",
            "data": get_retention_report(),
        }
        return render(request, "admin/analytics/retention.html", context)

    def _broker_performance_view(request):
        from analytics.broker_performance import get_broker_performance

        context = {
            **admin_site.each_context(request),
            "title": "Broker Performance Scoreboard",
            "data": get_broker_performance(),
        }
        return render(request, "admin/analytics/broker_performance.html", context)

    def _claims_triangle_view(request):
        from analytics.claims_triangle import get_claims_triangle

        context = {
            **admin_site.each_context(request),
            "title": "Claims Development Triangle",
            "data": get_claims_triangle(),
        }
        return render(request, "admin/analytics/claims_triangle.html", context)

    def _regulatory_reporting_view(request):
        from django.http import HttpResponse
        from analytics.regulatory import (
            get_regulatory_report,
            export_regulatory_csv,
            SUPPORTED_STATES,
            SUPPORTED_QUARTERS,
        )

        state = request.GET.get("state", "")
        quarter = request.GET.get("quarter", "")

        # CSV export
        if request.GET.get("export") == "csv":
            csv_content = export_regulatory_csv(
                state=state or None,
                quarter=quarter or None,
            )
            filename_parts = ["regulatory"]
            if state:
                filename_parts.append(state)
            if quarter:
                filename_parts.append(quarter.replace("-", "_"))
            filename = "_".join(filename_parts) + ".csv"
            response = HttpResponse(csv_content, content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        context = {
            **admin_site.each_context(request),
            "title": "Regulatory Reporting",
            "states": SUPPORTED_STATES,
            "quarters": SUPPORTED_QUARTERS,
            "selected_state": state,
            "selected_quarter": quarter,
            "report": get_regulatory_report(
                state=state or None, quarter=quarter or None
            ),
        }
        return render(request, "admin/analytics/regulatory_reporting.html", context)

    def _executive_dashboard_view(request):
        from analytics.executive import get_executive_dashboard

        context = {
            **admin_site.each_context(request),
            "title": "Executive Dashboard",
            "data": get_executive_dashboard(),
        }
        return render(request, "admin/analytics/executive_dashboard.html", context)

    return [
        path(
            "admin/reports/earned-premium/",
            admin_site.admin_view(earned_premium_admin_view),
            name="analytics_earned_premium_report",
        ),
        path(
            "admin/analytics/pipeline-velocity/",
            admin_site.admin_view(_pipeline_velocity_view),
            name="analytics_pipeline_velocity",
        ),
        path(
            "admin/analytics/retention/",
            admin_site.admin_view(_retention_view),
            name="analytics_retention",
        ),
        path(
            "admin/analytics/broker-performance/",
            admin_site.admin_view(_broker_performance_view),
            name="analytics_broker_performance",
        ),
        path(
            "admin/analytics/claims-triangle/",
            admin_site.admin_view(_claims_triangle_view),
            name="analytics_claims_triangle",
        ),
        path(
            "admin/analytics/regulatory-reporting/",
            admin_site.admin_view(_regulatory_reporting_view),
            name="analytics_regulatory_reporting",
        ),
        path(
            "admin/executive-dashboard/",
            admin_site.admin_view(_executive_dashboard_view),
            name="analytics_executive_dashboard",
        ),
    ]


try:
    from analytics.models import ScheduledReport

    @admin.register(ScheduledReport)
    class ScheduledReportAdmin(admin.ModelAdmin):
        list_display = [
            "name",
            "report_type",
            "frequency",
            "is_active",
            "last_sent_at",
            "created_at",
        ]
        list_filter = ["report_type", "frequency", "is_active"]
        search_fields = ["name"]
        readonly_fields = ["last_sent_at", "created_at", "updated_at"]
        fieldsets = [
            (None, {"fields": ["name", "report_type", "frequency", "is_active"]}),
            ("Recipients", {"fields": ["recipients"]}),
            ("Filters", {"fields": ["extra_filters"]}),
            ("Status", {"fields": ["last_sent_at", "created_at", "updated_at"]}),
        ]

except ImportError:
    pass
