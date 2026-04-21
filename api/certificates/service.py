import logging
import math
from io import BytesIO
from typing import Optional

from django.db.models import Q
from django.utils import timezone

from certificates.constants import ADDITIONAL_INSURED_TEXT, ENDORSEMENT_TEXT
from certificates.models import CustomCertificate
from common.constants import (
    COVERAGE_DISPLAY_NAMES,
    CGL_COVERAGE,
    HNOA_COVERAGE,
    NTIC_CARRIER,
    NTIC_NAIC_CODE,
    TECHRRG_CARRIER,
    TECHRRG_NAIC_CODE,
)
from common.exceptions import AccessDeniedError
from common.utils import (
    format_currency,
    format_address_street,
    format_address_city_state_zip,
)
from documents_generator.constants import COIPaths
from documents_generator.schemas import (
    CertificateHolderInput,
    COIFormInput,
    COIProducerInput,
    COIInsurerInput,
    COIInsuredInput,
    COIGeneralLiabilityInput,
    COIAutoLiabilityInput,
    COIAdditionalCoverageInput,
)
from organizations.service import OrganizationService
from pdf.service import PDFService
from policies.models import Policy
from s3.service import S3Service
from s3.schemas import UploadFileInput
from users.models import UserDocument

logger = logging.getLogger(__name__)


class CertificateService:
    """Service for consolidated COI operations across all policies."""

    @staticmethod
    def generate_consolidated_coi(user, organization_id: int | None = None) -> dict:
        """
        Build a consolidated Certificate of Insurance data structure for all
        active policies in the user's organization.

        Groups policies by COI number (policies purchased together share a COI),
        and for each group returns coverage details with brokered/non-brokered
        carrier distinction.

        Returns:
            {
                "organization_id": int,
                "coi_groups": [
                    {
                        "coi_number": str,
                        "effective_date": str,
                        "expiration_date": str,
                        "policies": [
                            {
                                "policy_number": str,
                                "coverage_type": str,
                                "carrier": str | {"insurer_a": str, "insurer_b": str},
                                "is_brokered": bool,
                                "limits": dict,
                                "premium": str,
                                "effective_date": str,
                                "expiration_date": str,
                            }
                        ]
                    }
                ],
                "total_policies": int,
                "total_coi_groups": int,
            }
        """
        org_id = organization_id or OrganizationService.get_active_org_id(user)

        active_policies = (
            Policy.objects.filter(
                quote__organization_id=org_id,
                status="active",
                coi_number__isnull=False,
            )
            .exclude(coi_number="")
            .select_related("quote__company")
            .order_by("coi_number", "coverage_type")
        )

        # Group policies by COI number
        groups: dict[str, list[Policy]] = {}
        for policy in active_policies:
            groups.setdefault(policy.coi_number, []).append(policy)

        coi_groups = []
        for coi_number, policies in groups.items():
            policy_data = []
            for p in policies:
                # Brokered policies: carrier listed as "Insurer A", Corgi as "Insurer B"
                if p.is_brokered:
                    carrier_info = {
                        "insurer_a": p.carrier,
                        "insurer_b": "Corgi Insurance Services, Inc.",
                    }
                else:
                    carrier_info = p.carrier

                limits = p.limits_retentions or {}

                policy_data.append(
                    {
                        "policy_number": p.policy_number,
                        "coverage_type": p.coverage_type,
                        "coverage_display": COVERAGE_DISPLAY_NAMES.get(
                            p.coverage_type, p.coverage_type
                        ),
                        "carrier": carrier_info,
                        "is_brokered": p.is_brokered,
                        "limits": limits,
                        "premium": str(p.premium) if p.premium else "0.00",
                        "effective_date": p.effective_date.isoformat(),
                        "expiration_date": p.expiration_date.isoformat(),
                    }
                )

            # Use earliest effective / latest expiration across group
            eff_dates = [p.effective_date for p in policies]
            exp_dates = [p.expiration_date for p in policies]

            coi_groups.append(
                {
                    "coi_number": coi_number,
                    "effective_date": min(eff_dates).isoformat(),
                    "expiration_date": max(exp_dates).isoformat(),
                    "policies": policy_data,
                }
            )

        total_policies = sum(len(g["policies"]) for g in coi_groups)

        return {
            "organization_id": org_id,
            "coi_groups": coi_groups,
            "total_policies": total_policies,
            "total_coi_groups": len(coi_groups),
        }


class CustomCertificateService:
    @staticmethod
    def get_available_cois(user) -> list[dict]:
        org_id = OrganizationService.get_active_org_id(user)
        policies = (
            Policy.objects.filter(
                quote__organization_id=org_id, coi_number__isnull=False
            )
            .exclude(coi_number="")
            .values("coi_number", "effective_date", "expiration_date")
            .distinct()
        )

        cois = []
        seen_cois = set()

        for policy in policies:
            coi_number = policy["coi_number"]
            if coi_number not in seen_cois:
                seen_cois.add(coi_number)
                custom_count = CustomCertificate.objects.filter(
                    coi_number=coi_number
                ).count()
                cois.append(
                    {
                        "coi_number": coi_number,
                        "effective_date": policy["effective_date"].isoformat(),
                        "expiration_date": policy["expiration_date"].isoformat(),
                        "custom_certificates_count": custom_count,
                    }
                )

        return cois

    @staticmethod
    def get_certificates_for_user(user) -> list[CustomCertificate]:
        org_id = OrganizationService.get_active_org_id(user)
        return list(
            CustomCertificate.objects.filter(organization_id=org_id).select_related(
                "document"
            )
        )

    @staticmethod
    def list_certificates(
        user, search: str = None, page: int = 1, page_size: int = 20
    ) -> dict:
        """List certificates with pagination and search."""
        org_id = OrganizationService.get_active_org_id(user)
        qs = CustomCertificate.objects.filter(organization_id=org_id).select_related(
            "document"
        )

        if search:
            qs = qs.filter(
                Q(holder_name__icontains=search)
                | Q(custom_coi_number__icontains=search)
                | Q(coi_number__icontains=search)
                | Q(holder_city__icontains=search)
            )

        total = qs.count()
        total_pages = max(1, math.ceil(total / page_size))
        page = max(1, min(page, total_pages))
        offset = (page - 1) * page_size
        certificates = list(qs[offset : offset + page_size])

        return {
            "certificates": certificates,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @staticmethod
    def revoke_certificate(user, certificate_id: int) -> CustomCertificate:
        """Revoke a certificate (soft-revoke)."""
        org_id = OrganizationService.get_active_org_id(user)
        certificate = CustomCertificate.objects.get(
            id=certificate_id, organization_id=org_id
        )
        if certificate.status == "revoked":
            raise ValueError("Certificate is already revoked")
        certificate.status = "revoked"
        certificate.revoked_at = timezone.now()
        certificate.revoked_by = user
        certificate.save(update_fields=["status", "revoked_at", "revoked_by"])
        return certificate

    @staticmethod
    def get_certificate(user, certificate_id: int) -> CustomCertificate:
        org_id = OrganizationService.get_active_org_id(user)
        return CustomCertificate.objects.select_related("document").get(
            id=certificate_id, organization_id=org_id
        )

    @staticmethod
    def get_download_info(user, certificate_id: int) -> dict:
        org_id = OrganizationService.get_active_org_id(user)
        certificate = CustomCertificate.objects.select_related("document").get(
            id=certificate_id, organization_id=org_id
        )
        if not certificate.document:
            raise ValueError("Document not available for this certificate")
        presigned_url = S3Service.generate_presigned_url(certificate.document.s3_key)
        return {
            "url": presigned_url,
            "filename": certificate.document.original_filename,
        }

    @staticmethod
    def user_has_coi_access(user, coi_number: str) -> bool:
        org_id = OrganizationService.get_active_org_id(user)
        return Policy.objects.filter(
            coi_number=coi_number, quote__organization_id=org_id
        ).exists()

    @staticmethod
    def build_certificate_description(custom_cert: CustomCertificate) -> str:
        lines = []

        if custom_cert.is_additional_insured:
            lines.append(ADDITIONAL_INSURED_TEXT)

        for endorsement in custom_cert.endorsements:
            text = ENDORSEMENT_TEXT.get(endorsement, "")

            if endorsement == "job_service_location" and text:
                location = (
                    custom_cert.service_location_address or "the specified location"
                )
                text = text.format(location=location)
            elif endorsement == "job_service_you_provide" and text:
                service = (
                    custom_cert.service_you_provide_service or "the specified service"
                )
                text = text.format(service=service)

            if text:
                lines.append(text)

        return " ".join(lines)

    @staticmethod
    def get_policies_for_coi(coi_number: str) -> list[Policy]:
        return list(
            Policy.objects.filter(coi_number=coi_number).select_related(
                "quote__company__business_address"
            )
        )

    @staticmethod
    def generate_custom_certificate(custom_cert: CustomCertificate) -> Optional[bytes]:
        policies = CustomCertificateService.get_policies_for_coi(custom_cert.coi_number)

        if not policies:
            logger.error(f"No policies found for COI number: {custom_cert.coi_number}")
            return None

        holder_name = custom_cert.holder_name
        if custom_cert.holder_second_line:
            holder_name = f"{holder_name}, {custom_cert.holder_second_line}"

        holder_address = custom_cert.holder_street_address
        if custom_cert.holder_suite:
            holder_address = f"{holder_address}, {custom_cert.holder_suite}"

        holder_info = CertificateHolderInput(
            name=holder_name,
            address_line1=holder_address,
            city_state_zip=f"{custom_cert.holder_city}, {custom_cert.holder_state} {custom_cert.holder_zip}",
        )

        description = CustomCertificateService.build_certificate_description(
            custom_cert
        )

        pdf_bytes = CustomCertificateService._generate_coi_with_custom_data(
            policies=policies,
            coi_number=custom_cert.custom_coi_number,
            holder_info=holder_info,
            description=description,
        )

        return pdf_bytes

    @staticmethod
    def generate_preview(
        coi_number: str,
        holder_name: str,
        holder_street_address: str,
        holder_city: str,
        holder_state: str,
        holder_zip: str,
        holder_second_line: str = "",
        holder_suite: str = "",
        is_additional_insured: bool = False,
        endorsements: list[str] = None,
        service_location_job: str = "",
        service_location_address: str = "",
        service_you_provide_job: str = "",
        service_you_provide_service: str = "",
    ) -> Optional[bytes]:
        endorsements = endorsements or []
        policies = CustomCertificateService.get_policies_for_coi(coi_number)

        if not policies:
            logger.error(f"No policies found for COI number: {coi_number}")
            return None

        full_holder_name = holder_name
        if holder_second_line:
            full_holder_name = f"{holder_name}, {holder_second_line}"

        full_holder_address = holder_street_address
        if holder_suite:
            full_holder_address = f"{holder_street_address}, {holder_suite}"

        holder_info = CertificateHolderInput(
            name=full_holder_name,
            address_line1=full_holder_address,
            city_state_zip=f"{holder_city}, {holder_state} {holder_zip}",
        )

        description = CustomCertificateService._build_description_from_params(
            is_additional_insured=is_additional_insured,
            endorsements=endorsements,
            service_location_address=service_location_address,
            service_you_provide_service=service_you_provide_service,
        )

        preview_coi_number = f"{coi_number}-PREVIEW"

        return CustomCertificateService._generate_coi_with_custom_data(
            policies=policies,
            coi_number=preview_coi_number,
            holder_info=holder_info,
            description=description,
        )

    @staticmethod
    def _build_description_from_params(
        is_additional_insured: bool,
        endorsements: list[str],
        service_location_address: str = "",
        service_you_provide_service: str = "",
    ) -> str:
        lines = []

        if is_additional_insured:
            lines.append(ADDITIONAL_INSURED_TEXT)

        for endorsement in endorsements:
            text = ENDORSEMENT_TEXT.get(endorsement, "")

            if endorsement == "job_service_location" and text:
                location = service_location_address or "the specified location"
                text = text.format(location=location)
            elif endorsement == "job_service_you_provide" and text:
                service = service_you_provide_service or "the specified service"
                text = text.format(service=service)

            if text:
                lines.append(text)

        return " ".join(lines)

    @staticmethod
    def _generate_coi_with_custom_data(
        policies: list[Policy],
        coi_number: str,
        holder_info: Optional[CertificateHolderInput] = None,
        description: str = "",
    ) -> Optional[bytes]:
        if not policies:
            return None

        first_policy = policies[0]
        quote = first_policy.quote
        company = quote.company
        address = company.business_address if company else None
        fmt = format_currency

        eff_date = first_policy.effective_date.strftime("%m/%d/%Y")
        exp_date = first_policy.expiration_date.strftime("%m/%d/%Y")

        non_brokered = [p for p in policies if not p.is_brokered]
        if non_brokered:
            any_ntic = any(p.carrier == NTIC_CARRIER for p in non_brokered)
            carrier_name = NTIC_CARRIER if any_ntic else non_brokered[0].carrier
        else:
            carrier_name = TECHRRG_CARRIER

        naic_code = (
            NTIC_NAIC_CODE if carrier_name == NTIC_CARRIER else TECHRRG_NAIC_CODE
        )

        coi_data = COIFormInput(
            certificate_date=eff_date,
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
                effective_date=eff_date,
                expiration_date=exp_date,
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
                effective_date=eff_date,
                expiration_date=exp_date,
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
                        effective_date=eff_date,
                        expiration_date=exp_date,
                        per_claim_limit=f"Per Claim: ${fmt(per_claim)}",
                        aggregate_limit=f"Aggregate: ${fmt(aggregate)}",
                    )
                )

        pdf_bytes = PDFService.fill_pdf_form(COIPaths.COI, coi_data.to_form_fields())
        return PDFService.flatten_pdf(pdf_bytes)

    @staticmethod
    def create_and_generate_certificate(
        user,
        coi_number: str,
        holder_name: str,
        holder_street_address: str,
        holder_city: str,
        holder_state: str,
        holder_zip: str,
        holder_second_line: str = "",
        holder_suite: str = "",
        is_additional_insured: bool = False,
        endorsements: list[str] = None,
        service_location_job: str = "",
        service_location_address: str = "",
        service_you_provide_job: str = "",
        service_you_provide_service: str = "",
    ) -> CustomCertificate:
        if not OrganizationService.can_edit(user):
            raise AccessDeniedError("You do not have permission to create certificates")

        endorsements = endorsements or []
        org_id = OrganizationService.get_active_org_id(user)

        custom_coi_number = CustomCertificate.generate_custom_coi_number(coi_number)

        custom_cert = CustomCertificate.objects.create(
            user=user,
            organization_id=org_id,
            coi_number=coi_number,
            custom_coi_number=custom_coi_number,
            holder_name=holder_name,
            holder_second_line=holder_second_line,
            holder_street_address=holder_street_address,
            holder_suite=holder_suite,
            holder_city=holder_city,
            holder_state=holder_state,
            holder_zip=holder_zip,
            is_additional_insured=is_additional_insured,
            endorsements=endorsements,
            service_location_job=service_location_job,
            service_location_address=service_location_address,
            service_you_provide_job=service_you_provide_job,
            service_you_provide_service=service_you_provide_service,
        )

        pdf_bytes = CustomCertificateService.generate_custom_certificate(custom_cert)

        if pdf_bytes:
            document = CustomCertificateService._upload_and_create_document(
                user=user,
                custom_cert=custom_cert,
                pdf_bytes=pdf_bytes,
                org_id=org_id,
            )
            custom_cert.document = document
            custom_cert.save()

        return custom_cert

    @staticmethod
    def _upload_and_create_document(
        user,
        custom_cert: CustomCertificate,
        pdf_bytes: bytes,
        org_id: int = None,
    ) -> UserDocument:
        filename = (
            f"Custom Certificate of Insurance - {custom_cert.custom_coi_number}.pdf"
        )

        policies = CustomCertificateService.get_policies_for_coi(custom_cert.coi_number)
        policy_id = policies[0].id if policies else "unknown"

        result = S3Service.upload_file(
            UploadFileInput(
                file=BytesIO(pdf_bytes),
                path_prefix=f"policies/{policy_id}/documents",
                original_filename=filename,
                content_type="application/pdf",
            )
        )

        doc_kwargs = dict(
            user=user,
            category="certificate",
            title=f"Custom Certificate - {custom_cert.holder_name}",
            file_type="custom-certificate-of-insurance",
            original_filename=filename,
            file_size=len(pdf_bytes),
            mime_type="application/pdf",
            s3_key=result["s3_key"],
            s3_url=result["s3_url"],
            policy_numbers=[custom_cert.custom_coi_number],
        )
        if org_id:
            doc_kwargs["organization_id"] = org_id
        document = UserDocument.objects.create(**doc_kwargs)

        return document
