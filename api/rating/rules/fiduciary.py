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

MINIMUM_BASE_PREMIUM = Decimal("748.94")
MINIMUM_BASE_PREMIUM_BENEFIT = Decimal("962.93")

ASSET_TIERS = [
    {
        "ceiling_000": 5_999,
        "rate_contribution": None,
        "rate_benefit": None,
        "full_cumulative_contribution": Decimal("748.94"),
        "full_cumulative_benefit": Decimal("962.93"),
    },
    {
        "prev_ceiling_000": 5_999,
        "ceiling_000": 50_999,
        "rate_contribution": Decimal("42.80"),
        "rate_benefit": Decimal("53.50"),
        "start_cumulative_contribution": Decimal("748.94"),
        "start_cumulative_benefit": Decimal("962.93"),
    },
    {
        "prev_ceiling_000": 50_999,
        "ceiling_000": 75_999,
        "rate_contribution": Decimal("21.40"),
        "rate_benefit": Decimal("26.75"),
        "start_cumulative_contribution": Decimal("2674.80"),
        "start_cumulative_benefit": Decimal("3370.24"),
    },
    {
        "prev_ceiling_000": 75_999,
        "ceiling_000": 150_999,
        "rate_contribution": Decimal("10.70"),
        "rate_benefit": Decimal("13.37"),
        "start_cumulative_contribution": Decimal("3209.76"),
        "start_cumulative_benefit": Decimal("4038.94"),
    },
    {
        "prev_ceiling_000": 150_999,
        "ceiling_000": float("inf"),
        "rate_contribution": Decimal("5.35"),
        "rate_benefit": Decimal("6.69"),
        "start_cumulative_contribution": Decimal("4012.20"),
        "start_cumulative_benefit": Decimal("5041.99"),
    },
]

LIMIT_FACTORS = {
    500_000: 0.646,
    1_000_000: 1.000,
    1_500_000: 1.291,
    2_000_000: 1.548,
    3_000_000: 1.950,
    4_000_000: 2.275,
    5_000_000: 2.600,
    10_000_000: 4.200,
}
HIGH_LIMIT_THRESHOLD = 5_000_000
RETENTION_BASE_FACTORS = {
    10_000: 0.818,
    20_000: 0.773,
    30_000: 0.733,
    40_000: 0.707,
    50_000: 0.682,
    60_000: 0.664,
}
RETENTION_DAMPENING_COEFFICIENT = Decimal("0.25")


def calculate_fiduciary_base_premium(
    plan_assets: float, has_defined_benefit: bool = False
) -> Decimal:
    minimum = (
        MINIMUM_BASE_PREMIUM_BENEFIT if has_defined_benefit else MINIMUM_BASE_PREMIUM
    )

    if not plan_assets or plan_assets <= 0:
        return minimum

    plan_assets_000 = plan_assets / 1000
    tier1 = ASSET_TIERS[0]

    if plan_assets_000 <= tier1["ceiling_000"]:
        # Tier 1: flat minimum premium
        return minimum

    for tier in ASSET_TIERS[1:]:
        if plan_assets_000 <= tier["ceiling_000"]:
            start_cumulative = (
                tier["start_cumulative_benefit"]
                if has_defined_benefit
                else tier["start_cumulative_contribution"]
            )
            rate = (
                tier["rate_benefit"]
                if has_defined_benefit
                else tier["rate_contribution"]
            )
            excess_000 = plan_assets_000 - tier["prev_ceiling_000"]
            return start_cumulative + Decimal(str(excess_000 / 1000)) * rate

    return minimum


def calculate_retention_factor(retention_amount: int) -> Decimal:
    base_factor = RETENTION_BASE_FACTORS.get(retention_amount)
    if base_factor is None:
        return Decimal("1.00")
    base = Decimal(str(base_factor))
    return (
        Decimal("1") - (Decimal("1") - base) * RETENTION_DAMPENING_COEFFICIENT
    ).quantize(Decimal("0.001"))


RETENTION_FACTORS = {
    r: float(calculate_retention_factor(r)) for r in RETENTION_BASE_FACTORS
}

DEFINITION = CoverageRatingDefinition(
    coverage_id="fiduciary-liability",
    limits_retentions=LimitRetentionConfig(
        aggregate_limits=[LimitOption(v, LIMIT_FACTORS[v]) for v in LIMIT_FACTORS],
        per_occurrence_limits=[
            LimitOption(500_000, 0.646),
            LimitOption(1_000_000, 1.0),
            LimitOption(2_000_000, 1.548),
            LimitOption(3_000_000, 1.95),
            LimitOption(4_000_000, 2.275),
            LimitOption(5_000_000, 2.6),
            LimitOption(10_000_000, 4.2),
        ],
        retentions=[
            RetentionOption(v, RETENTION_FACTORS[v]) for v in RETENTION_FACTORS
        ],
    ),
    multiplier_rules=[
        ConditionalMultiplier(
            "db_funding_level",
            [
                (lambda q: not q.get("has_defined_benefit_plan", False), 1.00),
                (lambda q: q.get("defined_benefit_funding_percent", 100) <= 65, 1.40),
                (lambda q: q.get("defined_benefit_funding_percent", 100) <= 79, 1.20),
                (lambda q: q.get("defined_benefit_funding_percent", 100) <= 85, 1.00),
                (lambda q: q.get("defined_benefit_funding_percent", 100) <= 100, 0.90),
            ],
            0.80,
        ),
        MultiplierRule(
            "service_providers",
            lambda q: (
                q.get(
                    "service_provider_count",
                    sum(
                        1
                        for f in [
                            "recordkeeper",
                            "third_party_admin",
                            "custodian",
                            "investment_advisor",
                            "benefits_broker",
                            "actuary",
                        ]
                        if q.get(f)
                    ),
                )
                < 3
            ),
            1.50,
            1.00,
        ),
        MultiplierRule(
            "company_stock",
            lambda q: q.get("has_company_stock_in_plan", False),
            1.50,
            1.00,
        ),
        MultiplierRule(
            "compliance_issues",
            lambda q: q.get("has_regulatory_issues", False),
            1.50,
            1.00,
        ),
        MultiplierRule(
            "plan_changes",
            lambda q: q.get("has_significant_changes", False),
            1.25,
            1.00,
        ),
        MultiplierRule(
            "fiduciary_oversight",
            lambda q: q.get("has_fiduciary_committee", False),
            1.00,
            1.50,
        ),
    ],
    review_triggers=[
        ReviewTrigger(
            "high_limit",
            lambda q, c: getattr(c, "limit", 0) > HIGH_LIMIT_THRESHOLD,
            "Review required: high limit selected",
        ),
    ],
)
