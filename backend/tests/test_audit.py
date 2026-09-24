import uuid
from datetime import UTC, datetime

from app.audit.service import hash_row


def test_row_hash_changes_when_audit_data_is_tampered() -> None:
    created_at = datetime.now(UTC)
    values = {
        "actor_id": uuid.uuid4(),
        "actor_role": "ADMIN",
        "action": "POST /api/v1/auth/officers [201]",
        "entity_type": "HTTP_REQUEST",
        "entity_id": uuid.uuid4(),
        "before": None,
        "after": {"status": 201},
        "reason": None,
        "ip": "127.0.0.1",
        "request_id": "request-1",
        "created_at": created_at,
        "prev_hash": None,
    }
    original = hash_row(**values)
    values["after"] = {"status": 500}
    assert hash_row(**values) != original
