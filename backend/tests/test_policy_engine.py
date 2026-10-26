from app.core.risk_engine import compute_risk, decision_from_risk


def test_risk_threshold_boundaries():
    assert decision_from_risk(39) == "ALLOW"
    assert decision_from_risk(40) == "REQUIRE_APPROVAL"
    assert decision_from_risk(69) == "REQUIRE_APPROVAL"
    assert decision_from_risk(70) == "BLOCK"


def test_risk_is_capped_and_explainable():
    score = compute_risk(untrusted_source=True, prompt_injection=True, intent_mismatch=True,
                         confidential_data=True, external_destination=True,
                         action_name="delete_file", bulk_access=True)
    assert score.score == 100
    assert "untrusted_source" in score.factors
    assert "destructive_operation" in score.factors
