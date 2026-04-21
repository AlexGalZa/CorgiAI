"""
Analysis API endpoints.

POST /api/v1/analysis/coverage-gap — AI-powered coverage gap analysis
"""

from typing import Any

from django.http import HttpRequest
from ninja import Router, Schema

from common.schemas import ApiResponseSchema
from users.auth import JWTAuth

router = Router(tags=["Analysis"])


class CoverageGapRequestSchema(Schema):
    company_name: str = ""
    industry: str
    employee_count: int = 1
    annual_revenue: float = 0
    description: str = ""
    current_coverage_slugs: list[str] = []


@router.post(
    "/coverage-gap",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 400: ApiResponseSchema},
    summary="AI-powered coverage gap analysis",
)
def analyze_coverage_gap(
    request: HttpRequest,
    payload: CoverageGapRequestSchema,
) -> tuple[int, dict[str, Any]]:
    """Analyze coverage gaps for a company.

    Compares the company's current coverages against what similar companies
    in the same industry/size band typically carry, and returns recommended
    missing coverages.

    If OpenAI is configured, uses GPT-4o-mini for contextual recommendations.
    Falls back to rule-based analysis if AI is unavailable.

    Args:
        payload.industry: Company industry (e.g. 'technology', 'healthcare', 'media')
        payload.employee_count: Number of employees
        payload.annual_revenue: Annual revenue in USD
        payload.description: Brief company description (improves AI quality)
        payload.current_coverage_slugs: List of coverage slugs the company currently has

    Returns:
        200 with gap analysis result including recommended_coverages list.
    """
    from analysis.service import analyze_coverage_gap as _analyze
    from organizations.service import OrganizationService
    from policies.models import Policy

    # Auto-populate current coverages from active policies if not provided
    current_slugs = payload.current_coverage_slugs
    if not current_slugs:
        try:
            org_id = OrganizationService.get_active_org_id(request.auth)
            active_policies = (
                Policy.objects.filter(
                    quote__organization_id=org_id,
                    status="active",
                    is_deleted=False,
                )
                .values_list("coverage_type", flat=True)
                .distinct()
            )
            current_slugs = list(active_policies)
        except Exception:
            current_slugs = []

    # Auto-populate company name from org if not provided
    company_name = payload.company_name
    if not company_name:
        try:
            org_id = OrganizationService.get_active_org_id(request.auth)
            from organizations.models import Organization

            org = Organization.objects.filter(pk=org_id).first()
            company_name = org.name if org else ""
        except Exception:
            pass

    if not payload.industry:
        return 400, {
            "success": False,
            "message": "Industry is required for coverage gap analysis",
            "data": None,
        }

    result = _analyze(
        company_name=company_name,
        industry=payload.industry,
        employee_count=max(1, payload.employee_count),
        annual_revenue=max(0, payload.annual_revenue),
        current_coverages=current_slugs,
        description=payload.description,
    )

    return 200, {
        "success": True,
        "message": "Coverage gap analysis complete",
        "data": {
            **result,
            "current_coverage_slugs": current_slugs,
            "company_name": company_name,
        },
    }
