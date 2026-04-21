"""
Certificate of Insurance API endpoints for the Corgi Insurance portal.

Provides CRUD operations for custom certificates, PDF preview generation,
downloads, and listing available COI numbers for certificate generation.
All endpoints require JWT authentication and are org-scoped.

Additional Insured coverage support (Trello 4.9):
    The Additional Insured flow (see ``certificates/additional_insured_service.py``)
    is coverage-agnostic. It operates on COI numbers and policies without
    gating on ``coverage_type``, so it natively supports:
        - Commercial General Liability (CGL)
        - Cyber Liability (``cyber-liability``)
        - Technology Errors & Omissions (``technology-errors-and-omissions``)
    No whitelist or conditional branch needs to be extended for these coverage
    types — the ``/additional-insureds`` endpoints accept any active COI
    regardless of the underlying coverage.
"""

from typing import Any, Optional

from django.http import HttpRequest, HttpResponse
from ninja import Router

from certificates.models import CustomCertificate
from certificates.schemas import (
    CreateCustomCertificateInput,
    CustomCertificateOutput,
)
from certificates.service import CertificateService, CustomCertificateService
from common.schemas import ApiResponseSchema
from users.auth import JWTAuth

router = Router(tags=["Certificates"])


@router.get("/consolidated", auth=JWTAuth())
def get_consolidated_coi(
    request: HttpRequest, format: Optional[str] = None, group: Optional[str] = None
) -> HttpResponse | tuple[int, dict[str, Any]]:
    """
    Return consolidated COI data for all active policies in the user's organization.
    Groups policies by COI number with brokered/non-brokered carrier distinction.

    Query params:
        format: Set to "pdf" to download a COI PDF instead of JSON.
        group:  COI number of a specific group (used with format=pdf for
                multi-group orgs). Defaults to the first group.
    """
    user = request.auth
    data = CertificateService.generate_consolidated_coi(user)

    if format == "pdf":
        from certificates.pdf import generate_coi_pdf, generate_coi_pdf_for_group

        if group:
            # Find the requested COI group
            target = next(
                (g for g in data.get("coi_groups", []) if g["coi_number"] == group),
                None,
            )
            if not target:
                return HttpResponse(
                    '{"success":false,"message":"COI group not found"}',
                    content_type="application/json",
                    status=404,
                )
            pdf_bytes = generate_coi_pdf_for_group(target, data["organization_id"])
            filename = f"COI-{group}.pdf"
        else:
            pdf_bytes = generate_coi_pdf(data)
            coi_groups = data.get("coi_groups", [])
            coi_num = coi_groups[0]["coi_number"] if coi_groups else "consolidated"
            filename = f"COI-{coi_num}.pdf"

        if not pdf_bytes:
            return HttpResponse(
                '{"success":false,"message":"Failed to generate COI PDF"}',
                content_type="application/json",
                status=500,
            )

        return HttpResponse(
            pdf_bytes,
            content_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    return 200, {
        "success": True,
        "message": "Consolidated COI data retrieved successfully",
        "data": data,
    }


@router.post(
    "/custom", auth=JWTAuth(), response={200: ApiResponseSchema, 400: ApiResponseSchema}
)
def create_custom_certificate(
    request: HttpRequest, payload: CreateCustomCertificateInput
) -> tuple[int, dict[str, Any]]:
    """Create a custom certificate with holder information and endorsements."""
    user = request.auth

    if not CustomCertificateService.user_has_coi_access(user, payload.coi_number):
        return 400, {
            "success": False,
            "message": "No policies found for this COI number or you don't have access",
            "data": None,
        }

    custom_cert = CustomCertificateService.create_and_generate_certificate(
        user=user,
        coi_number=payload.coi_number,
        holder_name=payload.holder_name,
        holder_second_line=payload.holder_second_line or "",
        holder_street_address=payload.holder_street_address,
        holder_suite=payload.holder_suite or "",
        holder_city=payload.holder_city,
        holder_state=payload.holder_state,
        holder_zip=payload.holder_zip,
        is_additional_insured=payload.is_additional_insured,
        endorsements=payload.endorsements,
        service_location_job=payload.service_location_job or "",
        service_location_address=payload.service_location_address or "",
        service_you_provide_job=payload.service_you_provide_job or "",
        service_you_provide_service=payload.service_you_provide_service or "",
    )

    return 200, {
        "success": True,
        "message": "Custom certificate created successfully",
        "data": CustomCertificateOutput.from_model(custom_cert).dict(),
    }


@router.post("/custom/preview", auth=JWTAuth())
def preview_custom_certificate(
    request: HttpRequest, payload: CreateCustomCertificateInput
) -> HttpResponse:
    """Generate a PDF preview of a custom certificate without saving."""
    user = request.auth

    if not CustomCertificateService.user_has_coi_access(user, payload.coi_number):
        return HttpResponse(status=400, content="No policies found for this COI number")

    pdf_bytes: bytes | None = CustomCertificateService.generate_preview(
        coi_number=payload.coi_number,
        holder_name=payload.holder_name,
        holder_second_line=payload.holder_second_line or "",
        holder_street_address=payload.holder_street_address,
        holder_suite=payload.holder_suite or "",
        holder_city=payload.holder_city,
        holder_state=payload.holder_state,
        holder_zip=payload.holder_zip,
        is_additional_insured=payload.is_additional_insured,
        endorsements=payload.endorsements,
        service_location_job=payload.service_location_job or "",
        service_location_address=payload.service_location_address or "",
        service_you_provide_job=payload.service_you_provide_job or "",
        service_you_provide_service=payload.service_you_provide_service or "",
    )

    if not pdf_bytes:
        return HttpResponse(
            status=400, content="Failed to generate certificate preview"
        )

    return HttpResponse(
        pdf_bytes,
        content_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=certificate-preview.pdf"},
    )


@router.get("/custom", auth=JWTAuth(), response={200: ApiResponseSchema})
def list_custom_certificates(
    request: HttpRequest,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[int, dict[str, Any]]:
    """List all custom certificates for the current organization with pagination and search."""
    result = CustomCertificateService.list_certificates(
        user=request.auth,
        search=search,
        page=page,
        page_size=min(page_size, 100),
    )
    return 200, {
        "success": True,
        "message": "Custom certificates retrieved successfully",
        "data": {
            "certificates": [
                CustomCertificateOutput.from_model(cert).dict()
                for cert in result["certificates"]
            ],
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "total_pages": result["total_pages"],
        },
    }


@router.get(
    "/custom/{certificate_id}",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema},
)
def get_custom_certificate(
    request: HttpRequest, certificate_id: int
) -> tuple[int, dict[str, Any]]:
    """Retrieve a single custom certificate by ID."""
    try:
        certificate = CustomCertificateService.get_certificate(
            request.auth, certificate_id
        )
        return 200, {
            "success": True,
            "message": "Custom certificate retrieved successfully",
            "data": CustomCertificateOutput.from_model(certificate).dict(),
        }
    except CustomCertificate.DoesNotExist:
        return 404, {
            "success": False,
            "message": "Custom certificate not found",
            "data": None,
        }


@router.delete(
    "/custom/{certificate_id}",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema, 400: ApiResponseSchema},
)
def revoke_custom_certificate(
    request: HttpRequest, certificate_id: int
) -> tuple[int, dict[str, Any]]:
    """Revoke a custom certificate (soft-delete, marks as revoked)."""
    try:
        certificate = CustomCertificateService.revoke_certificate(
            request.auth, certificate_id
        )
        return 200, {
            "success": True,
            "message": "Certificate revoked successfully",
            "data": CustomCertificateOutput.from_model(certificate).dict(),
        }
    except CustomCertificate.DoesNotExist:
        return 404, {
            "success": False,
            "message": "Custom certificate not found",
            "data": None,
        }
    except ValueError as e:
        return 400, {
            "success": False,
            "message": str(e),
            "data": None,
        }


@router.get(
    "/custom/{certificate_id}/download",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema},
)
def download_custom_certificate(
    request: HttpRequest, certificate_id: int
) -> tuple[int, dict[str, Any]]:
    """Get a presigned S3 download URL for a custom certificate PDF."""
    try:
        data = CustomCertificateService.get_download_info(request.auth, certificate_id)
        return 200, {
            "success": True,
            "message": "Download URL retrieved successfully",
            "data": data,
        }
    except CustomCertificate.DoesNotExist:
        return 404, {
            "success": False,
            "message": "Custom certificate not found",
            "data": None,
        }
    except ValueError as e:
        return 404, {
            "success": False,
            "message": str(e),
            "data": None,
        }


@router.get("/available-cois", auth=JWTAuth(), response={200: ApiResponseSchema})
def get_available_cois(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """List COI numbers available for custom certificate generation."""
    cois = CustomCertificateService.get_available_cois(request.auth)
    return 200, {
        "success": True,
        "message": "Available COIs retrieved successfully",
        "data": cois,
    }


# ── Additional Insured Endpoints ──────────────────────────────────────────────

from pydantic import BaseModel as PydanticBaseModel  # noqa: E402


class AddAdditionalInsuredInput(PydanticBaseModel):
    coi_number: str
    name: str
    address: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""


@router.get(
    "/additional-insureds",
    auth=JWTAuth(),
    response={200: ApiResponseSchema},
)
def list_additional_insureds(
    request: HttpRequest,
    coi_number: Optional[str] = None,
) -> tuple[int, dict[str, Any]]:
    """List all active additional insureds for the current organization.

    Query params:
        coi_number: Optional filter by COI number.

    Returns:
        200 with list of additional insured records.
    """
    from certificates.additional_insured_service import AdditionalInsuredService

    records = AdditionalInsuredService.list_additional_insureds(
        user=request.auth,
        coi_number=coi_number,
    )
    return 200, {
        "success": True,
        "message": "Additional insureds retrieved successfully",
        "data": records,
    }


@router.post(
    "/additional-insureds",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 400: ApiResponseSchema},
)
def add_additional_insured(
    request: HttpRequest,
    payload: AddAdditionalInsuredInput,
) -> tuple[int, dict[str, Any]]:
    """Add an additional insured to a policy's COI.

    Creates an AdditionalInsured record, auto-generates a custom COI
    certificate, and emails a copy to the additional insured's email
    address if provided.

    Args:
        payload.coi_number: The COI to add the additional insured to.
        payload.name: Full legal name of the additional insured.
        payload.address: Mailing address.
        payload.email: Email to receive COI copy.
        payload.phone: Contact phone.
    """
    from certificates.additional_insured_service import AdditionalInsuredService

    if not CustomCertificateService.user_has_coi_access(
        request.auth, payload.coi_number
    ):
        return 400, {
            "success": False,
            "message": "No policies found for this COI number or you don't have access",
            "data": None,
        }

    try:
        record = AdditionalInsuredService.add_additional_insured(
            user=request.auth,
            coi_number=payload.coi_number,
            name=payload.name,
            address=payload.address or "",
            email=payload.email or "",
            phone=payload.phone or "",
        )
        return 200, {
            "success": True,
            "message": "Additional insured added successfully",
            "data": record,
        }
    except ValueError as e:
        return 400, {
            "success": False,
            "message": str(e),
            "data": None,
        }


@router.delete(
    "/additional-insureds/{additional_insured_id}",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema, 400: ApiResponseSchema},
)
def remove_additional_insured(
    request: HttpRequest,
    additional_insured_id: int,
) -> tuple[int, dict[str, Any]]:
    """Remove an additional insured from a policy's COI.

    Marks the AdditionalInsured record as removed and revokes
    the associated custom certificate.
    """
    from certificates.additional_insured_service import AdditionalInsuredService
    from certificates.models import AdditionalInsured

    try:
        record = AdditionalInsuredService.remove_additional_insured(
            user=request.auth,
            additional_insured_id=additional_insured_id,
        )
        return 200, {
            "success": True,
            "message": "Additional insured removed successfully",
            "data": record,
        }
    except AdditionalInsured.DoesNotExist:
        return 404, {
            "success": False,
            "message": "Additional insured not found",
            "data": None,
        }
    except ValueError as e:
        return 400, {
            "success": False,
            "message": str(e),
            "data": None,
        }
