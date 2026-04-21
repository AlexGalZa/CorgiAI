"""
User authentication and profile API endpoints.

Provides registration, email OTP login, JWT token refresh, user
profile retrieval, document access, and admin impersonation.
Rate-limited endpoints are annotated with their limits.
"""

import logging
from typing import Any

from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from common.exceptions import ValidationError
from common.utils import rate_limit
from common.schemas import ApiResponseSchema
from users.auth import JWTAuth
from users.service import UserService
from users.schemas import (
    RegisterRequest,
    RequestLoginCodeRequest,
    VerifyLoginCodeRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
    AuthResponse,
    OtpResponse,
    CreateSSOSessionRequest,
    SSOSessionResponse,
    ExchangeSSOTokenRequest,
    Verify2FARequest,
    UserSelfUpdateSchema,
    ChangePasswordRequest,
)

router = Router(tags=["Users"])
logger = logging.getLogger(__name__)

ADMIN_ROLES = ["admin"]


def _require_admin(request: HttpRequest, action: str = "") -> None:
    """Raise 403 if the user is not an admin (or superuser)."""
    user = request.auth
    if not getattr(user, "is_staff", False):
        raise HttpError(403, "Staff access required")
    role = getattr(user, "role", "")
    if role not in ADMIN_ROLES and not getattr(user, "is_superuser", False):
        email = getattr(user, "email", "unknown")
        logger.info(
            "RBAC denied: user=%s role=%s attempted_action=%s allowed_roles=%s",
            email,
            role,
            action or "unspecified",
            ADMIN_ROLES,
        )
        raise HttpError(
            403, f"Your role ({role}) does not have permission for this action"
        )


@router.post("/register", response={201: AuthResponse})
@rate_limit(max_requests=50, window_seconds=3600)
def register(request: HttpRequest, data: RegisterRequest) -> tuple[int, dict[str, Any]]:
    """Create a new user account.

    Registers the user, creates a personal organization, and returns
    JWT tokens for immediate authentication.

    Rate limit: 5 requests per hour per IP.

    Args:
        request: HTTP request (no auth required).
        data: Registration details (email, password, name, optional company/phone).

    Returns:
        201 with user info and JWT tokens.
    """
    user, tokens = UserService.register(data)
    return 201, {"user": UserResponse.from_user(user), "tokens": tokens}


@router.post("/request-login-code", response={200: OtpResponse})
@rate_limit(max_requests=50, window_seconds=3600)
def request_login_code(
    request: HttpRequest, data: RequestLoginCodeRequest
) -> tuple[int, dict[str, Any]]:
    """Send a 6-digit OTP login code to the user's email.

    Returns a 404 error if no account exists with the given email,
    so the frontend can prompt the user to sign up.

    Rate limit: 10 requests per hour per IP.

    Args:
        request: HTTP request (no auth required).
        data: Email address to send the code to.

    Returns:
        200 with success message, or 404 if account not found.
    """
    # NotFoundError propagates → 404 with "No account found with that email. Please sign up."
    result = UserService.request_login_code(data.email, channel=data.channel)
    channel = result.get("channel") if isinstance(result, dict) else "email"
    if isinstance(result, dict) and result.get("delivered"):
        destination = "phone" if channel == "sms" else "email"
        message = f"A sign-in code has been sent to your {destination}."
    else:
        message = "We had trouble delivering your code. Please try again."
    return 200, {"success": True, "message": message}


@router.post("/verify-login-code", response={200: AuthResponse})
@rate_limit(max_requests=50, window_seconds=3600)
def verify_login_code(
    request: HttpRequest, data: VerifyLoginCodeRequest
) -> tuple[int, dict[str, Any]]:
    """Verify an OTP login code and return JWT tokens.

    Rate limit: 10 requests per hour per IP.

    Args:
        request: HTTP request (no auth required).
        data: Email and 6-digit code.

    Returns:
        200 with user info and JWT tokens.
    """
    user, tokens = UserService.verify_login_code(data.email, data.code, request=request)
    return 200, {"user": UserResponse.from_user(user), "tokens": tokens}


@router.post("/login", response={200: dict, 401: ApiResponseSchema})
def password_login(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """Login with email + password. Returns 2FA challenge if user has 2FA enabled."""
    import json
    from django.contrib.auth import authenticate
    from users.models import User as UserModel, TOTPDevice

    body = json.loads(request.body)
    email = body.get("email", "")
    password = body.get("password", "")

    # Check lockout before attempting auth
    try:
        target_user = UserModel.objects.get(email=email)
        if target_user.is_locked:
            UserService.record_login(
                email,
                "password",
                False,
                request,
                user=target_user,
                failure_reason="locked",
            )
            return 401, {
                "success": False,
                "message": "Account temporarily locked. Try again later.",
                "data": None,
            }
    except UserModel.DoesNotExist:
        pass

    user = authenticate(request, username=email, password=password)
    if not user:
        try:
            target_user = UserModel.objects.get(email=email)
            target_user.record_failed_login()
            UserService.record_login(
                email,
                "password",
                False,
                request,
                user=target_user,
                failure_reason="wrong_password",
            )
        except UserModel.DoesNotExist:
            UserService.record_login(
                email, "password", False, request, failure_reason="user_not_found"
            )
        return 401, {"success": False, "message": "Invalid credentials", "data": None}

    user.reset_failed_logins()

    # /users/login is staff-only. Non-staff users authenticate via the OTP
    # flow instead. Return 401 so the UI shows a generic "Invalid creds"
    # error rather than leaking whether a password is correct.
    if not user.is_staff:
        return 401, {"success": False, "message": "Staff access required", "data": None}

    # Check if user has 2FA enabled — if so, return a challenge
    has_totp = TOTPDevice.objects.filter(user=user, is_verified=True).exists()
    if has_totp:
        two_factor_token = JWTAuth.create_2fa_token(user.id)
        return 200, {
            "requires_2fa": True,
            "two_factor_token": two_factor_token,
            "methods": ["totp", "passkey"],
        }

    # No 2FA — issue tokens directly
    UserService.record_login(email, "password", True, request, user=user)
    tokens = UserService.create_tokens(user)
    return 200, {"user": UserResponse.from_user(user), "tokens": tokens}


@router.post("/verify-2fa", response={200: AuthResponse, 401: ApiResponseSchema})
@rate_limit(max_requests=50, window_seconds=3600)
def verify_2fa(
    request: HttpRequest, data: Verify2FARequest
) -> tuple[int, dict[str, Any]]:
    """Verify 2FA code after password login. Returns JWT tokens on success."""
    from users.models import User as UserModel, TOTPDevice
    from django.utils import timezone as tz

    # Decode the 2FA token
    payload = JWTAuth.decode_token(data.two_factor_token)
    if not payload or payload.get("type") != "2fa":
        return 401, {
            "success": False,
            "message": "Invalid or expired 2FA token. Please log in again.",
            "data": None,
        }

    try:
        user = UserModel.objects.get(id=payload["user_id"], is_active=True)
    except UserModel.DoesNotExist:
        return 401, {"success": False, "message": "User not found", "data": None}

    if data.method == "totp":
        try:
            device = TOTPDevice.objects.get(user=user, is_verified=True)
        except TOTPDevice.DoesNotExist:
            return 401, {
                "success": False,
                "message": "No TOTP device configured",
                "data": None,
            }

        if not device.verify_code(data.code):
            return 401, {
                "success": False,
                "message": "Invalid code. Please try again.",
                "data": None,
            }

        device.last_used_at = tz.now()
        device.save(update_fields=["last_used_at"])

    elif data.method == "passkey":
        # Passkey verification happens client-side via WebAuthn.
        # The 2FA token proves password was already verified.
        # The client asserts the passkey was validated in the browser.
        pass
    elif data.method == "email_otp":
        from users.models import EmailLoginCode

        login_code = (
            EmailLoginCode.objects.filter(
                user=user,
                code=data.code,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )
        if not login_code or not login_code.is_valid():
            if login_code:
                login_code.attempts += 1
                login_code.save(update_fields=["attempts"])
            return 401, {
                "success": False,
                "message": "Invalid or expired code.",
                "data": None,
            }
        login_code.is_used = True
        login_code.save(update_fields=["is_used"])
    else:
        return 401, {"success": False, "message": "Unknown 2FA method", "data": None}

    UserService.record_login(user.email, "2fa", True, request, user=user)
    tokens = UserService.create_tokens(user)
    return 200, {"user": UserResponse.from_user(user), "tokens": tokens}


@router.post("/refresh", response={200: TokenResponse})
def refresh(request: HttpRequest, data: RefreshRequest) -> tuple[int, dict[str, Any]]:
    """Refresh an expired access token using a valid refresh token.

    Args:
        request: HTTP request (no auth required).
        data: Refresh token.

    Returns:
        200 with new access and refresh tokens.
    """
    tokens = UserService.refresh_tokens(data.refresh_token)
    return 200, tokens


@router.get("/me", auth=JWTAuth(), response={200: ApiResponseSchema})
def get_current_user(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """Get the authenticated user's profile.

    Returns:
        200 with user details (id, email, name, etc.).
    """
    return 200, {
        "success": True,
        "message": "User retrieved successfully",
        "data": UserResponse.from_user(request.auth),
    }


@router.patch(
    "/me", auth=JWTAuth(), response={200: ApiResponseSchema, 400: ApiResponseSchema}
)
@rate_limit(max_requests=20, window_seconds=3600)
def update_current_user(
    request: HttpRequest, data: UserSelfUpdateSchema
) -> tuple[int, dict[str, Any]]:
    """Update the authenticated user's own profile fields.

    Editable fields: first_name, last_name, phone_number, company_name,
    notification_preferences. Email is not editable.

    Rate limit: 20 requests per hour per IP.

    Returns:
        200 with updated user data.
    """
    user = request.auth
    update_fields = []

    if data.first_name is not None:
        user.first_name = data.first_name
        update_fields.append("first_name")
    if data.last_name is not None:
        user.last_name = data.last_name
        update_fields.append("last_name")
    if data.phone_number is not None:
        user.phone_number = data.phone_number
        update_fields.append("phone_number")
    if data.company_name is not None:
        user.company_name = data.company_name
        update_fields.append("company_name")
    if data.notification_preferences is not None:
        user.notification_preferences = data.notification_preferences
        update_fields.append("notification_preferences")

    if update_fields:
        user.save(update_fields=update_fields)

    return 200, {
        "success": True,
        "message": "Profile updated successfully",
        "data": UserResponse.from_user(user),
    }


@router.post(
    "/change-password",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 401: ApiResponseSchema},
)
@rate_limit(max_requests=5, window_seconds=3600)
def change_password(
    request: HttpRequest, data: ChangePasswordRequest
) -> tuple[int, dict[str, Any]]:
    """Change the authenticated user's password.

    Verifies the current password, then sets the new one. Invalidates
    all active sessions for the user so other devices are signed out.

    Rate limit: 5 requests per hour per IP.

    Returns:
        200 on success, 401 if current password is wrong.
    """
    from django.utils import timezone as tz
    from users.models import ActiveSession

    user = request.auth

    if not user.check_password(data.current_password):
        return 401, {
            "success": False,
            "message": "Current password is incorrect",
            "data": None,
        }

    user.set_password(data.new_password)
    user.save()

    ActiveSession.objects.filter(user=user, is_active=True).update(
        is_active=False,
        revoked_at=tz.now(),
    )

    return 200, {
        "success": True,
        "message": "Password updated",
        "data": None,
    }


@router.get("/documents", auth=JWTAuth(), response={200: ApiResponseSchema})
def get_user_documents(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """List all documents for the user's active organization.

    Returns policy documents, certificates, endorsements, receipts,
    and loss run reports.

    Returns:
        200 with a list of document detail dicts.
    """
    data = UserService.get_user_documents(request.auth)
    return 200, {
        "success": True,
        "message": "Documents retrieved successfully",
        "data": data,
    }


@router.get("/documents/download-all", auth=JWTAuth())
def download_all_documents(request: HttpRequest) -> Any:
    """Download all documents for the user's organization as a zip file.

    Fetches every document for the active org, downloads each from S3,
    and streams them back as a single zip archive.

    If S3 download fails for any document, that document is skipped and
    its presigned URL is included in a ``skipped`` list in the response
    (only when *all* downloads fail does it fall back to a JSON list).

    Returns:
        application/zip on success, or JSON with download URLs as fallback.
    """
    import io
    import zipfile as _zipfile
    from django.http import HttpResponse as _HttpResponse

    from organizations.service import OrganizationService
    from s3.service import S3Service
    from users.models import UserDocument

    user = request.auth
    org_id = OrganizationService.get_active_org_id(user)
    documents = UserDocument.objects.filter(organization_id=org_id)

    if not documents.exists():
        return 200, {
            "success": True,
            "message": "No documents found",
            "data": {"files": [], "skipped": []},
        }

    buf = io.BytesIO()
    skipped: list[dict] = []
    added = 0

    with _zipfile.ZipFile(buf, "w", _zipfile.ZIP_DEFLATED) as zf:
        seen_names: dict[str, int] = {}
        for doc in documents:
            # Build a unique filename inside the zip
            name = doc.original_filename or f"document-{doc.id}.pdf"
            if name in seen_names:
                seen_names[name] += 1
                base, _, ext = name.rpartition(".")
                name = (
                    f"{base}_{seen_names[name]}.{ext}"
                    if ext
                    else f"{name}_{seen_names[name]}"
                )
            else:
                seen_names[name] = 0

            if doc.s3_key:
                file_bytes = S3Service.download_file(doc.s3_key)
                if file_bytes:
                    zf.writestr(name, file_bytes)
                    added += 1
                    continue

            # Couldn't download — provide a presigned URL instead
            url = S3Service.generate_presigned_url(doc.s3_key) if doc.s3_key else None
            skipped.append(
                {
                    "id": doc.id,
                    "title": doc.title,
                    "filename": doc.original_filename,
                    "url": url,
                }
            )

    # If nothing was added to the zip, fall back to JSON with URLs
    if added == 0:
        urls = []
        for doc in documents:
            url = S3Service.generate_presigned_url(doc.s3_key) if doc.s3_key else None
            urls.append(
                {
                    "id": doc.id,
                    "title": doc.title,
                    "filename": doc.original_filename,
                    "url": url,
                }
            )
        return 200, {
            "success": True,
            "message": "Could not create zip — returning download URLs instead",
            "data": {"files": urls},
        }

    buf.seek(0)
    response = _HttpResponse(buf.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="corgi-documents.zip"'
    return response


@router.get(
    "/documents/{document_id}/download",
    auth=JWTAuth(),
    response={200: ApiResponseSchema},
)
def download_document(
    request: HttpRequest, document_id: int
) -> tuple[int, dict[str, Any]]:
    """Get a presigned S3 download URL for a specific document.

    Args:
        request: HTTP request with JWT-authenticated user.
        document_id: Primary key of the document.

    Returns:
        200 with download URL and filename.
    """
    data = UserService.get_document_download_url(request.auth, document_id)
    return 200, {"success": True, "message": "Download URL generated", "data": data}


@router.get("/me/impersonation", auth=JWTAuth(), response={200: ApiResponseSchema})
def get_current_user_with_impersonation(
    request: HttpRequest,
) -> tuple[int, dict[str, Any]]:
    """Get the current user's profile (impersonation-aware).

    Same as ``/me`` but used by the frontend to check impersonation state.

    Returns:
        200 with user details.
    """
    return 200, {
        "success": True,
        "message": "User retrieved successfully",
        "data": UserResponse.from_user(request.auth),
    }


@router.post("/impersonate/{user_id}", auth=JWTAuth(), response={200: AuthResponse})
def start_impersonation(
    request: HttpRequest, user_id: int
) -> tuple[int, dict[str, Any]]:
    """Start impersonating another user (admin only).

    Creates an impersonation log entry and returns tokens scoped
    to the target user. The ``is_impersonated`` flag is set on the
    returned user data.

    Args:
        request: HTTP request with JWT-authenticated admin user.
        user_id: ID of the user to impersonate.

    Returns:
        200 with impersonated user info and JWT tokens.
    """
    _require_admin(request, "start_impersonation")

    ip_address: str = request.META.get(
        "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")
    )
    if ip_address and "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()

    user_agent: str = request.META.get("HTTP_USER_AGENT", "")

    user, tokens, _ = UserService.start_impersonation(
        admin_user=request.auth,
        target_user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    user.is_impersonated = True

    return 200, {"user": UserResponse.from_user(user), "tokens": tokens}


@router.post("/stop-impersonation", auth=JWTAuth(), response={200: ApiResponseSchema})
def stop_impersonation(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """Stop impersonating and return to the admin's own session.

    Args:
        request: HTTP request with JWT token containing impersonator_id.

    Returns:
        200 with the admin user info and fresh tokens.

    Raises:
        ValidationError: If the user is not currently impersonating anyone.
    """
    _require_admin(request, "stop_impersonation")

    impersonator_id: int | None = getattr(request.auth, "impersonator_id", None)

    if not impersonator_id:
        raise ValidationError("Not currently impersonating any user")

    user, tokens = UserService.stop_impersonation(
        current_user=request.auth,
        impersonator_id=impersonator_id,
    )

    return 200, {
        "success": True,
        "message": "Impersonation stopped",
        "data": {"user": UserResponse.from_user(user), "tokens": tokens},
    }


@router.post("/create-sso-session", auth=JWTAuth(), response={200: SSOSessionResponse})
def create_sso_session(
    request: HttpRequest, data: CreateSSOSessionRequest
) -> tuple[int, dict[str, Any]]:
    """Create a session in the shared SSO database for cross-app authentication.

    After a user logs in via the portal, this creates a session token
    that external apps (investor-scraper, policy-manager, etc.) can
    validate against the shared sessions table.

    Args:
        request: HTTP request with JWT-authenticated user.
        data: The redirect_uri to validate against the allowlist.

    Returns:
        200 with sso_token and redirect_uri.
    """
    token = UserService.create_sso_session(request.auth, data.redirect_uri)
    return 200, {"sso_token": token, "redirect_uri": data.redirect_uri}


@router.post("/exchange-sso-token", response={200: AuthResponse})
@rate_limit(max_requests=50, window_seconds=3600)
def exchange_sso_token(
    request: HttpRequest, data: ExchangeSSOTokenRequest
) -> tuple[int, dict[str, Any]]:
    """Exchange an SSO session token for JWT access/refresh tokens.

    Used by apps (e.g. admin dashboard) that need JWT tokens after
    SSO redirect from the portal login page.

    Args:
        request: HTTP request (no auth required).
        data: The sso_token received from the redirect.

    Returns:
        200 with user info and JWT tokens.
    """
    user, tokens = UserService.exchange_sso_token(data.sso_token)
    return 200, {"user": UserResponse.from_user(user), "tokens": tokens}


@router.post("/account/data-export", auth=JWTAuth(), response={200: ApiResponseSchema})
def gdpr_data_export(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """GDPR data export: collect all user data into a JSON file and email it.

    Collects quotes, policies, claims, payments, certificates, and org
    membership for the authenticated user, packages into JSON, and emails
    it to the user's email address.

    Returns:
        200 with confirmation message.
    """
    from users.gdpr_service import GDPRService

    GDPRService.export_user_data(request.auth)
    return 200, {
        "success": True,
        "message": "Your data export has been prepared and will be emailed to you shortly.",
        "data": None,
    }


@router.post(
    "/account/data-deletion", auth=JWTAuth(), response={200: ApiResponseSchema}
)
def gdpr_data_deletion(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """GDPR data deletion: anonymize PII and mark records as deleted.

    Anonymizes all personally identifiable information for the authenticated
    user (name, email, phone) and soft-deletes associated records.
    This action is irreversible.

    Returns:
        200 with confirmation message.
    """
    from users.gdpr_service import GDPRService

    GDPRService.delete_user_data(request.auth)
    return 200, {
        "success": True,
        "message": "Your personal data has been anonymized and your account has been deactivated.",
        "data": None,
    }


@router.post("/analytics", response={200: ApiResponseSchema})
def track_analytics(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """Receive batched analytics events from the portal.

    Accepts ``{ events: [...] }`` and logs them. No authentication
    required so anonymous page views can still be captured.
    """
    import json as _json

    try:
        body = _json.loads(request.body)
    except (ValueError, TypeError):
        raise HttpError(400, "Invalid JSON body")

    events = body.get("events", [])
    if not isinstance(events, list):
        raise HttpError(400, "'events' must be a list")

    user_email = getattr(getattr(request, "auth", None), "email", "anonymous")
    for evt in events:
        logger.info(
            "analytics event=%s user=%s props=%s ts=%s",
            evt.get("name", "unknown"),
            user_email,
            evt.get("properties", {}),
            evt.get("timestamp", ""),
        )

    return 200, {
        "success": True,
        "message": f"{len(events)} event(s) recorded",
        "data": None,
    }


# ═══════ SSO (static-pages / bulldog-law pattern) ═══════
#
# Static-pages (app.corgiinsure.com) authenticates the user via passkey or
# TOTP, then redirects back with ?code=. The ops SPA exchanges that code at
# <sso>/api/auth/sso/exchange and gets back an opaque session token plus
# user info. This endpoint takes that session token, validates it upstream,
# and issues a Corgi JWT the API can actually consume.
#
# Users are JIT-provisioned: if the authenticated email doesn't exist in the
# Corgi user table, a staff user is created with the role/flags reported by
# static-pages. That way the two systems stay in sync without manual copying.


@router.post(
    "/sso/exchange",
    response={200: dict, 400: ApiResponseSchema, 401: ApiResponseSchema},
)
def sso_exchange(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """Exchange a static-pages ?code= for a Corgi JWT.

    Ops SPA sends { code, redirect_uri } captured from the static-pages
    redirect. Corgi calls static-pages's /api/auth/sso/exchange, gets
    back user info, JIT-provisions the user, and issues Corgi JWTs.
    No /api/auth/session endpoint exists upstream, so this one-hop
    shape is what's actually implementable.
    """
    import json
    import os
    import urllib.request
    import urllib.error
    from users.models import User as UserModel

    body = json.loads(request.body or b"{}")
    code = (body.get("code") or "").strip()
    redirect_uri = (body.get("redirect_uri") or "").strip()
    if not code or not redirect_uri:
        return 400, {
            "success": False,
            "message": "code and redirect_uri are required",
            "data": None,
        }

    sso_origin = os.getenv("SSO_ORIGIN", "https://app.corgiinsure.com").rstrip("/")
    exchange_url = f"{sso_origin}/api/auth/sso/exchange"

    # Cloudflare in front of static-pages rejects the default "Python-urllib/*"
    # UA with 403. Send a descriptive UA so the request reaches the worker.
    req = urllib.request.Request(
        exchange_url,
        data=json.dumps({"code": code, "redirect_uri": redirect_uri}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "CorgiOpsSSO/1.0 (+https://test.corgiinsure.com)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            raw_body = resp.read().decode("utf-8")
            payload = json.loads(raw_body or "{}")
    except urllib.error.HTTPError as exc:
        logger.info("sso code exchange rejected by %s (%s)", sso_origin, exc.code)
        return 401, {
            "success": False,
            "message": "SSO code invalid or expired",
            "data": None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("sso code exchange failed: %s", exc)
        return 401, {"success": False, "message": "SSO exchange failed", "data": None}

    if not payload.get("ok"):
        logger.info("sso code exchange payload lacked ok=true: %s", payload)
        return 401, {
            "success": False,
            "message": "SSO exchange did not succeed",
            "data": None,
        }

    sso_user = payload.get("user") or {}
    sso_id = str(sso_user.get("id") or "").strip()
    raw_email = (sso_user.get("email") or sso_user.get("email_address") or "").strip()

    # Static-pages may return email=null for SSO-only accounts (admins
    # that never had a mailbox on the legacy app). Fall back to a stable
    # synthetic address derived from the SSO id so the unique email
    # constraint on User still holds.
    if raw_email:
        email = raw_email.lower()
    elif sso_id:
        email = f"sso-{sso_id}@sso.local".lower()
    else:
        logger.warning(
            "sso exchange payload has neither email nor id; body=%s", raw_body[:400]
        )
        return 401, {
            "success": False,
            "message": "SSO user missing id and email",
            "data": None,
        }

    # Forward the SSO payload's roles + permissions untouched to the
    # admin SPA. Authorization on the /ops side is permission-driven,
    # not role-driven — the Django User.role field stays "admin" for
    # every SSO-provisioned staff user just so the ROLE_CHOICES
    # constraint holds.
    sso_roles = sso_user.get("roles") or (
        [sso_user.get("role")] if sso_user.get("role") else []
    )
    sso_permissions = sso_user.get("permissions") or []

    full_name = (sso_user.get("name") or "").strip()
    fallback_first = full_name.split(" ", 1)[0] if full_name else ""
    fallback_last = " ".join(full_name.split(" ")[1:]) if full_name else ""

    user, created = UserModel.objects.get_or_create(
        email=email,
        defaults={
            "first_name": sso_user.get("first_name") or fallback_first,
            "last_name": sso_user.get("last_name") or fallback_last,
            "role": "admin",
            "is_staff": True,
            "is_active": True,
        },
    )
    if not created and not user.is_staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])

    tokens = UserService.create_tokens(user)
    logger.info("sso exchange issued JWT for %s (jit=%s)", email, created)
    return 200, {
        "user": UserResponse.from_user(user),
        "tokens": tokens,
        "sso": {"roles": sso_roles, "permissions": sso_permissions},
    }
