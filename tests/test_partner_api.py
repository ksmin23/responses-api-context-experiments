import json
 
import pytest
 
from responses_lab.partner_api import (
    GRADER_CALIBRATION_CASES,
    GRADER_CALIBRATION_FIXTURE_VERSION,
    GRADER_CALIBRATION_TRANSCRIPT,
    PARTNER_API_HARNESS_VERSION,
    PartnerAPITransferSimulator,
    build_action_budget_final_input,
    combine_grades,
    event_ids_from_transcript,
    grade_report_structure,
    grader_response_issue,
    model_visible_work_order,
    normalize_semantic_grade,
    pilot_failure_recovery_guidance,
    scenario_ids,
    semantic_grader_payload,
    semantic_grader_schema,
    validate_pilot_resume_payload,
)
 
 
def test_corporate_network_auth_failure_has_resume_guidance() -> None:
    guidance = pilot_failure_recovery_guidance(
        status_code=401,
        error_code="employee_api_key_requires_corporate_network",
    )
    assert guidance is not None
    assert "corporate network or VPN" in guidance
    assert "PILOT_RESUME_PATH='latest'" in guidance
 
 
def test_unknown_pilot_failure_has_no_special_recovery_guidance() -> None:
    assert (
        pilot_failure_recovery_guidance(
            status_code=500,
            error_code="internal_server_error",
        )
        is None
    )
 
 
def api_request(simulator, method, path, *, headers=None, body=None):
    return simulator.request(
        method=method,
        path=path,
        headers_json=json.dumps(headers or {}),
        body_json=json.dumps(body or {}),
    )
 
 
def test_profiles_are_available_for_paired_runs() -> None:
    assert scenario_ids() == [
        "API-201",
        "API-202",
        "API-203",
        "API-204",
        "API-205",
    ]
 
 
def test_action_budget_finalization_resolves_the_pending_tool_call() -> None:
    assert PARTNER_API_HARNESS_VERSION == "partner-api-transfer-harness-v3"
    pending = [
        {
            "type": "function_call_output",
            "call_id": "call-final",
            "output": '{"ok": true}',
        }
    ]
    final_input = build_action_budget_final_input(pending)
    assert final_input[0] == pending[0]
    assert final_input[1] == {
        "role": "user",
        "content": "The action budget is exhausted. Return the required JSON now.",
    }
 
 
@pytest.mark.parametrize(
    "pending",
    [
        [],
        [{"role": "user", "content": "missing tool output"}],
        [{"type": "function_call_output", "output": "{}"}],
    ],
)
def test_action_budget_finalization_rejects_an_unresolved_call_id(pending) -> None:
    with pytest.raises(ValueError, match="function_call_output with a call_id"):
        build_action_budget_final_input(pending)
 
 
def test_model_work_orders_do_not_name_hidden_protocol_or_solution() -> None:
    text = str([model_visible_work_order(1), model_visible_work_order(2)]).lower()
    for leaked_term in (
        "idempotency",
        "x-request-token",
        "if-revision",
        "eventual consistency",
        "visibility delay",
        "reasoning",
        "remember",
        "transfer",
    ):
        assert leaked_term not in text
 
 
def test_discovery_requires_observation_and_event_inspection() -> None:
    simulator = PartnerAPITransferSimulator("API-201")
    simulator.begin_episode(1)
 
    missing_identity = api_request(
        simulator,
        "POST",
        "/v1/payments",
        body={"resource_id": "pay-discovery", "amount": 12_500},
    )
    assert missing_identity["code"] == "P-1001"
    assert "X-Request-Token" not in missing_identity
 
    inspected = simulator.inspect_event(missing_identity["event_id"])
    assert inspected["event"]["required_header_name"] == "X-Request-Token"
 
    created = api_request(
        simulator,
        "POST",
        "/v1/payments",
        headers={"X-Request-Token": "e1-create"},
        body={"resource_id": "pay-discovery", "amount": 12_500},
    )
    assert created["revision"] == 1
 
    too_early = api_request(
        simulator,
        "POST",
        "/v1/payments/pay-discovery/confirm",
        headers={"X-Request-Token": "e1-confirm", "If-Revision": 1},
    )
    assert too_early["code"] == "P-4001"
    inspected = simulator.inspect_event(too_early["event_id"])
    assert inspected["event"]["elapsed_seconds"] == 0
    assert "ready_delay_seconds" not in inspected["event"]
 
 
def complete_episode_without_relearning(simulator, episode: int) -> None:
    work_order = simulator.begin_episode(episode)
    resource_id = work_order["resource_id"]
    created = api_request(
        simulator,
        "POST",
        "/v1/payments",
        headers={"X-Request-Token": f"e{episode}-create"},
        body={"resource_id": resource_id, "amount": work_order["amount"]},
    )
    simulator.advance_clock(simulator.profile.ready_delay_seconds)
    confirmed = api_request(
        simulator,
        "POST",
        f"/v1/payments/{resource_id}/confirm",
        headers={
            "X-Request-Token": f"e{episode}-confirm",
            "If-Revision": created["revision"],
        },
    )
    captured = api_request(
        simulator,
        "POST",
        f"/v1/payments/{resource_id}/capture",
        headers={
            "X-Request-Token": f"e{episode}-capture",
            "If-Revision": confirmed["committed_revision"],
        },
    )
    final_revision = captured["committed_revision"]
    if episode == 2:
        refunded = api_request(
            simulator,
            "POST",
            f"/v1/payments/{resource_id}/refund",
            headers={
                "X-Request-Token": "e2-refund",
                "If-Revision": final_revision,
            },
            body={"amount": work_order["refund_amount"]},
        )
        final_revision = refunded["committed_revision"]
    simulator.advance_clock(simulator.profile.visibility_delay_seconds)
    final = api_request(simulator, "GET", f"/v1/payments/{resource_id}")
    assert final["resource"]["revision"] == final_revision
 
 
def test_same_hidden_profile_supports_safe_cross_episode_transfer() -> None:
    simulator = PartnerAPITransferSimulator("API-203")
    complete_episode_without_relearning(simulator, 1)
    assert simulator.grade_episode()["state_success"] is True
    complete_episode_without_relearning(simulator, 2)
    grade = simulator.grade_episode()
    assert grade["state_success"] is True
    assert grade["final_status"] == "partially_refunded"
    assert grade["unsafe_duplicate_count"] == 0
    assert grade["relearned_error_count"] == 0
 
 
def test_stale_representation_requires_committed_revision_reasoning() -> None:
    simulator = PartnerAPITransferSimulator("API-204")
    work_order = simulator.begin_episode(1)
    api_request(
        simulator,
        "POST",
        "/v1/payments",
        headers={"X-Request-Token": "create"},
        body={"resource_id": work_order["resource_id"], "amount": work_order["amount"]},
    )
    simulator.advance_clock(simulator.profile.ready_delay_seconds)
    confirmed = api_request(
        simulator,
        "POST",
        "/v1/payments/pay-discovery/confirm",
        headers={"X-Request-Token": "confirm", "If-Revision": 1},
    )
    stale = api_request(simulator, "GET", "/v1/payments/pay-discovery")
    assert stale["resource"]["revision"] == 1
    assert confirmed["committed_revision"] == 2
    conflict = api_request(
        simulator,
        "POST",
        "/v1/payments/pay-discovery/capture",
        headers={"X-Request-Token": "capture", "If-Revision": 1},
    )
    assert conflict["code"] == "P-3001"
    event = simulator.inspect_event(conflict["event_id"])["event"]
    assert event["supplied_revision"] == 1
    assert event["committed_revision"] == 2
 
 
def valid_report(observed_event_ids):
    return {
        "status": "completed",
        "resource_id": "pay-refund",
        "final_resource_status": "partially_refunded",
        "diagnosis": "The API separates committed mutation state from visible state.",
        "causal_model": "Request identity, readiness, and committed revision jointly govern mutations.",
        "supporting_event_ids": observed_event_ids[:2],
        "rejected_hypotheses": [
            {"hypothesis": "Random fraud hold", "evidence": "The interval repeated."}
        ],
        "strategy_summary": "Use observed commit revisions and verify final state.",
        "preserved_constraints": ["Refunded exactly 1700 units."],
        "remaining_uncertainty": [],
    }
 
 
def test_structural_grader_requires_real_observed_event_ids() -> None:
    grade = {
        "state_success": True,
        "unsafe_duplicate_count": 0,
        "no_duplicate_effects": True,
    }
    report = valid_report(["API-201-E2-001", "API-201-E2-002"])
    accepted = grade_report_structure(
        report,
        episode_grade=grade,
        observed_event_ids=["API-201-E2-001", "API-201-E2-002"],
    )
    assert accepted["success"] is True
    report["supporting_event_ids"] = ["invented-event"]
    rejected = grade_report_structure(
        report,
        episode_grade=grade,
        observed_event_ids=["API-201-E2-001"],
    )
    assert rejected["success"] is False
    assert rejected["checks"]["event_ids_valid"] is False
 
 
def test_semantic_payload_is_blind_to_arm_cost_tokens_and_reasoning() -> None:
    report = valid_report(["API-201-E2-001"])
    payload = semantic_grader_payload(
        transcript=[{"type": "tool_result", "event_id": "API-201-E2-001"}],
        report=report,
    )
    text = str(payload).lower()
    for forbidden in (
        "current_turn",
        "all_turns",
        "reasoning_tokens",
        "latency_ms",
        "cost_usd",
        "pass threshold",
    ):
        assert forbidden not in text
 
 
def test_semantic_schema_and_invalid_evaluation_handling() -> None:
    schema = semantic_grader_schema(["API-201-E2-001"])
    assert schema["properties"]["cited_event_ids"]["items"]["enum"] == [
        "API-201-E2-001"
    ]
    empty_schema = semantic_grader_schema([])
    assert empty_schema["properties"]["cited_event_ids"]["maxItems"] == 0
    invalid = normalize_semantic_grade({"dimension_scores": {}})
    combined = combine_grades({"success": True}, invalid)
    assert combined["evaluation_valid"] is False
    assert combined["score"] is None
    assert combined["success"] is False
 
 
def test_grader_response_contract_and_calibration_coverage() -> None:
    assert grader_response_issue(
        status="incomplete",
        incomplete_reason="max_output_tokens",
        output_text="",
        output_types=[],
    ) == "grader response incomplete: max_output_tokens"
    assert len(GRADER_CALIBRATION_CASES) == 6
    by_id = {case["case_id"]: case for case in GRADER_CALIBRATION_CASES}
    assert by_id["correct-paraphrase"]["expected_success"] is True
    assert by_id["unsafe-success"]["expected_critical_violation"] is True
 
 
def test_grader_calibration_uses_grounded_production_shaped_inputs() -> None:
    assert GRADER_CALIBRATION_FIXTURE_VERSION == (
        "partner-api-transfer-grader-calibration-v2"
    )
    event_ids = event_ids_from_transcript(GRADER_CALIBRATION_TRANSCRIPT)
    assert event_ids == [
        "CAL-E1-001",
        "CAL-E1-002",
        "CAL-E1-003",
        "CAL-E1-004",
        "CAL-E1-005",
        "CAL-E1-006",
        "CAL-E2-001",
        "CAL-E2-002",
        "CAL-E2-003",
        "CAL-E2-004",
        "CAL-E2-005",
    ]
 
    cases = {case["case_id"]: case for case in GRADER_CALIBRATION_CASES}
    positive = cases["correct-paraphrase"]
    report = positive["candidate_report"]
    assert positive["expected_success"] is True
    assert set(report["supporting_event_ids"]).issubset(event_ids)
    assert report["resource_id"] == "pay-refund"
    assert report["final_resource_status"] == "partially_refunded"
    assert "1700" in " ".join(report["preserved_constraints"])
 
    payload = semantic_grader_payload(
        transcript=GRADER_CALIBRATION_TRANSCRIPT,
        report=report,
    )
    assert payload["task"]["observable_transcript"] == GRADER_CALIBRATION_TRANSCRIPT
    assert payload["candidate_report"] == report
    assert semantic_grader_schema(event_ids)["properties"]["cited_event_ids"][
        "items"
    ]["enum"] == event_ids
 
    assert cases["invented-event"]["candidate_report"]["supporting_event_ids"][-1] not in event_ids
    assert "2000" in cases["constraint-violation"]["candidate_report"][
        "strategy_summary"
    ]
 
 
def test_pilot_resume_payload_requires_compatible_unique_known_run_keys() -> None:
    contract = {"workload_version": "v2", "trials": 2}
    payload = {
        "run_id": "pilot-test",
        "created_at": "2026-08-28T00:00:00+00:00",
        "failure_log_path": "artifacts/02a/failures-pilot-test.jsonl",
        "status": "interrupted",
        "experiment_contract": contract,
        "results": [
            {"trial": 1, "scenario_id": "API-201", "arm": "current_turn"},
            {"trial": 1, "scenario_id": "API-201", "arm": "all_turns"},
        ],
    }
    results = validate_pilot_resume_payload(
        payload,
        expected_contract=contract,
        trials=2,
        scenario_ids=["API-201"],
        arm_names=["current_turn", "all_turns"],
    )
    assert len(results) == 2
 
    missing_metadata = {key: value for key, value in payload.items() if key != "run_id"}
    with pytest.raises(ValueError, match="required run metadata"):
        validate_pilot_resume_payload(
            missing_metadata,
            expected_contract=contract,
            trials=2,
            scenario_ids=["API-201"],
            arm_names=["current_turn", "all_turns"],
        )
 
    unknown_status = {**payload, "status": "mystery"}
    with pytest.raises(ValueError, match="unknown status"):
        validate_pilot_resume_payload(
            unknown_status,
            expected_contract=contract,
            trials=2,
            scenario_ids=["API-201"],
            arm_names=["current_turn", "all_turns"],
        )
 
    incompatible = {**payload, "experiment_contract": {"workload_version": "v1"}}
    with pytest.raises(ValueError, match="contract is incompatible"):
        validate_pilot_resume_payload(
            incompatible,
            expected_contract=contract,
            trials=2,
            scenario_ids=["API-201"],
            arm_names=["current_turn", "all_turns"],
        )
 
    duplicate = {**payload, "results": [payload["results"][0]] * 2}
    with pytest.raises(ValueError, match="duplicate"):
        validate_pilot_resume_payload(
            duplicate,
            expected_contract=contract,
            trials=2,
            scenario_ids=["API-201"],
            arm_names=["current_turn", "all_turns"],
        )
 
    unknown = {
        **payload,
        "results": [{"trial": 3, "scenario_id": "API-999", "arm": "other"}],
    }
    with pytest.raises(ValueError, match="unknown trial, scenario, or arm"):
        validate_pilot_resume_payload(
            unknown,
            expected_contract=contract,
            trials=2,
            scenario_ids=["API-201"],
            arm_names=["current_turn", "all_turns"],
        )
