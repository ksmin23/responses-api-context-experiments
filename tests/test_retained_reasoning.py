import pytest
from copy import deepcopy
 
from responses_lab.retained_reasoning import (
    ADAPTIVE_CONFIG,
    canary_catalog,
    canary_result,
    correction_event,
    grade_answer,
    grade_adaptive_answer,
    grade_adaptive_tool_path,
    observation,
    parse_json_object,
    probe_catalog,
    probe_result,
    scenario_ids,
)
 
 
def test_all_scenarios_have_seven_workload_turns_after_initial_prompt() -> None:
    assert len(scenario_ids()) == 5
    for scenario_id in scenario_ids():
        records = [observation(scenario_id, f"OBS-{index:02d}") for index in range(2, 8)]
        assert [record["observation_id"] for record in records] == [
            "OBS-02",
            "OBS-03",
            "OBS-04",
            "OBS-05",
            "OBS-06",
            "OBS-07",
        ]
        assert all("ground_truth" not in record for record in records)
 
 
def test_parse_json_object_accepts_code_fence() -> None:
    assert parse_json_object('```json\n{"status": "conclusive"}\n```') == {
        "status": "conclusive"
    }
 
 
def test_parse_json_object_rejects_array() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        parse_json_object("[]")
 
 
REFERENCE_ANSWERS = {
    "INC-101": {
        "status": "conclusive",
        "diagnosis": "Retry amplification caused by a mismatched timeout budget.",
        "supporting_observation_ids": ["OBS-04", "OBS-05", "OBS-06", "OBS-07"],
        "rejected_hypotheses": [
            {
                "hypothesis": "database saturation",
                "reason": "The corrected per-request measurement stayed flat.",
                "observation_ids": ["OBS-03", "OBS-04"],
            }
        ],
        "recommendation": "Reduce retry count and add jitter while aligning the timeout.",
        "preserved_constraints": [
            "Keep fraud validation enabled.",
            "Do not rollback during the schema migration.",
        ],
        "confidence": "high",
    },
    "INC-102": {
        "status": "conclusive",
        "diagnosis": "Connection pool saturation caused connection-acquire queueing.",
        "supporting_observation_ids": [
            "OBS-03",
            "OBS-04",
            "OBS-05",
            "OBS-06",
            "OBS-07",
        ],
        "rejected_hypotheses": [
            {
                "hypothesis": "payment-provider latency",
                "reason": "The corrected provider span was normal.",
                "observation_ids": ["OBS-02", "OBS-04"],
            }
        ],
        "recommendation": "Increase the connection pool to the tested 56 limit.",
        "preserved_constraints": [
            "Make no schema change.",
            "Do not shed or drop premium traffic.",
        ],
        "confidence": "high",
    },
    "INC-103": {
        "status": "conclusive",
        "diagnosis": "A duplicate serialization pass caused the CPU regression.",
        "supporting_observation_ids": ["OBS-04", "OBS-05", "OBS-06", "OBS-07"],
        "rejected_hypotheses": [
            {
                "hypothesis": "database saturation",
                "reason": "Corrected checkout-only database metrics stayed flat.",
                "observation_ids": ["OBS-02", "OBS-04"],
            }
        ],
        "recommendation": "Remove the duplicate serialization pass and keep a single pass.",
        "preserved_constraints": [
            "Keep correctness validation enabled.",
            "Do not resize the database.",
        ],
        "confidence": "high",
    },
    "INC-104": {
        "status": "conclusive",
        "diagnosis": "Payment-provider tail latency degradation caused the timeouts.",
        "supporting_observation_ids": [
            "OBS-03",
            "OBS-04",
            "OBS-05",
            "OBS-06",
            "OBS-07",
        ],
        "rejected_hypotheses": [
            {
                "hypothesis": "fraud validation CPU",
                "reason": "The corrected stage metric removed downstream wait.",
                "observation_ids": ["OBS-02", "OBS-04"],
            }
        ],
        "recommendation": "Enable the circuit breaker and limit retry with jittered backoff.",
        "preserved_constraints": [
            "Keep fraud validation enabled.",
            "Do not change the provider contract.",
            "Do not rollback during the migration.",
        ],
        "confidence": "high",
    },
    "INC-105": {
        "status": "insufficient_evidence",
        "diagnosis": "The mixed cohorts and missing experiment make the evidence insufficient.",
        "supporting_observation_ids": ["OBS-04", "OBS-06", "OBS-07"],
        "rejected_hypotheses": [
            {
                "hypothesis": "provider or database saturation",
                "reason": "Both samples were invalidated by the cohort correction.",
                "observation_ids": ["OBS-02", "OBS-03", "OBS-04"],
            }
        ],
        "recommendation": "Run a matched-cohort canary and collect a comparable trace sample.",
        "preserved_constraints": [
            "Keep fraud validation enabled.",
            "Do not rollback during the schema migration.",
        ],
        "confidence": "low",
    },
}
 
 
@pytest.mark.parametrize("scenario_id", scenario_ids())
def test_grader_accepts_complete_reference_answers(scenario_id: str) -> None:
    grade = grade_answer(scenario_id, REFERENCE_ANSWERS[scenario_id])
    assert grade["success"] is True
    assert grade["score"] == 100
 
 
def test_grader_rejects_answer_that_ignores_correction_and_constraints() -> None:
    answer = {
        "status": "conclusive",
        "diagnosis": "Database saturation",
        "supporting_observation_ids": ["OBS-03"],
        "rejected_hypotheses": [],
        "recommendation": "Resize the database.",
        "preserved_constraints": [],
    }
    grade = grade_answer("INC-101", answer)
    assert grade["success"] is False
    assert grade["checks"]["correction_ok"] is False
    assert grade["checks"]["constraint_ok"] is False
 
 
def test_adaptive_catalog_and_results_do_not_expose_ground_truth() -> None:
    assert len(probe_catalog()) == 8
    assert len(canary_catalog()) == 5
    for scenario_id in scenario_ids():
        correction = correction_event(scenario_id)
        assert correction["correction_id"].startswith("COR-")
        assert correction["supersedes_probe_ids"]
        for row in probe_catalog():
            result = probe_result(scenario_id, row["probe_id"])
            assert result["probe_id"] == row["probe_id"]
            assert "ground_truth" not in result
 
 
@pytest.mark.parametrize("scenario_id", scenario_ids())
def test_adaptive_tool_path_accepts_required_probes_and_safe_canary(
    scenario_id: str,
) -> None:
    config = ADAPTIVE_CONFIG[scenario_id]
    selected = list(config["required_probe_ids"])
    selected.extend(
        probe["probe_id"]
        for probe in probe_catalog()
        if probe["probe_id"] not in selected
    )
    selected = selected[:4]
    grade = grade_adaptive_tool_path(
        scenario_id, selected, config["safe_canary_id"]
    )
    assert grade["success"] is True
    result = canary_result(scenario_id, config["safe_canary_id"])
    assert result["canary_id"] == config["safe_canary_id"]
    if scenario_id == "INC-105":
        assert result["executed"] is False
    else:
        assert result["executed"] is True
 
 
@pytest.mark.parametrize("scenario_id", scenario_ids())
def test_adaptive_grader_accepts_reference_answers(scenario_id: str) -> None:
    config = ADAPTIVE_CONFIG[scenario_id]
    answer = deepcopy(REFERENCE_ANSWERS[scenario_id])
    answer.pop("supporting_observation_ids")
    answer["supporting_evidence_ids"] = [
        *config["required_probe_ids"],
        f"COR-{scenario_id.removeprefix('INC-')}",
        config["safe_canary_id"],
    ]
    answer["superseded_probe_ids"] = list(config["superseded_probe_ids"])
    grade = grade_adaptive_answer(scenario_id, answer)
    assert grade["success"] is True
    assert grade["score"] == 100
 
 
def test_adaptive_grader_uses_explicit_superseded_probe_contract() -> None:
    answer = {
        "status": "conclusive",
        "diagnosis": "Retry amplification caused by a mismatched timeout budget.",
        "supporting_evidence_ids": [
            "PROBE-04",
            "PROBE-05",
            "COR-101",
            "CANARY-RETRY-BUDGET",
        ],
        "superseded_probe_ids": ["PROBE-02"],
        "rejected_hypotheses": [
            {"hypothesis": "database saturation", "reason": "corrected timing"}
        ],
        "recommendation": "Reduce retry count and add jittered backoff to the timeout.",
        "preserved_constraints": [
            "Keep fraud validation enabled.",
            "Do not rollback during the schema migration.",
        ],
        "confidence": "high",
    }
    grade = grade_adaptive_answer("INC-101", answer)
    assert grade["success"] is True
    assert grade["score"] == 100
 
    answer["superseded_probe_ids"] = []
    failed = grade_adaptive_answer("INC-101", answer)
    assert failed["success"] is False
    assert failed["checks"]["correction_ok"] is False
