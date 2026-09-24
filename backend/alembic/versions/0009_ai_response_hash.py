from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "0009_ai_response_hash"
down_revision: str | None = "0008_correction_loop"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        return
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("ai_recommendations")
    }
    if "response_hash" in columns:
        return
    op.add_column(
        "ai_recommendations",
        sa.Column("response_hash", sa.String(128), nullable=True),
    )
    op.execute(
        "UPDATE ai_recommendations SET response_hash = prompt_hash "
        "WHERE response_hash IS NULL"
    )
    op.alter_column("ai_recommendations", "response_hash", nullable=False)


def downgrade() -> None:
    if context.is_offline_mode():
        return
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("ai_recommendations")
    }
    if "response_hash" in columns:
        op.drop_column("ai_recommendations", "response_hash")
