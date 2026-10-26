from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ActionInspectRequest(BaseModel):
    task_id: UUID
    proposed_tool: str
    proposed_action: str
    tool_parameters: dict[str, Any] = Field(default_factory=dict)
    source_context_ids: list[str] = Field(default_factory=list)
    data_classification: str = "internal"
    target_destination: str | None = None
    idempotency_key: str = Field(min_length=8)
    bypass_attempt: bool = False


class ActionInspectResponse(BaseModel):
    action_id: str
    status: str
    decision: str
    risk_score: int
    risk_breakdown: dict[str, Any] | None = None
    triggered_rules: list[str]
    reasons: list[str]
    approval_id: str | None = None
    grant_issued: bool = False


class ActionOut(BaseModel):
    id: UUID
    task_id: UUID
    original_user_intent: str
    proposed_tool: str
    proposed_action: str
    tool_parameters: dict[str, Any]
    parameter_hash: str
    data_classification: str
    target_destination: str | None
    status: str
    risk_score: int | None
    risk_breakdown: dict[str, Any] | None
    policy_version: str
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class ExecuteResponse(BaseModel):
    execution_id: str
    status: str
    result_summary: dict[str, Any] | None = None
