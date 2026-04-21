"""
PDF generation for consolidated Certificate of Insurance (COI).

Uses the existing PDF form-filling infrastructure (PDFService + COI template)
to generate a professional COI document from consolidated data.
"""

import logging
from typing import Optional

from common.constants import (
    COVERAGE_DISPLAY_NAMES,
    CGL_COVERAGE,
    HNOA_COVERAGE,
    NTIC_CARRIER,
    NTIC_NAIC_CODE,
    TECHRRG_CARRIER,
    TECHRRG_NAIC_CODE,
)
from common.utils import format_currency
from documents_generator.constants import COIPaths
from documents_generator.schemas import (
    COIFormInput,
    COIProducerInput,
    COIInsurerInput,
    COIInsuredInput,
    COIGeneralLiabilityInput,
    COIAutoLiabilityInput,
    COIAdditionalCoverageInput,
)
from pdf.service import PDFService
from policies.models import Policy

logger = logging.getLogger(__name__)


def generate_coi_pdf(consolidated_data: dict) -> Optional[bytes]:
    """
    Generate a COI PDF from consolidated data returned by
    CertificateService.generate_consolidated_coi().

    Produces one COI per COI group (the first group). For multi-group
    organizations, the caller should specify which group or iterate.

    Args:
        consolidated_data: The dict returned by generate_consolidated_coi().

    Returns:
        PDF bytes, or None if generation fails.
    """
    coi_groups = consolidated_data.get("coi_groups", [])
    if not coi_groups:
        logger.warning("No COI groups found in consolidated data — cannot generate PDF")
        return None

    # Generate PDF for the first COI group (most common case)
    # For multi-group scenarios the endpoint can be extended with a group selector
    return _generate_pdf_for_coi_group(
        coi_groups[0], consolidated_data.get("organization_id")
    )


def generate_coi_pdf_for_group(
    coi_group: dict, organization_id: int
) -> Optional[bytes]:
    """Generate a COI PDF for a specific COI group."""
    return _generate_pdf_for_coi_group(coi_group, organization_id)


def _generate_pdf_for_coi_group(
    coi_group: dict, organization_id: int = None
) -> Optional[bytes]:
    """
    Internal: build COI form data from a single COI group and render via
    the standard ACORD 25 PDF template.
    """
    coi_number = coi_group["coi_number"]
    policies_data = coi_group.get("policies", [])
    if not policies_data:
        return None

    # Fetch actual Policy objects to get company/address info
    db_policies = list(
        Policy.objects.filter(coi_number=coi_number, status="active").select_related(
            "quote__company__business_address"
        )
    )
    if not db_policies:
        logger.warning("No active policies in DB for COI %s", coi_number)
        return None

    first_policy = db_policies[0]
    company = first_policy.quote.company
    address = company.business_address if company else None
    fmt = format_currency

    eff_date = coi_group["effective_date"]
    exp_date = coi_group["expiration_date"]

    # Convert ISO dates to MM/DD/YYYY for the PDF form
    eff_display = _iso_to_display(eff_date)
    exp_display = _iso_to_display(exp_date)

    # Determine primary carrier
    non_brokered = [p for p in db_policies if not p.is_brokered]
    if non_brokered:
        any_ntic = any(p.carrier == NTIC_CARRIER for p in non_brokered)
        carrier_name = NTIC_CARRIER if any_ntic else non_brokered[0].carrier
    else:
        carrier_name = TECHRRG_CARRIER

    naic_code = NTIC_NAIC_CODE if carrier_name == NTIC_CARRIER else TECHRRG_NAIC_CODE

    from common.utils import format_address_street, format_address_city_state_zip

    # NAICS (industry classification) — required on NTIC templates; harmless on others.
    naics_code = getattr(company, "naics_code", None) or ""
    description = f"NAICS Code: {naics_code}" if naics_code else ""

    coi_data = COIFormInput(
        certificate_date=eff_display,
        certificate_number=coi_number,
        description=description,
        producer=COIProducerInput(
            name="Corgi Insurance Services, Inc.",
            address_line1="425 Bush St, STE 500",
            address_line2="San Francisco, CA 94104",
            contact_name="Nicolas Laqua",
            phone="1 850 662 6744",
            email="hello@corgi.insure",
        ),
        insurer=COIInsurerInput(
            name=carrier_name,
            naic_code=naic_code,
        ),
        insured=COIInsuredInput(
            name=company.entity_legal_name
            or (company.business_description[:50] if company else ""),
            address_line1=format_address_street(address) if address else "",
            address_line2=format_address_city_state_zip(address) if address else "",
        ),
    )

    # Build a lookup of DB policies by coverage type
    policies_by_coverage = {p.coverage_type: p for p in db_policies}

    # General Liability
    cgl_policy = policies_by_coverage.get(CGL_COVERAGE)
    if cgl_policy:
        limits = cgl_policy.limits_retentions or {}
        cgl_questionnaire = first_policy.quote.coverage_data.get(CGL_COVERAGE, {})
        agg = int(limits.get("aggregate_limit", 1000000))
        occ = int(limits.get("per_occurrence_limit", agg))
        has_products_ops = cgl_questionnaire.get(
            "has_products_completed_operations", False
        )

        coi_data.general_liability = COIGeneralLiabilityInput(
            insurer_letter="A",
            policy_number=cgl_policy.policy_number,
            effective_date=eff_display,
            expiration_date=exp_display,
            each_occurrence=fmt(occ),
            damage_to_rented=fmt(100_000),
            med_exp=fmt(5_000),
            general_aggregate=fmt(agg),
            products_comp_op_agg=fmt(agg) if has_products_ops else fmt(0),
        )

    # Auto Liability (HNOA)
    hnoa_policy = policies_by_coverage.get(HNOA_COVERAGE)
    if hnoa_policy:
        limits = hnoa_policy.limits_retentions or {}
        aggregate = int(limits.get("aggregate_limit", 1000000))

        coi_data.auto_liability = COIAutoLiabilityInput(
            insurer_letter="A",
            policy_number=hnoa_policy.policy_number,
            effective_date=eff_display,
            expiration_date=exp_display,
            combined_single_limit=fmt(aggregate),
            bodily_injury_per_person=fmt(100_000),
            bodily_injury_per_accident=fmt(300_000),
            property_damage_per_accident=fmt(100_000),
        )

    # Additional coverages (Tech E&O, Cyber, D&O, EPL, Fiduciary, Media, Umbrella, Crime)
    additional_coverage_ids = [
        "technology-errors-and-omissions",
        "cyber-liability",
        "directors-and-officers",
        "employment-practices-liability",
        "fiduciary-liability",
        "media-liability",
        "custom-umbrella",
        "custom-crime",
    ]

    for coverage_id in additional_coverage_ids:
        policy = policies_by_coverage.get(coverage_id)
        if policy:
            limits = policy.limits_retentions or {}
            aggregate = limits.get("aggregate_limit", 0)
            per_claim = limits.get("per_occurrence_limit", aggregate)

            coi_data.additional_coverages.append(
                COIAdditionalCoverageInput(
                    name=COVERAGE_DISPLAY_NAMES.get(coverage_id, coverage_id),
                    policy_number=policy.policy_number,
                    effective_date=eff_display,
                    expiration_date=exp_display,
                    per_claim_limit=f"Per Claim: ${fmt(per_claim)}",
                    aggregate_limit=f"Aggregate: ${fmt(aggregate)}",
                )
            )

    try:
        pdf_bytes = PDFService.fill_pdf_form(COIPaths.COI, coi_data.to_form_fields())
        return PDFService.flatten_pdf(pdf_bytes)
    except Exception:
        logger.exception("Failed to generate COI PDF for %s", coi_number)
        return None


def _iso_to_display(iso_date: str) -> str:
    """Convert ISO date (YYYY-MM-DD) to MM/DD/YYYY display format."""
    try:
        from datetime import date as _date

        d = _date.fromisoformat(iso_date)
        return d.strftime("%m/%d/%Y")
    except (ValueError, TypeError):
        return iso_date
