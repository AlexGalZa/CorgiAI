"""
Management command to send policy renewal reminder emails.

Finds active policies expiring in 60, 30, and 7 days and sends
appropriately-toned reminders. Uses the Notification model to
track which reminders have already been sent (avoiding duplicates).

Usage:
    python manage.py send_renewal_reminders
    python manage.py send_renewal_reminders --dry-run
    python manage.py send_renewal_reminders --days 30
"""

import logging
from datetime import date, timedelta

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from common.models import Notification
from emails.schemas import SendEmailInput
from emails.service import EmailService
from policies.models import Policy

logger = logging.getLogger(__name__)

# Reminder tiers: (days_before_expiry, notification_tag, subject, urgency_label)
REMINDER_TIERS = [
    (
        60,
        "renewal_reminder_60d",
        "Your {coverage} policy expires in 60 days",
        "gentle",
    ),
    (
        30,
        "renewal_reminder_30d",
        "Action needed — your {coverage} policy expires in 30 days",
        "urgent",
    ),
    (
        7,
        "renewal_reminder_7d",
        "Final warning — your {coverage} policy expires in 7 days",
        "final",
    ),
]


class Command(BaseCommand):
    help = "Send renewal reminder emails for policies expiring in 60, 30, and 7 days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be sent without actually sending emails.",
        )
        parser.add_argument(
            "--days",
            type=int,
            choices=[60, 30, 7],
            help="Only process a single tier (60, 30, or 7).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        only_days = options.get("days")
        today = date.today()
        policy_ct = ContentType.objects.get_for_model(Policy)

        tiers = REMINDER_TIERS
        if only_days:
            tiers = [t for t in REMINDER_TIERS if t[0] == only_days]

        total_sent = 0

        for days_before, tag, subject_tpl, urgency in tiers:
            target_date = today + timedelta(days=days_before)

            policies = Policy.objects.filter(
                status="active",
                expiration_date=target_date,
            ).select_related("quote__user", "quote__company")

            self.stdout.write(
                f"\n[{tag}] Checking policies expiring on {target_date} "
                f"({days_before} days out): {policies.count()} found"
            )

            for policy in policies:
                # Check if reminder already sent
                already_sent = Notification.objects.filter(
                    related_content_type=policy_ct,
                    related_object_id=policy.pk,
                    title=tag,
                ).exists()

                if already_sent:
                    self.stdout.write(
                        f"  SKIP {policy.policy_number} — {tag} already sent"
                    )
                    continue

                user = getattr(policy.quote, "user", None)
                if not user or not user.email:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  SKIP {policy.policy_number} — no user/email on quote"
                        )
                    )
                    continue

                coverage_display = (
                    policy.coverage_type.replace("-", " ").title()
                    if policy.coverage_type
                    else "Insurance"
                )
                subject = subject_tpl.format(coverage=coverage_display)

                html = render_to_string(
                    "emails/policy_expiring.html",
                    {
                        "first_name": user.first_name or "there",
                        "coverage_type": coverage_display,
                        "policy_number": policy.policy_number,
                        "expiration_date": policy.expiration_date.strftime("%B %d, %Y"),
                        "portal_url": settings.FRONTEND_URL,
                    },
                )

                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(f"  DRY-RUN → {user.email} | {subject}")
                    )
                    total_sent += 1
                    continue

                # Send email
                try:
                    EmailService.send(
                        SendEmailInput(
                            to=[user.email],
                            subject=subject,
                            html=html,
                            from_email=settings.HELLO_CORGI_EMAIL,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Failed to send %s email for policy %s to %s",
                        tag,
                        policy.policy_number,
                        user.email,
                    )
                    self.stdout.write(
                        self.style.ERROR(
                            f"  FAIL {policy.policy_number} → {user.email}"
                        )
                    )
                    continue

                # Record notification to prevent duplicates
                urgency_messages = {
                    "gentle": (
                        f"Your {coverage_display} policy ({policy.policy_number}) "
                        f"expires on {policy.expiration_date.strftime('%B %d, %Y')}. "
                        "Consider renewing soon."
                    ),
                    "urgent": (
                        f"Your {coverage_display} policy ({policy.policy_number}) "
                        f"expires in 30 days. Renew now to avoid a coverage gap."
                    ),
                    "final": (
                        f"Final warning: your {coverage_display} policy ({policy.policy_number}) expires in 7 days!"
                    ),
                }

                Notification.objects.create(
                    user=user,
                    notification_type="policy_update",
                    title=tag,
                    message=urgency_messages.get(urgency, subject),
                    action_url=f"/policies/{policy.pk}",
                    related_content_type=policy_ct,
                    related_object_id=policy.pk,
                )

                logger.info(
                    "Sent %s email for policy %s to %s",
                    tag,
                    policy.policy_number,
                    user.email,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"  SENT {policy.policy_number} → {user.email}")
                )
                total_sent += 1

        action = "Would send" if dry_run else "Sent"
        self.stdout.write(
            self.style.SUCCESS(f"\nDone. {action} {total_sent} reminder(s).")
        )
