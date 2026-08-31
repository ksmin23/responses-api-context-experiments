import pytest
 
from responses_lab.support_policy_v2 import (
    ACTIONS,
    RULES,
    SupportPolicyV2Simulator,
    decisive_rule,
    expected_action,
    identifiability_report,
    scenario_ids,
    ticket_sequence,
    validate_workload,
)
 
 
def test_v2_workload_is_balanced_and_identifiable() -> None:
    preflight = validate_workload()
    assert preflight["scenario_count"] == 5
    for summary in preflight["scenarios"].values():
        assert summary["phase_counts"] == {
            "learning": 10,
            "boundary": 8,
            "evaluation": 20,
        }
        assert summary["evaluation_rule_counts"] == {
            rule: 4 for rule in RULES
        }
        assert summary["evaluation_action_counts"] == {
            action: 4 for action in ACTIONS
        }
        assert summary["identifiability"]["matching_behavior_signatures"] == 1
 
 
@pytest.mark.parametrize("scenario_id", scenario_ids())
def test_labeled_phases_identify_one_policy_behavior(scenario_id: str) -> None:
    report = identifiability_report(scenario_id)
    assert report["candidate_parameterizations"] == 2_880
    assert report["matching_parameterizations"] == 1
    assert report["identifiable"] is True
 
 
def test_evaluation_feedback_does_not_reveal_correctness() -> None:
    simulator = SupportPolicyV2Simulator("POL2-401")
    evaluation = next(
        ticket for ticket in simulator.tickets if ticket["phase"] == "evaluation"
    )
    ticket_id = evaluation["ticket_id"]
    observation = simulator.inspect_ticket(ticket_id)
    assert observation["phase"] == "evaluation"
    feedback = simulator.submit_disposition(ticket_id, ACTIONS[0])
    assert feedback == {"ticket_id": ticket_id, "recorded": True}
    assert "accepted_action" not in feedback
    assert "accepted" not in feedback
 
 
def test_labeled_feedback_is_uniform_for_correct_and_incorrect_actions() -> None:
    scenario_id = "POL2-402"
    tickets = [
        ticket
        for ticket in ticket_sequence(scenario_id)
        if ticket["phase"] in {"learning", "boundary"}
    ]
    correct_ticket, wrong_ticket = tickets[:2]
    simulator = SupportPolicyV2Simulator(scenario_id)
    correct = expected_action(scenario_id, correct_ticket)
    wrong = next(action for action in ACTIONS if action != expected_action(scenario_id, wrong_ticket))
    correct_feedback = simulator.submit_disposition(
        correct_ticket["ticket_id"], correct
    )
    wrong_feedback = simulator.submit_disposition(wrong_ticket["ticket_id"], wrong)
    assert set(correct_feedback) == {"ticket_id", "recorded", "accepted_action"}
    assert set(wrong_feedback) == set(correct_feedback)
    assert "accepted" not in correct_feedback
    assert "accepted" not in wrong_feedback
 
 
def test_grade_reports_blind_accuracy_and_strategy_consistency() -> None:
    scenario_id = "POL2-403"
    simulator = SupportPolicyV2Simulator(scenario_id)
    for ticket in simulator.tickets:
        simulator.inspect_ticket(ticket["ticket_id"])
        simulator.submit_disposition(
            ticket["ticket_id"], expected_action(scenario_id, ticket)
        )
    grade = simulator.grade()
    assert grade["complete"] is True
    assert grade["evaluation_accuracy"] == 1
    assert grade["evaluation_errors"] == 0
    assert grade["strategy_consistency"] == 1
    assert all(value == 1 for value in grade["evaluation_rule_accuracy"].values())
    assert all(
        decisive_rule(ticket) in RULES for ticket in simulator.tickets
    )
