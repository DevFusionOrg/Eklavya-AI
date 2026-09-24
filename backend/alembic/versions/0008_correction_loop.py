from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_correction_loop"
down_revision: str | None = "0007_validation_references"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("correction_round", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "applications", sa.Column("correction_deadline", sa.DateTime(timezone=True))
    )
    op.add_column("deficiencies", sa.Column("resolved_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("deficiencies", "resolved_at")
    op.drop_column("applications", "correction_deadline")
    op.drop_column("applications", "correction_round")
