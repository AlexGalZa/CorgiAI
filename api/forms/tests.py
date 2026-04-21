"""
Tests for the forms module.

Covers FormDefinition CRUD, form duplication (version increment),
conditional logic evaluation (all operators), form validation,
rating field extraction, and visible fields calculation.
"""

from django.test import TestCase

from forms.models import FormDefinition
from forms.service import FormService
from forms.logic import (
    evaluate_conditions,
    _evaluate_single_condition,
    _is_empty,
)
from tests.factories import create_test_form_definition


class FormDefinitionModelTest(TestCase):
    """Tests for FormDefinition model."""

    def test_form_definition_str(self):
        form = create_test_form_definition(name="Cyber Form", version=2)
        self.assertEqual(str(form), "Cyber Form v2")

    def test_form_definition_unique_slug_version(self):
        create_test_form_definition(slug="test-unique", version=1)
        with self.assertRaises(Exception):
            create_test_form_definition(slug="test-unique", version=1)


class FormServiceCRUDTest(TestCase):
    """Tests for FormService CRUD operations."""

    def test_create_form(self):
        data = {
            "name": "New Form",
            "slug": "new-form",
            "version": 1,
            "fields": [
                {"key": "name", "label": "Name", "field_type": "text", "required": True}
            ],
            "is_active": True,
            "coverage_type": "cyber-liability",
        }
        form = FormService.create_form(data)
        self.assertIsNotNone(form.id)
        self.assertEqual(form.name, "New Form")
        self.assertTrue(form.is_active)

    def test_get_form_by_id(self):
        form = create_test_form_definition()
        found = FormService.get_form_by_id(form.id)
        self.assertEqual(found.id, form.id)

    def test_get_form_by_id_not_found(self):
        found = FormService.get_form_by_id(99999)
        self.assertIsNone(found)

    def test_update_form(self):
        form = create_test_form_definition()
        updated = FormService.update_form(form.id, {"name": "Updated Name"})
        self.assertEqual(updated.name, "Updated Name")

    def test_delete_form_deactivates(self):
        form = create_test_form_definition(is_active=True)
        result = FormService.delete_form(form.id)
        self.assertTrue(result)
        form.refresh_from_db()
        self.assertFalse(form.is_active)

    def test_list_forms(self):
        create_test_form_definition(name="Form A", slug="form-a")
        create_test_form_definition(name="Form B", slug="form-b")
        forms = FormService.list_forms()
        self.assertGreaterEqual(len(forms), 2)

    def test_get_active_form_for_coverage(self):
        create_test_form_definition(
            slug="cyber-form",
            coverage_type="cyber-liability",
            is_active=True,
            version=1,
        )
        form = FormService.get_active_form("cyber-liability")
        self.assertIsNotNone(form)
        self.assertEqual(form.coverage_type, "cyber-liability")


class FormDuplicationTest(TestCase):
    """Tests for form duplication with version increment."""

    def test_duplicate_form_increments_version(self):
        original = create_test_form_definition(slug="dup-form", version=1)
        duplicate = FormService.duplicate_form(original.id)

        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate.slug, original.slug)
        self.assertEqual(duplicate.version, 2)
        self.assertFalse(duplicate.is_active)  # New version starts inactive
        self.assertEqual(duplicate.name, original.name)

    def test_duplicate_finds_highest_version(self):
        create_test_form_definition(slug="multi-ver", version=1)
        create_test_form_definition(slug="multi-ver", version=3)
        original = FormDefinition.objects.filter(slug="multi-ver", version=1).first()

        duplicate = FormService.duplicate_form(original.id)
        self.assertEqual(duplicate.version, 4)  # max(1,3) + 1

    def test_duplicate_nonexistent_returns_none(self):
        result = FormService.duplicate_form(99999)
        self.assertIsNone(result)


class ConditionalLogicEqualsTest(TestCase):
    """Tests for equals operator."""

    def test_equals_string(self):
        condition = {"field_key": "country", "operator": "equals", "value": "US"}
        self.assertTrue(_evaluate_single_condition(condition, {"country": "US"}))
        self.assertFalse(_evaluate_single_condition(condition, {"country": "UK"}))

    def test_equals_boolean_true(self):
        condition = {"field_key": "has_employees", "operator": "equals", "value": True}
        self.assertTrue(_evaluate_single_condition(condition, {"has_employees": True}))
        self.assertFalse(
            _evaluate_single_condition(condition, {"has_employees": False})
        )

    def test_equals_boolean_string_comparison(self):
        condition = {"field_key": "active", "operator": "equals", "value": "true"}
        self.assertTrue(_evaluate_single_condition(condition, {"active": True}))


class ConditionalLogicNotEqualsTest(TestCase):
    """Tests for not_equals operator."""

    def test_not_equals(self):
        condition = {"field_key": "status", "operator": "not_equals", "value": "active"}
        self.assertTrue(_evaluate_single_condition(condition, {"status": "inactive"}))
        self.assertFalse(_evaluate_single_condition(condition, {"status": "active"}))


class ConditionalLogicContainsTest(TestCase):
    """Tests for contains operator."""

    def test_contains_in_string(self):
        condition = {
            "field_key": "description",
            "operator": "contains",
            "value": "tech",
        }
        self.assertTrue(
            _evaluate_single_condition(condition, {"description": "technology company"})
        )
        self.assertFalse(
            _evaluate_single_condition(condition, {"description": "retail store"})
        )

    def test_contains_in_list(self):
        condition = {"field_key": "tags", "operator": "contains", "value": "saas"}
        self.assertTrue(
            _evaluate_single_condition(condition, {"tags": ["saas", "b2b"]})
        )
        self.assertFalse(_evaluate_single_condition(condition, {"tags": ["retail"]}))


class ConditionalLogicComparisonTest(TestCase):
    """Tests for gt and lt operators."""

    def test_greater_than(self):
        condition = {"field_key": "revenue", "operator": "gt", "value": 1000000}
        self.assertTrue(_evaluate_single_condition(condition, {"revenue": 2000000}))
        self.assertFalse(_evaluate_single_condition(condition, {"revenue": 500000}))

    def test_less_than(self):
        condition = {"field_key": "employees", "operator": "lt", "value": 50}
        self.assertTrue(_evaluate_single_condition(condition, {"employees": 25}))
        self.assertFalse(_evaluate_single_condition(condition, {"employees": 100}))

    def test_gt_with_non_numeric_returns_false(self):
        condition = {"field_key": "value", "operator": "gt", "value": 10}
        self.assertFalse(_evaluate_single_condition(condition, {"value": "abc"}))


class ConditionalLogicInNotInTest(TestCase):
    """Tests for in and not_in operators."""

    def test_in_operator(self):
        condition = {
            "field_key": "state",
            "operator": "in",
            "value": ["CA", "NY", "TX"],
        }
        self.assertTrue(_evaluate_single_condition(condition, {"state": "CA"}))
        self.assertFalse(_evaluate_single_condition(condition, {"state": "FL"}))

    def test_not_in_operator(self):
        condition = {"field_key": "state", "operator": "not_in", "value": ["CA", "NY"]}
        self.assertTrue(_evaluate_single_condition(condition, {"state": "TX"}))
        self.assertFalse(_evaluate_single_condition(condition, {"state": "CA"}))


class ConditionalLogicEmptyTest(TestCase):
    """Tests for is_empty and is_not_empty operators."""

    def test_is_empty_none(self):
        condition = {"field_key": "notes", "operator": "is_empty"}
        self.assertTrue(_evaluate_single_condition(condition, {"notes": None}))

    def test_is_empty_empty_string(self):
        condition = {"field_key": "notes", "operator": "is_empty"}
        self.assertTrue(_evaluate_single_condition(condition, {"notes": ""}))
        self.assertTrue(_evaluate_single_condition(condition, {"notes": "   "}))

    def test_is_empty_empty_list(self):
        condition = {"field_key": "items", "operator": "is_empty"}
        self.assertTrue(_evaluate_single_condition(condition, {"items": []}))

    def test_is_not_empty(self):
        condition = {"field_key": "name", "operator": "is_not_empty"}
        self.assertTrue(_evaluate_single_condition(condition, {"name": "John"}))
        self.assertFalse(_evaluate_single_condition(condition, {"name": ""}))

    def test_is_empty_missing_field(self):
        condition = {"field_key": "missing", "operator": "is_empty"}
        self.assertTrue(_evaluate_single_condition(condition, {}))


class EvaluateConditionsTest(TestCase):
    """Tests for evaluate_conditions with rule lists."""

    def test_show_action_with_all_match(self):
        rules = [
            {
                "target_field": "details",
                "action": "show",
                "conditions": [
                    {"field_key": "type", "operator": "equals", "value": "business"},
                    {"field_key": "size", "operator": "gt", "value": 10},
                ],
                "match": "all",
            }
        ]
        visibility = evaluate_conditions(rules, {"type": "business", "size": 20})
        self.assertTrue(visibility.get("details"))

        visibility = evaluate_conditions(rules, {"type": "business", "size": 5})
        self.assertFalse(visibility.get("details"))

    def test_show_action_with_any_match(self):
        rules = [
            {
                "target_field": "alert",
                "action": "show",
                "conditions": [
                    {"field_key": "status", "operator": "equals", "value": "critical"},
                    {"field_key": "priority", "operator": "equals", "value": "high"},
                ],
                "match": "any",
            }
        ]
        visibility = evaluate_conditions(
            rules, {"status": "normal", "priority": "high"}
        )
        self.assertTrue(visibility.get("alert"))

    def test_hide_action(self):
        rules = [
            {
                "target_field": "hidden_field",
                "action": "hide",
                "conditions": [
                    {
                        "field_key": "show_advanced",
                        "operator": "equals",
                        "value": False,
                    },
                ],
                "match": "all",
            }
        ]
        visibility = evaluate_conditions(rules, {"show_advanced": False})
        self.assertFalse(visibility.get("hidden_field"))


class FormValidationTest(TestCase):
    """Tests for FormService.validate_submission."""

    def test_valid_submission(self):
        form = create_test_form_definition()
        data = {
            "company_name": "Acme",
            "revenue": 1000000,
        }
        is_valid, errors = FormService.validate_submission(form, data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_missing_required_field(self):
        form = create_test_form_definition()
        data = {"revenue": 1000000}  # Missing company_name
        is_valid, errors = FormService.validate_submission(form, data)
        self.assertFalse(is_valid)
        self.assertTrue(any("Company Name" in e for e in errors))

    def test_number_below_min(self):
        form = create_test_form_definition()
        data = {"company_name": "Test", "revenue": -100}
        is_valid, errors = FormService.validate_submission(form, data)
        self.assertFalse(is_valid)

    def test_number_above_max(self):
        form = create_test_form_definition()
        data = {
            "company_name": "Test",
            "revenue": 500,
            "has_employees": "yes",
            "employee_count": 200000,
        }
        is_valid, errors = FormService.validate_submission(form, data)
        self.assertFalse(is_valid)

    def test_conditional_field_only_validated_when_visible(self):
        form = create_test_form_definition()
        # employee_count is only visible when has_employees=yes
        # When has_employees is not "yes", employee_count should not be validated
        data = {
            "company_name": "Test",
            "revenue": 1000000,
            "has_employees": "no",
        }
        is_valid, errors = FormService.validate_submission(form, data)
        self.assertTrue(is_valid)

    def test_invalid_select_option(self):
        form = create_test_form_definition()
        data = {
            "company_name": "Test",
            "revenue": 1000,
            "has_employees": "maybe",  # Not in options
        }
        is_valid, errors = FormService.validate_submission(form, data)
        self.assertFalse(is_valid)


class RatingFieldExtractionTest(TestCase):
    """Tests for FormService.extract_rating_inputs."""

    def test_extract_mapped_fields(self):
        form = create_test_form_definition()
        data = {
            "company_name": "Acme",
            "revenue": 1000000,
            "employee_count": 50,
            "extra_field": "ignored",
        }
        result = FormService.extract_rating_inputs(form, data)
        self.assertEqual(result["revenue"], 1000000)
        self.assertEqual(result["employee_count"], 50)
        self.assertNotIn("extra_field", result)
        self.assertNotIn("company_name", result)

    def test_extract_missing_field_not_included(self):
        form = create_test_form_definition()
        data = {"company_name": "Acme"}
        result = FormService.extract_rating_inputs(form, data)
        self.assertNotIn("employee_count", result)


class VisibleFieldsTest(TestCase):
    """Tests for FormService.get_visible_fields."""

    def test_all_fields_visible_without_rules(self):
        form = create_test_form_definition(conditional_logic={})
        data = {}
        visible = FormService.get_visible_fields(form, data)
        self.assertEqual(len(visible), len(form.fields))

    def test_conditional_field_hidden_when_condition_not_met(self):
        form = create_test_form_definition()
        data = {"has_employees": "no"}
        visible = FormService.get_visible_fields(form, data)
        visible_keys = {f["key"] for f in visible}
        self.assertNotIn("employee_count", visible_keys)

    def test_conditional_field_shown_when_condition_met(self):
        form = create_test_form_definition()
        data = {"has_employees": "yes"}
        visible = FormService.get_visible_fields(form, data)
        visible_keys = {f["key"] for f in visible}
        self.assertIn("employee_count", visible_keys)


class IsEmptyHelperTest(TestCase):
    """Tests for the _is_empty helper function."""

    def test_none_is_empty(self):
        self.assertTrue(_is_empty(None))

    def test_empty_string_is_empty(self):
        self.assertTrue(_is_empty(""))
        self.assertTrue(_is_empty("   "))

    def test_empty_list_is_empty(self):
        self.assertTrue(_is_empty([]))

    def test_empty_dict_is_empty(self):
        self.assertTrue(_is_empty({}))

    def test_nonempty_values_not_empty(self):
        self.assertFalse(_is_empty("hello"))
        self.assertFalse(_is_empty([1]))
        self.assertFalse(_is_empty(0))
        self.assertFalse(_is_empty(False))
