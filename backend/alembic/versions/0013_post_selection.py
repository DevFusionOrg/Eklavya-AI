from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "0013_post_selection"
down_revision: str | None = "0012_selection_details"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _checks(table: str) -> set[str]:
    return {
        check["name"]
        for check in sa.inspect(op.get_bind()).get_check_constraints(table)
        if check["name"]
    }


def upgrade() -> None:
    if context.is_offline_mode():
        return
    awards = _columns("awards")
    if "ck_awards_status" in _checks("awards"):
        op.drop_constraint("ck_awards_status", "awards", type_="check")
    op.create_check_constraint(
        "ck_awards_status",
        "awards",
        "status IN ('PLANNED', 'DISBURSED', 'ON_HOLD', 'CANCELLED')",
    )
    if "instalments" not in awards:
        op.add_column(
            "awards",
            sa.Column("instalments", sa.JSON(), nullable=False, server_default="[]"),
        )
    if "hold_reason" not in awards:
        op.add_column("awards", sa.Column("hold_reason", sa.Text(), nullable=True))
    requirements = _columns("followup_requirements")
    if "requirement_type" not in requirements:
        op.add_column(
            "followup_requirements",
            sa.Column(
                "requirement_type",
                sa.String(64),
                nullable=False,
                server_default="DOCUMENT",
            ),
        )
    if "validation_schema" not in requirements:
        op.add_column(
            "followup_requirements",
            sa.Column(
                "validation_schema", sa.JSON(), nullable=False, server_default="{}"
            ),
        )
    if "status" not in requirements:
        op.add_column(
            "followup_requirements",
            sa.Column(
                "status", sa.String(16), nullable=False, server_default="UPCOMING"
            ),
        )
    if "ck_followup_requirements_status" not in _checks("followup_requirements"):
        op.create_check_constraint(
            "ck_followup_requirements_status",
            "followup_requirements",
            "status IN ('UPCOMING', 'SUBMITTED', 'ACCEPTED', 'REJECTED', 'OVERDUE')",
        )
    submissions = _columns("followup_submissions")
    if "document_id" not in submissions:
        op.add_column(
            "followup_submissions", sa.Column("document_id", sa.Uuid(), nullable=True)
        )
        op.create_foreign_key(
            "fk_followup_submissions_document",
            "followup_submissions",
            "application_documents",
            ["document_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "reviewed_by" not in submissions:
        op.add_column(
            "followup_submissions", sa.Column("reviewed_by", sa.Uuid(), nullable=True)
        )
        op.create_foreign_key(
            "fk_followup_submissions_reviewer",
            "followup_submissions",
            "users",
            ["reviewed_by"],
            ["id"],
        )
    if "reviewed_at" not in submissions:
        op.add_column(
            "followup_submissions",
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "review_remarks" not in submissions:
        op.add_column(
            "followup_submissions",
            sa.Column("review_remarks", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    if context.is_offline_mode():
        return
    for column in ("review_remarks", "reviewed_at"):
        if column in _columns("followup_submissions"):
            op.drop_column("followup_submissions", column)
    if "reviewed_by" in _columns("followup_submissions"):
        op.drop_constraint(
            "fk_followup_submissions_reviewer",
            "followup_submissions",
            type_="foreignkey",
        )
        op.drop_column("followup_submissions", "reviewed_by")
    if "document_id" in _columns("followup_submissions"):
        op.drop_constraint(
            "fk_followup_submissions_document",
            "followup_submissions",
            type_="foreignkey",
        )
        op.drop_column("followup_submissions", "document_id")
    for column in ("status", "validation_schema", "requirement_type"):
        if column in _columns("followup_requirements"):
            op.drop_column("followup_requirements", column)
    for column in ("hold_reason", "instalments"):
        if column in _columns("awards"):
            op.drop_column("awards", column)
