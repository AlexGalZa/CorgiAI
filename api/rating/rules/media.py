from decimal import Decimal
from rating.schemas import (
    CoverageRatingDefinition,
    LimitRetentionConfig,
    LimitOption,
    RetentionOption,
    MultiplierRule,
    ReviewTrigger,
)

REVENUE_TIERS = [
    {"max": 500_000, "premium": Decimal("1500")},
    {"max": 750_000, "premium": Decimal("1700")},
    {"max": 1_000_000, "premium": Decimal("1900")},
    {"max": 2_000_000, "premium": Decimal("2400")},
    {"max": 3_000_000, "premium": Decimal("2800")},
    {"max": 5_000_000, "premium": Decimal("3400")},
    {"max": 7_500_000, "premium": Decimal("4100")},
    {"max": 10_000_000, "premium": Decimal("4800")},
    {"max": 15_000_000, "premium": Decimal("6000")},
    {"max": 20_000_000, "premium": Decimal("7200")},
    {"max": 25_000_000, "premium": Decimal("8400")},
    {"max": 30_000_000, "premium": Decimal("9600")},
    {"max": 40_000_000, "premium": Decimal("11500")},
    {"max": 50_000_000, "premium": Decimal("13500")},
]

LIMIT_FACTORS = {
    500_000: 0.829,
    1_000_000: 1.000,
    1_500_000: 1.116,
    2_000_000: 1.206,
    3_000_000: 1.500,
    4_000_000: 1.750,
    5_000_000: 2.000,
    10_000_000: 3.200,
}
HIGH_LIMIT_THRESHOLD = 5_000_000

RETENTION_FACTORS = {
    1_000: 1.000,
    5_000: 0.914,
    10_000: 0.862,
    15_000: 0.816,
    20_000: 0.770,
    25_000: 0.724,
    50_000: 0.494,
}

CONTENT_EXPOSURE_FACTORS = {
    "low": 0.85,
    "moderate": 0.95,
    "elevated": 1.10,
    "high": 1.25,
    "very_high": 1.50,
    "extreme": 2.00,  # Very high volume - will trigger review
}


def get_content_exposure_factor(questionnaire: dict) -> float:
    # company_content_volume is a computed field that parses original_content_volume band
    company_volume = questionnaire.get("company_content_volume") or 0
    # ugc_content_volume_numeric is a computed field that parses ugc_content_volume band
    ugc_volume = questionnaire.get("ugc_content_volume_numeric") or 0
    total_volume = company_volume + ugc_volume
    if total_volume >= 50_000:
        return CONTENT_EXPOSURE_FACTORS["extreme"]
    elif total_volume >= 20_000:
        return CONTENT_EXPOSURE_FACTORS["very_high"]
    elif total_volume >= 5_000:
        return CONTENT_EXPOSURE_FACTORS["high"]
    elif total_volume >= 1_000:
        return CONTENT_EXPOSURE_FACTORS["elevated"]
    elif total_volume >= 100:
        return CONTENT_EXPOSURE_FACTORS["moderate"]
    return CONTENT_EXPOSURE_FACTORS["low"]


DEFINITION = CoverageRatingDefinition(
    coverage_id="media-liability",
    limits_retentions=LimitRetentionConfig(
        aggregate_limits=[LimitOption(v, LIMIT_FACTORS[v]) for v in LIMIT_FACTORS],
        per_occurrence_limits=[
            LimitOption(500_000, LIMIT_FACTORS[500_000]),
            LimitOption(1_000_000, LIMIT_FACTORS[1_000_000]),
            LimitOption(2_000_000, LIMIT_FACTORS[2_000_000]),
            LimitOption(3_000_000, LIMIT_FACTORS[3_000_000]),
            LimitOption(4_000_000, LIMIT_FACTORS[4_000_000]),
            LimitOption(5_000_000, LIMIT_FACTORS[5_000_000]),
            LimitOption(10_000_000, LIMIT_FACTORS[10_000_000]),
        ],
        retentions=[
            RetentionOption(v, RETENTION_FACTORS[v]) for v in RETENTION_FACTORS
        ],
    ),
    multiplier_rules=[
        MultiplierRule(
            "content_moderation",
            lambda q: q.get("has_content_moderation", False),
            1.00,
            1.30,
        ),
        MultiplierRule(
            "ip_controls", lambda q: q.get("has_media_controls", False), 0.90, 1.30
        ),
        MultiplierRule(
            "legal_complaints",
            lambda q: q.get("has_past_complaints", False),
            1.50,
            1.00,
        ),
        MultiplierRule(
            "third_party_content",
            lambda q: q.get("uses_third_party_content", False),
            1.30,
            1.00,
        ),
    ],
    review_triggers=[
        # Use computed fields: company_content_volume and ugc_content_volume_numeric
        ReviewTrigger(
            "extreme_content_volume",
            lambda q, c: (
                (q.get("company_content_volume") or 0)
                + (q.get("ugc_content_volume_numeric") or 0)
                >= 50_000
            ),
            "Review required: extreme_content_volume",
        ),
        ReviewTrigger(
            "extreme_ugc_unmoderated",
            lambda q, c: (
                (q.get("ugc_content_volume_numeric") or 0) >= 50_000
                and not q.get("has_content_moderation", False)
            ),
            "Review required: extreme_ugc_unmoderated",
        ),
        ReviewTrigger(
            "high_limit",
            lambda q, c: getattr(c, "limit", 0) > HIGH_LIMIT_THRESHOLD,
            "Review required: high_limit",
        ),
    ],
)
