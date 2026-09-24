from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_validation_references"
down_revision: str | None = "0006_document_storage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_deficiencies_severity", "deficiencies", type_="check")
    op.create_check_constraint(
        "ck_deficiencies_severity",
        "deficiencies",
        "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'NEEDS_REVIEW', 'BLOCKER', 'WARNING')",
    )
    op.add_column("deficiencies", sa.Column("field", sa.String(128), nullable=True))
    op.add_column(
        "deficiencies",
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("application_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_constraint("ck_deficiencies_severity", "deficiencies", type_="check")
    op.create_check_constraint(
        "ck_deficiencies_severity",
        "deficiencies",
        "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
    )
    op.drop_column("deficiencies", "document_id")
    op.drop_column("deficiencies", "field")
