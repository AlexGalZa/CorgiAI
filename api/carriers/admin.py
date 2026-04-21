from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display

from carriers.models import Carrier
from common.admin_permissions import is_corgi_admin


@admin.register(Carrier)
class CarrierAdmin(UnfoldModelAdmin):
    list_display = [
        "name",
        "am_best_rating",
        "status_badge",
        "contact_name",
        "contact_email",
        "created_at",
    ]
    list_filter = ["status", "am_best_rating"]
    search_fields = ["name", "contact_name", "contact_email"]
    ordering = ["name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Carrier",
            {
                "fields": ("name", "am_best_rating", "status", "appetite_description"),
            },
        ),
        (
            "Commission Rates",
            {
                "fields": ("commission_rates",),
                "description": 'JSON mapping of coverage type slugs to commission rates (e.g. {"tech-eo": 0.15})',
            },
        ),
        (
            "Contact",
            {
                "fields": ("contact_name", "contact_email", "contact_phone"),
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

    @display(description="Status", label=True)
    def status_badge(self, obj):
        if obj.status == "active":
            return "success", "Active"
        return "danger", "Inactive"

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
