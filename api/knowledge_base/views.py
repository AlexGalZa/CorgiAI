"""
Staff-facing read-only knowledge base view.

Available at /admin/knowledge-base/ for all authenticated staff.
Renders articles with markdown support using the admin layout.
"""

import markdown as _markdown
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from knowledge_base.models import KnowledgeArticle


@staff_member_required
def knowledge_base_index(request):
    """Knowledge base home — list articles by category."""
    from django.contrib import admin

    query = request.GET.get("q", "").strip()
    category_filter = request.GET.get("category", "").strip()

    articles_qs = KnowledgeArticle.objects.filter(is_published=True)

    if query:
        articles_qs = articles_qs.filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
            | Q(tags__icontains=query)
        )

    if category_filter:
        articles_qs = articles_qs.filter(category=category_filter)

    categories = {}
    for choice_value, choice_label in KnowledgeArticle.CATEGORY_CHOICES:
        cat_articles = articles_qs.filter(category=choice_value)
        if cat_articles.exists() or not (query or category_filter):
            categories[choice_value] = {
                "label": choice_label,
                "articles": cat_articles.order_by("title"),
            }

    context = {
        **admin.site.each_context(request),
        "title": "Knowledge Base",
        "categories": categories,
        "query": query,
        "category_filter": category_filter,
        "category_choices": KnowledgeArticle.CATEGORY_CHOICES,
        "total_articles": articles_qs.count(),
    }
    return TemplateResponse(request, "admin/knowledge_base/index.html", context)


@staff_member_required
def knowledge_base_article(request, slug):
    """Single article view with rendered markdown."""
    from django.contrib import admin

    article = get_object_or_404(KnowledgeArticle, slug=slug, is_published=True)

    # Increment view count
    KnowledgeArticle.objects.filter(pk=article.pk).update(
        view_count=article.view_count + 1
    )

    # Render markdown to HTML
    md = _markdown.Markdown(extensions=["tables", "fenced_code", "codehilite", "nl2br"])
    content_html = md.convert(article.content)

    # Related articles in same category
    related = (
        KnowledgeArticle.objects.filter(
            category=article.category,
            is_published=True,
        )
        .exclude(pk=article.pk)
        .order_by("?")[:5]
    )

    context = {
        **admin.site.each_context(request),
        "title": article.title,
        "article": article,
        "content_html": content_html,
        "related_articles": related,
    }
    return TemplateResponse(request, "admin/knowledge_base/article.html", context)
