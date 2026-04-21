"""
Management command: daily_change_report

Emails a daily summary of django-auditlog activity from the prior 24 hours,
grouped by (actor, model), including per-group count and first/last timestamps.

Recipients resolution order:
    1. DAILY_REPORT_RECIPIENTS env var (comma-separated)
    2. settings.DAILY_REPORT_RECIPIENTS (list/tuple or comma-separated str)
    3. Empty list -> no send, warning logged

Usage:
    python manage.py daily_change_report
    python manage.py daily_change_report --hours 48
    python manage.py daily_change_report --dry-run
    python manage.py daily_change_report --to sergio@corgi.insure

The command is idempotent and safe to re-run (it only reads LogEntry rows and
sends an email; it does not mutate audit-log state).
"""

import logging
import os
from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


# Map django-auditlog action ints to display names (fallback if an older/newer
# version lacks matching constants).
_ACTION_LABELS = {0: "create", 1: "update", 2: "delete", 3: "access"}


def _resolve_recipients(override=None):
    """Return the list of recipient emails, in priority order."""
    if override:
        return [e.strip() for e in override.split(",") if e.strip()]

    env_val = os.environ.get("DAILY_REPORT_RECIPIENTS", "")
    if env_val:
        return [e.strip() for e in env_val.split(",") if e.strip()]

    settings_val = getattr(settings, "DAILY_REPORT_RECIPIENTS", None)
    if not settings_val:
        return []
    if isinstance(settings_val, (list, tuple)):
        return [str(e).strip() for e in settings_val if str(e).strip()]
    # string fallback
    return [e.strip() for e in str(settings_val).split(",") if e.strip()]


def _actor_label(user):
    if user is None:
        return "system / anonymous"
    # Prefer email; fall back to username; then str(user)
    email = getattr(user, "email", None)
    if email:
        return email
    username = getattr(user, "username", None)
    if username:
        return username
    return str(user)


def _model_label(content_type):
    if content_type is None:
        return "unknown"
    app_label = getattr(content_type, "app_label", "") or ""
    model = getattr(content_type, "model", "") or "unknown"
    return f"{app_label}.{model}" if app_label else model


class Command(BaseCommand):
    help = "Email a daily summary of audit-log activity from the last 24 hours."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Lookback window in hours (default: 24).",
        )
        parser.add_argument(
            "--to",
            type=str,
            default=None,
            help="Override recipients (comma-separated). Bypasses env / settings.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Render the report and print a summary, but do not send email.",
        )

    def handle(self, *args, **options):
        from auditlog.models import LogEntry
        from emails.service import EmailService
        from emails.schemas import SendEmailInput

        hours = options["hours"]
        dry_run = options["dry_run"]
        override = options["to"]

        window_end = timezone.now()
        window_start = window_end - timezone.timedelta(hours=hours)

        self.stdout.write(
            self.style.NOTICE(
                f"Collecting audit-log entries from {window_start.isoformat()} "
                f"to {window_end.isoformat()} ({hours}h window)..."
            )
        )

        entries = (
            LogEntry.objects.filter(
                timestamp__gte=window_start, timestamp__lte=window_end
            )
            .select_related("actor", "content_type")
            .order_by("timestamp")
        )

        # Group in Python so actor __str__ / user email can be used cleanly.
        # Key: (actor_label, model_label)
        grouped = defaultdict(lambda: {"count": 0, "first_ts": None, "last_ts": None})
        actor_set = set()
        model_set = set()
        total_entries = 0

        for entry in entries.iterator():
            actor_label = _actor_label(entry.actor)
            model_label = _model_label(entry.content_type)
            key = (actor_label, model_label)
            bucket = grouped[key]
            bucket["count"] += 1
            ts = entry.timestamp
            if bucket["first_ts"] is None or ts < bucket["first_ts"]:
                bucket["first_ts"] = ts
            if bucket["last_ts"] is None or ts > bucket["last_ts"]:
                bucket["last_ts"] = ts
            actor_set.add(actor_label)
            model_set.add(model_label)
            total_entries += 1

        rows = [
            {
                "actor": actor,
                "model": model,
                "count": data["count"],
                "first_ts": data["first_ts"].strftime("%Y-%m-%d %H:%M:%S UTC")
                if data["first_ts"]
                else "",
                "last_ts": data["last_ts"].strftime("%Y-%m-%d %H:%M:%S UTC")
                if data["last_ts"]
                else "",
            }
            for (actor, model), data in grouped.items()
        ]
        rows.sort(key=lambda r: (-r["count"], r["actor"], r["model"]))

        context = {
            "window_start": window_start.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "window_end": window_end.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "total_entries": total_entries,
            "actor_count": len(actor_set),
            "model_count": len(model_set),
            "groups": rows,
        }

        html = render_to_string("emails/daily_change_report.html", context)

        self.stdout.write(
            f"  {total_entries} log entries across {len(actor_set)} actor(s) "
            f"and {len(model_set)} model(s); {len(rows)} group(s)."
        )

        recipients = _resolve_recipients(override)
        if not recipients:
            msg = "DAILY_REPORT_RECIPIENTS is not configured (env var and settings both empty). Skipping send."
            logger.warning(msg)
            self.stdout.write(self.style.WARNING(msg))
            return

        subject = (
            f"[Corgi] Daily Change Report "
            f"{window_start.strftime('%Y-%m-%d %H:%M')} -> "
            f"{window_end.strftime('%Y-%m-%d %H:%M')} UTC "
            f"({total_entries} entries)"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Would send to {', '.join(recipients)} (subject: {subject})"
                )
            )
            return

        from_email = getattr(
            settings,
            "HELLO_CORGI_EMAIL",
            getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@corgi.insure"),
        )

        try:
            EmailService.send(
                SendEmailInput(
                    to=recipients,
                    subject=subject,
                    html=html,
                    from_email=from_email,
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Daily change report sent to {', '.join(recipients)}."
                )
            )
        except Exception as exc:
            logger.error("Failed to send daily change report: %s", exc, exc_info=True)
            self.stdout.write(
                self.style.ERROR(f"Failed to send daily change report: {exc}")
            )
            raise
