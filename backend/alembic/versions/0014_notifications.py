from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "0014_notifications"
down_revision: str | None = "0013_post_selection"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        return
    inspector = sa.inspect(op.get_bind())
    notification_columns = {
        column["name"] for column in inspector.get_columns("notifications")
    }
    additions = [
        ("template_key", sa.String(64), None),
        ("locale", sa.String(8), "en"),
        ("retry_count", sa.Integer(), "0"),
        ("last_error", sa.Text(), None),
        ("provider_message_id", sa.String(255), None),
    ]
    for name, column_type, default in additions:
        if name not in notification_columns:
            op.add_column(
                "notifications",
                sa.Column(
                    name,
                    column_type,
                    nullable=name in {"locale", "retry_count"},
                    server_default=default,
                ),
            )
    if "notification_preferences" not in inspector.get_table_names():
        op.create_table(
            "notification_preferences",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "user_id",
                sa.Uuid(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            sa.Column("locale", sa.String(8), nullable=False, server_default="en"),
            sa.Column(
                "sms_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.Column(
                "email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.Column(
                "in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
        )


def downgrade() -> None:
    if context.is_offline_mode():
        return
    inspector = sa.inspect(op.get_bind())
    if "notification_preferences" in inspector.get_table_names():
        op.drop_table("notification_preferences")
    columns = {column["name"] for column in inspector.get_columns("notifications")}
    for name in (
        "provider_message_id",
        "last_error",
        "retry_count",
        "locale",
        "template_key",
    ):
        if name in columns:
            op.drop_column("notifications", name)
