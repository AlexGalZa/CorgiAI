from decimal import Decimal

from rating.schemas import (
    CoverageRatingDefinition,
    LimitRetentionConfig,
    LimitOption,
    RetentionOption,
    MultiplierRule,
    ConditionalMultiplier,
    ReviewTrigger,
)

REVENUE_TIERS = [
    {"min": 0, "max": 250_000, "premium": Decimal("4119.19")},
    {"min": 250_000, "max": 500_000, "premium": Decimal("4796.45")},
    {"min": 500_000, "max": 1_000_000, "premium": Decimal("6032.20")},
    {"min": 1_000_000, "max": 2_500_000, "premium": Decimal("7209.11")},
    {"min": 2_500_000, "max": 5_000_000, "premium": Decimal("8327.18")},
    {"min": 5_000_000, "max": 10_000_000, "premium": Decimal("10392.12")},
    {"min": 10_000_000, "max": 25_000_000, "premium": Decimal("14158.23")},
    {"min": 25_000_000, "max": 50_000_000, "premium": Decimal("22129.13")},
    {"min": 50_000_000, "max": 100_000_000, "premium": Decimal("29190.59")},
    {"min": 100_000_000, "max": 500_000_000, "premium": Decimal("41601.65")},
    {"min": 500_000_000, "max": float("inf"), "premium": Decimal("52193.84")},
]

LIMIT_FACTORS = {
    500_000: 0.737,
    1_000_000: 1.000,
    1_500_000: 1.196,
    2_000_000: 1.357,
    3_000_000: 1.700,
    4_000_000: 1.950,
    5_000_000: 2.200,
    10_000_000: 3.500,
}
HIGH_LIMIT_THRESHOLD = 5_000_000
RETENTION_FACTORS = {
    5_000: 1.000,
    10_000: 0.833,
    15_000: 0.794,
    20_000: 0.756,
    25_000: 0.717,
    50_000: 0.522,
}

HAZARD_CLASS_FACTORS = {
    "nonprofit-commerce": 0.70,
    "dev-tools": 0.90,
    "ecommerce-enablement": 0.95,
    "b2c-apps": 1.00,
    "b2b-saas": 1.10,
    "marketplace": 1.20,
    "adtech-martech": 1.20,
    "data-analytics": 1.25,
    "it-services": 1.25,
    "iot-hardware": 1.30,
    "ai-ml": 1.30,
    "healthtech": 1.35,
    "ai-regulated": 1.40,
    "fintech-consumer": 1.45,
    "fintech-lending": 1.50,
    "fintech-infrastructure": 1.55,
    "crypto-web3": 1.70,
}

AI_COVERAGE_MULTIPLIERS = {
    "service-interruption-liability": 1.00,
    "training-data-misuse-liability": 1.00,
    "regulatory-investigation-defense-costs": 1.00,
    "data-poisoning-adversarial-attack": 1.00,
    "civil-fines-penalties": 1.00,
    "ai-intellectual-property-liability": 1.10,
    "hallucination-defamation-liability": 1.10,
    "algorithmic-bias-liability": 1.15,
    "deepfake-synthetic-media-liability": 1.25,
    "bodily-injury-property-damage-autonomous-ai": 1.35,
}


def calculate_ai_coverage_multiplier(questionnaire: dict) -> float:
    if not questionnaire.get("wants_ai_coverage"):
        return 1.0

    ai_options = questionnaire.get("ai_coverage_options", [])
    if not ai_options:
        return 1.0

    total_multiplier = 1.0
    for option in ai_options:
        if option in AI_COVERAGE_MULTIPLIERS:
            total_multiplier *= AI_COVERAGE_MULTIPLIERS[option]

    return total_multiplier


DEFINITION = CoverageRatingDefinition(
    coverage_id="technology-errors-and-omissions",
    limits_retentions=LimitRetentionConfig(
        aggregate_limits=[LimitOption(v, LIMIT_FACTORS[v]) for v in LIMIT_FACTORS],
        per_occurrence_limits=[
            LimitOption(500_000, 0.737),
            LimitOption(1_000_000, 1.0),
            LimitOption(2_000_000, 1.357),
            LimitOption(3_000_000, 1.7),
            LimitOption(4_000_000, 1.950),
            LimitOption(5_000_000, 2.2),
            LimitOption(10_000_000, 3.5),
        ],
        retentions=[
            RetentionOption(v, RETENTION_FACTORS[v]) for v in RETENTION_FACTORS
        ],
    ),
    multiplier_rules=[
        ConditionalMultiplier(
            "criticality",
            [
                (lambda q: q.get("service_criticality") == "not-critical", 1.00),
                (lambda q: q.get("service_criticality") == "moderately-critical", 1.15),
                (lambda q: q.get("service_criticality") == "highly-critical", 1.35),
            ],
            1.00,
        ),
        MultiplierRule(
            "contract_protections",
            lambda q: q.get("has_liability_protections", False),
            0.75,
            1.00,
        ),
        MultiplierRule(
            "quality_assurance",
            lambda q: q.get("has_quality_assurance", False),
            0.75,
            1.00,
        ),
    ],
    review_triggers=[
        ReviewTrigger(
            "prior_incidents",
            lambda q, c: q.get("has_prior_incidents", False),
            "Review required: prior_incidents",
        ),
        ReviewTrigger(
            "high_limit",
            lambda q, c: getattr(c, "limit", 0) > HIGH_LIMIT_THRESHOLD,
            "Review required: high limit selected",
        ),
    ],
)

# Backwards-compat alias: tests and older imports expect TECH_EO_DEFINITION.
TECH_EO_DEFINITION = DEFINITION
