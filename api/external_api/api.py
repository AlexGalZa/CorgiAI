from typing import Optional

from ninja import Router, Query

from common.utils import rate_limit
from external_api.auth import ApiKeyAuth
from external_api.schemas import (
    QuoteDetailSchema,
    QuoteListSchema,
    QuoteResponse,
    QuoteListResponse,
    PolicyDetailSchema,
    PolicyListSchema,
    PolicyResponse,
    PolicyListResponse,
    RedeemInviteInput,
    RedeemInviteData,
    RedeemInviteResponse,
    CreateQuoteInput,
)
from api_keys.service import ApiKeyService
from external_api.constants import PAGINATION_MAX_LIMIT
from quotes.service import QuoteService
from policies.models import Policy


def _api_key_bucket(request):
    """Rate-limit bucket keyed by API key prefix; falls back to IP."""
    key = getattr(request, "auth", None)
    return getattr(key, "prefix", None)


router = Router(auth=ApiKeyAuth())
policies_router = Router(auth=ApiKeyAuth())
public_router = Router()


def _serialize_policy(policy: Policy) -> dict:
    """Serialize a Policy to the non-PII fields exposed via the external API."""
    return {
        "policy_number": policy.policy_number,
        "coverage_type": policy.coverage_type or "",
        "carrier": policy.carrier or "",
        "is_brokered": bool(policy.is_brokered),
        "status": policy.status,
        "effective_date": policy.effective_date.isoformat()
        if policy.effective_date
        else "",
        "expiration_date": policy.expiration_date.isoformat()
        if policy.expiration_date
        else "",
        "premium": float(policy.premium) if policy.premium is not None else 0.0,
    }


@public_router.post("/invites/{token}/redeem", response=RedeemInviteResponse, auth=None)
def redeem_invite(request, token: str, payload: RedeemInviteInput):
    success, message, raw = ApiKeyService.redeem_invite(
        token=token,
        first_name=payload.first_name,
        last_name=payload.last_name,
        org_name=payload.org_name,
        email=payload.email,
    )
    if not success:
        return RedeemInviteResponse(success=False, message=message)
    return RedeemInviteResponse(
        success=True,
        message=message,
        data=RedeemInviteData(api_key=raw),
    )


@router.post("", response=QuoteResponse)
@rate_limit(max_requests=60, window_seconds=60, key_func=_api_key_bucket)
def create_quote(request, payload: CreateQuoteInput):
    try:
        quote = QuoteService.create_quote_for_external(payload, request.auth)
    except ValueError as e:
        return QuoteResponse(success=False, message=str(e))
    if quote is None:
        return QuoteResponse(success=False, message="Failed to create quote")
    return QuoteResponse(
        success=True,
        message="Quote created successfully",
        data=QuoteDetailSchema(**quote),
    )


@router.get("", response=QuoteListResponse)
def list_quotes(
    request,
    limit: int = Query(50, ge=1, le=PAGINATION_MAX_LIMIT),
    offset: int = Query(0, ge=0),
):
    total, results = QuoteService.get_all_quotes_for_external(
        limit=limit, offset=offset
    )
    return QuoteListResponse(
        success=True,
        message="Quotes retrieved successfully",
        data=QuoteListSchema(
            total=total,
            limit=limit,
            offset=offset,
            results=[QuoteDetailSchema(**q) for q in results],
        ),
    )


@router.get("/{identifier}", response=QuoteResponse)
def get_quote(request, identifier: str):
    quote = QuoteService.get_quote_for_external(identifier)
    if quote is None:
        return QuoteResponse(success=False, message="Quote not found")
    return QuoteResponse(
        success=True,
        message="Quote retrieved successfully",
        data=QuoteDetailSchema(**quote),
    )


@policies_router.get("", response=PolicyListResponse)
def list_policies(
    request,
    limit: int = Query(50, ge=1, le=PAGINATION_MAX_LIMIT),
    offset: int = Query(0, ge=0),
    organization_id: Optional[int] = Query(None),
):
    """List policies scoped to the API key's organization (read-only)."""
    api_key = request.auth
    org = getattr(api_key, "organization", None)

    qs = Policy.objects.select_related("quote").order_by("-created_at")
    if org is not None:
        qs = qs.filter(quote__organization=org)
    if organization_id is not None:
        qs = qs.filter(quote__organization_id=organization_id)

    total = qs.count()
    results = [_serialize_policy(p) for p in qs[offset : offset + limit]]

    return PolicyListResponse(
        success=True,
        message="Policies retrieved successfully",
        data=PolicyListSchema(
            total=total,
            limit=limit,
            offset=offset,
            results=[PolicyDetailSchema(**r) for r in results],
        ),
    )


@policies_router.get("/{policy_number}", response=PolicyResponse)
def get_policy(request, policy_number: str):
    """Retrieve a single policy by policy_number, scoped to the API key's organization."""
    api_key = request.auth
    org = getattr(api_key, "organization", None)

    qs = Policy.objects.select_related("quote")
    if org is not None:
        qs = qs.filter(quote__organization=org)

    try:
        policy = qs.get(policy_number=policy_number)
    except Policy.DoesNotExist:
        return PolicyResponse(success=False, message="Policy not found")

    return PolicyResponse(
        success=True,
        message="Policy retrieved successfully",
        data=PolicyDetailSchema(**_serialize_policy(policy)),
    )
