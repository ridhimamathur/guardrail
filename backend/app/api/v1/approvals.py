from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.config import get_settings
from app.core.audit import append_audit_event
from app.core.grant_manager import grant_fields_for_db, issue_grant
from app.core.security import new_nonce, parameter_hash, utcnow
from app.database import get_db
from app.models.action import ActionRequest
from app.models.approval import ApprovalDecision, ApprovalRequest
from app.models.enums import ActionStatus, ApprovalStatus, RoleName
from app.models.user import User
from app.schemas.approvals import ApprovalDecisionRequest

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("")
def list_approvals(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleName.MANAGER, RoleName.SECURITY_ADMIN)),
) -> list[dict]:
    q = db.query(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
    if status_filter:
        q = q.filter(ApprovalRequest.status == status_filter)
    rows = q.limit(100).all()
    out = []
    for row in rows:
        action = db.get(ActionRequest, row.action_request_id)
        out.append(
            {
                "id": str(row.id),
                "action_request_id": str(row.action_request_id),
                "parameter_hash": row.parameter_hash,
                "policy_version": row.policy_version,
                "status": row.status,
                "expires_at": row.expires_at.isoformat(),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "action": {
                    "tool": action.proposed_tool if action else None,
                    "action": action.proposed_action if action else None,
                    "parameters": action.tool_parameters if action else None,
                    "target_destination": action.target_destination if action else None,
                    "risk_score": action.risk_score if action else None,
                    "data_classification": action.data_classification if action else None,
                    "original_user_intent": action.original_user_intent if action else None,
                    "risk_breakdown": action.risk_breakdown if action else None,
                },
            }
        )
    return out


@router.get("/{approval_id}")
def get_approval(
    approval_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleName.MANAGER, RoleName.SECURITY_ADMIN)),
) -> dict:
    row = db.get(ApprovalRequest, approval_id)
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    action = db.get(ActionRequest, row.action_request_id)
    return {
        "id": str(row.id),
        "status": row.status,
        "parameter_hash": row.parameter_hash,
        "policy_version": row.policy_version,
        "expires_at": row.expires_at.isoformat(),
        "action": {
            "id": str(action.id) if action else None,
            "tool": action.proposed_tool if action else None,
            "action": action.proposed_action if action else None,
            "parameters": action.tool_parameters if action else None,
            "recipient": action.target_destination if action else None,
            "file": (action.tool_parameters or {}).get("object_name") if action else None,
            "risk_score": action.risk_score if action else None,
            "risk_breakdown": action.risk_breakdown if action else None,
            "original_user_intent": action.original_user_intent if action else None,
        },
    }


@router.post("/{approval_id}/approve")
def approve(
    approval_id: UUID,
    body: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleName.MANAGER, RoleName.SECURITY_ADMIN)),
) -> dict:
    settings = get_settings()
    row = db.get(ApprovalRequest, approval_id)
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    if row.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Approval status is {row.status}")
    expires = row.expires_at
    if expires.tzinfo is None:
        from datetime import UTC

        expires = expires.replace(tzinfo=UTC)
    if utcnow() > expires:
        row.status = ApprovalStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=400, detail="Approval expired")

    action = db.get(ActionRequest, row.action_request_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    # P7: bind to exact parameters
    if parameter_hash(action.tool_parameters) != row.parameter_hash:
        raise HTTPException(status_code=403, detail="Parameter mismatch — approval binding failed")
    if action.policy_version != row.policy_version or row.policy_version != settings.policy_version:
        raise HTTPException(status_code=403, detail="Policy version mismatch")

    decision = ApprovalDecision(
        approval_request_id=row.id,
        approver_id=user.id,
        decision="approved",
        comment=body.comment,
        approval_nonce=new_nonce(),
    )
    db.add(decision)
    row.status = ApprovalStatus.APPROVED
    action.status = ActionStatus.APPROVED

    grant = issue_grant(
        action_id=str(action.id),
        parameter_hash=action.parameter_hash,
        policy_version=action.policy_version,
        ttl_minutes=settings.approval_expiry_minutes,
        approver_id=str(user.id),
    )
    fields = grant_fields_for_db(grant)
    action.grant_token = fields["grant_token"]
    action.grant_nonce = fields["grant_nonce"]
    action.grant_expires_at = fields["grant_expires_at"]

    append_audit_event(
        db,
        event_type="approval_decision",
        actor_type="user",
        actor_id=str(user.id),
        action_request_id=action.id,
        details={"decision": "approved", "approval_id": str(row.id), "comment": body.comment},
    )
    append_audit_event(
        db,
        event_type="execution_grant_creation",
        actor_type="system",
        actor_id="grant_manager",
        action_request_id=action.id,
        details={"grant_nonce": action.grant_nonce, "bound_to_approval": str(row.id)},
    )
    db.commit()
    return {"status": "approved", "action_id": str(action.id), "grant_issued": True}


@router.post("/{approval_id}/deny")
def deny(
    approval_id: UUID,
    body: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleName.MANAGER, RoleName.SECURITY_ADMIN)),
) -> dict:
    row = db.get(ApprovalRequest, approval_id)
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    if row.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Approval status is {row.status}")

    action = db.get(ActionRequest, row.action_request_id)
    decision = ApprovalDecision(
        approval_request_id=row.id,
        approver_id=user.id,
        decision="denied",
        comment=body.comment,
        approval_nonce=new_nonce(),
    )
    db.add(decision)
    row.status = ApprovalStatus.DENIED
    if action:
        action.status = ActionStatus.BLOCKED
        append_audit_event(
            db,
            event_type="approval_decision",
            actor_type="user",
            actor_id=str(user.id),
            action_request_id=action.id,
            details={"decision": "denied", "approval_id": str(row.id), "comment": body.comment},
        )
    db.commit()
    return {"status": "denied", "action_id": str(action.id) if action else None}
