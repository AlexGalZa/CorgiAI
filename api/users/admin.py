import urllib.parse

from django import forms
from django.conf import settings
from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.admin import TabularInline as UnfoldTabularInline
from unfold.decorators import display
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.html import format_html, mark_safe

from auditlog.models import LogEntry

from common.admin_permissions import (
    ReadOnlyAdminMixin,
    is_corgi_admin,
    is_corgi_full_access,
)
from organizations.models import Organization
from s3.service import S3Service
from s3.schemas import UploadFileInput
from users.models import (
    User,
    UserDocument,
    ImpersonationLog,
    TOTPDevice,
    ActiveSession,
    LoginEvent,
)
from users.service import UserService


# ── Forms ────────────────────────────────────────────────────────────────


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return [single_file_clean(data, initial)]


class UploadDocumentForm(forms.Form):
    category = forms.ChoiceField(choices=UserDocument.CATEGORY_CHOICES)
    title = forms.CharField(
        max_length=255, help_text="Display title (e.g., 'Errors & Omissions')"
    )
    policy_numbers = forms.CharField(
        max_length=500, required=False, help_text="Comma-separated policy numbers"
    )
    effective_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    expiration_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    files = MultipleFileField(help_text="Select one or more files to upload")


class AddUserDocumentForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={"class": "admin-autocomplete"}),
    )
    category = forms.ChoiceField(choices=UserDocument.CATEGORY_CHOICES)
    title = forms.CharField(
        max_length=255, help_text="Display title (e.g., 'Errors & Omissions')"
    )
    policy_numbers = forms.CharField(
        max_length=500, required=False, help_text="Comma-separated policy numbers"
    )
    effective_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    expiration_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    file = forms.FileField(help_text="Select a file to upload")


class ReplaceDocumentForm(forms.Form):
    file = forms.FileField(help_text="Select a new file to replace the current one")


# ── Inlines ──────────────────────────────────────────────────────────────


class UserDocumentInline(UnfoldTabularInline):
    model = UserDocument
    extra = 0
    show_change_link = True
    readonly_fields = [
        "category",
        "title",
        "policy_numbers_display",
        "original_filename",
        "file_size_display",
        "s3_url",
        "created_at",
    ]
    fields = [
        "category",
        "title",
        "policy_numbers_display",
        "original_filename",
        "file_size_display",
        "created_at",
    ]
    can_delete = True

    def policy_numbers_display(self, obj):
        if obj.policy_numbers:
            return ", ".join(obj.policy_numbers)
        return "-"

    policy_numbers_display.short_description = "Policy Numbers"

    def file_size_display(self, obj):
        if obj.file_size is None:
            return "N/A"
        return f"{obj.file_size / 1024:.2f} KB"

    file_size_display.short_description = "File Size"


# ── UserAdmin ────────────────────────────────────────────────────────────


@admin.register(User)
class UserAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin, BaseUserAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "company_name",
        "document_count",
        "is_active_badge",
        "is_staff_badge",
        "impersonate_link",
    )
    list_filter = ("is_active", "is_staff", "created_at")
    search_fields = ("email", "first_name", "last_name", "company_name")
    ordering = ("-created_at",)
    list_per_page = 25
    date_hierarchy = "created_at"
    inlines = [UserDocumentInline]
    change_form_template = "admin/users/user/change_form.html"
    readonly_fields = (
        "notification_prefs_display",
        "last_login",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Account",
            {
                "classes": ["tab"],
                "fields": (
                    "email",
                    "password",
                    "first_name",
                    "last_name",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
        (
            "Profile",
            {
                "classes": ["tab"],
                "fields": ("phone_number", "company_name", "avatar_url", "timezone"),
            },
        ),
        (
            "Notifications",
            {
                "classes": ["tab"],
                "fields": ("notification_prefs_display",),
            },
        ),
        (
            "Permissions",
            {
                "classes": ["tab"],
                "fields": ("is_superuser", "groups", "user_permissions"),
            },
        ),
        (
            "Dates",
            {
                "classes": ["tab"],
                "fields": ("last_login", "created_at", "updated_at"),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        fieldsets = super().get_fieldsets(request, obj)
        if not is_corgi_admin(request.user):
            return [fs for fs in fieldsets if fs[0] != "Permissions"]
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if "created_at" not in base:
            base.append("created_at")
        if "updated_at" not in base:
            base.append("updated_at")
        if "notification_prefs_display" not in base:
            base.append("notification_prefs_display")
        return base

    def has_add_permission(self, request):
        if not is_corgi_admin(request.user):
            return False
        return super().has_add_permission(request)

    @display(description="Active", label=True)
    def is_active_badge(self, obj):
        if obj.is_active:
            return "active", "Active"
        return "inactive", "Inactive"

    @display(description="Staff", label=True)
    def is_staff_badge(self, obj):
        if obj.is_staff:
            return "staff", "Staff"
        return "user", "User"

    def document_count(self, obj):
        count = obj.documents.count()
        if count > 0:
            return format_html(
                '<span style="background-color: #007bff; color: white; padding: 2px 8px; border-radius: 10px;">{}</span>',
                count,
            )
        return count

    document_count.short_description = "Docs"

    def impersonate_link(self, obj):
        if obj.is_staff or obj.is_superuser:
            return format_html('<span style="color: #999;">N/A</span>')
        return format_html(
            '<a href="{}" class="button" style="padding: 3px 10px; background: #79aec8; color: white; border-radius: 4px; text-decoration: none; font-size: 11px;">Impersonate</a>',
            f"/admin/users/user/{obj.id}/impersonate/",
        )

    impersonate_link.short_description = "Action"

    @admin.display(description="Notification Preferences")
    def notification_prefs_display(self, obj):
        prefs = obj.notification_preferences
        if not prefs:
            return mark_safe('<em style="color:#6b7280">No preferences set</em>')
        rows = []
        for key, value in prefs.items():
            label = key.replace("_", " ").title()
            if isinstance(value, bool):
                icon = (
                    '<span style="color:#16a34a">✓ Enabled</span>'
                    if value
                    else '<span style="color:#6b7280">✗ Disabled</span>'
                )
            else:
                icon = str(value)
            rows.append(
                f'<tr style="border-top:1px solid #f3f4f6">'
                f'<td style="padding:8px 14px;font-size:13px;color:#6b7280;width:200px">{label}</td>'
                f'<td style="padding:8px 14px;font-size:13px;color:#374151">{icon}</td>'
                f"</tr>"
            )
        return mark_safe(
            '<table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;background:#fff">'
            "<tbody>" + "".join(rows) + "</tbody></table>"
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:user_id>/upload-documents/",
                self.admin_site.admin_view(self.upload_documents_view),
                name="users_user_upload_documents",
            ),
            path(
                "<int:user_id>/impersonate/",
                self.admin_site.admin_view(self.impersonate_user_view),
                name="users_user_impersonate",
            ),
        ]
        return custom_urls + urls

    def impersonate_user_view(self, request, user_id):
        if not is_corgi_full_access(request.user):
            messages.error(request, "You do not have permission to impersonate users.")
            return redirect("admin:users_user_changelist")

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found")
            return redirect("admin:users_user_changelist")

        if target_user.is_staff or target_user.is_superuser:
            messages.error(request, "Cannot impersonate staff or admin users")
            return redirect("admin:users_user_changelist")

        try:
            ip_address = request.META.get(
                "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")
            )
            if ip_address and "," in ip_address:
                ip_address = ip_address.split(",")[0].strip()

            user, tokens, _ = UserService.start_impersonation(
                admin_user=request.user,
                target_user_id=user_id,
                ip_address=ip_address,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

            params = urllib.parse.urlencode(
                {
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "impersonating": user.email,
                }
            )
            redirect_url = f"{settings.PORTAL_BASE_URL}/impersonate?{params}"

            LogEntry.objects.log_create(
                instance=user,
                action=LogEntry.Action.ACCESS,
                changes={"message": ["", "Impersonated user"]},
                actor=request.user,
            )
            messages.success(request, f"Impersonating {user.email}")
            return HttpResponseRedirect(redirect_url)

        except Exception as e:
            messages.error(request, f"Failed to impersonate: {str(e)}")
            return redirect("admin:users_user_changelist")

    def upload_documents_view(self, request, user_id):
        user = User.objects.get(id=user_id)

        if request.method == "POST":
            form = UploadDocumentForm(request.POST, request.FILES)
            if form.is_valid():
                category = form.cleaned_data["category"]
                title = form.cleaned_data["title"]
                policy_numbers_str = form.cleaned_data.get("policy_numbers", "")
                policy_numbers = (
                    [pn.strip() for pn in policy_numbers_str.split(",") if pn.strip()]
                    if policy_numbers_str
                    else []
                )
                effective_date = form.cleaned_data.get("effective_date")
                expiration_date = form.cleaned_data.get("expiration_date")
                files = form.cleaned_data["files"]

                success_count = 0
                for f in files:
                    path_prefix = f"users/{user.id}/documents/{category}"
                    result = S3Service.upload_file(
                        UploadFileInput(
                            file=f,
                            path_prefix=path_prefix,
                            original_filename=f.name,
                            content_type=getattr(
                                f, "content_type", "application/octet-stream"
                            ),
                        )
                    )

                    if result:
                        personal_org = Organization.objects.filter(
                            owner=user, is_personal=True
                        ).first()
                        UserDocument.objects.create(
                            user=user,
                            organization=personal_org,
                            category=category,
                            title=title,
                            policy_numbers=policy_numbers,
                            effective_date=effective_date,
                            expiration_date=expiration_date,
                            file_type=category,
                            original_filename=f.name,
                            file_size=f.size,
                            mime_type=getattr(f, "content_type", ""),
                            s3_key=result["s3_key"],
                            s3_url=result["s3_url"],
                        )
                        success_count += 1

                if success_count > 0:
                    LogEntry.objects.log_create(
                        instance=user,
                        action=LogEntry.Action.UPDATE,
                        changes={"message": ["", "Uploaded documents"]},
                        actor=request.user,
                    )
                    self.message_user(
                        request,
                        f"Successfully uploaded {success_count} document(s)",
                        messages.SUCCESS,
                    )
                else:
                    self.message_user(
                        request, "Failed to upload documents", messages.ERROR
                    )

                return redirect("admin:users_user_change", user_id)
        else:
            form = UploadDocumentForm()

        context = {
            "form": form,
            "user_obj": user,
            "opts": self.model._meta,
            "title": f"Upload Documents - {user.email}",
        }
        return render(request, "admin/users/user/upload_documents.html", context)


# ── UserDocument ─────────────────────────────────────────────────────────


@admin.register(UserDocument)
class UserDocumentAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "title",
        "user_email",
        "category_badge",
        "policy_numbers_display",
        "original_filename",
        "file_size_kb",
        "download_link",
        "created_at",
    ]
    search_fields = ["title", "user__email", "policy_numbers", "original_filename"]
    list_filter = ["category", "created_at"]
    readonly_fields = [
        "user",
        "file_type",
        "original_filename",
        "file_size",
        "mime_type",
        "s3_key",
        "s3_url",
        "download_button",
        "replace_button",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]
    list_per_page = 25
    date_hierarchy = "created_at"

    fieldsets = (
        ("Document Info", {"fields": ("user", "category", "title", "policy_numbers")}),
        (
            "Dates",
            {"classes": ["tab"], "fields": ("effective_date", "expiration_date")},
        ),
        (
            "File Details",
            {
                "classes": ["tab"],
                "fields": (
                    "file_type",
                    "original_filename",
                    "file_size",
                    "mime_type",
                    "s3_url",
                    "download_button",
                    "replace_button",
                ),
            },
        ),
        ("Timestamps", {"classes": ["tab"], "fields": ("created_at", "updated_at")}),
    )

    def policy_numbers_display(self, obj):
        if obj.policy_numbers:
            return ", ".join(obj.policy_numbers)
        return "-"

    policy_numbers_display.short_description = "Policy Numbers"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "add/",
                self.admin_site.admin_view(self.add_document_view),
                name="users_userdocument_add",
            ),
            path(
                "<int:document_id>/download/",
                self.admin_site.admin_view(self.download_document_view),
                name="users_userdocument_download",
            ),
            path(
                "<int:document_id>/replace/",
                self.admin_site.admin_view(self.replace_document_view),
                name="users_userdocument_replace",
            ),
        ]
        return custom_urls + urls

    def add_document_view(self, request):
        if request.method == "POST":
            form = AddUserDocumentForm(request.POST, request.FILES)
            if form.is_valid():
                user = form.cleaned_data["user"]
                category = form.cleaned_data["category"]
                title = form.cleaned_data["title"]
                policy_numbers_str = form.cleaned_data.get("policy_numbers", "")
                policy_numbers = (
                    [pn.strip() for pn in policy_numbers_str.split(",") if pn.strip()]
                    if policy_numbers_str
                    else []
                )
                effective_date = form.cleaned_data.get("effective_date")
                expiration_date = form.cleaned_data.get("expiration_date")
                f = form.cleaned_data["file"]

                path_prefix = f"users/{user.id}/documents/{category}"
                result = S3Service.upload_file(
                    UploadFileInput(
                        file=f,
                        path_prefix=path_prefix,
                        original_filename=f.name,
                        content_type=getattr(
                            f, "content_type", "application/octet-stream"
                        ),
                    )
                )

                if result:
                    personal_org = Organization.objects.filter(
                        owner=user, is_personal=True
                    ).first()
                    doc = UserDocument.objects.create(
                        user=user,
                        organization=personal_org,
                        category=category,
                        title=title,
                        policy_numbers=policy_numbers,
                        effective_date=effective_date,
                        expiration_date=expiration_date,
                        file_type=category,
                        original_filename=f.name,
                        file_size=f.size,
                        mime_type=getattr(f, "content_type", ""),
                        s3_key=result["s3_key"],
                        s3_url=result["s3_url"],
                    )
                    messages.success(
                        request, f"Successfully uploaded document: {title}"
                    )
                    return redirect("admin:users_userdocument_change", doc.id)
                else:
                    messages.error(request, "Failed to upload file to S3")
        else:
            form = AddUserDocumentForm()

        context = {
            "form": form,
            "opts": self.model._meta,
            "title": "Add User Document",
            "has_view_permission": True,
        }
        return render(request, "admin/users/userdocument/add_form.html", context)

    def download_document_view(self, request, document_id):
        document = UserDocument.objects.get(id=document_id)
        download_url = S3Service.generate_presigned_url(document.s3_key, expiration=60)
        if download_url:
            return redirect(download_url)
        messages.error(request, "Failed to generate download URL")
        return redirect("admin:users_userdocument_change", document_id)

    def replace_document_view(self, request, document_id):
        document = UserDocument.objects.get(id=document_id)

        if request.method == "POST":
            form = ReplaceDocumentForm(request.POST, request.FILES)
            if form.is_valid():
                f = form.cleaned_data["file"]
                old_s3_key = document.s3_key

                path_prefix = f"users/{document.user.id}/documents/{document.category}"
                result = S3Service.upload_file(
                    UploadFileInput(
                        file=f,
                        path_prefix=path_prefix,
                        original_filename=f.name,
                        content_type=getattr(
                            f, "content_type", "application/octet-stream"
                        ),
                    )
                )

                if result:
                    document.original_filename = f.name
                    document.file_size = f.size
                    document.mime_type = getattr(f, "content_type", "")
                    document.s3_key = result["s3_key"]
                    document.s3_url = result["s3_url"]
                    document.save()

                    if old_s3_key and old_s3_key != result["s3_key"]:
                        S3Service.delete_file(old_s3_key)

                    messages.success(
                        request, f"Successfully replaced file with: {f.name}"
                    )
                    return redirect("admin:users_userdocument_change", document_id)
                else:
                    messages.error(request, "Failed to upload new file to S3")
        else:
            form = ReplaceDocumentForm()

        context = {
            "form": form,
            "document": document,
            "opts": self.model._meta,
            "title": f"Replace File - {document.title}",
        }
        return render(request, "admin/users/userdocument/replace_form.html", context)

    def user_email(self, obj):
        from django.urls import reverse

        url = reverse("admin:users_user_change", args=[obj.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)

    user_email.short_description = "User"

    @display(
        description="Category",
        label={
            "policy": "info",
            "certificate": "success",
            "endorsement": "warning",
            "receipt": "info",
            "loss_run": "info",
        },
    )
    def category_badge(self, obj):
        return obj.category, obj.get_category_display()

    def file_size_kb(self, obj):
        if obj.file_size is None:
            return "N/A"
        return f"{obj.file_size / 1024:.2f} KB"

    file_size_kb.short_description = "File Size"

    def download_link(self, obj):
        url = f"/admin/users/userdocument/{obj.id}/download/"
        return format_html('<a href="{}" target="_blank">Download</a>', url)

    download_link.short_description = "Download"

    def download_button(self, obj):
        url = f"/admin/users/userdocument/{obj.id}/download/"
        return format_html(
            '<a href="{}" class="button" style="padding: 5px 15px; background: #417690; color: white; border-radius: 4px; text-decoration: none;">Download File</a>',
            url,
        )

    download_button.short_description = "Download"

    def replace_button(self, obj):
        url = f"/admin/users/userdocument/{obj.id}/replace/"
        return format_html(
            '<a href="{}" class="button" style="padding: 5px 15px; background: #dc6b2f; color: white; border-radius: 4px; text-decoration: none;">Replace File</a>',
            url,
        )

    replace_button.short_description = "Replace"


# ── ImpersonationLog ────────────────────────────────────────────────────


@admin.register(ImpersonationLog)
class ImpersonationLogAdmin(UnfoldModelAdmin):
    list_display = [
        "admin_email",
        "impersonated_email",
        "started_at",
        "ended_at",
        "duration",
        "ip_address",
    ]
    list_filter = ["started_at", "ended_at"]
    search_fields = ["admin_user__email", "impersonated_user__email", "ip_address"]
    readonly_fields = [
        "admin_user",
        "impersonated_user",
        "started_at",
        "ended_at",
        "ip_address",
        "user_agent",
        "created_at",
        "updated_at",
    ]
    ordering = ["-started_at"]
    list_per_page = 25

    def admin_email(self, obj):
        return obj.admin_user.email

    admin_email.short_description = "Admin"

    def impersonated_email(self, obj):
        return obj.impersonated_user.email

    impersonated_email.short_description = "Impersonated User"

    def duration(self, obj):
        if obj.ended_at:
            delta = obj.ended_at - obj.started_at
            minutes = int(delta.total_seconds() / 60)
            if minutes < 60:
                return f"{minutes} min"
            hours = minutes // 60
            remaining_mins = minutes % 60
            return f"{hours}h {remaining_mins}m"
        return format_html(
            '<span style="color: #28a745; font-weight: bold;">Active</span>'
        )

    duration.short_description = "Duration"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ── TOTP Devices (V3 #54) ──────────────────────────────────────────────────────


@admin.register(TOTPDevice)
class TOTPDeviceAdmin(UnfoldModelAdmin):
    list_display = ["user", "is_verified", "last_used_at", "created_at"]
    list_filter = ["is_verified"]
    search_fields = ["user__email"]
    readonly_fields = [
        "user",
        "secret_key",
        "is_verified",
        "last_used_at",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False


# ── Active Sessions (V3 #56) ───────────────────────────────────────────────────


@admin.register(ActiveSession)
class ActiveSessionAdmin(UnfoldModelAdmin):
    list_display = [
        "user",
        "session_key_short",
        "ip_address",
        "last_activity",
        "is_active",
    ]
    list_filter = ["is_active"]
    search_fields = ["user__email", "ip_address"]
    readonly_fields = [
        "user",
        "session_key",
        "ip_address",
        "user_agent",
        "created_at",
        "last_activity",
        "is_active",
        "revoked_at",
    ]
    ordering = ["-last_activity"]

    def session_key_short(self, obj):
        return obj.session_key[:12] + "..."

    session_key_short.short_description = "Session Key"

    def has_add_permission(self, request):
        return False


# ── Login Events ─────────────────────────────────────────────────────────────


@admin.register(LoginEvent)
class LoginEventAdmin(UnfoldModelAdmin):
    list_display = [
        "email",
        "method",
        "success_icon",
        "ip_address",
        "user_agent_short",
        "failure_reason",
        "created_at",
    ]
    list_filter = ["success", "method", "created_at"]
    search_fields = ["email", "ip_address", "user_agent"]
    readonly_fields = [
        "user",
        "email",
        "method",
        "success",
        "ip_address",
        "user_agent",
        "failure_reason",
        "country",
        "created_at",
    ]
    ordering = ["-created_at"]
    list_per_page = 50
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Login Attempt",
            {
                "fields": ("user", "email", "method", "success", "failure_reason"),
            },
        ),
        (
            "Client Info",
            {
                "fields": ("ip_address", "user_agent", "country"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at",),
            },
        ),
    )

    @display(description="Success", boolean=True)
    def success_icon(self, obj):
        return obj.success

    def user_agent_short(self, obj):
        ua = obj.user_agent or ""
        return ua[:80] + "..." if len(ua) > 80 else ua

    user_agent_short.short_description = "User Agent"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return is_corgi_admin(request.user)
