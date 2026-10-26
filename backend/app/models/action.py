import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

ACTION_STATUSES = (
    "PROPOSED",
    "INSPECTING",
    "ALLOW",
    "APPROVAL_PENDING",
    "APPROVED",
    "EXECUTING",
    "SUCCEEDED",
    "FAILED",
    "BLOCKED",
    "EXPIRED",
    "CANCELLED",
)


class ActionRequest(Base):
    __tablename__ = "action_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PROPOSED','INSPECTING','ALLOW','APPROVAL_PENDING','APPROVED',"
            "'EXECUTING','SUCCEEDED','FAILED','BLOCKED','EXPIRED','CANCELLED')",
            name="ck_action_status",
        ),
        CheckConstraint("risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)", name="ck_risk_score"),
        UniqueConstraint("idempotency_key", name="uq_action_idempotency"),
        UniqueConstraint("request_nonce", name="uq_action_nonce"),
        UniqueConstraint("grant_nonce", name="uq_grant_nonce"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_sessions.id"), nullable=False
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_requests.id"), nullable=False, index=True
    )
    original_user_intent: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_tool: Mapped[str] = mapped_column(String(64), nullable=False)
    proposed_action: Mapped[str] = mapped_column(String(64), nullable=False)
    tool_parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    parameter_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_context_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    data_classification: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    target_destination: Mapped[str | None] = mapped_column(String(512), nullable=True)
    request_nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PROPOSED")
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    grant_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    grant_nonce: Mapped[str | None] = mapped_column(String(64), nullable=True)
    grant_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    grant_consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PolicyDecision(Base):
    __tablename__ = "policy_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('ALLOW','REQUIRE_APPROVAL','BLOCK')",
            name="ck_policy_decision",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action_requests.id"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    triggered_rules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action_requests.id"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    action_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
