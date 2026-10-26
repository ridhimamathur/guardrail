"""Deterministic intent-to-action alignment for Phase 1."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class AlignmentResult:
    aligned: bool
    mismatch: bool
    score: float
    reasons: list[str]


# Expected action families for common intents
INTENT_ACTION_MAP: dict[str, set[tuple[str, str]]] = {
    "invoice": {
        ("email", "search_email"),
        ("email", "read_email"),
        ("storage", "upload_file"),
        ("storage", "list_files"),
        ("storage", "read_file"),
        ("ticket", "create_ticket"),
        ("ticket", "add_comment"),
    },
    "share": {
        ("storage", "share_file"),
        ("storage", "read_file"),
        ("storage", "list_files"),
        ("email", "send_email"),
    },
    "report": {
        ("storage", "share_file"),
        ("storage", "read_file"),
        ("storage", "list_files"),
        ("email", "send_email"),
    },
}


def _intent_keywords(intent: str) -> set[str]:
    text = (intent or "").lower()
    keys: set[str] = set()
    if "invoice" in text or "vendor" in text:
        keys.add("invoice")
    if "share" in text or "auditor" in text:
        keys.add("share")
    if "report" in text or "confidential" in text:
        keys.add("report")
    return keys or {"invoice"}


def intent_allows_action(intent: str, tool: str, action: str) -> AlignmentResult:
    keywords = _intent_keywords(intent)
    allowed: set[tuple[str, str]] = set()
    for key in keywords:
        allowed |= INTENT_ACTION_MAP.get(key, set())

    pair = (tool, action)
    reasons: list[str] = []

    # External send to attacker is always a mismatch vs invoice/share legitimate intents
    if action == "send_email" and "attacker@" in str(intent).lower():
        # intent itself mentions attacker — rare; treat carefully
        pass

    if pair in allowed:
        return AlignmentResult(aligned=True, mismatch=False, score=1.0, reasons=["Action matches user intent family."])

    # send_email / share to external when user asked only for invoice find/upload/ticket
    if "invoice" in keywords and action in {"send_email", "share_file", "delete_file"}:
        reasons.append("Proposed action is outside invoice workflow (search/upload/ticket).")
        return AlignmentResult(aligned=False, mismatch=True, score=0.0, reasons=reasons)

    if action == "send_email" and not re.search(r"send|email|share", intent or "", re.I):
        reasons.append("User did not request sending email.")
        return AlignmentResult(aligned=False, mismatch=True, score=0.0, reasons=reasons)

    if action == "delete_file":
        reasons.append("Destructive delete is not part of user intent.")
        return AlignmentResult(aligned=False, mismatch=True, score=0.0, reasons=reasons)

    reasons.append(f"Action {tool}.{action} is not clearly aligned with intent.")
    return AlignmentResult(aligned=False, mismatch=True, score=0.2, reasons=reasons)


def untrusted_content_tries_to_override(intent: str, untrusted_snippets: list[str]) -> bool:
    """P8: Untrusted content cannot change the original user task."""
    intent_l = (intent or "").lower()
    for snippet in untrusted_snippets:
        s = (snippet or "").lower()
        if "ignore" in s and ("request" in s or "instruction" in s):
            return True
        if "attacker@" in s and "attacker@" not in intent_l:
            return True
        if re.search(r"send\s+(them|all|every)", s) and "send" not in intent_l:
            return True
    return False
