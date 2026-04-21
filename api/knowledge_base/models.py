"""
Internal knowledge base models.

KnowledgeArticle: A markdown-formatted wiki article for internal staff.

Categories:
- product-knowledge: Product features, coverage details, quoting process
- underwriting-guidelines: Risk assessment, appetite, pricing guidance
- claim-procedures: How to handle, investigate, and settle claims
- sales-playbook: Sales scripts, objection handling, competitive analysis
"""

from django.db import models
from common.models import TimestampedModel


class KnowledgeArticle(TimestampedModel):
    CATEGORY_CHOICES = [
        ("product-knowledge", "Product Knowledge"),
        ("underwriting-guidelines", "Underwriting Guidelines"),
        ("claim-procedures", "Claim Procedures"),
        ("sales-playbook", "Sales Playbook"),
    ]

    title = models.CharField(
        max_length=255,
        verbose_name="Title",
        help_text="Article title",
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name="Slug",
        help_text="URL-friendly identifier (auto-generated from title if blank)",
        blank=True,
    )
    content = models.TextField(
        verbose_name="Content",
        help_text="Article body in Markdown format",
    )
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        db_index=True,
        verbose_name="Category",
    )
    author = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_articles",
        verbose_name="Author",
    )
    is_published = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Published",
        help_text="Only published articles are visible to staff",
    )
    tags = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Tags",
        help_text="Comma-separated tags for search and filtering",
    )
    view_count = models.PositiveIntegerField(
        default=0,
        verbose_name="View Count",
        help_text="Number of times this article has been viewed",
    )
    last_reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Reviewed At",
        help_text="When this article was last reviewed for accuracy",
    )
    last_reviewed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_articles",
        verbose_name="Last Reviewed By",
    )

    class Meta:
        db_table = "knowledge_articles"
        verbose_name = "Knowledge Article"
        verbose_name_plural = "Knowledge Articles"
        ordering = ["category", "title"]
        indexes = [
            models.Index(fields=["category", "is_published"]),
            models.Index(fields=["is_published", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while (
                KnowledgeArticle.objects.filter(slug=slug).exclude(pk=self.pk).exists()
            ):
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def tag_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def reading_time_minutes(self) -> int:
        """Estimate reading time based on 200 words/minute."""
        words = len(self.content.split())
        return max(1, round(words / 200))
