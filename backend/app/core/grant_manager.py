"""One-time HMAC-signed execution grants."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from app.config import get_settings
from app.core.security import canonical_json, hmac_sign, hmac_verify, new_nonce, utcnow


@dataclass
class ExecutionGrant:
    action_id: str
    parameter_hash: str
    policy_version: str
    grant_nonce: str
    expires_at: str
    signature: str
    approver_id: str | None = None

    def to_token(self) -> str:
        payload = canonical_json(
            {
                "action_id": self.action_id,
                "parameter_hash": self.parameter_hash,
                "policy_version": self.policy_version,
                "grant_nonce": self.grant_nonce,
                "expires_at": self.expires_at,
                "approver_id": self.approver_id,
            }
        )
        return f"{payload}.{self.signature}"

    @staticmethod
    def from_token(token: str) -> "ExecutionGrant":
        if "." not in token:
            raise ValueError("Invalid grant token format")
        payload, signature = token.rsplit(".", 1)
        import json

        data = json.loads(payload)
        return ExecutionGrant(
            action_id=data["action_id"],
            parameter_hash=data["parameter_hash"],
            policy_version=data["policy_version"],
            grant_nonce=data["grant_nonce"],
            expires_at=data["expires_at"],
            signature=signature,
            approver_id=data.get("approver_id"),
        )


def issue_grant(
    *,
    action_id: str,
    parameter_hash: str,
    policy_version: str | None = None,
    ttl_minutes: int | None = None,
    approver_id: str | None = None,
) -> ExecutionGrant:
    settings = get_settings()
    ttl = ttl_minutes if ttl_minutes is not None else settings.approval_expiry_minutes
    nonce = new_nonce()
    expires = utcnow() + timedelta(minutes=ttl)
    expires_at = expires.isoformat()
    payload = canonical_json(
        {
            "action_id": str(action_id),
            "parameter_hash": parameter_hash,
            "policy_version": policy_version or settings.policy_version,
            "grant_nonce": nonce,
            "expires_at": expires_at,
            "approver_id": approver_id,
        }
    )
    signature = hmac_sign(payload)
    return ExecutionGrant(
        action_id=str(action_id),
        parameter_hash=parameter_hash,
        policy_version=policy_version or settings.policy_version,
        grant_nonce=nonce,
        expires_at=expires_at,
        signature=signature,
        approver_id=approver_id,
    )


@dataclass
class GrantValidation:
    valid: bool
    reason: str = ""


def validate_grant(
    token: str,
    *,
    action_id: str,
    parameter_hash: str,
    policy_version: str,
    already_consumed: bool,
    stored_nonce: str | None,
    approver_id: str | None = None,
) -> GrantValidation:
    try:
        grant = ExecutionGrant.from_token(token)
    except Exception:
        return GrantValidation(False, "Invalid signature or grant format")

    payload = canonical_json(
        {
            "action_id": grant.action_id,
            "parameter_hash": grant.parameter_hash,
            "policy_version": grant.policy_version,
            "grant_nonce": grant.grant_nonce,
            "expires_at": grant.expires_at,
            "approver_id": grant.approver_id,
        }
    )
    if not hmac_verify(payload, grant.signature):
        return GrantValidation(False, "Invalid signature")

    if already_consumed:
        return GrantValidation(False, "Reused grant")

    if stored_nonce and grant.grant_nonce != stored_nonce:
        return GrantValidation(False, "Grant nonce mismatch")

    if grant.action_id != str(action_id):
        return GrantValidation(False, "Grant action_id mismatch")

    if grant.parameter_hash != parameter_hash:
        return GrantValidation(False, "Parameter mismatch")

    if grant.policy_version != policy_version:
        return GrantValidation(False, "Policy version mismatch")

    if grant.approver_id != approver_id:
        return GrantValidation(False, "Approver binding mismatch")

    from datetime import datetime

    expires = datetime.fromisoformat(grant.expires_at)
    if expires.tzinfo is None:
        from datetime import UTC

        expires = expires.replace(tzinfo=UTC)
    if utcnow() > expires:
        return GrantValidation(False, "Expired grant")

    return GrantValidation(True, "ok")


def grant_fields_for_db(grant: ExecutionGrant) -> dict[str, Any]:
    from datetime import datetime

    return {
        "grant_token": grant.to_token(),
        "grant_nonce": grant.grant_nonce,
        "grant_expires_at": datetime.fromisoformat(grant.expires_at),
    }
