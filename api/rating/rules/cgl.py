from decimal import Decimal

from rating.schemas import (
    CoverageRatingDefinition,
    LimitRetentionConfig,
    LimitOption,
    RetentionOption,
    BaseRateTable,
    BaseRateEntry,
    MultiplierRule,
    ConditionalMultiplier,
    ReviewTrigger,
)

BASE_RATES = BaseRateTable(
    entries={
        "low-hazard": BaseRateEntry(
            key="low-hazard", rate=0.55, minimum_premium=Decimal("250")
        ),
        "moderate-hazard": BaseRateEntry(
            key="moderate-hazard", rate=0.90, minimum_premium=Decimal("350")
        ),
        "elevated-hazard": BaseRateEntry(
            key="elevated-hazard", rate=1.40, minimum_premium=Decimal("500")
        ),
        "high-hazard": BaseRateEntry(
            key="high-hazard", rate=2.10, minimum_premium=Decimal("750")
        ),
        "not-applicable": BaseRateEntry(
            key="not-applicable", rate=1.00, minimum_premium=Decimal("300")
        ),
    }
)

ALT_CLASS_RATES = {
    "low-hazard": Decimal("7.50"),
    "moderate-hazard": Decimal("11.00"),
    "elevated-hazard": Decimal("16.00"),
    "high-hazard": Decimal("25.00"),
    "not-applicable": Decimal("11.00"),
}

SQUARE_FOOTAGE_VALUES = {
    "up_to_2500": 1250,
    "2501_5000": 3750,
    "5001_10000": 7500,
    "10001_25000": 17500,
    "over_25000": 30000,
    "not_applicable": 0,
}

LIMIT_FACTORS = {
    500_000: 1.000,
    1_000_000: 1.189,
    1_500_000: 1.302,
    2_000_000: 1.381,
    3_000_000: 1.700,
    4_000_000: 1.950,
    5_000_000: 2.200,
    10_000_000: 3.500,
}
HIGH_LIMIT_THRESHOLD = 5_000_000
RETENTION_FACTORS = {500: 0.992, 1_000: 0.985, 1_500: 0.979, 2_000: 0.973}

DEFINITION = CoverageRatingDefinition(
    coverage_id="commercial-general-liability",
    limits_retentions=LimitRetentionConfig(
        aggregate_limits=[LimitOption(v, LIMIT_FACTORS[v]) for v in LIMIT_FACTORS],
        per_occurrence_limits=[
            LimitOption(500_000, 1.0),
            LimitOption(1_000_000, 1.189),
            LimitOption(2_000_000, 1.381),
            LimitOption(3_000_000, 1.7),
            LimitOption(4_000_000, 1.950),
            LimitOption(5_000_000, 2.2),
            LimitOption(10_000_000, 3.5),
        ],
        retentions=[
            RetentionOption(v, RETENTION_FACTORS[v]) for v in RETENTION_FACTORS
        ],
    ),
    base_rate_table=BASE_RATES,
    multiplier_rules=[
        MultiplierRule(
            "physical_locations",
            lambda q: q.get("has_physical_locations", False),
            1.10,
            0.90,
        ),
        ConditionalMultiplier(
            "client_site_work",
            [
                (lambda q: not q.get("has_products_completed_operations", False), 1.00),
                (lambda q: q.get("has_client_site_work", False), 1.25),
                (lambda q: not q.get("has_client_site_work", False), 1.00),
            ],
            1.00,
        ),
        ConditionalMultiplier(
            "premises_safety",
            [
                (lambda q: not q.get("has_physical_locations", False), 1.00),
                (lambda q: q.get("has_safety_measures") == "N/A", 1.00),
                (
                    lambda q: (
                        q.get("has_safety_measures") == "Yes"
                        or q.get("has_safety_measures") is True
                    ),
                    0.90,
                ),
                (
                    lambda q: (
                        q.get("has_safety_measures") == "No"
                        or q.get("has_safety_measures") is False
                    ),
                    1.10,
                ),
            ],
            1.00,
        ),
        ConditionalMultiplier(
            "quality_control",
            [
                (lambda q: not q.get("has_products_completed_operations", False), 1.00),
                (lambda q: q.get("has_quality_control") == "N/A", 1.00),
                (lambda q: q.get("has_quality_control") == "Yes", 0.90),
                (lambda q: q.get("has_quality_control") == "No", 1.15),
            ],
            1.00,
        ),
        ConditionalMultiplier(
            "subcontractors",
            [
                (lambda q: not q.get("has_products_completed_operations", False), 1.00),
                (lambda q: not q.get("uses_subcontractors", False), 0.90),
                (
                    lambda q: (
                        q.get("uses_subcontractors")
                        and q.get("requires_subcontractor_insurance")
                    ),
                    1.00,
                ),
                (
                    lambda q: (
                        q.get("uses_subcontractors")
                        and not q.get("requires_subcontractor_insurance")
                    ),
                    1.20,
                ),
            ],
            1.00,
        ),
        MultiplierRule(
            "contractual_liability",
            lambda q: q.get("has_contractual_liability", False),
            0.95,
            1.10,
        ),
    ],
    review_triggers=[
        ReviewTrigger(
            "hazardous_materials",
            lambda q, c: q.get("has_hazardous_materials", False),
            "Review required: hazardous_materials",
        ),
        ReviewTrigger(
            "other_exposures",
            lambda q, c: (
                q.get("has_other_exposures", False)
                and q.get("other_exposures_description")
            ),
            "Review required: other_exposures",
        ),
        ReviewTrigger(
            "high_limit",
            lambda q, c: getattr(c, "limit", 0) > HIGH_LIMIT_THRESHOLD,
            "Review required: high limit selected",
        ),
    ],
)
