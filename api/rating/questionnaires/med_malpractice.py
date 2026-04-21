from typing import Literal, Optional
from pydantic import BaseModel


MedMalpracticeService = Literal[
    "elective-hormone-therapy",
    "elective-iv-hydration-vitamin",
    "ketamine-injections-psychiatric",
    "stem-cells-injections",
    "other",
]

PolicyType = Literal["claims-made", "occurrence"]


class MedMalpracticeQuestionnaire(BaseModel):
    insurance_start_date: str
    practice_type: str
    group_practicing_year: bool
    policy_type: PolicyType
    correctional_facility_services: bool
    special_services: list[MedMalpracticeService] = []
    special_services_other: Optional[str] = None
    cosmetic_aesthetics_procedures: bool
    prescribes_controlled_substances: bool
    known_claims_circumstances: bool
    known_claims_explanation: Optional[str] = None
