"""
Custom exception classes and global exception handlers for the API.

Provides domain-specific exceptions (ValidationError, NotFoundError,
AccessDeniedError, AuthenticationError, RateLimitError) and registers
them with the NinjaAPI instance for consistent JSON error responses.
"""

from ninja import NinjaAPI
from ninja.errors import ValidationError as NinjaValidationError
from pydantic import ValidationError as PydanticValidationError


class ValidationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class AccessDeniedError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class RateLimitError(Exception):
    pass


def register_exception_handlers(api: NinjaAPI):
    @api.exception_handler(ValidationError)
    def custom_validation_handler(request, exc):
        return api.create_response(
            request,
            {"success": False, "message": str(exc), "code": "validation_error"},
            status=400,
        )

    @api.exception_handler(NotFoundError)
    def custom_not_found_handler(request, exc):
        return api.create_response(
            request,
            {"success": False, "message": str(exc), "code": "not_found"},
            status=404,
        )

    @api.exception_handler(AccessDeniedError)
    def custom_access_denied_handler(request, exc):
        return api.create_response(
            request,
            {"success": False, "message": str(exc), "code": "forbidden"},
            status=403,
        )

    @api.exception_handler(AuthenticationError)
    def custom_authentication_handler(request, exc):
        return api.create_response(
            request,
            {"success": False, "message": str(exc), "code": "unauthorized"},
            status=401,
        )

    @api.exception_handler(RateLimitError)
    def custom_rate_limit_handler(request, exc):
        return api.create_response(
            request,
            {
                "success": False,
                "message": "Too many requests. Please try again later.",
                "code": "rate_limited",
            },
            status=429,
        )

    @api.exception_handler(NinjaValidationError)
    def ninja_validation_handler(request, exc):
        return api.create_response(
            request,
            {"success": False, "message": "Invalid Data", "errors": exc.errors},
            status=422,
        )

    @api.exception_handler(PydanticValidationError)
    def pydantic_validation_handler(request, exc):
        return api.create_response(
            request,
            {"success": False, "message": "Invalid Data", "errors": exc.errors()},
            status=422,
        )
