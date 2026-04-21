"""
Form rendering and validation service.

Provides the business logic layer between the API endpoints and the
``FormDefinition`` model, including field visibility, validation, and
mapping form answers to rating engine inputs.
"""

from __future__ import annotations

import re
from typing import Any

from forms.constants import (
    NON_INPUT_TYPES,
)
from forms.logic import evaluate_conditions
from forms.models import FormDefinition


class FormService:
    """Stateless service for form definition operations."""

    # ── Retrieval ────────────────────────────────────────────────────

    @staticmethod
    def get_active_form(coverage_type: str) -> FormDefinition | None:
        """Get the active form definition for a coverage type.

        Returns the highest-version active form for the given coverage slug,
        or None if no active form exists.
        """
        return (
            FormDefinition.objects.filter(coverage_type=coverage_type, is_active=True)
            .order_by("-version")
            .first()
        )

    @staticmethod
    def get_form_by_id(form_id: int) -> FormDefinition | None:
        """Get a form definition by primary key."""
        try:
            return FormDefinition.objects.get(pk=form_id)
        except FormDefinition.DoesNotExist:
            return None

    @staticmethod
    def list_forms() -> list[FormDefinition]:
        """List all form definitions ordered by name."""
        return list(FormDefinition.objects.all().order_by("name", "-version"))

    # ── Visibility ───────────────────────────────────────────────────

    @staticmethod
    def get_visible_fields(form_def: FormDefinition, data: dict) -> list[dict]:
        """Apply conditional logic to determine which fields are visible.

        Returns the list of field dicts that should be displayed given
        the current form data.
        """
        fields = form_def.fields or []
        rules = form_def.conditional_logic or {}

        # conditional_logic can be a list of rules or a dict with a "rules" key
        if isinstance(rules, dict):
            rule_list = rules.get("rules", [])
        elif isinstance(rules, list):
            rule_list = rules
        else:
            rule_list = []

        if not rule_list:
            return fields

        visibility = evaluate_conditions(rule_list, data)

        visible_fields = []
        for f in fields:
            key = f.get("key", "")
            # If a field has no rule, it's visible by default
            if key not in visibility or visibility[key]:
                visible_fields.append(f)

        return visible_fields

    # ── Validation ───────────────────────────────────────────────────

    @staticmethod
    def validate_submission(
        form_def: FormDefinition, data: dict
    ) -> tuple[bool, list[str]]:
        """Validate form data against the form definition.

        Only validates visible fields (respects conditional logic).
        Returns (is_valid, list_of_error_messages).
        """
        errors: list[str] = []
        visible = FormService.get_visible_fields(form_def, data)
        {f.get("key") for f in visible}

        for field_dict in visible:
            key = field_dict.get("key", "")
            field_type = field_dict.get("field_type", "text")
            required = field_dict.get("required", False)
            validation = field_dict.get("validation") or {}
            label = field_dict.get("label", key)

            # Skip non-input types
            if field_type in NON_INPUT_TYPES:
                continue

            value = data.get(key)

            # Required check
            if required:
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    errors.append(f"{label} is required")
                    continue
                if isinstance(value, (list, dict)) and len(value) == 0:
                    errors.append(f"{label} is required")
                    continue

            # Skip further validation if value is empty and not required
            if value is None or (isinstance(value, str) and value.strip() == ""):
                continue

            # Type-specific validation
            if field_type in ("number", "currency", "percentage"):
                try:
                    num_val = float(value)
                except (TypeError, ValueError):
                    errors.append(f"{label} must be a number")
                    continue

                if "min" in validation and num_val < validation["min"]:
                    errors.append(f"{label} must be at least {validation['min']}")
                if "max" in validation and num_val > validation["max"]:
                    errors.append(f"{label} must be at most {validation['max']}")

            if field_type == "text" or field_type == "textarea":
                str_val = str(value)
                if (
                    "min_length" in validation
                    and len(str_val) < validation["min_length"]
                ):
                    errors.append(
                        f"{label} must be at least {validation['min_length']} characters"
                    )
                if (
                    "max_length" in validation
                    and len(str_val) > validation["max_length"]
                ):
                    errors.append(
                        f"{label} must be at most {validation['max_length']} characters"
                    )
                if "pattern" in validation:
                    if not re.match(validation["pattern"], str_val):
                        errors.append(f"{label} does not match the required format")

            if field_type == "email":
                if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(value)):
                    errors.append(f"{label} must be a valid email address")

            if field_type == "ein":
                cleaned = str(value).replace("-", "").replace(" ", "")
                if not re.match(r"^\d{9}$", cleaned):
                    errors.append(f"{label} must be a valid EIN (XX-XXXXXXX)")

            if field_type == "phone":
                cleaned = re.sub(r"[\s\-\(\)\+]", "", str(value))
                if not re.match(r"^\d{10,15}$", cleaned):
                    errors.append(f"{label} must be a valid phone number")

            if field_type in ("select", "radio"):
                options = field_dict.get("options") or []
                valid_values = {o.get("value") for o in options}
                if value not in valid_values:
                    errors.append(f"{label} has an invalid selection")

            if field_type in ("multi_select", "checkbox_group"):
                if not isinstance(value, list):
                    errors.append(f"{label} must be a list")
                else:
                    options = field_dict.get("options") or []
                    valid_values = {o.get("value") for o in options}
                    for v in value:
                        if v not in valid_values:
                            errors.append(f"{label} contains invalid option: {v}")

        return (len(errors) == 0, errors)

    # ── Rating Mapping ───────────────────────────────────────────────

    @staticmethod
    def extract_rating_inputs(form_def: FormDefinition, data: dict) -> dict:
        """Extract rating engine inputs from form data using field mappings.

        Uses ``form_def.rating_field_mappings`` to map form field keys to
        the keys expected by the rating engine's questionnaire models.

        Returns:
            Dict of rating engine input keys → values.
        """
        mappings = form_def.rating_field_mappings or {}
        result: dict[str, Any] = {}

        for form_key, rating_key in mappings.items():
            if form_key in data:
                result[rating_key] = data[form_key]

        return result

    # ── CRUD helpers ─────────────────────────────────────────────────

    @staticmethod
    def create_form(data: dict) -> FormDefinition:
        """Create a new FormDefinition from validated data."""
        # Deactivate other versions of the same coverage type if setting active
        if data.get("is_active") and data.get("coverage_type"):
            FormDefinition.objects.filter(
                coverage_type=data["coverage_type"],
                is_active=True,
            ).update(is_active=False)

        return FormDefinition.objects.create(**data)

    @staticmethod
    def update_form(form_id: int, data: dict) -> FormDefinition | None:
        """Update an existing FormDefinition."""
        form_def = FormService.get_form_by_id(form_id)
        if not form_def:
            return None

        # Deactivate other versions if setting active
        if data.get("is_active") and data.get("coverage_type"):
            FormDefinition.objects.filter(
                coverage_type=data["coverage_type"],
                is_active=True,
            ).exclude(pk=form_id).update(is_active=False)

        for attr, value in data.items():
            setattr(form_def, attr, value)
        form_def.save()
        return form_def

    @staticmethod
    def duplicate_form(form_id: int) -> FormDefinition | None:
        """Duplicate a form definition with incremented version.

        The new copy is created inactive to avoid conflicts.
        """
        original = FormService.get_form_by_id(form_id)
        if not original:
            return None

        # Find the highest version for this slug
        max_version = (
            FormDefinition.objects.filter(slug=original.slug)
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
        ) or original.version

        return FormDefinition.objects.create(
            name=original.name,
            slug=original.slug,
            version=max_version + 1,
            description=original.description,
            fields=original.fields,
            conditional_logic=original.conditional_logic,
            rating_field_mappings=original.rating_field_mappings,
            coverage_type=original.coverage_type,
            is_active=False,  # New version starts inactive
        )

    @staticmethod
    def delete_form(form_id: int) -> bool:
        """Soft-delete a form by deactivating it."""
        form_def = FormService.get_form_by_id(form_id)
        if not form_def:
            return False
        form_def.is_active = False
        form_def.save(update_fields=["is_active"])
        return True
