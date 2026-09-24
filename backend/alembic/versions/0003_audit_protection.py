from collections.abc import Sequence

from alembic import op

revision: str = "0003_audit_protection"
down_revision: str | None = "0002_auth_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """)
    op.execute("""
        DROP TRIGGER IF EXISTS audit_logs_append_only ON audit_logs;
        CREATE TRIGGER audit_logs_append_only
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();
        """)
    op.execute("REVOKE UPDATE, DELETE ON audit_logs FROM CURRENT_USER")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_append_only ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_mutation()")
