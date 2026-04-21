import re
from django.core.management.base import BaseCommand
from quotes.models import Quote


class Command(BaseCommand):
    help = "Convert form_data_snapshot keys from camelCase to snake_case"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without saving",
        )

    def camel_to_snake(self, name: str) -> str:
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name)
        return name.lower()

    def camel_to_snake_deep(self, obj):
        if obj is None:
            return obj
        if isinstance(obj, list):
            return [self.camel_to_snake_deep(item) for item in obj]
        if isinstance(obj, dict):
            return {
                self.camel_to_snake(k): self.camel_to_snake_deep(v)
                for k, v in obj.items()
            }
        return obj

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        quotes = Quote.objects.exclude(form_data_snapshot={}).exclude(
            form_data_snapshot__isnull=True
        )

        updated_count = 0
        skipped_count = 0

        for quote in quotes:
            snapshot = quote.form_data_snapshot
            if not snapshot:
                continue

            first_key = next(iter(snapshot.keys()), None)
            if (
                first_key
                and "_" in first_key
                and not any(c.isupper() for c in first_key)
            ):
                skipped_count += 1
                continue

            normalized = self.camel_to_snake_deep(snapshot)

            if dry_run:
                self.stdout.write(f"Would update {quote.quote_number}")
                updated_count += 1
            else:
                quote.form_data_snapshot = normalized
                quote.save(update_fields=["form_data_snapshot"])
                updated_count += 1
                self.stdout.write(f"Updated {quote.quote_number}")

        action = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {updated_count} quotes, skipped {skipped_count} (already normalized)"
            )
        )
