"""
Pydantic schemas for the Admin API.

Defines request/response models for analytics, quote actions,
policy actions, audit log, form management, and Shepherd pipeline endpoints.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from ninja import Schema
from pydantic import Field


# ── Shepherd Pipeline Responses ──────────────────────────────────────


class PipelineRow(Schema):
    """One open quote, annotated with closeability + next-best-action."""

    quote_id: int
    quote_number: str
    company_name: str
    customer_email: str
    customer_name: str
    status: str = Field(..., description="Quote status (draft/submitted/needs_review/quoted)")
    premium: Optional[Decimal] = None
    billing_frequency: str
    days_since_update: int
    days_until_expiry: Optional[int] = Field(
        None, description="Days until quote expires (only set for status='quoted')"
    )
    next_action: str = Field(
        ...,
        description=(
            "Recommended next action: send_followup | send_expiry_warning | "
            "review_underwriting | awaiting_rating | none"
        ),
    )
    closeability_score: int = Field(
        ..., description="0-200 ranking heuristic; higher means closer to closing"
    )
    updated_at: datetime
    quoted_at: Optional[datetime] = None


class PipelineListResponse(Schema):
    items: list[PipelineRow] = Field(default_factory=list)
    total: int = 0


class PipelineFollowUpResponse(Schema):
    quote_number: str
    sent_to: str
    subject: str


# ── Analytics Responses ──────────────────────────────────────────────


class PipelineStatusCount(Schema):
    """Count of quotes in each pipeline status."""

    status: str = Field(
        ..., description="Quote status (draft, submitted, quoted, etc.)"
    )
    count: int = Field(..., description="Number of quotes in this status")


class PipelineAnalyticsResponse(Schema):
    """Aggregated pipeline status counts across all quotes."""

    statuses: list[PipelineStatusCount] = Field(default_factory=list)
    total: int = Field(0, description="Total quotes across all statuses")


class CarrierPremium(Schema):
    """Premium aggregated by insurance carrier."""

    carrier: str = Field(..., description="Carrier name")
    total_premium: Decimal = Field(..., description="Sum of premiums for this carrier")
    policy_count: int = Field(..., description="Number of policies with this carrier")


class PremiumByCarrierResponse(Schema):
    """Premium breakdown by carrier."""

    carriers: list[CarrierPremium] = Field(default_factory=list)


class CoverageCount(Schema):
    """Count of policies per coverage type."""

    coverage_type: str = Field(..., description="Coverage slug")
    display_name: str = Field(..., description="Human-readable coverage name")
    count: int = Field(..., description="Number of active policies")


class CoverageBreakdownItem(Schema):
    """Count and premium of policies per coverage type."""

    coverage_type: str = Field(..., description="Coverage slug")
    display_name: str = Field(..., description="Human-readable coverage name")
    count: int = Field(..., description="Number of active policies")
    total_premium: Decimal = Field(
        Decimal("0"), description="Sum of premiums for this coverage type"
    )


class CoverageBreakdownResponse(Schema):
    """Active policy counts grouped by coverage type."""

    coverages: list[CoverageBreakdownItem] = Field(default_factory=list)


class PolicyStatsResponse(Schema):
    """High-level policy statistics."""

    active_count: int = Field(0, description="Number of active policies")
    total_premium: Decimal = Field(
        Decimal("0"), description="Sum of all active policy premiums"
    )
    average_premium: Decimal = Field(
        Decimal("0"), description="Average premium per active policy"
    )


class ClaimsStatusCount(Schema):
    """Count of claims by status."""

    status: str
    count: int


class ClaimsSummaryResponse(Schema):
    """Claims summary with financial totals."""

    by_status: list[ClaimsStatusCount] = Field(default_factory=list)
    total_reserves: Decimal = Field(
        Decimal("0"), description="Sum of case reserves (loss + LAE)"
    )
    total_paid: Decimal = Field(Decimal("0"), description="Sum of paid losses + LAE")


class ActionItem(Schema):
    """A single action item requiring admin attention."""

    type: str = Field(..., description="Item type: blocker | expiring | pending")
    title: str
    description: str
    quote_number: Optional[str] = None
    policy_number: Optional[str] = None
    due_date: Optional[date] = None


class ActionItemsResponse(Schema):
    """Pending action items for the admin dashboard."""

    items: list[ActionItem] = Field(default_factory=list)
    total: int = Field(0)


class MonthlyPremiumPoint(Schema):
    """Single data point in a monthly premium time series."""

    month: str = Field(..., description="YYYY-MM format")
    premium: Decimal


class MonthlyPremiumResponse(Schema):
    """Monthly premium time series for charting."""

    data: list[MonthlyPremiumPoint] = Field(default_factory=list)


class LossRatioResponse(Schema):
    """Loss ratio = paid losses / earned premium."""

    earned_premium: Decimal = Field(Decimal("0"))
    paid_losses: Decimal = Field(Decimal("0"))
    loss_ratio: Optional[Decimal] = Field(
        None, description="Ratio as decimal (0.45 = 45%)"
    )


# ── Pipeline Velocity (V3 #43) ───────────────────────────────────────


class StageVelocity(Schema):
    """Velocity metrics for a single pipeline stage."""

    stage: str
    display: str
    avg_days: Optional[float] = None
    count: int = 0


class ConversionRates(Schema):
    """Stage-to-stage conversion rates."""

    submitted_to_quoted: Optional[float] = None
    quoted_to_purchased: Optional[float] = None
    submitted_to_purchased: Optional[float] = None
    decline_rate: Optional[float] = None


class PipelineVelocityResponse(Schema):
    """Full pipeline velocity report."""

    stage_velocity: list[StageVelocity] = Field(default_factory=list)
    conversion_rates: ConversionRates = Field(default_factory=ConversionRates)
    pipeline_value: float = 0.0
    total_quotes: int = 0
    purchased_count: int = 0
    open_quotes: int = 0
    avg_open_age_days: Optional[float] = None
    stage_counts: dict[str, int] = Field(default_factory=dict)


# ── Customer Retention / Churn (V3 #44) ─────────────────────────────


class MonthlyRenewalRate(Schema):
    """Renewal rate for a single month."""

    month: str
    eligible_renewals: int = 0
    renewed: int = 0
    renewal_rate: Optional[float] = None


class ChurnReason(Schema):
    """Churn breakdown by cancellation reason."""

    reason: str
    count: int
    percentage: Optional[float] = None


class CohortRetention(Schema):
    """Cohort of customers by signup month and their retention status."""

    cohort_month: str
    total: int
    retained: int
    churned: int
    retention_rate: Optional[float] = None


class RetentionReportResponse(Schema):
    """Full customer retention/churn report."""

    renewal_rates: list[MonthlyRenewalRate] = Field(default_factory=list)
    churn_reasons: list[ChurnReason] = Field(default_factory=list)
    revenue_retention_rate: Optional[float] = None
    cohort_analysis: list[CohortRetention] = Field(default_factory=list)
    overall_renewal_rate: Optional[float] = None
    total_eligible: int = 0
    total_renewed: int = 0


# ── Broker Performance (V3 #45) ──────────────────────────────────────


class BrokerPerformanceItem(Schema):
    """Performance metrics for a single broker/producer."""

    producer_id: int
    producer_name: str
    producer_type: str
    production_volume: float = 0.0
    quote_count: int = 0
    bound_count: int = 0
    hit_ratio: Optional[float] = None
    avg_deal_size: Optional[float] = None
    commission_earned: float = 0.0


class BrokerPerformanceResponse(Schema):
    """Broker performance scoreboard."""

    brokers: list[BrokerPerformanceItem] = Field(default_factory=list)
    total_production: float = 0.0
    total_commission: float = 0.0


# ── Quote Action Schemas ─────────────────────────────────────────────


class RecalculateRequest(Schema):
    """Optional overrides when recalculating a quote."""

    coverages: Optional[list[str]] = None
    revenue: Optional[Decimal] = None
    state: Optional[str] = None


class RecalculateResponse(Schema):
    """Result after re-running the rating engine on a quote."""

    quote_number: str
    status: str
    total_premium: Optional[Decimal] = None
    breakdown: Optional[dict[str, Any]] = None


class ApproveRequest(Schema):
    """Payload for approving a quote."""

    send_email: bool = Field(True, description="Whether to send the quote-ready email")
    effective_date: Optional[date] = None


class ApproveResponse(Schema):
    """Result after approving a quote."""

    quote_number: str
    status: str
    message: str


class DuplicateResponse(Schema):
    """Result after duplicating a quote."""

    original_quote_number: str
    new_quote_number: str


class SimulateRequest(Schema):
    """Override parameters for the rating simulator."""

    coverages: Optional[list[str]] = None
    coverage_data: Optional[dict[str, Any]] = None
    limits_retentions: Optional[dict[str, Any]] = None
    revenue: Optional[Decimal] = None
    employee_count: Optional[int] = None
    state: Optional[str] = None
    business_description: Optional[str] = None


class SimulateResponse(Schema):
    """Simulated rating result (not persisted)."""

    total_premium: Decimal
    coverages: dict[str, Any]


# ── Policy Action Schemas ────────────────────────────────────────────


class EndorseRequest(Schema):
    """Endorsement action request."""

    action: str = Field(
        ..., description="modify_limits | add_coverage | remove_coverage | backdate"
    )
    new_limits: Optional[dict[str, Any]] = None
    new_premium: Optional[Decimal] = None
    new_coverage_type: Optional[str] = None
    new_effective_date: Optional[date] = None
    reason: str = Field(..., description="Admin reason for the endorsement")
    is_brokered: bool = False
    carrier: str = ""


class EndorseResponse(Schema):
    """Endorsement result."""

    policy_number: str
    action: str
    old_premium: Optional[Decimal] = None
    new_premium: Optional[Decimal] = None
    prorated_delta: Optional[Decimal] = None
    message: str


class CancelRequest(Schema):
    """Policy cancellation request."""

    reason: str = Field(..., description="Admin reason for cancellation")


class CancelResponse(Schema):
    """Cancellation result."""

    policy_number: str
    refund_amount: Decimal
    message: str


class ReactivateRequest(Schema):
    """Policy reactivation request."""

    reactivation_date: date


class ReactivateResponse(Schema):
    """Reactivation result."""

    policy_numbers: list[str]
    subscription_id: Optional[str] = None
    gap_premium: Decimal = Decimal("0")
    message: str


# ── Audit Log ────────────────────────────────────────────────────────


class AuditLogEntry(Schema):
    """Single audit log entry."""

    id: int
    timestamp: datetime
    actor: Optional[str] = None
    action: str
    content_type: Optional[str] = None
    object_id: Optional[str] = None
    changes: Optional[dict[str, Any]] = None


class AuditLogResponse(Schema):
    """Paginated audit log entries."""

    entries: list[AuditLogEntry] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0


# ── Form Builder ─────────────────────────────────────────────────────


class FormFieldSchema(Schema):
    """Single field definition in a form."""

    key: str = Field(..., description="Unique field identifier")
    label: str
    field_type: str = Field(
        ..., description="text | number | select | checkbox | radio | textarea"
    )
    required: bool = False
    options: Optional[list[str]] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    validation: Optional[dict[str, Any]] = None


class FormDefinitionInput(Schema):
    """Request schema for creating/updating a form definition."""

    name: str
    slug: str
    version: int = 1
    description: str = ""
    fields: list[FormFieldSchema] = Field(default_factory=list)
    conditional_logic: Optional[dict[str, Any]] = None
    rating_field_mappings: Optional[dict[str, str]] = None
    coverage_type: Optional[str] = None
    is_active: bool = True


class FormDefinitionOutput(Schema):
    """Response schema for a form definition."""

    id: int
    name: str
    slug: str
    version: int
    description: str
    fields: list[FormFieldSchema]
    conditional_logic: Optional[dict[str, Any]] = None
    rating_field_mappings: Optional[dict[str, str]] = None
    coverage_type: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
