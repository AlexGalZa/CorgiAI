"""
Analytics endpoints for the Admin API.

Provides dashboard-level aggregations: pipeline counts, premium by carrier,
coverage breakdown, policy stats, claims summary, action items, monthly
premium time series, and loss ratio.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum, Q
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpRequest
from django.utils import timezone

from django.core.cache import cache as django_cache

from admin_api.helpers import (
    ADMIN_ROLES,
    ALL_STAFF_ROLES,
    _require_role,
    _scope_queryset_by_role,
)
from admin_api.schemas import (
    ActionItem,
    ActionItemsResponse,
    BrokerPerformanceItem,
    BrokerPerformanceResponse,
    CarrierPremium,
    ChurnReason,
    ClaimsStatusCount,
    ClaimsSummaryResponse,
    CohortRetention,
    ConversionRates,
    CoverageBreakdownItem,
    CoverageBreakdownResponse,
    LossRatioResponse,
    MonthlyPremiumPoint,
    MonthlyPremiumResponse,
    MonthlyRenewalRate,
    PipelineAnalyticsResponse,
    PipelineStatusCount,
    PipelineVelocityResponse,
    PolicyStatsResponse,
    PremiumByCarrierResponse,
    RetentionReportResponse,
    StageVelocity,
)
from common.schemas import ApiResponseSchema
from users.auth import JWTAuth


def register_analytics_routes(router):
    """Register all /analytics/* endpoints on the given router."""

    @router.get(
        "/analytics/pipeline",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Pipeline status counts",
    )
    def analytics_pipeline(request: HttpRequest) -> tuple[int, dict[str, Any]]:
        """Return the number of quotes in each pipeline status."""
        _require_role(request, ALL_STAFF_ROLES, "view_pipeline_analytics")

        cache_key = "analytics_pipeline"
        cached = django_cache.get(cache_key)
        if cached:
            return 200, cached

        from quotes.models import Quote

        pipeline_qs = (
            Quote.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        statuses = [
            PipelineStatusCount(status=row["status"], count=row["count"])
            for row in pipeline_qs
        ]
        total = sum(s.count for s in statuses)

        data = PipelineAnalyticsResponse(statuses=statuses, total=total)
        result = {"success": True, "message": "Pipeline analytics", "data": data.dict()}
        django_cache.set(cache_key, result, timeout=60)
        return 200, result

    @router.get(
        "/analytics/premium-by-carrier",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Premium aggregated by carrier",
    )
    def analytics_premium_by_carrier(
        request: HttpRequest,
    ) -> tuple[int, dict[str, Any]]:
        """Aggregate total written premium grouped by insurance carrier."""
        _require_role(request, ALL_STAFF_ROLES, "view_premium_by_carrier")

        from policies.models import Policy

        carrier_qs = (
            Policy.objects.filter(status="active")
            .values("carrier")
            .annotate(
                total_premium=Coalesce(Sum("premium"), Decimal("0")),
                policy_count=Count("id"),
            )
            .order_by("-total_premium")
        )

        carriers = [
            CarrierPremium(
                carrier=row["carrier"] or "Unknown",
                total_premium=row["total_premium"],
                policy_count=row["policy_count"],
            )
            for row in carrier_qs
        ]

        data = PremiumByCarrierResponse(carriers=carriers)
        return 200, {
            "success": True,
            "message": "Premium by carrier",
            "data": data.dict(),
        }

    @router.get(
        "/analytics/coverage-breakdown",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Coverage type counts",
    )
    def analytics_coverage_breakdown(
        request: HttpRequest,
    ) -> tuple[int, dict[str, Any]]:
        """Count active policies per coverage type with total premium."""
        _require_role(request, ALL_STAFF_ROLES, "view_coverage_breakdown")

        cache_key = "analytics_coverage_breakdown"
        cached = django_cache.get(cache_key)
        if cached:
            return 200, cached

        from common.constants import COVERAGE_DISPLAY_NAMES
        from policies.models import Policy

        breakdown_qs = (
            Policy.objects.filter(status="active")
            .values("coverage_type")
            .annotate(
                count=Count("id"),
                total_premium=Coalesce(Sum("premium"), Decimal("0")),
            )
            .order_by("-count")
        )

        coverages = [
            CoverageBreakdownItem(
                coverage_type=row["coverage_type"],
                display_name=COVERAGE_DISPLAY_NAMES.get(
                    row["coverage_type"], row["coverage_type"]
                ),
                count=row["count"],
                total_premium=row["total_premium"],
            )
            for row in breakdown_qs
        ]

        data = CoverageBreakdownResponse(coverages=coverages)
        result = {"success": True, "message": "Coverage breakdown", "data": data.dict()}
        django_cache.set(cache_key, result, timeout=60)
        return 200, result

    @router.get(
        "/analytics/policy-stats",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Active policy count and total premium",
    )
    def analytics_policy_stats(request: HttpRequest) -> tuple[int, dict[str, Any]]:
        """Return high-level statistics for active policies."""
        _require_role(request, ALL_STAFF_ROLES, "view_policy_stats")

        cache_key = "analytics_policy_stats"
        cached = django_cache.get(cache_key)
        if cached:
            return 200, cached

        from policies.models import Policy

        stats = Policy.objects.filter(status="active").aggregate(
            active_count=Count("id"),
            total_premium=Coalesce(Sum("premium"), Decimal("0")),
        )

        active_count = stats["active_count"] or 0
        total_premium = stats["total_premium"] or Decimal("0")
        average_premium = (
            (total_premium / active_count).quantize(Decimal("0.01"))
            if active_count > 0
            else Decimal("0")
        )

        data = PolicyStatsResponse(
            active_count=active_count,
            total_premium=total_premium,
            average_premium=average_premium,
        )
        result = {"success": True, "message": "Policy stats", "data": data.dict()}
        django_cache.set(cache_key, result, timeout=60)
        return 200, result

    @router.get(
        "/analytics/claims-summary",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Claims summary by status, reserves, paid",
    )
    def analytics_claims_summary(request: HttpRequest) -> tuple[int, dict[str, Any]]:
        """Summarise claims by status with total reserves and paid amounts."""
        _require_role(request, ALL_STAFF_ROLES, "view_claims_summary")

        from claims.models import Claim

        by_status_qs = (
            Claim.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        by_status = [
            ClaimsStatusCount(status=row["status"], count=row["count"])
            for row in by_status_qs
        ]

        totals = Claim.objects.aggregate(
            total_reserves=Coalesce(Sum("case_reserve_loss"), Decimal("0"))
            + Coalesce(Sum("case_reserve_lae"), Decimal("0")),
            total_paid=Coalesce(Sum("paid_loss"), Decimal("0"))
            + Coalesce(Sum("paid_lae"), Decimal("0")),
        )

        data = ClaimsSummaryResponse(
            by_status=by_status,
            total_reserves=totals["total_reserves"] or Decimal("0"),
            total_paid=totals["total_paid"] or Decimal("0"),
        )
        return 200, {"success": True, "message": "Claims summary", "data": data.dict()}

    @router.get(
        "/analytics/action-items",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Blockers, expiring, and pending items",
    )
    def analytics_action_items(request: HttpRequest) -> tuple[int, dict[str, Any]]:
        """Return items requiring admin attention."""
        _require_role(request, ALL_STAFF_ROLES, "view_action_items")

        from claims.models import Claim
        from policies.models import Payment, Policy
        from quotes.models import Quote

        items: list[ActionItem] = []
        today = date.today()
        thirty_days = today + timedelta(days=30)

        # Quotes needing review (scoped by role)
        review_qs = Quote.objects.filter(status="needs_review").order_by("-created_at")
        review_qs = _scope_queryset_by_role(review_qs, request.auth, "quotes")
        review_quotes = review_qs[:20]
        for q in review_quotes:
            items.append(
                ActionItem(
                    type="blocker",
                    title=f"Quote {q.quote_number} needs review",
                    description=f"Company: {q.company.entity_legal_name or 'N/A'}",
                    quote_number=q.quote_number,
                )
            )

        # Policies expiring within 30 days (scoped by role)
        expiring_qs = Policy.objects.filter(
            status="active",
            expiration_date__gte=today,
            expiration_date__lte=thirty_days,
        ).order_by("expiration_date")
        expiring_qs = _scope_queryset_by_role(expiring_qs, request.auth, "policies")
        expiring = expiring_qs[:20]
        for p in expiring:
            items.append(
                ActionItem(
                    type="expiring",
                    title=f"Policy {p.policy_number} expires {p.expiration_date}",
                    description=f"Coverage: {p.coverage_type}, Premium: ${p.premium}",
                    policy_number=p.policy_number,
                    due_date=p.expiration_date,
                )
            )

        # Open claims (submitted or under_review)
        open_claims = Claim.objects.filter(
            status__in=["submitted", "under_review"]
        ).order_by("-created_at")[:20]
        for c in open_claims:
            items.append(
                ActionItem(
                    type="pending",
                    title=f"Claim {c.claim_number} - {c.get_status_display()}",
                    description=f"Policy: {c.policy.policy_number}, Reported: {c.claim_report_date or c.created_at.date()}",
                )
            )

        # Overdue payments
        overdue = Payment.objects.filter(status="pending").order_by("created_at")[:10]
        for pay in overdue:
            items.append(
                ActionItem(
                    type="blocker",
                    title=f"Overdue payment on {pay.policy.policy_number}",
                    description=f"Amount: ${pay.amount}",
                    policy_number=pay.policy.policy_number,
                )
            )

        data = ActionItemsResponse(items=items, total=len(items))
        return 200, {"success": True, "message": "Action items", "data": data.dict()}

    @router.get(
        "/analytics/monthly-premium",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Monthly premium time series",
    )
    def analytics_monthly_premium(request: HttpRequest) -> tuple[int, dict[str, Any]]:
        """Return monthly written premium as a time series for the last 12 months."""
        _require_role(request, ALL_STAFF_ROLES, "view_monthly_premium")

        from policies.models import PolicyTransaction

        twelve_months_ago = timezone.now().date() - timedelta(days=365)

        monthly_qs = (
            PolicyTransaction.objects.filter(
                accounting_date__gte=twelve_months_ago,
                transaction_type__in=["new", "renewal"],
            )
            .annotate(month=TruncMonth("accounting_date"))
            .values("month")
            .annotate(premium=Coalesce(Sum("gross_written_premium"), Decimal("0")))
            .order_by("month")
        )

        points = [
            MonthlyPremiumPoint(
                month=row["month"].strftime("%Y-%m"),
                premium=row["premium"],
            )
            for row in monthly_qs
        ]

        data = MonthlyPremiumResponse(data=points)
        return 200, {"success": True, "message": "Monthly premium", "data": data.dict()}

    @router.get(
        "/analytics/loss-ratio",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Loss ratio: paid losses / earned premium",
    )
    def analytics_loss_ratio(request: HttpRequest) -> tuple[int, dict[str, Any]]:
        """Calculate overall loss ratio across all policies."""
        _require_role(request, ALL_STAFF_ROLES, "view_loss_ratio")

        from claims.models import Claim
        from policies.models import Policy

        earned = Policy.objects.filter(status__in=["active", "expired"]).aggregate(
            total=Coalesce(Sum("premium"), Decimal("0"))
        )["total"]

        paid = Claim.objects.aggregate(
            total=Coalesce(Sum("paid_loss"), Decimal("0"))
            + Coalesce(Sum("paid_lae"), Decimal("0"))
        )["total"]

        loss_ratio = None
        if earned and earned > 0:
            loss_ratio = (paid / earned).quantize(Decimal("0.0001"))

        data = LossRatioResponse(
            earned_premium=earned or Decimal("0"),
            paid_losses=paid or Decimal("0"),
            loss_ratio=loss_ratio,
        )
        return 200, {"success": True, "message": "Loss ratio", "data": data.dict()}

    # ── V3 #43 — Sales Pipeline Velocity ─────────────────────────────

    @router.get(
        "/analytics/pipeline-velocity",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Sales pipeline velocity — stage durations and conversion rates",
    )
    def analytics_pipeline_velocity(request: HttpRequest) -> tuple[int, dict[str, Any]]:
        """Return average days in each pipeline stage, stage-to-stage conversion
        rates (submitted → quoted → purchased), and total open pipeline value."""
        _require_role(request, ALL_STAFF_ROLES, "view_pipeline_velocity")

        cache_key = "analytics_pipeline_velocity"
        cached = django_cache.get(cache_key)
        if cached:
            return 200, cached

        from analytics.pipeline import get_pipeline_velocity

        raw = get_pipeline_velocity()

        data = PipelineVelocityResponse(
            stage_velocity=[StageVelocity(**sv) for sv in raw["stage_velocity"]],
            conversion_rates=ConversionRates(**raw["conversion_rates"]),
            pipeline_value=raw["pipeline_value"],
            total_quotes=raw["total_quotes"],
            purchased_count=raw["purchased_count"],
            open_quotes=raw["open_quotes"],
            avg_open_age_days=raw["avg_open_age_days"],
            stage_counts=raw["stage_counts"],
        )
        result = {"success": True, "message": "Pipeline velocity", "data": data.dict()}
        django_cache.set(cache_key, result, timeout=120)
        return 200, result

    # ── V3 #44 — Customer Retention / Churn ──────────────────────────

    @router.get(
        "/analytics/retention",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Customer retention and churn report",
    )
    def analytics_retention(request: HttpRequest) -> tuple[int, dict[str, Any]]:
        """Return renewal rates by month, churn reasons, revenue retention rate,
        and cohort analysis by signup month."""
        _require_role(request, ALL_STAFF_ROLES, "view_retention")

        cache_key = "analytics_retention"
        cached = django_cache.get(cache_key)
        if cached:
            return 200, cached

        from analytics.retention import get_retention_report

        raw = get_retention_report()

        data = RetentionReportResponse(
            renewal_rates=[MonthlyRenewalRate(**r) for r in raw["renewal_rates"]],
            churn_reasons=[ChurnReason(**c) for c in raw["churn_reasons"]],
            revenue_retention_rate=raw["revenue_retention_rate"],
            cohort_analysis=[CohortRetention(**c) for c in raw["cohort_analysis"]],
            overall_renewal_rate=raw["overall_renewal_rate"],
            total_eligible=raw["total_eligible"],
            total_renewed=raw["total_renewed"],
        )
        result = {"success": True, "message": "Retention report", "data": data.dict()}
        django_cache.set(cache_key, result, timeout=300)
        return 200, result

    # ── V3 #45 — Broker Performance Scoreboard ────────────────────────

    @router.get(
        "/analytics/broker-performance",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Broker performance scoreboard",
    )
    def analytics_broker_performance(
        request: HttpRequest,
    ) -> tuple[int, dict[str, Any]]:
        """Return per-producer/broker metrics: production volume, hit ratio
        (quotes→bound), average deal size, and commission earned."""
        _require_role(request, ALL_STAFF_ROLES, "view_broker_performance")

        cache_key = "analytics_broker_performance"
        cached = django_cache.get(cache_key)
        if cached:
            return 200, cached

        from analytics.broker_performance import get_broker_performance

        raw = get_broker_performance()

        data = BrokerPerformanceResponse(
            brokers=[BrokerPerformanceItem(**b) for b in raw["brokers"]],
            total_production=raw["total_production"],
            total_commission=raw["total_commission"],
        )
        result = {"success": True, "message": "Broker performance", "data": data.dict()}
        django_cache.set(cache_key, result, timeout=120)
        return 200, result

    @router.get(
        "/analytics/earned-premium",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Earned premium report with filters by month, carrier, and coverage type",
    )
    def analytics_earned_premium(
        request: HttpRequest,
        month: str = None,
        carrier: str = None,
        coverage_type: str = None,
    ) -> tuple[int, dict[str, Any]]:
        """
        Return earned premium breakdown.

        Filters:
        - month: YYYY-MM format (e.g. 2026-03)
        - carrier: partial match on carrier name
        - coverage_type: exact coverage type slug (e.g. 'tech-eo')
        """
        _require_role(request, ALL_STAFF_ROLES, "view_earned_premium")

        from analytics.reports import get_earned_premium_report

        report = get_earned_premium_report(
            month=month,
            carrier=carrier,
            coverage_type=coverage_type,
        )
        return 200, {
            "success": True,
            "message": "Earned premium report",
            "data": report,
        }

    # ── Claims Adjuster analytics ────────────────────────────────────

    @router.get(
        "/analytics/claims-adjuster-summary",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Claims adjuster dashboard metrics",
    )
    def analytics_claims_adjuster_summary(
        request: HttpRequest,
    ) -> tuple[int, dict[str, Any]]:
        """Return metrics for the claims adjuster dashboard."""
        _require_role(request, ALL_STAFF_ROLES, "view_claims_adjuster_summary")

        from claims.models import Claim
        from django.db.models import Sum
        from decimal import Decimal

        qs = Claim.objects.all()

        assigned = qs.count()
        pending_reserves = qs.filter(
            status__in=["submitted", "under_review"]
        ).aggregate(total=Sum("case_reserve_loss") + Sum("case_reserve_lae"))[
            "total"
        ] or Decimal("0")

        # Avg resolution time in days for closed claims
        closed = qs.filter(
            status="closed",
            resolution_date__isnull=False,
            claim_report_date__isnull=False,
        )
        avg_resolution_days = None
        if closed.exists():
            try:
                avg_resolution_days = round(
                    sum(
                        (c.resolution_date - c.claim_report_date).days
                        for c in closed
                        if c.resolution_date and c.claim_report_date
                    )
                    / max(closed.count(), 1),
                    1,
                )
            except Exception:
                avg_resolution_days = None

        # SLA compliance from SLA metrics
        from sla.models import SLAMetric

        claim_slas = SLAMetric.objects.filter(entity_type="claim")
        total_slas = claim_slas.count()
        breached = claim_slas.filter(breached=True).count()
        sla_rate = (
            round((1 - breached / total_slas) * 100, 1) if total_slas > 0 else 100.0
        )

        return 200, {
            "success": True,
            "message": "Claims adjuster summary",
            "data": {
                "assigned_claims": assigned,
                "avg_resolution_days": avg_resolution_days,
                "pending_reserves": float(pending_reserves),
                "sla_compliance_rate": sla_rate,
                "total_slas": total_slas,
                "sla_breaches": breached,
            },
        }

    @router.get(
        "/analytics/claims-reserves",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Claim reserves table",
    )
    def analytics_claims_reserves(
        request: HttpRequest,
        page: int = 1,
        search: str = "",
        status: str = "",
    ) -> tuple[int, dict[str, Any]]:
        """Return per-claim reserve data for the reserves tab."""
        _require_role(request, ALL_STAFF_ROLES, "view_claims_reserves")

        from claims.models import Claim

        qs = Claim.objects.select_related("policy").all()
        if status:
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(
                Q(claim_number__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(organization_name__icontains=search)
            )

        total = qs.count()
        page_size = 25
        offset = (page - 1) * page_size
        claims = qs.order_by("-created_at")[offset : offset + page_size]

        def d(v):
            return float(v) if v else 0.0

        results = [
            {
                "id": c.id,
                "claim_number": c.claim_number,
                "insured": c.organization_name
                or f"{c.first_name} {c.last_name}".strip(),
                "policy_number": c.policy.policy_number if c.policy else None,
                "status": c.status,
                "case_reserve_loss": d(c.case_reserve_loss),
                "case_reserve_lae": d(c.case_reserve_lae),
                "paid_loss": d(c.paid_loss),
                "paid_lae": d(c.paid_lae),
                "total_incurred": d(c.case_reserve_loss)
                + d(c.case_reserve_lae)
                + d(c.paid_loss)
                + d(c.paid_lae),
            }
            for c in claims
        ]

        return 200, {
            "success": True,
            "message": "Claims reserves",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }

    @router.get(
        "/analytics/claims-sla-metrics",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="SLA metrics for claims",
    )
    def analytics_claims_sla_metrics(
        request: HttpRequest, page: int = 1
    ) -> tuple[int, dict[str, Any]]:
        """Return SLA metrics for claims with breach status."""
        _require_role(request, ALL_STAFF_ROLES, "view_claims_sla_metrics")

        from sla.models import SLAMetric

        qs = SLAMetric.objects.filter(entity_type="claim").order_by("-started_at")
        total = qs.count()
        page_size = 25
        offset = (page - 1) * page_size
        metrics = qs[offset : offset + page_size]

        results = [
            {
                "id": m.id,
                "entity_id": m.entity_id,
                "metric_type": m.metric_type,
                "metric_type_display": m.get_metric_type_display(),
                "target_hours": float(m.target_hours),
                "elapsed_hours": float(m.elapsed_hours),
                "started_at": m.started_at.isoformat(),
                "completed_at": m.completed_at.isoformat() if m.completed_at else None,
                "breached": m.breached,
                "notes": m.notes,
            }
            for m in metrics
        ]

        return 200, {
            "success": True,
            "message": "Claims SLA metrics",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }

    # ── Admin Security analytics ─────────────────────────────────────

    @router.get(
        "/analytics/security-summary",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Security and session analytics for admin",
    )
    def analytics_security_summary(request: HttpRequest) -> tuple[int, dict[str, Any]]:
        """Return security metrics: active sessions, login attempts, 2FA status."""
        _require_role(request, ADMIN_ROLES, "view_security_summary")

        from users.models import User, ImpersonationLog
        from django.utils import timezone

        users_qs = User.objects.filter(is_staff=True)
        total_staff = users_qs.count()

        # Users locked out
        now = timezone.now()
        locked_out = (
            users_qs.filter(locked_until__gt=now).count()
            if hasattr(User, "locked_until")
            else 0
        )

        # Recent failed logins (users with failed_login_attempts > 0)
        recent_failures = []
        if hasattr(User, "failed_login_attempts"):
            failed_users = users_qs.filter(failed_login_attempts__gt=0).values(
                "email", "failed_login_attempts", "locked_until", "updated_at"
            )[:20]
            for u in failed_users:
                recent_failures.append(
                    {
                        "email": u["email"],
                        "failed_attempts": u["failed_login_attempts"],
                        "locked_until": u["locked_until"].isoformat()
                        if u.get("locked_until")
                        else None,
                        "last_attempt": u["updated_at"].isoformat()
                        if u.get("updated_at")
                        else None,
                    }
                )

        # Impersonation logs (active sessions)
        recent_impersonations = []
        try:
            imp_logs = ImpersonationLog.objects.select_related(
                "admin", "target"
            ).order_by("-created_at")[:10]
            for log in imp_logs:
                recent_impersonations.append(
                    {
                        "id": log.id,
                        "admin_email": log.admin.email if log.admin else None,
                        "target_email": log.target.email if log.target else None,
                        "started_at": log.created_at.isoformat()
                        if hasattr(log, "created_at") and log.created_at
                        else None,
                    }
                )
        except Exception:
            pass

        # User 2FA status (using has_usable_password as proxy; real 2FA would need a field)
        users_with_password = users_qs.filter(password__startswith="pbkdf2").count()

        return 200, {
            "success": True,
            "message": "Security summary",
            "data": {
                "total_staff_users": total_staff,
                "locked_out_count": locked_out,
                "recent_login_failures": recent_failures,
                "active_impersonations": recent_impersonations,
                "users_with_password_auth": users_with_password,
            },
        }
