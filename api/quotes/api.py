"""
Quote API endpoints for the Corgi Insurance portal.

Handles the full quote lifecycle: draft creation, step-by-step form saving,
final submission with file uploads, rating, retrieval, checkout URL generation,
and moving quotes between organizations.

All endpoints require JWT authentication via ``JWTAuth``.
"""

import os
from typing import Any, List

from django.http import HttpRequest
from ninja import Router, Schema, UploadedFile, File, Form

from quotes.service import QuoteService
from quotes.models import Quote
from quotes.schemas import (
    QuoteCreateSchema,
    QuoteResponseSchema,
    DraftQuoteCreateSchema,
    DraftQuoteResponseSchema,
    StepSaveSchema,
    CheckoutRequestSchema,
    MoveQuoteSchema,
)
from common.schemas import ApiResponseSchema
from common.api_utils import parse_form_data_json
from users.auth import JWTAuth
from forms.validators import (
    build_validation_error_response,
    extract_coverage_payloads_from_form_data,
    validate_coverage_payloads,
)

router = Router(tags=["Quotes"])


@router.post(
    "/draft",
    auth=JWTAuth(),
    response={201: ApiResponseSchema, 400: ApiResponseSchema, 500: ApiResponseSchema},
)
def create_draft_quote(
    request: HttpRequest, data: DraftQuoteCreateSchema
) -> tuple[int, dict[str, Any]]:
    """Create a new draft quote with selected coverages.

    Initialises a blank company, address, and quote record in ``draft`` status.
    The user can then save individual form steps via ``PATCH /{quote_number}/step``.

    Args:
        request: HTTP request with JWT-authenticated user.
        data: Coverage selections and optional package choice.

    Returns:
        201 response with the new quote number and step tracking info.
    """
    user = request.auth

    quote = QuoteService.create_draft_quote(
        coverages=data.coverages, selected_package=data.selected_package, user=user
    )

    return 201, {
        "success": True,
        "message": "Draft quote created successfully",
        "data": DraftQuoteResponseSchema(
            quote_number=quote.quote_number,
            status=quote.status,
            completed_steps=quote.completed_steps,
            current_step=quote.current_step,
        ).dict(),
    }


@router.patch(
    "/{quote_number}/step",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema, 500: ApiResponseSchema},
)
def save_quote_step(
    request: HttpRequest, quote_number: str, data: StepSaveSchema
) -> tuple[int, dict[str, Any]]:
    """Save a single form step for auto-save as the user progresses.

    Updates the form data snapshot, marks the step as completed, and
    optionally advances to the next step. If the quote was already rated,
    it resets to ``draft`` status.

    Args:
        request: HTTP request with JWT-authenticated user.
        quote_number: Unique quote identifier.
        data: Step ID, form data for that step, and optional next step.

    Returns:
        200 with updated step tracking, or 404 if quote not found.
    """
    user = request.auth

    quote = QuoteService.save_step(
        quote_number=quote_number,
        step_id=data.step_id,
        data=data.data,
        user=user,
        next_step=data.next_step,
    )

    if not quote:
        return 404, {
            "success": False,
            "message": "Quote not found or access denied",
            "data": None,
        }

    return 200, {
        "success": True,
        "message": "Step saved successfully",
        "data": {
            "quote_number": quote.quote_number,
            "completed_steps": quote.completed_steps,
        },
    }


@router.post(
    "/",
    auth=JWTAuth(),
    response={201: ApiResponseSchema, 400: ApiResponseSchema, 500: ApiResponseSchema},
)
def create_quote(
    request: HttpRequest,
    data: str = Form(...),
    financial_files: List[UploadedFile] = File(None),
    transaction_files: List[UploadedFile] = File(None),
    claim_files: List[UploadedFile] = File(None),
) -> tuple[int, dict[str, Any]]:
    """Submit a completed quote for rating.

    Accepts multipart form data: JSON string ``data`` plus optional file uploads
    for financial statements, transaction documents, and claim documents.
    Creates/updates the company, creates the quote, uploads files to S3,
    triggers the rating engine, and (for Workers' Comp) initiates Skyvern automation.

    Args:
        request: HTTP request with JWT-authenticated user.
        data: JSON string conforming to ``QuoteCreateSchema``.
        financial_files: Optional financial statement uploads.
        transaction_files: Optional transaction document uploads.
        claim_files: Optional claim document uploads.

    Returns:
        201 with quote details and rating result.
    """
    validated_data = parse_form_data_json(data, QuoteCreateSchema)
    user = request.auth

    # ── Schema-drift enforcement (H6) ────────────────────────────────
    # Older in-flight quotes may have been started before new required
    # fields were added to specialized coverage schemas (e.g. Crime).
    # Re-validate every such coverage payload against the LATEST active
    # schema version BEFORE we persist the quote.
    form_data_dict = validated_data.model_dump(mode="json")
    coverage_payloads = extract_coverage_payloads_from_form_data(form_data_dict)
    schema_errors = validate_coverage_payloads(coverage_payloads)
    if schema_errors:
        return 400, build_validation_error_response(schema_errors)

    quote = QuoteService.create_quote(
        form_data=form_data_dict,
        financial_files=financial_files or [],
        transaction_files=transaction_files or [],
        claim_files=claim_files or [],
        user=user,
    )

    rating_result = QuoteService.process_quote_rating(quote)

    return 201, {
        "success": True,
        "message": "Quote created successfully",
        "data": QuoteResponseSchema.from_quote(
            quote,
            rating_result=rating_result,
        ).dict(),
    }


@router.patch(
    "/{quote_number}/",
    auth=JWTAuth(),
    response={
        200: ApiResponseSchema,
        400: ApiResponseSchema,
        404: ApiResponseSchema,
        500: ApiResponseSchema,
    },
)
def update_quote(
    request: HttpRequest,
    quote_number: str,
    data: QuoteCreateSchema,
) -> tuple[int, dict[str, Any]]:
    """Update an existing quote and re-run the rating engine.

    Replaces the company data, coverages, and questionnaire answers,
    then triggers a fresh rating calculation.

    Args:
        request: HTTP request with JWT-authenticated user.
        quote_number: Unique quote identifier.
        data: Full quote data conforming to ``QuoteCreateSchema``.

    Returns:
        200 with updated quote and new rating result, or 404.
    """
    user = request.auth

    # ── Schema-drift enforcement (H6) — mirror of create_quote ───────
    form_data_dict = data.model_dump(mode="json")
    coverage_payloads = extract_coverage_payloads_from_form_data(form_data_dict)
    schema_errors = validate_coverage_payloads(coverage_payloads)
    if schema_errors:
        return 400, build_validation_error_response(schema_errors)

    quote = QuoteService.update_and_recalculate_quote(
        quote_number=quote_number, form_data=form_data_dict, user=user
    )

    if not quote:
        return 404, {
            "success": False,
            "message": "Quote not found or access denied",
            "data": None,
        }

    rating_result = QuoteService.process_quote_rating(quote)

    return 200, {
        "success": True,
        "message": "Quote updated and recalculated successfully",
        "data": QuoteResponseSchema.from_quote(
            quote,
            rating_result=rating_result,
        ).dict(),
    }


@router.get(
    "/{quote_number}/form-data",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema},
)
def get_quote_form_data(
    request: HttpRequest, quote_number: str
) -> tuple[int, dict[str, Any]]:
    """Retrieve full form data for resuming or reviewing a quote.

    Returns the complete form data snapshot along with pricing info,
    promo discount details, and split coverage information needed
    by the frontend to render the quote form and summary page.

    Args:
        request: HTTP request with JWT-authenticated user.
        quote_number: Unique quote identifier.

    Returns:
        200 with form data, step tracking, and pricing, or 404.
    """
    form_data = QuoteService.get_quote_form_data(quote_number, request.auth)

    if not form_data:
        return 404, {"success": False, "message": "Quote not found", "data": None}

    return 200, {
        "success": True,
        "message": "Quote form data retrieved successfully",
        "data": form_data,
    }


@router.get("/me", auth=JWTAuth(), response={200: ApiResponseSchema})
def get_user_quotes(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """List all non-purchased quotes for the current organization.

    Returns:
        200 with a list of quote summaries (id, quote_number, status, etc.).
    """
    quotes = QuoteService.get_quotes_for_user(request.auth)
    return 200, {
        "success": True,
        "message": "Quotes retrieved successfully",
        "data": quotes,
    }


@router.get(
    "/{quote_number}",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema},
)
def get_quote(request: HttpRequest, quote_number: str) -> tuple[int, dict[str, Any]]:
    """Retrieve quote details with pricing breakdown.

    Includes annual/monthly amounts, custom product totals,
    and the per-coverage rating breakdown.

    Args:
        request: HTTP request with JWT-authenticated user.
        quote_number: Unique quote identifier.

    Returns:
        200 with detailed quote data, or 404.
    """
    quote_data = QuoteService.get_quote_by_number(quote_number, request.auth)
    if not quote_data:
        return 404, {"success": False, "message": "Quote not found", "data": None}
    return 200, {
        "success": True,
        "message": "Quote retrieved successfully",
        "data": quote_data,
    }


@router.post(
    "/{quote_number}/checkout",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 400: ApiResponseSchema, 404: ApiResponseSchema},
)
def create_checkout(
    request: HttpRequest, quote_number: str, data: CheckoutRequestSchema
) -> tuple[int, dict[str, Any]]:
    """Generate a Stripe checkout URL for purchasing the quote.

    Supports annual (one-time) and monthly (subscription) billing.
    For mixed quotes with both instant and review coverages, the
    ``coverages`` field selects which subset to purchase.

    Args:
        request: HTTP request with JWT-authenticated user.
        quote_number: Unique quote identifier.
        data: Billing frequency, optional effective date, optional coverage subset.

    Returns:
        200 with the Stripe checkout URL, or 404 if not ready.
    """
    checkout_url = QuoteService.create_checkout_url(
        quote_number=quote_number,
        user=request.auth,
        billing_frequency=data.billing_frequency,
        effective_date=data.effective_date,
        coverages=data.coverages,
        success_url=data.success_url,
        cancel_url=data.cancel_url,
    )

    if checkout_url is None:
        return 404, {
            "success": False,
            "message": "Quote not found or not ready for payment",
            "data": None,
        }

    return 200, {
        "success": True,
        "message": "Checkout URL generated successfully",
        "data": {
            "checkout_url": checkout_url,
        },
    }


@router.post(
    "/{quote_number}/documents",
    auth=JWTAuth(),
    response={
        201: ApiResponseSchema,
        400: ApiResponseSchema,
        404: ApiResponseSchema,
        500: ApiResponseSchema,
    },
)
def upload_quote_document(
    request: HttpRequest,
    quote_number: str,
    file: UploadedFile = File(...),
    document_type: str = Form("claim-documents"),
) -> tuple[int, dict[str, Any]]:
    """Upload a document (e.g. claim/lawsuit PDF) for an existing draft quote.

    Used mid-flow (e.g. from the loss-history step) so files don't have to
    wait until final submission. The file is stored in S3 and a
    ``QuoteDocument`` row is created. ``document_type`` defaults to
    ``claim-documents``; ``financial-statements`` and
    ``transaction-documents`` are also accepted.

    Args:
        request: HTTP request with JWT-authenticated user.
        quote_number: Unique quote identifier.
        file: Uploaded file (multipart).
        document_type: Category string stored on ``QuoteDocument.file_type``.

    Returns:
        201 with the document metadata, 404 if the quote isn't accessible.
    """
    allowed_types = {"claim-documents", "financial-statements", "transaction-documents"}
    if document_type not in allowed_types:
        return 400, {
            "success": False,
            "message": f"Invalid document_type '{document_type}'. Allowed: {sorted(allowed_types)}",
            "data": None,
        }

    result = QuoteService.upload_quote_document(
        quote_number=quote_number,
        file=file,
        document_type=document_type,
        user=request.auth,
    )

    if result is None:
        return 404, {
            "success": False,
            "message": "Quote not found or access denied",
            "data": None,
        }

    return 201, {
        "success": True,
        "message": "Document uploaded successfully",
        "data": result,
    }


@router.post(
    "/{quote_number}/move",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 403: ApiResponseSchema, 404: ApiResponseSchema},
)
def move_quote(
    request: HttpRequest, quote_number: str, data: MoveQuoteSchema
) -> tuple[int, dict[str, Any]]:
    """Move a quote to a different organization.

    The user must have editor permissions in both the source and
    target organizations.

    Args:
        request: HTTP request with JWT-authenticated user.
        quote_number: Unique quote identifier.
        data: Target organization ID.

    Returns:
        200 on success, 403 if insufficient permissions.
    """
    QuoteService.move_quote_to_org(
        quote_number=quote_number,
        target_org_id=data.organization_id,
        user=request.auth,
    )
    return 200, {
        "success": True,
        "message": "Quote moved successfully",
        "data": None,
    }


@router.post(
    "/{quote_number}/bind",
    auth=JWTAuth(),
    response={
        200: ApiResponseSchema,
        400: ApiResponseSchema,
        404: ApiResponseSchema,
    },
)
def bind_quote(request: HttpRequest, quote_number: str) -> tuple[int, dict[str, Any]]:
    """Initiate binding workflow for a quote.

    Marks the quote as ready for binding. The quote must be in 'quoted' status.

    Args:
        request: HTTP request with JWT-authenticated user.
        quote_number: Unique quote identifier.

    Returns:
        200 on success, 400 if not in correct status, 404 if not found.
    """
    try:
        quote = Quote.objects.get(quote_number=quote_number, user=request.auth)
    except Quote.DoesNotExist:
        return 404, {
            "success": False,
            "message": "Quote not found",
            "data": None,
        }

    if quote.status != "quoted":
        return 400, {
            "success": False,
            "message": f'Quote must be in "quoted" status to bind (current: {quote.status})',
            "data": None,
        }

    # Mark as binding initiated — downstream checkout or manual process handles activation
    quote.status = "binding"
    quote.save(update_fields=["status"])

    return 200, {
        "success": True,
        "message": "Binding initiated successfully",
        "data": {"quote_number": quote.quote_number, "status": quote.status},
    }


# ── Membership Agreement (H5) ────────────────────────────────────────────────
# Crime and Umbrella products require a signed membership agreement at checkout.
# The full flow lands when Josh delivers the spec. For now the endpoint exists
# behind the MEMBERSHIP_AGREEMENT_ENABLED feature flag so the frontend wiring
# can be completed.


class MembershipAgreementSignSchema(Schema):
    signed_agreement_id: str


def _membership_agreement_enabled() -> bool:
    return os.environ.get("MEMBERSHIP_AGREEMENT_ENABLED", "").lower() == "true"


@router.post(
    "/{quote_number}/membership-agreement/sign",
    auth=JWTAuth(),
    response={
        200: ApiResponseSchema,
        404: ApiResponseSchema,
        501: ApiResponseSchema,
    },
)
def sign_membership_agreement(
    request: HttpRequest,
    quote_number: str,
    data: MembershipAgreementSignSchema,
) -> tuple[int, dict[str, Any]]:
    """Record a signed membership agreement for a quote (H5 stub).

    Crime and Umbrella products require signing a membership agreement before
    checkout. This endpoint is gated by the ``MEMBERSHIP_AGREEMENT_ENABLED``
    env var. When the flag is off we return 501. When the flag is on the real
    signing service is invoked — which currently raises ``NotImplementedError``
    until Josh's spec is delivered.

    Args:
        request: HTTP request with JWT-authenticated user.
        quote_number: Unique quote identifier.
        data: Body containing ``signed_agreement_id`` returned by the e-sign provider.

    Returns:
        200 when the signature is verified and stored, 404 if the quote does not
        exist, or 501 when the feature flag is disabled.
    """
    if not _membership_agreement_enabled():
        return 501, {
            "success": False,
            "message": "Membership agreement flow is not enabled",
            "data": None,
        }

    try:
        quote = Quote.objects.get(quote_number=quote_number, user=request.auth)
    except Quote.DoesNotExist:
        return 404, {
            "success": False,
            "message": "Quote not found",
            "data": None,
        }

    # Will raise NotImplementedError until Josh delivers the spec — surfaced
    # to the caller as a 500 by the framework, which is the intended behaviour
    # for a flag-on-but-unimplemented state.
    from certificates.signing_service import MembershipAgreementService

    MembershipAgreementService.verify_signature(quote, data.signed_agreement_id)

    return 200, {
        "success": True,
        "message": "Membership agreement recorded",
        "data": {
            "quote_number": quote.quote_number,
            "signed_agreement_id": data.signed_agreement_id,
        },
    }
