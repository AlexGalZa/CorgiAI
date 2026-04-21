"""
Seed default PlatformConfig entries.

Usage:
    python manage.py seed_platform_config          # create missing keys only
    python manage.py seed_platform_config --reset   # overwrite all to defaults
"""

from django.core.management.base import BaseCommand
from common.models import PlatformConfig


DEFAULTS = [
    # ── Underwriting ──────────────────────────────────────────────────────
    {
        "key": "aggregate_limit_options",
        "category": "underwriting",
        "description": "Available aggregate limit choices for quotes and brokered requests",
        "value": [
            {"value": 500000, "label": "$500,000"},
            {"value": 1000000, "label": "$1,000,000"},
            {"value": 2000000, "label": "$2,000,000"},
            {"value": 3000000, "label": "$3,000,000"},
            {"value": 4000000, "label": "$4,000,000"},
            {"value": 5000000, "label": "$5,000,000"},
            {"value": 10000000, "label": "$10,000,000"},
        ],
    },
    {
        "key": "per_occurrence_limit_options",
        "category": "underwriting",
        "description": "Available per-occurrence limit choices for quotes and brokered requests",
        "value": [
            {"value": 500000, "label": "$500,000"},
            {"value": 1000000, "label": "$1,000,000"},
            {"value": 2000000, "label": "$2,000,000"},
            {"value": 3000000, "label": "$3,000,000"},
            {"value": 4000000, "label": "$4,000,000"},
            {"value": 5000000, "label": "$5,000,000"},
            {"value": 10000000, "label": "$10,000,000"},
        ],
    },
    {
        "key": "retention_options",
        "category": "underwriting",
        "description": "Available retention/deductible choices for quotes and brokered requests",
        "value": [
            {"value": 0, "label": "$0"},
            {"value": 1000, "label": "$1,000"},
            {"value": 2500, "label": "$2,500"},
            {"value": 5000, "label": "$5,000"},
            {"value": 10000, "label": "$10,000"},
            {"value": 15000, "label": "$15,000"},
            {"value": 25000, "label": "$25,000"},
            {"value": 50000, "label": "$50,000"},
            {"value": 100000, "label": "$100,000"},
        ],
    },
    # ── Carriers ──────────────────────────────────────────────────────────
    {
        "key": "carrier_options",
        "category": "carriers",
        "description": "Available carrier options for brokered quote requests",
        "value": [
            {"value": "limit", "label": "Limit"},
            {"value": "am_trust", "label": "AM Trust"},
            {"value": "coterie", "label": "Coterie"},
            {"value": "rts", "label": "RTS / Nautilus"},
            {"value": "ergo_next", "label": "Ergo / NEXT"},
            {"value": "hiscox", "label": "Hiscox"},
            {"value": "zane", "label": "Zane"},
            {"value": "novella", "label": "Novella"},
            {"value": "wesure", "label": "weSure"},
            {"value": "rli", "label": "RLI"},
            {"value": "other", "label": "Other"},
        ],
    },
    # ── Coverages ─────────────────────────────────────────────────────────
    {
        "key": "brokered_coverage_type_options",
        "category": "coverages",
        "description": "Coverage types available in the brokered request form",
        "value": [
            {"value": "cgl", "label": "Commercial General Liability"},
            {"value": "cul", "label": "Commercial Umbrella"},
            {"value": "cyber", "label": "Cyber Liability"},
            {"value": "tech_eo", "label": "Technology E&O"},
            {"value": "workers_comp", "label": "Workers Compensation"},
            {"value": "dno", "label": "Directors & Officers"},
            {"value": "bop", "label": "Business Owners Policy"},
            {"value": "crime", "label": "Crime"},
            {"value": "epl", "label": "Employment Practices Liability"},
            {"value": "med_malpractice", "label": "Medical Malpractice"},
            {"value": "comm_auto", "label": "Commercial Auto"},
            {"value": "hnoa", "label": "Hired & Non-Owned Auto"},
            {"value": "kidnap_ransom", "label": "Kidnap & Ransom"},
            {"value": "inland_marine", "label": "Inland Marine"},
            {"value": "aviation", "label": "Aviation"},
            {"value": "real_estate_eo", "label": "Real Estate E&O"},
            {"value": "misc_eo", "label": "Miscellaneous E&O"},
            {"value": "reps_warranties", "label": "Representations & Warranties"},
            {"value": "fiduciary", "label": "Fiduciary"},
            {"value": "erisa", "label": "ERISA 401(k)"},
            {"value": "pollution", "label": "Pollution/Environmental"},
            {"value": "international", "label": "International Package"},
            {"value": "media", "label": "Media Liability"},
            {"value": "crime_bond", "label": "Crime Bond"},
            {"value": "uas_aviation", "label": "UAS/Aviation Liability"},
            {"value": "other", "label": "Other"},
        ],
    },
    # ── Brokerage ─────────────────────────────────────────────────────────
    {
        "key": "brokered_status_options",
        "category": "brokerage",
        "description": "Status choices for brokered quote requests pipeline",
        "value": [
            {"value": "received", "label": "Received"},
            {"value": "submitted", "label": "Submitted"},
            {"value": "otm", "label": "Out to Market"},
            {"value": "quoted", "label": "Quoted"},
            {"value": "on_hold", "label": "On Hold"},
            {"value": "denied", "label": "Denied"},
            {"value": "recalled", "label": "Recalled"},
            {"value": "blocked", "label": "Blocked"},
            {"value": "stalled", "label": "Stalled"},
            {"value": "cancelled", "label": "Cancelled"},
            {"value": "bound", "label": "Bound"},
        ],
    },
    # ── Billing & Fees ────────────────────────────────────────────────────
    {
        "key": "monthly_billing_surcharge",
        "category": "billing",
        "description": "Surcharge multiplier for monthly billing (e.g. 1.111 = ~11.1% surcharge over annual)",
        "value": 1.111,
    },
    {
        "key": "stripe_processing_fee_multiplier",
        "category": "billing",
        "description": "Stripe processing fee multiplier applied to premiums (e.g. 1.029 = 2.9%)",
        "value": 1.029,
    },
    {
        "key": "admin_fee_rate",
        "category": "billing",
        "description": "Admin fee rate as a decimal (e.g. 0.22 = 22%)",
        "value": 0.22,
    },
    # ── General ───────────────────────────────────────────────────────────
    {
        "key": "organization_type_options",
        "category": "general",
        "description": "Legal structure / organization type choices for the quote flow",
        "value": [
            {"value": "corporation", "label": "Corporation"},
            {"value": "llc", "label": "LLC"},
            {"value": "partnership", "label": "Partnership"},
            {"value": "sole_proprietorship", "label": "Sole Proprietorship"},
            {"value": "non_profit", "label": "Non-Profit"},
            {"value": "other", "label": "Other"},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed default PlatformConfig entries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Overwrite existing values with defaults",
        )

    def handle(self, *args, **options):
        reset = options["reset"]
        created = 0
        updated = 0
        skipped = 0

        for entry in DEFAULTS:
            obj, was_created = PlatformConfig.objects.get_or_create(
                key=entry["key"],
                defaults={
                    "value": entry["value"],
                    "category": entry["category"],
                    "description": entry["description"],
                },
            )
            if was_created:
                created += 1
                self.stdout.write(f"  ✅ Created: {entry['key']}")
            elif reset:
                obj.value = entry["value"]
                obj.category = entry["category"]
                obj.description = entry["description"]
                obj.save()
                updated += 1
                self.stdout.write(f"  🔄 Reset: {entry['key']}")
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone: {created} created, {updated} reset, {skipped} skipped"
            )
        )
