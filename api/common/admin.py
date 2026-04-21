"""
Admin configuration for common models: Notification and AuditLogEntry.
"""

from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display

from common.models import (
    Notification,
    AuditLogEntry,
    DataAccessLog,
    FeatureFlag,
    PlatformConfig,
)
from common.widgets import PrettyJSONWidget


@admin.register(Notification)
class NotificationAdmin(UnfoldModelAdmin):
    list_display = [
        "title",
        "user",
        "type_colored",
        "read_status",
        "action_url_link",
        "created_at",
    ]
    list_filter = ["notification_type", "created_at"]
    search_fields = ["title", "message", "user__email"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]
    list_per_page = 25
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Notification",
            {
                "fields": (
                    "user",
                    "organization",
                    "notification_type",
                    "title",
                    "message",
                ),
            },
        ),
        (
            "Status",
            {
                "classes": ["tab"],
                "fields": ("read_at", "action_url"),
            },
        ),
        (
            "Related Object",
            {
                "classes": ["tab"],
                "fields": ("related_content_type", "related_object_id"),
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

    @display(
        description="Type",
        ordering="notification_type",
        label={
            "info": "info",
            "warning": "warning",
            "error": "danger",
            "success": "success",
            "quote_update": "info",
            "policy_update": "info",
            "claim_update": "warning",
            "billing": "info",
            "system": "info",
        },
    )
    def type_colored(self, obj):
        return obj.notification_type, obj.get_notification_type_display()

    @admin.display(description="Read")
    def read_status(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="color:#28a745; font-weight:bold;">✓ Read</span>'
            )
        return format_html(
            '<span style="color:#dc3545; font-weight:bold;">● Unread</span>'
        )

    @admin.display(description="Action")
    def action_url_link(self, obj):
        if obj.action_url:
            return format_html(
                '<a href="{}" target="_blank">Open →</a>', obj.action_url
            )
        return "—"


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(UnfoldModelAdmin):
    list_display = [
        "timestamp",
        "user",
        "action_colored",
        "model_name",
        "object_id",
        "ip_address",
    ]
    list_filter = ["action", "model_name", "timestamp"]
    search_fields = ["user__email", "model_name", "object_id", "ip_address"]
    readonly_fields = [
        "user",
        "action",
        "model_name",
        "object_id",
        "changes",
        "ip_address",
        "user_agent",
        "timestamp",
    ]
    ordering = ["-timestamp"]
    list_per_page = 25
    date_hierarchy = "timestamp"

    fieldsets = (
        (
            "Action",
            {
                "fields": ("user", "action", "model_name", "object_id"),
            },
        ),
        (
            "Changes",
            {
                "classes": ["tab"],
                "fields": ("changes",),
            },
        ),
        (
            "Request Info",
            {
                "classes": ["tab"],
                "fields": ("ip_address", "user_agent"),
            },
        ),
        (
            "Timestamp",
            {
                "classes": ["tab"],
                "fields": ("timestamp",),
            },
        ),
    )

    @display(
        description="Action",
        ordering="action",
        label={
            "create": "success",
            "update": "info",
            "delete": "danger",
            "login": "info",
            "logout": "info",
            "impersonate": "warning",
            "export": "info",
            "approve": "success",
            "decline": "danger",
        },
    )
    def action_colored(self, obj):
        return obj.action, obj.get_action_display()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ── Data Access Log (SOC 2, V3 #51) ──────────────────────────────────────────


@admin.register(DataAccessLog)
class DataAccessLogAdmin(UnfoldModelAdmin):
    list_display = [
        "timestamp",
        "user",
        "action_colored",
        "model_name",
        "object_id",
        "ip_address",
    ]
    list_filter = ["action", "model_name", "timestamp"]
    search_fields = ["user__email", "model_name", "object_id", "ip_address"]
    readonly_fields = [
        "timestamp",
        "user",
        "model_name",
        "object_id",
        "action",
        "ip_address",
        "user_agent",
        "extra",
    ]
    ordering = ["-timestamp"]
    list_per_page = 50
    date_hierarchy = "timestamp"

    fieldsets = (
        (
            "Access Info",
            {
                "fields": ("user", "action", "model_name", "object_id"),
            },
        ),
        (
            "Request Info",
            {
                "classes": ["tab"],
                "fields": ("ip_address", "user_agent", "extra"),
            },
        ),
        (
            "Timestamp",
            {
                "classes": ["tab"],
                "fields": ("timestamp",),
            },
        ),
    )

    @display(
        description="Action",
        ordering="action",
        label={
            "view": "info",
            "export": "warning",
            "modify": "success",
            "delete": "danger",
        },
    )
    def action_colored(self, obj):
        return obj.action, obj.get_action_display()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ── Compliance Calendar (V3 #29) ──────────────────────────────────────────────

from common.models import ComplianceDeadline  # noqa: E402


@admin.register(ComplianceDeadline)
class ComplianceDeadlineAdmin(UnfoldModelAdmin):
    list_display = [
        "title",
        "type_badge",
        "deadline_date",
        "days_until_badge",
        "responsible_person",
        "status_badge",
        "alert_sent_at",
    ]
    list_filter = ["type", "status", "deadline_date"]
    search_fields = ["title", "responsible_person", "description", "notes"]
    ordering = ["deadline_date"]
    list_per_page = 30
    date_hierarchy = "deadline_date"

    readonly_fields = [
        "created_at",
        "updated_at",
        "alert_sent_at",
        "completed_at",
        "days_until_display",
    ]

    fieldsets = (
        (
            "Deadline",
            {
                "fields": (
                    "title",
                    "type",
                    "deadline_date",
                    "status",
                    "responsible_person",
                ),
            },
        ),
        (
            "Details",
            {
                "fields": ("description", "notes"),
            },
        ),
        (
            "Tracking",
            {
                "fields": ("days_until_display", "completed_at", "alert_sent_at"),
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

    def save_model(self, request, obj, form, change):
        from django.utils import timezone

        if change and obj.status == "completed" and not obj.completed_at:
            obj.completed_at = timezone.now()
        super().save_model(request, obj, form, change)

    @display(
        description="Type",
        ordering="type",
        label={
            "license_renewal": "info",
            "carrier_filing": "warning",
            "regulatory": "danger",
            "audit": "success",
        },
    )
    def type_badge(self, obj):
        return obj.type, obj.get_type_display()

    @display(
        description="Status",
        ordering="status",
        label={
            "open": "warning",
            "in_progress": "info",
            "completed": "success",
            "overdue": "danger",
            "waived": "default",
        },
    )
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    @display(description="Days Until")
    def days_until_badge(self, obj):
        days = obj.days_until_deadline
        if days < 0:
            return format_html(
                '<span style="color:#dc2626;font-weight:700;">{} days overdue</span>',
                abs(days),
            )
        elif days <= 7:
            return format_html(
                '<span style="color:#d97706;font-weight:700;">{} days</span>', days
            )
        elif days <= 30:
            return format_html('<span style="color:#2563eb;">{} days</span>', days)
        return format_html("{} days", days)

    @display(description="Days Until Deadline")
    def days_until_display(self, obj):
        days = obj.days_until_deadline
        if days < 0:
            return f"{abs(days)} days overdue"
        return f"{days} days remaining"


@admin.register(FeatureFlag)
class FeatureFlagAdmin(UnfoldModelAdmin):
    list_display = [
        "key",
        "status_display",
        "rollout_percentage",
        "staff_only",
        "allowed_orgs_count",
        "updated_at",
    ]
    list_filter = ["is_enabled", "staff_only"]
    search_fields = ["key", "description"]
    filter_horizontal = ["allowed_orgs"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["key"]

    fieldsets = (
        (
            "Flag",
            {
                "fields": ("key", "description"),
            },
        ),
        (
            "Control",
            {
                "fields": ("is_enabled", "rollout_percentage", "staff_only"),
            },
        ),
        (
            "Org Allowlist",
            {
                "fields": ("allowed_orgs",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @display(description="Status")
    def status_display(self, obj):
        if obj.is_enabled:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Enabled</span>'
            )
        return format_html('<span style="color: #999;">✗ Disabled</span>')

    @display(description="Allowed Orgs")
    def allowed_orgs_count(self, obj):
        count = obj.allowed_orgs.count()
        return f"{count} org(s)" if count else "—"


class PlatformConfigForm(admin.ModelAdmin):
    """Just for the widget override."""

    pass


@admin.register(PlatformConfig)
class PlatformConfigAdmin(UnfoldModelAdmin):
    list_display = ["key", "category", "value_preview", "description", "updated_at"]
    list_display_links = ["key"]
    list_filter = ["category"]
    search_fields = ["key", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["category", "key"]
    list_per_page = 50

    JSON_STYLE = (
        'font-family: "SF Mono", Monaco, "Cascadia Code", Consolas, monospace; '
        "font-size: 13px; line-height: 1.6; padding: 12px; border-radius: 8px; "
        "background-color: #f9fafb; color: #374151; border: 1px solid #e5e7eb; "
        "white-space: pre; overflow-x: auto; tab-size: 2; width: 100%; min-height: 120px;"
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["value"].widget = PrettyJSONWidget(
            attrs={"rows": 12, "style": self.JSON_STYLE}
        )
        return form

    fieldsets = (
        (
            None,
            {
                "fields": ("key", "category", "description"),
            },
        ),
        (
            "Value",
            {
                "fields": ("value",),
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

    @display(description="Value")
    def value_preview(self, obj):
        import json

        text = json.dumps(obj.value)
        if len(text) > 80:
            text = text[:77] + "..."
        return text
