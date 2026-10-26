# API Contract (Phase 1)

Base URL: `http://localhost:8000`

Auth: `Authorization: Bearer <jwt>` for protected routes.

OpenAPI: `http://localhost:8000/docs`

## Auth

### POST /api/v1/auth/login
```json
Request: { "email": "employee@guardrail.local", "password": "<your local DEMO_EMPLOYEE_PASSWORD>" }
Response: { "access_token": "...", "token_type": "bearer", "user": { "id", "email", "full_name", "roles": [] } }
```

### GET /api/v1/auth/me
Returns current user profile and roles.

## Tasks

### POST /api/v1/tasks
```json
Request: { "intent": "Find the latest invoice...", "demo_scenario": "A" }
Response: { "id", "original_intent", "status", "session_id", "agent_id", "demo_scenario", "created_at" }
```

### GET /api/v1/tasks/{task_id}
Task detail including linked actions.

### POST /api/v1/tasks/{task_id}/run
Runs the mock agent workflow for the task (Demo A/B/C). Returns action timeline.

## Actions

### GET /api/v1/actions?limit=100
Lists recent action proposals. Employees see their own actions; managers and security admins can review all actions.

### POST /api/v1/actions/inspect
```json
Request: {
  "task_id": "uuid",
  "proposed_tool": "email",
  "proposed_action": "search_email",
  "tool_parameters": {},
  "source_context_ids": [],
  "data_classification": "internal",
  "target_destination": null,
  "idempotency_key": "unique-key"
}
Response: {
  "action_id", "status", "decision", "risk_score", "risk_breakdown",
  "triggered_rules", "reasons", "approval_id", "grant_issued"
}
```

### GET /api/v1/actions/{action_id}
Frozen action request + latest decision.

### GET /api/v1/actions/{action_id}/timeline
Ordered events for the action.

### POST /api/v1/actions/{action_id}/execute
Executes using frozen DB parameters + one-time grant validation.
Does **not** accept arbitrary tool parameters.

Only the action owner or a manager/security admin may view or execute an action. Approved grants are bound to the exact reviewer identity as well as action ID, parameter hash, policy version, expiry, and nonce.
```json
Response: { "execution_id", "status", "result_summary" }
```

## Approvals

### GET /api/v1/approvals
List pending (and optional filter) approval requests. Manager / security_admin.

### GET /api/v1/approvals/{approval_id}
Detail with exact parameters, risk, reasons.

### POST /api/v1/approvals/{approval_id}/approve
```json
Request: { "comment": "ok" }
```

### POST /api/v1/approvals/{approval_id}/deny
```json
Request: { "comment": "too risky" }
```

## Audit

### GET /api/v1/audit/events
Paginated audit events.

### GET /api/v1/audit/events/{event_id}
Single event.

### GET /api/v1/audit/verify
```json
Response: { "valid": true, "checked_events": N, "first_break_sequence": null }
```

## System

### GET /api/v1/health
```json
{ "status": "ok", "version": "0.1.0", "phase": 1 }
```

### GET /api/v1/metrics
Simple counters: actions today, allowed, blocked, pending approvals, risk buckets.

## WebSocket

### WS /ws/live-feed
Requires `?token=<jwt>`.
Pushes JSON events: `action_update`, `approval_update`, `audit_event`, `execution_update`.
