from typing import Literal
from pydantic import BaseModel, computed_field

BenefitPlanType = Literal["401k", "pension", "health", "welfare", "other"]
ReviewFrequency = Literal["annually", "every-2-years", "every-3-years", "other"]
PlanAssetBand = Literal[
    "under_100k", "100k_500k", "500k_1m", "1m_5m", "5m_25m", "25m_100m", "over_100m"
]

PLAN_ASSET_BAND_VALUES: dict[str, float] = {
    "under_100k": 50_000,
    "100k_500k": 300_000,
    "500k_1m": 750_000,
    "1m_5m": 3_000_000,
    "5m_25m": 15_000_000,
    "25m_100m": 62_500_000,
    "over_100m": 150_000_000,
}


class FiduciaryQuestionnaire(BaseModel):
    benefit_plan_types: list[BenefitPlanType]
    benefit_plan_other_description: str | None = None
    total_plan_assets: PlanAssetBand
    has_defined_benefit_plan: bool
    defined_benefit_funding_percent: float | None = None
    has_company_stock_in_plan: bool
    company_stock_details: str | None = None
    recordkeeper: str | None = None
    third_party_admin: str | None = None
    custodian: str | None = None
    investment_advisor: str | None = None
    benefits_broker: str | None = None
    actuary: str | None = None
    has_written_agreements: bool
    review_frequency: ReviewFrequency
    review_frequency_other: str | None = None
    has_regulatory_issues: bool
    has_significant_changes: bool
    compliance_issues_description: str | None = None
    has_fiduciary_committee: bool
    has_fiduciary_training: bool
    has_past_claims: bool
    past_claims_details: str | None = None

    @computed_field
    @property
    def has_recordkeeper(self) -> bool:
        return bool(self.recordkeeper)

    @computed_field
    @property
    def has_third_party_admin(self) -> bool:
        return bool(self.third_party_admin)

    @computed_field
    @property
    def has_custodian(self) -> bool:
        return bool(self.custodian)

    @computed_field
    @property
    def has_investment_advisor(self) -> bool:
        return bool(self.investment_advisor)

    @computed_field
    @property
    def has_benefits_broker(self) -> bool:
        return bool(self.benefits_broker)

    @computed_field
    @property
    def has_actuary(self) -> bool:
        return bool(self.actuary)

    @computed_field
    @property
    def service_provider_count(self) -> int:
        return sum(
            [
                self.has_recordkeeper,
                self.has_third_party_admin,
                self.has_custodian,
                self.has_investment_advisor,
                self.has_benefits_broker,
                self.has_actuary,
            ]
        )

    @computed_field
    @property
    def total_plan_assets_value(self) -> float:
        return PLAN_ASSET_BAND_VALUES.get(self.total_plan_assets, 0)
