from enum import StrEnum


class RoleName(StrEnum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    FINANCE_ADMIN = "finance_admin"
    SECURITY_ADMIN = "security_admin"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(StrEnum):
    SYSTEM_POLICY = "SYSTEM_POLICY"
    USER_REQUEST = "USER_REQUEST"
    INTERNAL_DATA = "INTERNAL_DATA"
    EXTERNAL_DATA = "EXTERNAL_DATA"
    TOOL_RESPONSE = "TOOL_RESPONSE"
    UNTRUSTED_CONTENT = "UNTRUSTED_CONTENT"


class TrustLevel(StrEnum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
    SYSTEM_POLICY = "system_policy"


class ActionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    INSPECTING = "INSPECTING"
    ALLOW = "ALLOW"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Decision(StrEnum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCK = "BLOCK"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class DataClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
