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

DRIVER_BAND_PREMIUMS = {
    "0_5": Decimal("750"),
    "6_10": Decimal("1100"),
    "11_25": Decimal("1800"),
    "26_50": Decimal("2900"),
    "51_100": Decimal("4600"),
    "101_250": Decimal("7500"),
    "251_500": Decimal("12000"),
    "501_1000": Decimal("19000"),
    "1001_2000": Decimal("29000"),
    "2001_plus": None,
}

LIMIT_FACTORS = {
    1_000_000: 1.000,
    1_500_000: 1.096,
    2_000_000: 1.170,
    3_000_000: 1.450,
    4_000_000: 1.675,
    5_000_000: 1.900,
    10_000_000: 3.000,
}
HIGH_LIMIT_THRESHOLD = 5_000_000
RETENTION_FACTORS = {300: 0.983, 500: 0.973, 1_000: 0.949, 1_500: 0.929, 2_000: 0.909}
PHYS_DAMAGE_FACTORS = {
    "none": 0.95,
    "25k_50k": 1.00,
    "50k_100k": 1.05,
    "100k_250k": 1.10,
}

DEFINITION = CoverageRatingDefinition(
    coverage_id="hired-and-non-owned-auto",
    limits_retentions=LimitRetentionConfig(
        aggregate_limits=[LimitOption(v, LIMIT_FACTORS[v]) for v in LIMIT_FACTORS],
        per_occurrence_limits=[
            LimitOption(1_000_000, 1.0),
            LimitOption(2_000_000, 1.170),
            LimitOption(3_000_000, 1.45),
            LimitOption(4_000_000, 1.675),
            LimitOption(5_000_000, 1.9),
            LimitOption(10_000_000, 3.0),
        ],
        retentions=[
            RetentionOption(v, RETENTION_FACTORS[v]) for v in RETENTION_FACTORS
        ],
    ),
    multiplier_rules=[
        MultiplierRule(
            "young_drivers", lambda q: q.get("has_drivers_under_25", False), 1.50, 1.00
        ),
        ConditionalMultiplier(
            "driving_frequency",
            [
                (lambda q: q.get("driving_frequency") == "rarely", 0.90),
                (lambda q: q.get("driving_frequency") == "occasionally", 1.00),
                (lambda q: q.get("driving_frequency") == "regularly", 1.15),
            ],
            1.00,
        ),
        ConditionalMultiplier(
            "travel_distance",
            [
                (lambda q: q.get("travel_distance") == "local", 0.95),
                (lambda q: q.get("travel_distance") == "long-distance", 1.15),
            ],
            1.00,
        ),
        MultiplierRule(
            "safety_measures",
            lambda q: q.get("has_driver_safety_measures", False),
            0.95,
            1.10,
        ),
        MultiplierRule(
            "vehicle_rentals", lambda q: q.get("rents_vehicles", False), 1.25, 1.00
        ),
        MultiplierRule(
            "specialty_vehicles",
            lambda q: q.get("has_high_value_vehicles", False),
            1.50,
            1.00,
        ),
    ],
    review_triggers=[
        ReviewTrigger(
            "past_incidents",
            lambda q, c: q.get("has_past_auto_incidents", False),
            "Review required: past_incidents",
        ),
        ReviewTrigger(
            "large_driver_count",
            lambda q, c: q.get("driver_band") == "2001_plus",
            "Review required: large_driver_count",
        ),
        ReviewTrigger(
            "high_limit",
            lambda q, c: getattr(c, "limit", 0) > HIGH_LIMIT_THRESHOLD,
            "Review required: high limit selected",
        ),
    ],
)
