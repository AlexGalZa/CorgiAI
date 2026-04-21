from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, Any, List
from ninja import Schema, Field
from quotes.models import Quote
from quotes.constants import MAX_REVENUE
from common.schemas import FrontendDate


@dataclass
class CoverageBreakdown:
    premium: float
    breakdown: str


@dataclass
class ReviewReason:
    coverage: str
    reason: str


@dataclass
class RatingResult:
    success: bool
    total_premium: Optional[Decimal] = None
    breakdown: Optional[Dict[str, CoverageBreakdown]] = None
    review_reasons: Optional[List[ReviewReason]] = None


@dataclass
class StoredRatingResult:
    success: bool
    total_premium: Optional[float] = None
    breakdown: Optional[Dict[str, CoverageBreakdown]] = None
    review_reasons: Optional[List[ReviewReason]] = None
    calculated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "total_premium": self.total_premium,
            "breakdown": {
                k: {"premium": v.premium, "breakdown": v.breakdown}
                for k, v in (self.breakdown or {}).items()
            }
            if self.breakdown
            else None,
            "review_reasons": [
                {"coverage": r.coverage, "reason": r.reason}
                for r in (self.review_reasons or [])
            ]
            if self.review_reasons
            else None,
            "calculated_at": self.calculated_at,
        }

    @classmethod
    def from_rating_result(
        cls, result: "RatingResult", calculated_at: str
    ) -> "StoredRatingResult":
        return cls(
            success=result.success,
            total_premium=float(result.total_premium) if result.total_premium else None,
            breakdown=result.breakdown,
            review_reasons=result.review_reasons,
            calculated_at=calculated_at,
        )


class FinancialDetailsSchema(Schema):
    last_12_months_revenue: float = Field(..., ge=0, le=MAX_REVENUE)
    projected_next_12_months_revenue: float = Field(..., ge=0, le=MAX_REVENUE)
    full_time_employees: Optional[int] = None
    part_time_employees: Optional[int] = None
    funding_raised: Optional[float] = None
    funding_date: Optional[FrontendDate] = None


class CompanyInfoSchema(Schema):
    financial_details: FinancialDetailsSchema
    business_address: Dict[str, Any]
    organization_info: Dict[str, Any]
    structure_operations: Dict[str, Any]


class UtmAttributionSchema(Schema):
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    referrer_url: Optional[str] = None
    landing_page_url: Optional[str] = None


class QuoteCreateSchema(Schema):
    company_info: CompanyInfoSchema
    coverages: List[str]
    limits_retentions: Dict[str, Any]
    billing_frequency: str = "annual"
    promo_code: Optional[str] = None
    referral_code: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    referrer_url: Optional[str] = None
    landing_page_url: Optional[str] = None
    claims_history: Optional[Dict[str, Any]] = None
    notices_signatures: Optional[Dict[str, Any]] = None
    cyber_liability: Optional[Dict[str, Any]] = None
    directors_officers: Optional[Dict[str, Any]] = None
    tech_errors_omissions: Optional[Dict[str, Any]] = None
    commercial_general_liability: Optional[Dict[str, Any]] = None
    fiduciary_liability: Optional[Dict[str, Any]] = None
    hired_non_owned_auto: Optional[Dict[str, Any]] = None
    media_liability: Optional[Dict[str, Any]] = None
    representations_warranties: Optional[Dict[str, Any]] = None
    employment_practices_liability: Optional[Dict[str, Any]] = None
    custom_commercial_auto: Optional[Dict[str, Any]] = None
    custom_crime: Optional[Dict[str, Any]] = None
    custom_kidnap_ransom: Optional[Dict[str, Any]] = None
    custom_med_malpractice: Optional[Dict[str, Any]] = None


class MoveQuoteSchema(Schema):
    organization_id: int


class DraftQuoteCreateSchema(Schema):
    coverages: List[str]
    selected_package: Optional[str] = None


class CheckoutRequestSchema(Schema):
    billing_frequency: str = "monthly"
    effective_date: Optional[FrontendDate] = None
    coverages: Optional[List[str]] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class StepSaveSchema(Schema):
    step_id: str
    data: Dict[str, Any]
    next_step: Optional[str] = None


class DraftQuoteResponseSchema(Schema):
    quote_number: str
    status: str
    completed_steps: List[str]
    current_step: Optional[str] = None


class CoverageBreakdownSchema(Schema):
    premium: float
    breakdown: str


class ReviewReasonSchema(Schema):
    coverage: str
    reason: str


class RatingResultSchema(Schema):
    success: bool
    total_premium: Optional[float] = None
    breakdown: Optional[Dict[str, CoverageBreakdownSchema]] = None
    review_reasons: Optional[List[ReviewReasonSchema]] = None


class CustomProductSchema(Schema):
    id: str
    name: str
    product_type: str
    per_occurrence_limit: Optional[int] = None
    aggregate_limit: Optional[int] = None
    retention: Optional[int] = None
    price: float


class QuoteResponseSchema(Schema):
    id: int
    quote_number: str
    status: str
    coverages: List[str]
    created_at: str
    quote_amount: Optional[float] = None
    monthly_amount: Optional[float] = None
    custom_products: List[CustomProductSchema] = []
    custom_products_total: float = 0
    custom_products_monthly: float = 0
    total_amount: float = 0
    total_monthly: float = 0
    needs_review: bool = False
    rating_result: Optional[RatingResultSchema] = None

    @staticmethod
    def from_quote(
        quote: Quote,
        rating_result: RatingResult = None,
    ):
        result_schema = None
        needs_review = False
        if rating_result:
            needs_review = not rating_result.success
            result_schema = RatingResultSchema(
                success=rating_result.success,
                total_premium=float(rating_result.total_premium)
                if rating_result.total_premium
                else None,
                breakdown={
                    k: CoverageBreakdownSchema(premium=v.premium, breakdown=v.breakdown)
                    for k, v in (rating_result.breakdown or {}).items()
                }
                if rating_result.breakdown
                else None,
                review_reasons=[
                    ReviewReasonSchema(coverage=r.coverage, reason=r.reason)
                    for r in (rating_result.review_reasons or [])
                ]
                if rating_result.review_reasons
                else None,
            )

        quote_amount = float(quote.quote_amount) if quote.quote_amount else 0
        monthly_amount = quote_amount / 12 if quote_amount else 0

        custom_products = [
            CustomProductSchema(
                id=f"custom-{p.id}",
                name=p.name,
                product_type=p.product_type,
                per_occurrence_limit=p.per_occurrence_limit,
                aggregate_limit=p.aggregate_limit,
                retention=p.retention,
                price=float(p.price),
            )
            for p in quote.custom_products.all()
        ]
        custom_products_total = sum(p.price for p in custom_products)
        custom_products_monthly = custom_products_total / 12

        return QuoteResponseSchema(
            id=quote.id,
            quote_number=quote.quote_number,
            status=quote.status,
            coverages=quote.coverages,
            created_at=quote.created_at.isoformat(),
            quote_amount=quote_amount,
            monthly_amount=monthly_amount,
            custom_products=custom_products,
            custom_products_total=custom_products_total,
            custom_products_monthly=custom_products_monthly,
            total_amount=quote_amount + custom_products_total,
            total_monthly=monthly_amount + custom_products_monthly,
            needs_review=needs_review,
            rating_result=result_schema,
        )
