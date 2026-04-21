from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display
from django.contrib import messages
from django.contrib.admin.widgets import AutocompleteSelect
from django.urls import path, reverse
from django.shortcuts import redirect, render
from django import forms

from api_keys.models import ApiKey, ApiKeyInvite
from api_keys.service import ApiKeyService
from organizations.models import Organization


class ApiKeyCreateForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        label="Key Name",
        help_text='Descriptive label, e.g. "Agency X production"',
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all().order_by("name"),
        label="Organization",
        required=False,
        widget=AutocompleteSelect(
            ApiKey._meta.get_field("organization"),
            admin.site,
        ),
    )


@admin.register(ApiKey)
class ApiKeyAdmin(UnfoldModelAdmin):
    list_display = [
        "name",
        "prefix",
        "organization",
        "is_active_badge",
        "last_used_at",
        "created_at",
    ]
    list_filter = ["is_active", "organization"]
    search_fields = ["name", "prefix", "organization__name"]
    readonly_fields = [
        "prefix",
        "key_hash",
        "last_used_at",
        "created_at",
        "updated_at",
        "created_by",
    ]
    ordering = ["-created_at"]
    list_per_page = 25
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "API Key",
            {
                "fields": ("name", "organization", "is_active"),
            },
        ),
        (
            "Key Details",
            {
                "classes": ["tab"],
                "fields": ("prefix", "key_hash", "last_used_at"),
            },
        ),
        (
            "Meta",
            {
                "classes": ["tab"],
                "fields": ("created_by", "created_at", "updated_at"),
            },
        ),
    )

    @display(description="Active", label=True)
    def is_active_badge(self, obj):
        if obj.is_active:
            return "active", "Active"
        return "inactive", "Inactive"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "create-key/",
                self.admin_site.admin_view(self.create_key_view),
                name="api_keys_apikey_create",
            ),
        ]
        return custom + urls

    def create_key_view(self, request):
        if request.method == "POST":
            form = ApiKeyCreateForm(request.POST)
            if form.is_valid():
                api_key, raw = ApiKeyService.create_key(
                    name=form.cleaned_data["name"],
                    organization=form.cleaned_data.get("organization"),
                    created_by=request.user,
                )
                self.message_user(
                    request,
                    f"API key created. Copy it now — it will NOT be shown again: {raw}",
                    level=messages.WARNING,
                )
                return redirect(
                    reverse("admin:api_keys_apikey_change", args=[api_key.pk])
                )
        else:
            form = ApiKeyCreateForm()

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "title": "Create API Key",
            "opts": self.model._meta,
        }
        return render(request, "admin/api_keys/create_key.html", context)

    def add_view(self, request, form_url="", extra_context=None):
        return redirect(reverse("admin:api_keys_apikey_create"))


@admin.register(ApiKeyInvite)
class ApiKeyInviteAdmin(UnfoldModelAdmin):
    list_display = [
        "token_preview",
        "is_used_badge",
        "partner_org_name",
        "partner_email",
        "expires_at",
        "used_at",
        "created_at",
    ]
    list_filter = ["is_used"]
    search_fields = ["partner_email", "partner_org_name"]
    readonly_fields = [
        "token",
        "is_used",
        "used_at",
        "partner_first_name",
        "partner_last_name",
        "partner_org_name",
        "partner_email",
        "api_key",
        "created_by",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]
    list_per_page = 25

    fieldsets = (
        (
            "Invite",
            {
                "fields": ("token", "expires_at"),
            },
        ),
        (
            "Status",
            {
                "classes": ["tab"],
                "fields": ("is_used", "used_at"),
            },
        ),
        (
            "Partner Info",
            {
                "classes": ["tab"],
                "fields": (
                    "partner_first_name",
                    "partner_last_name",
                    "partner_org_name",
                    "partner_email",
                ),
            },
        ),
        (
            "Result",
            {
                "classes": ["tab"],
                "fields": ("api_key",),
            },
        ),
        (
            "Meta",
            {
                "classes": ["tab"],
                "fields": ("created_by", "created_at", "updated_at"),
            },
        ),
    )

    def token_preview(self, obj):
        return f"{obj.token[:16]}…"

    token_preview.short_description = "Token"

    @display(description="Used", label=True)
    def is_used_badge(self, obj):
        if obj.is_used:
            return "used", "Used"
        return "available", "Available"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "create-invite/",
                self.admin_site.admin_view(self.create_invite_view),
                name="api_keys_apikeyinvite_create",
            ),
        ]
        return custom + urls

    def create_invite_view(self, request):
        if request.method == "POST":
            invite, token = ApiKeyService.create_invite(created_by=request.user)
            self.message_user(
                request,
                f"Invite created. Share this token — it will NOT be shown again: {token}",
                level=messages.WARNING,
            )
            return redirect(
                reverse("admin:api_keys_apikeyinvite_change", args=[invite.pk])
            )

        context = {
            **self.admin_site.each_context(request),
            "title": "Create API Key Invite",
            "opts": self.model._meta,
        }
        return render(request, "admin/api_keys/create_invite.html", context)

    def add_view(self, request, form_url="", extra_context=None):
        return redirect(reverse("admin:api_keys_apikeyinvite_create"))
