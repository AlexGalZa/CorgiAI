"""
Coverage Gap Analysis service.

Analyzes a company's current coverage against similar companies in the
same industry/size band and recommends missing coverages.
"""

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


# Coverage descriptions for LLM context
COVERAGE_DESCRIPTIONS = {
    "commercial-general-liability": "Commercial General Liability (CGL) — covers bodily injury, property damage, and personal injury claims from third parties.",
    "technology-errors-and-omissions": "Technology E&O / Professional Liability — covers claims arising from errors, omissions, or negligent professional services.",
    "cyber-liability": "Cyber Liability — covers data breaches, ransomware, and cyber extortion incidents.",
    "directors-and-officers": "Directors & Officers (D&O) — protects executives and board members from personal liability for management decisions.",
    "employment-practices-liability": "Employment Practices Liability (EPLI) — covers wrongful termination, discrimination, harassment claims.",
    "fiduciary-liability": "Fiduciary Liability — covers breaches of fiduciary duty related to employee benefit plans.",
    "hired-and-non-owned-auto": "Hired & Non-Owned Auto (HNOA) — covers employees using personal or rented vehicles for business.",
    "media-liability": "Media Liability — covers copyright infringement, defamation, and intellectual property claims.",
    "commercial-auto": "Commercial Auto — covers company-owned vehicles.",
    "workers-compensation": "Workers' Compensation — covers employee injuries and illnesses on the job.",
    "umbrella": "Umbrella / Excess Liability — extra liability coverage on top of other policies.",
    "business-owners-policy": "Business Owners Policy (BOP) — bundled coverage for property and general liability.",
}

# Industry-to-recommended-coverage mapping (fallback if AI unavailable)
INDUSTRY_COVERAGE_MAP = {
    "technology": [
        "technology-errors-and-omissions",
        "cyber-liability",
        "directors-and-officers",
        "employment-practices-liability",
        "commercial-general-liability",
    ],
    "saas": [
        "technology-errors-and-omissions",
        "cyber-liability",
        "directors-and-officers",
        "employment-practices-liability",
        "commercial-general-liability",
        "fiduciary-liability",
    ],
    "healthcare": [
        "commercial-general-liability",
        "cyber-liability",
        "employment-practices-liability",
        "directors-and-officers",
        "fiduciary-liability",
    ],
    "finance": [
        "directors-and-officers",
        "fiduciary-liability",
        "employment-practices-liability",
        "commercial-general-liability",
        "cyber-liability",
    ],
    "media": [
        "media-liability",
        "commercial-general-liability",
        "employment-practices-liability",
        "cyber-liability",
    ],
    "default": [
        "commercial-general-liability",
        "technology-errors-and-omissions",
        "cyber-liability",
        "employment-practices-liability",
    ],
}


def _get_industry_key(industry: str) -> str:
    industry_lower = industry.lower()
    for key in INDUSTRY_COVERAGE_MAP:
        if key in industry_lower:
            return key
    return "default"


def analyze_coverage_gap(
    company_name: str,
    industry: str,
    employee_count: int,
    annual_revenue: float,
    current_coverages: list[str],
    description: str = "",
) -> dict:
    """
    Analyze coverage gaps for a company.

    Tries OpenAI first; falls back to rule-based analysis if AI unavailable.

    Returns a dict with:
    - recommended_coverages: list of gap recommendations
    - summary: brief summary string
    - risk_score: 'low' | 'medium' | 'high'
    """

    # Try AI-powered analysis first
    try:
        openai_key = getattr(settings, "OPENAI_API_KEY", None)
        if openai_key:
            return _analyze_with_ai(
                company_name=company_name,
                industry=industry,
                employee_count=employee_count,
                annual_revenue=annual_revenue,
                current_coverages=current_coverages,
                description=description,
            )
    except Exception as e:
        logger.warning(f"AI coverage gap analysis failed, falling back to rules: {e}")

    # Rule-based fallback
    return _analyze_with_rules(
        industry=industry,
        employee_count=employee_count,
        current_coverages=current_coverages,
    )


def _analyze_with_ai(
    company_name: str,
    industry: str,
    employee_count: int,
    annual_revenue: float,
    current_coverages: list[str],
    description: str,
) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    current_coverage_text = (
        "\n".join(f"- {COVERAGE_DESCRIPTIONS.get(c, c)}" for c in current_coverages)
        or "None"
    )

    all_coverages_text = "\n".join(
        f"- {slug}: {desc}" for slug, desc in COVERAGE_DESCRIPTIONS.items()
    )

    prompt = f"""You are an expert insurance advisor analyzing coverage gaps for a business.

Company Profile:
- Name: {company_name}
- Industry: {industry}
- Employees: {employee_count}
- Annual Revenue: ${annual_revenue:,.0f}
- Description: {description or "Not provided"}

Current Coverage:
{current_coverage_text}

Available Coverage Types:
{all_coverages_text}

Task: Identify coverage gaps — policies similar companies in this industry typically carry that this company doesn't have. For each gap:
1. Explain why it's important for this specific company
2. Estimate the risk level if they don't have it (low/medium/high)
3. Rate the urgency (immediate/soon/optional)

Respond with a JSON object in this exact format:
{{
  "summary": "Brief 1-2 sentence summary of the company's coverage situation",
  "risk_score": "low|medium|high",
  "gaps": [
    {{
      "coverage_slug": "slug-from-available-list",
      "coverage_name": "Human readable name",
      "reason": "Why this company specifically needs this coverage",
      "risk_level": "low|medium|high",
      "urgency": "immediate|soon|optional",
      "industry_adoption": "What % of similar companies have this (e.g. '85% of tech companies')"
    }}
  ]
}}

Only include coverages the company does NOT currently have. Limit to 5 most important gaps."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert insurance advisor. Always respond with valid JSON only, no markdown.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    # Normalize output
    gaps = result.get("gaps", [])
    recommendations = []
    for gap in gaps:
        recommendations.append(
            {
                "coverage_slug": gap.get("coverage_slug", ""),
                "coverage_name": gap.get("coverage_name", ""),
                "reason": gap.get("reason", ""),
                "risk_level": gap.get("risk_level", "medium"),
                "urgency": gap.get("urgency", "soon"),
                "industry_adoption": gap.get("industry_adoption", ""),
                "description": COVERAGE_DESCRIPTIONS.get(
                    gap.get("coverage_slug", ""), ""
                ),
            }
        )

    return {
        "summary": result.get("summary", ""),
        "risk_score": result.get("risk_score", "medium"),
        "recommended_coverages": recommendations,
        "analysis_method": "ai",
    }


def _analyze_with_rules(
    industry: str,
    employee_count: int,
    current_coverages: list[str],
) -> dict:
    """Rule-based fallback when AI is unavailable."""
    industry_key = _get_industry_key(industry)
    recommended_slugs = INDUSTRY_COVERAGE_MAP[industry_key]

    gaps = []
    for slug in recommended_slugs:
        if slug not in current_coverages:
            gaps.append(
                {
                    "coverage_slug": slug,
                    "coverage_name": slug.replace("-", " ").title(),
                    "reason": f"Most {industry} companies carry this coverage to protect against common risks in the industry.",
                    "risk_level": "medium",
                    "urgency": "soon",
                    "industry_adoption": "Most similar companies",
                    "description": COVERAGE_DESCRIPTIONS.get(slug, ""),
                }
            )

    # Add employee-count based recommendations
    if (
        employee_count >= 5
        and "employment-practices-liability" not in current_coverages
    ):
        epli_slug = "employment-practices-liability"
        if not any(g["coverage_slug"] == epli_slug for g in gaps):
            gaps.append(
                {
                    "coverage_slug": epli_slug,
                    "coverage_name": "Employment Practices Liability",
                    "reason": f"With {employee_count} employees, EPLI protects against wrongful termination and harassment claims.",
                    "risk_level": "high",
                    "urgency": "immediate",
                    "industry_adoption": "90%+ of companies with 5+ employees",
                    "description": COVERAGE_DESCRIPTIONS.get(epli_slug, ""),
                }
            )

    if employee_count >= 10 and "directors-and-officers" not in current_coverages:
        do_slug = "directors-and-officers"
        if not any(g["coverage_slug"] == do_slug for g in gaps):
            gaps.append(
                {
                    "coverage_slug": do_slug,
                    "coverage_name": "Directors & Officers",
                    "reason": "Protects founders and executives from personal liability as the company grows.",
                    "risk_level": "medium",
                    "urgency": "soon",
                    "industry_adoption": "Most funded startups",
                    "description": COVERAGE_DESCRIPTIONS.get(do_slug, ""),
                }
            )

    risk_score = "low" if len(gaps) <= 1 else ("high" if len(gaps) >= 3 else "medium")
    summary = (
        f"Your company has {len(current_coverages)} active coverage(s) but is missing {len(gaps)} commonly recommended coverage(s) for a {industry} company."
        if gaps
        else f"Your company appears well-covered for a {industry} company."
    )

    return {
        "summary": summary,
        "risk_score": risk_score,
        "recommended_coverages": gaps[:5],
        "analysis_method": "rules",
    }
