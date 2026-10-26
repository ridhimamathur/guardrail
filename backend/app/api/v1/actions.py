from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.pep import execute_action, inspect_action
from app.database import get_db
from app.models.action import ActionRequest, PolicyDecision, ToolExecution
from app.models.approval import ApprovalDecision, ApprovalRequest
from app.models.audit import AuditEvent
from app.models.context import ContextSource
from app.models.user import User
from app.schemas.actions import ActionInspectRequest, ActionInspectResponse, ActionOut, ExecuteResponse

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("")
def list_actions(limit: int = 100, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    """Recent actions visible to the current user or a reviewer."""
    q = db.query(ActionRequest).order_by(ActionRequest.created_at.desc())
    if not ({"manager", "security_admin"} & {r.name for r in user.roles}):
        q = q.filter(ActionRequest.user_id == user.id)
    return [
        {"id": str(a.id), "task_id": str(a.task_id), "tool": a.proposed_tool,
         "action": a.proposed_action, "status": a.status, "risk_score": a.risk_score,
         "decision_params": a.tool_parameters, "created_at": a.created_at.isoformat() if a.created_at else None}
        for a in q.limit(min(max(limit, 1), 500)).all()
    ]


def _can_view_action(action: ActionRequest, user: User) -> bool:
    return action.user_id == user.id or bool({"manager", "security_admin"} & {r.name for r in user.roles})


@router.post("/inspect", response_model=ActionInspectResponse)
def inspect(body: ActionInspectRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = inspect_action(
        db,
        user_id=user.id,
        task_id=body.task_id,
        proposed_tool=body.proposed_tool,
        proposed_action=body.proposed_action,
        tool_parameters=body.tool_parameters,
        source_context_ids=body.source_context_ids,
        data_classification=body.data_classification,
        target_destination=body.target_destination,
        idempotency_key=body.idempotency_key,
        bypass_attempt=body.bypass_attempt,
    )
    return ActionInspectResponse(**result)


@router.get("/{action_id}", response_model=dict)
def get_action(action_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    action = db.get(ActionRequest, action_id)
    if not action or not _can_view_action(action, user):
        raise HTTPException(status_code=404, detail="Action not found")
    decision = (
        db.query(PolicyDecision)
        .filter(PolicyDecision.action_request_id == action_id)
        .order_by(PolicyDecision.created_at.desc())
        .first()
    )
    contexts = []
    if action.source_context_ids:
        ids = [UUID(x) for x in action.source_context_ids]
        contexts = db.query(ContextSource).filter(ContextSource.id.in_(ids)).all()
    return {
        "action": ActionOut.model_validate(action).model_dump(),
        "decision": {
            "decision": decision.decision if decision else None,
            "triggered_rules": decision.triggered_rules if decision else [],
            "reasons": decision.reasons if decision else [],
            "risk_score": decision.risk_score if decision else action.risk_score,
        },
        "contexts": [
            {
                "id": str(c.id),
                "source_type": c.source_type,
                "trust_level": c.trust_level,
                "injection_risk_score": c.injection_risk_score,
                "content_preview": c.content_preview,
                "provenance": c.provenance,
            }
            for c in contexts
        ],
        "executions": [
            {
                "id": str(x.id),
                "status": x.status,
                "tool": x.tool_name,
                "action": x.action_name,
                "result_summary": x.result_summary,
                "started_at": x.started_at.isoformat() if x.started_at else None,
                "completed_at": x.completed_at.isoformat() if x.completed_at else None,
            }
            for x in db.query(ToolExecution)
            .filter(ToolExecution.action_request_id == action_id)
            .order_by(ToolExecution.started_at.asc())
            .all()
        ],
    }


@router.get("/{action_id}/timeline", response_model=list)
def action_timeline(action_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list:
    action = db.get(ActionRequest, action_id)
    if not action or not _can_view_action(action, user):
        raise HTTPException(status_code=404, detail="Action not found")
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.action_request_id == action_id)
        .order_by(AuditEvent.sequence.asc())
        .all()
    )
    return [
        {
            "sequence": e.sequence,
            "event_type": e.event_type,
            "actor_type": e.actor_type,
            "actor_id": e.actor_id,
            "details": e.details,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "event_hash": e.event_hash,
        }
        for e in events
    ]


@router.post("/{action_id}/execute", response_model=ExecuteResponse)
def execute(action_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ExecuteResponse:
    """Execute frozen action from DB. Does not accept arbitrary tool parameters."""
    action = db.get(ActionRequest, action_id)
    if not action or not _can_view_action(action, user):
        raise HTTPException(status_code=404, detail="Action not found")
    result = execute_action(db, action_id=action_id, actor_id=str(user.id))
    return ExecuteResponse(**result)
