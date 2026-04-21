from typing import Optional
from ninja import Schema


class CreateCustomCertificateInput(Schema):
    coi_number: str
    holder_name: str
    holder_second_line: Optional[str] = ""
    holder_street_address: str
    holder_suite: Optional[str] = ""
    holder_city: str
    holder_state: str
    holder_zip: str
    is_additional_insured: bool = False
    endorsements: list[str] = []
    service_location_job: Optional[str] = ""
    service_location_address: Optional[str] = ""
    service_you_provide_job: Optional[str] = ""
    service_you_provide_service: Optional[str] = ""


class CustomCertificateOutput(Schema):
    id: int
    coi_number: str
    custom_coi_number: str
    holder_name: str
    holder_second_line: str
    holder_street_address: str
    holder_suite: str
    holder_city: str
    holder_state: str
    holder_zip: str
    holder_full_address: str
    is_additional_insured: bool
    endorsements: list[str]
    service_location_job: str
    service_location_address: str
    service_you_provide_job: str
    service_you_provide_service: str
    status: str
    document_url: Optional[str] = None
    created_at: str
    revoked_at: Optional[str] = None

    @staticmethod
    def from_model(cert) -> "CustomCertificateOutput":
        return CustomCertificateOutput(
            id=cert.id,
            coi_number=cert.coi_number,
            custom_coi_number=cert.custom_coi_number,
            holder_name=cert.holder_name,
            holder_second_line=cert.holder_second_line,
            holder_street_address=cert.holder_street_address,
            holder_suite=cert.holder_suite,
            holder_city=cert.holder_city,
            holder_state=cert.holder_state,
            holder_zip=cert.holder_zip,
            holder_full_address=cert.holder_full_address,
            is_additional_insured=cert.is_additional_insured,
            endorsements=cert.endorsements,
            service_location_job=cert.service_location_job,
            service_location_address=cert.service_location_address,
            service_you_provide_job=cert.service_you_provide_job,
            service_you_provide_service=cert.service_you_provide_service,
            status=cert.status,
            document_url=cert.document.s3_url if cert.document else None,
            created_at=cert.created_at.isoformat()
            if hasattr(cert.created_at, "isoformat")
            else str(cert.created_at),
            revoked_at=(
                cert.revoked_at.isoformat()
                if cert.revoked_at and hasattr(cert.revoked_at, "isoformat")
                else str(cert.revoked_at)
                if cert.revoked_at
                else None
            ),
        )


class CertificateListResponse(Schema):
    certificates: list[CustomCertificateOutput]
    total: int
    page: int
    page_size: int
    total_pages: int
