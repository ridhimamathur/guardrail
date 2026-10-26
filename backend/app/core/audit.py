"""Tamper-evident chained audit log (SHA-256)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import canonical_json, sha256_hex, utcnow
from app.models.audit import AuditEvent

GENESIS_HASH = "0" * 64

SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "authorization", "grant_token"}


def redact(details: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for k, v in (details or {}).items():
        if k.lower() in SENSITIVE_KEYS or any(s in k.lower() for s in ("password", "secret", "token", "api_key")):
            redacted[k] = "[REDACTED]"
        elif isinstance(v, dict):
            redacted[k] = redact(v)
        else:
            redacted[k] = v
    return redacted


def _hash_details(details: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in details.items() if k != "_hash_timestamp"}


def compute_event_hash(
    previous_event_hash: str,
    *,
    event_type: str,
    actor_type: str,
    actor_id: str,
    action_request_id: str | None,
    details: dict[str, Any],
    timestamp: str,
) -> str:
    material = previous_event_hash + canonical_json(
        {
            "event_type": event_type,
            "actor_type": actor_type,
            "actor_id": str(actor_id),
            "action_request_id": action_request_id,
            "details": _hash_details(details),
            "timestamp": timestamp,
        }
    )
    return sha256_hex(material)


def append_audit_event(
    db: Session,
    *,
    event_type: str,
    actor_type: str,
    actor_id: str,
    details: dict[str, Any] | None = None,
    action_request_id: uuid.UUID | None = None,
) -> AuditEvent:
    last = db.query(AuditEvent).order_by(AuditEvent.sequence.desc()).first()
    prev_hash = last.event_hash if last else GENESIS_HASH
    next_seq = (last.sequence + 1) if last else 1
    ts = utcnow().isoformat()
    safe_details = redact(details or {})
    safe_details["_hash_timestamp"] = ts
    event_hash = compute_event_hash(
        prev_hash,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=str(actor_id),
        action_request_id=str(action_request_id) if action_request_id else None,
        details=safe_details,
        timestamp=ts,
    )
    event = AuditEvent(
        sequence=next_seq,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=str(actor_id),
        action_request_id=action_request_id,
        details=safe_details,
        previous_event_hash=prev_hash,
        event_hash=event_hash,
    )
    db.add(event)
    db.flush()
    return event


def verify_audit_chain(db: Session) -> dict[str, Any]:
    events = db.query(AuditEvent).order_by(AuditEvent.sequence.asc()).all()
    prev = GENESIS_HASH
    expected_seq = 1
    for event in events:
        if event.sequence != expected_seq:
            return {
                "valid": False,
                "checked_events": event.sequence,
                "first_break_sequence": event.sequence,
                "reason": "sequence_gap",
            }
        if event.previous_event_hash != prev:
            return {
                "valid": False,
                "checked_events": event.sequence,
                "first_break_sequence": event.sequence,
                "reason": "chain_break",
            }
        ts = (event.details or {}).get("_hash_timestamp")
        if not ts:
            return {
                "valid": False,
                "checked_events": event.sequence,
                "first_break_sequence": event.sequence,
                "reason": "missing_hash_timestamp",
            }
        expected = compute_event_hash(
            prev,
            event_type=event.event_type,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            action_request_id=str(event.action_request_id) if event.action_request_id else None,
            details=event.details or {},
            timestamp=ts,
        )
        if expected != event.event_hash:
            return {
                "valid": False,
                "checked_events": event.sequence,
                "first_break_sequence": event.sequence,
                "reason": "hash_mismatch",
            }
        prev = event.event_hash
        expected_seq += 1
    return {"valid": True, "checked_events": len(events), "first_break_sequence": None}


def next_sequence(db: Session) -> int:
    value = db.query(func.coalesce(func.max(AuditEvent.sequence), 0)).scalar()
    return int(value) + 1
