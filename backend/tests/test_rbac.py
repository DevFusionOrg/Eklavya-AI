import uuid

import pytest
from fastapi import HTTPException

from app.auth.dependencies import require_roles
from app.db.models import User


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    ["APPLICANT", "SCRUTINY_OFFICER", "VERIFYING_OFFICER", "COMMITTEE_MEMBER"],
)
async def test_non_admin_roles_are_denied_admin_capability(role: str) -> None:
    user = User(
        id=uuid.uuid4(),
        email="applicant@example.com",
        password_hash="hash",
        role=role,
        is_active=True,
        token_version=0,
        failed_login_attempts=0,
    )
    dependency = require_roles("ADMIN")
    with pytest.raises(HTTPException) as error:
        await dependency(user)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_role_dependency_allows_listed_role() -> None:
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        password_hash="hash",
        role="ADMIN",
        is_active=True,
        token_version=0,
        failed_login_attempts=0,
    )
    assert await require_roles("ADMIN")(user) is user
