CGL_COVERAGE = "commercial-general-liability"
HNOA_COVERAGE = "hired-and-non-owned-auto"
COMMERCIAL_AUTO_COVERAGE = "custom-commercial-auto"
EPL_COVERAGE = "employment-practices-liability"
DO_COVERAGE = "directors-and-officers"
FIDUCIARY_COVERAGE = "fiduciary-liability"
CYBER_COVERAGE = "cyber-liability"
EO_COVERAGE = "technology-errors-and-omissions"
MEDIA_COVERAGE = "media-liability"

COVERAGE_DISPLAY_NAMES = {
    "commercial-general-liability": "Commercial General Liability",
    "cyber-liability": "Cyber Liability",
    "directors-and-officers": "Directors & Officers Liability",
    "employment-practices-liability": "Employment Practices Liability",
    "fiduciary-liability": "Fiduciary Liability",
    "hired-and-non-owned-auto": "Hired & Non-Owned Auto Liability",
    "custom-commercial-auto": "Commercial Auto",
    "media-liability": "Media Liability",
    "technology-errors-and-omissions": "Tech E&O",
    "custom-workers-comp": "Workers Compensation",
    "custom-bop": "Business Owners Policy",
    "custom-umbrella": "Umbrella",
    "custom-excess-liability": "Excess Liability",
    "custom-crime": "Crime Insurance",
    "custom-fidelity": "Fidelity Bond",
    "custom-kidnap-ransom": "Kidnap & Ransom",
    "custom-med-malpractice": "Medical Malpractice",
}

ALL_COVERAGES = [
    CGL_COVERAGE,
    DO_COVERAGE,
    EO_COVERAGE,
    CYBER_COVERAGE,
    FIDUCIARY_COVERAGE,
    HNOA_COVERAGE,
    COMMERCIAL_AUTO_COVERAGE,
    MEDIA_COVERAGE,
    EPL_COVERAGE,
]

TECHRRG_CARRIER = "Technology Risk Retention Group, Inc."
TECHRRG_NAIC_CODE = "17763"

NTIC_CARRIER = "National Technology Insurance Company Inc"
NTIC_NAIC_CODE = ""
NTIC_LIMIT_THRESHOLD = 2_000_000
MAX_SELF_SERVE_LIMIT = 5_000_000

STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "AS": "American Samoa",
    "GU": "Guam",
    "MP": "Northern Mariana Islands",
    "PR": "Puerto Rico",
    "VI": "U.S. Virgin Islands",
}

ADMIN_FEE_RATE = "0.22"
ADMIN_FEE_RECIPIENT = "Corgi Administration, LLC"
COLLECTOR_ENTITY = "Corgi Insurance Services, Inc."

CORGI_SIGNATURE_HEADER = "X-Corgi-Signature"

DEFAULT_TREATY_ID = "XOL-2026-01"
DEFAULT_REINSURANCE_TYPE = "XOL"
DEFAULT_ATTACHMENT_POINT = "250000.00"
DEFAULT_CEDED_PREMIUM_RATE = "0.2830"
DEFAULT_REINSURER_NAME = "Corgi Reinsurance"
