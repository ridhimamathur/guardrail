from app.agent.provider import MockLLMProvider


def test_mock_provider_proposes_all_demo_sequences_without_decisions():
    provider = MockLLMProvider()
    a = [provider.propose_next_action(intent="invoice", scenario="A", history=[])]
    assert a[0]["proposed_action"] == "search_email"
    b = provider.propose_next_action(intent="invoice", scenario="B", history=[{}, {}])
    assert b["proposed_action"] == "send_email"
    c = provider.propose_next_action(intent="share confidential report", scenario="C", history=[])
    assert c["proposed_action"] == "share_file"
    assert all("decision" not in proposal for proposal in [a[0], b, c])
