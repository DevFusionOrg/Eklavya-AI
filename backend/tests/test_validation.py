from app.validation.service import fuzzy_matches


def test_fuzzy_name_matching_tolerates_case_and_punctuation() -> None:
    assert fuzzy_matches("Sita Kumari", "sita-kumari", 0.9)


def test_fuzzy_name_matching_rejects_wrong_name() -> None:
    assert not fuzzy_matches("Sita Kumari", "Ravi Kumar", 0.8)
