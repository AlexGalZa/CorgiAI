"""
Underwriting Workbench admin views.

Provides a dedicated Django admin view for reviewing quotes with
status='needs_review'. Features:
- Company info summary
- Coverage requested with amounts
- Risk assessment notes field (editable)
- Approve / Decline buttons with reason
- Link to company research (Google, LinkedIn, SEC, Crunchbase)

Registered as a custom admin URL under /admin/quotes/underwriting-workbench/
"""

import logging

from django import forms
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html

from quotes.models import Quote

logger = logging.getLogger(__name__)


class UnderwriterReviewForm(forms.Form):
    """Form for approving or declining a quote with notes and reason."""

    action = forms.ChoiceField(
        choices=[("approve", "Approve"), ("decline", "Decline")],
        widget=forms.HiddenInput(),
    )
    notes = forms.CharField(
        widget=forms.Textarea(
            attrs={"rows": 4, "style": "width: 100%; font-size: 13px;"}
        ),
        required=False,
        label="Risk Assessment Notes",
        help_text="Internal notes visible to underwriters only.",
    )
    decline_reason = forms.CharField(
        widget=forms.Textarea(
            attrs={"rows": 3, "style": "width: 100%; font-size: 13px;"}
        ),
        required=False,
        label="Decline Reason",
        help_text="Reason shown to the applicant when declining.",
    )
    effective_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        label="Effective Date (for approval)",
        help_text="Policy start date. Defaults to today.",
    )


def underwriting_workbench_list(request):
    """
    List view: show all quotes with status='needs_review'.
    """
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden

        return HttpResponseForbidden("Staff access required.")

    quotes = (
        Quote.objects.filter(status="needs_review")
        .select_related("company", "company__business_address", "user")
        .prefetch_related("policies")
        .order_by("-created_at")
    )

    context = {
        **admin.site.each_context(request),
        "title": "Underwriting Workbench",
        "quotes": quotes,
        "opts": {"app_label": "quotes", "model_name": "quote"},
    }
    return render(request, "admin/quotes/underwriting_workbench_list.html", context)


def underwriting_workbench_detail(request, quote_id):
    """
    Detail view: full underwriting review for a single quote.
    Handles approve/decline POST actions.
    """
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden

        return HttpResponseForbidden("Staff access required.")

    quote = get_object_or_404(
        Quote.objects.select_related(
            "company", "company__business_address", "user", "referral_partner"
        ).prefetch_related(
            "custom_products", "underwriter_overrides", "brokered_requests"
        ),
        pk=quote_id,
    )

    if request.method == "POST":
        form = UnderwriterReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]
            notes = form.cleaned_data.get("notes", "").strip()
            decline_reason = form.cleaned_data.get("decline_reason", "").strip()
            effective_date = form.cleaned_data.get("effective_date")

            if action == "approve":
                return _handle_approve(request, quote, notes, effective_date)
            elif action == "decline":
                return _handle_decline(request, quote, notes, decline_reason)
    else:
        form = UnderwriterReviewForm(
            initial={
                "notes": quote.underwriter_notes
                if hasattr(quote, "underwriter_notes")
                else "",
            }
        )

    # Build coverage display data
    coverages_data = _build_coverage_display(quote)

    # Build company research links
    company_name = quote.company.entity_legal_name if quote.company else ""
    research_links = _build_research_links(company_name)

    context = {
        **admin.site.each_context(request),
        "title": f"Underwriting Review — {quote.quote_number}",
        "quote": quote,
        "form": form,
        "coverages_data": coverages_data,
        "research_links": research_links,
        "opts": {"app_label": "quotes", "model_name": "quote"},
    }
    return render(request, "admin/quotes/underwriting_workbench_detail.html", context)


def _handle_approve(request, quote, notes: str, effective_date):
    """Approve a needs_review quote by generating a checkout link."""
    from datetime import date
    from quotes.service import QuoteService

    if not effective_date:
        effective_date = date.today()

    try:
        # Store notes on the quote
        if notes and hasattr(quote, "underwriter_notes"):
            quote.underwriter_notes = notes
            quote.save(update_fields=["underwriter_notes"])

        # Generate checkout URL
        checkout_url = QuoteService.create_checkout_url(
            quote_id=quote.pk,
            effective_date=effective_date,
        )

        messages.success(
            request,
            format_html(
                "Quote {} approved. Checkout link: <a href='{}' target='_blank'>{}</a>",
                quote.quote_number,
                checkout_url,
                checkout_url[:60] + "...",
            ),
        )
    except Exception as exc:
        logger.exception("Error approving quote %s: %s", quote.quote_number, exc)
        messages.error(request, f"Error approving quote: {exc}")

    return redirect("admin:underwriting_workbench_list")


def _handle_decline(request, quote, notes: str, decline_reason: str):
    """Decline a needs_review quote and send notification email."""
    from emails.schemas import SendEmailInput
    from emails.service import EmailService
    from django.conf import settings

    try:
        quote.status = "declined"
        quote.save(update_fields=["status"])

        # Send decline email to applicant
        user = quote.user
        company_name = (
            quote.company.entity_legal_name if quote.company else "your company"
        )
        if user and user.email:
            try:
                html = (
                    f"<p>Hi {user.first_name or 'there'},</p>"
                    f"<p>After reviewing your application for <strong>{company_name}</strong>, "
                    "we are unable to offer coverage at this time.</p>"
                )
                if decline_reason:
                    html += f"<p><strong>Reason:</strong> {decline_reason}</p>"
                html += (
                    "<p>If you have questions, please reply to this email or contact us at "
                    f"<a href='mailto:{settings.HELLO_CORGI_EMAIL}'>{settings.HELLO_CORGI_EMAIL}</a>.</p>"
                )
                EmailService.send(
                    SendEmailInput(
                        to=[user.email],
                        subject=f"Your application for {company_name} — coverage declined",
                        html=html,
                        from_email=settings.HELLO_CORGI_EMAIL,
                    )
                )
            except Exception as email_exc:
                logger.warning("Could not send decline email: %s", email_exc)

        messages.success(
            request,
            f"Quote {quote.quote_number} declined. Customer notified by email.",
        )
    except Exception as exc:
        logger.exception("Error declining quote %s: %s", quote.quote_number, exc)
        messages.error(request, f"Error declining quote: {exc}")

    return redirect("admin:underwriting_workbench_list")


def _build_coverage_display(quote: Quote) -> list[dict]:
    """Build a display-friendly list of requested coverages with amounts."""
    from common.constants import COVERAGE_DISPLAY_NAMES

    coverages = []
    rating_result = quote.rating_result or {}
    breakdown = rating_result.get("breakdown", {})

    for cov in quote.coverages or []:
        display_name = COVERAGE_DISPLAY_NAMES.get(cov, cov.replace("-", " ").title())
        rating = breakdown.get(cov, {})

        # Get limits from quote
        limits = {}
        if quote.limits_retentions:
            limits = quote.limits_retentions.get(cov, {})

        coverages.append(
            {
                "slug": cov,
                "display_name": display_name,
                "premium": rating.get("final_premium"),
                "per_occurrence_limit": limits.get("per_occurrence_limit"),
                "aggregate_limit": limits.get("aggregate_limit"),
                "retention": limits.get("retention"),
                "needs_review": (
                    cov in (quote.coverages or []) and quote.status == "needs_review"
                ),
            }
        )

    return coverages


def _build_research_links(company_name: str) -> list[dict]:
    """Build research URL links for a company name."""
    import urllib.parse

    encoded = urllib.parse.quote_plus(company_name)
    return [
        {
            "label": "🔍 Google",
            "url": f"https://www.google.com/search?q={encoded}+insurance",
        },
        {
            "label": "💼 LinkedIn",
            "url": f"https://www.linkedin.com/search/results/companies/?keywords={encoded}",
        },
        {
            "label": "📈 Crunchbase",
            "url": f"https://www.crunchbase.com/search/organizations/field/organizations/facet_ids/{encoded}",
        },
        {
            "label": "📊 SEC EDGAR",
            "url": f"https://efts.sec.gov/LATEST/search-index?q=%22{encoded}%22&dateRange=custom",
        },
        {
            "label": "⚖️ PACER",
            "url": "https://pcl.uscourts.gov/pcl/pages/search/find.jsf",
        },
    ]
