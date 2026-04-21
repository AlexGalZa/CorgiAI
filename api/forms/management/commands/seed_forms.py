"""
Management command to seed all Tier 1 coverage form definitions.

Usage:
    python manage.py seed_forms           # Create/update all forms
    python manage.py seed_forms --clear   # Delete existing then recreate
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from forms.models import FormDefinition
from forms.seed_data import ALL_FORMS


class Command(BaseCommand):
    help = "Seed form definitions for all 8 Tier 1 coverage types."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing seeded form definitions before creating new ones.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            slugs = [f["slug"] for f in ALL_FORMS]
            deleted_count, _ = FormDefinition.objects.filter(slug__in=slugs).delete()
            self.stdout.write(
                self.style.WARNING(
                    f"Deleted {deleted_count} existing form definitions."
                )
            )

        created = 0
        updated = 0

        for form_data in ALL_FORMS:
            slug = form_data["slug"]
            version = form_data["version"]

            existing = FormDefinition.objects.filter(slug=slug, version=version).first()

            if existing:
                # Update existing form
                for key, value in form_data.items():
                    if key not in ("slug", "version"):
                        setattr(existing, key, value)
                existing.save()
                updated += 1
                self.stdout.write(f"  Updated: {form_data['name']} v{version}")
            else:
                # Deactivate other versions of same coverage type
                if form_data.get("is_active") and form_data.get("coverage_type"):
                    FormDefinition.objects.filter(
                        coverage_type=form_data["coverage_type"],
                        is_active=True,
                    ).update(is_active=False)

                FormDefinition.objects.create(**form_data)
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  Created: {form_data['name']} v{version}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone! Created {created}, updated {updated} form definitions."
            )
        )
