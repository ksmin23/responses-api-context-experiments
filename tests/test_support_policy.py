import pytest
 
from responses_lab.support_policy import (
    ACTIONS,
    POLICY_PROFILES,
    RULE_PRECEDENCE,
    SupportPolicySimulator,
    decisive_rule,
    expected_action,
    scenario_ids,
    ticket_sequence,
    validate_workload,
)
 
 
def test_workload_covers_every_rule_in_both_phases() -> None:
    preflight = validate_workload()
    assert preflight["scenario_count"] == 5
    for summary in preflight["scenarios"].values():
        assert summary == {
            "learning_cases": 5,
            "transfer_cases": 7,
            "covered_rules": 5,
        }
 
 
@pytest.mark.parametrize("scenario_id", scenario_ids())
def test_each_profile_uses_all_actions_and_stable_precedence(scenario_id: str) -> None:
    tickets = ticket_sequence(scenario_id)
    assert set(POLICY_PROFILES[scenario_id]) == set(RULE_PRECEDENCE)
    assert {expected_action(scenario_id, ticket) for ticket in tickets} == set(ACTIONS)
    transfer = [ticket for ticket in tickets if ticket["phase"] == "transfer"]
    assert {decisive_rule(ticket) for ticket in transfer} == set(RULE_PRECEDENCE)
 
 
def test_simulator_feedback_hides_rule_but_grader_keeps_ground_truth() -> None:
    simulator = SupportPolicySimulator("POL-301")
    ticket = simulator.tickets[0]
    ticket_id = ticket["ticket_id"]
    observation = simulator.inspect_ticket(ticket_id)
    assert "decisive_rule" not in observation
    assert "expected_action" not in observation
 
    wrong_action = next(
        action for action in ACTIONS if action != expected_action("POL-301", ticket)
    )
    feedback = simulator.submit_disposition(ticket_id, wrong_action)
    assert feedback["accepted"] is False
    assert feedback["accepted_action"] == expected_action("POL-301", ticket)
    assert "decisive_rule" not in feedback
 
    grade = simulator.grade()
    assert grade["completed_ticket_count"] == 1
    assert grade["decisions"][0]["decisive_rule"] == decisive_rule(ticket)
 
 
def test_simulator_rejects_duplicate_disposition() -> None:
    simulator = SupportPolicySimulator("POL-302")
    ticket = simulator.tickets[0]
    ticket_id = ticket["ticket_id"]
    simulator.submit_disposition(
        ticket_id, expected_action("POL-302", ticket)
    )
    with pytest.raises(ValueError, match="already submitted"):
        simulator.submit_disposition(
            ticket_id, expected_action("POL-302", ticket)
        )
