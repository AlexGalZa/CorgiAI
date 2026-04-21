import logging
import re
from datetime import date, timedelta
from io import BytesIO
from typing import Optional, Any

from pdf.service import PDFService
from policies.models import Policy
from quotes.models import Quote

logger = logging.getLogger(__name__)
from common.constants import (  # noqa: E402
    COVERAGE_DISPLAY_NAMES,
    CGL_COVERAGE,
    HNOA_COVERAGE,
    EPL_COVERAGE,
    EO_COVERAGE,
    CYBER_COVERAGE,
    STATE_NAMES,
    NTIC_CARRIER,
    NTIC_NAIC_CODE,
    TECHRRG_CARRIER,
    TECHRRG_NAIC_CODE,
)
from common.utils import (  # noqa: E402
    format_currency,
    format_address,
    format_address_street,
    format_address_city_state_zip,
)
from documents_generator.constants import (  # noqa: E402
    CGLPolicyPaths,
    TechPolicyPaths,
    NTICPolicyPaths,
    COIPaths,
    TECH_COVERAGE_CONFIG,
    TECH_STATIC_FORMS,
    TECH_EPL_ENDORSEMENTS,
    TECH_EPL_CA_ENDORSEMENTS,
    TECH_EPL_NY_ENDORSEMENTS,
    TECH_AI_COVERAGE_ENDORSEMENT,
    TECH_HIPAA_PENALTIES_ENDORSEMENT,
    TECH_FINAL_ENDORSEMENTS,
    AI_COVERAGE_PDF_MAPPING,
    NTIC_COVERAGE_CONFIG,
    NTIC_TECH_STATIC_FORMS,
    NTIC_EPL_ENDORSEMENTS,
    NTIC_AI_COVERAGE_ENDORSEMENT,
    NTIC_FINAL_ENDORSEMENTS,
    NTIC_CA_ENDORSEMENTS,
    NTIC_NY_ENDORSEMENTS,
)
from documents_generator.schemas import (  # noqa: E402
    CGLMasterFormInput,
    CGLLimitsInput,
    HNOALimitsInput,
    TechMasterFormInput,
    TechCoverageInput,
    TechFormEntry,
    CertificateHolderInput,
    COIFormInput,
    COIProducerInput,
    COIInsurerInput,
    COIInsuredInput,
    COIGeneralLiabilityInput,
    COIAutoLiabilityInput,
    COIAdditionalCoverageInput,
)
from documents_generator.questionnaire_labels import (  # noqa: E402
    SECTION_LABELS,
    FIELD_LABELS,
    VALUE_DISPLAY,
    COVERAGE_DISPLAY_NAMES as QUESTIONNAIRE_COVERAGE_NAMES,
)


class DocumentsGeneratorService:
    @staticmethod
    def _get_subsidiary_fields(quote: Quote, effective_date: str) -> dict:
        fields = {}
        form_data = quote.form_data_snapshot or {}

        company_info = form_data.get("company_info") or form_data.get("companyInfo", {})
        structure = company_info.get("structure_operations") or company_info.get(
            "structureOperations", {}
        )
        subsidiaries = structure.get("subsidiaries", [])

        for i, sub in enumerate(subsidiaries[:9], start=1):
            jurisdiction_abbr = sub.get("jurisdiction", "")
            jurisdiction_name = STATE_NAMES.get(jurisdiction_abbr, jurisdiction_abbr)
            fields[f"covered_{i}_name"] = sub.get("name", "")
            fields[f"covered_{i}_jurisdiction"] = jurisdiction_name
            fields[f"covered_{i}_effective_date"] = effective_date

        return fields

    @staticmethod
    def _get_ai_coverage_fields(
        quote: Quote,
        policy_number: str,
        effective_date: str,
        per_occurrence: int,
        aggregate: int,
        retention: int,
    ) -> dict:
        fields = {
            "endorsement_number": policy_number,
            "endorsement_effective_date": effective_date,
        }

        tech_eo_data = quote.coverage_data.get(EO_COVERAGE, {})
        ai_coverage_options = tech_eo_data.get("ai_coverage_options", [])

        for option_id, row_num in AI_COVERAGE_PDF_MAPPING.items():
            if option_id in ai_coverage_options:
                fields[f"per_ocurrence_{row_num}"] = format_currency(per_occurrence)
                fields[f"aggregate_limit_{row_num}"] = format_currency(aggregate)
                fields[f"retention_{row_num}"] = format_currency(retention)

        return fields

    @staticmethod
    def _has_ai_coverage(quote: Quote) -> bool:
        tech_eo_data = quote.coverage_data.get(EO_COVERAGE, {})
        return (
            tech_eo_data.get("uses_ai", False)
            and tech_eo_data.get("wants_ai_coverage", False)
            and len(tech_eo_data.get("ai_coverage_options", [])) > 0
        )

    @staticmethod
    def _has_hipaa_penalties_coverage(quote: Quote) -> bool:
        cyber_data = quote.coverage_data.get(CYBER_COVERAGE, {})
        regulations = cyber_data.get("regulations_subject_to", []) or []
        return "hipaa" in regulations and cyber_data.get(
            "wants_hipaa_penalties_coverage", False
        )

    @staticmethod
    def generate_cgl_policy_for_policy(
        policy: Policy, all_policies: list[Policy] = None
    ) -> Optional[bytes]:
        coverages = policy.quote.coverages
        include_cgl = CGL_COVERAGE in coverages
        include_hnoa = HNOA_COVERAGE in coverages

        if not include_cgl and not include_hnoa:
            return None

        company = policy.quote.company

        policies_by_coverage = {}
        if all_policies:
            policies_by_coverage = {p.coverage_type: p for p in all_policies}

        cgl_policy = policies_by_coverage.get(CGL_COVERAGE, policy)
        cgl_limits_data = cgl_policy.limits_retentions or {}
        cgl_questionnaire = policy.quote.coverage_data.get(CGL_COVERAGE, {})
        cgl_aggregate = int(
            cgl_limits_data.get("aggregate_limit")
            or cgl_limits_data.get("aggregateLimit")
            or 1000000
        )
        cgl_per_occurrence = int(
            cgl_limits_data.get("per_occurrence_limit")
            or cgl_limits_data.get("perOccurrenceLimit")
            or cgl_aggregate
        )
        cgl_limits = CGLLimitsInput(
            per_occurrence=cgl_per_occurrence,
            aggregate=cgl_aggregate,
            retention=int(cgl_limits_data.get("retention") or 10000),
            has_products_completed_operations=cgl_questionnaire.get(
                "has_products_completed_operations", False
            ),
        )

        hnoa_data = None
        if include_hnoa:
            hnoa_policy = policies_by_coverage.get(HNOA_COVERAGE, policy)
            hnoa_limits_data = hnoa_policy.limits_retentions or {}
            hnoa_aggregate = int(
                hnoa_limits_data.get("aggregate_limit")
                or hnoa_limits_data.get("aggregateLimit")
                or 1000000
            )
            hnoa_per_occurrence = int(
                hnoa_limits_data.get("per_occurrence_limit")
                or hnoa_limits_data.get("perOccurrenceLimit")
                or hnoa_aggregate
            )
            hnoa_data = HNOALimitsInput(
                per_occurrence=hnoa_per_occurrence,
                aggregate=hnoa_aggregate,
                retention=int(hnoa_limits_data.get("retention") or 10000),
            )

        form_data = CGLMasterFormInput(
            name_insured=company.entity_legal_name,
            policy_start_date=policy.effective_date,
            policy_end_date=policy.expiration_date,
            insured_address=format_address(company.business_address),
            retroactive_date=policy.effective_date,
            cgl_policy_number=policy.policy_number,
            cgl=cgl_limits,
            hnoa=hnoa_data,
        )

        filled_master = PDFService.fill_pdf_form(
            CGLPolicyPaths.MASTER, form_data.to_form_fields()
        )

        additional_pdfs = []
        if include_cgl:
            additional_pdfs.append(CGLPolicyPaths.POLICY)
        if include_hnoa:
            additional_pdfs.append(CGLPolicyPaths.HNOA)

        pdf_bytes = PDFService.merge_pdfs_with_bytes(filled_master, additional_pdfs)
        return PDFService.flatten_pdf(pdf_bytes) if pdf_bytes else None

    @staticmethod
    def generate_tech_policy_for_policy(
        policy: Policy, all_policies: list[Policy] = None
    ) -> Optional[bytes]:
        coverages = policy.quote.coverages
        tech_coverage_keys = [c for c in coverages if c in TECH_COVERAGE_CONFIG]

        if not tech_coverage_keys:
            return None

        company = policy.quote.company
        company_state = (
            company.business_address.state if company.business_address else None
        )

        policies_by_coverage = {}
        if all_policies:
            policies_by_coverage = {p.coverage_type: p for p in all_policies}

        tech_coverages = []
        form_entries = []

        for form in TECH_STATIC_FORMS:
            form_entries.append(TechFormEntry(name=form["name"], code=form["code"]))

        for coverage_key in tech_coverage_keys:
            config = TECH_COVERAGE_CONFIG[coverage_key]
            coverage_policy = policies_by_coverage.get(coverage_key, policy)
            limits_data = coverage_policy.limits_retentions or {}
            aggregate = int(limits_data.get("aggregate_limit", 1000000))
            per_occurrence = int(limits_data.get("per_occurrence_limit", aggregate))
            retention = int(limits_data.get("retention", 10000))

            tech_coverages.append(
                TechCoverageInput(
                    name=config["name"],
                    policy_number=coverage_policy.policy_number,
                    form_code=config["form_code"],
                    per_occurrence=per_occurrence,
                    aggregate=aggregate,
                    retention=retention,
                )
            )

            form_entries.append(
                TechFormEntry(name=config["name"], code=config["form_code"])
            )

        if EPL_COVERAGE in tech_coverage_keys:
            for form in TECH_EPL_ENDORSEMENTS:
                form_entries.append(TechFormEntry(name=form["name"], code=form["code"]))

            if company_state == "CA":
                for form in TECH_EPL_CA_ENDORSEMENTS:
                    form_entries.append(
                        TechFormEntry(name=form["name"], code=form["code"])
                    )
            elif company_state == "NY":
                for form in TECH_EPL_NY_ENDORSEMENTS:
                    form_entries.append(
                        TechFormEntry(name=form["name"], code=form["code"])
                    )

        has_ai_coverage = (
            EO_COVERAGE in tech_coverage_keys
            and DocumentsGeneratorService._has_ai_coverage(policy.quote)
        )
        if has_ai_coverage:
            form_entries.append(
                TechFormEntry(
                    name=TECH_AI_COVERAGE_ENDORSEMENT["name"],
                    code=TECH_AI_COVERAGE_ENDORSEMENT["code"],
                )
            )

        has_hipaa_penalties_coverage = (
            CYBER_COVERAGE in tech_coverage_keys
            and DocumentsGeneratorService._has_hipaa_penalties_coverage(policy.quote)
        )
        if has_hipaa_penalties_coverage:
            form_entries.append(
                TechFormEntry(
                    name=TECH_HIPAA_PENALTIES_ENDORSEMENT["name"],
                    code=TECH_HIPAA_PENALTIES_ENDORSEMENT["code"],
                )
            )

        for form in TECH_FINAL_ENDORSEMENTS:
            form_entries.append(TechFormEntry(name=form["name"], code=form["code"]))

        form_data = TechMasterFormInput(
            name_insured=company.entity_legal_name,
            policy_start_date=policy.effective_date,
            policy_end_date=policy.expiration_date,
            insured_address=format_address(company.business_address),
            retroactive_date=policy.effective_date,
            coverages=tech_coverages,
            form_entries=form_entries,
        )

        endorsement_fields = {
            "endorsement_number": policy.policy_number,
            "endorsement_effective_date": policy.effective_date.strftime("%m/%d/%Y"),
        }

        pdf_configs = [
            {"path": TechPolicyPaths.MASTER, "form_data": form_data.to_form_fields()},
            {"path": TechPolicyPaths.TERMS},
        ]

        for coverage_key in tech_coverage_keys:
            pdf_configs.append({"path": TECH_COVERAGE_CONFIG[coverage_key]["path"]})

        if EPL_COVERAGE in tech_coverage_keys:
            pdf_configs.append(
                {
                    "path": TechPolicyPaths.EPL_THIRD_PARTY_EXCLUSION,
                    "form_data": endorsement_fields,
                }
            )

            if company_state == "CA":
                pdf_configs.append(
                    {
                        "path": TechPolicyPaths.EPL_CA_SERVICE_SUIT,
                        "form_data": endorsement_fields,
                    }
                )
            elif company_state == "NY":
                pdf_configs.append(
                    {
                        "path": TechPolicyPaths.EPL_NY_SERVICE_SUIT,
                        "form_data": endorsement_fields,
                    }
                )
                pdf_configs.append(
                    {
                        "path": TechPolicyPaths.EPL_NY_ARBITRATION,
                        "form_data": endorsement_fields,
                    }
                )
                pdf_configs.append(
                    {
                        "path": TechPolicyPaths.EPL_NY_EXTENDED_REPORTING,
                        "form_data": endorsement_fields,
                    }
                )

        if has_ai_coverage:
            eo_policy = policies_by_coverage.get(EO_COVERAGE, policy)
            tech_eo_limits = eo_policy.limits_retentions or {}
            tech_eo_aggregate = int(tech_eo_limits.get("aggregate_limit", 1000000))
            tech_eo_per_occurrence = int(
                tech_eo_limits.get("per_occurrence_limit", tech_eo_aggregate)
            )
            tech_eo_retention = int(tech_eo_limits.get("retention", 10000))

            ai_coverage_fields = DocumentsGeneratorService._get_ai_coverage_fields(
                policy.quote,
                policy.policy_number,
                policy.effective_date.strftime("%m/%d/%Y"),
                tech_eo_per_occurrence,
                tech_eo_aggregate,
                tech_eo_retention,
            )
            pdf_configs.append(
                {
                    "path": TechPolicyPaths.AI_COVERAGE,
                    "form_data": ai_coverage_fields,
                }
            )

        if has_hipaa_penalties_coverage:
            cyber_policy = policies_by_coverage.get(CYBER_COVERAGE, policy)
            cyber_limits = cyber_policy.limits_retentions or {}
            cyber_aggregate = int(cyber_limits.get("aggregate_limit", 1000000))
            cyber_retention = int(cyber_limits.get("retention", 10000))

            hipaa_fields = {
                **endorsement_fields,
                "endorsement_aggregate_limit": format_currency(cyber_aggregate),
                "endorsement_retention": format_currency(cyber_retention),
            }
            pdf_configs.append(
                {
                    "path": TechPolicyPaths.HIPAA_PENALTIES,
                    "form_data": hipaa_fields,
                }
            )

        subsidiary_fields = DocumentsGeneratorService._get_subsidiary_fields(
            policy.quote, policy.effective_date.strftime("%m/%d/%Y")
        )
        excluded_subsidiary_form_data = {**endorsement_fields, **subsidiary_fields}

        pdf_configs.append(
            {
                "path": TechPolicyPaths.EXCLUDED_SUBSIDIARY,
                "form_data": excluded_subsidiary_form_data,
            }
        )

        pdf_bytes = PDFService.merge_pdfs_with_form_data(pdf_configs)
        return PDFService.flatten_pdf(pdf_bytes) if pdf_bytes else None

    @staticmethod
    def generate_ntic_cgl_policy_for_policy(
        policy: Policy, all_policies: list[Policy] = None
    ) -> Optional[bytes]:
        coverages = policy.quote.coverages
        include_cgl = CGL_COVERAGE in coverages
        include_hnoa = HNOA_COVERAGE in coverages

        if not include_cgl and not include_hnoa:
            return None

        company = policy.quote.company
        policies_by_coverage = (
            {p.coverage_type: p for p in all_policies} if all_policies else {}
        )

        cgl_policy = policies_by_coverage.get(CGL_COVERAGE, policy)
        cgl_limits_data = cgl_policy.limits_retentions or {}
        cgl_aggregate = int(
            cgl_limits_data.get("aggregate_limit")
            or cgl_limits_data.get("aggregateLimit")
            or 1000000
        )
        cgl_per_occurrence = int(
            cgl_limits_data.get("per_occurrence_limit")
            or cgl_limits_data.get("perOccurrenceLimit")
            or cgl_aggregate
        )
        cgl_questionnaire = policy.quote.coverage_data.get(CGL_COVERAGE, {})
        cgl_limits = CGLLimitsInput(
            per_occurrence=cgl_per_occurrence,
            aggregate=cgl_aggregate,
            retention=int(cgl_limits_data.get("retention") or 10000),
            has_products_completed_operations=cgl_questionnaire.get(
                "has_products_completed_operations", False
            ),
        )

        hnoa_data = None
        if include_hnoa:
            hnoa_policy = policies_by_coverage.get(HNOA_COVERAGE, policy)
            hnoa_limits_data = hnoa_policy.limits_retentions or {}
            hnoa_aggregate = int(
                hnoa_limits_data.get("aggregate_limit")
                or hnoa_limits_data.get("aggregateLimit")
                or 1000000
            )
            hnoa_per_occurrence = int(
                hnoa_limits_data.get("per_occurrence_limit")
                or hnoa_limits_data.get("perOccurrenceLimit")
                or hnoa_aggregate
            )
            hnoa_data = HNOALimitsInput(
                per_occurrence=hnoa_per_occurrence,
                aggregate=hnoa_aggregate,
                retention=int(hnoa_limits_data.get("retention") or 10000),
            )

        master_fields = CGLMasterFormInput(
            name_insured=company.entity_legal_name,
            policy_start_date=policy.effective_date,
            policy_end_date=policy.expiration_date,
            insured_address=format_address(company.business_address),
            retroactive_date=policy.effective_date,
            cgl_policy_number=policy.policy_number,
            cgl=cgl_limits,
            hnoa=hnoa_data,
        ).to_form_fields()
        master_fields.update(
            {
                "form_name_a1": "Master Declarations Page",
                "form_code_a2": "CORG-NTIC-0001",
                "form_name_b1": "Commercial General Liability Policy",
                "form_name_b2": "CORG-NTIC-0100",
            }
        )
        if include_hnoa:
            master_fields.update(
                {
                    "form_name_c1": "Hired and Non-Owned Auto Liability Endorsement",
                    "form_name_c2": "CORGI-NTIC-1033",
                }
            )

        pdf_configs = [{"path": NTICPolicyPaths.CGL_MASTER, "form_data": master_fields}]

        if include_cgl:
            pdf_configs.append({"path": NTICPolicyPaths.CGL})
        if include_hnoa:
            pdf_configs.append({"path": NTICPolicyPaths.HNOA})

        pdf_bytes = PDFService.merge_pdfs_with_form_data(pdf_configs)
        return PDFService.flatten_pdf(pdf_bytes) if pdf_bytes else None

    @staticmethod
    def generate_ntic_tech_policy_for_policy(
        policy: Policy, all_policies: list[Policy] = None
    ) -> Optional[bytes]:
        coverages = policy.quote.coverages
        ntic_tech_coverage_keys = [
            c
            for c in coverages
            if c in NTIC_COVERAGE_CONFIG and c not in {CGL_COVERAGE}
        ]

        if not ntic_tech_coverage_keys:
            return None

        quote = policy.quote
        company = quote.company
        company_state = (
            company.business_address.state if company.business_address else None
        )

        policies_by_coverage = (
            {p.coverage_type: p for p in all_policies} if all_policies else {}
        )

        tech_coverages = []
        form_entries = []

        for form in NTIC_TECH_STATIC_FORMS:
            form_entries.append(TechFormEntry(name=form["name"], code=form["code"]))

        for coverage_key in ntic_tech_coverage_keys:
            config = NTIC_COVERAGE_CONFIG[coverage_key]
            coverage_policy = policies_by_coverage.get(coverage_key, policy)
            limits_data = coverage_policy.limits_retentions or {}
            aggregate = int(limits_data.get("aggregate_limit", 1000000))
            per_occurrence = int(limits_data.get("per_occurrence_limit", aggregate))
            retention = int(limits_data.get("retention", 10000))

            tech_coverages.append(
                TechCoverageInput(
                    name=config["name"],
                    policy_number=coverage_policy.policy_number,
                    form_code=config["form_code"],
                    per_occurrence=per_occurrence,
                    aggregate=aggregate,
                    retention=retention,
                )
            )

            form_entries.append(
                TechFormEntry(name=config["name"], code=config["form_code"])
            )

        if EPL_COVERAGE in ntic_tech_coverage_keys:
            for form in NTIC_EPL_ENDORSEMENTS:
                form_entries.append(TechFormEntry(name=form["name"], code=form["code"]))

        has_ai_coverage = (
            EO_COVERAGE in ntic_tech_coverage_keys
            and DocumentsGeneratorService._has_ai_coverage(quote)
        )
        if has_ai_coverage:
            form_entries.append(
                TechFormEntry(
                    name=NTIC_AI_COVERAGE_ENDORSEMENT["name"],
                    code=NTIC_AI_COVERAGE_ENDORSEMENT["code"],
                )
            )

        for form in NTIC_FINAL_ENDORSEMENTS:
            form_entries.append(TechFormEntry(name=form["name"], code=form["code"]))

        if company_state == "CA":
            for form in NTIC_CA_ENDORSEMENTS:
                form_entries.append(TechFormEntry(name=form["name"], code=form["code"]))
        elif company_state == "NY":
            for form in NTIC_NY_ENDORSEMENTS:
                form_entries.append(TechFormEntry(name=form["name"], code=form["code"]))

        master_form_data = TechMasterFormInput(
            name_insured=company.entity_legal_name,
            policy_start_date=policy.effective_date,
            policy_end_date=policy.expiration_date,
            insured_address=format_address(company.business_address),
            retroactive_date=policy.effective_date,
            coverages=tech_coverages,
            form_entries=form_entries,
        )

        endorsement_fields = {
            "endorsement_number": policy.policy_number,
            "endorsement_effective_date": policy.effective_date.strftime("%m/%d/%Y"),
        }

        pdf_configs = [
            {
                "path": NTICPolicyPaths.TECH_MASTER,
                "form_data": master_form_data.to_form_fields(),
            }
        ]

        for coverage_key in ntic_tech_coverage_keys:
            pdf_configs.append({"path": NTIC_COVERAGE_CONFIG[coverage_key]["path"]})

        if EPL_COVERAGE in ntic_tech_coverage_keys:
            pdf_configs.append(
                {
                    "path": NTICPolicyPaths.EPL_THIRD_PARTY_EXCLUSION,
                    "form_data": endorsement_fields,
                }
            )

        if has_ai_coverage:
            eo_policy = policies_by_coverage.get(EO_COVERAGE, policy)
            eo_limits = eo_policy.limits_retentions or {}
            eo_aggregate = int(eo_limits.get("aggregate_limit", 1000000))
            eo_per_occurrence = int(eo_limits.get("per_occurrence_limit", eo_aggregate))
            eo_retention = int(eo_limits.get("retention", 10000))
            ai_fields = DocumentsGeneratorService._get_ai_coverage_fields(
                quote,
                policy.policy_number,
                policy.effective_date.strftime("%m/%d/%Y"),
                eo_per_occurrence,
                eo_aggregate,
                eo_retention,
            )
            ai_fields.pop("endorsement_number", None)
            ai_fields.pop("endorsement_effective_date", None)
            pdf_configs.append(
                {"path": NTICPolicyPaths.EO_AI_COVERAGE, "form_data": ai_fields}
            )

        subsidiary_fields = DocumentsGeneratorService._get_subsidiary_fields(
            quote, policy.effective_date.strftime("%m/%d/%Y")
        )
        pdf_configs.append(
            {
                "path": NTICPolicyPaths.EXCLUDED_SUBSIDIARY,
                "form_data": subsidiary_fields,
            }
        )

        if company_state == "CA":
            pdf_configs.append(
                {
                    "path": NTICPolicyPaths.CA_SERVICE_SUIT,
                    "form_data": endorsement_fields,
                }
            )
        elif company_state == "NY":
            pdf_configs.append(
                {
                    "path": NTICPolicyPaths.NY_SERVICE_SUIT,
                    "form_data": endorsement_fields,
                }
            )

        pdf_bytes = PDFService.merge_pdfs_with_form_data(pdf_configs)
        return PDFService.flatten_pdf(pdf_bytes) if pdf_bytes else None

    @staticmethod
    def generate_coi_for_policies(
        policies: list[Policy],
        coi_number: str,
        holder_info: Optional[CertificateHolderInput] = None,
    ) -> Optional[bytes]:
        if not policies:
            return None

        first_policy = policies[0]
        quote = first_policy.quote
        company = quote.company
        address = company.business_address if company else None
        fmt = format_currency

        non_brokered = [p for p in policies if not p.is_brokered]
        if non_brokered:
            any_ntic = any(p.carrier == NTIC_CARRIER for p in non_brokered)
            carrier_name = NTIC_CARRIER if any_ntic else non_brokered[0].carrier
        else:
            carrier_name = TECHRRG_CARRIER

        naic_code = (
            NTIC_NAIC_CODE if carrier_name == NTIC_CARRIER else TECHRRG_NAIC_CODE
        )

        # NAICS (industry classification) — required on NTIC templates; harmless on others.
        naics_code = getattr(company, "naics_code", None) or ""
        description = f"NAICS Code: {naics_code}" if naics_code else ""

        coi_data = COIFormInput(
            certificate_date=first_policy.effective_date.strftime("%m/%d/%Y"),
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
            holder=holder_info,
        )

        policies_by_coverage = {p.coverage_type: p for p in policies}

        cgl_policy = policies_by_coverage.get(CGL_COVERAGE)
        if cgl_policy:
            limits = cgl_policy.limits_retentions
            cgl_questionnaire = quote.coverage_data.get(CGL_COVERAGE, {})
            agg = int(limits.get("aggregate_limit", 1000000))
            occ = int(limits.get("per_occurrence_limit", agg))
            has_products_ops = cgl_questionnaire.get(
                "has_products_completed_operations", False
            )

            coi_data.general_liability = COIGeneralLiabilityInput(
                insurer_letter="A",
                policy_number=cgl_policy.policy_number,
                effective_date=cgl_policy.effective_date.strftime("%m/%d/%Y"),
                expiration_date=cgl_policy.expiration_date.strftime("%m/%d/%Y"),
                each_occurrence=fmt(occ),
                damage_to_rented=fmt(100_000),
                med_exp=fmt(5_000),
                general_aggregate=fmt(agg),
                products_comp_op_agg=fmt(agg) if has_products_ops else fmt(0),
            )

        hnoa_policy = policies_by_coverage.get(HNOA_COVERAGE)
        if hnoa_policy:
            limits = hnoa_policy.limits_retentions
            aggregate = int(limits.get("aggregate_limit", 1000000))

            coi_data.auto_liability = COIAutoLiabilityInput(
                insurer_letter="A",
                policy_number=hnoa_policy.policy_number,
                effective_date=hnoa_policy.effective_date.strftime("%m/%d/%Y"),
                expiration_date=hnoa_policy.expiration_date.strftime("%m/%d/%Y"),
                combined_single_limit=fmt(aggregate),
                bodily_injury_per_person=fmt(100_000),
                bodily_injury_per_accident=fmt(300_000),
                property_damage_per_accident=fmt(100_000),
            )

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
                limits = policy.limits_retentions
                aggregate = limits.get("aggregate_limit", 0)
                per_claim = limits.get("per_occurrence_limit", aggregate)

                coi_data.additional_coverages.append(
                    COIAdditionalCoverageInput(
                        name=COVERAGE_DISPLAY_NAMES.get(coverage_id, coverage_id),
                        policy_number=policy.policy_number,
                        effective_date=policy.effective_date.strftime("%m/%d/%Y"),
                        expiration_date=policy.expiration_date.strftime("%m/%d/%Y"),
                        per_claim_limit=f"Per Claim: ${fmt(per_claim)}",
                        aggregate_limit=f"Aggregate: ${fmt(aggregate)}",
                    )
                )

        pdf_bytes = PDFService.fill_pdf_form(COIPaths.COI, coi_data.to_form_fields())
        return PDFService.flatten_pdf(pdf_bytes)

    @staticmethod
    def regenerate_policy_doc_with_endorsement(
        policy: Policy,
        additional_insured,
        user=None,
        organization=None,
    ) -> Optional[dict]:
        """
        Regenerate the main policy document with an Additional Insured endorsement
        page appended, upload the resulting PDF to S3, and version it as a new
        UserDocument row (category='endorsement').

        This is the auto-generation path triggered when a customer adds an
        Additional Insured via the portal, replacing the previous manual
        Django-admin workflow.

        Args:
            policy: The ``policies.models.Policy`` the AI was added to.
            additional_insured: The ``certificates.models.AdditionalInsured``
                record just created.
            user: Optional owner of the resulting document. Falls back to
                ``additional_insured.created_by``.
            organization: Optional organisation. Falls back to
                ``additional_insured.organization``.

        Returns:
            ``{'s3_key': ..., 's3_url': ..., 'filename': ..., 'document_id': ...}``
            on success, or ``None`` on failure. Failure is logged but never
            raised — auto-regeneration must not block AI creation.
        """
        from s3.schemas import UploadFileInput
        from s3.service import S3Service
        from users.models import UserDocument

        try:
            from documents_generator.endorsement import generate_endorsement
        except Exception:
            logger.exception(
                "Could not import endorsement generator for policy %s", policy.pk
            )
            return None

        owner = user or getattr(additional_insured, "created_by", None)
        org = organization or getattr(additional_insured, "organization", None)

        # Build an AI-flavoured change payload for the existing endorsement
        # generator. Treat it as a "named insured extension" so the standard
        # before/after page renders cleanly without new template work.
        changes = {
            "type": "name_change",
            "effective_date": date.today(),
            "reason": f"Addition of Additional Insured: {additional_insured.name}",
            "name_change": {
                "before": (
                    policy.insured_legal_name
                    or (
                        policy.quote.company.entity_legal_name
                        if policy.quote and policy.quote.company
                        else "—"
                    )
                ),
                "after": (
                    f"{policy.insured_legal_name or ''} + Additional Insured: "
                    f"{additional_insured.name}"
                    + (
                        f" ({additional_insured.address})"
                        if additional_insured.address
                        else ""
                    )
                ).strip(" +"),
            },
        }

        try:
            endorsement_pdf = generate_endorsement(policy, changes)
        except Exception:
            logger.exception(
                "Failed to generate AI endorsement PDF for policy %s / AI %s",
                policy.pk,
                getattr(additional_insured, "pk", None),
            )
            return None

        if not endorsement_pdf:
            return None

        # Try to merge the endorsement page onto the existing main policy doc
        # so the regenerated file is the full policy + endorsement. If the
        # main doc can't be fetched, fall back to uploading the endorsement
        # on its own — it still supersedes the manual Django step.
        merged_bytes = DocumentsGeneratorService._merge_endorsement_into_policy(
            policy, endorsement_pdf
        )
        final_bytes = merged_bytes or endorsement_pdf

        filename = f"Policy {policy.policy_number} with AI Endorsement - {additional_insured.name}.pdf"

        try:
            upload = S3Service.upload_file(
                UploadFileInput(
                    file=BytesIO(final_bytes),
                    path_prefix=f"policies/{policy.id}/documents",
                    original_filename=filename,
                    content_type="application/pdf",
                )
            )
        except Exception:
            logger.exception(
                "S3 upload failed for AI endorsement on policy %s", policy.pk
            )
            return None

        if not upload:
            logger.warning(
                "S3 upload returned None for AI endorsement on policy %s",
                policy.pk,
            )
            return None

        document_id = None
        if owner is not None:
            try:
                doc_kwargs = dict(
                    user=owner,
                    category="endorsement",
                    title=f"Policy Document + AI Endorsement ({additional_insured.name})",
                    policy_numbers=[policy.policy_number],
                    effective_date=policy.effective_date,
                    expiration_date=policy.expiration_date,
                    file_type="policy-endorsement",
                    original_filename=filename,
                    file_size=len(final_bytes),
                    mime_type="application/pdf",
                    s3_key=upload["s3_key"],
                    s3_url=upload["s3_url"],
                )
                if org is not None:
                    doc_kwargs["organization"] = org
                doc = UserDocument.objects.create(**doc_kwargs)
                document_id = doc.pk
            except Exception:
                logger.exception(
                    "Failed to create UserDocument for AI endorsement on policy %s",
                    policy.pk,
                )

        logger.info(
            "Regenerated policy doc with AI endorsement for policy %s (AI=%s, s3_key=%s)",
            policy.policy_number,
            getattr(additional_insured, "pk", None),
            upload["s3_key"],
        )

        return {
            "s3_key": upload["s3_key"],
            "s3_url": upload["s3_url"],
            "filename": filename,
            "document_id": document_id,
        }

    @staticmethod
    def _merge_endorsement_into_policy(
        policy: Policy, endorsement_pdf: bytes
    ) -> Optional[bytes]:
        """Download the most recent main policy PDF from S3 and append the
        endorsement page. Returns merged bytes, or None if the main doc
        can't be found / downloaded."""
        from s3.service import S3Service
        from users.models import UserDocument

        try:
            latest_main = (
                UserDocument.objects.filter(
                    policy_numbers__contains=[policy.policy_number],
                    category="policy",
                )
                .exclude(s3_key="")
                .order_by("-created_at")
                .first()
            )
        except Exception:
            logger.exception(
                "Could not query existing policy docs for %s", policy.policy_number
            )
            return None

        if not latest_main or not latest_main.s3_key:
            return None

        try:
            main_bytes = S3Service.download_file(latest_main.s3_key)
        except Exception:
            logger.exception(
                "Could not download main policy doc %s for merge",
                latest_main.s3_key,
            )
            return None

        if not main_bytes:
            return None

        try:
            return PDFService.merge_pdfs_with_form_data(
                [
                    {"bytes": main_bytes},
                    {"bytes": endorsement_pdf},
                ]
            )
        except Exception:
            logger.exception(
                "Failed to merge endorsement onto main policy %s",
                policy.policy_number,
            )
            return None

    @staticmethod
    def generate_sample_documents_for_quote(quote: Quote) -> dict:
        effective_date = quote.quoted_at.date() if quote.quoted_at else date.today()
        expiration_date = effective_date + timedelta(days=365)
        sample_policy_number = f"SAMPLE-{quote.quote_number}"

        class MockPolicy:
            def __init__(self, coverage_type, limits_retentions):
                self.quote = quote
                self.effective_date = effective_date
                self.expiration_date = expiration_date
                self.policy_number = sample_policy_number
                self.coverage_type = coverage_type
                self.limits_retentions = limits_retentions

        all_limits = quote.limits_retentions or {}
        coverages = quote.coverages or []

        mock_policies = []
        for coverage_key in coverages:
            limits = all_limits.get(coverage_key, {})
            mock_policies.append(MockPolicy(coverage_key, limits))

        result = {"cgl": None, "tech": None}

        cgl_coverages = {CGL_COVERAGE, HNOA_COVERAGE}
        if cgl_coverages & set(coverages):
            first_cgl = next(
                (mp for mp in mock_policies if mp.coverage_type in cgl_coverages),
                mock_policies[0] if mock_policies else None,
            )
            if first_cgl:
                cgl_bytes = DocumentsGeneratorService.generate_cgl_policy_for_policy(
                    first_cgl, mock_policies
                )
                if cgl_bytes:
                    result["cgl"] = PDFService.add_watermark(cgl_bytes)

        tech_coverage_keys = set(TECH_COVERAGE_CONFIG.keys())
        if tech_coverage_keys & set(coverages):
            first_tech = next(
                (mp for mp in mock_policies if mp.coverage_type in tech_coverage_keys),
                mock_policies[0] if mock_policies else None,
            )
            if first_tech:
                tech_bytes = DocumentsGeneratorService.generate_tech_policy_for_policy(
                    first_tech, mock_policies
                )
                if tech_bytes:
                    result["tech"] = PDFService.add_watermark(tech_bytes)

        return result

    @staticmethod
    def generate_questionnaire_text_for_quote(quote: Quote) -> str:
        form_data = quote.form_data_snapshot or {}
        lines = []

        lines.append("=" * 80)
        lines.append("QUOTE QUESTIONNAIRE")
        lines.append("=" * 80)
        lines.append(f"Quote Number: {quote.quote_number}")
        lines.append(f"Submitted: {quote.created_at.strftime('%m/%d/%Y')}")
        lines.append("")

        def camel_to_snake(name: str) -> str:
            s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
            return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

        def format_value(val: Any) -> str:
            if val is None:
                return ""
            if isinstance(val, bool):
                return VALUE_DISPLAY.get(val, str(val))
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                if val >= 1000:
                    return f"${val:,.0f}"
                return str(val)
            if isinstance(val, str):
                return VALUE_DISPLAY.get(val, val)
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return str(val)

        def get_field_label(key: str) -> str:
            return FIELD_LABELS.get(key, key.replace("_", " ").title())

        def render_section(data: dict, indent: int = 0) -> list:
            result = []
            prefix = "  " * indent
            for key, value in data.items():
                snake_key = camel_to_snake(key)
                if value is None or value == "" or value == []:
                    continue
                if isinstance(value, dict):
                    section_label = SECTION_LABELS.get(
                        snake_key, snake_key.replace("_", " ").title()
                    )
                    result.append(f"{prefix}{section_label}")
                    result.append(f"{prefix}{'-' * len(section_label)}")
                    result.extend(render_section(value, indent + 1))
                    result.append("")
                else:
                    label = get_field_label(snake_key)
                    formatted = format_value(value)
                    if formatted:
                        result.append(f"{prefix}{snake_key}: {formatted}")
                        result.append(f"{prefix}  Q: {label}")
            return result

        company_info = form_data.get("company_info") or form_data.get("companyInfo", {})
        if company_info:
            lines.append("-" * 80)
            lines.append(SECTION_LABELS.get("company_info", "COMPANY INFORMATION"))
            lines.append("-" * 80)
            lines.append("")
            lines.extend(render_section(company_info))

        coverages = form_data.get("coverages", [])
        if coverages:
            lines.append("-" * 80)
            lines.append("SELECTED COVERAGES")
            lines.append("-" * 80)
            for cov in coverages:
                display_name = QUESTIONNAIRE_COVERAGE_NAMES.get(cov, cov)
                lines.append(f"  - {display_name}")
            lines.append("")

        coverage_sections = [
            ("commercial_general_liability", "commercialGeneralLiability"),
            ("directors_officers", "directorsOfficers"),
            ("cyber_liability", "cyberLiability"),
            ("tech_errors_omissions", "techErrorsOmissions"),
            ("media_liability", "mediaLiability"),
            ("employment_practices_liability", "employmentPracticesLiability"),
            ("fiduciary_liability", "fiduciaryLiability"),
            ("hired_non_owned_auto", "hiredNonOwnedAuto"),
            ("custom_commercial_auto", "customCommercialAuto"),
        ]

        for snake_key, camel_key in coverage_sections:
            section_data = form_data.get(snake_key) or form_data.get(camel_key, {})
            if section_data:
                lines.append("-" * 80)
                lines.append(
                    SECTION_LABELS.get(snake_key, snake_key.replace("_", " ").upper())
                )
                lines.append("-" * 80)
                lines.append("")
                lines.extend(render_section(section_data))

        claims_history = form_data.get("claims_history") or form_data.get(
            "claimsHistory", {}
        )
        if claims_history:
            lines.append("-" * 80)
            lines.append(SECTION_LABELS.get("claims_history", "CLAIMS HISTORY"))
            lines.append("-" * 80)
            lines.append("")
            lines.extend(render_section(claims_history))

        limits_retentions = form_data.get("limits_retentions") or form_data.get(
            "limitsRetentions", {}
        )
        if limits_retentions:
            lines.append("-" * 80)
            lines.append(SECTION_LABELS.get("limits_retentions", "LIMITS & RETENTIONS"))
            lines.append("-" * 80)
            lines.append("")
            for cov_key, limits in limits_retentions.items():
                camel_to_snake(cov_key)
                cov_name = QUESTIONNAIRE_COVERAGE_NAMES.get(
                    cov_key, cov_key.replace("-", " ").title()
                )
                lines.append(f"  {cov_name}:")
                if isinstance(limits, dict):
                    for limit_key, limit_val in limits.items():
                        snake_limit = camel_to_snake(limit_key)
                        get_field_label(snake_limit)
                        if limit_val is not None:
                            lines.append(
                                f"    {snake_limit}: ${limit_val:,.0f}"
                                if isinstance(limit_val, (int, float))
                                else f"    {snake_limit}: {limit_val}"
                            )
            lines.append("")

        notices = form_data.get("notices_signatures") or form_data.get(
            "noticesSignatures", {}
        )
        if notices:
            lines.append("-" * 80)
            lines.append(
                SECTION_LABELS.get("notices_signatures", "NOTICES & SIGNATURES")
            )
            lines.append("-" * 80)
            lines.append("")
            lines.extend(render_section(notices))

        lines.append("=" * 80)
        lines.append("END OF QUESTIONNAIRE")
        lines.append("=" * 80)

        return "\n".join(lines)
