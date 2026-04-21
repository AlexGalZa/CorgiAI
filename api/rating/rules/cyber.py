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

RATE_TIERS = [
    {"revenue": 0, "group1": 0.00104130, "group2": 0.00122506, "group3": 0.00139058},
    {
        "revenue": 500_000,
        "group1": 0.00104130,
        "group2": 0.00122506,
        "group3": 0.00139058,
    },
    {
        "revenue": 1_000_000,
        "group1": 0.00101166,
        "group2": 0.00119020,
        "group3": 0.00135100,
    },
    {
        "revenue": 2_500_000,
        "group1": 0.00092868,
        "group2": 0.00116086,
        "group3": 0.00131942,
    },
    {
        "revenue": 5_000_000,
        "group1": 0.00073268,
        "group2": 0.00091652,
        "group3": 0.00104130,
    },
    {
        "revenue": 7_500_000,
        "group1": 0.00068438,
        "group2": 0.00085564,
        "group3": 0.00097234,
    },
    {
        "revenue": 10_000_000,
        "group1": 0.00063682,
        "group2": 0.00079604,
        "group3": 0.00090458,
    },
    {
        "revenue": 15_000_000,
        "group1": 0.00059146,
        "group2": 0.00073896,
        "group3": 0.00083972,
    },
    {
        "revenue": 25_000_000,
        "group1": 0.00054694,
        "group2": 0.00068322,
        "group3": 0.00077638,
    },
    {
        "revenue": 50_000_000,
        "group1": 0.00046986,
        "group2": 0.00058786,
        "group3": 0.00066790,
    },
    {
        "revenue": 75_000_000,
        "group1": 0.00042446,
        "group2": 0.00053128,
        "group3": 0.00060356,
    },
    {
        "revenue": 100_000_000,
        "group1": 0.00039250,
        "group2": 0.00049140,
        "group3": 0.00055824,
    },
    {
        "revenue": 250_000_000,
        "group1": 0.00034146,
        "group2": 0.00042738,
        "group3": 0.00048590,
    },
]

BASE_RATES = BaseRateTable(
    entries={
        "500000_group1": BaseRateEntry(key="500000_group1", rate=0.00104130),
        "500000_group2": BaseRateEntry(key="500000_group2", rate=0.00122506),
        "500000_group3": BaseRateEntry(key="500000_group3", rate=0.00139058),
        "1000000_group1": BaseRateEntry(key="1000000_group1", rate=0.00101166),
        "1000000_group2": BaseRateEntry(key="1000000_group2", rate=0.00119020),
        "1000000_group3": BaseRateEntry(key="1000000_group3", rate=0.00135100),
        "2500000_group1": BaseRateEntry(key="2500000_group1", rate=0.00092868),
        "2500000_group2": BaseRateEntry(key="2500000_group2", rate=0.00116086),
        "2500000_group3": BaseRateEntry(key="2500000_group3", rate=0.00131942),
        "5000000_group1": BaseRateEntry(key="5000000_group1", rate=0.00073268),
        "5000000_group2": BaseRateEntry(key="5000000_group2", rate=0.00091652),
        "5000000_group3": BaseRateEntry(key="5000000_group3", rate=0.00104130),
        "7500000_group1": BaseRateEntry(key="7500000_group1", rate=0.00068438),
        "7500000_group2": BaseRateEntry(key="7500000_group2", rate=0.00085564),
        "7500000_group3": BaseRateEntry(key="7500000_group3", rate=0.00097234),
        "10000000_group1": BaseRateEntry(key="10000000_group1", rate=0.00063682),
        "10000000_group2": BaseRateEntry(key="10000000_group2", rate=0.00079604),
        "10000000_group3": BaseRateEntry(key="10000000_group3", rate=0.00090458),
        "15000000_group1": BaseRateEntry(key="15000000_group1", rate=0.00059146),
        "15000000_group2": BaseRateEntry(key="15000000_group2", rate=0.00073896),
        "15000000_group3": BaseRateEntry(key="15000000_group3", rate=0.00083972),
        "25000000_group1": BaseRateEntry(key="25000000_group1", rate=0.00054694),
        "25000000_group2": BaseRateEntry(key="25000000_group2", rate=0.00068322),
        "25000000_group3": BaseRateEntry(key="25000000_group3", rate=0.00077638),
        "50000000_group1": BaseRateEntry(key="50000000_group1", rate=0.00046986),
        "50000000_group2": BaseRateEntry(key="50000000_group2", rate=0.00058786),
        "50000000_group3": BaseRateEntry(key="50000000_group3", rate=0.00066790),
        "75000000_group1": BaseRateEntry(key="75000000_group1", rate=0.00042446),
        "75000000_group2": BaseRateEntry(key="75000000_group2", rate=0.00053128),
        "75000000_group3": BaseRateEntry(key="75000000_group3", rate=0.00060356),
        "100000000_group1": BaseRateEntry(key="100000000_group1", rate=0.00039250),
        "100000000_group2": BaseRateEntry(key="100000000_group2", rate=0.00049140),
        "100000000_group3": BaseRateEntry(key="100000000_group3", rate=0.00055824),
        "250000000_group1": BaseRateEntry(key="250000000_group1", rate=0.00034146),
        "250000000_group2": BaseRateEntry(key="250000000_group2", rate=0.00042738),
        "250000000_group3": BaseRateEntry(key="250000000_group3", rate=0.00048590),
    }
)

LIMIT_FACTORS = {
    500_000: 0.607,
    1_000_000: 0.818,
    1_500_000: 0.968,
    2_000_000: 1.441,
    3_000_000: 1.900,
    4_000_000: 2.250,
    5_000_000: 2.600,
    10_000_000: 4.200,
}
HIGH_LIMIT_THRESHOLD = 5_000_000
RETENTION_FACTORS = {
    10_000: 0.890,
    20_000: 0.875,
    30_000: 0.869,
    40_000: 0.864,
    50_000: 0.858,
    60_000: 0.855,
}
RECORD_COUNT_FACTORS = {
    "under_10k": 1.00,
    "10k_100k": 1.10,
    "100k_1m": 1.30,
    "over_1m": 1.50,
}
EMPLOYEE_FACTORS = {
    "under_25": 0.80,
    "25_50": 0.90,
    "50_250": 1.00,
    "250_500": 1.25,
    "500_1000": 1.50,
    "over_1000": None,
}
REGULATORY_SUBLIMIT_FACTORS = {
    "0": 0.80,
    "5": 0.825,
    "10": 0.85,
    "25": 0.875,
    "50": 0.90,
    "100": 1.00,
}


def get_security_controls_factor(questionnaire: dict) -> float:
    controls = questionnaire.get("security_controls", []) or []
    count = len(controls)
    return min(1.5 ** (6 - count), 4.0)


def get_regulations_factor(questionnaire: dict) -> float:
    regulations = questionnaire.get("regulations_subject_to", []) or []
    actual_regulations = [r for r in regulations if r != "none"]
    return 1.5 ** len(actual_regulations)


DEFINITION = CoverageRatingDefinition(
    coverage_id="cyber-liability",
    limits_retentions=LimitRetentionConfig(
        aggregate_limits=[LimitOption(v, LIMIT_FACTORS[v]) for v in LIMIT_FACTORS],
        per_occurrence_limits=[
            LimitOption(500_000, 0.607),
            LimitOption(1_000_000, 0.818),
            LimitOption(2_000_000, 1.441),
            LimitOption(3_000_000, 1.9),
            LimitOption(4_000_000, 2.250),
            LimitOption(5_000_000, 2.6),
            LimitOption(10_000_000, 4.2),
        ],
        retentions=[
            RetentionOption(v, RETENTION_FACTORS[v]) for v in sorted(RETENTION_FACTORS)
        ],
    ),
    base_rate_table=BASE_RATES,
    multiplier_rules=[
        ConditionalMultiplier(
            "employee_band",
            [
                (
                    lambda q: q.get("employee_band") == "under_25",
                    EMPLOYEE_FACTORS["under_25"],
                ),
                (
                    lambda q: q.get("employee_band") == "25_50",
                    EMPLOYEE_FACTORS["25_50"],
                ),
                (
                    lambda q: q.get("employee_band") == "50_250",
                    EMPLOYEE_FACTORS["50_250"],
                ),
                (
                    lambda q: q.get("employee_band") == "250_500",
                    EMPLOYEE_FACTORS["250_500"],
                ),
                (
                    lambda q: q.get("employee_band") == "500_1000",
                    EMPLOYEE_FACTORS["500_1000"],
                ),
            ],
            1.00,
        ),
        ConditionalMultiplier(
            "sensitive_record_count",
            [
                (
                    lambda q: q.get("sensitive_record_count") == "under_10k",
                    RECORD_COUNT_FACTORS["under_10k"],
                ),
                (
                    lambda q: q.get("sensitive_record_count") == "10k_100k",
                    RECORD_COUNT_FACTORS["10k_100k"],
                ),
                (
                    lambda q: q.get("sensitive_record_count") == "100k_1m",
                    RECORD_COUNT_FACTORS["100k_1m"],
                ),
                (
                    lambda q: q.get("sensitive_record_count") == "over_1m",
                    RECORD_COUNT_FACTORS["over_1m"],
                ),
            ],
            1.00,
        ),
        ConditionalMultiplier(
            "regulatory_sublimit",
            [
                (
                    lambda q: q.get("regulatory_sublimit") == "0",
                    REGULATORY_SUBLIMIT_FACTORS["0"],
                ),
                (
                    lambda q: q.get("regulatory_sublimit") == "5",
                    REGULATORY_SUBLIMIT_FACTORS["5"],
                ),
                (
                    lambda q: q.get("regulatory_sublimit") == "10",
                    REGULATORY_SUBLIMIT_FACTORS["10"],
                ),
                (
                    lambda q: q.get("regulatory_sublimit") == "25",
                    REGULATORY_SUBLIMIT_FACTORS["25"],
                ),
                (
                    lambda q: q.get("regulatory_sublimit") == "50",
                    REGULATORY_SUBLIMIT_FACTORS["50"],
                ),
                (
                    lambda q: q.get("regulatory_sublimit") == "100",
                    REGULATORY_SUBLIMIT_FACTORS["100"],
                ),
            ],
            1.00,
        ),
        ConditionalMultiplier(
            "security_framework",
            [
                (lambda q: q.get("security_framework_certified") == "yes", 0.80),
                (
                    lambda q: q.get("security_framework_certified") == "in-progress",
                    1.00,
                ),
                (lambda q: q.get("security_framework_certified") == "no", 1.50),
            ],
            1.00,
        ),
        ConditionalMultiplier(
            "third_party_exposure",
            [
                (lambda q: not q.get("outsources_it", False), 1.00),
                (
                    lambda q: (
                        q.get("outsources_it")
                        and q.get("requires_vendor_security") == "Yes"
                    ),
                    1.00,
                ),
                (
                    lambda q: (
                        q.get("outsources_it")
                        and q.get("requires_vendor_security") == "N/A"
                    ),
                    1.05,
                ),
                (
                    lambda q: (
                        q.get("outsources_it")
                        and q.get("requires_vendor_security") == "No"
                    ),
                    1.50,
                ),
            ],
            1.00,
        ),
        MultiplierRule(
            "compliance_history",
            lambda q: q.get("maintained_compliance", False),
            1.50,
            1.00,
        ),
        MultiplierRule(
            "hipaa_penalties_coverage",
            lambda q: q.get("wants_hipaa_penalties_coverage", False),
            1.20,
            1.00,
        ),
    ],
    review_triggers=[
        ReviewTrigger(
            "previous_incidents",
            lambda q, c: q.get("has_past_incidents", False),
            "Review required: previous_incidents",
        ),
        ReviewTrigger(
            "large_employee_count",
            lambda q, c: q.get("employee_band") == "over_1000",
            "Review required: large_employee_count",
        ),
        ReviewTrigger(
            "high_limit",
            lambda q, c: getattr(c, "limit", 0) > HIGH_LIMIT_THRESHOLD,
            "Review required: high limit selected",
        ),
    ],
)
