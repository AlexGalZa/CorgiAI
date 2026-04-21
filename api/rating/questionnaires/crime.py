from typing import Literal, Optional
from pydantic import BaseModel


HiringCheck = Literal[
    "prior-employment-verification",
    "drug-testing",
    "education-verification",
    "credit-history",
    "criminal-history",
    "none",
]

CashHandling = Literal["yes", "no", "not-applicable"]
InventoryManagement = Literal["yes", "no", "not-applicable"]

SegregationArea = Literal[
    "blank-checks-oversight",
    "purchase-order-approval",
    "vendor-approval",
    "none",
]

SpecialExposure = Literal[
    "precious-metals",
    "warehousing",
    "managed-assets",
    "high-unit-portable-inventory",
    "care-custody-client-property",
]


class CrimeQuestionnaire(BaseModel):
    hiring_process_checks: list[HiringCheck]
    segregation_cash_receipts: CashHandling
    cash_quantity: Optional[float] = None
    has_crime_losses: Optional[bool] = None
    separate_check_signer: Optional[bool] = None
    countersign_procedure: Optional[bool] = None
    property_credit_card_receipts: Optional[float] = None
    property_retail_checks: Optional[float] = None
    authority_separated: bool
    segregation_areas: list[SegregationArea]
    segregation_inventory_management: InventoryManagement
    special_exposures: list[SpecialExposure] = []
    inventory_computerized: Optional[bool] = None
    physical_inventory_count_annual: Optional[bool] = None
    software_fraud_detection: bool
    edp_authorized_documented: bool
    incoming_checks_stamped_deposit_only: Optional[bool] = None
    separate_deposit_person: bool
    separate_withdrawal_person: bool
    passwords_changed_regularly: Optional[bool] = None
