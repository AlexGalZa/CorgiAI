"""
Bulk sync all existing records to HubSpot.

Usage:
    python manage.py hubspot_sync_all                    # sync everything
    python manage.py hubspot_sync_all --contacts         # contacts only
    python manage.py hubspot_sync_all --companies        # companies only
    python manage.py hubspot_sync_all --deals            # deals only
    python manage.py hubspot_sync_all --dry-run          # preview without syncing
"""

import time

from django.core.management.base import BaseCommand

from hubspot_sync.service import HubSpotSyncService


class Command(BaseCommand):
    help = "Bulk sync Django records to HubSpot (initial backfill)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--contacts", action="store_true", help="Sync users → contacts only"
        )
        parser.add_argument(
            "--companies", action="store_true", help="Sync orgs → companies only"
        )
        parser.add_argument(
            "--deals", action="store_true", help="Sync policies → deals only"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Preview without syncing"
        )
        parser.add_argument(
            "--batch-delay",
            type=float,
            default=0.2,
            help="Seconds between API calls (rate limit protection)",
        )

    def handle(self, *args, **options):
        if not HubSpotSyncService.is_enabled():
            self.stderr.write(
                self.style.ERROR(
                    "HubSpot not configured. Set HUBSPOT_ACCESS_TOKEN in your environment."
                )
            )
            return

        dry_run = options["dry_run"]
        delay = options["batch_delay"]
        sync_all = not (options["contacts"] or options["companies"] or options["deals"])

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN — no API calls will be made\n")
            )

        # ── Contacts ──────────────────────────────────────────────
        if sync_all or options["contacts"]:
            from users.models import User

            users = User.objects.filter(
                is_active=True,
                hubspot_contact_id__isnull=True,
            ).exclude(email="")
            self.stdout.write(f"\n📇 Contacts: {users.count()} users to sync")

            if not dry_run:
                ok, fail = 0, 0
                for user in users.iterator():
                    result = HubSpotSyncService.sync_user_to_contact(user.id)
                    if result:
                        ok += 1
                        self.stdout.write(f"  ✅ {user.email} → {result}")
                    else:
                        fail += 1
                        self.stdout.write(f"  ❌ {user.email}")
                    time.sleep(delay)
                self.stdout.write(f"  Done: {ok} synced, {fail} failed")

        # ── Companies ─────────────────────────────────────────────
        if sync_all or options["companies"]:
            from organizations.models import Organization

            orgs = Organization.objects.filter(
                is_personal=False,
                hubspot_company_id__isnull=True,
            )
            self.stdout.write(f"\n🏢 Companies: {orgs.count()} organizations to sync")

            if not dry_run:
                ok, fail = 0, 0
                for org in orgs.iterator():
                    result = HubSpotSyncService.sync_org_to_company(org.id)
                    if result:
                        ok += 1
                        self.stdout.write(f"  ✅ {org.name} → {result}")
                    else:
                        fail += 1
                        self.stdout.write(f"  ❌ {org.name}")
                    time.sleep(delay)
                self.stdout.write(f"  Done: {ok} synced, {fail} failed")

        # ── Deals ─────────────────────────────────────────────────
        if sync_all or options["deals"]:
            from policies.models import Policy

            policies = Policy.objects.filter(
                hubspot_deal_id__isnull=True,
            ).exclude(status="cancelled")
            self.stdout.write(f"\n📋 Deals: {policies.count()} policies to sync")

            if not dry_run:
                ok, fail = 0, 0
                for policy in policies.iterator():
                    result = HubSpotSyncService.sync_policy_to_deal(policy.id)
                    if result:
                        ok += 1
                        self.stdout.write(f"  ✅ {policy.policy_number} → {result}")
                    else:
                        fail += 1
                        self.stdout.write(f"  ❌ {policy.policy_number}")
                    time.sleep(delay)
                self.stdout.write(f"  Done: {ok} synced, {fail} failed")

        self.stdout.write(self.style.SUCCESS("\n✅ Bulk sync complete"))
