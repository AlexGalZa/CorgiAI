"""
Form Builder constants and field schema definitions.

Defines the complete vocabulary of field types, layout hints, and
validation schemas used by FormDefinition's JSON ``fields`` column.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ── Field Types ──────────────────────────────────────────────────────

FIELD_TYPES = [
    "text",  # Single line text
    "textarea",  # Multi-line text
    "number",  # Numeric input
    "currency",  # Dollar amount
    "percentage",  # Percentage input
    "date",  # Date picker
    "select",  # Single select dropdown
    "multi_select",  # Multi-select
    "radio",  # Radio button group
    "checkbox",  # Single checkbox (boolean)
    "checkbox_group",  # Multiple checkboxes
    "file_upload",  # File upload (S3)
    "address",  # Address block (street, suite, city, state, zip)
    "phone",  # Phone number with formatting
    "email",  # Email with validation
    "ein",  # Federal EIN with formatting
    "heading",  # Section heading (non-input)
    "paragraph",  # Explanatory text (non-input)
]

FIELD_TYPE_SET = set(FIELD_TYPES)

# Non-input field types (no value collected)
NON_INPUT_TYPES = {"heading", "paragraph"}

# Field types that require an ``options`` list
OPTIONS_REQUIRED_TYPES = {"select", "multi_select", "radio", "checkbox_group"}

# Layout width choices
WIDTH_CHOICES = ("full", "half", "third")


# ── Field Definition Schema ──────────────────────────────────────────


@dataclass
class FieldDefinition:
    """Schema for a single field inside a FormDefinition's ``fields`` JSON.

    Mirrors the JSON structure stored in the database. Provides defaults
    and can be round-tripped to/from dict via ``to_dict`` / ``from_dict``.
    """

    key: str  # Unique field identifier
    label: str  # Display label
    field_type: str  # One of FIELD_TYPES
    required: bool = False
    placeholder: str = ""
    help_text: str = ""
    default_value: Any = None
    options: list[dict] | None = (
        None  # For select/radio/checkbox_group: [{"value": "x", "label": "X"}]
    )
    validation: dict | None = (
        None  # {"min": 0, "max": 100, "pattern": "regex", "min_length": 1, "max_length": 500}
    )
    width: str = "full"  # "full", "half", "third"
    group: str = ""  # Visual grouping key
    order: int = 0  # Sort order within group
    conditions: list[dict] | None = None  # Inline conditional visibility rules

    def to_dict(self) -> dict:
        """Serialize to a plain dict suitable for JSON storage."""
        d: dict[str, Any] = {
            "key": self.key,
            "label": self.label,
            "field_type": self.field_type,
            "required": self.required,
            "order": self.order,
        }
        if self.placeholder:
            d["placeholder"] = self.placeholder
        if self.help_text:
            d["help_text"] = self.help_text
        if self.default_value is not None:
            d["default_value"] = self.default_value
        if self.options:
            d["options"] = self.options
        if self.validation:
            d["validation"] = self.validation
        if self.width != "full":
            d["width"] = self.width
        if self.group:
            d["group"] = self.group
        if self.conditions:
            d["conditions"] = self.conditions
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "FieldDefinition":
        """Deserialize from a plain dict (e.g. from JSON storage)."""
        return cls(
            key=data["key"],
            label=data["label"],
            field_type=data["field_type"],
            required=data.get("required", False),
            placeholder=data.get("placeholder", ""),
            help_text=data.get("help_text", ""),
            default_value=data.get("default_value"),
            options=data.get("options"),
            validation=data.get("validation"),
            width=data.get("width", "full"),
            group=data.get("group", ""),
            order=data.get("order", 0),
            conditions=data.get("conditions"),
        )


# ── Tier 1 Coverage Types ───────────────────────────────────────────

TIER_1_COVERAGE_TYPES = [
    "commercial-general-liability",
    "directors-and-officers",
    "technology-errors-and-omissions",
    "cyber-liability",
    "fiduciary-liability",
    "hired-and-non-owned-auto",
    "media-liability",
    "employment-practices-liability",
]

COVERAGE_TYPE_LABELS = {
    "commercial-general-liability": "Commercial General Liability",
    "directors-and-officers": "Directors & Officers",
    "technology-errors-and-omissions": "Technology E&O",
    "cyber-liability": "Cyber Liability",
    "fiduciary-liability": "Fiduciary Liability",
    "hired-and-non-owned-auto": "Hired & Non-Owned Auto",
    "media-liability": "Media Liability",
    "employment-practices-liability": "Employment Practices Liability",
}
