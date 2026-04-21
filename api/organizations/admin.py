from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.admin import TabularInline as UnfoldTabularInline
from unfold.decorators import display
from django.urls import path, reverse
from django.utils.html import format_html

from common.admin_permissions import ReadOnlyAdminMixin
from organizations.models import Organization, OrganizationMember, OrganizationInvite

# ── Customer 360 URL registration ─────────────────────────────────────────────
from organizations.customer_360_admin import customer_360_view

_original_orgs_get_urls = admin.site.__class__.get_urls


def _patched_orgs_get_urls(self):
    urls = _original_orgs_get_urls(self)
    custom = [
        path(
            "organizations/<int:org_id>/360/",
            self.admin_view(customer_360_view),
            name="organization_customer_360",
        ),
    ]
    return custom + urls


admin.site.__class__.get_urls = _patched_orgs_get_urls
# ─────────────────────────────────────────────────────────────────────────────


class OrganizationMemberInline(UnfoldTabularInline):
    model = OrganizationMember
    extra = 0
    show_change_link = True
    fields = ["user", "role"]
    autocomplete_fields = ["user"]


class OrganizationInviteInline(UnfoldTabularInline):
    model = OrganizationInvite
    extra = 0
    show_change_link = True
    fields = [
        "code",
        "default_role",
        "max_uses",
        "use_count",
        "expires_at",
        "is_revoked",
    ]
    readonly_fields = ["code", "use_count"]


@admin.register(Organization)
class OrganizationAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "name",
        "owner",
        "industry",
        "member_count",
        "customer_360_link",
        "logo_thumbnail",
        "is_personal",
        "created_at",
    ]
    search_fields = ["name", "owner__email", "industry"]
    list_filter = ["is_personal", "industry", "created_at"]
    autocomplete_fields = ["owner"]
    ordering = ["-created_at"]
    list_per_page = 25
    date_hierarchy = "created_at"
    inlines = [OrganizationMemberInline, OrganizationInviteInline]

    fieldsets = (
        (
            "Organization",
            {
                "fields": ("name", "owner", "is_personal", "industry"),
            },
        ),
        (
            "Branding",
            {
                "classes": ["tab"],
                "fields": ("logo_url",),
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
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Members")
    def member_count(self, obj):
        count = obj.members.count()
        return format_html(
            '<span style="background-color:#007bff; color:#fff; padding:2px 8px; border-radius:10px;">{}</span>',
            count,
        )

    @admin.display(description="360 View")
    def customer_360_link(self, obj):
        url = reverse("admin:organization_customer_360", args=[obj.pk])
        return format_html(
            '<a href="{}" style="background:#2563eb;color:white;padding:2px 8px;border-radius:4px;font-size:11px;text-decoration:none;font-weight:500;">360°</a>',
            url,
        )

    @admin.display(description="Logo")
    def logo_thumbnail(self, obj):
        if obj.logo_url:
            return format_html(
                '<img src="{}" style="width:24px; height:24px; border-radius:4px; object-fit:cover;" />',
                obj.logo_url,
            )
        return "—"


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = ["user", "organization", "role_colored", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["user__email", "organization__name"]
    autocomplete_fields = ["user", "organization"]
    ordering = ["-created_at"]
    list_per_page = 25

    @display(
        description="Role",
        ordering="role",
        label={
            "owner": "danger",
            "admin": "warning",
            "member": "info",
            "viewer": "info",
        },
    )
    def role_colored(self, obj):
        return obj.role, obj.get_role_display()


@admin.register(OrganizationInvite)
class OrganizationInviteAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "code",
        "organization",
        "default_role",
        "usage_display",
        "is_revoked",
        "expires_at",
        "created_at",
    ]
    list_filter = ["is_revoked", "default_role", "created_at"]
    search_fields = ["code", "organization__name"]
    autocomplete_fields = ["organization"]
    ordering = ["-created_at"]
    list_per_page = 25

    @admin.display(description="Usage")
    def usage_display(self, obj):
        if obj.max_uses:
            return f"{obj.use_count}/{obj.max_uses}"
        return f"{obj.use_count}/∞"
