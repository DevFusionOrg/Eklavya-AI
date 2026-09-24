import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.rules.engine import evaluate
from app.rules.selection import select_candidates


@given(st.booleans())
def test_all_combinator_preserves_true_child(value: bool) -> None:
    result = evaluate(
        {"all": [{"id": "one", "field": "value", "operator": "eq", "value": value}]},
        {"value": value},
    )[0]
    assert result.passed is True


@given(st.booleans())
def test_any_and_not_combinators(value: bool) -> None:
    results = evaluate(
        [
            {
                "id": "any",
                "any": [
                    {"id": "child", "field": "value", "operator": "eq", "value": value}
                ],
            },
            {
                "id": "not",
                "not": {
                    "id": "child",
                    "field": "value",
                    "operator": "eq",
                    "value": not value,
                },
            },
        ],
        {"value": value},
    )
    assert all(result.passed for result in results)


@pytest.mark.parametrize(
    ("operator", "actual", "expected", "passed"),
    [
        ("eq", 10, 10, True),
        ("ne", 10, 9, True),
        ("lt", 9, 10, True),
        ("lte", 10, 10, True),
        ("gt", 11, 10, True),
        ("gte", 10, 10, True),
        ("in", "ST", ["SC", "ST"], True),
        ("between", 75, [60, 80], True),
        ("exists", "yes", True, True),
        ("exists", None, True, False),
        ("regex", "ST-123", r"^ST-", True),
        ("date_before", "2026-01-01", "2026-02-01", True),
        ("date_after", "2026-03-01", "2026-02-01", True),
        ("eq", "10", 10, True),
        ("lte", "10", 10, True),
        ("gte", "10", 10, True),
        ("lt", "9", 10, True),
        ("gt", "11", 10, True),
        ("ne", "10", 11, True),
        ("in", "PG", ["UG", "PG"], True),
        ("between", 60, [60, 80], True),
        ("between", 80, [60, 80], True),
        ("regex", "ST", r"ST", True),
        ("date_before", "2026-01-31", "2026-02-01", True),
        ("date_after", "2026-02-02", "2026-02-01", True),
        ("eq", 10, 11, False),
        ("ne", 10, 10, False),
        ("lt", 10, 10, False),
        ("lte", 11, 10, False),
        ("gt", 10, 11, False),
        ("gte", 9, 10, False),
        ("in", "X", ["A", "B"], False),
        ("between", 81, [60, 80], False),
        ("regex", "SC", r"^ST", False),
        ("date_before", "2026-03-01", "2026-02-01", False),
        ("date_after", "2026-01-01", "2026-02-01", False),
        ("eq", None, 10, False),
        ("lt", None, 10, False),
        ("lte", None, 10, False),
        ("gt", None, 10, False),
        ("gte", None, 10, False),
        ("between", None, [1, 2], False),
    ],
)
def test_operator_matrix(
    operator: str, actual: object, expected: object, passed: bool
) -> None:
    result = evaluate(
        [
            {
                "id": operator,
                "field": "form_data.value",
                "operator": operator,
                "value": expected,
            }
        ],
        {"form_data": {"value": actual}},
    )[0]
    assert result.passed is passed
    assert result.inputs["field"] == "form_data.value"


def test_acceptance_rules_income_certificate_marks_age_and_course() -> None:
    rules = [
        {
            "id": "income",
            "field": "form_data.income",
            "operator": "lte",
            "value": 250000,
            "severity": "BLOCKER",
        },
        {
            "id": "certificate",
            "field": "extracted_fields.st_certificate",
            "operator": "exists",
            "value": True,
            "severity": "BLOCKER",
        },
        {
            "id": "marks",
            "field": "form_data.marks",
            "operator": "gte",
            "value": 60,
            "severity": "BLOCKER",
        },
        {
            "id": "age",
            "field": "form_data.age",
            "operator": "lte",
            "value": 35,
            "severity": "BLOCKER",
        },
        {
            "id": "course",
            "field": "form_data.course_level",
            "operator": "in",
            "value": ["PG", "PHD"],
            "severity": "BLOCKER",
        },
    ]
    context = {
        "form_data": {
            "income": "200000",
            "marks": 75,
            "age": 30,
            "course_level": "PHD",
        },
        "extracted_fields": {"st_certificate": "verified"},
    }
    assert all(result.passed for result in evaluate(rules, context))


def test_missing_field_fails_with_explainable_input() -> None:
    result = evaluate(
        [
            {
                "id": "income",
                "field": "form_data.income",
                "operator": "lte",
                "value": 100,
            }
        ],
        {"form_data": {}},
    )[0]
    assert result.passed is False
    assert result.inputs["value"] is None


def test_selection_weights_tie_breakers_and_quota() -> None:
    config = {
        "filters": [],
        "weights": [
            {
                "id": "marks",
                "weight": 10,
                "rule": {"field": "marks", "operator": "gte", "value": 60},
            }
        ],
        "tie_breakers": ["rank"],
        "quotas": [{"field": "gender", "value": "F", "limit": 1}],
    }
    selected = select_candidates(
        [
            {"id": "a", "marks": 90, "rank": 2, "gender": "F"},
            {"id": "b", "marks": 90, "rank": 1, "gender": "F"},
            {"id": "c", "marks": 80, "rank": 3, "gender": "M"},
        ],
        config,
    )
    assert [candidate["id"] for candidate in selected] == ["b", "c"]
