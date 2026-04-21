from typing import Literal
from pydantic import BaseModel, computed_field

EPLSalaryLevel = Literal["under-75k", "over-75k"]
EPLHRPolicy = Literal["handbook", "training", "reporting", "dedicated-hr"]


class GeographicSpreadItem(BaseModel):
    state: str
    employee_count: int


class InternationalSpreadItem(BaseModel):
    country: str
    employee_count: int


class EPLQuestionnaire(BaseModel):
    geographic_spread: list[GeographicSpreadItem] | None = None
    international_spread: list[InternationalSpreadItem] | None = None
    average_salary_level: EPLSalaryLevel
    uses_contractors: bool
    wants_contractor_epli: bool | None = None
    contractor_geographic_spread: list[GeographicSpreadItem] | None = None
    contractor_international_spread: list[InternationalSpreadItem] | None = None
    has_past_layoffs: bool
    past_layoff_details: str | None = None
    has_planned_layoffs: bool
    planned_layoff_details: str | None = None
    hr_policies: list[EPLHRPolicy] | None = None
    has_hourly_employees: bool
    is_wage_compliant: bool | None = None
    has_third_party_interaction: bool
    has_third_party_training: bool | None = None

    @computed_field
    @property
    def hr_policies_count(self) -> int:
        return len(self.hr_policies or [])

    @computed_field
    @property
    def total_employees_us(self) -> int:
        return sum(item.employee_count for item in (self.geographic_spread or []))

    @computed_field
    @property
    def total_employees_international(self) -> int:
        return sum(item.employee_count for item in (self.international_spread or []))

    @computed_field
    @property
    def total_employees(self) -> int:
        return self.total_employees_us + self.total_employees_international

    @computed_field
    @property
    def total_contractors_us(self) -> int:
        return sum(
            item.employee_count for item in (self.contractor_geographic_spread or [])
        )

    @computed_field
    @property
    def total_contractors_international(self) -> int:
        return sum(
            item.employee_count for item in (self.contractor_international_spread or [])
        )

    @computed_field
    @property
    def total_contractors(self) -> int:
        return self.total_contractors_us + self.total_contractors_international
