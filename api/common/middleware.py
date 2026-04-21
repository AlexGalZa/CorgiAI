"""
Custom middleware for performance monitoring, security, and audit logging.
"""

import logging
import time
import uuid

from django.conf import settings
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("corgi.middleware")


class CorrelationIdMiddleware:
    """
    Assigns a correlation ID to every request for distributed tracing.

    Reads X-Correlation-ID from the incoming request headers; generates a
    new UUID if the header is absent.  The ID is attached to the request
    object and echoed back on the response so callers can correlate logs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.correlation_id = correlation_id

        response = self.get_response(request)
        response["X-Correlation-ID"] = correlation_id
        return response


class RequestTimingMiddleware:
    """
    Logs request duration for performance monitoring.

    Adds X-Request-ID and X-Response-Time headers to every response.
    Logs slow requests (>1s) at WARNING level.
    """

    SLOW_REQUEST_THRESHOLD = 1.0  # seconds

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.META["REQUEST_ID"] = request_id

        start = time.monotonic()
        response = self.get_response(request)
        duration = time.monotonic() - start

        response["X-Request-ID"] = request_id
        response["X-Response-Time"] = f"{duration:.3f}s"

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "duration_ms": round(duration * 1000, 1),
            "user": getattr(request, "user", None)
            and str(getattr(request.user, "id", "anon")),
        }

        if duration > self.SLOW_REQUEST_THRESHOLD:
            logger.warning(
                "Slow request: %(method)s %(path)s took %(duration_ms)sms", log_data
            )
        else:
            logger.info("%(method)s %(path)s %(status)s %(duration_ms)sms", log_data)

        return response


class SecurityHeadersMiddleware:
    """
    Comprehensive OWASP-recommended security headers (V3 #59).

    Sets the following headers on every response:
    - Content-Security-Policy       (restrictive default; relaxed in DEBUG)
    - Strict-Transport-Security     (production only)
    - X-Frame-Options               DENY
    - X-Content-Type-Options        nosniff
    - Referrer-Policy               strict-origin-when-cross-origin
    - Permissions-Policy            deny camera/mic/geolocation
    - Cross-Origin-Opener-Policy    same-origin (production)
    """

    # Default CSP for production. Tight, but allows Stripe, S3, Resend CDN.
    CSP_PRODUCTION = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://js.stripe.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.stripe.com https://r.resend.com; "
        "frame-src https://js.stripe.com https://hooks.stripe.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "upgrade-insecure-requests;"
    )

    # Django admin CSP. Unfold ships AlpineJS which compiles templates via
    # `new AsyncFunction(...)`, so the script-src needs 'unsafe-eval'. Kept
    # scoped to /admin/* via the path prefix check below so the rest of the
    # surface stays strict.
    CSP_ADMIN = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "upgrade-insecure-requests;"
    )

    # Relaxed CSP for development. Allows hot reload, devtools.
    CSP_DEVELOPMENT = (
        "default-src 'self' 'unsafe-inline' 'unsafe-eval' *; frame-ancestors 'none';"
    )

    HSTS_VALUE = "max-age=31536000; includeSubDomains; preload"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # ── Content-Security-Policy ───────────────────────────────────────
        if settings.DEBUG:
            csp = self.CSP_DEVELOPMENT
        elif request.path.startswith("/admin/"):
            csp = self.CSP_ADMIN
        else:
            csp = self.CSP_PRODUCTION
        response["Content-Security-Policy"] = csp

        # ── Strict-Transport-Security (HTTPS only) ────────────────────────
        if not settings.DEBUG:
            response.setdefault("Strict-Transport-Security", self.HSTS_VALUE)

        # ── X-Frame-Options ───────────────────────────────────────────────
        response["X-Frame-Options"] = "DENY"

        # ── X-Content-Type-Options ────────────────────────────────────────
        response["X-Content-Type-Options"] = "nosniff"

        # ── Referrer-Policy ───────────────────────────────────────────────
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ── Permissions-Policy ────────────────────────────────────────────
        response["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # ── Cross-Origin-Opener-Policy ────────────────────────────────────
        if not settings.DEBUG:
            response.setdefault("Cross-Origin-Opener-Policy", "same-origin")

        return response


class SessionActivityMiddleware:
    """
    Tracks active sessions for authenticated requests (V3 #56).

    On each authenticated request:
    - Extracts the session_key from the JWT token (jti claim).
    - Creates an ActiveSession record on first encounter.
    - Updates last_activity timestamp on subsequent requests.
    - Auto-expires sessions inactive for SESSION_INACTIVITY_HOURS.

    The session_key is the JWT `jti` claim when present; otherwise a
    hash of the Authorization header token is used.
    """

    # Skip paths that don't carry meaningful session context
    SKIP_PREFIXES = ("/health/", "/static/", "/admin/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        user = getattr(request, "auth", None)
        if not user or not getattr(user, "is_authenticated", False):
            return response

        if any(request.path.startswith(p) for p in self.SKIP_PREFIXES):
            return response

        try:
            self._track_session(request, user)
        except Exception:
            logger.exception("Failed to track session activity")

        return response

    def _track_session(self, request: HttpRequest, user) -> None:
        from datetime import timedelta
        from django.utils import timezone
        from users.models import ActiveSession

        session_key = self._extract_session_key(request)
        if not session_key:
            return

        ip = self._get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")[:500]

        try:
            session = ActiveSession.objects.get(session_key=session_key)
            if not session.is_active:
                return  # revoked — don't re-activate
            # Check inactivity expiry
            if session.is_expired:
                session.revoke()
                return
            session.touch()
        except ActiveSession.DoesNotExist:
            ActiveSession.objects.create(
                user=user,
                session_key=session_key,
                ip_address=ip,
                user_agent=ua,
            )

        # Background: expire old inactive sessions (once every ~100 requests via hash)
        import hashlib

        if int(hashlib.md5(session_key.encode()).hexdigest(), 16) % 100 == 0:
            cutoff = timezone.now() - timedelta(
                hours=ActiveSession.SESSION_INACTIVITY_HOURS
            )
            ActiveSession.objects.filter(
                is_active=True,
                last_activity__lt=cutoff,
            ).update(is_active=False)

    @staticmethod
    def _extract_session_key(request: HttpRequest) -> str | None:
        """Extract a stable session key from the request."""
        import hashlib
        import base64

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]

        # Try to extract jti from JWT payload (second segment)
        try:
            parts = token.split(".")
            if len(parts) == 3:
                padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
                import json

                payload = json.loads(base64.urlsafe_b64decode(padded))
                jti = payload.get("jti")
                if jti:
                    return str(jti)
        except Exception:
            pass

        # Fallback: sha256 of the token (truncated to 64 chars)
        return hashlib.sha256(token.encode()).hexdigest()[:64]

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class AuditMiddleware:
    """
    SOC 2 audit middleware: logs write operations to AuditLogEntry and
    sensitive read/export operations to DataAccessLog.

    Write operations (POST/PUT/PATCH/DELETE) on API paths → AuditLogEntry.
    GET access to sensitive model endpoints → DataAccessLog (action=view).
    """

    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    # Paths to skip (health checks, static, token refresh, etc.)
    SKIP_PREFIXES = ("/health/", "/static/", "/admin/")
    SKIP_EXACT = {"/api/v1/users/refresh", "/api/v1/users/request-login-code"}

    # URL substrings that map to (model_name, action) for read logging
    READ_AUDIT_MAP = [
        ("/api/v1/quotes", "Quote", "view"),
        ("/api/v1/policies", "Policy", "view"),
        ("/api/v1/claims", "Claim", "view"),
        ("/api/v1/users/documents", "UserDocument", "view"),
        ("/api/external/v1/quotes", "Quote", "export"),
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # Skip non-API paths and certain exact paths
        if any(request.path.startswith(p) for p in self.SKIP_PREFIXES):
            return response
        if request.path.rstrip("/") in self.SKIP_EXACT:
            return response

        user = getattr(request, "auth", None) or getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return response

        try:
            if request.method in self.WRITE_METHODS:
                self._log_write(request, response, user)
            elif request.method == "GET" and response.status_code == 200:
                self._log_read(request, user)
        except Exception:
            logger.exception(
                "Failed to create audit log entry for %s %s",
                request.method,
                request.path,
            )

        return response

    def _log_write(self, request: HttpRequest, response: HttpResponse, user) -> None:
        from common.models import AuditLogEntry

        # Map HTTP method to audit action
        method_action_map = {
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
        }
        action = method_action_map.get(request.method, "update")

        # Extract model name and object id from path heuristically
        model_name, object_id = self._extract_model_info(request.path)

        AuditLogEntry.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_id=object_id,
            changes={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "request_id": request.META.get("REQUEST_ID", ""),
                "organization_id": request.headers.get("X-Organization-ID", ""),
            },
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )

    def _log_read(self, request: HttpRequest, user) -> None:
        from common.models import DataAccessLog

        for path_prefix, model_name, action in self.READ_AUDIT_MAP:
            if request.path.startswith(path_prefix):
                _, object_id = self._extract_model_info(request.path)
                DataAccessLog.objects.create(
                    user=user,
                    model_name=model_name,
                    object_id=object_id,
                    action=action,
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                    extra={
                        "path": request.path,
                        "query": request.META.get("QUERY_STRING", ""),
                        "request_id": request.META.get("REQUEST_ID", ""),
                    },
                )
                break

    @staticmethod
    def _extract_model_info(path: str):
        """
        Heuristically extract model_name and object_id from a URL path.

        e.g. /api/v1/quotes/42  → ('Quote', '42')
             /api/v1/policies/  → ('Policy', None)
        """
        import re

        segment_to_model = {
            "quotes": "Quote",
            "policies": "Policy",
            "claims": "Claim",
            "users": "User",
            "certificates": "Certificate",
            "organizations": "Organization",
            "documents": "UserDocument",
        }
        parts = [p for p in path.split("/") if p]
        model_name = "Unknown"
        object_id = None
        for i, part in enumerate(parts):
            if part in segment_to_model:
                model_name = segment_to_model[part]
                if i + 1 < len(parts):
                    candidate = parts[i + 1]
                    if re.match(r"^\d+$", candidate) or re.match(
                        r"^[A-Za-z0-9_-]{4,}$", candidate
                    ):
                        object_id = candidate
                break
        return model_name, object_id

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
