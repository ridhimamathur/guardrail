# Test Plan

Run `cd backend && python -m pip install -e ".[dev]" && pytest`.

| Module | Coverage |
|---|---|
| `test_auth.py` | Password hashing and signed access token round trip |
| `test_policy_engine.py` | Explainable score boundaries and safe proxy allowlist |
| `test_context_analyzer.py` | Trust labeling, hashes, and injection indicators |
| `test_intent_aligner.py` | Invoice workflow alignment and untrusted override |
| `test_grant_manager.py` | Grant signature, binding, expiry and replay validation |
| `test_tool_proxy.py` | Unknown and destructive actions rejected before adapter execution |
| `test_audit_chain.py` | Canonical hash sensitivity and redaction |
| `test_end_to_end_scenarios.py` | Deterministic proposal sequences for A/B/C |

These unit tests do not replace database-backed API/integration tests. Verify Compose startup, login roles, Demo A tool results, Demo B MailHog absence, Demo C approval flow, action ownership, session expiry, grant replay/tampering, and audit verification in a local integration environment before presenting a demo.
