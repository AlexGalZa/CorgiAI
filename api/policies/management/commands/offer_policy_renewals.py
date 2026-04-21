"""
Management command to mark policies expiring within 60 days as renewal-offered.

Finds active policies with expiration_date within the next N days (default 60)
that have not yet had a renewal offer and:
  1. Sets policy.renewal_status = 'offered'
  2. Creates a PolicyRenewal record (status=pending)
  3. Optionally sends a notification (if --notify flag is set)

Usage:
    python manage.py offer_policy_renewals
    python manage.py offer_policy_renewals --days 90
    python manage.py offer_policy_renewals --dry-run
    python manage.py offer_policy_renewals --notify
"""

import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from policies.models import Policy, PolicyRenewal

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Mark policies expiring within 60 days as renewal-offered and create PolicyRenewal records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=60,
            help="Number of days before expiration to trigger renewal offer (default: 60).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would happen without making changes.",
        )
        parser.add_argument(
            "--notify",
            action="store_true",
            help="Also send renewal offer emails to customers.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        days = options["days"]
        do_notify = options["notify"]
        today = date.today()
        cutoff = today + timedelta(days=days)

        # Find active policies expiring within the window that haven't been offered yet
        policies = Policy.objects.filter(
            status="active",
            expiration_date__gt=today,
            expiration_date__lte=cutoff,
            renewal_status="not_due",
        ).select_related("quote__user", "quote__company")

        self.stdout.write(
            f"\nChecking policies expiring between {today} and {cutoff}: {policies.count()} found"
        )

        total_offered = 0
        total_skipped = 0

        for policy in policies:
            # Double-check no renewal record already exists
            already_has_renewal = PolicyRenewal.objects.filter(
                policy=policy,
                status__in=["pending", "accepted"],
            ).exists()

            if already_has_renewal:
                self.stdout.write(
                    f"  SKIP {policy.policy_number} — renewal already exists"
                )
                total_skipped += 1
                continue

            days_left = (policy.expiration_date - today).days
            user = getattr(policy.quote, "user", None)

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  DRY-RUN → {policy.policy_number} | "
                        f"{policy.coverage_type} | expires in {days_left}d | "
                        f"user: {user.email if user else 'unknown'}"
                    )
                )
                total_offered += 1
                continue

            # Update policy renewal status
            policy.renewal_status = "offered"
            policy.save(
                update_fields=["renewal_status", "updated_at"], skip_validation=True
            )

            # Create PolicyRenewal record
            renewal = PolicyRenewal.objects.create(
                policy=policy,
                status="pending",
                offered_at=timezone.now(),
                expires_at=timezone.now() + timedelta(days=days),
                notes=f"Auto-generated renewal offer. Policy expires {policy.expiration_date}.",
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  OFFERED {policy.policy_number} | "
                    f"{policy.coverage_type} | expires in {days_left}d | "
                    f"renewal_id={renewal.pk}"
                )
            )

            if do_notify and user and user.email:
                try:
                    self._send_renewal_offer_email(policy, user, days_left)
                    self.stdout.write(f"    ✉ Renewal offer email sent to {user.email}")
                except Exception:
                    logger.exception(
                        "Failed to send renewal offer email for policy %s",
                        policy.policy_number,
                    )
                    self.stdout.write(
                        self.style.WARNING(
                            f"    ✗ Failed to send email to {user.email}"
                        )
                    )

            logger.info(
                "Renewal offered for policy %s (expires %s)",
                policy.policy_number,
                policy.expiration_date,
            )
            total_offered += 1

        action = "Would offer" if dry_run else "Offered"
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {action} {total_offered} renewal(s). Skipped {total_skipped} (already offered)."
            )
        )

    def _send_renewal_offer_email(self, policy, user, days_left: int):
        """Send a renewal offer email to the policyholder."""
        from django.conf import settings
        from django.template.loader import render_to_string
        from emails.schemas import SendEmailInput
        from emails.service import EmailService

        coverage_display = (
            policy.coverage_type.replace("-", " ").title()
            if policy.coverage_type
            else "Insurance"
        )

        html = render_to_string(
            "emails/renewal_offer.html",
            {
                "first_name": user.first_name or "there",
                "coverage_type": coverage_display,
                "policy_number": policy.policy_number,
                "expiration_date": policy.expiration_date.strftime("%B %d, %Y"),
                "days_left": days_left,
                "portal_url": settings.FRONTEND_URL,
                "renewal_url": f"{settings.FRONTEND_URL}/policies/renew",
            },
        )

        EmailService.send(
            SendEmailInput(
                to=[user.email],
                subject=f"Renew your {coverage_display} policy before it expires",
                html=html,
                from_email=settings.HELLO_CORGI_EMAIL,
            )
        )
