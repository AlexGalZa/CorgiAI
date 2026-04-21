"""
Tests for forms.validators.missing_required_fields (H6 — Custom Crime).

Verifies schema-drift detection: when the latest active FormDefinition for
the ``custom-crime`` coverage adds a required field, older in-flight payloads
that lack it get a 400 with the missing field keys.
"""

from django.test import TestCase

from forms.models import FormDefinition
from forms.validators import (
    COVERAGES_REQUIRING_LATEST_SCHEMA,
    missing_required_fields,
    validate_coverage_payloads,
)


def _crime_form(version=1, fields=None, conditional_logic=None, is_active=True):
    """Create a FormDefinition for custom-crime with the given schema."""
    return FormDefinition.objects.create(
        name=f"Custom Crime v{version}",
        slug=f"custom-crime-v{version}",
        version=version,
        description="Custom crime coverage form",
        fields=fields
        or [
            {
                "key": "employee_count",
                "label": "Employees",
                "field_type": "number",
                "required": True,
            },
            {
                "key": "annual_revenue",
                "label": "Revenue",
                "field_type": "number",
                "required": True,
            },
        ],
        conditional_logic=conditional_logic or {"rules": []},
        rating_field_mappings={},
        coverage_type="custom-crime",
        is_active=is_active,
    )


class MissingRequiredFieldsTest(TestCase):
    """Unit coverage for the Crime v2 schema enforcement."""

    def test_custom_crime_is_flagged_for_latest_schema_enforcement(self):
        # Guardrail: if this coverage is accidentally removed from the set
        # the whole validator silently no-ops on Crime payloads.
        self.assertIn("custom-crime", COVERAGES_REQUIRING_LATEST_SCHEMA)

    def test_complete_payload_returns_empty_list(self):
        _crime_form()
        missing = missing_required_fields(
            "custom-crime",
            {"employee_count": 10, "annual_revenue": 5_000_000},
        )
        self.assertEqual(missing, [])

    def test_missing_required_field_is_reported(self):
        _crime_form()
        missing = missing_required_fields(
            "custom-crime",
            {"employee_count": 10},  # annual_revenue absent
        )
        self.assertEqual(missing, ["annual_revenue"])

    def test_blank_string_counts_as_missing(self):
        _crime_form()
        missing = missing_required_fields(
            "custom-crime",
            {"employee_count": 10, "annual_revenue": "   "},
        )
        self.assertEqual(missing, ["annual_revenue"])

    def test_none_value_counts_as_missing(self):
        _crime_form()
        missing = missing_required_fields(
            "custom-crime",
            {"employee_count": None, "annual_revenue": 5_000_000},
        )
        self.assertEqual(missing, ["employee_count"])

    def test_empty_collection_counts_as_missing(self):
        _crime_form(
            fields=[
                {
                    "key": "locations",
                    "label": "Locations",
                    "field_type": "multi",
                    "required": True,
                },
            ]
        )
        missing = missing_required_fields("custom-crime", {"locations": []})
        self.assertEqual(missing, ["locations"])

    def test_zero_value_is_not_missing(self):
        _crime_form()
        # A legitimate answer of "0 employees" should not trip the validator.
        missing = missing_required_fields(
            "custom-crime",
            {"employee_count": 0, "annual_revenue": 1_000},
        )
        self.assertEqual(missing, [])

    def test_non_required_field_not_reported(self):
        _crime_form(
            fields=[
                {"key": "employee_count", "field_type": "number", "required": True},
                {"key": "optional_note", "field_type": "text", "required": False},
            ]
        )
        missing = missing_required_fields(
            "custom-crime",
            {"employee_count": 5},  # optional_note blank
        )
        self.assertEqual(missing, [])

    def test_latest_active_schema_takes_precedence(self):
        """Newly-required fields in v2 catch legacy payloads built against v1."""
        _crime_form(version=1, is_active=False)
        # v2 introduces a new required field.
        _crime_form(
            version=2,
            fields=[
                {"key": "employee_count", "field_type": "number", "required": True},
                {"key": "annual_revenue", "field_type": "number", "required": True},
                {"key": "has_prior_losses", "field_type": "select", "required": True},
            ],
        )

        # A legacy payload from before v2 — missing the new required field.
        missing = missing_required_fields(
            "custom-crime",
            {"employee_count": 10, "annual_revenue": 5_000_000},
        )
        self.assertEqual(missing, ["has_prior_losses"])

    def test_inactive_form_is_ignored(self):
        """Only active FormDefinitions participate in latest-schema lookup."""
        _crime_form(version=1, is_active=False)
        # Highest *active* version is now nothing → validator should no-op.
        missing = missing_required_fields("custom-crime", {})
        self.assertEqual(missing, [])

    def test_no_schema_returns_empty_list(self):
        missing = missing_required_fields("custom-crime", {})
        self.assertEqual(missing, [])

    def test_none_payload_treated_as_empty_dict(self):
        _crime_form()
        missing = missing_required_fields("custom-crime", None)
        self.assertEqual(sorted(missing), ["annual_revenue", "employee_count"])

    def test_conditional_hidden_field_is_not_required(self):
        """Fields hidden by conditional logic should not be flagged."""
        _crime_form(
            fields=[
                {"key": "has_prior_losses", "field_type": "select", "required": True},
                {"key": "prior_loss_detail", "field_type": "text", "required": True},
            ],
            conditional_logic={
                "rules": [
                    {
                        "target_field": "prior_loss_detail",
                        "action": "show",
                        "conditions": [
                            {
                                "field_key": "has_prior_losses",
                                "operator": "equals",
                                "value": "yes",
                            }
                        ],
                        "match": "all",
                    }
                ]
            },
        )
        # User said "no" — prior_loss_detail is hidden, so we don't require it.
        missing = missing_required_fields(
            "custom-crime",
            {"has_prior_losses": "no"},
        )
        self.assertEqual(missing, [])

    def test_conditional_visible_field_is_required(self):
        """If the conditional makes a field visible, missing value must be reported."""
        _crime_form(
            fields=[
                {"key": "has_prior_losses", "field_type": "select", "required": True},
                {"key": "prior_loss_detail", "field_type": "text", "required": True},
            ],
            conditional_logic={
                "rules": [
                    {
                        "target_field": "prior_loss_detail",
                        "action": "show",
                        "conditions": [
                            {
                                "field_key": "has_prior_losses",
                                "operator": "equals",
                                "value": "yes",
                            }
                        ],
                        "match": "all",
                    }
                ]
            },
        )
        missing = missing_required_fields(
            "custom-crime",
            {"has_prior_losses": "yes"},  # prior_loss_detail blank
        )
        self.assertEqual(missing, ["prior_loss_detail"])


class ValidateCoveragePayloadsTest(TestCase):
    """Higher-level wrapper that gates coverages via COVERAGES_REQUIRING_LATEST_SCHEMA."""

    def test_non_enforced_coverage_is_skipped(self):
        """Only coverages in the enforcement set are validated."""
        _crime_form()  # not used here, but ensures DB is clean + consistent
        result = validate_coverage_payloads({"cyber-liability": {}})
        self.assertEqual(result, {})

    def test_enforced_coverage_reports_missing_fields(self):
        _crime_form()
        result = validate_coverage_payloads({"custom-crime": {"employee_count": 1}})
        self.assertEqual(result, {"custom-crime": ["annual_revenue"]})

    def test_empty_coverage_data_returns_empty(self):
        self.assertEqual(validate_coverage_payloads(None), {})
        self.assertEqual(validate_coverage_payloads({}), {})

    def test_passing_payload_produces_no_entry(self):
        _crime_form()
        result = validate_coverage_payloads(
            {"custom-crime": {"employee_count": 10, "annual_revenue": 5000}}
        )
        self.assertEqual(result, {})
