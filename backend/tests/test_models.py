from sqlalchemy import CheckConstraint

from app.db.models import Application, User


def test_application_status_constraint_is_declared() -> None:
    checks = {
        constraint.name
        for constraint in Application.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_applications_status" in checks


def test_user_role_constraint_is_declared() -> None:
    checks = {
        constraint.name
        for constraint in User.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_users_role" in checks
