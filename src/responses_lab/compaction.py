"""Deterministic long-context workload and hidden grader for Notebook 03."""
 
from __future__ import annotations
 
import hashlib
import json
import random
from pathlib import Path
from typing import Any
 
 
def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]
 
 
def _read_fixture(name: str) -> Any:
    path = _project_root() / "fixtures" / "compaction" / name
    return json.loads(path.read_text(encoding="utf-8"))
 
 
SCENARIO = _read_fixture("scenario.json")
GROUND_TRUTH = _read_fixture("ground_truth.json")
LEGACY_SCENARIO_24 = _read_fixture("scenario_24.json")
LEGACY_GROUND_TRUTH_24 = _read_fixture("ground_truth_24.json")
GRADER_CALIBRATION_CASES = _read_fixture("grader_calibration.json")
 
 
EXPERIMENT_STAGES = (
    "preflight",
    "grader_calibration",
    "threshold_calibration",
    "benchmark_new",
    "benchmark_resume",
    "uniform_regrade",
)
 
 
def experiment_stage_settings(
    stage: str,
    *,
    benchmark_resume_path: str | None = "latest",
    regrade_results_path: str | None = None,
) -> dict[str, Any]:
    """Map one human-facing stage to mutually exclusive notebook settings."""
    if stage not in EXPERIMENT_STAGES:
        raise ValueError(
            f"Unknown experiment stage {stage!r}; choose one of {EXPERIMENT_STAGES}"
        )
    settings: dict[str, Any] = {
        "stage": stage,
        "run_grader_calibration": False,
        "run_calibration": False,
        "run_benchmark": False,
        "run_regrading": False,
        "resume_results_path": None,
        "regrade_results_path": None,
    }
    if stage == "grader_calibration":
        settings["run_grader_calibration"] = True
    elif stage == "threshold_calibration":
        settings["run_calibration"] = True
    elif stage == "benchmark_new":
        settings["run_benchmark"] = True
    elif stage == "benchmark_resume":
        if not benchmark_resume_path:
            raise ValueError(
                "benchmark_resume requires benchmark_resume_path, usually 'latest'"
            )
        settings["run_benchmark"] = True
        settings["resume_results_path"] = benchmark_resume_path
    elif stage == "uniform_regrade":
        if not regrade_results_path or regrade_results_path == "latest":
            raise ValueError(
                "uniform_regrade requires an explicit regrade_results_path"
            )
        settings["run_regrading"] = True
        settings["regrade_results_path"] = regrade_results_path
    return settings
 
 
def grading_fixture_for_turn_count(turn_count: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the exact evaluation fixture used by a persisted workload version."""
    if turn_count == len(SCENARIO["observations"]):
        return SCENARIO, GROUND_TRUTH
    if turn_count == len(LEGACY_SCENARIO_24["observations"]):
        return LEGACY_SCENARIO_24, LEGACY_GROUND_TRUTH_24
    raise ValueError(f"No grading fixture is registered for turn_count={turn_count}")
 
 
def workload_overview() -> dict[str, Any]:
    """Return model-safe, human-readable workload metadata."""
    return {
        "scenario_id": SCENARIO["scenario_id"],
        "name": SCENARIO["name"],
        "description": SCENARIO["description"],
        "turn_count": len(SCENARIO["observations"]),
    }
 
 
def initial_prompt() -> str:
    return str(SCENARIO["initial_prompt"])
 
 
def observation_ids() -> list[str]:
    return [row["id"] for row in SCENARIO["observations"]]
 
 
def observation(observation_id: str) -> dict[str, Any]:
    for row in SCENARIO["observations"]:
        if row["id"] == observation_id:
            return dict(row)
    raise KeyError(observation_id)
 
 
def render_tool_output(
    observation_id: str,
    *,
    sample_count: int = 72,
    seed: int = 56,
) -> str:
    """Render a fixed-size realistic tool payload without grading hints."""
    record = observation(observation_id)
    sample_rng = random.Random(f"{SCENARIO['scenario_id']}:{observation_id}:{seed}")
    samples = [
        {
            "sample_id": f"{observation_id}-{index:04d}",
            "region": sample_rng.choice(["ap-northeast", "us-east", "eu-west"]),
            "worker_pool": sample_rng.choice(["pool-a", "pool-b", "pool-c"]),
            "latency_bucket": sample_rng.choice(["lt-5m", "5m-15m", "gt-15m"]),
            "retry_count": sample_rng.choice([0, 0, 1, 1, 2, 3]),
            "observation_ref": observation_id,
        }
        for index in range(sample_count)
    ]
    return json.dumps(
        {
            "scenario_id": SCENARIO["scenario_id"],
            "record": record,
            "diagnostic_samples": samples,
            "sample_count": sample_count,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
 
 
def parse_json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines.pop()
        candidate = "\n".join(lines).strip()
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed
 
 
def needs_compaction_continuation(
    output_types: list[str], output_text: str
) -> bool:
    """Return whether server-side compaction produced no assistant message yet."""
    return (
        "compaction" in output_types
        and "message" not in output_types
        and not output_text.strip()
    )
 
 
def grader_response_issue(
    *,
    status: str | None,
    incomplete_reason: str | None,
    output_text: str,
    output_types: list[str],
) -> str | None:
    """Return a contract failure without treating it as a quality score."""
    if status != "completed":
        reason = incomplete_reason or "unknown_reason"
        return f"grader response {status or 'unknown'}: {reason}"
    if not output_text.strip():
        if "refusal" in output_types:
            return "grader response refused the structured evaluation"
        return "grader response completed without output text"
    return None
 
 
def stable_json_sha256(value: Any) -> str:
    """Return a deterministic hash for a JSON-compatible contract value."""
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
 
 
def grader_calibration_approval_issue(
    payload: dict[str, Any], expected: dict[str, Any]
) -> str | None:
    """Validate a persisted semantic-grader calibration approval."""
    if (
        payload.get("status") != "accepted"
        or payload.get("agreement") != 1.0
        or payload.get("all_evaluations_valid") is not True
    ):
        return "grader calibration artifact is not accepted"
    mismatches = {
        key: {"expected": value, "observed": payload.get(key)}
        for key, value in expected.items()
        if payload.get(key) != value
    }
    if mismatches:
        return "grader calibration artifact is incompatible: " + json.dumps(
            mismatches, ensure_ascii=False, sort_keys=True
        )
    expected_case_ids = expected.get("calibration_case_ids")
    if expected_case_ids is not None:
        results = payload.get("results")
        observed_case_ids = (
            [row.get("case_id") for row in results]
            if isinstance(results, list)
            else None
        )
        valid_results = (
            isinstance(results, list)
            and payload.get("result_count") == len(expected_case_ids)
            and observed_case_ids == expected_case_ids
            and all(
                row.get("matched") is True
                and row.get("evaluation_valid") is True
                for row in results
            )
        )
        if not valid_results:
            return "grader calibration artifact has incomplete case results"
    return None
 
 
def calibration_approval_issue(
    payload: dict[str, Any], expected: dict[str, Any]
) -> str | None:
    """Validate a persisted threshold calibration against the current run.
 
    The persisted artifact is the hand-off between the calibration kernel and a
    fresh benchmark kernel. It must be explicitly accepted and match every
    configuration field that affects the observed context trajectory.
    """
    if payload.get("status") != "accepted" or payload.get(
        "thresholds_within_tolerance"
    ) is not True:
        return "calibration artifact is not accepted"
    mismatches = {
        key: {"expected": value, "observed": payload.get(key)}
        for key, value in expected.items()
        if payload.get(key) != value
    }
    if mismatches:
        return "calibration artifact is incompatible: " + json.dumps(
            mismatches, ensure_ascii=False, sort_keys=True
        )
    return None
 
 
SEMANTIC_DIMENSION_MAX_POINTS = {
    "diagnosis_and_causal_chain": 30,
    "evidence_fidelity": 20,
    "corrections": 15,
    "constraints": 15,
    "rejected_hypotheses": 10,
    "recommendation": 10,
}
 
 
SEMANTIC_GRADER_SCHEMA = {
    "type": "object",
    "properties": {
        "dimension_scores": {
            "type": "object",
            "properties": {
                name: {"type": "integer", "minimum": 0, "maximum": maximum}
                for name, maximum in SEMANTIC_DIMENSION_MAX_POINTS.items()
            },
            "required": list(SEMANTIC_DIMENSION_MAX_POINTS),
            "additionalProperties": False,
        },
        "critical_constraint_violation": {"type": "boolean"},
        "critical_violation_explanation": {"type": "string"},
        "cited_observation_ids": {
            "type": "array",
            "items": {"type": "string", "enum": observation_ids()},
        },
        "summary": {"type": "string"},
        "issues": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "dimension_scores",
        "critical_constraint_violation",
        "critical_violation_explanation",
        "cited_observation_ids",
        "summary",
        "issues",
    ],
    "additionalProperties": False,
}
 
 
def semantic_grader_schema_for_observation_ids(
    allowed_observation_ids: list[str],
) -> dict[str, Any]:
    """Return a version-scoped structured-output schema for regrading."""
    schema = json.loads(json.dumps(SEMANTIC_GRADER_SCHEMA))
    schema["properties"]["cited_observation_ids"]["items"]["enum"] = list(
        allowed_observation_ids
    )
    return schema
 
 
def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)
 
 
def grade_final_report_structure(report: dict[str, Any]) -> dict[str, Any]:
    """Apply only deterministic schema and hard-contract checks.
 
    Semantic correctness, evidence sufficiency, and negated constraints belong to
    the model grader. This avoids treating a keyword such as ``rollback`` as a
    violation when the candidate says ``without rollback``.
    """
    valid_observations = set(observation_ids())
    supporting = report.get("supporting_observation_ids")
    superseded = report.get("superseded_observation_ids")
    constraints = report.get("preserved_constraint_ids")
    rejected = report.get("rejected_hypotheses")
    observed_ids = set(supporting or []) | set(superseded or [])
    checks = {
        "status": report.get("status") == GROUND_TRUTH["expected_status"],
        "diagnosis_present": bool(str(report.get("diagnosis", "")).strip()),
        "causal_chain_present": bool(str(report.get("causal_chain", "")).strip()),
        "recommendation_present": bool(str(report.get("recommendation", "")).strip()),
        "supporting_ids_valid": _is_string_list(supporting)
        and bool(supporting)
        and set(supporting).issubset(valid_observations),
        "superseded_ids_valid": _is_string_list(superseded)
        and set(superseded).issubset(valid_observations),
        "required_corrections_recorded": _is_string_list(superseded)
        and set(GROUND_TRUTH["required_superseded_observation_ids"]).issubset(superseded),
        "required_constraints_recorded": _is_string_list(constraints)
        and set(GROUND_TRUTH["required_constraint_ids"]).issubset(constraints),
        "no_unknown_observation_ids": observed_ids.issubset(valid_observations),
        "rejected_hypotheses_well_formed": isinstance(rejected, list)
        and bool(rejected)
        and all(
            isinstance(item, dict)
            and bool(str(item.get("hypothesis", "")).strip())
            and bool(str(item.get("reason", "")).strip())
            for item in rejected
        ),
        "confidence_valid": report.get("confidence") in {"low", "medium", "high"},
    }
    score = round(100 * sum(checks.values()) / len(checks))
    return {"score": score, "success": all(checks.values()), "checks": checks}
 
 
def semantic_grader_payload(
    report: dict[str, Any],
    *,
    scenario: dict[str, Any] | None = None,
    ground_truth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a blind grading payload with no arm, threshold, latency, or cost data."""
    scenario = SCENARIO if scenario is None else scenario
    ground_truth = GROUND_TRUTH if ground_truth is None else ground_truth
    return {
        "task": {
            "scenario_id": scenario["scenario_id"],
            "initial_prompt": scenario["initial_prompt"],
            "observations": scenario["observations"],
        },
        "evaluation_reference": ground_truth["semantic_reference"],
        "candidate_report": report,
        "rubric": {
            "dimension_max_points": SEMANTIC_DIMENSION_MAX_POINTS,
            "pass_score": 90,
            "instructions": [
                "Judge meaning across the entire report, not keyword presence.",
                "Require claims to be supported by the supplied observations.",
                "Treat an action mentioned only to reject or prohibit it as compliant.",
                "Do not reward copied labels unsupported by a coherent causal chain.",
            ],
        },
    }
 
 
def normalize_semantic_grade(
    raw_grade: dict[str, Any], *, pass_score: int = 90
) -> dict[str, Any]:
    """Validate a structured model grade and calculate its score locally."""
    scores = raw_grade.get("dimension_scores")
    if not isinstance(scores, dict):
        raise ValueError("Semantic grade is missing dimension_scores")
    for name, maximum in SEMANTIC_DIMENSION_MAX_POINTS.items():
        value = scores.get(name)
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= maximum:
            raise ValueError(f"Invalid semantic score for {name}: {value!r}")
    critical_violation = raw_grade.get("critical_constraint_violation")
    if not isinstance(critical_violation, bool):
        raise ValueError("critical_constraint_violation must be boolean")
    score = sum(scores[name] for name in SEMANTIC_DIMENSION_MAX_POINTS)
    return {
        **raw_grade,
        "valid": True,
        "score": score,
        "success": score >= pass_score and not critical_violation,
    }
 
 
def combine_final_grades(
    structure_grade: dict[str, Any], semantic_grade: dict[str, Any]
) -> dict[str, Any]:
    """Combine a deterministic hard gate with a semantic model score."""
    structure_passed = bool(structure_grade.get("success"))
    evaluation_valid = bool(semantic_grade.get("valid", True))
    semantic_passed = bool(semantic_grade.get("success"))
    return {
        "score": (
            semantic_grade.get("score", 0)
            if structure_passed and evaluation_valid
            else (0 if not structure_passed else None)
        ),
        "success": structure_passed and evaluation_valid and semantic_passed,
        "evaluation_valid": evaluation_valid,
        "critical_constraint_violation": bool(
            semantic_grade.get("critical_constraint_violation", False)
        ),
        "structure_grade": structure_grade,
        "semantic_grade": semantic_grade,
    }
 
 
def grade_checkpoint(report: dict[str, Any], *, turn: int) -> dict[str, Any]:
    """Check long-range state without requiring the final diagnosis."""
    constraints = set(report.get("preserved_constraint_ids") or [])
    superseded = set(report.get("superseded_observation_ids") or [])
    required_constraints = set(GROUND_TRUTH["required_constraint_ids"])
    seen_corrections = {value for value in superseded if value in {"OBS-03", "OBS-05", "OBS-06"}}
    required_corrections = {"OBS-03"}
    if turn >= 16:
        required_corrections.add("OBS-05")
    if turn >= 24:
        required_corrections.add("OBS-06")
    checks = {
        "constraints": required_constraints.issubset(constraints),
        "corrections_are_valid": superseded.issubset({"OBS-03", "OBS-05", "OBS-06"}),
        "corrections_retained": required_corrections.issubset(superseded),
        "has_working_hypotheses": bool(report.get("active_hypotheses")),
        "has_unresolved_questions": isinstance(report.get("unresolved_questions"), list),
    }
    return {
        "score": round(100 * sum(checks.values()) / len(checks)),
        "success": all(checks.values()),
        "seen_correction_count": len(seen_corrections),
        "checks": checks,
    }
