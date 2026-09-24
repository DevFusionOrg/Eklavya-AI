from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "0010_officer_assignments"
down_revision: str | None = "0009_ai_response_hash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        return
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("applications")
    }
    if "scrutiny_officer_id" not in columns:
        op.add_column(
            "applications",
            sa.Column(
                "scrutiny_officer_id",
                sa.Uuid(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if "verifying_officer_id" not in columns:
        op.add_column(
            "applications",
            sa.Column(
                "verifying_officer_id",
                sa.Uuid(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    if context.is_offline_mode():
        return
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("applications")
    }
    if "verifying_officer_id" in columns:
        op.drop_column("applications", "verifying_officer_id")
    if "scrutiny_officer_id" in columns:
        op.drop_column("applications", "scrutiny_officer_id")
