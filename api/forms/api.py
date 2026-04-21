"""
Public Form Builder API endpoints.

Provides read-only endpoints for the portal frontend to fetch active
form definitions by coverage type and validate submissions.
"""

from typing import Any

from django.core.cache import cache as django_cache
from django.http import HttpRequest
from ninja import Router, Schema
from pydantic import Field

from forms.service import FormService

router = Router(tags=["Forms"])


# ── Schemas ──────────────────────────────────────────────────────────


class FormFieldOutput(Schema):
    """Single field in the form definition."""

    key: str
    label: str
    field_type: str
    required: bool = False
    placeholder: str = ""
    help_text: str = ""
    default_value: Any = None
    options: list[dict] | None = None
    validation: dict | None = None
    width: str = "full"
    group: str = ""
    order: int = 0
    conditions: list[dict] | None = None


class PublicFormOutput(Schema):
    """Public form definition response."""

    id: int
    name: str
    slug: str
    version: int
    coverage_type: str | None = None
    fields: list[dict] = Field(default_factory=list)
    conditional_logic: dict | None = None


class ValidateInput(Schema):
    """Form validation request."""

    data: dict = Field(..., description="Form field values to validate")


class ValidateOutput(Schema):
    """Form validation response."""

    is_valid: bool
    errors: list[str] = Field(default_factory=list)


class VisibleFieldsInput(Schema):
    """Request to compute visible fields."""

    data: dict = Field(
        ..., description="Current form data for conditional logic evaluation"
    )


# ── Endpoints ────────────────────────────────────────────────────────


@router.get(
    "/{coverage_type}",
    response={200: dict, 404: dict},
    summary="Get active form for a coverage type",
)
def get_form_by_coverage(
    request: HttpRequest, coverage_type: str
) -> tuple[int, dict[str, Any]]:
    """Fetch the active form definition for a coverage type.

    This is the main endpoint the portal frontend uses to render
    coverage-specific questionnaires dynamically.

    Args:
        coverage_type: Coverage slug (e.g. ``cyber-liability``).

    Returns:
        The active form definition or 404.
    """
    cache_key = f"form_definition_{coverage_type}"
    cached = django_cache.get(cache_key)
    if cached:
        return cached

    form_def = FormService.get_active_form(coverage_type)
    if not form_def:
        return 404, {
            "success": False,
            "message": f"No active form found for coverage type: {coverage_type}",
            "data": None,
        }

    result = (
        200,
        {
            "success": True,
            "message": "Form definition retrieved",
            "data": {
                "id": form_def.id,
                "name": form_def.name,
                "slug": form_def.slug,
                "version": form_def.version,
                "coverage_type": form_def.coverage_type,
                "fields": form_def.fields,
                "conditional_logic": form_def.conditional_logic,
            },
        },
    )
    django_cache.set(cache_key, result, timeout=300)
    return result


@router.post(
    "/{coverage_type}/validate",
    response={200: dict, 404: dict},
    summary="Validate a form submission",
)
def validate_form_submission(
    request: HttpRequest, coverage_type: str, payload: ValidateInput
) -> tuple[int, dict[str, Any]]:
    """Validate form data against the active form definition.

    Applies conditional logic to determine visible fields, then
    validates only those fields against their requirements.

    Args:
        coverage_type: Coverage slug.
        payload: Form data to validate.

    Returns:
        Validation result with is_valid flag and any errors.
    """
    form_def = FormService.get_active_form(coverage_type)
    if not form_def:
        return 404, {
            "success": False,
            "message": f"No active form found for coverage type: {coverage_type}",
            "data": None,
        }

    is_valid, errors = FormService.validate_submission(form_def, payload.data)
    return 200, {
        "success": True,
        "message": "Validation complete",
        "data": {
            "is_valid": is_valid,
            "errors": errors,
        },
    }


@router.post(
    "/{coverage_type}/visible-fields",
    response={200: dict, 404: dict},
    summary="Get visible fields based on current form data",
)
def get_visible_fields(
    request: HttpRequest, coverage_type: str, payload: VisibleFieldsInput
) -> tuple[int, dict[str, Any]]:
    """Compute which fields are visible given current form state.

    Uses the conditional logic engine to evaluate show/hide rules
    against the provided form data.

    Args:
        coverage_type: Coverage slug.
        payload: Current form data.

    Returns:
        List of visible field definitions.
    """
    form_def = FormService.get_active_form(coverage_type)
    if not form_def:
        return 404, {
            "success": False,
            "message": f"No active form found for coverage type: {coverage_type}",
            "data": None,
        }

    visible = FormService.get_visible_fields(form_def, payload.data)
    return 200, {
        "success": True,
        "message": "Visible fields computed",
        "data": {"fields": visible},
    }
