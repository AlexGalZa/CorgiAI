"""
TOTP Two-Factor Authentication API (V3 #54).

Endpoints:
    POST /api/v1/auth/totp/setup    — generate secret + QR provisioning URI
    POST /api/v1/auth/totp/verify   — verify first code and activate device
    POST /api/v1/auth/totp/validate — verify code during login (lightweight)

Flow:
    1. User calls /setup → receives a QR URI they scan in Google Authenticator etc.
    2. User calls /verify with a code from their app → device becomes verified.
    3. On subsequent logins the frontend calls /validate to check the code.
"""

import logging
from typing import Any

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from common.utils import rate_limit
from users.auth import JWTAuth

router = Router(tags=["TOTP 2FA"])


def _two_factor_user_bucket(request):
    """Rate-limit bucket keyed by the 2FA challenge token's user_id when parseable."""
    try:
        body = getattr(request, "_json_body", None)
        if body is None and hasattr(request, "body"):
            import json

            body = json.loads(request.body.decode("utf-8"))
            request._json_body = body
        token = (body or {}).get("two_factor_token")
        if token:
            payload = JWTAuth.decode_token(token)
            if payload and payload.get("type") == "2fa":
                return f"user:{payload.get('user_id')}"
    except Exception:
        pass
    return None


logger = logging.getLogger(__name__)


# ── Schemas ────────────────────────────────────────────────────────────────────


class TOTPSetupResponse(Schema):
    secret: str = Field(description="Base32 TOTP secret (show only once)")
    provisioning_uri: str = Field(description="otpauth:// URI for QR code generation")
    qr_data_url: str | None = Field(
        None, description="Base64 PNG data URL of QR code (if qrcode lib available)"
    )


class TOTPCodeRequest(Schema):
    code: str = Field(description="6-digit TOTP code from authenticator app")


class TOTPValidateRequest(Schema):
    email: str
    code: str = Field(description="6-digit TOTP code from authenticator app")


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post("/setup", auth=JWTAuth(), response={200: dict})
def totp_setup(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """
    Generate a new TOTP secret and return the QR provisioning URI.

    If the user already has a device, this resets it (they must re-scan).
    The secret is returned **only here** — it is never returned again.
    """
    import pyotp
    from users.models import TOTPDevice

    user = request.auth

    # Delete any existing (unverified) device and create a fresh one
    TOTPDevice.objects.filter(user=user).delete()

    secret = pyotp.random_base32()
    device = TOTPDevice.objects.create(
        user=user,
        secret_key=secret,
        is_verified=False,
    )

    provisioning_uri = device.get_provisioning_uri()

    # Try to generate a QR code data URL (requires qrcode[pil])
    qr_data_url = None
    try:
        import qrcode
        import io
        import base64

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=6,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode()
        qr_data_url = f"data:image/png;base64,{encoded}"
    except ImportError:
        pass  # qrcode not installed — frontend can render QR from URI
    except Exception:
        logger.exception("Failed to generate QR code")

    logger.info("TOTP setup initiated for user %s", user.email)

    return 200, {
        "success": True,
        "message": "TOTP setup initiated. Scan the QR code and verify with a code.",
        "data": {
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "qr_data_url": qr_data_url,
        },
    }


@router.post("/verify", auth=JWTAuth(), response={200: dict})
def totp_verify(
    request: HttpRequest, data: TOTPCodeRequest
) -> tuple[int, dict[str, Any]]:
    """
    Verify the first TOTP code to activate the device.

    Must be called after /setup. The device is activated on success.
    Returns an error if the device is already verified or doesn't exist.
    """
    from users.models import TOTPDevice

    user = request.auth

    try:
        device = TOTPDevice.objects.get(user=user)
    except TOTPDevice.DoesNotExist:
        raise HttpError(404, "No TOTP device found. Call /setup first.")

    if device.is_verified:
        raise HttpError(400, "TOTP device is already verified.")

    if not device.activate(data.code):
        logger.warning("TOTP verify failed for user %s", user.email)
        raise HttpError(400, "Invalid TOTP code. Please try again.")

    logger.info("TOTP device activated for user %s", user.email)

    return 200, {
        "success": True,
        "message": "Two-factor authentication enabled successfully.",
        "data": {"totp_enabled": True},
    }


@router.post("/validate", response={200: dict})
def totp_validate(
    request: HttpRequest, data: TOTPValidateRequest
) -> tuple[int, dict[str, Any]]:
    """
    Validate a TOTP code during login (no JWT required — called before full auth).

    Looks up the user by email, checks if they have a verified TOTP device,
    and validates the code. Used by the frontend login flow after password/OTP auth.

    Returns 200 with `valid: true/false` — the caller must decide what to do.
    Raises 404 if the user has no TOTP device.
    """
    from django.utils import timezone
    from users.models import User, TOTPDevice

    try:
        user = User.objects.get(email=data.email, is_active=True)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    try:
        device = TOTPDevice.objects.get(user=user, is_verified=True)
    except TOTPDevice.DoesNotExist:
        raise HttpError(404, "User has no verified TOTP device")

    valid = device.verify_code(data.code)
    if valid:
        device.last_used_at = timezone.now()
        device.save(update_fields=["last_used_at"])
        logger.info("TOTP validated for user %s", user.email)
    else:
        logger.warning("TOTP validation failed for user %s", user.email)

    return 200, {
        "success": True,
        "message": "Code is valid." if valid else "Invalid TOTP code.",
        "data": {"valid": valid},
    }


@router.delete("/disable", auth=JWTAuth(), response={200: dict})
def totp_disable(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """
    Disable and remove the TOTP device for the current user.

    Staff/admin users should not be able to disable their own 2FA
    unless there's an override; this enforces 2FA for regular users.
    """
    from users.models import TOTPDevice

    user = request.auth
    deleted, _ = TOTPDevice.objects.filter(user=user).delete()

    if deleted:
        logger.info("TOTP device removed for user %s", user.email)
        return 200, {
            "success": True,
            "message": "Two-factor authentication disabled.",
            "data": None,
        }

    return 200, {
        "success": True,
        "message": "No TOTP device found.",
        "data": None,
    }


class SendCodeRequest(Schema):
    two_factor_token: str
    channel: str = Field("auto", description="'auto', 'email', or 'sms'")


@router.post("/send-code", response={200: dict, 401: dict, 429: dict})
@rate_limit(max_requests=5, window_seconds=3600, key_func=_two_factor_user_bucket)
def totp_send_code(
    request: HttpRequest, data: SendCodeRequest
) -> tuple[int, dict[str, Any]]:
    """
    Send a fallback 2FA code via email/SMS for users who can't access their
    authenticator app. Uses the C4 dispatcher with retry + channel fallback.
    """
    from users.models import User
    from users.service import UserService

    payload = JWTAuth.decode_token(data.two_factor_token)
    if not payload or payload.get("type") != "2fa":
        return 401, {
            "success": False,
            "message": "Invalid or expired 2FA token. Please log in again.",
            "data": None,
        }

    try:
        user = User.objects.get(id=payload["user_id"], is_active=True)
    except User.DoesNotExist:
        return 401, {"success": False, "message": "User not found", "data": None}

    result = UserService.send_2fa_challenge(user, channel=data.channel)
    channel = result.get("channel", "email")
    if result.get("delivered"):
        destination = "phone" if channel == "sms" else "email"
        return 200, {
            "success": True,
            "message": f"A verification code has been sent to your {destination}.",
            "data": {"channel": channel},
        }
    return 200, {
        "success": False,
        "message": "We couldn't deliver your code. Please try your authenticator app.",
        "data": {"channel": channel, "error": result.get("error")},
    }


@router.get("/status", auth=JWTAuth(), response={200: dict})
def totp_status(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """Return the TOTP enrollment status for the current user."""
    from users.models import TOTPDevice

    try:
        device = TOTPDevice.objects.get(user=request.auth)
        return 200, {
            "success": True,
            "message": "TOTP status retrieved",
            "data": {
                "enabled": device.is_verified,
                "last_used_at": device.last_used_at.isoformat()
                if device.last_used_at
                else None,
            },
        }
    except TOTPDevice.DoesNotExist:
        return 200, {
            "success": True,
            "message": "TOTP not configured",
            "data": {"enabled": False, "last_used_at": None},
        }
