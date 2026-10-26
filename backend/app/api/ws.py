"""WebSocket live feed for dashboard updates."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import SessionLocal
from app.models.audit import AuditEvent
from app.models.user import User

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


def _auth_user(token: str, db: Session) -> User | None:
    try:
        payload = decode_access_token(token)
        from uuid import UUID

        return db.get(User, UUID(payload["sub"]))
    except Exception:
        return None


@router.websocket("/ws/live-feed")
async def live_feed(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    db = SessionLocal()
    try:
        user = _auth_user(token or "", db) if token else None
        if not user:
            await websocket.close(code=4401)
            return
        await manager.connect(websocket)
        last_seq = db.query(AuditEvent).order_by(AuditEvent.sequence.desc()).first()
        cursor = last_seq.sequence if last_seq else 0
        await websocket.send_json({"type": "connected", "cursor": cursor})
        try:
            while True:
                # Poll for new audit events (simple Phase 1 approach)
                await asyncio.sleep(1.5)
                events = (
                    db.query(AuditEvent)
                    .filter(AuditEvent.sequence > cursor)
                    .order_by(AuditEvent.sequence.asc())
                    .limit(20)
                    .all()
                )
                for e in events:
                    cursor = e.sequence
                    msg = {
                        "type": "audit_event",
                        "event_type": e.event_type,
                        "sequence": e.sequence,
                        "action_request_id": str(e.action_request_id) if e.action_request_id else None,
                        "details": e.details,
                        "created_at": e.created_at.isoformat() if e.created_at else None,
                    }
                    if e.event_type in {"policy_decision", "blocked_action", "action_proposal"}:
                        msg["type"] = "action_update"
                    elif e.event_type in {"approval_request", "approval_decision"}:
                        msg["type"] = "approval_update"
                    elif e.event_type in {"tool_execution", "tool_result"}:
                        msg["type"] = "execution_update"
                    await websocket.send_json(msg)
                # Keepalive / allow client ping
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                    if data == "ping":
                        await websocket.send_json({"type": "pong"})
                except asyncio.TimeoutError:
                    pass
        except WebSocketDisconnect:
            manager.disconnect(websocket)
    finally:
        db.close()
