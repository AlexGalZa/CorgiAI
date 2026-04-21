from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display

from common.admin_permissions import is_corgi_admin
from products.models import ProductConfiguration


@admin.register(ProductConfiguration)
class ProductConfigurationAdmin(UnfoldModelAdmin):
    list_display = [
        "display_name",
        "coverage_type",
        "rating_tier",
        "min_limit",
        "max_limit",
        "active_badge",
        "requires_review",
        "updated_at",
    ]
    list_filter = ["is_active", "rating_tier", "requires_review"]
    search_fields = ["coverage_type", "display_name"]
    ordering = ["display_name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Product",
            {
                "fields": ("coverage_type", "display_name", "description", "is_active"),
            },
        ),
        (
            "Limits & Retentions",
            {
                "fields": ("min_limit", "max_limit", "available_retentions"),
                "description": "Adjust the available limits and retentions for this product.",
            },
        ),
        (
            "Rating",
            {
                "fields": ("rating_tier", "requires_review"),
            },
        ),
        (
            "Admin Notes",
            {
                "fields": ("admin_notes",),
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

    @display(description="Active", label=True)
    def active_badge(self, obj):
        if obj.is_active:
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
