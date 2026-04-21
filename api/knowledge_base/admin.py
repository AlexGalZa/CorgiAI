"""
Django admin for the internal knowledge base.

Staff can create, edit, publish, and review articles via /admin/knowledge-base/.
Read-only view available at the same URL for non-admin staff (via custom view).
"""

from django.contrib import admin
from django.utils import timezone
from unfold.admin import ModelAdmin

from knowledge_base.models import KnowledgeArticle


@admin.register(KnowledgeArticle)
class KnowledgeArticleAdmin(ModelAdmin):
    list_display = [
        "title",
        "category",
        "author",
        "is_published",
        "view_count",
        "reading_time_display",
        "last_reviewed_at",
        "updated_at",
    ]
    list_filter = ["category", "is_published", "created_at"]
    search_fields = ["title", "content", "tags", "author__email"]
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ["view_count", "created_at", "updated_at", "reading_time_display"]
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = [
        (
            None,
            {
                "fields": ["title", "slug", "category", "author", "is_published"],
            },
        ),
        (
            "Content",
            {
                "fields": ["content", "tags"],
            },
        ),
        (
            "Review & Metrics",
            {
                "fields": [
                    "last_reviewed_at",
                    "last_reviewed_by",
                    "view_count",
                    "reading_time_display",
                    "created_at",
                    "updated_at",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    actions = ["publish_articles", "unpublish_articles", "mark_reviewed"]

    @admin.display(description="Reading Time")
    def reading_time_display(self, obj):
        if not obj.pk:
            return "—"
        return f"~{obj.reading_time_minutes} min"

    @admin.action(description="Publish selected articles")
    def publish_articles(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"{updated} article(s) published.")

    @admin.action(description="Unpublish selected articles")
    def unpublish_articles(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"{updated} article(s) unpublished.")

    @admin.action(description="Mark as reviewed today")
    def mark_reviewed(self, request, queryset):
        updated = queryset.update(
            last_reviewed_at=timezone.now(),
            last_reviewed_by=request.user,
        )
        self.message_user(request, f"{updated} article(s) marked as reviewed.")

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return (
            super().get_queryset(request).select_related("author", "last_reviewed_by")
        )
