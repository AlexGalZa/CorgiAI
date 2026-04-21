COVERAGE_TO_FORM_KEY = {
    "commercial-general-liability": "commercial_general_liability",
    "media-liability": "media_liability",
    "directors-and-officers": "directors_officers",
    "technology-errors-and-omissions": "tech_errors_omissions",
    "cyber-liability": "cyber_liability",
    "fiduciary-liability": "fiduciary_liability",
    "hired-and-non-owned-auto": "hired_non_owned_auto",
    "custom-commercial-auto": "custom_commercial_auto",
    "custom-crime": "custom_crime",
    "custom-kidnap-ransom": "custom_kidnap_ransom",
    "custom-med-malpractice": "custom_med_malpractice",
    "employment-practices-liability": "employment_practices_liability",
}

BROKERED_FORM_COVERAGE_TYPES = [
    "custom-commercial-auto",
    "custom-crime",
    "custom-kidnap-ransom",
    "custom-med-malpractice",
]

BROKERED_NO_FORM_COVERAGE_TYPES = [
    "custom-workers-comp",
    "custom-bop",
    "custom-umbrella",
    "custom-excess-liability",
]

MAX_REVENUE = 9_999_999_999_999

FILE_FIELDS = {"financial_statements", "transaction_documents", "claim_documents"}
