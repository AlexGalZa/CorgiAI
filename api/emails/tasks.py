"""
Background tasks for the emails app.

Scheduling note: this module only *defines* tasks. Wiring a cron
schedule for ``prune_expired_email_contexts`` in settings.py is tracked
as a follow-up (H20 — the card explicitly defers scheduling).

Invoke manually via django-q::

    from django_q.tasks import async_task
    async_task('emails.tasks.prune_expired_email_contexts')
"""

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def prune_expired_email_contexts() -> dict:
    """Delete EmailContext rows whose ``expires_at`` is in the past.

    Intended to be scheduled every ~15 minutes so the 7h TTL is honored
    with bounded drift. Safe to run concurrently — deletion is idempotent.

    Returns:
        Summary dict with the number of rows deleted (``deleted``) and
        the cutoff timestamp used (``cutoff``). Suitable for logging.
    """
    from emails.models import EmailContext

    cutoff = timezone.now()
    qs = EmailContext.objects.filter(expires_at__lt=cutoff)
    deleted_count, _ = qs.delete()

    summary = {
        "deleted": deleted_count,
        "cutoff": cutoff.isoformat(),
    }
    logger.info("prune_expired_email_contexts complete: %s", summary)
    return summary
