from typing import Literal
from pydantic import BaseModel, computed_field

CyberDataExposure = Literal[
    "stores-sensitive-data",
    "maintains-large-volume-data",
    "critical-tech-service",
]
CyberSecurityControl = Literal[
    "mfa-required",
    "backups-incident-plan",
    "security-training",
    "security-assessments",
]
CyberRegulation = Literal["none", "gdpr", "ccpa-cpra", "hipaa", "glba"]
SecurityFrameworkStatus = Literal["yes", "no", "in-progress"]
EmployeeBand = Literal[
    "under_25", "25_50", "50_250", "250_500", "500_1000", "over_1000"
]
SensitiveRecordCount = Literal["under_10k", "10k_100k", "100k_1m", "over_1m"]
RegulatorySublimit = Literal["0", "5", "10", "25", "50", "100"]
YesNoNA = Literal["Yes", "No", "N/A"]

EMPLOYEE_BAND_VALUES = {
    "under_25": 10,
    "25_50": 35,
    "50_250": 100,
    "250_500": 350,
    "500_1000": 750,
    "over_1000": 1500,
}


class CyberQuestionnaire(BaseModel):
    data_systems_exposure: list[CyberDataExposure] | None = None
    employee_band: EmployeeBand
    sensitive_record_count: SensitiveRecordCount
    all_users_have_unique_logins: bool
    security_controls: list[CyberSecurityControl] | None = None
    security_framework_certified: SecurityFrameworkStatus
    regulatory_sublimit: RegulatorySublimit
    outsources_it: bool
    requires_vendor_security: YesNoNA | None = None
    has_past_incidents: bool
    incident_details: str | None = None
    regulations_subject_to: list[CyberRegulation] | None = None
    wants_hipaa_penalties_coverage: bool | None = None
    maintained_compliance: bool
    compliance_issues_description: str | None = None

    @computed_field
    @property
    def total_employees(self) -> int:
        return EMPLOYEE_BAND_VALUES.get(self.employee_band, 10)

    @computed_field
    @property
    def security_controls_count(self) -> int:
        return len(self.security_controls or [])
