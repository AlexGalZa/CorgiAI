from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display

from common.admin_permissions import is_corgi_admin
from sla.models import SLAMetric


@admin.register(SLAMetric)
class SLAMetricAdmin(UnfoldModelAdmin):
    list_display = [
        "metric_type",
        "entity_type",
        "entity_id",
        "target_hours",
        "elapsed_hours_display",
        "breach_badge",
        "started_at",
        "completed_at",
    ]
    list_filter = ["metric_type", "breached", "entity_type"]
    search_fields = ["entity_type", "entity_id"]
    ordering = ["-started_at"]
    readonly_fields = ["created_at", "updated_at", "elapsed_hours_display"]

    fieldsets = (
        (
            "SLA",
            {
                "fields": ("metric_type", "target_hours", "entity_type", "entity_id"),
            },
        ),
        (
            "Timing",
            {
                "fields": (
                    "started_at",
                    "completed_at",
                    "elapsed_hours_display",
                    "breached",
                ),
            },
        ),
        (
            "Notes",
            {
                "fields": ("notes",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @display(description="Elapsed Hours")
    def elapsed_hours_display(self, obj):
        return f"{obj.elapsed_hours}h"

    @display(description="Breach", label=True)
    def breach_badge(self, obj):
        if obj.breached:
            return "danger", "BREACHED"
        if not obj.completed_at:
            return "warning", "Open"
        return "success", "OK"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "compliance/",
                self.admin_site.admin_view(self.compliance_report_view),
                name="sla_compliance_report",
            ),
        ]
        return custom_urls + urls

    def compliance_report_view(self, request):
        from sla.services import get_compliance_rate
        from sla.models import SLAMetric

        overall = get_compliance_rate()
        by_type = [
            {
                "label": label,
                "slug": slug,
                **get_compliance_rate(slug),
            }
            for slug, label in SLAMetric.METRIC_TYPE_CHOICES
        ]

        context = {
            **self.admin_site.each_context(request),
            "title": "SLA Compliance Report",
            "overall": overall,
            "by_type": by_type,
            "opts": self.model._meta,
        }
        return render(request, "admin/sla/compliance_report.html", context)

    def changelist_view(self, request, extra_context=None):
        from django.urls import reverse

        extra_context = extra_context or {}
        extra_context["compliance_url"] = reverse("admin:sla_compliance_report")
        return super().changelist_view(request, extra_context=extra_context)

    def has_module_perms(self, request, app_label=None):
        if not is_corgi_admin(request.user):
            return False
        return (
            super().has_module_perms(request, app_label)
            if hasattr(super(), "has_module_perms")
            else True
        )

    def has_view_permission(self, request, obj=None):
        if not is_corgi_admin(request.user):
            return False
        return super().has_view_permission(request, obj)
