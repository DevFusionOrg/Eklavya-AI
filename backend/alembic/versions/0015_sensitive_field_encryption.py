"""Encrypt applicant contact and Aadhaar-derived fields at rest."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

from app.core.encryption import decrypt_value, encrypt_value

revision: str = "0015_sensitive_field_encryption"
down_revision: str | None = "0014_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        return
    op.alter_column(
        "applicants", "aadhaar_last4", existing_type=sa.String(4), type_=sa.String(128)
    )
    op.alter_column(
        "applicants", "phone", existing_type=sa.String(32), type_=sa.String(512)
    )
    op.alter_column(
        "applicants", "email", existing_type=sa.String(320), type_=sa.String(512)
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, aadhaar_last4, phone, email FROM applicants "
            "WHERE aadhaar_last4 IS NOT NULL OR phone IS NOT NULL OR email IS NOT NULL"
        )
    ).mappings()
    for row in rows:
        values = {
            field: encrypt_value(row[field])
            for field in ("aadhaar_last4", "phone", "email")
            if row[field] is not None
        }
        if values:
            connection.execute(
                sa.text(
                    "UPDATE applicants SET aadhaar_last4 = :aadhaar_last4, "
                    "phone = :phone, email = :email WHERE id = :id"
                ),
                {
                    "id": row["id"],
                    "aadhaar_last4": values.get("aadhaar_last4", row["aadhaar_last4"]),
                    "phone": values.get("phone", row["phone"]),
                    "email": values.get("email", row["email"]),
                },
            )


def downgrade() -> None:
    if context.is_offline_mode():
        return
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, aadhaar_last4, phone, email FROM applicants "
            "WHERE aadhaar_last4 IS NOT NULL OR phone IS NOT NULL OR email IS NOT NULL"
        )
    ).mappings()
    for row in rows:
        values = {}
        for field in ("aadhaar_last4", "phone", "email"):
            if row[field] is not None:
                values[field] = decrypt_value(row[field])
        connection.execute(
            sa.text(
                "UPDATE applicants SET aadhaar_last4 = :aadhaar_last4, "
                "phone = :phone, email = :email WHERE id = :id"
            ),
            {
                "id": row["id"],
                "aadhaar_last4": values.get("aadhaar_last4", row["aadhaar_last4"]),
                "phone": values.get("phone", row["phone"]),
                "email": values.get("email", row["email"]),
            },
        )
    op.alter_column(
        "applicants", "aadhaar_last4", existing_type=sa.String(128), type_=sa.String(4)
    )
    op.alter_column(
        "applicants", "phone", existing_type=sa.String(512), type_=sa.String(32)
    )
    op.alter_column(
        "applicants", "email", existing_type=sa.String(512), type_=sa.String(320)
    )
