import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


class Entity(Base):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Entity):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('APPLICANT', 'SCRUTINY_OFFICER', 'VERIFYING_OFFICER', "
            "'COMMITTEE_MEMBER', 'ADMIN')",
            name="ck_users_role",
        ),
    )

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Scheme(Entity):
    __tablename__ = "schemes"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SchemeVersion(Base):
    __tablename__ = "scheme_versions"
    __table_args__ = (
        CheckConstraint(
            "version_number > 0", name="ck_scheme_versions_positive_version"
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'RETIRED')",
            name="ck_scheme_versions_status",
        ),
        Index(
            "ix_scheme_versions_scheme_version",
            "scheme_id",
            "version_number",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    rules: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    form_schema: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    ui_hints: Mapped[dict[str, Any]] = mapped_column(
        JsonType, default=dict, nullable=False
    )
    eligibility_rules: Mapped[dict[str, Any]] = mapped_column(
        JsonType, default=dict, nullable=False
    )
    selection_rules: Mapped[dict[str, Any]] = mapped_column(
        JsonType, default=dict, nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", nullable=False)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    open_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SchemeDocumentRequired(Entity):
    __tablename__ = "scheme_documents_required"
    __table_args__ = (
        Index("ix_scheme_documents_required_version", "scheme_version_id"),
    )

    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_versions.id", ondelete="CASCADE"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    validity_rules: Mapped[dict[str, Any]] = mapped_column(
        JsonType, default=dict, nullable=False
    )


class Applicant(Entity):
    __tablename__ = "applicants"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aadhaar_last4: Mapped[str | None] = mapped_column(String(4))
    aadhaar_hash: Mapped[str | None] = mapped_column(String(128))
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(320))
    address: Mapped[dict[str, Any] | None] = mapped_column(JsonType)


class Application(Entity):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'AUTO_VALIDATION', 'DEFICIENT', "
            "'RESUBMITTED', 'UNDER_SCRUTINY', 'OFFICER_VERIFIED', 'SELECTED', "
            "'NOT_SELECTED', 'WAITLISTED', 'APPROVED', 'AWARDED', 'CLOSED')",
            name="ck_applications_status",
        ),
        Index("ix_applications_status", "status"),
        Index("ix_applications_scheme_version", "scheme_version_id"),
        Index("ix_applications_applicant", "applicant_id"),
    )

    applicant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applicants.id", ondelete="RESTRICT"), nullable=False
    )
    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_versions.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False)
    form_data: Mapped[dict[str, Any]] = mapped_column(
        JsonType, default=dict, nullable=False
    )
    correction_round: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correction_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    scrutiny_officer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    verifying_officer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"
    __table_args__ = (
        Index(
            "ix_application_status_history_application_created",
            "application_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str | None] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ApplicationDocument(Entity):
    __tablename__ = "application_documents"
    __table_args__ = (
        CheckConstraint("size >= 0", name="ck_application_documents_size"),
        CheckConstraint(
            "ocr_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'REVIEW_REQUIRED')",
            name="ck_application_documents_ocr_status",
        ),
        Index("ix_application_documents_application", "application_id"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    object_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    ocr_status: Mapped[str] = mapped_column(
        String(32), default="PENDING", nullable=False
    )


class ExtractedField(Entity):
    __tablename__ = "extracted_fields"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_extracted_fields_confidence",
        ),
        Index("ix_extracted_fields_document", "document_id"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_documents.id", ondelete="CASCADE"), nullable=False
    )
    field: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    source_bbox: Mapped[dict[str, Any] | None] = mapped_column(JsonType)


class Deficiency(Entity):
    __tablename__ = "deficiencies"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'NEEDS_REVIEW', 'BLOCKER', 'WARNING')",
            name="ck_deficiencies_severity",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'RESOLVED', 'WAIVED')", name="ck_deficiencies_status"
        ),
        CheckConstraint(
            "raised_by_type IN ('SYSTEM', 'OFFICER')",
            name="ck_deficiencies_raised_by_type",
        ),
        Index("ix_deficiencies_application", "application_id"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False)
    raised_by_type: Mapped[str] = mapped_column(String(16), nullable=False)
    raised_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    field: Mapped[str | None] = mapped_column(String(128))
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("application_documents.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewAction(Entity):
    __tablename__ = "review_actions"
    __table_args__ = (Index("ix_review_actions_application", "application_id"),)

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    officer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)
    override_source: Mapped[str] = mapped_column(
        String(16), default="NONE", nullable=False
    )


class AiRecommendation(Entity):
    __tablename__ = "ai_recommendations"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_ai_recommendations_confidence",
        ),
        Index("ix_ai_recommendations_application", "application_id"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    response_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    output: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))


class Selection(Entity):
    __tablename__ = "selections"

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    selected_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    rank: Mapped[int | None] = mapped_column(Integer)
    remarks: Mapped[str | None] = mapped_column(Text)
    list_status: Mapped[str] = mapped_column(
        String(16), default="PROVISIONAL", nullable=False
    )
    score: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JsonType, default=dict, nullable=False
    )
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Award(Entity):
    __tablename__ = "awards"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_awards_amount"),
        CheckConstraint(
            "status IN ('PLANNED', 'DISBURSED', 'ON_HOLD', 'CANCELLED')",
            name="ck_awards_status",
        ),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    instalments: Mapped[list[dict[str, Any]]] = mapped_column(
        JsonType, default=list, nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), default="PLANNED", nullable=False)
    hold_reason: Mapped[str | None] = mapped_column(Text)
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FollowupRequirement(Entity):
    __tablename__ = "followup_requirements"
    __table_args__ = (
        CheckConstraint(
            "status IN ('UPCOMING', 'SUBMITTED', 'ACCEPTED', 'REJECTED', 'OVERDUE')",
            name="ck_followup_requirements_status",
        ),
        Index("ix_followup_requirements_due_status", "due_date", "status"),
    )

    award_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("awards.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    requirement_type: Mapped[str] = mapped_column(String(64), default="DOCUMENT")
    validation_schema: Mapped[dict[str, Any]] = mapped_column(
        JsonType, default=dict, nullable=False
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="UPCOMING", nullable=False)


class FollowupSubmission(Entity):
    __tablename__ = "followup_submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SUBMITTED', 'ACCEPTED', 'REJECTED')",
            name="ck_followup_submissions_status",
        ),
    )

    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("followup_requirements.id", ondelete="CASCADE"), nullable=False
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    data: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="SUBMITTED", nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("application_documents.id", ondelete="SET NULL")
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_remarks: Mapped[str | None] = mapped_column(Text)


class Notification(Entity):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('SMS', 'EMAIL', 'IN_APP')", name="ck_notifications_channel"
        ),
        CheckConstraint(
            "status IN ('PENDING', 'SENT', 'FAILED')", name="ck_notifications_status"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    template_key: Mapped[str | None] = mapped_column(String(64))
    locale: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))


class NotificationPreference(Entity):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    locale: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str | None] = mapped_column(String(32))
    ip: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    before: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    after: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    reason: Mapped[str | None] = mapped_column(Text)
    prev_hash: Mapped[str | None] = mapped_column(String(64))
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
