from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "0011_review_override_source"
down_revision: str | None = "0010_officer_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        return
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("review_actions")
    }
    if "override_source" not in columns:
        op.add_column(
            "review_actions",
            sa.Column(
                "override_source",
                sa.String(length=16),
                nullable=False,
                server_default="NONE",
            ),
        )


def downgrade() -> None:
    if context.is_offline_mode():
        return
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("review_actions")
    }
    if "override_source" in columns:
        op.drop_column("review_actions", "override_source")
