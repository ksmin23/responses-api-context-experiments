"""Deterministic fixtures and grading for the retained-reasoning notebook."""
 
from __future__ import annotations
 
import json
from copy import deepcopy
from typing import Any
 
 
SCENARIOS: dict[str, dict[str, Any]] = {
    "INC-101": {
        "category": "single_cause",
        "title": "Retry amplification after a checkout deployment",
        "initial_prompt": (
            "Investigate checkout latency after release 2026.08.26.3. p95 rose from "
            "420 ms to 780 ms and timeout rate from 0.5% to 8.1%. Rollback is unavailable "
            "because the release includes an active schema migration. Fraud validation must "
            "remain enabled. Consider database saturation, payment-provider latency, "
            "application CPU or serialization regression, and retry amplification. Keep the "
            "same investigation goal and constraints through the final turn. Reply only with "
            "a short acknowledgement; do not publish a cumulative investigation summary."
        ),
        "observations": {
            "OBS-02": {
                "source": "payment_provider_metrics",
                "baseline_p95_ms": 310,
                "current_p95_ms": 325,
                "baseline_error_rate_percent": 0.3,
                "current_error_rate_percent": 0.3,
                "sample_size": 18000,
            },
            "OBS-03": {
                "source": "database_pool_metrics",
                "baseline_connection_occupancy_percent": 61,
                "current_connection_occupancy_percent": 93,
                "baseline_wait_p95_ms": 8,
                "current_wait_p95_ms": 42,
            },
            "OBS-04": {
                "source": "database_metric_correction",
                "supersedes_observation_id": "OBS-03",
                "reason": "retry attempts were counted as independent database operations",
                "baseline_unique_request_db_p95_ms": 71,
                "current_unique_request_db_p95_ms": 74,
                "corrected_wait_p95_ms": 9,
            },
            "OBS-05": {
                "source": "request_trace_cohort",
                "retry_count_p95": 4,
                "timeout_rate_percent": 7.8,
                "zero_retry_timeout_rate_percent": 0.6,
                "sample_size": 12400,
            },
            "OBS-06": {
                "source": "client_configuration",
                "client_timeout_ms": 600,
                "payment_provider_p99_ms": 720,
                "max_retries": 3,
                "retry_backoff": "none",
                "retry_jitter": False,
            },
            "OBS-07": {
                "source": "canary_result",
                "canary_configuration": {
                    "client_timeout_ms": 800,
                    "max_retries": 1,
                    "retry_backoff": "exponential_with_jitter",
                },
                "checkout_p95_ms": 455,
                "timeout_rate_percent": 0.9,
                "fraud_mismatch_count": 0,
                "sample_size": 26000,
            },
        },
        "ground_truth": {
            "expected_status": "conclusive",
            "diagnosis_keyword_groups": [["retry"], ["timeout", "budget"]],
            "required_evidence": ["OBS-04", "OBS-05", "OBS-06", "OBS-07"],
            "invalidated_evidence": ["OBS-03"],
            "constraint_keyword_groups": [["fraud"], ["rollback", "schema"]],
            "recommendation_keyword_groups": [["retry"], ["jitter", "backoff", "timeout"]],
        },
    },
    "INC-102": {
        "category": "late_correction",
        "title": "Connection-pool queueing hidden by a corrected provider trace",
        "initial_prompt": (
            "Investigate checkout p95 increasing from 410 ms to 690 ms after capacity was "
            "doubled. Do not change the database schema and do not shed premium traffic. "
            "Consider database saturation, payment-provider latency, application CPU or "
            "serialization regression, and retry amplification. Preserve these constraints. "
            "Reply only with a short acknowledgement; do not publish a cumulative summary."
        ),
        "observations": {
            "OBS-02": {
                "source": "distributed_trace",
                "payment_provider_span_p95_ms": 905,
                "sample_size": 9200,
                "collector_region": "ap-northeast",
            },
            "OBS-03": {
                "source": "application_thread_profile",
                "threads_waiting_for_db_connection_percent": 62,
                "pool_in_use": 40,
                "pool_max": 40,
                "query_runtime_p95_ms": 39,
            },
            "OBS-04": {
                "source": "trace_timing_correction",
                "supersedes_observation_id": "OBS-02",
                "collector_clock_offset_ms": 575,
                "corrected_payment_provider_span_p95_ms": 330,
                "provider_error_rate_percent": 0.2,
            },
            "OBS-05": {
                "source": "database_queue_metrics",
                "connection_acquire_p95_ms": 244,
                "query_runtime_p95_ms": 41,
                "database_cpu_percent": 46,
                "sample_size": 15000,
            },
            "OBS-06": {
                "source": "pool_configuration",
                "application_replicas_before": 8,
                "application_replicas_after": 16,
                "pool_max_per_cluster": 40,
                "approved_connection_budget": 64,
            },
            "OBS-07": {
                "source": "canary_result",
                "canary_pool_max": 56,
                "checkout_p95_ms": 438,
                "timeout_rate_percent": 0.7,
                "database_cpu_percent": 50,
                "premium_requests_dropped": 0,
                "sample_size": 21000,
            },
        },
        "ground_truth": {
            "expected_status": "conclusive",
            "diagnosis_keyword_groups": [["connection", "pool"], ["queue", "saturation", "exhaust"]],
            "required_evidence": ["OBS-03", "OBS-04", "OBS-05", "OBS-06", "OBS-07"],
            "invalidated_evidence": ["OBS-02"],
            "constraint_keyword_groups": [["schema"], ["premium", "shed", "drop"]],
            "recommendation_keyword_groups": [["pool", "connection"], ["56", "increase", "raise"]],
        },
    },
    "INC-103": {
        "category": "distractor_heavy",
        "title": "Duplicate serialization work behind a shared-database distractor",
        "initial_prompt": (
            "Investigate checkout p95 increasing from 390 ms to 735 ms after an application "
            "release. Correctness validation must remain enabled and the shared database "
            "cluster cannot be resized during the incident window. Consider database "
            "saturation, payment-provider latency, application CPU or serialization "
            "regression, and retry amplification. Reply only with a short acknowledgement."
        ),
        "observations": {
            "OBS-02": {
                "source": "shared_database_cluster",
                "baseline_cpu_percent": 54,
                "current_cpu_percent": 88,
                "checkout_latency_correlation": 0.82,
            },
            "OBS-03": {
                "source": "payment_provider_metrics",
                "baseline_p95_ms": 300,
                "current_p95_ms": 304,
                "current_error_rate_percent": 0.2,
            },
            "OBS-04": {
                "source": "database_workload_correction",
                "supersedes_observation_id": "OBS-02",
                "batch_job_cpu_share_percent": 34,
                "checkout_query_p95_before_ms": 43,
                "checkout_query_p95_current_ms": 45,
                "checkout_only_cpu_percent": 55,
            },
            "OBS-05": {
                "source": "application_cpu_profile",
                "serialization_cpu_share_before_percent": 18,
                "serialization_cpu_share_current_percent": 47,
                "payload_bytes_change_percent": 1.2,
                "sample_size": 11000,
            },
            "OBS-06": {
                "source": "request_stage_counters",
                "validation_calls_per_request_before": 1.0,
                "validation_calls_per_request_current": 1.0,
                "serialization_passes_per_request_before": 1.0,
                "serialization_passes_per_request_current": 1.96,
            },
            "OBS-07": {
                "source": "canary_result",
                "serialization_passes_per_request": 1.0,
                "validation_calls_per_request": 1.0,
                "checkout_p95_ms": 416,
                "validation_mismatch_count": 0,
                "sample_size": 24000,
            },
        },
        "ground_truth": {
            "expected_status": "conclusive",
            "diagnosis_keyword_groups": [["serialization"], ["duplicate", "twice", "pass"]],
            "required_evidence": ["OBS-04", "OBS-05", "OBS-06", "OBS-07"],
            "invalidated_evidence": ["OBS-02"],
            "constraint_keyword_groups": [["validation", "correctness"], ["database", "resize"]],
            "recommendation_keyword_groups": [["serialization"], ["single", "duplicate", "pass"]],
        },
    },
    "INC-104": {
        "category": "constraint_conflict",
        "title": "Provider tail latency with a prohibited shortcut",
        "initial_prompt": (
            "Investigate checkout timeout growth during a provider degradation. Fraud "
            "validation must remain enabled, the provider contract cannot be changed today, "
            "and rollback is blocked by an active migration. Consider database saturation, "
            "payment-provider latency, application CPU or serialization regression, and "
            "retry amplification. Reply only with a short acknowledgement."
        ),
        "observations": {
            "OBS-02": {
                "source": "stage_timing",
                "fraud_stage_reported_p95_ms": 610,
                "baseline_fraud_stage_reported_p95_ms": 120,
            },
            "OBS-03": {
                "source": "payment_provider_metrics",
                "provider_p50_ms": 315,
                "provider_p99_ms": 1180,
                "provider_error_rate_percent": 4.8,
                "sample_size": 17000,
            },
            "OBS-04": {
                "source": "stage_timing_correction",
                "supersedes_observation_id": "OBS-02",
                "fraud_stage_own_cpu_p95_ms": 74,
                "downstream_wait_included_in_original_metric": True,
                "fraud_decision_mismatch_count": 0,
            },
            "OBS-05": {
                "source": "retry_overlap_trace",
                "requests_with_overlapping_provider_attempts_percent": 38,
                "overlap_timeout_rate_percent": 12.4,
                "single_attempt_timeout_rate_percent": 2.1,
            },
            "OBS-06": {
                "source": "resilience_configuration",
                "circuit_breaker_enabled": False,
                "max_retries": 2,
                "retry_backoff": "immediate",
                "idempotency_key_enabled": True,
            },
            "OBS-07": {
                "source": "canary_result",
                "circuit_breaker_enabled": True,
                "max_retries": 1,
                "retry_backoff": "exponential_with_jitter",
                "checkout_timeout_rate_percent": 1.6,
                "fraud_validation_enabled": True,
                "duplicate_charge_count": 0,
                "sample_size": 28000,
            },
        },
        "ground_truth": {
            "expected_status": "conclusive",
            "diagnosis_keyword_groups": [["provider"], ["tail", "latency", "degradation"]],
            "required_evidence": ["OBS-03", "OBS-04", "OBS-05", "OBS-06", "OBS-07"],
            "invalidated_evidence": ["OBS-02"],
            "constraint_keyword_groups": [["fraud"], ["provider", "contract"], ["rollback", "migration"]],
            "recommendation_keyword_groups": [["circuit breaker", "breaker"], ["jitter", "backoff", "retry"]],
        },
    },
    "INC-105": {
        "category": "insufficient_evidence",
        "title": "Ambiguous checkout regression without a valid cohort or canary",
        "initial_prompt": (
            "Investigate checkout p95 increasing from 405 ms to 650 ms. Fraud validation "
            "must remain enabled and rollback is unavailable during schema migration. "
            "Consider database saturation, payment-provider latency, application CPU or "
            "serialization regression, and retry amplification. Do not force a diagnosis "
            "when the observations cannot distinguish the hypotheses. Reply only with a "
            "short acknowledgement."
        ),
        "observations": {
            "OBS-02": {
                "source": "payment_provider_sample",
                "provider_p95_ms": 810,
                "sample_size": 42,
                "region": "unknown",
            },
            "OBS-03": {
                "source": "database_pool_sample",
                "connection_occupancy_percent": 91,
                "sample_size": 55,
                "traffic_cohort": "mixed",
            },
            "OBS-04": {
                "source": "sampling_correction",
                "supersedes_observation_ids": ["OBS-02", "OBS-03"],
                "reason": "samples combined canary and production regions with different load",
                "valid_comparable_sample_size": 0,
            },
            "OBS-05": {
                "source": "request_trace_sample",
                "retry_timeout_correlation": 0.71,
                "sample_size": 37,
                "release_version": "mixed",
            },
            "OBS-06": {
                "source": "configuration_inventory",
                "pods_checked": 3,
                "total_pods": 24,
                "timeout_values_ms": [600, 800],
                "retry_limits": [1, 3],
            },
            "OBS-07": {
                "source": "experiment_status",
                "matched_cohort_canary_run": False,
                "reason": "traffic allocation approval pending",
                "next_available_window": "2026-08-27T02:00:00Z",
            },
        },
        "ground_truth": {
            "expected_status": "insufficient_evidence",
            "diagnosis_keyword_groups": [],
            "required_evidence": ["OBS-04", "OBS-06", "OBS-07"],
            "invalidated_evidence": ["OBS-02", "OBS-03"],
            "constraint_keyword_groups": [["fraud"], ["rollback", "schema", "migration"]],
            "recommendation_keyword_groups": [["canary", "cohort", "sample"], ["trace", "measure", "collect", "compare"]],
        },
    },
}
 
 
def scenario_ids() -> list[str]:
    """Return scenario IDs in stable notebook order."""
    return list(SCENARIOS)
 
 
def scenario_overview() -> list[dict[str, Any]]:
    """Return model-safe metadata for the notebook's workload explanation."""
    return [
        {
            "scenario_id": scenario_id,
            "category": scenario["category"],
            "title": scenario["title"],
            "observation_count": len(scenario["observations"]),
        }
        for scenario_id, scenario in SCENARIOS.items()
    ]
 
 
def initial_prompt(scenario_id: str) -> str:
    return str(SCENARIOS[scenario_id]["initial_prompt"])
 
 
def observation_ids(scenario_id: str) -> list[str]:
    return list(SCENARIOS[scenario_id]["observations"])
 
 
def observation(scenario_id: str, observation_id: str) -> dict[str, Any]:
    """Return only raw observation data; never expose local grading criteria."""
    record = deepcopy(SCENARIOS[scenario_id]["observations"][observation_id])
    return {"observation_id": observation_id, **record}
 
 
def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object, accepting a surrounding Markdown code fence."""
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(candidate[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Final answer must be a JSON object")
    return parsed
 
 
def _contains_groups(text: str, groups: list[list[str]]) -> bool:
    lowered = text.lower()
    return all(any(term.lower() in lowered for term in group) for group in groups)
 
 
def grade_answer(scenario_id: str, answer: dict[str, Any]) -> dict[str, Any]:
    """Grade without sending the hidden ground truth to the model."""
    truth = SCENARIOS[scenario_id]["ground_truth"]
    status = str(answer.get("status", "")).strip().lower()
    diagnosis = str(answer.get("diagnosis", ""))
    recommendation = str(answer.get("recommendation", ""))
    supporting = set(answer.get("supporting_observation_ids") or [])
    constraints = " ".join(str(value) for value in (answer.get("preserved_constraints") or []))
    rejected_items = answer.get("rejected_hypotheses") or []
    rejected_observations = {
        observation_id
        for item in rejected_items
        if isinstance(item, dict)
        for observation_id in (item.get("observation_ids") or [])
    }
 
    expected_status = truth["expected_status"]
    status_ok = status == expected_status
    diagnosis_ok = status_ok and (
        expected_status == "insufficient_evidence"
        or _contains_groups(diagnosis, truth["diagnosis_keyword_groups"])
    )
    evidence_ok = set(truth["required_evidence"]).issubset(supporting)
    rejected_ok = bool(rejected_items)
    correction_ok = set(truth["invalidated_evidence"]).issubset(rejected_observations)
    constraint_ok = _contains_groups(constraints, truth["constraint_keyword_groups"])
    recommendation_ok = _contains_groups(
        recommendation, truth["recommendation_keyword_groups"]
    )
 
    components = {
        "root_cause_or_abstention": 20 if diagnosis_ok else 0,
        "evidence_chain": 25 if evidence_ok else 0,
        "rejected_hypotheses": 15 if rejected_ok else 0,
        "late_correction": 15 if correction_ok else 0,
        "constraint_fidelity": 15 if constraint_ok else 0,
        "actionable_recommendation": 10 if recommendation_ok else 0,
    }
    score = sum(components.values())
    return {
        "scenario_id": scenario_id,
        "score": score,
        "success": score >= 80 and diagnosis_ok and correction_ok and constraint_ok,
        "components": components,
        "checks": {
            "status_ok": status_ok,
            "diagnosis_ok": diagnosis_ok,
            "evidence_ok": evidence_ok,
            "rejected_ok": rejected_ok,
            "correction_ok": correction_ok,
            "constraint_ok": constraint_ok,
            "recommendation_ok": recommendation_ok,
        },
    }
 
 
# Adaptive benchmark ---------------------------------------------------------
#
# The original OBS-02..OBS-07 sequence remains available for the fixed-path
# protocol smoke test.  The primary benchmark exposes a catalog and lets the
# model choose four diagnostic probes plus one canary.  Ground truth and the
# action-quality rubric stay local to this module.
 
PROBE_CATALOG: dict[str, str] = {
    "PROBE-01": "Payment-provider latency and error cohort",
    "PROBE-02": "Database connection occupancy and wait profile",
    "PROBE-03": "Normalized database timing by unique checkout request",
    "PROBE-04": "Retry-overlap and timeout trace cohort",
    "PROBE-05": "Relevant runtime and resilience configuration",
    "PROBE-06": "Application CPU stage profile",
    "PROBE-07": "Validation and serialization stage counters",
    "PROBE-08": "Matched-cohort experiment readiness and sample validity",
}
 
CANARY_CATALOG: dict[str, str] = {
    "CANARY-RETRY-BUDGET": "Reduce retries and add bounded jittered backoff",
    "CANARY-POOL-LIMIT": "Raise the connection-pool limit within its approved budget",
    "CANARY-SERIALIZATION-SINGLE-PASS": "Restore one serialization pass per request",
    "CANARY-CIRCUIT-BREAKER": "Enable a circuit breaker and bounded retry policy",
    "CANARY-MATCHED-COHORT": "Run a matched-cohort measurement without changing production",
}
 
ADAPTIVE_CONFIG: dict[str, dict[str, Any]] = {
    "INC-101": {
        "probe_observations": {
            "PROBE-01": "OBS-02",
            "PROBE-02": "OBS-03",
            "PROBE-04": "OBS-05",
            "PROBE-05": "OBS-06",
        },
        "correction_observation": "OBS-04",
        "superseded_probe_ids": ["PROBE-02"],
        "required_probe_ids": ["PROBE-04", "PROBE-05"],
        "safe_canary_id": "CANARY-RETRY-BUDGET",
    },
    "INC-102": {
        "probe_observations": {
            "PROBE-01": "OBS-02",
            "PROBE-02": "OBS-03",
            "PROBE-03": "OBS-05",
            "PROBE-05": "OBS-06",
        },
        "correction_observation": "OBS-04",
        "superseded_probe_ids": ["PROBE-01"],
        "required_probe_ids": ["PROBE-02", "PROBE-05"],
        "safe_canary_id": "CANARY-POOL-LIMIT",
    },
    "INC-103": {
        "probe_observations": {
            "PROBE-01": "OBS-03",
            "PROBE-02": "OBS-02",
            "PROBE-03": "OBS-04",
            "PROBE-06": "OBS-05",
            "PROBE-07": "OBS-06",
        },
        "correction_observation": "OBS-04",
        "superseded_probe_ids": ["PROBE-02"],
        "required_probe_ids": ["PROBE-06", "PROBE-07"],
        "safe_canary_id": "CANARY-SERIALIZATION-SINGLE-PASS",
    },
    "INC-104": {
        "probe_observations": {
            "PROBE-01": "OBS-03",
            "PROBE-04": "OBS-05",
            "PROBE-05": "OBS-06",
            "PROBE-06": "OBS-02",
        },
        "correction_observation": "OBS-04",
        "superseded_probe_ids": ["PROBE-06"],
        "required_probe_ids": ["PROBE-01", "PROBE-04"],
        "safe_canary_id": "CANARY-CIRCUIT-BREAKER",
    },
    "INC-105": {
        "probe_observations": {
            "PROBE-01": "OBS-02",
            "PROBE-02": "OBS-03",
            "PROBE-04": "OBS-05",
            "PROBE-05": "OBS-06",
            "PROBE-08": "OBS-07",
        },
        "correction_observation": "OBS-04",
        "superseded_probe_ids": ["PROBE-01", "PROBE-02"],
        "required_probe_ids": ["PROBE-05", "PROBE-08"],
        "safe_canary_id": "CANARY-MATCHED-COHORT",
    },
}
 
 
def probe_catalog() -> list[dict[str, str]]:
    """Return model-visible diagnostic actions without scenario ground truth."""
    return [
        {"probe_id": probe_id, "description": description}
        for probe_id, description in PROBE_CATALOG.items()
    ]
 
 
def canary_catalog() -> list[dict[str, str]]:
    """Return model-visible canary actions without marking the correct choice."""
    return [
        {"canary_id": canary_id, "description": description}
        for canary_id, description in CANARY_CATALOG.items()
    ]
 
 
def _neutral_probe_result(probe_id: str) -> dict[str, Any]:
    neutral_results: dict[str, dict[str, Any]] = {
        "PROBE-01": {"provider_p95_ms": 318, "provider_error_rate_percent": 0.3},
        "PROBE-02": {"connection_occupancy_percent": 58, "connection_wait_p95_ms": 9},
        "PROBE-03": {"unique_request_db_p95_ms": 73, "database_cpu_percent": 51},
        "PROBE-04": {"overlapping_attempts_percent": 1.2, "timeout_rate_percent": 0.7},
        "PROBE-05": {"configuration_diff_count": 0, "sampled_instances": 24},
        "PROBE-06": {"application_cpu_percent": 49, "hot_stage_change_percent": 1.0},
        "PROBE-07": {"validation_calls_per_request": 1.0, "serialization_passes_per_request": 1.0},
        "PROBE-08": {"matched_cohort_available": True, "minimum_sample_size": 10000},
    }
    return deepcopy(neutral_results[probe_id])
 
 
def probe_result(scenario_id: str, probe_id: str) -> dict[str, Any]:
    """Return a raw result for a selected probe; never return grading criteria."""
    if probe_id not in PROBE_CATALOG:
        raise KeyError(f"Unknown probe: {probe_id}")
    observation_id = ADAPTIVE_CONFIG[scenario_id]["probe_observations"].get(probe_id)
    if observation_id is None:
        payload = _neutral_probe_result(probe_id)
    else:
        payload = deepcopy(SCENARIOS[scenario_id]["observations"][observation_id])
    payload.pop("supersedes_observation_id", None)
    payload.pop("supersedes_observation_ids", None)
    return {"probe_id": probe_id, **payload}
 
 
def correction_event(scenario_id: str) -> dict[str, Any]:
    """Return the scheduled correction using the same IDs required by the final contract."""
    config = ADAPTIVE_CONFIG[scenario_id]
    observation_id = config["correction_observation"]
    payload = deepcopy(SCENARIOS[scenario_id]["observations"][observation_id])
    payload.pop("supersedes_observation_id", None)
    payload.pop("supersedes_observation_ids", None)
    return {
        "correction_id": f"COR-{scenario_id.removeprefix('INC-')}",
        "supersedes_probe_ids": list(config["superseded_probe_ids"]),
        **payload,
    }
 
 
def canary_result(scenario_id: str, canary_id: str) -> dict[str, Any]:
    """Return a deterministic canary result for the model-selected intervention."""
    if canary_id not in CANARY_CATALOG:
        raise KeyError(f"Unknown canary: {canary_id}")
    safe_canary_id = ADAPTIVE_CONFIG[scenario_id]["safe_canary_id"]
    if canary_id != safe_canary_id:
        return {
            "canary_id": canary_id,
            "executed": False,
            "reason": "The action was not approved for this synthetic incident fixture.",
        }
    payload = deepcopy(SCENARIOS[scenario_id]["observations"]["OBS-07"])
    executed = payload.get("matched_cohort_canary_run", True) is not False
    return {"canary_id": canary_id, "executed": executed, **payload}
 
 
def grade_adaptive_tool_path(
    scenario_id: str, selected_probe_ids: list[str], selected_canary_id: str | None
) -> dict[str, Any]:
    """Score diagnostic choices separately from final-answer quality."""
    config = ADAPTIVE_CONFIG[scenario_id]
    selected = set(selected_probe_ids)
    required = set(config["required_probe_ids"])
    discriminating_probe_ok = required.issubset(selected)
    no_duplicate_probe = len(selected_probe_ids) == len(selected)
    within_budget = len(selected_probe_ids) <= 4
    canary_ok = selected_canary_id == config["safe_canary_id"]
    score = (
        (50 if discriminating_probe_ok else 0)
        + (15 if no_duplicate_probe else 0)
        + (10 if within_budget else 0)
        + (25 if canary_ok else 0)
    )
    return {
        "score": score,
        "success": score >= 85 and discriminating_probe_ok and canary_ok,
        "checks": {
            "discriminating_probe_ok": discriminating_probe_ok,
            "no_duplicate_probe": no_duplicate_probe,
            "within_budget": within_budget,
            "canary_ok": canary_ok,
        },
        "required_probe_ids": sorted(required),
    }
 
 
def grade_adaptive_answer(scenario_id: str, answer: dict[str, Any]) -> dict[str, Any]:
    """Grade the adaptive final contract, including an explicit correction field."""
    truth = SCENARIOS[scenario_id]["ground_truth"]
    config = ADAPTIVE_CONFIG[scenario_id]
    status = str(answer.get("status", "")).strip().lower()
    diagnosis = str(answer.get("diagnosis", ""))
    recommendation = str(answer.get("recommendation", ""))
    supporting = set(answer.get("supporting_evidence_ids") or [])
    superseded = set(answer.get("superseded_probe_ids") or [])
    constraints = " ".join(
        str(value) for value in (answer.get("preserved_constraints") or [])
    )
    rejected_items = answer.get("rejected_hypotheses") or []
 
    status_ok = status == truth["expected_status"]
    diagnosis_ok = status_ok and (
        truth["expected_status"] == "insufficient_evidence"
        or _contains_groups(diagnosis, truth["diagnosis_keyword_groups"])
    )
    required_evidence = {
        *config["required_probe_ids"],
        f"COR-{scenario_id.removeprefix('INC-')}",
        config["safe_canary_id"],
    }
    evidence_ok = required_evidence.issubset(supporting)
    rejected_ok = bool(rejected_items)
    correction_ok = set(config["superseded_probe_ids"]).issubset(superseded)
    constraint_ok = _contains_groups(constraints, truth["constraint_keyword_groups"])
    recommendation_ok = _contains_groups(
        recommendation, truth["recommendation_keyword_groups"]
    )
    components = {
        "root_cause_or_abstention": 20 if diagnosis_ok else 0,
        "evidence_chain": 25 if evidence_ok else 0,
        "rejected_hypotheses": 15 if rejected_ok else 0,
        "late_correction": 15 if correction_ok else 0,
        "constraint_fidelity": 15 if constraint_ok else 0,
        "actionable_recommendation": 10 if recommendation_ok else 0,
    }
    score = sum(components.values())
    return {
        "scenario_id": scenario_id,
        "score": score,
        "success": score >= 80 and diagnosis_ok and correction_ok and constraint_ok,
        "components": components,
        "checks": {
            "status_ok": status_ok,
            "diagnosis_ok": diagnosis_ok,
            "evidence_ok": evidence_ok,
            "rejected_ok": rejected_ok,
            "correction_ok": correction_ok,
            "constraint_ok": constraint_ok,
            "recommendation_ok": recommendation_ok,
        },
        "required_evidence_ids": sorted(required_evidence),
    }
