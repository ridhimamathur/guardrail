from datetime import timedelta

from app.core.grant_manager import issue_grant, validate_grant
from app.core.security import utcnow


def test_grant_is_bound_to_action_parameters_and_consumed_once():
    grant = issue_grant(action_id="a1", parameter_hash="hash1", policy_version="1.0.0")
    args = dict(action_id="a1", parameter_hash="hash1", policy_version="1.0.0",
                already_consumed=False, stored_nonce=grant.grant_nonce)
    assert validate_grant(grant.to_token(), **args).valid
    assert not validate_grant(grant.to_token(), **{**args, "already_consumed": True}).valid
    assert not validate_grant(grant.to_token(), **{**args, "parameter_hash": "changed"}).valid
    assert not validate_grant(grant.to_token()+"x", **args).valid


def test_expired_grant_rejected():
    grant = issue_grant(action_id="a1", parameter_hash="h", ttl_minutes=-1)
    result = validate_grant(grant.to_token(), action_id="a1", parameter_hash="h",
                            policy_version=grant.policy_version, already_consumed=False,
                            stored_nonce=grant.grant_nonce)
    assert not result.valid and "Expired" in result.reason


def test_approval_grant_is_bound_to_reviewer():
    grant = issue_grant(action_id="a2", parameter_hash="h2", approver_id="manager-1")
    args = dict(action_id="a2", parameter_hash="h2", policy_version=grant.policy_version,
                already_consumed=False, stored_nonce=grant.grant_nonce)
    assert validate_grant(grant.to_token(), **args, approver_id="manager-1").valid
    assert not validate_grant(grant.to_token(), **args, approver_id="manager-2").valid
