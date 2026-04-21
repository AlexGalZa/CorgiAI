"""
Issue (or reactivate) a read-only API key for a user with role=read_only.

Usage:
    python manage.py issue_readonly_key --user someone@example.com
    python manage.py issue_readonly_key --user someone@example.com --name "Partner X"

The raw key is printed exactly once. It is never stored in plaintext.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api_keys.models import ApiKey
from api_keys.service import ApiKeyService, READONLY_NAME_PREFIX
from users.models import User


class Command(BaseCommand):
    help = "Issue or reactivate a read-only API key for a read_only user."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            required=True,
            help="Email of the user the key will belong to. Must have role='read_only'.",
        )
        parser.add_argument(
            "--name",
            default=None,
            help=(
                "Optional descriptive label for the key (e.g. 'Partner X - reporting'). "
                "Defaults to '<email> - read-only'."
            ),
        )
        parser.add_argument(
            "--force-new",
            action="store_true",
            help=(
                "Always mint a brand-new key even if an active read-only key already "
                "exists for this user. The existing active key(s) will be deactivated."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        email = (options["user"] or "").strip().lower()
        if not email:
            raise CommandError("--user email is required.")

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise CommandError(f"No user found with email '{email}'.")

        if user.role != "read_only":
            raise CommandError(
                f"User '{user.email}' has role '{user.role}'. "
                f"Only users with role='read_only' may be issued a read-only API key. "
                f"Update the user's role first."
            )

        label = options["name"] or f"{user.email} - read-only"

        existing = ApiKey.objects.filter(
            created_by=user,
            name__startswith=READONLY_NAME_PREFIX,
        )
        active_existing = existing.filter(is_active=True)

        if active_existing.exists() and not options["force_new"]:
            # Reactivation path is a no-op: the raw key is unrecoverable by design.
            # The operator must pass --force-new to rotate.
            key = active_existing.order_by("-created_at").first()
            self.stdout.write(
                self.style.WARNING(
                    f"An active read-only API key already exists for {user.email}: "
                    f"prefix={key.prefix}. The raw key cannot be re-displayed. "
                    f"Re-run with --force-new to rotate and mint a new one."
                )
            )
            return

        # Deactivate any prior read-only keys belonging to this user.
        deactivated = existing.filter(is_active=True).update(is_active=False)

        api_key, raw = ApiKeyService.create_readonly_key(
            name=label,
            created_by=user,
        )

        if deactivated:
            self.stdout.write(
                self.style.WARNING(
                    f"Deactivated {deactivated} previously-active read-only key(s) for {user.email}."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Read-only API key issued for {user.email} (prefix={api_key.prefix})."
            )
        )
        self.stdout.write("")
        self.stdout.write("Store this key securely - it will NOT be shown again:")
        self.stdout.write("")
        self.stdout.write(f"    {raw}")
        self.stdout.write("")
