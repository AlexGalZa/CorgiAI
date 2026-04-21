"""
API Version Negotiation Middleware (V3 #85)

Responsibilities:
1. Read `API-Version` request header and attach to request for downstream use.
2. Add `API-Version` response header so clients know which version served the request.
3. Add `Sunset` header to v1 API responses to communicate the v1 deprecation timeline.
4. Add `Deprecation` header (RFC 8594) to v1 responses.

Sunset / Deprecation schedule:
    - v1 deprecated:  2027-01-01
    - v1 sunset:      2027-07-01
"""

import logging

logger = logging.getLogger("corgi.api.version")

# V1 external API path prefix
_V1_EXTERNAL_PREFIX = "/api/external/v1/"

# RFC 7231 HTTP date format
_V1_SUNSET_DATE = "Thu, 01 Jul 2027 00:00:00 GMT"
_V1_DEPRECATION_DATE = "Fri, 01 Jan 2027 00:00:00 GMT"

_LINK_MIGRATION_DOC = (
    '<https://docs.corgiinsurance.com/api/migration-v2>; rel="successor-version"'
)


class ApiVersionMiddleware:
    """
    Django middleware that:
    - Detects requested API version from `API-Version` header
    - Tags v1 external API responses with Sunset + Deprecation headers
    - Attaches `request.api_version` for downstream use
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Determine requested version
        requested_version = request.headers.get("API-Version", "").strip()
        request.api_version = requested_version or self._infer_version_from_path(
            request.path
        )

        response = self.get_response(request)

        # Tag all API responses with the served version
        if request.path.startswith("/api/"):
            response["API-Version"] = request.api_version or "1"

        # Add Sunset header to v1 external API responses
        if request.path.startswith(_V1_EXTERNAL_PREFIX):
            response["Sunset"] = _V1_SUNSET_DATE
            response["Deprecation"] = _V1_DEPRECATION_DATE
            response["Link"] = _LINK_MIGRATION_DOC

        return response

    @staticmethod
    def _infer_version_from_path(path: str) -> str:
        """Infer the API version from the URL path segment (v1, v2, etc.)."""
        if "/v1/" in path:
            return "1"
        if "/v2/" in path:
            return "2"
        return "1"  # default
