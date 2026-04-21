"""
Conditional logic engine for dynamic form visibility.

Evaluates show/hide rules stored in ``FormDefinition.conditional_logic``
against the current form data to determine which fields are visible.
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Any


class ConditionOperator(str, Enum):
    """Operators supported by conditional visibility rules."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    IN = "in"
    NOT_IN = "not_in"


@dataclass
class Condition:
    """A single condition that checks a field's value."""

    field_key: str  # The field to check
    operator: str  # ConditionOperator value
    value: Any = None  # Expected value (ignored for is_empty/is_not_empty)


@dataclass
class ConditionalRule:
    """A rule that controls visibility of a target field."""

    target_field: str  # Field to show/hide
    action: str = "show"  # "show" or "hide"
    conditions: list[Condition] = field(default_factory=list)
    match: str = "all"  # "all" (AND) or "any" (OR)


def _is_empty(value: Any) -> bool:
    """Check if a value is considered empty."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _evaluate_single_condition(condition: dict, form_data: dict) -> bool:
    """Evaluate a single condition against form data.

    Args:
        condition: Dict with ``field_key``, ``operator``, and ``value``.
        form_data: Current form submission data.

    Returns:
        True if the condition is satisfied.
    """
    field_key = condition.get("field_key", "")
    operator = condition.get("operator", "equals")
    expected = condition.get("value")
    actual = form_data.get(field_key)

    if operator == ConditionOperator.EQUALS:
        # Handle boolean comparisons flexibly
        if isinstance(expected, bool) or expected in ("true", "false", "True", "False"):
            expected_bool = (
                expected if isinstance(expected, bool) else expected.lower() == "true"
            )
            if isinstance(actual, bool):
                return actual == expected_bool
            if isinstance(actual, str):
                return actual.lower() == str(expected_bool).lower()
        return actual == expected

    if operator == ConditionOperator.NOT_EQUALS:
        if isinstance(expected, bool) or expected in ("true", "false", "True", "False"):
            expected_bool = (
                expected if isinstance(expected, bool) else expected.lower() == "true"
            )
            if isinstance(actual, bool):
                return actual != expected_bool
            if isinstance(actual, str):
                return actual.lower() != str(expected_bool).lower()
        return actual != expected

    if operator == ConditionOperator.CONTAINS:
        if isinstance(actual, str):
            return str(expected) in actual
        if isinstance(actual, (list, tuple)):
            return expected in actual
        return False

    if operator == ConditionOperator.GREATER_THAN:
        try:
            return float(actual) > float(expected)
        except (TypeError, ValueError):
            return False

    if operator == ConditionOperator.LESS_THAN:
        try:
            return float(actual) < float(expected)
        except (TypeError, ValueError):
            return False

    if operator == ConditionOperator.IS_EMPTY:
        return _is_empty(actual)

    if operator == ConditionOperator.IS_NOT_EMPTY:
        return not _is_empty(actual)

    if operator == ConditionOperator.IN:
        if isinstance(expected, (list, tuple)):
            return actual in expected
        return False

    if operator == ConditionOperator.NOT_IN:
        if isinstance(expected, (list, tuple)):
            return actual not in expected
        return False

    return False


def evaluate_conditions(rules: list[dict], form_data: dict) -> dict[str, bool]:
    """Evaluate all conditional rules and return field visibility map.

    Args:
        rules: List of rule dicts, each with:
            - ``target_field``: str — field key affected
            - ``action``: "show" or "hide"
            - ``conditions``: list of condition dicts
            - ``match``: "all" or "any"
        form_data: Current form data dict.

    Returns:
        Dict mapping field_key → is_visible (bool).
        Fields not mentioned in any rule are assumed visible (not included).
    """
    visibility: dict[str, bool] = {}

    for rule in rules:
        target = rule.get("target_field", "")
        action = rule.get("action", "show")
        conditions = rule.get("conditions", [])
        match_mode = rule.get("match", "all")

        if not target or not conditions:
            continue

        results = [_evaluate_single_condition(c, form_data) for c in conditions]

        if match_mode == "any":
            conditions_met = any(results)
        else:  # "all"
            conditions_met = all(results)

        if action == "show":
            visibility[target] = conditions_met
        elif action == "hide":
            visibility[target] = not conditions_met

    return visibility
