"""End-to-end demo workflow runner using mock agent + PEP + Tool Proxy."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.agent import get_llm_provider
from app.core.pep import execute_action, ingest_tool_response_context, inspect_action
from app.core.security import new_nonce
from app.models.action import ActionRequest
from app.models.enums import ActionStatus, Decision, TaskStatus
from app.models.task import UserRequest
from app.models.user import User


def run_task_workflow(db: Session, *, task: UserRequest, user: User, auto_execute: bool = True) -> dict[str, Any]:
    """Run mock agent proposals through GuardRAIL until done or blocked/pending approval."""
    provider = get_llm_provider()
    history: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    task.status = TaskStatus.RUNNING
    db.commit()

    for _ in range(8):
        proposal = provider.propose_next_action(
            intent=task.original_intent,
            scenario=task.demo_scenario,
            history=history,
        )
        if proposal.get("done") or not proposal.get("proposed_action"):
            task.status = TaskStatus.COMPLETED
            db.commit()
            break

        inspect_result = inspect_action(
            db,
            user_id=user.id,
            task_id=task.id,
            proposed_tool=proposal["tool"],
            proposed_action=proposal["proposed_action"],
            tool_parameters=proposal.get("parameters") or {},
            source_context_ids=[],
            data_classification=proposal.get("data_classification") or "internal",
            target_destination=proposal.get("target_destination"),
            idempotency_key=f"{task.id}-{proposal['proposed_action']}-{new_nonce(4)}",
        )
        step: dict[str, Any] = {
            "proposal": proposal,
            "inspect": inspect_result,
            "execution": None,
        }

        decision = inspect_result["decision"]
        action_id = uuid.UUID(inspect_result["action_id"])

        if decision == Decision.BLOCK:
            steps.append(step)
            task.status = TaskStatus.COMPLETED
            db.commit()
            break

        if decision == Decision.REQUIRE_APPROVAL:
            steps.append(step)
            task.status = TaskStatus.RUNNING
            db.commit()
            break

        if decision == Decision.ALLOW and auto_execute and inspect_result.get("grant_issued"):
            execution = execute_action(db, action_id=action_id, actor_id=str(user.id))
            step["execution"] = execution
            # Ingest tool response as context (especially email bodies)
            result = execution.get("result_summary") or {}
            content = ""
            if "body" in result:
                content = str(result["body"])
            elif result:
                content = str(result)[:2000]
            if content:
                ingest_tool_response_context(
                    db,
                    task_id=task.id,
                    content=content,
                    provenance=f"{proposal['tool']}.{proposal['proposed_action']}",
                    is_external=proposal["tool"] == "email",
                )
                db.commit()
            history.append({"proposal": proposal, "result": result})

        steps.append(step)

    else:
        task.status = TaskStatus.COMPLETED
        db.commit()

    return {
        "task_id": str(task.id),
        "status": task.status,
        "steps": steps,
        "message": "Workflow finished or waiting on approval",
    }


def continue_after_approval(db: Session, *, action_id: uuid.UUID, user: User) -> dict[str, Any]:
    action = db.get(ActionRequest, action_id)
    if not action:
        raise ValueError("Action not found")
    if action.status != ActionStatus.APPROVED:
        raise ValueError("Action not approved")
    return execute_action(db, action_id=action_id, actor_id=str(user.id))
