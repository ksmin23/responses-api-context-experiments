import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import median
 
import pytest
 
from responses_lab.compaction import (
    GRADER_CALIBRATION_CASES,
    GROUND_TRUTH,
    SCENARIO,
    calibration_approval_issue,
    combine_final_grades,
    experiment_stage_settings,
    grader_calibration_approval_issue,
    grader_response_issue,
    grading_fixture_for_turn_count,
    grade_checkpoint,
    grade_final_report_structure,
    normalize_semantic_grade,
    needs_compaction_continuation,
    observation_ids,
    render_tool_output,
    semantic_grader_payload,
    semantic_grader_schema_for_observation_ids,
    stable_json_sha256,
)
 
 
REFERENCE_REPORT = {
    "status": "conclusive",
    "diagnosis": "Worker-scoped idempotency keys let a shard handoff create a second key for the same invoice event.",
    "causal_chain": "A retry moved to another worker, which changed the idempotency key and admitted a duplicate ledger candidate.",
    "supporting_observation_ids": [
        "OBS-04", "OBS-09", "OBS-10", "OBS-14", "OBS-19", "OBS-20", "OBS-21"
    ],
    "superseded_observation_ids": ["OBS-03", "OBS-05", "OBS-06"],
    "rejected_hypotheses": [
        {"hypothesis": "database connection saturation", "reason": "corrected live metrics"},
        {"hypothesis": "provider connector latency", "reason": "matched control"},
        {"hypothesis": "CPU serialization regression", "reason": "profile stayed flat"},
    ],
    "preserved_constraint_ids": ["CON-01", "CON-02", "CON-03", "CON-04"],
    "recommendation": "Use a stable account and invoice event idempotency key at the deduplication boundary.",
    "confidence": "high",
}
 
 
def test_workload_has_thirty_ordered_observations() -> None:
    assert observation_ids() == [f"OBS-{index:02d}" for index in range(1, 31)]
 
 
def test_workload_has_post_break_even_durability_tail() -> None:
    by_id = {row["id"]: row for row in SCENARIO["observations"]}
    assert by_id["OBS-26"]["checkpoint"] == "post_break_even_durability"
    assert by_id["OBS-27"]["source"] == "regional_rollout_validation"
    assert by_id["OBS-29"]["source"] == "retry_stress_test"
    assert by_id["OBS-30"]["source"] == "final_review"
 
 
def test_regrading_uses_the_artifacts_original_workload_fixture() -> None:
    scenario_24, truth_24 = grading_fixture_for_turn_count(24)
    scenario_30, truth_30 = grading_fixture_for_turn_count(30)
    assert len(scenario_24["observations"]) == 24
    assert scenario_24["observations"][-1]["source"] == "final_review"
    assert len(scenario_30["observations"]) == 30
    assert "OBS-29" in truth_30["semantic_reference"]["strong_supporting_observation_ids"]
    assert "OBS-29" not in truth_24["semantic_reference"]["strong_supporting_observation_ids"]
    schema_24 = semantic_grader_schema_for_observation_ids(
        [row["id"] for row in scenario_24["observations"]]
    )
    allowed_ids = schema_24["properties"]["cited_observation_ids"]["items"]["enum"]
    assert allowed_ids[-1] == "OBS-24"
    assert "OBS-25" not in allowed_ids
 
 
def test_model_visible_fixture_has_no_ground_truth_or_implication() -> None:
    visible = json.dumps(SCENARIO).lower()
    assert "ground_truth" not in visible
    assert "implication" not in visible
 
 
def test_tool_output_is_deterministic_and_model_safe() -> None:
    first = render_tool_output("OBS-09", sample_count=4)
    second = render_tool_output("OBS-09", sample_count=4)
    assert first == second
    payload = json.loads(first)
    assert payload["record"]["id"] == "OBS-09"
    assert "ground_truth" not in payload
 
 
def test_compaction_only_response_requires_continuation() -> None:
    assert needs_compaction_continuation(["compaction"], "") is True
    assert needs_compaction_continuation(["compaction", "message"], "ACK") is False
    assert needs_compaction_continuation(["message"], "ACK") is False
 
 
def test_structural_grader_accepts_reference_report() -> None:
    grade = grade_final_report_structure(REFERENCE_REPORT)
    assert grade["success"] is True
    assert grade["score"] == 100
 
 
def test_structural_grader_rejects_incomplete_report() -> None:
    grade = grade_final_report_structure(
        {
            "status": "conclusive",
            "diagnosis": REFERENCE_REPORT["diagnosis"],
            "supporting_observation_ids": [],
            "superseded_observation_ids": [],
            "rejected_hypotheses": [],
            "preserved_constraint_ids": [],
            "recommendation": "rollback and drop event",
        }
    )
    assert grade["success"] is False
 
 
def test_semantic_payload_is_blind_to_experiment_arm_and_cost() -> None:
    payload = semantic_grader_payload(REFERENCE_REPORT)
    serialized = json.dumps(payload).lower()
    assert "candidate_report" in payload
    assert "compaction_threshold" not in serialized
    assert "cost_usd" not in serialized
    assert '"arm"' not in serialized
 
 
def test_grader_calibration_cases_cover_paraphrase_and_failures() -> None:
    by_id = {case["case_id"]: case for case in GRADER_CALIBRATION_CASES}
    assert by_id["correct-negated-constraint"]["expected_success"] is True
    assert by_id["copied-label-unsupported-chain"]["expected_success"] is False
    assert by_id["wrong-provider-cause"]["expected_success"] is False
    assert by_id["explicit-critical-violation"]["expected_critical_violation"] is True
    assert all(
        grade_final_report_structure(case["report"])["success"]
        for case in GRADER_CALIBRATION_CASES
    )
 
 
def test_hybrid_grader_accepts_semantically_correct_negated_constraint() -> None:
    report = {
        **REFERENCE_REPORT,
        "recommendation": "Deploy the stable key without rollback or event loss.",
    }
    structure = grade_final_report_structure(report)
    semantic = normalize_semantic_grade(
        {
            "dimension_scores": {
                "diagnosis_and_causal_chain": 30,
                "evidence_fidelity": 20,
                "corrections": 15,
                "constraints": 15,
                "rejected_hypotheses": 10,
                "recommendation": 10,
            },
            "critical_constraint_violation": False,
            "critical_violation_explanation": "Rollback is prohibited, not proposed.",
            "cited_observation_ids": ["OBS-14", "OBS-19"],
            "summary": "Correct and supported.",
            "issues": [],
        }
    )
    grade = combine_final_grades(structure, semantic)
    assert grade["success"] is True
    assert grade["score"] == 100
 
 
def test_hybrid_grader_hard_fails_structurally_invalid_report() -> None:
    structure = grade_final_report_structure({})
    semantic = {
        "score": 100,
        "success": True,
        "critical_constraint_violation": False,
    }
    grade = combine_final_grades(structure, semantic)
    assert grade["success"] is False
    assert grade["score"] == 0
 
 
def test_grader_response_contract_distinguishes_incomplete_and_empty_output() -> None:
    incomplete = grader_response_issue(
        status="incomplete",
        incomplete_reason="max_output_tokens",
        output_text="",
        output_types=["reasoning"],
    )
    empty = grader_response_issue(
        status="completed",
        incomplete_reason=None,
        output_text="",
        output_types=["message"],
    )
    complete = grader_response_issue(
        status="completed",
        incomplete_reason=None,
        output_text='{"dimension_scores": {}}',
        output_types=["message"],
    )
    assert incomplete == "grader response incomplete: max_output_tokens"
    assert empty == "grader response completed without output text"
    assert complete is None
 
 
def test_invalid_grader_response_is_not_converted_to_quality_zero() -> None:
    structure = grade_final_report_structure(REFERENCE_REPORT)
    grade = combine_final_grades(
        structure,
        {
            "valid": False,
            "score": None,
            "success": False,
            "critical_constraint_violation": False,
            "error": "grader response incomplete: max_output_tokens",
        },
    )
    assert grade["evaluation_valid"] is False
    assert grade["score"] is None
    assert grade["success"] is False
 
 
def test_persisted_calibration_approval_survives_a_kernel_restart() -> None:
    expected = {
        "model": "gpt-5.6",
        "turn_count": 30,
        "output_reserve_tokens": 25_000,
        "compaction_thresholds": {"early": 21_000, "middle": 41_000, "late": 61_000},
    }
    persisted = {
        **expected,
        "status": "accepted",
        "thresholds_within_tolerance": True,
    }
    assert calibration_approval_issue(persisted, expected) is None
 
 
def test_persisted_calibration_rejects_stale_or_failed_configuration() -> None:
    expected = {
        "model": "gpt-5.6",
        "turn_count": 30,
        "output_reserve_tokens": 25_000,
        "compaction_thresholds": {"early": 21_000, "middle": 41_000, "late": 61_000},
    }
    stale = {
        **expected,
        "status": "accepted",
        "thresholds_within_tolerance": True,
        "turn_count": 24,
    }
    rejected = {
        **expected,
        "status": "rejected",
        "thresholds_within_tolerance": False,
    }
    assert "turn_count" in calibration_approval_issue(stale, expected)
    assert "not accepted" in calibration_approval_issue(rejected, expected)
 
 
def test_grader_calibration_approval_survives_restart_with_same_contract() -> None:
    expected = {
        "grader_model": "gpt-5.6-luna",
        "grader_reasoning_effort": "medium",
        "grader_pass_score": 90,
        "grader_max_output_tokens": 4_096,
        "rubric_hash": stable_json_sha256({"pass_score": 90}),
    }
    persisted = {
        **expected,
        "status": "accepted",
        "agreement": 1.0,
        "all_evaluations_valid": True,
    }
    assert grader_calibration_approval_issue(persisted, expected) is None
 
 
def test_grader_calibration_rejects_invalid_or_stale_contract() -> None:
    expected = {
        "grader_model": "gpt-5.6-luna",
        "grader_pass_score": 90,
        "rubric_hash": stable_json_sha256({"pass_score": 90}),
    }
    invalid = {
        **expected,
        "status": "rejected",
        "agreement": 1.0,
        "all_evaluations_valid": False,
    }
    stale = {
        **expected,
        "status": "accepted",
        "agreement": 1.0,
        "all_evaluations_valid": True,
        "grader_pass_score": 80,
    }
    assert "not accepted" in grader_calibration_approval_issue(invalid, expected)
    assert "grader_pass_score" in grader_calibration_approval_issue(stale, expected)
 
 
def test_grader_calibration_requires_every_predeclared_case_result() -> None:
    expected = {
        "grader_model": "gpt-5.6-luna",
        "calibration_case_ids": ["case-a", "case-b"],
    }
    incomplete = {
        **expected,
        "status": "accepted",
        "agreement": 1.0,
        "all_evaluations_valid": True,
        "result_count": 1,
        "results": [
            {"case_id": "case-a", "matched": True, "evaluation_valid": True}
        ],
    }
    assert "case results" in grader_calibration_approval_issue(incomplete, expected)
 
 
def test_stable_json_hash_is_order_independent_and_value_sensitive() -> None:
    assert stable_json_sha256({"b": 2, "a": 1}) == stable_json_sha256(
        {"a": 1, "b": 2}
    )
    assert stable_json_sha256({"a": 1}) != stable_json_sha256({"a": 2})
 
 
@pytest.mark.parametrize(
    ("stage", "enabled_flag", "resume_path"),
    [
        ("preflight", None, None),
        ("grader_calibration", "run_grader_calibration", None),
        ("threshold_calibration", "run_calibration", None),
        ("benchmark_new", "run_benchmark", None),
        ("benchmark_resume", "run_benchmark", "latest"),
    ],
)
def test_experiment_stage_settings_select_exactly_one_paid_mode(
    stage: str, enabled_flag: str | None, resume_path: str | None
) -> None:
    settings = experiment_stage_settings(stage, benchmark_resume_path="latest")
    paid_flags = [
        "run_grader_calibration",
        "run_calibration",
        "run_benchmark",
        "run_regrading",
    ]
    assert sum(bool(settings[name]) for name in paid_flags) == (enabled_flag is not None)
    if enabled_flag is not None:
        assert settings[enabled_flag] is True
    assert settings["resume_results_path"] == resume_path
 
 
def test_uniform_regrade_stage_requires_explicit_source_path() -> None:
    with pytest.raises(ValueError, match="regrade_results_path"):
        experiment_stage_settings("uniform_regrade")
    settings = experiment_stage_settings(
        "uniform_regrade", regrade_results_path="artifacts/results.json"
    )
    assert settings["run_regrading"] is True
    assert settings["regrade_results_path"] == "artifacts/results.json"
 
 
def test_unknown_experiment_stage_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown experiment stage"):
        experiment_stage_settings("benchmark_typo")
 
 
def test_checkpoint_requires_long_range_state() -> None:
    grade = grade_checkpoint(
        {
            "active_hypotheses": ["retry handling"],
            "superseded_observation_ids": ["OBS-03"],
            "preserved_constraint_ids": ["CON-01", "CON-02", "CON-03", "CON-04"],
            "unresolved_questions": ["key scope"],
        },
        turn=8,
    )
    assert grade["success"] is True
 
 
def test_late_checkpoint_must_retain_both_prior_corrections() -> None:
    report = {
        "active_hypotheses": ["retry handling"],
        "superseded_observation_ids": ["OBS-03"],
        "preserved_constraint_ids": ["CON-01", "CON-02", "CON-03", "CON-04"],
        "unresolved_questions": ["key scope"],
    }
    grade = grade_checkpoint(report, turn=16)
    assert grade["success"] is False
    assert grade["checks"]["corrections_retained"] is False
 
 
def test_notebook_requests_fast_mode_and_records_effective_tier() -> None:
    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "03_compaction_break_even_gpt_5_6.ipynb"
    )
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_text = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    assert 'SERVICE_TIER = "fast"' in code_text
    assert '"service_tier": SERVICE_TIER' in code_text
    assert 'getattr(response, "service_tier", None)' in code_text
    assert "FAST_MODE_RATE_MULTIPLIER = 2.0" in code_text
    assert "GRADER_MAX_OUTPUT_TOKENS = 4_096" in code_text
    assert "TRIALS = 10" in code_text
    assert "CHECKPOINT_TURNS = (8, 16, 22, 26, 29)" in code_text
    assert "MIN_POST_BREAK_EVEN_TURNS = 4" in code_text
    assert "REASONING_OUTPUT_RESERVE_TOKENS = 25_000" in code_text
    assert "TURN_MAX_OUTPUT_TOKENS = REASONING_OUTPUT_RESERVE_TOKENS" in code_text
    assert "CHECKPOINT_MAX_OUTPUT_TOKENS = REASONING_OUTPUT_RESERVE_TOKENS" in code_text
    assert "FINAL_MAX_OUTPUT_TOKENS = REASONING_OUTPUT_RESERVE_TOKENS" in code_text
    assert '"early": 21_000' in code_text
    assert '"middle": 41_000' in code_text
    assert '"late": 61_000' in code_text
    assert "MAX_COMPACTION_CONTINUATIONS_PER_TURN = 2" in code_text
    assert "MAX_API_CALLS = 5_000" in code_text
    assert "MAX_OBSERVED_COST_USD = 250.0" in code_text
    assert '"response_status": getattr(response, "status", None)' in code_text
    assert '"continuation_calls"' in code_text
 
 
def test_notebook_persists_failures_and_resumes_completed_arms() -> None:
    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "03_compaction_break_even_gpt_5_6.ipynb"
    )
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_text = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    assert "CONNECT_TIMEOUT_SECONDS = 20.0" in code_text
    assert "max_retries=TRANSPORT_MAX_RETRIES" in code_text
    assert 'EXPERIMENT_STAGE = "preflight"' in code_text
    assert "stage_settings = experiment_stage_settings(" in code_text
    assert 'RUN_BENCHMARK = stage_settings["run_benchmark"]' in code_text
    assert 'RESUME_RESULTS_PATH = stage_settings["resume_results_path"]' in code_text
    assert "def append_failure_log(record: dict) -> Path:" in code_text
    assert '"event": "openai_api_failure"' in code_text
    assert 'completed_runs = {' in code_text
    assert "if run_key in completed_runs:" in code_text
    assert 'status="interrupted"' in code_text
    assert 'RUN_REGRADING = stage_settings["run_regrading"]' in code_text
    assert 'REGRADE_RESULTS_PATH = stage_settings["regrade_results_path"]' in code_text
    assert 'GRADER_CALIBRATION_RESULTS_PATH = "latest"' in code_text
    assert '"event": "grader_response_failure"' in code_text
    assert "def persist_grader_calibration_result(" in code_text
    assert "def load_grader_calibration_approval(" in code_text
    assert '"grader_calibration_artifact_path"' in code_text
    assert '"threshold_calibration_artifact_path"' in code_text
    assert "def regrade_saved_results(" in code_text
    assert '"evaluation_valid_rate"' in code_text
 
    notebook_text = "\n".join(
        "".join(cell.get("source", [])) for cell in notebook["cells"]
    )
    assert "restart the kernel" not in notebook_text.lower()
    assert "Run All Below" in notebook_text
 
 
def test_notebook_uses_fresh_calibration_and_paired_incremental_break_even() -> None:
    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "03_compaction_break_even_gpt_5_6.ipynb"
    )
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_text = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    assert "if calibration_thresholds_valid is not True:" not in code_text
    assert "def persist_calibration_result(" in code_text
    assert "def load_calibration_approval(" in code_text
    assert "calibration_approval = load_calibration_approval()" in code_text
    assert "def paired_incremental_cost_curve(" in code_text
    assert "pretreatment_delta" in code_text
    assert "def paired_sustained_break_even_turn(" in code_text
    assert 'required_pairs=TRIALS' in code_text
    assert "minimum_tail_turns=MIN_POST_BREAK_EVEN_TURNS" in code_text
 
 
def test_paired_break_even_normalizes_pretreatment_cost_differences() -> None:
    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "03_compaction_break_even_gpt_5_6.ipynb"
    )
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = next(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
        and "def paired_incremental_cost_curve(" in "".join(cell["source"])
    )
    namespace = {
        "defaultdict": defaultdict,
        "median": median,
        "random": random,
        "RANDOM_SEED": 56,
        "TRIALS": 2,
        "benchmark_results": [],
    }
    exec(compile(source, "notebook-break-even-cell", "exec"), namespace)
 
    def result(trial: int, arm: str, costs: list[float]) -> dict:
        return {
            "trial": trial,
            "arm": arm,
            "compaction_turns": [] if arm == "baseline" else [3],
            "rows": [
                {"turn": turn, "cumulative_cost_usd": cost}
                for turn, cost in enumerate(costs, start=1)
            ],
        }
 
    results = [
        result(1, "baseline", [1.0, 2.0, 3.0, 4.0]),
        result(1, "early", [1.2, 2.2, 3.4, 3.8]),
        result(2, "baseline", [0.9, 1.9, 2.9, 3.9]),
        result(2, "early", [0.8, 1.8, 3.0, 3.4]),
    ]
    curve = namespace["paired_incremental_cost_curve"](results, "early")
    crossing = namespace["paired_sustained_break_even_turn"](
        curve, required_pairs=2, minimum_tail_turns=0
    )
    assert curve[3]["pairs"] == 2
    assert curve[3]["median_delta_usd"] == pytest.approx(0.2)
    assert curve[4]["median_delta_usd"] == pytest.approx(-0.4)
    assert crossing == 4
