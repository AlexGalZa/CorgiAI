from decimal import Decimal
from typing import Literal, Optional, TypedDict

from ninja import Schema


class WorkersCompFormPayload(TypedDict):
    quote_number: str
    credential: str
    policy_effective_date: str
    zip_code: int
    business_legal_name: str
    entity_type: str
    fein: str
    class_code: int
    full_time_employees: int
    part_time_employees: int
    annual_payroll: Optional[str]
    year_established: Optional[int]
    current_year: str
    business_description: str


class WorkersCompWebhookSchema(Schema):
    run_id: str
    status: Literal["quoted", "declined"]
    premium_amount: Optional[Decimal] = None
    decline_reason: Optional[str] = None
    quote_url: Optional[str] = None


class SkyvernRunWebhookSchema(Schema):
    workflow_run_id: str
    status: str
    failure_reason: Optional[str] = None
