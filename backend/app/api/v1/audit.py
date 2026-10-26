from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import verify_audit_chain
from app.database import get_db
from app.models.audit import AuditEvent
from app.models.user import User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events")
def list_events(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    events = (
        db.query(AuditEvent)
        .order_by(AuditEvent.sequence.desc())
        .offset(offset)
        .limit(min(limit, 500))
        .all()
    )
    return [
        {
            "id": str(e.id),
            "sequence": e.sequence,
            "event_type": e.event_type,
            "actor_type": e.actor_type,
            "actor_id": e.actor_id,
            "action_request_id": str(e.action_request_id) if e.action_request_id else None,
            "details": e.details,
            "previous_event_hash": e.previous_event_hash,
            "event_hash": e.event_hash,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


@router.get("/events/{event_id}")
def get_event(event_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    e = db.get(AuditEvent, event_id)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    return {
        "id": str(e.id),
        "sequence": e.sequence,
        "event_type": e.event_type,
        "actor_type": e.actor_type,
        "actor_id": e.actor_id,
        "action_request_id": str(e.action_request_id) if e.action_request_id else None,
        "details": e.details,
        "previous_event_hash": e.previous_event_hash,
        "event_hash": e.event_hash,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/verify")
def verify(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return verify_audit_chain(db)
