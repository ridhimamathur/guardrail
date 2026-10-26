from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    intent: str = Field(min_length=3)
    demo_scenario: str | None = Field(default=None, pattern="^[ABCabc]?$")


class TaskOut(BaseModel):
    id: UUID
    original_intent: str
    status: str
    session_id: UUID
    agent_id: UUID
    demo_scenario: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskRunResult(BaseModel):
    task_id: UUID
    status: str
    steps: list[dict]
    message: str
