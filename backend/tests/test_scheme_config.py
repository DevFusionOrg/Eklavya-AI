from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.api.v1.schemes import SchemeCreate, VersionCreate


def test_version_definition_rejects_reversed_application_dates() -> None:
    with pytest.raises(ValidationError):
        VersionCreate(
            open_at=datetime(2026, 2, 1, tzinfo=UTC),
            close_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_fifth_scheme_is_data_driven() -> None:
    scheme = SchemeCreate(code="FIFTH_SCHEME", name="Fifth Scheme")
    assert scheme.code == "FIFTH_SCHEME"
