import logging
import random
import secrets
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone as django_timezone
from common.exceptions import (
    ValidationError,
    AuthenticationError,
    NotFoundError,
    AccessDeniedError,
)
from emails.schemas import SendEmailInput
from emails.service import EmailService
from organizations.service import OrganizationService
from quotes.models import ReferralPartner
from s3.service import S3Service
from users.auth import JWTAuth
from users.models import (
    User,
    UserDocument,
    ImpersonationLog,
    EmailLoginCode,
    LoginEvent,
    TwoFactorDeliveryLog,
)
from users.schemas import RegisterRequest, UserDocumentResponse

logger = logging.getLogger(__name__)


class ResendError(Exception):
    """Raised when the Resend email provider fails after retries."""


class TwilioError(Exception):
    """Raised when the Twilio SMS provider fails after retries."""


def _send_email_2fa(user: "User", code: str) -> str | None:
    """Send a 2FA code via Resend. Returns provider message id or raises ResendError."""
    if not getattr(settings, "RESEND_API_KEY", None):
        logger.warning("RESEND_API_KEY not configured; cannot send email 2FA")
        raise ResendError("Resend not configured")

    html = render_to_string(
        "emails/login_otp.html",
        {
            "user_name": user.first_name or user.email,
            "code": code,
        },
    )
    try:
        email_input = SendEmailInput(
            to=[user.email],
            from_email=settings.HELLO_CORGI_EMAIL,
            subject="Your Corgi Sign-In Code",
            html=html,
        )
        result = EmailService.send(email_input)
        provider_id = None
        if isinstance(result, dict):
            provider_id = result.get("id")
        else:
            provider_id = getattr(result, "id", None)
        return str(provider_id) if provider_id else None
    except Exception as exc:
        raise ResendError(str(exc)) from exc


def _send_sms_2fa(user: "User", code: str) -> str | None:
    """Send a 2FA code via Twilio. Returns provider message id or raises TwilioError."""
    phone = (getattr(user, "phone_number", "") or "").strip()
    if not phone:
        raise TwilioError("User has no phone_number")

    sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
    from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)
    if not (sid and token and from_number):
        logger.warning("Twilio not fully configured; cannot send SMS 2FA")
        raise TwilioError("Twilio not configured")

    try:
        from twilio.rest import Client  # type: ignore
        from twilio.base.exceptions import TwilioRestException  # type: ignore
    except ImportError as exc:
        raise TwilioError("twilio package not installed") from exc

    try:
        client = Client(sid, token)
        msg = client.messages.create(
            to=phone,
            from_=from_number,
            body=f"Your Corgi sign-in code is {code}. It expires in 10 minutes.",
        )
        return getattr(msg, "sid", None)
    except TwilioRestException as exc:
        raise TwilioError(str(exc)) from exc
    except Exception as exc:
        raise TwilioError(str(exc)) from exc


def _dispatch_channel(
    user: "User", code: str, channel: str
) -> tuple[bool, str | None, str | None]:
    """Try once, retry once after 2s backoff. Returns (ok, provider_msg_id, error)."""
    import time

    sender = _send_email_2fa if channel == "email" else _send_sms_2fa
    last_error: str | None = None
    for attempt in (1, 2):
        try:
            provider_id = sender(user, code)
            return True, provider_id, None
        except (ResendError, TwilioError) as exc:
            last_error = str(exc)
            logger.warning(
                "2FA send attempt %d via %s failed for user=%s: %s",
                attempt,
                channel,
                user.email,
                exc,
            )
            # "not configured" is unrecoverable: retrying burns 2s for nothing.
            # Short-circuit so tests (and prod misconfigurations) fail fast.
            if "not configured" in last_error.lower():
                break
            if attempt == 1:
                TwoFactorDeliveryLog.objects.create(
                    user=user,
                    channel=channel,
                    status="retried",
                    error=last_error,
                )
                time.sleep(2)
    return False, None, last_error


def send_2fa_code(user: "User", code: str, channel_preference: str = "auto") -> dict:
    """
    Dispatch a 2FA code with retry + channel fallback (C4).

    Tries the primary channel (email default; SMS if preference='sms' and user has phone).
    On provider failure, retries once with 2s backoff; if still failing, falls back
    to the other channel. Every attempt is recorded in TwoFactorDeliveryLog.

    Returns a summary dict: {delivered, channel, provider_msg_id, error}.
    """
    has_phone = bool((getattr(user, "phone_number", "") or "").strip())
    if channel_preference == "sms" and has_phone:
        primary, secondary = "sms", "email"
    else:
        primary, secondary = "email", "sms" if has_phone else None

    ok, provider_id, error = _dispatch_channel(user, code, primary)
    if ok:
        TwoFactorDeliveryLog.objects.create(
            user=user,
            channel=primary,
            status="sent",
            provider_msg_id=provider_id or "",
        )
        return {
            "delivered": True,
            "channel": primary,
            "provider_msg_id": provider_id,
            "error": None,
        }

    TwoFactorDeliveryLog.objects.create(
        user=user,
        channel=primary,
        status="failed",
        error=error or "",
    )

    if not secondary:
        return {
            "delivered": False,
            "channel": primary,
            "provider_msg_id": None,
            "error": error,
        }

    ok2, provider_id2, error2 = _dispatch_channel(user, code, secondary)
    if ok2:
        TwoFactorDeliveryLog.objects.create(
            user=user,
            channel=secondary,
            status="fallback",
            provider_msg_id=provider_id2 or "",
        )
        return {
            "delivered": True,
            "channel": secondary,
            "provider_msg_id": provider_id2,
            "error": None,
        }

    TwoFactorDeliveryLog.objects.create(
        user=user,
        channel=secondary,
        status="failed",
        error=error2 or "",
    )
    return {
        "delivered": False,
        "channel": secondary,
        "provider_msg_id": None,
        "error": error2,
    }


def _get_client_ip(request) -> str | None:
    """Extract client IP from request, respecting X-Forwarded-For."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_user_agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")


class UserService:
    @staticmethod
    def record_login(
        email: str,
        method: str,
        success: bool,
        request=None,
        user: User | None = None,
        failure_reason: str = "",
    ) -> LoginEvent:
        """Record a login attempt (successful or failed)."""
        ip = _get_client_ip(request) if request else None
        ua = _get_user_agent(request) if request else ""
        return LoginEvent.objects.create(
            user=user,
            email=email,
            method=method,
            success=success,
            ip_address=ip,
            user_agent=ua,
            failure_reason=failure_reason,
        )

    @staticmethod
    def create_tokens(user: User, impersonator_id: int | None = None) -> dict:
        return {
            "access_token": JWTAuth.create_access_token(user.id, impersonator_id),
            "refresh_token": JWTAuth.create_refresh_token(user.id, impersonator_id),
            "token_type": "Bearer",
        }

    @staticmethod
    def _send_login_code(user: User, channel_preference: str = "auto") -> dict:
        EmailLoginCode.objects.filter(user=user, is_used=False).update(is_used=True)

        code = f"{random.randint(0, 999999):06d}"
        EmailLoginCode.objects.create(
            user=user,
            code=code,
            expires_at=django_timezone.now() + timedelta(minutes=10),
        )

        # In dev mode, print the code to console for easy testing
        if settings.DEBUG:
            print(f"\n{'=' * 50}")
            print(f"  OTP CODE for {user.email}: {code}")
            print(f"{'=' * 50}\n")

        result = send_2fa_code(user, code, channel_preference=channel_preference)
        if not result["delivered"] and settings.DEBUG:
            print("  (2FA delivery failed — use the code above)")
        return result

    @staticmethod
    @transaction.atomic
    def register(data: RegisterRequest) -> User:
        if User.objects.filter(email=data.email).exists():
            raise ValidationError("Email already registered")

        if data.invite_code:
            try:
                invite = OrganizationService.validate_invite(data.invite_code)
            except Exception as e:
                raise ValidationError(str(e))
        else:
            invite = None

        user = User.objects.create_user(
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            phone_number=data.phone_number,
            company_name=data.company_name,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])

        if invite:
            OrganizationService.join_organization(user, invite.code)
        else:
            OrganizationService.create_personal_org(user)

        referral_partner = None
        if data.referral_code:
            referral_partner = ReferralPartner.objects.filter(
                slug=data.referral_code, is_active=True
            ).first()

        try:
            recipients = [settings.CORGI_NOTIFICATION_EMAIL]
            if referral_partner and referral_partner.notification_emails:
                recipients.extend(referral_partner.notification_emails)

            email_input = SendEmailInput(
                to=recipients,
                from_email=settings.HELLO_CORGI_EMAIL,
                subject=f"New User Registration: {user.email}",
                html=f"""
                    <h2>New User Registered</h2>
                    <p><strong>Name:</strong> {user.first_name} {user.last_name}</p>
                    <p><strong>Email:</strong> {user.email}</p>
                    <p><strong>Phone:</strong> {user.phone_number}</p>
                    <p><strong>Company:</strong> {user.company_name}</p>
                """,
            )
            EmailService.send(email_input)
        except Exception:
            pass

        UserService._send_login_code(user)
        return user, UserService.create_tokens(user)

    @staticmethod
    def request_login_code(email: str, channel: str = "auto") -> dict:
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            raise NotFoundError("No account found with that email. Please sign up.")

        return UserService._send_login_code(user, channel_preference=channel)

    @staticmethod
    def send_2fa_challenge(user: User, channel: str = "auto") -> dict:
        """Public entry point used by the 2FA challenge flow (C4)."""
        return UserService._send_login_code(user, channel_preference=channel)

    @staticmethod
    def verify_login_code(email: str, code: str, request=None) -> tuple[User, dict]:
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            UserService.record_login(
                email, "otp", False, request, failure_reason="user_not_found"
            )
            raise AuthenticationError("Invalid or expired code")

        # Check account lockout
        if user.is_locked:
            UserService.record_login(
                email, "otp", False, request, user=user, failure_reason="locked"
            )
            raise AuthenticationError("Account temporarily locked. Try again later.")

        login_code = (
            EmailLoginCode.objects.filter(
                user=user,
                code=code,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not login_code:
            user.record_failed_login()
            UserService.record_login(
                email, "otp", False, request, user=user, failure_reason="invalid_code"
            )
            raise AuthenticationError("Invalid or expired code")

        login_code.attempts += 1
        login_code.save(update_fields=["attempts"])

        if not login_code.is_valid():
            user.record_failed_login()
            UserService.record_login(
                email, "otp", False, request, user=user, failure_reason="expired_code"
            )
            raise AuthenticationError("Invalid or expired code")

        login_code.is_used = True
        login_code.save(update_fields=["is_used"])

        user.reset_failed_logins()
        UserService.record_login(email, "otp", True, request, user=user)
        return user, UserService.create_tokens(user)

    @staticmethod
    def refresh_tokens(refresh_token: str) -> dict:
        payload = JWTAuth.decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise AuthenticationError("Invalid refresh token")

        try:
            user = User.objects.get(id=payload["user_id"], is_active=True)
        except User.DoesNotExist:
            raise AuthenticationError("User not found")

        impersonator_id = payload.get("impersonator_id")
        return UserService.create_tokens(user, impersonator_id)

    @staticmethod
    def get_user_documents(user: User) -> dict:
        org_id = OrganizationService.get_active_org_id(user)
        documents = UserDocument.objects.filter(organization_id=org_id)

        grouped = {
            "policies": [],
            "certificates": [],
            "endorsements": [],
            "receipts": [],
            "loss_runs": [],
        }

        category_map = {
            "policy": "policies",
            "certificate": "certificates",
            "endorsement": "endorsements",
            "receipt": "receipts",
            "loss_run": "loss_runs",
        }

        for doc in documents:
            key = category_map.get(doc.category, "policies")
            grouped[key].append(UserDocumentResponse.from_document(doc))

        return grouped

    @staticmethod
    def get_document_download_url(user: User, document_id: int) -> dict:
        org_id = OrganizationService.get_active_org_id(user)
        try:
            document = UserDocument.objects.get(id=document_id, organization_id=org_id)
        except UserDocument.DoesNotExist:
            raise NotFoundError("Document not found")

        download_url = S3Service.generate_presigned_url(document.s3_key, expiration=300)

        if not download_url:
            raise NotFoundError("Failed to generate download URL")

        return {"download_url": download_url, "filename": document.original_filename}

    @staticmethod
    def start_impersonation(
        admin_user: User,
        target_user_id: int,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> tuple[User, dict, ImpersonationLog]:
        if not admin_user.is_staff:
            raise AccessDeniedError("Only staff members can impersonate users")

        try:
            target_user = User.objects.get(id=target_user_id, is_active=True)
        except User.DoesNotExist:
            raise NotFoundError("User not found")

        if target_user.is_staff or target_user.is_superuser:
            raise AccessDeniedError("Cannot impersonate staff or admin users")

        log = ImpersonationLog.objects.create(
            admin_user=admin_user,
            impersonated_user=target_user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        tokens = UserService.create_tokens(target_user, impersonator_id=admin_user.id)

        return target_user, tokens, log

    @staticmethod
    def stop_impersonation(
        current_user: User, impersonator_id: int
    ) -> tuple[User, dict]:
        try:
            admin_user = User.objects.get(
                id=impersonator_id, is_active=True, is_staff=True
            )
        except User.DoesNotExist:
            raise AuthenticationError("Original admin user not found")

        log = (
            ImpersonationLog.objects.filter(
                admin_user_id=impersonator_id,
                impersonated_user=current_user,
                ended_at__isnull=True,
            )
            .order_by("-started_at")
            .first()
        )

        if log:
            log.ended_at = django_timezone.now()
            log.save()

        tokens = UserService.create_tokens(admin_user)

        return admin_user, tokens

    # ── SSO Session Management ──────────────────────────────────────────

    @staticmethod
    def _get_sso_db():
        """Get a connection to the shared SSO PostgreSQL database."""
        import psycopg2

        url = settings.SSO_DATABASE_URL
        if not url:
            raise ValidationError("SSO database not configured")
        sslmode = (
            "require" if any(h in url for h in ("xata.tech", "neon.tech")) else "prefer"
        )
        return psycopg2.connect(url, sslmode=sslmode)

    @staticmethod
    def _validate_redirect_uri(redirect_uri: str) -> None:
        """Validate the redirect URI against the allowlist."""
        allowed = settings.SSO_ALLOWED_REDIRECTS
        if not any(redirect_uri.startswith(prefix) for prefix in allowed):
            raise ValidationError(f"Redirect URI not allowed: {redirect_uri}")

    @staticmethod
    def create_sso_session(user: User, redirect_uri: str) -> str:
        """Create a session in the shared SSO database and return the token."""
        UserService._validate_redirect_uri(redirect_uri)

        token = secrets.token_hex(32)
        user_name = user.get_full_name() or user.email
        user_id = user.email  # Use email as the shared user_id

        conn = UserService._get_sso_db()
        try:
            cur = conn.cursor()
            # Ensure the user exists in the shared users table
            cur.execute(
                "INSERT INTO users (user_id, name) VALUES (%s, %s) "
                "ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name",
                (user_id, user_name),
            )
            # Create the session
            cur.execute(
                "INSERT INTO sessions (token, user_id, user_name) VALUES (%s, %s, %s)",
                (token, user_id, user_name),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("Failed to create SSO session: %s", e)
            raise ValidationError("Failed to create SSO session")
        finally:
            conn.close()

        return token

    @staticmethod
    def exchange_sso_token(sso_token: str) -> tuple[User, dict]:
        """Exchange an SSO token for JWT tokens. Looks up the session, finds or creates the Django user."""
        conn = UserService._get_sso_db()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id, user_name FROM sessions WHERE token = %s",
                (sso_token,),
            )
            row = cur.fetchone()
        except Exception as e:
            logger.error("Failed to look up SSO token: %s", e)
            raise AuthenticationError("Failed to validate SSO token")
        finally:
            conn.close()

        if not row:
            raise AuthenticationError("Invalid or expired SSO token")

        user_id_email, user_name = row

        # Look up the Django user by email
        try:
            user = User.objects.get(email=user_id_email, is_active=True)
        except User.DoesNotExist:
            raise AuthenticationError("No account found for this SSO session")

        tokens = UserService.create_tokens(user)
        return user, tokens
