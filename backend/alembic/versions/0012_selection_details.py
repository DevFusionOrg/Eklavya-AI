from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "0012_selection_details"
down_revision: str | None = "0011_review_override_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        return
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("selections")
    }
    additions = [
        ("list_status", sa.String(16), "PROVISIONAL"),
        ("score", sa.Numeric(12, 4), None),
        ("score_breakdown", sa.JSON(), "{}"),
        ("is_frozen", sa.Boolean(), "false"),
    ]
    for name, column_type, default in additions:
        if name not in columns:
            op.add_column(
                "selections",
                sa.Column(
                    name,
                    column_type,
                    nullable=name
                    not in {"list_status", "score_breakdown", "is_frozen"},
                    server_default=default,
                ),
            )


def downgrade() -> None:
    if context.is_offline_mode():
        return
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("selections")
    }
    for name in ("is_frozen", "score_breakdown", "score", "list_status"):
        if name in columns:
            op.drop_column("selections", name)
