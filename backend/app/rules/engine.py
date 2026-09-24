import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class EvaluationResult:
    rule_id: str
    passed: bool
    reason: str
    inputs: dict[str, Any]
    severity: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "passed": self.passed,
            "reason": self.reason,
            "inputs": self.inputs,
            "severity": self.severity,
        }


def _resolve(context: Any, path: str) -> Any:
    current = context
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                return None
            current = current[index]
        else:
            return None
    return current


def _value(rule: Any, context: dict[str, Any]) -> tuple[Any, str | None]:
    if isinstance(rule, dict) and "field" in rule:
        path = str(rule["field"])
        return _resolve(context, path), path
    return rule, None


def _coerce_pair(left: Any, right: Any) -> tuple[Any, Any]:
    if isinstance(left, str) and isinstance(right, (int, float)):
        try:
            return float(left), right
        except ValueError:
            return left, right
    if isinstance(right, str) and isinstance(left, (int, float)):
        try:
            return left, float(right)
        except ValueError:
            return left, right
    return left, right


def _date_value(value: Any) -> date | datetime | None:
    if isinstance(value, (date, datetime)):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
    return None


def _compare(operator: str, actual: Any, expected: Any) -> bool:
    if operator == "exists":
        return (actual is not None) is bool(expected)
    if operator == "regex":
        return actual is not None and re.search(str(expected), str(actual)) is not None
    if operator in {"date_before", "date_after"}:
        left_date, right_date = _date_value(actual), _date_value(expected)
        if left_date is None or right_date is None:
            return False
        return (
            left_date < right_date
            if operator == "date_before"
            else left_date > right_date
        )
    actual, expected = _coerce_pair(actual, expected)
    if operator == "eq":
        return bool(actual == expected)
    if operator == "ne":
        return bool(actual != expected)
    if operator == "lt":
        return bool(actual is not None and actual < expected)
    if operator == "lte":
        return bool(actual is not None and actual <= expected)
    if operator == "gt":
        return bool(actual is not None and actual > expected)
    if operator == "gte":
        return bool(actual is not None and actual >= expected)
    if operator == "in":
        return actual in expected if isinstance(expected, (list, tuple, set)) else False
    if operator == "between":
        return (
            isinstance(expected, (list, tuple))
            and len(expected) == 2
            and actual is not None
            and expected[0] <= actual <= expected[1]
        )
    raise ValueError(f"Unsupported rule operator: {operator}")


def _evaluate_rule(rule: dict[str, Any], context: dict[str, Any]) -> EvaluationResult:
    rule_id = str(rule.get("id", "anonymous"))
    message = str(rule.get("message", rule_id))
    severity = str(rule.get("severity", "BLOCKER"))
    inputs: dict[str, Any]
    if "all" in rule:
        children = [_evaluate_rule(child, context) for child in rule["all"]]
        passed = all(child.passed for child in children)
        inputs = {"all": [child.as_dict() for child in children]}
    elif "any" in rule:
        children = [_evaluate_rule(child, context) for child in rule["any"]]
        passed = any(child.passed for child in children)
        inputs = {"any": [child.as_dict() for child in children]}
    elif "not" in rule:
        child = _evaluate_rule(rule["not"], context)
        passed = not child.passed
        inputs = {"not": child.as_dict()}
    else:
        operator = str(rule.get("operator", "eq"))
        field: str | None
        if "field" in rule:
            field = str(rule["field"])
            actual = _resolve(context, field)
            expected, expected_field = _value(
                rule.get("expected", rule.get("value")), context
            )
        else:
            actual, field = _value(rule.get("value"), context)
            expected, expected_field = _value(rule.get("expected"), context)
        passed = _compare(operator, actual, expected)
        inputs = {
            "field": field,
            "value": actual,
            "expected": expected,
            "expected_field": expected_field,
            "operator": operator,
        }
    return EvaluationResult(
        rule_id, passed, message if passed else f"{message}", inputs, severity
    )


def evaluate(
    rules: dict[str, Any] | list[dict[str, Any]], context: dict[str, Any]
) -> list[EvaluationResult]:
    entries = rules if isinstance(rules, list) else rules.get("rules", [rules])
    return [_evaluate_rule(rule, context) for rule in entries]
