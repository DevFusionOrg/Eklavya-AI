from app.selection import export_csv, export_pdf, export_xlsx, rank_candidates


def test_selection_ranking_is_deterministic_and_explainable() -> None:
    candidates = [
        {"id": "b", "marks": 90, "gender": "F"},
        {"id": "a", "marks": 90, "gender": "F"},
        {"id": "c", "marks": 80, "gender": "M"},
    ]
    config = {
        "limit": 1,
        "weights": [
            {
                "id": "marks",
                "weight": 10,
                "rule": {"field": "marks", "operator": "gte", "value": 60},
            }
        ],
        "tie_breakers": ["id"],
        "quotas": [{"field": "gender", "value": "F", "limit": 1}],
    }
    first = rank_candidates(candidates, config)
    second = rank_candidates(list(reversed(candidates)), config)
    assert [item["id"] for item in first] == [item["id"] for item in second]
    assert first[0]["list_status"] == "SELECTED"
    assert first[0]["selection"]["components"][0]["points"] == 10
    assert first[1]["list_status"] == "WAITLISTED"


def test_selection_exports_have_expected_signatures() -> None:
    rows = [{"rank": 1, "application_id": "a", "list_status": "SELECTED", "score": 10}]
    assert export_csv(rows).startswith(b"rank,application_id")
    assert export_xlsx(rows).startswith(b"PK")
    assert export_pdf(rows).startswith(b"%PDF")
