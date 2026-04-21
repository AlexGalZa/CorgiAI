from typing import Literal
from pydantic import BaseModel


CGLHazardGroup = Literal[
    "low-hazard", "moderate-hazard", "elevated-hazard", "high-hazard", "not-applicable"
]
OfficeSquareFootage = Literal[
    "up_to_2500",
    "2501_5000",
    "5001_10000",
    "10001_25000",
    "over_25000",
    "not_applicable",
]
YesNoNA = Literal["Yes", "No", "N/A"]


class CGLQuestionnaire(BaseModel):
    primary_operations_hazard: CGLHazardGroup
    is_address_primary_office: bool
    office_square_footage: OfficeSquareFootage
    has_contractual_liability: bool
    has_other_exposures: bool
    other_exposures_description: str | None = None
    has_physical_locations: bool
    physical_locations_description: str | None = None
    square_footage: int | None = None
    has_safety_measures: YesNoNA | bool
    has_hazardous_materials: bool
    hazardous_materials_description: str | None = None
    has_products_completed_operations: bool
    products_completed_operations_description: str | None = None
    has_client_site_work: bool | None = None
    client_site_work_description: str | None = None
    has_quality_control: YesNoNA | None = None
    uses_subcontractors: bool | None = None
    requires_subcontractor_insurance: bool | None = None
