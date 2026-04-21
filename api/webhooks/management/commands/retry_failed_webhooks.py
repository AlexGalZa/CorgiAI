"""
Management command: retry failed webhook deliveries.

Usage:
    python manage.py retry_failed_webhooks
    python manage.py retry_failed_webhooks --older-than 30
"""

from django.core.management.base import BaseCommand

from webhooks.delivery import WebhookDeliveryService


class Command(BaseCommand):
    help = "Retry failed webhook deliveries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--older-than",
            type=int,
            default=0,
            metavar="MINUTES",
            help=(
                "Only retry deliveries that failed more than N minutes ago. Default 0 = retry all failed deliveries."
            ),
        )

    def handle(self, *args, **options):
        older_than = options["older_than"]

        self.stdout.write(
            self.style.NOTICE(
                "Retrying failed webhook deliveries"
                + (f" older than {older_than} minutes" if older_than else "")
                + "..."
            )
        )

        count = WebhookDeliveryService.retry_failed(older_than_minutes=older_than)

        self.stdout.write(
            self.style.SUCCESS(f"Retried {count} failed webhook deliveries.")
        )
