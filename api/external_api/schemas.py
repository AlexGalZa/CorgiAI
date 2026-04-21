from typing import Any, Literal, Optional
from ninja import Schema
from pydantic import Field

OrganizationType = Literal["individual", "partnership", "corporation", "llc", "other"]
ProfitType = Literal["for-profit", "not-for-profit"]
BillingFrequency = Literal["annual", "monthly"]
CoverageSlug = Literal[
    "commercial-general-liability",
    "technology-errors-and-omissions",
    "cyber-liability",
    "directors-and-officers",
    "fiduciary-liability",
    "hired-and-non-owned-auto",
    "media-liability",
    "employment-practices-liability",
]


class AddressInput(Schema):
    street_address: str
    suite: Optional[str] = None
    city: str
    state: str
    zip: str


class CompanyInput(Schema):
    entity_legal_name: str
    organization_type: OrganizationType
    is_for_profit: ProfitType
    last_12_months_revenue: float
    projected_next_12_months_revenue: float
    full_time_employees: Optional[int] = None
    part_time_employees: Optional[int] = None
    business_description: str
    has_subsidiaries: bool = False
    planned_acquisitions: bool = False
    planned_acquisitions_details: Optional[str] = None
    is_technology_company: Optional[bool] = None
    federal_ein: Optional[str] = None
    business_start_date: Optional[str] = None
    estimated_payroll: Optional[float] = None
    business_address: AddressInput


class CreateQuoteInput(Schema):
    company: CompanyInput
    coverages: list[CoverageSlug] = Field(
        description="List of coverage slugs to quote. See the **Coverage Slugs** section in the docs for all supported values."
    )
    coverage_data: dict[str, Any] = Field(
        default={},
        description="Per-coverage questionnaire answers, keyed by coverage slug. See the **Coverage Questionnaires** section in the docs for the full field reference for each coverage.",
    )
    limits_retentions: dict[str, Any] = Field(
        default={},
        description="Per-coverage limits and retentions, keyed by coverage slug. See the **Limits & Retentions** section in the docs for accepted values per coverage. Omitting a coverage uses its default limits.",
    )
    billing_frequency: BillingFrequency = "annual"
    claims_history: Optional[dict[str, Any]] = Field(
        default=None,
        description='Loss and insurance history. Shape: `{"loss_history": {"has_past_claims": false}, "insurance_history": {}}`. Setting `has_past_claims: true` triggers underwriter review.',
    )
    utm_source: Optional[str] = Field(
        default=None, description="Lead source attribution: utm_source value."
    )
    utm_medium: Optional[str] = Field(
        default=None, description="Lead source attribution: utm_medium value."
    )
    utm_campaign: Optional[str] = Field(
        default=None, description="Lead source attribution: utm_campaign value."
    )
    referrer_url: Optional[str] = Field(
        default=None, description="Referrer URL at time of quote creation."
    )
    landing_page_url: Optional[str] = Field(
        default=None, description="Initial landing page URL including query string."
    )


class CompanySchema(Schema):
    entity_legal_name: str
    state: str
    last_12_months_revenue: float
    full_time_employees: Optional[int] = None
    part_time_employees: Optional[int] = None
    email: Optional[str] = None


class QuoteDetailSchema(Schema):
    quote_number: str
    status: str
    coverages: list[str]
    billing_frequency: str
    quote_amount: float
    monthly_amount: float
    total_amount: float
    total_monthly: float
    needs_review: bool
    created_at: str
    company: CompanySchema
    questionnaire: dict[str, Any]
    limits_retentions: dict[str, Any]
    custom_products: list[dict[str, Any]]
    rating_result: dict[str, Any]
    monthly_breakdown: dict[str, Any]


class QuoteListSchema(Schema):
    total: int
    limit: int
    offset: int
    results: list[QuoteDetailSchema]


class QuoteResponse(Schema):
    success: bool
    message: str
    data: Optional[QuoteDetailSchema] = None


class QuoteListResponse(Schema):
    success: bool
    message: str
    data: Optional[QuoteListSchema] = None


class PolicyDetailSchema(Schema):
    policy_number: str
    coverage_type: str
    carrier: str
    is_brokered: bool
    status: str
    effective_date: str
    expiration_date: str
    premium: float


class PolicyListSchema(Schema):
    total: int
    limit: int
    offset: int
    results: list[PolicyDetailSchema]


class PolicyResponse(Schema):
    success: bool
    message: str
    data: Optional[PolicyDetailSchema] = None


class PolicyListResponse(Schema):
    success: bool
    message: str
    data: Optional[PolicyListSchema] = None


class RedeemInviteInput(Schema):
    first_name: str
    last_name: str
    org_name: str
    email: str


class RedeemInviteData(Schema):
    api_key: str


class RedeemInviteResponse(Schema):
    success: bool
    message: str
    data: Optional[RedeemInviteData] = None
