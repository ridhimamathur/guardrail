from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import append_audit_event
from app.core.pep import ingest_user_context
from app.core.security import utcnow
from app.core.workflow import run_task_workflow
from app.database import get_db
from app.models.action import ActionRequest
from app.models.agent import Agent, AgentSession
from app.models.task import UserRequest
from app.models.user import User
from app.schemas.tasks import TaskCreate, TaskOut, TaskRunResult

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut)
def create_task(body: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> TaskOut:
    agent = db.query(Agent).filter(Agent.name == "guardrail-demo-agent", Agent.is_active.is_(True)).first()
    if not agent:
        raise HTTPException(status_code=500, detail="Demo agent not seeded")

    session = AgentSession(
        agent_id=agent.id,
        user_id=user.id,
        status="active",
        expires_at=utcnow() + timedelta(hours=8),
    )
    db.add(session)
    db.flush()

    scenario = body.demo_scenario.upper() if body.demo_scenario else None
    task = UserRequest(
        user_id=user.id,
        agent_id=agent.id,
        session_id=session.id,
        original_intent=body.intent,
        demo_scenario=scenario,
        status="pending",
    )
    db.add(task)
    db.flush()
    session.task_id = task.id

    ingest_user_context(db, task)
    append_audit_event(
        db,
        event_type="task_creation",
        actor_type="user",
        actor_id=str(user.id),
        details={"task_id": str(task.id), "demo_scenario": scenario},
    )
    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)


@router.get("/{task_id}", response_model=dict)
def get_task(task_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    task = db.get(UserRequest, task_id)
    if not task or task.user_id != user.id:
        # managers/security can view all
        roles = {r.name for r in user.roles}
        if not task or ("manager" not in roles and "security_admin" not in roles and task.user_id != user.id):
            raise HTTPException(status_code=404, detail="Task not found")
    actions = (
        db.query(ActionRequest)
        .filter(ActionRequest.task_id == task_id)
        .order_by(ActionRequest.created_at.asc())
        .all()
    )
    return {
        "task": TaskOut.model_validate(task).model_dump(),
        "actions": [
            {
                "id": str(a.id),
                "tool": a.proposed_tool,
                "action": a.proposed_action,
                "status": a.status,
                "risk_score": a.risk_score,
                "decision_params": a.tool_parameters,
            }
            for a in actions
        ],
    }


@router.post("/{task_id}/run", response_model=TaskRunResult)
def run_task(task_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> TaskRunResult:
    task = db.get(UserRequest, task_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    result = run_task_workflow(db, task=task, user=user, auto_execute=True)
    return TaskRunResult(
        task_id=task.id,
        status=result["status"],
        steps=result["steps"],
        message=result["message"],
    )
