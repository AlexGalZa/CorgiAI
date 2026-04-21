from rating.schemas import (
    CoverageRatingDefinition,
    LimitRetentionConfig,
    LimitOption,
    RetentionOption,
    MultiplierRule,
    ConditionalMultiplier,
    ReviewTrigger,
)

EMPLOYEE_TIERS = [
    {"floor": 0, "ceiling": 10, "rate": 128.39, "cumulative": 1283.90},
    {"floor": 10, "ceiling": 25, "rate": 85.45, "cumulative": 2535.71},
    {"floor": 25, "ceiling": 100, "rate": 53.50, "cumulative": 6547.90},
    {"floor": 100, "ceiling": 250, "rate": 23.54, "cumulative": 10078.63},
    {"floor": 250, "ceiling": 500, "rate": 10.70, "cumulative": 12753.43},
    {"floor": 500, "ceiling": 1000, "rate": 5.35, "cumulative": 15428.23},
    {"floor": 1000, "ceiling": float("inf"), "rate": 1.07, "cumulative": None},
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
RETENTION_FACTORS = {
    5_000: 0.864,
    10_000: 0.818,
    15_000: 0.800,
    20_000: 0.782,
    25_000: 0.764,
    50_000: 0.710,
    75_000: 0.670,
    100_000: 0.640,
}

INDUSTRY_FACTORS = {
    "b2b-saas": 1.10,
    "developer-tools": 0.95,
    "fintech": 1.40,
    "healthtech": 1.35,
    "ai-ml": 1.35,
    "marketplace": 1.65,
    "gaming": 1.50,
    "social-ugc": 1.55,
    "adtech-martech": 1.25,
    "ecommerce": 1.40,
    "it-services": 1.25,
    "hardware-iot": 1.25,
    "semiconductors": 1.15,
    "cleantech": 1.30,
    "edtech": 1.20,
    "crypto-web3": 1.45,
    "consulting": 1.20,
    "eor": 2.75,
    "other": 1.25,
}

GEOGRAPHY_FACTORS = {
    "very-low": 0.75,
    "low": 0.85,
    "standard": 0.95,
    "elevated": 1.10,
    "high": 1.45,
    "very-high": 1.55,
    "extreme": 2.00,
    "international-developed": 1.35,
    "international-emerging": 1.80,
}

GEOGRAPHY_STATES = {
    "very-low": [
        "AL",
        "AR",
        "ID",
        "IN",
        "IA",
        "KS",
        "KY",
        "MS",
        "MO",
        "MT",
        "NE",
        "ND",
        "OK",
        "SD",
        "UT",
        "WV",
        "WY",
    ],
    "low": ["AK", "AZ", "GA", "LA", "ME", "MI", "MN", "NH", "NM", "SC", "TN", "VA"],
    "standard": ["CO", "FL", "MD", "NV", "NC", "OH", "OR", "PA", "TX", "VT", "WI"],
    "elevated": ["CT", "DE", "HI", "IL", "NJ", "RI", "WA"],
    "high": ["MA"],
    "very-high": ["CA", "NY"],
    "extreme": ["DC"],
}

INTERNATIONAL_COUNTRIES = {
    "international-developed": [
        "CA",
        "UK",
        "EU",
        "AU",
        "SG",
        "ISR",
        "KR",
        # Europe
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IS",
        "IE",
        "IT",
        "LV",
        "LI",
        "LT",
        "LU",
        "MT",
        "MC",
        "NL",
        "NO",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
        "CH",
        # Developed Asia-Pacific
        "JP",
        "NZ",
        "TW",
        # Other developed
        "SM",
        "AD",
    ],
    "international-emerging": [
        "IN",
        "NG",
        "LATAM",
        "AFRICA",
        "SEA",
        "AE",
        "CN",
        # Latin America
        "AR",
        "BO",
        "BR",
        "CL",
        "CO",
        "CR",
        "CU",
        "DO",
        "EC",
        "SV",
        "GT",
        "HN",
        "JM",
        "MX",
        "NI",
        "PA",
        "PY",
        "PE",
        "SR",
        "TT",
        "UY",
        "VE",
        "BZ",
        "GY",
        "AG",
        "BB",
        "BS",
        "DM",
        "GD",
        "HT",
        "KN",
        "LC",
        "VC",
        # Middle East
        "BH",
        "IQ",
        "IR",
        "JO",
        "KW",
        "LB",
        "OM",
        "PS",
        "QA",
        "SA",
        "SY",
        "YE",
        # Africa
        "DZ",
        "AO",
        "BJ",
        "BW",
        "BF",
        "BI",
        "CV",
        "CM",
        "CF",
        "TD",
        "KM",
        "CG",
        "CD",
        "CI",
        "DJ",
        "EG",
        "GQ",
        "ER",
        "SZ",
        "ET",
        "GA",
        "GM",
        "GH",
        "GN",
        "GW",
        "KE",
        "LS",
        "LR",
        "LY",
        "MG",
        "MW",
        "ML",
        "MR",
        "MU",
        "MA",
        "MZ",
        "NA",
        "NE",
        "RW",
        "ST",
        "SN",
        "SC",
        "SL",
        "SO",
        "ZA",
        "SS",
        "SD",
        "TZ",
        "TG",
        "TN",
        "UG",
        "ZM",
        "ZW",
        # Asia
        "AF",
        "BD",
        "BT",
        "BN",
        "KH",
        "IDN",
        "KZ",
        "KG",
        "LA",
        "MY",
        "MV",
        "MM",
        "MN",
        "NP",
        "KP",
        "PK",
        "PH",
        "LK",
        "TJ",
        "TH",
        "TL",
        "TM",
        "UZ",
        "VN",
        # Europe (emerging)
        "ALB",
        "AM",
        "AZ",
        "BY",
        "BA",
        "GE",
        "XK",
        "MD",
        "ME",
        "MK",
        "RS",
        "RU",
        "TR",
        "UA",
        # Oceania
        "FJ",
        "KI",
        "MH",
        "FM",
        "NR",
        "PW",
        "PG",
        "WS",
        "SB",
        "TO",
        "TV",
        "VU",
    ],
}

HR_POLICIES_FACTORS = {0: 1.30, 1: 1.15, 2: 1.00, 3: 0.85, 4: 0.70}


def get_geography_factor_from_state(state: str) -> float:
    state_upper = state.upper() if state else ""
    for group, states in GEOGRAPHY_STATES.items():
        if state_upper in states:
            return GEOGRAPHY_FACTORS[group]
    return GEOGRAPHY_FACTORS["standard"]


def get_geography_group_from_state(state: str) -> str:
    state_upper = state.upper() if state else ""
    for group, states in GEOGRAPHY_STATES.items():
        if state_upper in states:
            return group
    return "standard"


def get_geography_group_from_country(country: str) -> str:
    country_upper = country.upper() if country else ""
    for group, countries in INTERNATIONAL_COUNTRIES.items():
        if country_upper in countries:
            return group
    return "international-emerging"


def get_highest_risk_geography(
    geographic_spread: list[dict], international_spread: list[dict] | None = None
) -> str:
    risk_order = [
        "very-low",
        "low",
        "standard",
        "elevated",
        "high",
        "very-high",
        "extreme",
        "international-developed",
        "international-emerging",
    ]
    highest_risk_index = 2
    highest_risk_group = "standard"

    for item in geographic_spread or []:
        state = item.get("state", "")
        group = get_geography_group_from_state(state)
        group_index = risk_order.index(group) if group in risk_order else 2

        if group_index > highest_risk_index:
            highest_risk_index = group_index
            highest_risk_group = group

    for item in international_spread or []:
        country = item.get("country", "")
        group = get_geography_group_from_country(country)
        group_index = risk_order.index(group) if group in risk_order else 8

        if group_index > highest_risk_index:
            highest_risk_index = group_index
            highest_risk_group = group

    return highest_risk_group


DEFINITION = CoverageRatingDefinition(
    coverage_id="employment-practices-liability",
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
            "industry",
            [
                (lambda q: q.get("industry_group") == "eor", INDUSTRY_FACTORS["eor"]),
                (
                    lambda q: q.get("industry_group") == "b2b-saas",
                    INDUSTRY_FACTORS["b2b-saas"],
                ),
                (
                    lambda q: q.get("industry_group") == "developer-tools",
                    INDUSTRY_FACTORS["developer-tools"],
                ),
                (
                    lambda q: q.get("industry_group") == "fintech",
                    INDUSTRY_FACTORS["fintech"],
                ),
                (
                    lambda q: q.get("industry_group") == "healthtech",
                    INDUSTRY_FACTORS["healthtech"],
                ),
                (
                    lambda q: q.get("industry_group") == "ai-ml",
                    INDUSTRY_FACTORS["ai-ml"],
                ),
                (
                    lambda q: q.get("industry_group") == "marketplace",
                    INDUSTRY_FACTORS["marketplace"],
                ),
                (
                    lambda q: q.get("industry_group") == "gaming",
                    INDUSTRY_FACTORS["gaming"],
                ),
                (
                    lambda q: q.get("industry_group") == "social-ugc",
                    INDUSTRY_FACTORS["social-ugc"],
                ),
                (
                    lambda q: q.get("industry_group") == "adtech-martech",
                    INDUSTRY_FACTORS["adtech-martech"],
                ),
                (
                    lambda q: q.get("industry_group") == "ecommerce",
                    INDUSTRY_FACTORS["ecommerce"],
                ),
                (
                    lambda q: q.get("industry_group") == "it-services",
                    INDUSTRY_FACTORS["it-services"],
                ),
                (
                    lambda q: q.get("industry_group") == "hardware-iot",
                    INDUSTRY_FACTORS["hardware-iot"],
                ),
                (
                    lambda q: q.get("industry_group") == "semiconductors",
                    INDUSTRY_FACTORS["semiconductors"],
                ),
                (
                    lambda q: q.get("industry_group") == "cleantech",
                    INDUSTRY_FACTORS["cleantech"],
                ),
                (
                    lambda q: q.get("industry_group") == "edtech",
                    INDUSTRY_FACTORS["edtech"],
                ),
                (
                    lambda q: q.get("industry_group") == "crypto-web3",
                    INDUSTRY_FACTORS["crypto-web3"],
                ),
                (
                    lambda q: q.get("industry_group") == "consulting",
                    INDUSTRY_FACTORS["consulting"],
                ),
            ],
            INDUSTRY_FACTORS["other"],
        ),
        ConditionalMultiplier(
            "geography",
            [
                (
                    lambda q: q.get("geography_group") == "very-low",
                    GEOGRAPHY_FACTORS["very-low"],
                ),
                (lambda q: q.get("geography_group") == "low", GEOGRAPHY_FACTORS["low"]),
                (
                    lambda q: q.get("geography_group") == "standard",
                    GEOGRAPHY_FACTORS["standard"],
                ),
                (
                    lambda q: q.get("geography_group") == "elevated",
                    GEOGRAPHY_FACTORS["elevated"],
                ),
                (
                    lambda q: q.get("geography_group") == "high",
                    GEOGRAPHY_FACTORS["high"],
                ),
                (
                    lambda q: q.get("geography_group") == "very-high",
                    GEOGRAPHY_FACTORS["very-high"],
                ),
                (
                    lambda q: q.get("geography_group") == "extreme",
                    GEOGRAPHY_FACTORS["extreme"],
                ),
                (
                    lambda q: q.get("geography_group") == "international-developed",
                    GEOGRAPHY_FACTORS["international-developed"],
                ),
                (
                    lambda q: q.get("geography_group") == "international-emerging",
                    GEOGRAPHY_FACTORS["international-emerging"],
                ),
            ],
            1.00,
        ),
        ConditionalMultiplier(
            "hr_policies",
            [
                (lambda q: q.get("hr_policies_count", 0) >= 4, HR_POLICIES_FACTORS[4]),
                (lambda q: q.get("hr_policies_count", 0) == 3, HR_POLICIES_FACTORS[3]),
                (lambda q: q.get("hr_policies_count", 0) == 2, HR_POLICIES_FACTORS[2]),
                (lambda q: q.get("hr_policies_count", 0) == 1, HR_POLICIES_FACTORS[1]),
            ],
            HR_POLICIES_FACTORS[0],
        ),
        MultiplierRule(
            "salary_level",
            lambda q: q.get("average_salary_level") == "over-75k",
            1.25,
            1.00,
        ),
        MultiplierRule(
            "contractors",
            lambda q: q.get("uses_contractors") and not q.get("wants_contractor_epli"),
            1.10,
            1.00,
        ),
        MultiplierRule(
            "past_layoffs", lambda q: q.get("has_past_layoffs", False), 1.20, 0.80
        ),
        MultiplierRule(
            "planned_layoffs", lambda q: q.get("has_planned_layoffs", False), 1.20, 0.80
        ),
        MultiplierRule(
            "hourly_employees",
            lambda q: q.get("has_hourly_employees", False),
            1.25,
            1.00,
        ),
        ConditionalMultiplier(
            "third_party_exposure",
            [
                (lambda q: not q.get("has_third_party_interaction", False), 1.00),
                (
                    lambda q: (
                        q.get("has_third_party_interaction")
                        and q.get("has_third_party_training")
                    ),
                    1.00,
                ),
                (
                    lambda q: (
                        q.get("has_third_party_interaction")
                        and not q.get("has_third_party_training")
                    ),
                    1.25,
                ),
            ],
            1.00,
        ),
    ],
    review_triggers=[
        ReviewTrigger(
            "dc_location",
            lambda q, c: any(
                item.get("state") == "DC" for item in (q.get("geographic_spread") or [])
            ),
            "Review required: dc_location",
        ),
        ReviewTrigger(
            "high_limit",
            lambda q, c: getattr(c, "limit", 0) > HIGH_LIMIT_THRESHOLD,
            "Review required: high limit selected",
        ),
        ReviewTrigger(
            "past_claims",
            lambda q, c: q.get("has_past_claims", False),
            "Review required: past_claims",
        ),
    ],
)
