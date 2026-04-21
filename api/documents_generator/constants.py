class CGLPolicyPaths:
    BASE = "pdfs/documents_generator/policy/techrrg/cgl"
    MASTER = f"{BASE}/cgl_0001_master.pdf"
    POLICY = f"{BASE}/cgl_0100_policy.pdf"
    HNOA = f"{BASE}/cgl_0101_hnoa.pdf"


class TechPolicyPaths:
    BASE = "pdfs/documents_generator/policy/techrrg/tech"
    MASTER = f"{BASE}/tech_0001_master.pdf"
    TERMS = f"{BASE}/tech_0002_terms.pdf"

    COVERAGES = f"{BASE}/coverages"
    DO = f"{COVERAGES}/tech_0100_do.pdf"
    EPL = f"{COVERAGES}/tech_0200_epl.pdf"
    FIDUCIARY = f"{COVERAGES}/tech_0300_fiduciary.pdf"
    CYBER = f"{COVERAGES}/tech_0400_cyber.pdf"
    EO = f"{COVERAGES}/tech_0500_eo.pdf"
    MEDIA = f"{COVERAGES}/tech_0600_media.pdf"

    ENDORSEMENTS = f"{BASE}/endorsements"
    AI_COVERAGE = f"{ENDORSEMENTS}/tech_0038_ai_coverage.pdf"
    EXCLUDED_SUBSIDIARY = f"{ENDORSEMENTS}/tech_0039_excluded_subsidiary.pdf"
    HIPAA_PENALTIES = f"{ENDORSEMENTS}/tech_0022_hipaa.pdf"

    EPL_ENDORSEMENTS = f"{ENDORSEMENTS}/epl"
    EPL_THIRD_PARTY_EXCLUSION = (
        f"{EPL_ENDORSEMENTS}/tech_0012_third_party_exclusion.pdf"
    )
    EPL_CA_SERVICE_SUIT = f"{EPL_ENDORSEMENTS}/tech_0015_ca_service_suit.pdf"
    EPL_NY_SERVICE_SUIT = f"{EPL_ENDORSEMENTS}/tech_0016_ny_service_suit.pdf"
    EPL_NY_ARBITRATION = f"{EPL_ENDORSEMENTS}/tech_0017_ny_arbitration.pdf"
    EPL_NY_EXTENDED_REPORTING = (
        f"{EPL_ENDORSEMENTS}/tech_0018_ny_extended_reporting.pdf"
    )


class NTICPolicyPaths:
    BASE = "pdfs/documents_generator/policy/ntic"

    CGL_BASE = f"{BASE}/cgl"
    CGL_MASTER = f"{CGL_BASE}/ntic_0001_master.pdf"
    CGL = f"{CGL_BASE}/ntic_0100_cgl.pdf"
    HNOA = f"{CGL_BASE}/ntic_1033_hnoa.pdf"

    TECH_BASE = f"{BASE}/tech"
    TECH_MASTER = f"{TECH_BASE}/ntic_0001_master.pdf"

    COVERAGES = f"{TECH_BASE}/coverages"
    CYBER = f"{COVERAGES}/ntic_0200_cyber.pdf"
    DO = f"{COVERAGES}/ntic_0300_do.pdf"
    EPL = f"{COVERAGES}/ntic_0400_epl.pdf"
    FIDUCIARY = f"{COVERAGES}/ntic_0500_fiduciary.pdf"
    MEDIA = f"{COVERAGES}/ntic_0600_media.pdf"
    EO = f"{COVERAGES}/ntic_0700_eo.pdf"

    ENDORSEMENTS = f"{TECH_BASE}/endorsements"
    CA_SERVICE_SUIT = f"{ENDORSEMENTS}/ntic_1005_ca_service_suit.pdf"
    EXCLUDED_SUBSIDIARY = f"{ENDORSEMENTS}/ntic_1013_excluded_subsidiary.pdf"
    NY_SERVICE_SUIT = f"{ENDORSEMENTS}/ntic_1019_ny_service_suit.pdf"
    PRE_CLAIM_ASSISTANCE = f"{ENDORSEMENTS}/ntic_1022_pre_claim_assistance.pdf"

    EPL_ENDORSEMENTS = f"{ENDORSEMENTS}/epl"
    EPL_THIRD_PARTY_EXCLUSION = (
        f"{EPL_ENDORSEMENTS}/ntic_1027_third_party_exclusion.pdf"
    )

    EO_ENDORSEMENTS = f"{ENDORSEMENTS}/eo"
    EO_AI_COVERAGE = f"{EO_ENDORSEMENTS}/ntic_1002_ai_coverage.pdf"


class COIPaths:
    BASE = "pdfs/documents_generator/coi"
    COI = f"{BASE}/coi_0001.pdf"


TECH_COVERAGE_CONFIG = {
    "directors-and-officers": {
        "path": TechPolicyPaths.DO,
        "name": "Directors & Officers Coverage Part",
        "form_code": "CORG-TECH-0100",
    },
    "employment-practices-liability": {
        "path": TechPolicyPaths.EPL,
        "name": "Employment Practices Liability Coverage Part",
        "form_code": "CORG-TECH-0200",
    },
    "fiduciary-liability": {
        "path": TechPolicyPaths.FIDUCIARY,
        "name": "Fiduciary Liability Coverage Part",
        "form_code": "CORG-TECH-0300",
    },
    "cyber-liability": {
        "path": TechPolicyPaths.CYBER,
        "name": "Cyber Liability Coverage Part",
        "form_code": "CORG-TECH-0400",
    },
    "technology-errors-and-omissions": {
        "path": TechPolicyPaths.EO,
        "name": "Tech E&O Coverage Part",
        "form_code": "CORG-TECH-0500",
    },
    "media-liability": {
        "path": TechPolicyPaths.MEDIA,
        "name": "Media Liability Coverage Part",
        "form_code": "CORG-TECH-0600",
    },
}

TECH_STATIC_FORMS = [
    {"name": "Master Declarations Page", "code": "CORG-TECH-0001"},
    {"name": "General Terms & Conditions", "code": "CORG-TECH-0002"},
]

TECH_EPL_ENDORSEMENTS = [
    {"name": "Third-Party Claim Exclusion Endorsement", "code": "CORG-TECH-0012"},
]

TECH_EPL_CA_ENDORSEMENTS = [
    {"name": "California Service of Suit Endorsement", "code": "CORG-TECH-0015"},
]

TECH_EPL_NY_ENDORSEMENTS = [
    {"name": "New York Service of Suit Endorsement", "code": "CORG-TECH-0016"},
    {"name": "New York Arbitration Optionality Endorsement", "code": "CORG-TECH-0017"},
    {"name": "New York Extended Reporting Period Compliance", "code": "CORG-TECH-0018"},
]

TECH_AI_COVERAGE_ENDORSEMENT = {
    "name": "Artificial Intelligence Coverage Endorsement",
    "code": "CORG-TECH-0038",
}

TECH_HIPAA_PENALTIES_ENDORSEMENT = {
    "name": "HIPAA Civil Penalty Coverage Endorsement",
    "code": "CORG-TECH-0022",
}

TECH_FINAL_ENDORSEMENTS = [
    {"name": "Excluded Subsidiary Endorsement", "code": "CORG-TECH-0039"},
]

NTIC_TECH_STATIC_FORMS = [
    {"name": "Master Declarations Page", "code": "CORG-NTIC-0001"},
]

NTIC_EPL_ENDORSEMENTS = [
    {"name": "Third-Party Claim Exclusion Endorsement", "code": "CORG-NTIC-1027"},
]

NTIC_AI_COVERAGE_ENDORSEMENT = {
    "name": "Artificial Intelligence Coverage Endorsement",
    "code": "CORG-NTIC-1002",
}

NTIC_PRE_CLAIM_ASSISTANCE_ENDORSEMENT = {
    "name": "Pre-Claim Assistance Endorsement",
    "code": "CORG-NTIC-1022",
}

NTIC_FINAL_ENDORSEMENTS = [
    {"name": "Excluded Subsidiary Endorsement", "code": "CORG-NTIC-1013"},
]

NTIC_CA_ENDORSEMENTS = [
    {"name": "California Service of Suit Endorsement", "code": "CORG-NTIC-1005"},
]

NTIC_NY_ENDORSEMENTS = [
    {"name": "New York Service of Suit Endorsement", "code": "CORG-NTIC-1019"},
]

NTIC_COVERAGE_CONFIG = {
    "commercial-general-liability": {
        "path": NTICPolicyPaths.CGL,
        "name": "Commercial General Liability Policy",
        "form_code": "CORG-NTIC-0100",
    },
    "cyber-liability": {
        "path": NTICPolicyPaths.CYBER,
        "name": "Cyber Liability Policy",
        "form_code": "CORG-NTIC-0200",
    },
    "directors-and-officers": {
        "path": NTICPolicyPaths.DO,
        "name": "Directors & Officers Liability Policy",
        "form_code": "CORG-NTIC-0300",
    },
    "employment-practices-liability": {
        "path": NTICPolicyPaths.EPL,
        "name": "Employment Practices Liability Policy",
        "form_code": "CORG-NTIC-0400",
    },
    "fiduciary-liability": {
        "path": NTICPolicyPaths.FIDUCIARY,
        "name": "Fiduciary Liability Policy",
        "form_code": "CORG-NTIC-0500",
    },
    "media-liability": {
        "path": NTICPolicyPaths.MEDIA,
        "name": "Media Liability Insurance Policy",
        "form_code": "CORG-NTIC-0600",
    },
    "technology-errors-and-omissions": {
        "path": NTICPolicyPaths.EO,
        "name": "Technology E&O Policy",
        "form_code": "CORG-NTIC-0700",
    },
}

AI_COVERAGE_PDF_MAPPING = {
    "algorithmic-bias-liability": 1,
    "ai-intellectual-property-liability": 2,
    "regulatory-investigation-defense-costs": 3,
    "hallucination-defamation-liability": 4,
    "training-data-misuse-liability": 5,
    "data-poisoning-adversarial-attack": 6,
    "service-interruption-liability": 7,
    "bodily-injury-property-damage-autonomous-ai": 8,
    "deepfake-synthetic-media-liability": 9,
    "civil-fines-penalties": 10,
}
