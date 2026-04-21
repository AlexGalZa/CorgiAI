"""
Claims API endpoints for the Corgi Insurance portal.

Provides claim filing (with file attachments), listing, and detail
retrieval. All endpoints require JWT authentication and are org-scoped.
"""

from typing import Any, List

from django.http import HttpRequest
from ninja import Router, UploadedFile, File, Form

from claims.schemas import ClaimCreateSchema, ClaimResponseSchema
from claims.service import ClaimService
from common.api_utils import parse_form_data_json
from common.schemas import ApiResponseSchema
from users.auth import JWTAuth

router = Router(tags=["Claims"])


@router.post(
    "/",
    auth=JWTAuth(),
    response={
        201: ApiResponseSchema,
        400: ApiResponseSchema,
        404: ApiResponseSchema,
        500: ApiResponseSchema,
    },
)
def submit_claim(
    request: HttpRequest,
    data: str = Form(...),
    attachments: List[UploadedFile] = File(None),
) -> tuple[int, dict[str, Any]]:
    """File a new insurance claim with optional document attachments.

    Accepts multipart form data with a JSON ``data`` field containing
    claim details (policy_number, contact info, description) and
    optional file attachments uploaded to S3.

    Args:
        request: HTTP request with JWT-authenticated user.
        data: JSON string conforming to ``ClaimCreateSchema``.
        attachments: Optional file uploads for supporting documents.

    Returns:
        201 with claim details, or 404 if the referenced policy is not found.
    """
    validated_data = parse_form_data_json(data, ClaimCreateSchema)
    user = request.auth

    try:
        claim = ClaimService.submit_claim(
            data=validated_data, files=attachments, user=user
        )
    except Exception as e:
        if "Policy matching query does not exist" in str(e):
            return 404, {
                "success": False,
                "message": "Policy not found or access denied",
                "data": None,
            }
        raise

    return 201, {
        "success": True,
        "message": "Claim submitted successfully",
        "data": ClaimResponseSchema.from_claim(claim).dict(),
    }


@router.get("/me", auth=JWTAuth(), response={200: ApiResponseSchema})
def get_user_claims(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """List all claims for the current organization.

    Returns claim summaries including claim number, policy number,
    status, description, and creation date.

    Returns:
        200 with a list of claim summary dicts.
    """
    claims = ClaimService.get_user_claims(request.auth)
    return 200, {
        "success": True,
        "message": "Claims retrieved successfully",
        "data": [claim.dict() for claim in claims],
    }


@router.get(
    "/{claim_number}",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema},
)
def get_claim(request: HttpRequest, claim_number: str) -> tuple[int, dict[str, Any]]:
    """Retrieve detailed information about a specific claim.

    Args:
        request: HTTP request with JWT-authenticated user.
        claim_number: Unique claim identifier.

    Returns:
        200 with full claim details, or 404 if not found.
    """
    claim = ClaimService.get_claim_by_number(claim_number, request.auth)

    if not claim:
        return 404, {"success": False, "message": "Claim not found", "data": None}

    return 200, {
        "success": True,
        "message": "Claim retrieved successfully",
        "data": ClaimResponseSchema.from_claim(claim).dict(),
    }
