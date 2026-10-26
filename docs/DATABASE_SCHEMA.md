# Database Schema (Phase 1)

All primary keys are UUID. All timestamps are UTC (`timestamptz`).

## Entity Relationship (logical)

```text
users ──┬── user_roles ── roles
        ├── agent_sessions ── agents ── agent_capabilities
        ├── user_requests (tasks)
        ├── action_requests ──┬── policy_decisions
        │                     ├── approval_requests ── approval_decisions
        │                     ├── tool_executions
        │                     └── context_sources (via source_context_ids)
        └── audit_events (chained)

destination_allowlists (standalone, scoped by type)
context_analysis_results ── context_sources
```

## Tables

### users
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email | VARCHAR UNIQUE | |
| full_name | VARCHAR | |
| password_hash | VARCHAR | bcrypt |
| is_active | BOOLEAN | default true |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### roles
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | VARCHAR UNIQUE | employee, manager, finance_admin, security_admin |
| description | TEXT | |

### user_roles
| Column | Type | Notes |
|--------|------|-------|
| user_id | UUID FK → users | PK composite |
| role_id | UUID FK → roles | PK composite |

### agents
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | VARCHAR UNIQUE | |
| description | TEXT | |
| is_active | BOOLEAN | |
| created_at | TIMESTAMPTZ | |

### agent_capabilities
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| agent_id | UUID FK → agents | |
| tool_name | VARCHAR | email, storage, ticket |
| action_name | VARCHAR | search_email, etc. |
| UNIQUE(agent_id, tool_name, action_name) | | |

### agent_sessions
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| agent_id | UUID FK | |
| user_id | UUID FK | |
| task_id | UUID FK nullable | |
| status | VARCHAR | active, revoked, expired |
| expires_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |
| revoked_at | TIMESTAMPTZ nullable | |

### user_requests
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | task_id |
| user_id | UUID FK | |
| agent_id | UUID FK | |
| session_id | UUID FK | |
| original_intent | TEXT | |
| demo_scenario | VARCHAR nullable | A, B, C |
| status | VARCHAR | pending, running, completed, failed |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### context_sources
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| task_id | UUID FK | |
| source_type | VARCHAR | SYSTEM_POLICY, USER_REQUEST, INTERNAL_DATA, EXTERNAL_DATA, TOOL_RESPONSE, UNTRUSTED_CONTENT |
| source_owner | VARCHAR | |
| trust_level | VARCHAR | trusted, untrusted, system_policy |
| content_hash | VARCHAR(64) | SHA-256 |
| provenance | TEXT | |
| content_preview | TEXT | redacted/truncated |
| injection_risk_score | INTEGER | 0–100 |
| received_at | TIMESTAMPTZ | |

### context_analysis_results
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| context_source_id | UUID FK | |
| action_request_id | UUID FK nullable | |
| indicators | JSONB | injection phrases found |
| trust_assessment | VARCHAR | |
| notes | TEXT | |
| created_at | TIMESTAMPTZ | |

### action_requests
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | action_id |
| user_id | UUID FK | |
| agent_id | UUID FK | |
| session_id | UUID FK | |
| task_id | UUID FK | |
| original_user_intent | TEXT | |
| proposed_tool | VARCHAR | |
| proposed_action | VARCHAR | |
| tool_parameters | JSONB | frozen |
| parameter_hash | VARCHAR(64) | SHA-256 canonical |
| source_context_ids | JSONB | UUID list |
| data_classification | VARCHAR | public, internal, confidential |
| target_destination | VARCHAR nullable | |
| request_nonce | VARCHAR UNIQUE | |
| idempotency_key | VARCHAR UNIQUE | |
| policy_version | VARCHAR | |
| status | VARCHAR | PROPOSED…CANCELLED |
| risk_score | INTEGER nullable | |
| risk_breakdown | JSONB nullable | |
| grant_token | TEXT nullable | |
| grant_nonce | VARCHAR UNIQUE nullable | |
| grant_expires_at | TIMESTAMPTZ nullable | |
| grant_consumed_at | TIMESTAMPTZ nullable | |
| created_at | TIMESTAMPTZ | |
| expires_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| CHECK status IN (...) | | |
| CHECK risk_score BETWEEN 0 AND 100 | | |

### policy_decisions
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| action_request_id | UUID FK | |
| decision | VARCHAR | ALLOW, REQUIRE_APPROVAL, BLOCK |
| policy_version | VARCHAR | |
| triggered_rules | JSONB | |
| reasons | JSONB | |
| risk_score | INTEGER | |
| created_at | TIMESTAMPTZ | |
| CHECK decision IN (...) | | |

### approval_requests
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| action_request_id | UUID FK UNIQUE | |
| parameter_hash | VARCHAR(64) | |
| policy_version | VARCHAR | |
| status | VARCHAR | pending, approved, denied, expired |
| expires_at | TIMESTAMPTZ | 15 min |
| created_at | TIMESTAMPTZ | |

### approval_decisions
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| approval_request_id | UUID FK | |
| approver_id | UUID FK | |
| decision | VARCHAR | approved, denied |
| comment | TEXT | |
| approval_nonce | VARCHAR UNIQUE | |
| created_at | TIMESTAMPTZ | |

### tool_executions
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| action_request_id | UUID FK | |
| tool_name | VARCHAR | |
| action_name | VARCHAR | |
| status | VARCHAR | succeeded, failed, rejected |
| result_summary | JSONB | redacted |
| error_message | TEXT nullable | |
| started_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ nullable | |

### audit_events
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| sequence | BIGINT UNIQUE | monotonic |
| event_type | VARCHAR | |
| actor_type | VARCHAR | user, agent, system |
| actor_id | VARCHAR | |
| action_request_id | UUID nullable | |
| details | JSONB | redacted |
| previous_event_hash | VARCHAR(64) | |
| event_hash | VARCHAR(64) | |
| created_at | TIMESTAMPTZ | |

### destination_allowlists
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| destination_type | VARCHAR | email, storage_bucket, ticket_repo |
| destination_value | VARCHAR | |
| classification_max | VARCHAR | |
| is_active | BOOLEAN | |
| created_at | TIMESTAMPTZ | |
| UNIQUE(destination_type, destination_value) | | |
