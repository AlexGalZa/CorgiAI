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

BASE_PREMIUMS = BaseRateTable(
    entries={
        "0_833000": BaseRateEntry(key="0_833000", rate=2458.03),
        "833001_2500000": BaseRateEntry(key="833001_2500000", rate=3220.08),
        "2500001_4167000": BaseRateEntry(key="2500001_4167000", rate=3655.31),
        "4167001_8333000": BaseRateEntry(key="4167001_8333000", rate=4343.87),
        "8333001_16667000": BaseRateEntry(key="8333001_16667000", rate=5435.19),
        "16667001_25000000": BaseRateEntry(key="16667001_25000000", rate=6066.44),
        "25000001_33333000": BaseRateEntry(key="25000001_33333000", rate=6237.63),
        "33333001_50000000": BaseRateEntry(key="33333001_50000000", rate=6954.47),
        "50000001_66667000": BaseRateEntry(key="50000001_66667000", rate=8559.35),
        "66667001_83333000": BaseRateEntry(key="66667001_83333000", rate=10057.24),
        "83333001_125000000": BaseRateEntry(key="83333001_125000000", rate=11662.11),
        "125000001_166667000": BaseRateEntry(key="125000001_166667000", rate=12732.03),
        "166667001_250000000": BaseRateEntry(key="166667001_250000000", rate=14015.93),
        "250000001_333333000": BaseRateEntry(key="250000001_333333000", rate=15406.83),
        "333333001_416667000": BaseRateEntry(key="333333001_416667000", rate=16476.75),
        "416667001_500000000": BaseRateEntry(key="416667001_500000000", rate=17332.68),
        "500000001_plus": BaseRateEntry(key="500000001_plus", rate=18509.59),
    }
)

LIMIT_FACTORS = {
    500_000: 0.646,
    1_000_000: 1.000,
    1_500_000: 1.274,
    2_000_000: 1.548,
    3_000_000: 1.900,
    4_000_000: 2.200,
    5_000_000: 2.500,
    10_000_000: 4.000,
}
HIGH_LIMIT_THRESHOLD = 5_000_000
RETENTION_FACTORS = {
    5_000: 0.929,
    10_000: 0.880,
    15_000: 0.853,
    20_000: 0.827,
    25_000: 0.800,
    50_000: 0.665,
}
INDUSTRY_GROUP_FACTORS = {
    "group1": 0.75,
    "group2": 1.00,
    "group3": 1.25,
    "group4": 1.50,
    "group5": 1.75,
    "group6": 2.00,
}
GEOGRAPHY_GROUP_FACTORS = {
    "low": 0.75,
    "standard": 1.00,
    "elevated": 1.25,
    "high": 1.50,
}

GEOGRAPHY_STATES = {
    "low": [
        "AL",
        "AK",
        "AR",
        "ID",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "MS",
        "MO",
        "MT",
        "NE",
        "ND",
        "OK",
        "SD",
        "TN",
        "UT",
        "WV",
        "WY",
    ],
    "standard": [
        "AZ",
        "CO",
        "FL",
        "GA",
        "ME",
        "MD",
        "MI",
        "MN",
        "NH",
        "NM",
        "NC",
        "OH",
        "OR",
        "PA",
        "SC",
        "TX",
        "VT",
        "VA",
        "WA",
        "WI",
    ],
    "elevated": ["CT", "DE", "HI", "IL", "MA", "NV", "NJ", "RI"],
    "high": ["CA", "DC"],
}


def get_geography_group_from_state(state: str) -> str:
    state_upper = state.upper() if state else ""
    for group, states in GEOGRAPHY_STATES.items():
        if state_upper in states:
            return group
    return "standard"


DEFINITION = CoverageRatingDefinition(
    coverage_id="directors-and-officers",
    limits_retentions=LimitRetentionConfig(
        aggregate_limits=[LimitOption(v, LIMIT_FACTORS[v]) for v in LIMIT_FACTORS],
        per_occurrence_limits=[
            LimitOption(500_000, 0.646),
            LimitOption(1_000_000, 1.0),
            LimitOption(2_000_000, 1.548),
            LimitOption(3_000_000, 1.9),
            LimitOption(4_000_000, 2.200),
            LimitOption(5_000_000, 2.5),
            LimitOption(10_000_000, 4.0),
        ],
        retentions=[
            RetentionOption(v, RETENTION_FACTORS[v]) for v in RETENTION_FACTORS
        ],
    ),
    base_rate_table=BASE_PREMIUMS,
    multiplier_rules=[
        ConditionalMultiplier(
            "industry_group",
            [
                (
                    lambda q: q.get("industry_group") == "group1",
                    INDUSTRY_GROUP_FACTORS["group1"],
                ),
                (
                    lambda q: q.get("industry_group") == "group2",
                    INDUSTRY_GROUP_FACTORS["group2"],
                ),
                (
                    lambda q: q.get("industry_group") == "group3",
                    INDUSTRY_GROUP_FACTORS["group3"],
                ),
                (
                    lambda q: q.get("industry_group") == "group4",
                    INDUSTRY_GROUP_FACTORS["group4"],
                ),
                (
                    lambda q: q.get("industry_group") == "group5",
                    INDUSTRY_GROUP_FACTORS["group5"],
                ),
                (
                    lambda q: q.get("industry_group") == "group6",
                    INDUSTRY_GROUP_FACTORS["group6"],
                ),
            ],
            1.00,
        ),
        ConditionalMultiplier(
            "geography",
            [
                (
                    lambda q: q.get("geography_group") == "low",
                    GEOGRAPHY_GROUP_FACTORS["low"],
                ),
                (
                    lambda q: q.get("geography_group") == "standard",
                    GEOGRAPHY_GROUP_FACTORS["standard"],
                ),
                (
                    lambda q: q.get("geography_group") == "elevated",
                    GEOGRAPHY_GROUP_FACTORS["elevated"],
                ),
                (
                    lambda q: q.get("geography_group") == "high",
                    GEOGRAPHY_GROUP_FACTORS["high"],
                ),
            ],
            1.00,
        ),
        MultiplierRule(
            "mergers_acquisitions",
            lambda q: q.get("has_mergers_acquisitions", False),
            1.35,
            1.00,
        ),
        ConditionalMultiplier(
            "board_composition",
            [
                (
                    lambda q: (
                        (
                            q.get("independent_directors", 0)
                            / max(q.get("board_size", 1), 1)
                        )
                        >= 0.50
                    ),
                    0.75,
                ),
            ],
            1.00,
        ),
        MultiplierRule(
            "board_governance", lambda q: q.get("has_board_meetings", False), 0.85, 1.30
        ),
        MultiplierRule(
            "financial_controls",
            lambda q: q.get("has_financial_audits", False),
            0.85,
            1.00,
        ),
        MultiplierRule(
            "legal_oversight",
            lambda q: q.get("has_legal_compliance_officer", False),
            0.85,
            1.15,
        ),
        MultiplierRule(
            "profitability", lambda q: q.get("is_profitable", False), 0.85, 1.15
        ),
        MultiplierRule(
            "indebtedness", lambda q: q.get("has_indebtedness", False), 1.50, 1.00
        ),
    ],
    review_triggers=[
        ReviewTrigger(
            "ipo_exposure",
            lambda q, c: q.get("is_publicly_traded", False),
            "Review required: ipo_exposure",
        ),
        ReviewTrigger(
            "covenant_breach",
            lambda q, c: (
                q.get("has_indebtedness")
                and q.get("has_breached_loan_covenants", False)
            ),
            "Review required: covenant_breach",
        ),
        ReviewTrigger(
            "high_limit",
            lambda q, c: getattr(c, "limit", 0) > HIGH_LIMIT_THRESHOLD,
            "Review required: high limit selected",
        ),
    ],
)
