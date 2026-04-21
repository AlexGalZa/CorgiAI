"""
Document signing API endpoints for the Corgi Insurance platform.

Provides a generic "type-to-sign" endpoint that creates TypeToSignRecord
instances linked to any signable model.

Endpoints:
    POST /api/v1/signing/sign  — Create a signature record
    GET  /api/v1/signing/{id}  — Retrieve a signature record
"""

from typing import Any, Optional

from django.http import HttpRequest
from ninja import Router
from pydantic import BaseModel as PydanticBaseModel

from common.schemas import ApiResponseSchema
from users.auth import JWTAuth

router = Router(tags=["Signing"])


class SignDocumentInput(PydanticBaseModel):
    """Input for type-to-sign flow."""

    signed_name: str
    """The full name typed by the signer."""

    document_type: str
    """Model name being signed, e.g. 'policy', 'endorsement', 'quote'."""

    document_id: int
    """Primary key of the document being signed."""

    agreement_text: Optional[str] = ""
    """The agreement text the user is signing off on (snapshot for audit trail)."""


@router.post(
    "/sign",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 400: ApiResponseSchema},
)
def sign_document(
    request: HttpRequest,
    payload: SignDocumentInput,
) -> tuple[int, dict[str, Any]]:
    """
    Create a type-to-sign electronic signature record.

    Stores:
    - The signer's typed full name
    - Timestamp (auto)
    - IP address extracted from the request
    - Authenticated user FK
    - Content type + object ID of the signed document

    Args:
        payload.signed_name: Full name typed by signer (required)
        payload.document_type: Model name to sign ('policy', 'quote', 'endorsement')
        payload.document_id: PK of the document
        payload.agreement_text: Optional snapshot of agreement text

    Returns:
        200 with signature record data, 400 if validation fails.
    """
    if not payload.signed_name.strip():
        return 400, {
            "success": False,
            "message": "signed_name is required.",
            "data": None,
        }

    # Resolve content type
    from django.contrib.contenttypes.models import ContentType

    MODEL_MAP = {
        "policy": "policies.policy",
        "quote": "quotes.quote",
        "endorsement": "policies.policyendorsement",
        "claim": "claims.claim",
    }

    ct_label = MODEL_MAP.get(payload.document_type.lower())
    if not ct_label:
        return 400, {
            "success": False,
            "message": (
                f"Unknown document_type '{payload.document_type}'. Valid types: {', '.join(MODEL_MAP.keys())}"
            ),
            "data": None,
        }

    try:
        app_label, model_name = ct_label.split(".")
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
    except ContentType.DoesNotExist:
        return 400, {
            "success": False,
            "message": f"Content type '{ct_label}' not found.",
            "data": None,
        }

    # Verify the document exists and the user has access to it
    model_class = content_type.model_class()
    try:
        model_class.objects.get(pk=payload.document_id)
    except model_class.DoesNotExist:
        return 400, {
            "success": False,
            "message": f"Document {payload.document_type} #{payload.document_id} not found.",
            "data": None,
        }

    # Extract IP address
    ip_address = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[
        0
    ].strip() or request.META.get("REMOTE_ADDR")
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    from common.models import TypeToSignRecord

    signature = TypeToSignRecord.objects.create(
        signed_name=payload.signed_name.strip(),
        ip_address=ip_address,
        user_agent=user_agent,
        signer=request.auth,
        signed_content_type=content_type,
        signed_object_id=payload.document_id,
        agreement_text=payload.agreement_text or "",
    )

    return 200, {
        "success": True,
        "message": "Document signed successfully.",
        "data": {
            "signature_id": signature.pk,
            "signed_name": signature.signed_name,
            "signed_at": signature.created_at.isoformat(),
            "document_type": payload.document_type,
            "document_id": payload.document_id,
            "ip_address": signature.ip_address,
        },
    }


@router.get(
    "/{signature_id}",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema},
)
def get_signature(
    request: HttpRequest,
    signature_id: int,
) -> tuple[int, dict[str, Any]]:
    """
    Retrieve a signature record by ID.

    Returns the signature metadata including signer name, timestamp,
    IP address, and linked document information.
    """
    from common.models import TypeToSignRecord

    try:
        sig = TypeToSignRecord.objects.select_related(
            "signer", "signed_content_type"
        ).get(pk=signature_id, signer=request.auth)
    except TypeToSignRecord.DoesNotExist:
        return 404, {
            "success": False,
            "message": "Signature record not found.",
            "data": None,
        }

    return 200, {
        "success": True,
        "message": "Signature record retrieved.",
        "data": {
            "signature_id": sig.pk,
            "signed_name": sig.signed_name,
            "signed_at": sig.created_at.isoformat(),
            "ip_address": sig.ip_address,
            "document_type": sig.signed_content_type.model
            if sig.signed_content_type
            else None,
            "document_id": sig.signed_object_id,
            "agreement_text": sig.agreement_text,
        },
    }
