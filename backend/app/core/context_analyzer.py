"""Context trust classification and rule-based prompt-injection indicators."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.security import sha256_hex
from app.models.enums import SourceType, TrustLevel

INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ignore_instructions", re.compile(r"ignore\s+(all\s+)?(previous|prior|the\s+user).{0,40}(request|instruction|command)", re.I)),
    ("system_override", re.compile(r"(you\s+are\s+now|new\s+instructions|system\s+prompt|override\s+policy)", re.I)),
    ("exfiltrate", re.compile(r"(send|forward|email|exfiltrate).{0,40}(all|every).{0,40}(invoice|document|file|secret)", re.I)),
    ("attacker_destination", re.compile(r"attacker@example\.com", re.I)),
    ("disregard_user", re.compile(r"disregard\s+(the\s+)?user", re.I)),
    ("do_instead", re.compile(r"instead,?\s+(search|send|share|delete|upload)", re.I)),
]


@dataclass
class ContextAnalysis:
    source_type: SourceType
    trust_level: TrustLevel
    content_hash: str
    injection_indicators: list[str] = field(default_factory=list)
    injection_risk_score: int = 0
    notes: str = ""


def classify_source_type(
    *,
    is_user_request: bool = False,
    is_system_policy: bool = False,
    is_external: bool = False,
    is_tool_response: bool = False,
    is_internal: bool = False,
) -> SourceType:
    if is_system_policy:
        return SourceType.SYSTEM_POLICY
    if is_user_request:
        return SourceType.USER_REQUEST
    if is_tool_response:
        return SourceType.TOOL_RESPONSE
    if is_external:
        return SourceType.EXTERNAL_DATA
    if is_internal:
        return SourceType.INTERNAL_DATA
    return SourceType.UNTRUSTED_CONTENT


def trust_for_source(source_type: SourceType) -> TrustLevel:
    if source_type == SourceType.SYSTEM_POLICY:
        return TrustLevel.SYSTEM_POLICY
    if source_type in {SourceType.USER_REQUEST, SourceType.INTERNAL_DATA}:
        return TrustLevel.TRUSTED
    return TrustLevel.UNTRUSTED


def detect_injection_indicators(content: str) -> list[str]:
    found: list[str] = []
    for name, pattern in INJECTION_PATTERNS:
        if pattern.search(content or ""):
            found.append(name)
    return found


def analyze_context(
    content: str,
    *,
    source_type: SourceType | None = None,
    is_user_request: bool = False,
    is_external: bool = False,
    is_tool_response: bool = False,
    is_internal: bool = False,
) -> ContextAnalysis:
    resolved = source_type or classify_source_type(
        is_user_request=is_user_request,
        is_external=is_external,
        is_tool_response=is_tool_response,
        is_internal=is_internal,
    )
    trust = trust_for_source(resolved)
    indicators: list[str] = []
    injection_score = 0
    notes = "User request kept separate from tool/email content."

    # Instructions inside email/document are untrusted data, not commands.
    if trust == TrustLevel.UNTRUSTED or resolved in {
        SourceType.EXTERNAL_DATA,
        SourceType.UNTRUSTED_CONTENT,
        SourceType.TOOL_RESPONSE,
    }:
        indicators = detect_injection_indicators(content)
        if indicators:
            injection_score = min(100, 25 + 10 * (len(indicators) - 1))
            notes = f"Untrusted content contains injection indicators: {', '.join(indicators)}"
            # Promote classification to UNTRUSTED_CONTENT when injection found in external data
            if resolved == SourceType.EXTERNAL_DATA:
                resolved = SourceType.UNTRUSTED_CONTENT
                trust = TrustLevel.UNTRUSTED

    return ContextAnalysis(
        source_type=resolved,
        trust_level=trust,
        content_hash=sha256_hex(content or ""),
        injection_indicators=indicators,
        injection_risk_score=injection_score,
        notes=notes,
    )
