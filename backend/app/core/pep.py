"""Policy Enforcement Point — inspect actions, issue grants, coordinate execution."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.audit import append_audit_event
from app.core.context_analyzer import analyze_context
from app.core.grant_manager import grant_fields_for_db, issue_grant, validate_grant
from app.core.policy_engine import PolicyInput, evaluate_policy
from app.core.security import new_nonce, parameter_hash, utcnow
from app.models.action import ActionRequest, PolicyDecision, ToolExecution
from app.models.agent import AgentCapability, AgentSession
from app.models.approval import ApprovalDecision, ApprovalRequest
from app.models.context import ContextAnalysisResult, ContextSource
from app.models.enums import ActionStatus, ApprovalStatus, Decision, ExecutionStatus, TrustLevel
from app.models.task import UserRequest
from app.tool_proxy import get_tool_proxy


def _session_valid(db: Session, session_id: uuid.UUID) -> bool:
    session = db.get(AgentSession, session_id)
    if not session:
        return False
    if session.status != "active":
        return False
    expires = session.expires_at
    if expires.tzinfo is None:
        from datetime import UTC

        expires = expires.replace(tzinfo=UTC)
    return utcnow() <= expires


def inspect_action(
    db: Session,
    *,
    user_id: uuid.UUID,
    task_id: uuid.UUID,
    proposed_tool: str,
    proposed_action: str,
    tool_parameters: dict[str, Any],
    source_context_ids: list[str] | None,
    data_classification: str,
    target_destination: str | None,
    idempotency_key: str,
    bypass_attempt: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    existing = db.query(ActionRequest).filter(ActionRequest.idempotency_key == idempotency_key).first()
    if existing:
        raise HTTPException(status_code=409, detail="Duplicate idempotency key")

    task = db.get(UserRequest, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="Task does not belong to user")

    session_ok = _session_valid(db, task.session_id)

    # Load context sources
    try:
        ctx_ids = [uuid.UUID(x) for x in (source_context_ids or [])]
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid source context ID") from exc
    contexts = (
        db.query(ContextSource)
        .filter(ContextSource.id.in_(ctx_ids), ContextSource.task_id == task_id)
        .all()
        if ctx_ids else []
    )
    # Include every context attached to this task even if the agent supplied
    # a subset. This prevents an agent from hiding hostile tool output by
    # selecting only trusted context IDs.
    task_contexts = (
        db.query(ContextSource)
        .filter(ContextSource.task_id == task_id)
        .order_by(ContextSource.received_at.asc())
        .all()
    )
    context_by_id = {c.id: c for c in [*task_contexts, *contexts]}
    contexts = sorted(context_by_id.values(), key=lambda c: c.received_at)

    untrusted = any(c.trust_level == TrustLevel.UNTRUSTED for c in contexts)
    injection: list[str] = []
    snippets: list[str] = []
    trust_levels = [c.trust_level for c in contexts]
    for c in contexts:
        if c.injection_risk_score > 0:
            injection.append(f"source:{c.id}")
        if c.trust_level == TrustLevel.UNTRUSTED and c.content_preview:
            snippets.append(c.content_preview)
            # Re-analyze preview for indicators
            analysis = analyze_context(c.content_preview, is_external=True)
            injection.extend(analysis.injection_indicators)

    append_audit_event(
        db,
        event_type="action_proposal",
        actor_type="agent",
        actor_id=str(task.agent_id),
        details={
            "tool": proposed_tool,
            "action": proposed_action,
            "task_id": str(task_id),
        },
    )

    action = ActionRequest(
        user_id=user_id,
        agent_id=task.agent_id,
        session_id=task.session_id,
        task_id=task_id,
        original_user_intent=task.original_intent,
        proposed_tool=proposed_tool,
        proposed_action=proposed_action,
        tool_parameters=tool_parameters or {},
        parameter_hash=parameter_hash(tool_parameters or {}),
        source_context_ids=[str(c.id) for c in contexts],
        data_classification=data_classification,
        target_destination=target_destination,
        request_nonce=new_nonce(),
        idempotency_key=idempotency_key,
        policy_version=settings.policy_version,
        status=ActionStatus.INSPECTING,
        expires_at=utcnow() + timedelta(minutes=settings.action_expiry_minutes),
    )
    db.add(action)
    db.flush()

    append_audit_event(
        db,
        event_type="context_analysis",
        actor_type="system",
        actor_id="pep",
        action_request_id=action.id,
        details={
            "untrusted": untrusted,
            "injection_indicators": list(set(injection)),
            "context_count": len(contexts),
        },
    )

    policy = evaluate_policy(
        db,
        PolicyInput(
            agent_id=task.agent_id,
            tool=proposed_tool,
            action=proposed_action,
            parameters=tool_parameters or {},
            original_intent=task.original_intent,
            data_classification=data_classification,
            target_destination=target_destination,
            session_valid=session_ok,
            bypass_attempt=bypass_attempt,
            untrusted_sources=untrusted,
            injection_indicators=list(set(injection)),
            untrusted_snippets=snippets,
            source_trust_levels=trust_levels,
        ),
    )

    decision_row = PolicyDecision(
        action_request_id=action.id,
        decision=policy.decision.value,
        policy_version=settings.policy_version,
        triggered_rules=policy.triggered_rules,
        reasons=policy.reasons,
        risk_score=policy.risk_score,
    )
    db.add(decision_row)

    action.risk_score = policy.risk_score
    action.risk_breakdown = policy.risk_breakdown

    approval_id = None
    grant_issued = False

    if policy.decision == Decision.BLOCK:
        action.status = ActionStatus.BLOCKED
        append_audit_event(
            db,
            event_type="blocked_action",
            actor_type="system",
            actor_id="pdp",
            action_request_id=action.id,
            details={"reasons": policy.reasons, "rules": policy.triggered_rules, "risk": policy.risk_score},
        )
    elif policy.decision == Decision.REQUIRE_APPROVAL:
        action.status = ActionStatus.APPROVAL_PENDING
        approval = ApprovalRequest(
            action_request_id=action.id,
            parameter_hash=action.parameter_hash,
            policy_version=settings.policy_version,
            status=ApprovalStatus.PENDING,
            expires_at=utcnow() + timedelta(minutes=settings.approval_expiry_minutes),
        )
        db.add(approval)
        db.flush()
        approval_id = approval.id
        append_audit_event(
            db,
            event_type="approval_request",
            actor_type="system",
            actor_id="pdp",
            action_request_id=action.id,
            details={"approval_id": str(approval.id), "risk": policy.risk_score},
        )
    else:
        action.status = ActionStatus.ALLOW
        grant = issue_grant(
            action_id=str(action.id),
            parameter_hash=action.parameter_hash,
            policy_version=settings.policy_version,
        )
        fields = grant_fields_for_db(grant)
        action.grant_token = fields["grant_token"]
        action.grant_nonce = fields["grant_nonce"]
        action.grant_expires_at = fields["grant_expires_at"]
        grant_issued = True
        append_audit_event(
            db,
            event_type="execution_grant_creation",
            actor_type="system",
            actor_id="grant_manager",
            action_request_id=action.id,
            details={"grant_nonce": action.grant_nonce, "expires_at": action.grant_expires_at.isoformat()},
        )

    append_audit_event(
        db,
        event_type="policy_decision",
        actor_type="system",
        actor_id="pdp",
        action_request_id=action.id,
        details={
            "decision": policy.decision.value,
            "risk_score": policy.risk_score,
            "triggered_rules": policy.triggered_rules,
            "reasons": policy.reasons,
        },
    )

    for c in contexts:
        db.add(
            ContextAnalysisResult(
                context_source_id=c.id,
                action_request_id=action.id,
                indicators={"injection": list(set(injection))},
                trust_assessment=c.trust_level,
                notes="Bound to action inspection",
            )
        )

    db.commit()
    db.refresh(action)

    return {
        "action_id": str(action.id),
        "status": action.status,
        "decision": policy.decision.value,
        "risk_score": policy.risk_score,
        "risk_breakdown": policy.risk_breakdown,
        "triggered_rules": policy.triggered_rules,
        "reasons": policy.reasons,
        "approval_id": str(approval_id) if approval_id else None,
        "grant_issued": grant_issued,
    }


def execute_action(db: Session, *, action_id: uuid.UUID, actor_id: str) -> dict[str, Any]:
    settings = get_settings()
    action = db.get(ActionRequest, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    expires = action.expires_at
    if expires.tzinfo is None:
        from datetime import UTC

        expires = expires.replace(tzinfo=UTC)
    if utcnow() > expires:
        action.status = ActionStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=400, detail="Expired action request")

    if action.status not in {ActionStatus.ALLOW, ActionStatus.APPROVED}:
        raise HTTPException(status_code=400, detail=f"Action status {action.status} is not executable")

    if not action.grant_token:
        raise HTTPException(status_code=400, detail="Missing execution grant")

    approved_by: str | None = None
    if action.status == ActionStatus.APPROVED:
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.action_request_id == action.id).first()
        decision = (
            db.query(ApprovalDecision)
            .filter(ApprovalDecision.approval_request_id == approval.id, ApprovalDecision.decision == "approved")
            .order_by(ApprovalDecision.created_at.desc())
            .first()
            if approval else None
        )
        if not decision:
            raise HTTPException(status_code=403, detail="Approved action has no valid reviewer decision")
        approved_by = str(decision.approver_id)

    validation = validate_grant(
        action.grant_token,
        action_id=str(action.id),
        parameter_hash=action.parameter_hash,
        policy_version=action.policy_version,
        already_consumed=action.grant_consumed_at is not None,
        stored_nonce=action.grant_nonce,
        approver_id=approved_by,
    )
    if not validation.valid:
        append_audit_event(
            db,
            event_type="policy_violation",
            actor_type="system",
            actor_id="grant_manager",
            action_request_id=action.id,
            details={"reason": validation.reason},
        )
        db.commit()
        raise HTTPException(status_code=403, detail=validation.reason)

    # Revalidate policy version
    if action.policy_version != settings.policy_version:
        raise HTTPException(status_code=403, detail="Policy version changed after approval")

    if not _session_valid(db, action.session_id):
        raise HTTPException(status_code=403, detail="Expired or revoked session")

    capability = (
        db.query(AgentCapability)
        .filter(
            AgentCapability.agent_id == action.agent_id,
            AgentCapability.tool_name == action.proposed_tool,
            AgentCapability.action_name == action.proposed_action,
        )
        .first()
    )
    if not capability:
        append_audit_event(
            db,
            event_type="policy_violation",
            actor_type="system",
            actor_id="pep",
            action_request_id=action.id,
            details={"reason": "Agent capability was revoked before execution"},
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Agent capability revoked")

    # Freeze: recompute parameter hash must match
    if parameter_hash(action.tool_parameters) != action.parameter_hash:
        raise HTTPException(status_code=403, detail="Parameter mismatch")

    action.status = ActionStatus.EXECUTING
    action.grant_consumed_at = utcnow()
    execution = ToolExecution(
        action_request_id=action.id,
        tool_name=action.proposed_tool,
        action_name=action.proposed_action,
        status=ExecutionStatus.SUCCEEDED,
    )
    db.add(execution)
    db.flush()

    append_audit_event(
        db,
        event_type="tool_execution",
        actor_type="system",
        actor_id="tool_proxy",
        action_request_id=action.id,
        details={"tool": action.proposed_tool, "action": action.proposed_action},
    )

    try:
        proxy = get_tool_proxy()
        result = proxy.execute(action.proposed_tool, action.proposed_action, action.tool_parameters)
        # Redact large content
        summary = {
            k: v for k, v in result.items()
            if k not in {"content_bytes", "body", "content", "preview"}
        }
        execution.result_summary = summary
        execution.status = ExecutionStatus.SUCCEEDED
        execution.completed_at = utcnow()
        action.status = ActionStatus.SUCCEEDED
        append_audit_event(
            db,
            event_type="tool_result",
            actor_type="system",
            actor_id="tool_proxy",
            action_request_id=action.id,
            details={"status": "succeeded", "summary_keys": list(summary.keys())},
        )
        db.commit()
        return {
            "execution_id": str(execution.id),
            "status": "succeeded",
            # Return tool output to the current authorized task while storing
            # only an operational summary in the database.
            "result_summary": result,
        }
    except Exception as exc:  # noqa: BLE001
        execution.status = ExecutionStatus.FAILED
        execution.error_message = str(exc)
        execution.completed_at = utcnow()
        action.status = ActionStatus.FAILED
        append_audit_event(
            db,
            event_type="tool_result",
            actor_type="system",
            actor_id="tool_proxy",
            action_request_id=action.id,
            details={"status": "failed", "error": str(exc)},
        )
        db.commit()
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {exc}") from exc


def ingest_user_context(db: Session, task: UserRequest) -> ContextSource:
    analysis = analyze_context(task.original_intent, is_user_request=True)
    ctx = ContextSource(
        task_id=task.id,
        source_type=analysis.source_type.value,
        source_owner=str(task.user_id),
        trust_level=analysis.trust_level.value,
        content_hash=analysis.content_hash,
        provenance="user_request",
        content_preview=task.original_intent[:1000],
        injection_risk_score=analysis.injection_risk_score,
    )
    db.add(ctx)
    db.flush()
    append_audit_event(
        db,
        event_type="context_ingestion",
        actor_type="user",
        actor_id=str(task.user_id),
        details={"context_id": str(ctx.id), "source_type": ctx.source_type, "trust_level": ctx.trust_level},
    )
    return ctx


def ingest_tool_response_context(
    db: Session,
    *,
    task_id: uuid.UUID,
    content: str,
    provenance: str,
    is_external: bool = True,
) -> ContextSource:
    analysis = analyze_context(content, is_external=is_external, is_tool_response=True)
    ctx = ContextSource(
        task_id=task_id,
        source_type=analysis.source_type.value,
        source_owner="tool_proxy",
        trust_level=analysis.trust_level.value,
        content_hash=analysis.content_hash,
        provenance=provenance,
        content_preview=(content or "")[:256],
        injection_risk_score=analysis.injection_risk_score,
    )
    db.add(ctx)
    db.flush()
    append_audit_event(
        db,
        event_type="context_ingestion",
        actor_type="system",
        actor_id="tool_proxy",
        details={
            "context_id": str(ctx.id),
            "source_type": ctx.source_type,
            "trust_level": ctx.trust_level,
            "injection_risk_score": ctx.injection_risk_score,
        },
    )
    return ctx
