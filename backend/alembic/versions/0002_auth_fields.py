from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "0002_auth_fields"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        return
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "failed_login_attempts" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if "locked_until" not in columns:
        op.add_column(
            "users",
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        )
    if "token_version" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "token_version", sa.Integer(), nullable=False, server_default="0"
            ),
        )


def downgrade() -> None:
    if context.is_offline_mode():
        return
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    for column in ("token_version", "locked_until", "failed_login_attempts"):
        if column in columns:
            op.drop_column("users", column)
