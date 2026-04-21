"""
Management command: check_compliance_deadlines

Scans ComplianceDeadline records and sends alert emails for deadlines
approaching within the configured window (default: 30 days).

Usage:
    python manage.py check_compliance_deadlines
    python manage.py check_compliance_deadlines --days 14
    python manage.py check_compliance_deadlines --dry-run

Recommended: schedule daily via cron or django-q2.
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check upcoming compliance deadlines and send alert emails"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Alert window in days (default: 30). Deadlines within this many days will trigger an alert.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print which deadlines would trigger alerts without sending emails.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-send alerts even if one was already sent today.",
        )

    def handle(self, *args, **options):
        from common.models import ComplianceDeadline
        from emails.service import EmailService
        from emails.schemas import SendEmailInput
        from django.conf import settings

        advance_days = options["days"]
        dry_run = options["dry_run"]
        force = options["force"]
        today = timezone.now().date()
        alert_cutoff = today + timezone.timedelta(days=advance_days)

        self.stdout.write(
            self.style.NOTICE(
                f"Checking compliance deadlines due within {advance_days} days (by {alert_cutoff})..."
            )
        )

        # Find open/in_progress deadlines approaching within the window
        upcoming = ComplianceDeadline.objects.filter(
            status__in=["open", "in_progress"],
            deadline_date__lte=alert_cutoff,
        ).order_by("deadline_date")

        # Also find overdue deadlines not yet marked as such
        overdue = ComplianceDeadline.objects.filter(
            status__in=["open", "in_progress"],
            deadline_date__lt=today,
        )

        # Auto-mark overdue deadlines
        overdue_ids = list(overdue.values_list("id", flat=True))
        if overdue_ids and not dry_run:
            updated = ComplianceDeadline.objects.filter(id__in=overdue_ids).update(
                status="overdue"
            )
            if updated:
                self.stdout.write(
                    self.style.WARNING(f"  Marked {updated} deadline(s) as overdue.")
                )
            # Re-query with updated statuses
            upcoming = ComplianceDeadline.objects.filter(
                status__in=["open", "in_progress", "overdue"],
                deadline_date__lte=alert_cutoff,
            ).order_by("deadline_date")

        if not upcoming.exists():
            self.stdout.write(
                self.style.SUCCESS("No upcoming compliance deadlines found. All clear!")
            )
            return

        alerts_sent = 0
        alerts_skipped = 0

        for deadline in upcoming:
            days_left = (deadline.deadline_date - today).days
            is_overdue_flag = days_left < 0

            # Skip if alert already sent today (unless --force)
            if not force and deadline.alert_sent_at:
                last_alert_date = deadline.alert_sent_at.date()
                if last_alert_date >= today:
                    alerts_skipped += 1
                    continue

            urgency = "OVERDUE" if is_overdue_flag else f"Due in {days_left} day(s)"
            subject = f"[Compliance Alert] {urgency}: {deadline.title}"

            body_lines = [
                f'<h2 style="color:{"#dc2626" if is_overdue_flag else "#d97706"}">Compliance Alert: {urgency}</h2>',
                f"<p><strong>Deadline:</strong> {deadline.title}</p>",
                f"<p><strong>Type:</strong> {deadline.get_type_display()}</p>",
                f"<p><strong>Due Date:</strong> {deadline.deadline_date}</p>",
                f"<p><strong>Status:</strong> {deadline.get_status_display()}</p>",
                f"<p><strong>Responsible:</strong> {deadline.responsible_person}</p>",
            ]
            if deadline.description:
                body_lines.append(
                    f"<p><strong>Description:</strong><br>{deadline.description}</p>"
                )
            if deadline.notes:
                body_lines.append(f"<p><strong>Notes:</strong><br>{deadline.notes}</p>")

            body_lines.append(
                '<p style="margin-top:20px;color:#64748b;font-size:12px;">'
                "This is an automated alert from the Corgi compliance calendar."
                "</p>"
            )

            html_body = "\n".join(body_lines)

            # Determine recipients: the responsible person + compliance_alert_email from settings
            recipients = []
            if "@" in deadline.responsible_person:
                recipients.append(deadline.responsible_person)

            alert_email = getattr(settings, "COMPLIANCE_ALERT_EMAIL", None)
            if alert_email and alert_email not in recipients:
                recipients.append(alert_email)

            if not recipients:
                # Fallback: log to stdout, no email
                self.stdout.write(
                    self.style.WARNING(
                        f"  [{urgency}] {deadline.title} (no valid recipient — set COMPLIANCE_ALERT_EMAIL in settings)"
                    )
                )
                continue

            if dry_run:
                self.stdout.write(
                    f"  [DRY RUN] Would alert {', '.join(recipients)}: {subject}"
                )
                alerts_sent += 1
                continue

            try:
                EmailService.send(
                    SendEmailInput(
                        to=recipients,
                        subject=subject,
                        html=html_body,
                        from_email=getattr(
                            settings, "DEFAULT_FROM_EMAIL", "noreply@corgi.insure"
                        ),
                    )
                )
                deadline.alert_sent_at = timezone.now()
                deadline.save(update_fields=["alert_sent_at"])
                alerts_sent += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Alert sent to {', '.join(recipients)}: {deadline.title} ({urgency})"
                    )
                )
            except Exception as e:
                logger.error(
                    "Failed to send compliance alert for deadline %s: %s",
                    deadline.pk,
                    e,
                )
                self.stdout.write(
                    self.style.ERROR(f"  ERROR sending alert for {deadline.title}: {e}")
                )

        summary = f"Done. {alerts_sent} alert(s) sent, {alerts_skipped} already alerted today."
        self.stdout.write(self.style.SUCCESS(summary))
