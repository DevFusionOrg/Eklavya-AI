from collections.abc import Sequence

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    import app.db.models  # noqa: F401
    from alembic import op
    from app.db.base import Base

    Base.metadata.create_all(op.get_bind())


def downgrade() -> None:
    import app.db.models  # noqa: F401
    from alembic import op
    from app.db.base import Base

    Base.metadata.drop_all(op.get_bind())
