"""Explainable deterministic risk scoring (0–100)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RiskAssessment:
    score: int
    factors: dict[str, int] = field(default_factory=dict)
    explanations: list[str] = field(default_factory=list)


RISK_FACTORS = {
    "untrusted_source": 20,
    "prompt_injection_indicator": 25,
    "intent_mismatch": 25,
    "confidential_data": 15,
    "external_destination": 20,
    "write_operation": 10,
    "destructive_operation": 30,
    "bulk_access": 15,
    "anomalous_behavior": 10,
}


WRITE_ACTIONS = {"send_email", "upload_file", "create_ticket", "add_comment", "share_file"}
DESTRUCTIVE_ACTIONS = {"delete_file"}
BULK_HINTS = ("all", "every", "bulk", "*")


def compute_risk(
    *,
    untrusted_source: bool = False,
    prompt_injection: bool = False,
    intent_mismatch: bool = False,
    confidential_data: bool = False,
    external_destination: bool = False,
    action_name: str = "",
    bulk_access: bool = False,
    anomalous_behavior: bool = False,
    anomalous_points: int = 10,
) -> RiskAssessment:
    factors: dict[str, int] = {}
    explanations: list[str] = []

    def add(name: str, points: int, reason: str) -> None:
        factors[name] = points
        explanations.append(f"+{points} {name}: {reason}")

    if untrusted_source:
        add("untrusted_source", RISK_FACTORS["untrusted_source"], "Context includes untrusted source")
    if prompt_injection:
        add(
            "prompt_injection_indicator",
            RISK_FACTORS["prompt_injection_indicator"],
            "Injection indicators detected in context",
        )
    if intent_mismatch:
        add("intent_mismatch", RISK_FACTORS["intent_mismatch"], "Proposed action mismatches user intent")
    if confidential_data:
        add("confidential_data", RISK_FACTORS["confidential_data"], "Action involves confidential data")
    if external_destination:
        add("external_destination", RISK_FACTORS["external_destination"], "Target is external destination")
    if action_name in WRITE_ACTIONS:
        add("write_operation", RISK_FACTORS["write_operation"], f"Write operation: {action_name}")
    if action_name in DESTRUCTIVE_ACTIONS:
        add("destructive_operation", RISK_FACTORS["destructive_operation"], f"Destructive: {action_name}")
    if bulk_access:
        add("bulk_access", RISK_FACTORS["bulk_access"], "Bulk access pattern detected")
    if anomalous_behavior:
        pts = max(10, min(30, anomalous_points))
        add("anomalous_behavior", pts, "Anomalous behavior signal")

    score = min(100, sum(factors.values()))
    return RiskAssessment(score=score, factors=factors, explanations=explanations)


def decision_from_risk(score: int) -> str:
    if score >= 70:
        return "BLOCK"
    if score >= 40:
        return "REQUIRE_APPROVAL"
    return "ALLOW"


def looks_bulk(parameters: dict) -> bool:
    blob = str(parameters).lower()
    return any(h in blob for h in BULK_HINTS)
