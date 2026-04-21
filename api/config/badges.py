"""
Badge callbacks for django-unfold sidebar navigation.

Each function returns a count string for display next to the nav item,
or an empty string if the count is zero (hides the badge).
"""


def pending_review_count(request):
    """Number of quotes awaiting underwriter review."""
    from quotes.models import Quote

    count = Quote.objects.filter(status="needs_review").count()
    return str(count) if count else ""


def open_claims_count(request):
    """Number of claims not yet closed or denied."""
    from claims.models import Claim

    count = Claim.objects.exclude(status__in=["closed", "denied"]).count()
    return str(count) if count else ""


def pending_brokered_count(request):
    """Number of brokered requests pending action."""
    from brokered.models import BrokeredQuoteRequest

    count = BrokeredQuoteRequest.objects.filter(status="pending").count()
    return str(count) if count else ""
