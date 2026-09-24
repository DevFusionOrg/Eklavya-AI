from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "0004_scheme_version_config"
down_revision: str | None = "0003_audit_protection"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        return
    inspector = sa.inspect(op.get_bind())
    version_columns = {
        column["name"] for column in inspector.get_columns("scheme_versions")
    }
    document_columns = {
        column["name"] for column in inspector.get_columns("scheme_documents_required")
    }
    additions = {
        "form_schema": sa.Column(
            "form_schema", sa.JSON(), nullable=False, server_default="{}"
        ),
        "ui_hints": sa.Column(
            "ui_hints", sa.JSON(), nullable=False, server_default="{}"
        ),
        "eligibility_rules": sa.Column(
            "eligibility_rules", sa.JSON(), nullable=False, server_default="{}"
        ),
        "selection_rules": sa.Column(
            "selection_rules", sa.JSON(), nullable=False, server_default="{}"
        ),
        "status": sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="DRAFT"
        ),
        "open_at": sa.Column("open_at", sa.DateTime(timezone=True), nullable=True),
        "close_at": sa.Column("close_at", sa.DateTime(timezone=True), nullable=True),
        "published_at": sa.Column(
            "published_at", sa.DateTime(timezone=True), nullable=True
        ),
    }
    for name, column in additions.items():
        if name not in version_columns:
            op.add_column("scheme_versions", column)
    if "validity_rules" not in document_columns:
        op.add_column(
            "scheme_documents_required",
            sa.Column("validity_rules", sa.JSON(), nullable=False, server_default="{}"),
        )


def downgrade() -> None:
    if context.is_offline_mode():
        return
    for name in (
        "published_at",
        "close_at",
        "open_at",
        "status",
        "selection_rules",
        "eligibility_rules",
        "ui_hints",
        "form_schema",
    ):
        op.drop_column("scheme_versions", name)
    op.drop_column("scheme_documents_required", "validity_rules")
