from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.action import ActionRequest
from app.models.approval import ApprovalRequest
from app.models.audit import AuditEvent
from app.models.enums import ActionStatus, ApprovalStatus
from app.models.user import User

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    total = db.query(func.count(ActionRequest.id)).filter(ActionRequest.created_at >= start).scalar() or 0
    allowed = (
        db.query(func.count(ActionRequest.id))
        .filter(ActionRequest.created_at >= start, ActionRequest.status.in_([ActionStatus.ALLOW, ActionStatus.SUCCEEDED, ActionStatus.APPROVED, ActionStatus.EXECUTING]))
        .scalar()
        or 0
    )
    blocked = (
        db.query(func.count(ActionRequest.id))
        .filter(ActionRequest.created_at >= start, ActionRequest.status == ActionStatus.BLOCKED)
        .scalar()
        or 0
    )
    pending = (
        db.query(func.count(ApprovalRequest.id)).filter(ApprovalRequest.status == ApprovalStatus.PENDING).scalar() or 0
    )

    risk_buckets = {"low_0_39": 0, "mid_40_69": 0, "high_70_100": 0}
    scores = db.query(ActionRequest.risk_score).filter(ActionRequest.created_at >= start).all()
    for (score,) in scores:
        if score is None:
            continue
        if score < 40:
            risk_buckets["low_0_39"] += 1
        elif score < 70:
            risk_buckets["mid_40_69"] += 1
        else:
            risk_buckets["high_70_100"] += 1

    recent = (
        db.query(AuditEvent)
        .order_by(AuditEvent.sequence.desc())
        .limit(10)
        .all()
    )
    return {
        "total_actions_today": total,
        "allowed_actions": allowed,
        "blocked_actions": blocked,
        "pending_approvals": pending,
        "risk_distribution": risk_buckets,
        "recent_security_events": [
            {
                "sequence": e.sequence,
                "event_type": e.event_type,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in recent
        ],
    }
