"""
Submission-time validators for coverage form answers.

This module enforces the LATEST active form-version's required fields at
submit time. When a questionnaire schema adds new required fields, older
in-flight quotes were started against a prior version of the schema and
therefore have stale answer payloads. Rather than migrate historic data,
we re-validate on submit: if the latest active schema declares a field as
required and it is missing (or blank) from the payload, the submission is
rejected with a 400 and the list of missing field keys.

Currently scoped to the Custom Crime coverage (H6). Other coverages fall
through this validator unchanged.
"""

from __future__ import annotations

from typing import Any

from forms.models import FormDefinition
from forms.logic import evaluate_conditions


# Coverages whose answer payloads must be re-validated against the
# latest active schema version at submit time.
COVERAGES_REQUIRING_LATEST_SCHEMA: set[str] = {
    "custom-crime",
}


def _is_blank(value: Any) -> bool:
    """Return True if a value is missing/blank for required-field purposes."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict, tuple, set)) and len(value) == 0:
        return True
    return False


def _latest_form(coverage_type: str) -> FormDefinition | None:
    """Return the highest-version active form definition for a coverage type."""
    return (
        FormDefinition.objects.filter(coverage_type=coverage_type, is_active=True)
        .order_by("-version")
        .first()
    )


def _visible_field_keys(form_def: FormDefinition, data: dict) -> set[str]:
    """Evaluate conditional logic and return keys of fields that are visible."""
    fields = form_def.fields or []
    rules = form_def.conditional_logic or {}
    if isinstance(rules, dict):
        rule_list = rules.get("rules", [])
    elif isinstance(rules, list):
        rule_list = rules
    else:
        rule_list = []

    visibility = evaluate_conditions(rule_list, data) if rule_list else {}
    visible_keys: set[str] = set()
    for f in fields:
        key = f.get("key", "")
        if not key:
            continue
        # Fields not mentioned by any rule are visible by default.
        if key not in visibility or visibility[key]:
            visible_keys.add(key)
    return visible_keys


def missing_required_fields(coverage_type: str, data: dict | None) -> list[str]:
    """Return the list of required field keys that are missing/blank.

    Compares the provided answer payload against the LATEST active
    ``FormDefinition`` for the given coverage type. Fields hidden by
    conditional logic based on the submitted data are skipped.

    Args:
        coverage_type: Coverage slug (e.g. ``custom-crime``).
        data: The answer payload for that coverage (may be ``None`` or ``{}``).

    Returns:
        List of missing field keys. Empty list means the payload satisfies
        every required field on the latest schema version.
    """
    form_def = _latest_form(coverage_type)
    if form_def is None:
        # No schema on file — nothing to enforce.
        return []

    payload = data or {}
    visible = _visible_field_keys(form_def, payload)
    missing: list[str] = []

    for field_dict in form_def.fields or []:
        key = field_dict.get("key", "")
        if not key or key not in visible:
            continue
        if not field_dict.get("required", False):
            continue
        if _is_blank(payload.get(key)):
            missing.append(key)

    return missing


def validate_coverage_payloads(
    coverage_data: dict[str, dict] | None,
) -> dict[str, list[str]]:
    """Validate every coverage payload that requires latest-schema enforcement.

    Args:
        coverage_data: Mapping ``{coverage_slug: answer_payload_dict}``.
            Typically the subset of the quote form data keyed by coverage.

    Returns:
        Mapping ``{coverage_slug: [missing_field_key, ...]}`` — only
        coverages with at least one missing required field are included.
        Empty dict means the submission passes.
    """
    result: dict[str, list[str]] = {}
    if not coverage_data:
        return result

    for coverage, payload in coverage_data.items():
        if coverage not in COVERAGES_REQUIRING_LATEST_SCHEMA:
            continue
        missing = missing_required_fields(coverage, payload or {})
        if missing:
            result[coverage] = missing
    return result


def build_validation_error_response(errors: dict[str, list[str]]) -> dict[str, Any]:
    """Build a 400 JSON body for a schema-drift validation failure."""
    flat_messages: list[str] = []
    for coverage, fields in errors.items():
        for f in fields:
            flat_messages.append(f"{coverage}: {f} is required")

    return {
        "success": False,
        "message": (
            "Form schema has been updated — the following required fields are missing from your submission."
        ),
        "data": {
            "errors": errors,
            "messages": flat_messages,
        },
    }


def extract_coverage_payloads_from_form_data(form_data: dict) -> dict[str, dict]:
    """Extract ``{coverage_slug: payload}`` from the inbound create_quote form data.

    The quote submission payload stores each coverage's answers under a
    snake_case form key (see ``quotes.constants.COVERAGE_TO_FORM_KEY``).
    We pluck only the coverages that are flagged for latest-schema
    enforcement to keep this validator cheap.
    """
    # Local import to avoid circulars at module import time.
    from quotes.constants import COVERAGE_TO_FORM_KEY

    selected = form_data.get("coverages") or []
    out: dict[str, dict] = {}
    for coverage in selected:
        if coverage not in COVERAGES_REQUIRING_LATEST_SCHEMA:
            continue
        form_key = COVERAGE_TO_FORM_KEY.get(coverage)
        if not form_key:
            continue
        payload = form_data.get(form_key)
        if payload is None:
            payload = {}
        out[coverage] = payload
    return out
