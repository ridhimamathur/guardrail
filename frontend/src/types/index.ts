export interface User {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Metrics {
  total_actions_today: number;
  allowed_actions: number;
  blocked_actions: number;
  pending_approvals: number;
  risk_distribution: {
    low_0_39: number;
    mid_40_69: number;
    high_70_100: number;
  };
  recent_security_events: SecurityEvent[];
}

export interface SecurityEvent {
  sequence: number;
  event_type: string;
  created_at: string | null;
}

export interface Task {
  id: string;
  original_intent: string;
  status: string;
  session_id: string;
  agent_id: string;
  demo_scenario: string | null;
  created_at: string;
}

export interface TaskActionSummary {
  id: string;
  tool: string;
  action: string;
  status: string;
  risk_score: number | null;
  decision_params: Record<string, unknown>;
}

export interface TaskDetail {
  task: Task;
  actions: TaskActionSummary[];
}

export interface TaskRunResult {
  task_id: string;
  status: string;
  steps: TaskStep[];
  message: string;
}

export interface TaskStep {
  proposal?: {
    tool?: string;
    proposed_action?: string;
    parameters?: Record<string, unknown>;
    reasoning?: string;
    target_destination?: string | null;
    data_classification?: string;
    done?: boolean;
  };
  inspect?: {
    action_id: string;
    status: string;
    decision: string;
    risk_score: number;
    risk_breakdown?: Record<string, unknown> | null;
    triggered_rules: string[];
    reasons: string[];
    approval_id?: string | null;
    grant_issued?: boolean;
  };
  execution?: {
    execution_id: string;
    status: string;
    result_summary?: Record<string, unknown> | null;
  } | null;
}

export interface ActionRecord {
  id: string;
  task_id: string;
  original_user_intent: string;
  proposed_tool: string;
  proposed_action: string;
  tool_parameters: Record<string, unknown>;
  parameter_hash: string;
  data_classification: string;
  target_destination: string | null;
  status: string;
  risk_score: number | null;
  risk_breakdown: Record<string, unknown> | null;
  policy_version: string;
  created_at: string;
  expires_at: string;
}

export interface ContextSource {
  id: string;
  source_type: string;
  trust_level: string;
  injection_risk_score: number;
  content_preview: string;
  provenance: string;
}

export interface ActionDetailResponse {
  action: ActionRecord;
  decision: {
    decision: string | null;
    triggered_rules: string[];
    reasons: string[];
    risk_score: number | null;
  };
  contexts: ContextSource[];
}

export interface TimelineEvent {
  sequence: number;
  event_type: string;
  actor_type: string;
  actor_id: string;
  details: Record<string, unknown> | null;
  created_at: string | null;
  event_hash: string;
}

export interface Approval {
  id: string;
  action_request_id: string;
  parameter_hash: string;
  policy_version: string;
  status: string;
  expires_at: string;
  created_at: string | null;
  action: {
    tool?: string | null;
    action?: string | null;
    parameters?: Record<string, unknown> | null;
    target_destination?: string | null;
    recipient?: string | null;
    file?: string | null;
    risk_score?: number | null;
    risk_breakdown?: Record<string, unknown> | null;
    data_classification?: string | null;
    original_user_intent?: string | null;
    id?: string | null;
  } | null;
}

export interface AuditEvent {
  id: string;
  sequence: number;
  event_type: string;
  actor_type: string;
  actor_id: string;
  action_request_id: string | null;
  details: Record<string, unknown> | null;
  previous_event_hash: string | null;
  event_hash: string;
  created_at: string | null;
}

export interface AuditVerifyResult {
  valid: boolean;
  checked_events: number;
  first_break_sequence: number | null;
}

export interface HealthStatus {
  status: string;
  version: string;
  phase: number;
}

export interface LiveFeedMessage {
  type: string;
  event_type?: string;
  sequence?: number;
  action_request_id?: string | null;
  details?: Record<string, unknown> | null;
  created_at?: string | null;
  cursor?: number;
  [key: string]: unknown;
}
