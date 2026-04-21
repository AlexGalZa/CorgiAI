"""
Management command to process the Stripe dunning sequence.

Dunning schedule (from the date of first payment failure):
- Day 1: First retry attempt
- Day 3: Second retry attempt
- Day 7: Final retry attempt → if still fails, auto-cancel the policy

Usage:
    python manage.py process_dunning
    python manage.py process_dunning --dry-run

Recommended cron: Run every hour (or at minimum once daily).
    0 * * * * python manage.py process_dunning
"""

import logging

import stripe
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from stripe_integration.models import DunningRecord

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3  # After 3 retries (day 1, 3, 7), cancel the policy


class Command(BaseCommand):
    help = "Process Stripe dunning: retry failed payments at day 1, 3, and 7. Auto-cancel policy after day 7 failure."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would happen without making Stripe calls or DB changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY-RUN mode — no changes will be made.\n")
            )

        # Find all active dunning records where next_retry_at is due
        due_records = DunningRecord.objects.filter(
            status="active",
            next_retry_at__lte=now,
        ).select_related("policy", "policy__quote", "policy__quote__user")

        self.stdout.write(
            f"Found {due_records.count()} dunning record(s) due for processing."
        )

        processed = 0
        retried = 0
        cancelled = 0
        resolved = 0
        errors = 0

        for record in due_records:
            policy = record.policy
            self.stdout.write(
                f"\n[{record.pk}] Policy {policy.policy_number} — "
                f"attempt {record.attempt_count} / {MAX_ATTEMPTS} | "
                f"invoice: {record.stripe_invoice_id or 'N/A'}"
            )

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  DRY-RUN → would retry invoice {record.stripe_invoice_id}"
                    )
                )
                processed += 1
                continue

            try:
                # Attempt to retry the Stripe invoice payment
                success = self._retry_stripe_payment(record)

                if success:
                    self._mark_resolved(record)
                    resolved += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ Payment recovered for {policy.policy_number}"
                        )
                    )
                else:
                    # Payment still failing
                    if record.attempt_count >= MAX_ATTEMPTS:
                        # Final attempt failed — cancel the policy
                        self._cancel_policy_for_non_payment(record)
                        cancelled += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"  ❌ Max retries reached — policy {policy.policy_number} CANCELLED"
                            )
                        )
                    else:
                        # Schedule the next retry
                        record.attempt_count += 1
                        record.last_attempt_at = now
                        record.schedule_next_retry()
                        record.save(
                            update_fields=[
                                "attempt_count",
                                "last_attempt_at",
                                "next_retry_at",
                            ]
                        )
                        retried += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠️  Still failing — scheduled retry {record.attempt_count} at {record.next_retry_at}"
                            )
                        )

                processed += 1

            except Exception as exc:
                errors += 1
                logger.exception(
                    "Error processing dunning record %s for policy %s",
                    record.pk,
                    policy.policy_number,
                )
                self.stdout.write(self.style.ERROR(f"  ERROR: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Processed={processed} | Resolved={resolved} | "
                f"Retried={retried} | Cancelled={cancelled} | Errors={errors}"
            )
        )

    def _retry_stripe_payment(self, record: DunningRecord) -> bool:
        """
        Attempt to pay the Stripe invoice.

        Returns True if the payment succeeded, False if still failing.
        """
        if not record.stripe_invoice_id:
            logger.warning(
                "DunningRecord %s has no stripe_invoice_id — skipping Stripe retry",
                record.pk,
            )
            return False

        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            invoice = stripe.Invoice.pay(record.stripe_invoice_id, forgive=True)

            if invoice.status == "paid":
                return True

            # Update failure reason from latest attempt
            payment_intent_id = invoice.get("payment_intent")
            if payment_intent_id:
                pi = stripe.PaymentIntent.retrieve(payment_intent_id)
                last_error = pi.get("last_payment_error", {})
                if last_error:
                    record.failure_reason = last_error.get("message", "")[:255]
                    record.save(update_fields=["failure_reason"])

            return False

        except stripe.error.CardError as exc:
            record.failure_reason = str(exc.user_message or exc)[:255]
            record.save(update_fields=["failure_reason"])
            return False

        except stripe.error.InvalidRequestError as exc:
            # Invoice may already be paid or voided
            logger.warning(
                "Stripe InvalidRequestError for invoice %s: %s",
                record.stripe_invoice_id,
                exc,
            )
            # If Stripe says invoice is already paid, mark as resolved
            if "already" in str(exc).lower() or "paid" in str(exc).lower():
                return True
            return False

    def _mark_resolved(self, record: DunningRecord):
        """Mark dunning record as resolved and restore policy to active."""

        now = timezone.now()
        record.status = "resolved"
        record.resolved_at = now
        record.last_attempt_at = now
        record.next_retry_at = None
        record.save(
            update_fields=["status", "resolved_at", "last_attempt_at", "next_retry_at"]
        )

        # Restore policy to active if it was past_due
        policy = record.policy
        if policy.status == "past_due":
            policy.status = "active"
            policy.save(update_fields=["status"])
            logger.info(
                "Policy %s restored to active after dunning recovery",
                policy.policy_number,
            )

        # Send success notification email
        self._send_payment_recovered_email(record)

    def _cancel_policy_for_non_payment(self, record: DunningRecord):
        """Cancel the policy after exhausting all dunning retries."""
        from django.conf import settings as django_settings
        from emails.schemas import SendEmailInput
        from emails.service import EmailService
        from django.template.loader import render_to_string

        now = timezone.now()
        policy = record.policy

        record.status = "cancelled"
        record.resolved_at = now
        record.last_attempt_at = now
        record.next_retry_at = None
        record.save(
            update_fields=["status", "resolved_at", "last_attempt_at", "next_retry_at"]
        )

        # Cancel the policy
        policy.status = "cancelled"
        policy.save(update_fields=["status"])

        logger.warning(
            "Policy %s cancelled after dunning exhaustion (record %s)",
            policy.policy_number,
            record.pk,
        )

        # Cancel the Stripe subscription if present
        if record.stripe_subscription_id:
            try:
                stripe.api_key = settings.STRIPE_SECRET_KEY
                stripe.Subscription.cancel(record.stripe_subscription_id)
            except Exception as exc:
                logger.warning(
                    "Could not cancel Stripe subscription %s: %s",
                    record.stripe_subscription_id,
                    exc,
                )

        # Send cancellation email
        user = getattr(policy.quote, "user", None)
        if user and user.email:
            try:
                coverage_display = (
                    policy.coverage_type.replace("-", " ").title()
                    if policy.coverage_type
                    else "Insurance"
                )
                html = render_to_string(
                    "emails/policy_cancelled.html",
                    {
                        "first_name": user.first_name or "there",
                        "coverage_type": coverage_display,
                        "policy_number": policy.policy_number,
                        "cancellation_reason": "non-payment",
                        "portal_url": django_settings.FRONTEND_URL,
                    },
                )
                EmailService.send(
                    SendEmailInput(
                        to=[user.email],
                        subject=f"Your {coverage_display} policy has been cancelled — non-payment",
                        html=html,
                        from_email=django_settings.HELLO_CORGI_EMAIL,
                    )
                )
            except Exception as exc:
                logger.warning(
                    "Could not send cancellation email for policy %s: %s",
                    policy.policy_number,
                    exc,
                )

    def _send_payment_recovered_email(self, record: DunningRecord):
        """Send a confirmation email when payment is recovered."""
        from django.conf import settings as django_settings
        from emails.schemas import SendEmailInput
        from emails.service import EmailService

        policy = record.policy
        user = getattr(policy.quote, "user", None)
        if not user or not user.email:
            return

        try:
            coverage_display = (
                policy.coverage_type.replace("-", " ").title()
                if policy.coverage_type
                else "Insurance"
            )
            html = (
                f"<p>Hi {user.first_name or 'there'},</p>"
                f"<p>Great news — your payment for <strong>{coverage_display}</strong> "
                f"(policy {policy.policy_number}) has been successfully processed.</p>"
                f"<p>Your coverage remains active. Thank you!</p>"
            )
            EmailService.send(
                SendEmailInput(
                    to=[user.email],
                    subject=f"Payment recovered — {coverage_display} policy active",
                    html=html,
                    from_email=django_settings.HELLO_CORGI_EMAIL,
                )
            )
        except Exception as exc:
            logger.warning(
                "Could not send payment recovered email for policy %s: %s",
                policy.policy_number,
                exc,
            )
