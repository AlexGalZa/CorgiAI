"""
Email log model for the Corgi Insurance platform.

Tracks all outgoing emails for audit, compliance, and customer service purposes.
Every email sent via EmailService should create an EmailLog record.
"""

from datetime import timedelta

from django.db import models
from django.utils import timezone

from common.models import TimestampedModel


# TTL for an EmailContext record. After this window elapses, the
# `prune_expired_email_contexts` task deletes the row to comply with
# our short-retention inbound-thread context policy (H20).
EMAIL_CONTEXT_TTL = timedelta(hours=7)
# Cap on how many recent message snippets we retain on an EmailContext.
EMAIL_CONTEXT_MAX_MESSAGES = 5


class EmailLog(TimestampedModel):
    """
    Audit record for every outgoing email.

    Created automatically when EmailService.send() is called.
    Provides a searchable history of all communications per customer,
    policy, and quote.
    """

    recipient = models.EmailField(
        db_index=True,
        verbose_name="Recipient",
        help_text="Primary recipient email address",
    )
    subject = models.CharField(
        max_length=500,
        verbose_name="Subject",
    )
    body = models.TextField(
        verbose_name="Body (HTML)",
        help_text="Full HTML body of the email",
        blank=True,
    )
    sent_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Sent At",
    )
    sent_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_emails",
        verbose_name="Sent By",
        help_text="Staff user who triggered this email (null = system/automated)",
    )
    related_policy = models.ForeignKey(
        "policies.Policy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_logs",
        verbose_name="Related Policy",
    )
    related_quote = models.ForeignKey(
        "quotes.Quote",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_logs",
        verbose_name="Related Quote",
    )
    # Delivery metadata
    provider_message_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Provider Message ID",
        help_text="Message ID returned by the email provider (Resend)",
    )
    status = models.CharField(
        max_length=20,
        default="sent",
        choices=[
            ("sent", "Sent"),
            ("failed", "Failed"),
            ("dev_log", "Dev Log (not sent)"),
        ],
        db_index=True,
        verbose_name="Delivery Status",
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name="Error Message",
        help_text="Error details if delivery failed",
    )

    class Meta:
        db_table = "email_logs"
        verbose_name = "Email Log"
        verbose_name_plural = "Email Logs"
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["recipient", "sent_at"]),
            models.Index(fields=["related_policy", "sent_at"]),
            models.Index(fields=["related_quote", "sent_at"]),
        ]

    def __str__(self):
        return f"[{self.status}] {self.recipient} — {self.subject[:60]} ({self.sent_at:%Y-%m-%d %H:%M})"


class EmailContext(TimestampedModel):
    """
    Short-lived conversation context for an inbound email thread (H20).

    Created/updated when the Resend inbound-email webhook fires. Stores
    the last few message snippets so sales can quickly eyeball what the
    customer replied to. Rows self-expire 7 hours after creation — the
    ``prune_expired_email_contexts`` task deletes them on a schedule.

    Retention is intentionally tight: the record is an operational cache
    for a sales reply, not a permanent archive. The durable record of
    every outgoing email still lives in :class:`EmailLog`.
    """

    thread_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        verbose_name="Thread ID",
        help_text="Provider-supplied thread / conversation identifier",
    )
    policy = models.ForeignKey(
        "policies.Policy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_contexts",
        verbose_name="Related Policy",
    )
    salesperson = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_contexts",
        verbose_name="Salesperson",
        help_text="Staff user owning this thread (receives reply notifications)",
    )
    last_messages = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Last Messages",
        help_text=(
            "Rolling array of recent messages, capped at "
            f"{EMAIL_CONTEXT_MAX_MESSAGES}. "
            'Each element: {"from": str, "snippet": str, "received_at": iso8601}.'
        ),
    )
    expires_at = models.DateTimeField(
        db_index=True,
        verbose_name="Expires At",
        help_text="Row is pruned after this time (created_at + 7h).",
    )

    class Meta:
        db_table = "email_contexts"
        verbose_name = "Email Context"
        verbose_name_plural = "Email Contexts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["expires_at"]),
            models.Index(fields=["salesperson", "expires_at"]),
        ]

    def save(self, *args, **kwargs):
        # Compute expires_at from created_at (or "now" on first save) + TTL.
        base = self.created_at or timezone.now()
        self.expires_at = base + EMAIL_CONTEXT_TTL
        super().save(*args, **kwargs)

    def append_message(self, sender: str, snippet: str, received_at=None) -> None:
        """Append a message to ``last_messages``, trimming to the cap."""
        received = received_at or timezone.now()
        received_iso = (
            received.isoformat() if hasattr(received, "isoformat") else str(received)
        )
        entry = {
            "from": sender or "",
            "snippet": (snippet or "")[:500],
            "received_at": received_iso,
        }
        messages = list(self.last_messages or [])
        messages.append(entry)
        if len(messages) > EMAIL_CONTEXT_MAX_MESSAGES:
            messages = messages[-EMAIL_CONTEXT_MAX_MESSAGES:]
        self.last_messages = messages

    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at < timezone.now()

    def __str__(self):
        return f"EmailContext(thread={self.thread_id}, expires_at={self.expires_at:%Y-%m-%d %H:%M})"
