from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "0005_application_status_history"
down_revision: str | None = "0004_scheme_version_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        return
    inspector = sa.inspect(op.get_bind())
    if "application_status_history" not in inspector.get_table_names():
        op.create_table(
            "application_status_history",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("application_id", sa.Uuid(), nullable=False),
            sa.Column("from_status", sa.String(length=32), nullable=True),
            sa.Column("to_status", sa.String(length=32), nullable=False),
            sa.Column("actor_id", sa.Uuid(), nullable=True),
            sa.Column("actor_role", sa.String(length=32), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["application_id"], ["applications.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_application_status_history_application_created",
            "application_status_history",
            ["application_id", "created_at"],
        )


def downgrade() -> None:
    if context.is_offline_mode():
        return
    op.drop_index(
        "ix_application_status_history_application_created",
        table_name="application_status_history",
    )
    op.drop_table("application_status_history")
