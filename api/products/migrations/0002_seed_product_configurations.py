"""
Seed migration: populate ProductConfiguration from existing Tier 1 and Tier 2/3 coverage types.
"""

from django.db import migrations


PRODUCT_CONFIGS = [
    # Tier 1 — Instant
    {
        "coverage_type": "commercial-general-liability",
        "display_name": "Commercial General Liability",
        "description": "Covers third-party bodily injury, property damage, and personal/advertising injury.",
        "is_active": True,
        "min_limit": 500000,
        "max_limit": 10000000,
        "available_retentions": [500, 1000, 1500, 2000],
        "rating_tier": "tier1_instant",
        "requires_review": False,
    },
    {
        "coverage_type": "directors-and-officers",
        "display_name": "Directors & Officers",
        "description": "Protects company directors and officers from personal liability for management decisions.",
        "is_active": True,
        "min_limit": 500000,
        "max_limit": 10000000,
        "available_retentions": [500, 1000, 2500, 5000],
        "rating_tier": "tier1_instant",
        "requires_review": False,
    },
    {
        "coverage_type": "technology-errors-and-omissions",
        "display_name": "Technology E&O",
        "description": "Covers technology service failures, software errors, and professional mistakes.",
        "is_active": True,
        "min_limit": 500000,
        "max_limit": 10000000,
        "available_retentions": [500, 1000, 2500, 5000],
        "rating_tier": "tier1_instant",
        "requires_review": False,
    },
    {
        "coverage_type": "cyber-liability",
        "display_name": "Cyber Liability",
        "description": "Covers data breaches, ransomware, and cyber incidents.",
        "is_active": True,
        "min_limit": 500000,
        "max_limit": 10000000,
        "available_retentions": [500, 1000, 2500, 5000],
        "rating_tier": "tier1_instant",
        "requires_review": False,
    },
    {
        "coverage_type": "fiduciary-liability",
        "display_name": "Fiduciary Liability",
        "description": "Covers ERISA fiduciary duties and employee benefit plan management.",
        "is_active": True,
        "min_limit": 500000,
        "max_limit": 5000000,
        "available_retentions": [500, 1000, 2500],
        "rating_tier": "tier1_instant",
        "requires_review": False,
    },
    {
        "coverage_type": "hired-and-non-owned-auto",
        "display_name": "Hired & Non-Owned Auto",
        "description": "Covers liability for business use of rented or employee vehicles.",
        "is_active": True,
        "min_limit": 500000,
        "max_limit": 2000000,
        "available_retentions": [500, 1000],
        "rating_tier": "tier1_instant",
        "requires_review": False,
    },
    {
        "coverage_type": "media-liability",
        "display_name": "Media Liability",
        "description": "Covers intellectual property claims, defamation, and media content liability.",
        "is_active": True,
        "min_limit": 500000,
        "max_limit": 5000000,
        "available_retentions": [500, 1000, 2500],
        "rating_tier": "tier1_instant",
        "requires_review": False,
    },
    {
        "coverage_type": "employment-practices-liability",
        "display_name": "Employment Practices Liability",
        "description": "Covers wrongful termination, discrimination, harassment, and other employment claims.",
        "is_active": True,
        "min_limit": 500000,
        "max_limit": 5000000,
        "available_retentions": [500, 1000, 2500, 5000],
        "rating_tier": "tier1_instant",
        "requires_review": False,
    },
    # Tier 2 — Brokered with Form
    {
        "coverage_type": "custom-commercial-auto",
        "display_name": "Commercial Auto",
        "description": "Commercial vehicle insurance for owned business vehicles.",
        "is_active": True,
        "min_limit": None,
        "max_limit": None,
        "available_retentions": [],
        "rating_tier": "tier2_brokered_form",
        "requires_review": True,
    },
    {
        "coverage_type": "custom-crime",
        "display_name": "Commercial Crime",
        "description": "Covers employee theft, fraud, and forgery.",
        "is_active": True,
        "min_limit": None,
        "max_limit": None,
        "available_retentions": [],
        "rating_tier": "tier2_brokered_form",
        "requires_review": True,
    },
    {
        "coverage_type": "custom-kidnap-ransom",
        "display_name": "Kidnap & Ransom",
        "description": "Covers ransom payments, extortion, and crisis response.",
        "is_active": True,
        "min_limit": None,
        "max_limit": None,
        "available_retentions": [],
        "rating_tier": "tier2_brokered_form",
        "requires_review": True,
    },
    {
        "coverage_type": "custom-med-malpractice",
        "display_name": "Medical Malpractice",
        "description": "Professional liability for healthcare providers.",
        "is_active": True,
        "min_limit": None,
        "max_limit": None,
        "available_retentions": [],
        "rating_tier": "tier2_brokered_form",
        "requires_review": True,
    },
    # Tier 3 — Brokered Intent Only
    {
        "coverage_type": "custom-workers-comp",
        "display_name": "Workers' Compensation",
        "description": "Covers employee injuries and occupational illness. Automated via Pie Insurance.",
        "is_active": True,
        "min_limit": None,
        "max_limit": None,
        "available_retentions": [],
        "rating_tier": "tier3_brokered_intent",
        "requires_review": True,
    },
    {
        "coverage_type": "custom-bop",
        "display_name": "Business Owners Policy (BOP)",
        "description": "Combines general liability and commercial property.",
        "is_active": True,
        "min_limit": None,
        "max_limit": None,
        "available_retentions": [],
        "rating_tier": "tier3_brokered_intent",
        "requires_review": True,
    },
    {
        "coverage_type": "custom-umbrella",
        "display_name": "Umbrella / Excess Liability",
        "description": "Provides additional limits above underlying policies.",
        "is_active": True,
        "min_limit": None,
        "max_limit": None,
        "available_retentions": [],
        "rating_tier": "tier3_brokered_intent",
        "requires_review": True,
    },
]


def seed_products(apps, schema_editor):
    ProductConfiguration = apps.get_model("products", "ProductConfiguration")
    for config in PRODUCT_CONFIGS:
        ProductConfiguration.objects.get_or_create(
            coverage_type=config["coverage_type"],
            defaults=config,
        )


def remove_seeded_products(apps, schema_editor):
    ProductConfiguration = apps.get_model("products", "ProductConfiguration")
    slugs = [c["coverage_type"] for c in PRODUCT_CONFIGS]
    ProductConfiguration.objects.filter(coverage_type__in=slugs).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_products, remove_seeded_products),
    ]
