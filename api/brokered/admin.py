"""
Admin configuration for Brokered Quote Requests — the underwriter workstation.
"""

import json

from django.contrib import admin
from django.utils import timezone
from django.utils.html import mark_safe
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display

from brokered.models import BrokeredQuoteRequest


class BrokeringStatusFilter(admin.SimpleListFilter):
    """Admin changelist filter that zooms in on deals still out to market."""

    title = "Brokering state"
    parameter_name = "brokering_state"

    def lookups(self, request, model_admin):
        return (
            ("brokering", "Stuck in brokering"),
            ("brokering_3d", "Brokering >= 3 days"),
            ("brokering_7d", "Brokering >= 7 days"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        qs = queryset.filter(status="brokering")
        if value == "brokering":
            return qs
        from datetime import timedelta

        days = 3 if value == "brokering_3d" else 7
        cutoff = timezone.now() - timedelta(days=days)
        return qs.filter(updated_at__lte=cutoff)


@admin.register(BrokeredQuoteRequest)
class BrokeredQuoteRequestAdmin(UnfoldModelAdmin):
    list_display = [
        "quote_link_header",
        "coverage_type",
        "carrier",
        "status_colored",
        "priority_colored",
        "days_stuck",
        "premium_display",
        "assigned_to",
        "external_quote_number",
        "updated_at",
    ]
    list_display_links = ["quote_link_header"]
    list_filter = [
        BrokeringStatusFilter,
        "status",
        "priority",
        "carrier",
        "coverage_type",
        "assigned_to",
        "created_at",
    ]
    search_fields = [
        "quote__quote_number",
        "carrier",
        "coverage_type",
        "external_quote_number",
        "notes",
    ]
    readonly_fields = ["created_at", "updated_at", "form_payload_display"]
    ordering = ["-created_at"]
    list_per_page = 25
    date_hierarchy = "created_at"
    autocomplete_fields = ["quote", "assigned_to"]

    fieldsets = (
        # Always visible — key info
        (
            "Overview",
            {
                "classes": ["tab"],
                "fields": (
                    "quote",
                    "coverage_type",
                    "carrier",
                    "status",
                    "priority",
                    "assigned_to",
                ),
            },
        ),
        (
            "Quote Result",
            {
                "classes": ["tab"],
                "fields": (
                    "premium_amount",
                    "external_quote_number",
                    "quote_url",
                    "decline_reason",
                ),
            },
        ),
        (
            "Form Payload",
            {
                "classes": ["tab"],
                "fields": ("form_payload_display",),
            },
        ),
        (
            "Automation",
            {
                "classes": ["tab"],
                "fields": ("run_id",),
            },
        ),
        (
            "Notes",
            {
                "classes": ["tab"],
                "fields": ("notes",),
            },
        ),
        (
            "Timestamps",
            {
                "classes": ["tab"],
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @display(description="Quote", header=True)
    def quote_link_header(self, obj):
        return [obj.quote.quote_number, ""]

    @display(
        description="Status",
        ordering="status",
        label={
            "pending": "warning",
            "in_progress": "info",
            "quoted": "success",
            "declined": "danger",
            "failed": "danger",
        },
    )
    def status_colored(self, obj):
        return obj.status, obj.get_status_display()

    @display(
        description="Priority",
        ordering="priority",
        label={
            "low": "info",
            "medium": "warning",
            "high": "danger",
            "urgent": "danger",
        },
    )
    def priority_colored(self, obj):
        return obj.priority, obj.get_priority_display()

    @display(description="Premium")
    def premium_display(self, obj):
        if obj.premium_amount:
            return f"${obj.premium_amount:,.2f}"
        return "—"

    @admin.display(description="Days stuck", ordering="updated_at")
    def days_stuck(self, obj):
        """Approximate days this deal has been sitting in 'brokering'.

        NOTE: BrokeredQuoteRequest does not yet record a dedicated
        ``status_changed_at`` timestamp, so we fall back to ``updated_at``
        (auto_now). TODO(H10): switch to a real status-transition timestamp
        once one exists.
        """
        if obj.status != "brokering":
            return "—"
        anchor = obj.updated_at or obj.created_at
        if anchor is None:
            return "—"
        days = max((timezone.now() - anchor).days, 0)
        return f"{days}d"

    @admin.display(description="Form Payload")
    def form_payload_display(self, obj):
        if not obj.form_payload:
            return mark_safe('<em style="color:#6b7280">No form payload</em>')

        rows = []
        data = obj.form_payload if isinstance(obj.form_payload, dict) else {}
        for key, value in data.items():
            label = key.replace("_", " ").replace("-", " ").title()
            if isinstance(value, bool):
                val_display = (
                    '<span style="color:#16a34a">Yes</span>'
                    if value
                    else '<span style="color:#6b7280">No</span>'
                )
            elif isinstance(value, dict):
                val_display = f'<pre style="margin:0;font-size:11px;background:#f9fafb;padding:4px 8px;border-radius:4px">{json.dumps(value, indent=2)}</pre>'
            elif isinstance(value, list):
                val_display = (
                    ", ".join(str(v) for v in value)
                    if value
                    else '<span style="color:#6b7280">—</span>'
                )
            else:
                val_display = (
                    str(value)
                    if value is not None
                    else '<span style="color:#6b7280">—</span>'
                )
            rows.append(
                f'<tr style="border-top:1px solid #f3f4f6">'
                f'<td style="padding:8px 14px;font-size:12px;font-weight:500;color:#6b7280;width:220px;vertical-align:top">{label}</td>'
                f'<td style="padding:8px 14px;font-size:12px;color:#374151">{val_display}</td>'
                f"</tr>"
            )
        if not rows:
            return mark_safe('<em style="color:#6b7280">Empty payload</em>')
        return mark_safe(
            '<table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;background:#fff">'
            "<tbody>" + "".join(rows) + "</tbody></table>"
        )
