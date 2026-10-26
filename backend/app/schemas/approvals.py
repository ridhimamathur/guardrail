from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ApprovalDecisionRequest(BaseModel):
    comment: str | None = None


class ApprovalOut(BaseModel):
    id: UUID
    action_request_id: UUID
    parameter_hash: str
    policy_version: str
    status: str
    expires_at: datetime
    created_at: datetime
    action: dict[str, Any] | None = None

    model_config = {"from_attributes": True}
