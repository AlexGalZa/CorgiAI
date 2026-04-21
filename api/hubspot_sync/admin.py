from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display

from hubspot_sync.models import HubSpotSyncLog


@admin.register(HubSpotSyncLog)
class HubSpotSyncLogAdmin(UnfoldModelAdmin):
    list_display = [
        "created_at",
        "direction_badge",
        "object_type",
        "action",
        "success_icon",
        "django_model",
        "django_id",
        "hubspot_id",
        "error_short",
    ]
    list_filter = ["success", "direction", "object_type", "action", "created_at"]
    search_fields = ["hubspot_id", "django_model", "error_message"]
    readonly_fields = [
        "direction",
        "object_type",
        "hubspot_id",
        "django_model",
        "django_id",
        "action",
        "success",
        "error_message",
        "payload_summary",
        "created_at",
    ]
    ordering = ["-created_at"]
    list_per_page = 50
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Sync Details",
            {
                "fields": ("direction", "object_type", "action", "success"),
            },
        ),
        (
            "Objects",
            {
                "fields": ("django_model", "django_id", "hubspot_id"),
            },
        ),
        (
            "Payload",
            {
                "fields": ("payload_summary",),
            },
        ),
        (
            "Error",
            {
                "fields": ("error_message",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at",),
            },
        ),
    )

    @display(
        description="Direction",
        label={
            "push": "info",
            "pull": "warning",
        },
    )
    def direction_badge(self, obj):
        labels = {"push": "→ Push", "pull": "← Pull"}
        return obj.direction, labels.get(obj.direction, obj.direction)

    @display(description="Success", boolean=True)
    def success_icon(self, obj):
        return obj.success

    def error_short(self, obj):
        if not obj.error_message:
            return "—"
        return (
            obj.error_message[:60] + "..."
            if len(obj.error_message) > 60
            else obj.error_message
        )

    error_short.short_description = "Error"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
