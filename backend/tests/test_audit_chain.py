from app.core.audit import GENESIS_HASH, compute_event_hash, redact


def test_hash_chain_detects_changed_payload():
    args = dict(event_type="policy_decision", actor_type="system", actor_id="pdp",
                action_request_id=None, details={"decision": "BLOCK"}, timestamp="2026-01-01T00:00:00+00:00")
    original = compute_event_hash(GENESIS_HASH, **args)
    altered = compute_event_hash(GENESIS_HASH, **{**args, "details": {"decision": "ALLOW"}})
    assert original != altered


def test_audit_redacts_secrets():
    assert redact({"api_token": "secret", "nested": {"password": "secret"}}) == {
        "api_token": "[REDACTED]", "nested": {"password": "[REDACTED]"}}
