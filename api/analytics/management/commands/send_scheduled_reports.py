"""
Management command: send_scheduled_reports

Generates and emails weekly/monthly analytics reports to configured recipients.
Only sends reports that are due (based on frequency and last_sent_at).

Usage:
    python manage.py send_scheduled_reports
    python manage.py send_scheduled_reports --dry-run
    python manage.py send_scheduled_reports --force          # send even if not due
    python manage.py send_scheduled_reports --report-id 3   # send a specific report

Recommended: schedule weekly via cron or django-q.
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


def _build_earned_premium_html(filters: dict) -> str:
    from analytics.reports import get_earned_premium_report

    data = get_earned_premium_report(
        month=filters.get("month"),
        carrier=filters.get("carrier"),
        coverage_type=filters.get("coverage_type"),
    )
    rows_html = ""
    for row in data["rows"]:
        rows_html += (
            f"<tr>"
            f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;">{row["month"] or "-"}</td>'
            f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;">{row["coverage_type"] or "-"}</td>'
            f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;text-align:right;">${row["earned_amount"]:,.2f}</td>'
            f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;text-align:right;">${row["unearned_amount"]:,.2f}</td>'
            f"</tr>"
        )

    if not rows_html:
        rows_html = '<tr><td colspan="4" style="padding:12px;color:#6b7280;text-align:center;">No data for this period</td></tr>'

    return f"""
    <h2 style="color:#1d1d1d;margin-bottom:8px;">Earned Premium Report</h2>
    <p style="color:#6b7280;margin-bottom:16px;">
        Total Earned: <strong>${data["total_earned"]:,.2f}</strong> &nbsp;|&nbsp;
        Total Unearned: <strong>${data["total_unearned"]:,.2f}</strong>
    </p>
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
            <tr style="background:#f9fafb;">
                <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e5e7eb;">Month</th>
                <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e5e7eb;">Coverage</th>
                <th style="padding:8px 12px;text-align:right;border-bottom:2px solid #e5e7eb;">Earned</th>
                <th style="padding:8px 12px;text-align:right;border-bottom:2px solid #e5e7eb;">Unearned</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """


def _build_pipeline_html(filters: dict) -> str:
    from analytics.pipeline import get_pipeline_summary

    try:
        data = get_pipeline_summary()
    except Exception as e:
        return f'<p style="color:#ef4444;">Pipeline report error: {e}</p>'

    return f"""
    <h2 style="color:#1d1d1d;margin-bottom:8px;">Pipeline Report</h2>
    <p style="color:#6b7280;margin-bottom:16px;">Current quote and policy pipeline summary.</p>
    <pre style="background:#f9fafb;padding:16px;border-radius:8px;font-size:13px;overflow:auto;">{data}</pre>
    """


def _build_claims_summary_html(filters: dict) -> str:
    from django.db.models import Count, Q
    from claims.models import Claim

    qs = Claim.objects.all()
    summary = qs.aggregate(
        total=Count("id"),
        submitted=Count("id", filter=Q(status="submitted")),
        under_review=Count("id", filter=Q(status="under_review")),
        approved=Count("id", filter=Q(status="approved")),
        denied=Count("id", filter=Q(status="denied")),
        closed=Count("id", filter=Q(status="closed")),
    )

    rows_html = ""
    for status, label in [
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("denied", "Denied"),
        ("closed", "Closed"),
    ]:
        count = summary.get(status, 0)
        rows_html += (
            f"<tr>"
            f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;">{label}</td>'
            f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;text-align:right;">{count}</td>'
            f"</tr>"
        )

    return f"""
    <h2 style="color:#1d1d1d;margin-bottom:8px;">Claims Summary Report</h2>
    <p style="color:#6b7280;margin-bottom:16px;">Total claims: <strong>{summary["total"]}</strong></p>
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
            <tr style="background:#f9fafb;">
                <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e5e7eb;">Status</th>
                <th style="padding:8px 12px;text-align:right;border-bottom:2px solid #e5e7eb;">Count</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
    """


def _build_generic_html(report_type: str, filters: dict) -> str:
    return f'<p style="color:#6b7280;">Report type <strong>{report_type}</strong> — no generator implemented yet.</p>'


REPORT_BUILDERS = {
    "earned_premium": _build_earned_premium_html,
    "pipeline": _build_pipeline_html,
    "claims_summary": _build_claims_summary_html,
}


def generate_report_html(report) -> str:
    """Generate the full HTML email body for a ScheduledReport instance."""
    builder = REPORT_BUILDERS.get(report.report_type, _build_generic_html)
    content_html = builder(report.extra_filters or {})

    generated_at = timezone.now().strftime("%B %d, %Y at %H:%M UTC")

    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto;padding:20px;color:#1d1d1d;">
        <div style="border-bottom:3px solid #ff5c00;padding-bottom:16px;margin-bottom:24px;">
            <img src="https://corgi.insure/logo.png" alt="Corgi Insurance" height="32"
                 style="vertical-align:middle;margin-right:12px;" onerror="this.style.display='none'">
            <span style="font-size:20px;font-weight:bold;color:#ff5c00;">Corgi Insurance</span>
        </div>

        <h1 style="font-size:22px;margin-bottom:4px;">{report.name}</h1>
        <p style="color:#6b7280;margin-bottom:24px;font-size:13px;">
            {report.get_frequency_display()} report &middot; Generated {generated_at}
        </p>

        {content_html}

        <hr style="margin-top:32px;border:none;border-top:1px solid #e5e7eb;">
        <p style="color:#9ca3af;font-size:12px;margin-top:12px;">
            This is an automated report from Corgi Insurance.
            To manage your report subscriptions, contact your administrator.
        </p>
    </body>
    </html>
    """


class Command(BaseCommand):
    help = "Generate and email scheduled analytics reports to configured recipients"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print which reports would be sent without actually sending emails.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Send all active reports regardless of whether they are due.",
        )
        parser.add_argument(
            "--report-id",
            type=int,
            default=None,
            help="Send a specific report by ID (ignores due check unless --force is also set).",
        )

    def handle(self, *args, **options):
        from analytics.models import ScheduledReport
        from emails.service import EmailService
        from emails.schemas import SendEmailInput
        from django.conf import settings

        dry_run = options["dry_run"]
        force = options["force"]
        report_id = options["report_id"]

        qs = ScheduledReport.objects.filter(is_active=True)
        if report_id:
            qs = qs.filter(pk=report_id)

        if not qs.exists():
            self.stdout.write(self.style.WARNING("No active scheduled reports found."))
            return

        sent = 0
        skipped = 0
        errors = 0

        for report in qs:
            if not force and not report.is_due():
                self.stdout.write(
                    f"  SKIP  {report.name} — not due yet (last sent: {report.last_sent_at})"
                )
                skipped += 1
                continue

            recipients = report.recipients or []
            if not recipients:
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP  {report.name} — no recipients configured"
                    )
                )
                skipped += 1
                continue

            subject = f"[Corgi] {report.get_frequency_display()} {report.get_report_type_display()}"

            if dry_run:
                self.stdout.write(
                    f'  [DRY RUN] Would send "{report.name}" to {", ".join(recipients)}'
                )
                sent += 1
                continue

            try:
                html = generate_report_html(report)
                from_email = getattr(
                    settings, "DEFAULT_FROM_EMAIL", "reports@corgi.insure"
                )
                EmailService.send(
                    SendEmailInput(
                        to=recipients,
                        subject=subject,
                        html=html,
                        from_email=from_email,
                    )
                )
                report.last_sent_at = timezone.now()
                report.save(update_fields=["last_sent_at"])
                sent += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  SENT  {report.name} → {', '.join(recipients)}"
                    )
                )
            except Exception as e:
                errors += 1
                logger.error("Failed to send scheduled report %s: %s", report.pk, e)
                self.stdout.write(self.style.ERROR(f"  ERROR  {report.name}: {e}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {sent} sent, {skipped} skipped, {errors} errors."
            )
        )
