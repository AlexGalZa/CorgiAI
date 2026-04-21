"""
Django admin registration for Document Management.

Provides:
- DocumentFolder admin with nested folder display
- DocumentFolderItem inline
- Search across documents by org/title/folder
"""

from django.contrib import admin
from django.db.models import Count
from unfold.admin import ModelAdmin, StackedInline

from document_management.models import DocumentFolder, DocumentFolderItem


class DocumentFolderItemInline(StackedInline):
    model = DocumentFolderItem
    extra = 0
    autocomplete_fields = ["document"]
    readonly_fields = ["added_by", "created_at"]
    fields = ["document", "added_by", "created_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("document", "added_by")


@admin.register(DocumentFolder)
class DocumentFolderAdmin(ModelAdmin):
    list_display = [
        "name",
        "organization",
        "parent",
        "document_count",
        "depth_display",
        "created_by",
        "created_at",
    ]
    list_filter = ["organization", "created_at"]
    search_fields = ["name", "organization__name", "description"]
    autocomplete_fields = ["organization", "parent", "created_by"]
    readonly_fields = ["created_at", "updated_at", "full_path_display"]
    inlines = [DocumentFolderItemInline]

    fieldsets = [
        (
            None,
            {
                "fields": ["organization", "name", "parent", "description", "color"],
            },
        ),
        (
            "Metadata",
            {
                "fields": [
                    "full_path_display",
                    "created_by",
                    "created_at",
                    "updated_at",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("organization", "parent", "created_by")
            .annotate(_doc_count=Count("items"))
        )

    @admin.display(description="Documents", ordering="_doc_count")
    def document_count(self, obj):
        return obj._doc_count

    @admin.display(description="Depth")
    def depth_display(self, obj):
        depth = obj.depth
        return "—" * depth + f" L{depth}" if depth else "Root"

    @admin.display(description="Full Path")
    def full_path_display(self, obj):
        return obj.full_path if obj.pk else "—"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DocumentFolderItem)
class DocumentFolderItemAdmin(ModelAdmin):
    list_display = ["document", "folder", "added_by", "created_at"]
    list_filter = ["folder__organization", "created_at"]
    search_fields = ["document__title", "folder__name", "folder__organization__name"]
    autocomplete_fields = ["folder", "document", "added_by"]
    readonly_fields = ["created_at"]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.added_by = request.user
        super().save_model(request, obj, form, change)
