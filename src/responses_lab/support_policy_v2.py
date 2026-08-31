"""Support Policy v2: identifiable learning and feedback-free evaluation."""
 
from __future__ import annotations
 
import hashlib
import itertools
import json
from collections import Counter
from copy import deepcopy
from typing import Any, Iterable
 
 
HARNESS_VERSION = "support-policy-v2-retained-reasoning-v1"
ACTIONS = ("monitor", "retry", "workaround", "escalate", "rollback")
RULES = (
    "dependency_degraded",
    "repeat_without_workaround",
    "enterprise_freeze",
    "workaround_available",
    "default",
)
TRUE_PRECEDENCE = RULES
PHASES = ("learning", "boundary", "evaluation")
 
POLICY_PROFILES: dict[str, dict[str, str]] = {
    "POL2-401": dict(zip(RULES, ACTIONS, strict=True)),
    "POL2-402": dict(zip(RULES, ACTIONS[1:] + ACTIONS[:1], strict=True)),
    "POL2-403": dict(zip(RULES, ACTIONS[2:] + ACTIONS[:2], strict=True)),
    "POL2-404": dict(zip(RULES, ACTIONS[3:] + ACTIONS[:3], strict=True)),
    "POL2-405": dict(zip(RULES, ACTIONS[4:] + ACTIONS[:4], strict=True)),
}
 
 
def _case(
    case_id: str,
    phase: str,
    tier: str,
    recurrence: str,
    workaround: bool,
    region: str,
    dependency: str,
    freeze: bool,
    severity: str,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "phase": phase,
        "tier": tier,
        "recurrence": recurrence,
        "workaround": workaround,
        "region": region,
        "dependency": dependency,
        "freeze": freeze,
        "severity": severity,
    }
 
 
_CASE_TEMPLATES: tuple[dict[str, Any], ...] = (
    # Phase 1: two labeled examples per isolated decisive rule.
    _case("L01", "learning", "standard", "first", False, "amer", "degraded", False, "high"),
    _case("L02", "learning", "pro", "first", False, "emea", "degraded", True, "medium"),
    _case("L03", "learning", "standard", "repeat", False, "apac", "healthy", False, "high"),
    _case("L04", "learning", "pro", "repeat", False, "amer", "healthy", True, "low"),
    _case("L05", "learning", "enterprise", "first", False, "emea", "healthy", True, "high"),
    _case("L06", "learning", "enterprise", "first", False, "apac", "healthy", True, "low"),
    _case("L07", "learning", "standard", "first", True, "amer", "healthy", False, "medium"),
    _case("L08", "learning", "pro", "first", True, "emea", "healthy", True, "high"),
    _case("L09", "learning", "standard", "first", False, "apac", "healthy", False, "low"),
    _case("L10", "learning", "pro", "first", False, "amer", "healthy", True, "medium"),
    # Phase 2: labeled counterfactuals reveal conjunction boundaries and precedence.
    _case("B01", "boundary", "standard", "repeat", False, "emea", "degraded", False, "high"),
    _case("B02", "boundary", "enterprise", "first", False, "apac", "degraded", True, "medium"),
    _case("B03", "boundary", "pro", "first", True, "amer", "degraded", False, "low"),
    _case("B04", "boundary", "enterprise", "repeat", False, "emea", "healthy", True, "high"),
    _case("B05", "boundary", "enterprise", "first", True, "apac", "healthy", True, "medium"),
    _case("B06", "boundary", "pro", "repeat", True, "amer", "healthy", False, "low"),
    _case("B07", "boundary", "standard", "first", False, "emea", "healthy", True, "high"),
    _case("B08", "boundary", "enterprise", "first", True, "apac", "healthy", False, "medium"),
    # Phase 3: 20 balanced cases. No correctness feedback is returned.
    _case("E01", "evaluation", "enterprise", "repeat", True, "amer", "degraded", True, "high"),
    _case("E02", "evaluation", "standard", "first", True, "apac", "degraded", True, "low"),
    _case("E03", "evaluation", "pro", "repeat", False, "emea", "degraded", True, "medium"),
    _case("E04", "evaluation", "enterprise", "first", False, "amer", "degraded", False, "low"),
    _case("E05", "evaluation", "enterprise", "repeat", False, "apac", "healthy", False, "high"),
    _case("E06", "evaluation", "standard", "repeat", False, "amer", "healthy", True, "medium"),
    _case("E07", "evaluation", "pro", "repeat", False, "apac", "healthy", False, "low"),
    _case("E08", "evaluation", "enterprise", "repeat", False, "amer", "healthy", True, "medium"),
    _case("E09", "evaluation", "enterprise", "first", False, "amer", "healthy", True, "medium"),
    _case("E10", "evaluation", "enterprise", "first", True, "emea", "healthy", True, "low"),
    _case("E11", "evaluation", "enterprise", "repeat", True, "apac", "healthy", True, "high"),
    _case("E12", "evaluation", "enterprise", "first", False, "amer", "healthy", True, "high"),
    _case("E13", "evaluation", "standard", "first", True, "emea", "healthy", True, "low"),
    _case("E14", "evaluation", "pro", "repeat", True, "apac", "healthy", True, "medium"),
    _case("E15", "evaluation", "standard", "repeat", True, "amer", "healthy", False, "high"),
    _case("E16", "evaluation", "enterprise", "first", True, "emea", "healthy", False, "medium"),
    _case("E17", "evaluation", "standard", "first", False, "amer", "healthy", True, "medium"),
    _case("E18", "evaluation", "pro", "first", False, "apac", "healthy", False, "high"),
    _case("E19", "evaluation", "standard", "first", False, "emea", "healthy", False, "low"),
    _case("E20", "evaluation", "pro", "first", False, "apac", "healthy", True, "low"),
)
 
 
def stable_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
 
 
def scenario_ids() -> list[str]:
    return list(POLICY_PROFILES)
 
 
def ticket_sequence(scenario_id: str) -> list[dict[str, Any]]:
    if scenario_id not in POLICY_PROFILES:
        raise ValueError(f"Unknown scenario_id: {scenario_id}")
    tickets = []
    for template in _CASE_TEMPLATES:
        ticket = deepcopy(template)
        ticket["ticket_id"] = f"{scenario_id}-{ticket.pop('case_id')}"
        tickets.append(ticket)
    return tickets
 
 
def active_rules(ticket: dict[str, Any]) -> set[str]:
    active = {"default"}
    if ticket["dependency"] == "degraded":
        active.add("dependency_degraded")
    if ticket["recurrence"] == "repeat" and not ticket["workaround"]:
        active.add("repeat_without_workaround")
    if ticket["tier"] == "enterprise" and ticket["freeze"]:
        active.add("enterprise_freeze")
    if ticket["workaround"]:
        active.add("workaround_available")
    return active
 
 
def decisive_rule(
    ticket: dict[str, Any], precedence: Iterable[str] = TRUE_PRECEDENCE
) -> str:
    active = active_rules(ticket)
    for rule in precedence:
        if rule in active:
            return rule
    raise AssertionError("A precedence must include the default rule")
 
 
def expected_action(
    scenario_id: str,
    ticket: dict[str, Any],
    *,
    mapping: dict[str, str] | None = None,
    precedence: Iterable[str] = TRUE_PRECEDENCE,
) -> str:
    profile = mapping or POLICY_PROFILES[scenario_id]
    return profile[decisive_rule(ticket, precedence)]
 
 
def _logical_feature_space() -> list[dict[str, Any]]:
    rows = []
    for tier, recurrence, workaround, dependency, freeze in itertools.product(
        ("standard", "pro", "enterprise"),
        ("first", "repeat"),
        (False, True),
        ("healthy", "degraded"),
        (False, True),
    ):
        rows.append(
            {
                "tier": tier,
                "recurrence": recurrence,
                "workaround": workaround,
                "dependency": dependency,
                "freeze": freeze,
            }
        )
    return rows
 
 
def identifiability_report(scenario_id: str) -> dict[str, Any]:
    """Verify that labeled phases select one behavior over the feature space."""
    tickets = ticket_sequence(scenario_id)
    labeled = [ticket for ticket in tickets if ticket["phase"] != "evaluation"]
    truth = [expected_action(scenario_id, ticket) for ticket in labeled]
    feature_space = _logical_feature_space()
    matching_parameterizations = 0
    behavior_signatures: set[tuple[str, ...]] = set()
    for action_order in itertools.permutations(ACTIONS):
        mapping = dict(zip(RULES, action_order, strict=True))
        for non_default_order in itertools.permutations(RULES[:-1]):
            precedence = (*non_default_order, "default")
            labels = [
                expected_action(
                    scenario_id, ticket, mapping=mapping, precedence=precedence
                )
                for ticket in labeled
            ]
            if labels != truth:
                continue
            matching_parameterizations += 1
            behavior_signatures.add(
                tuple(
                    expected_action(
                        scenario_id, row, mapping=mapping, precedence=precedence
                    )
                    for row in feature_space
                )
            )
    return {
        "scenario_id": scenario_id,
        "labeled_case_count": len(labeled),
        "candidate_parameterizations": 120 * 24,
        "matching_parameterizations": matching_parameterizations,
        "matching_behavior_signatures": len(behavior_signatures),
        "identifiable": len(behavior_signatures) == 1,
    }
 
 
class SupportPolicyV2Simulator:
    """Black-box policy learner with labeled calibration and blind evaluation."""
 
    def __init__(self, scenario_id: str):
        if scenario_id not in POLICY_PROFILES:
            raise ValueError(f"Unknown scenario_id: {scenario_id}")
        self.scenario_id = scenario_id
        self._tickets = {
            ticket["ticket_id"]: ticket for ticket in ticket_sequence(scenario_id)
        }
        self.inspected: set[str] = set()
        self.decisions: list[dict[str, Any]] = []
 
    @property
    def tickets(self) -> list[dict[str, Any]]:
        return [deepcopy(ticket) for ticket in self._tickets.values()]
 
    def inspect_ticket(self, ticket_id: str) -> dict[str, Any]:
        try:
            ticket = self._tickets[ticket_id]
        except KeyError as exc:
            raise ValueError(f"Unknown ticket_id: {ticket_id}") from exc
        self.inspected.add(ticket_id)
        return {
            "ticket_id": ticket_id,
            "phase": ticket["phase"],
            "tier": ticket["tier"],
            "recurrence": ticket["recurrence"],
            "workaround_available": ticket["workaround"],
            "region": ticket["region"],
            "dependency_health": ticket["dependency"],
            "change_freeze": ticket["freeze"],
            "severity": ticket["severity"],
        }
 
    def submit_disposition(self, ticket_id: str, action: str) -> dict[str, Any]:
        if action not in ACTIONS:
            raise ValueError(f"Unsupported action: {action}")
        try:
            ticket = self._tickets[ticket_id]
        except KeyError as exc:
            raise ValueError(f"Unknown ticket_id: {ticket_id}") from exc
        if any(row["ticket_id"] == ticket_id for row in self.decisions):
            raise ValueError(f"A disposition was already submitted for {ticket_id}")
        expected = expected_action(self.scenario_id, ticket)
        row = {
            "ticket_id": ticket_id,
            "phase": ticket["phase"],
            "action": action,
            "accepted": action == expected,
            "inspected_first": ticket_id in self.inspected,
            "decisive_rule": decisive_rule(ticket),
            "expected_action": expected,
        }
        self.decisions.append(row)
        feedback: dict[str, Any] = {"ticket_id": ticket_id, "recorded": True}
        if ticket["phase"] in {"learning", "boundary"}:
            feedback["accepted_action"] = expected
        return feedback
 
    def grade(self) -> dict[str, Any]:
        by_phase = {
            phase: [row for row in self.decisions if row["phase"] == phase]
            for phase in PHASES
        }
 
        def accuracy(rows: list[dict[str, Any]]) -> float | None:
            return (
                sum(row["accepted"] for row in rows) / len(rows) if rows else None
            )
 
        evaluation_rows = by_phase["evaluation"]
        rule_accuracy = {}
        rule_consistency = {}
        for rule in RULES:
            rows = [row for row in evaluation_rows if row["decisive_rule"] == rule]
            rule_accuracy[rule] = accuracy(rows)
            action_counts = Counter(row["action"] for row in rows)
            rule_consistency[rule] = (
                max(action_counts.values()) / len(rows) if rows else None
            )
        consistency_values = [
            value for value in rule_consistency.values() if value is not None
        ]
        return {
            "complete": len(self.decisions) == len(self._tickets),
            "expected_ticket_count": len(self._tickets),
            "completed_ticket_count": len(self.decisions),
            "learning_accuracy": accuracy(by_phase["learning"]),
            "boundary_accuracy": accuracy(by_phase["boundary"]),
            "evaluation_accuracy": accuracy(evaluation_rows),
            "evaluation_errors": sum(
                not row["accepted"] for row in evaluation_rows
            ),
            "evaluation_rule_accuracy": rule_accuracy,
            "evaluation_rule_consistency": rule_consistency,
            "strategy_consistency": (
                sum(consistency_values) / len(consistency_values)
                if consistency_values
                else None
            ),
            "inspected_before_decision_rate": (
                sum(row["inspected_first"] for row in self.decisions)
                / len(self.decisions)
                if self.decisions
                else None
            ),
            "decisions": deepcopy(self.decisions),
        }
 
 
def validate_workload() -> dict[str, Any]:
    scenario_summary = {}
    for scenario_id in scenario_ids():
        tickets = ticket_sequence(scenario_id)
        counts = Counter(ticket["phase"] for ticket in tickets)
        evaluation = [
            ticket for ticket in tickets if ticket["phase"] == "evaluation"
        ]
        evaluation_rules = Counter(decisive_rule(ticket) for ticket in evaluation)
        evaluation_actions = Counter(
            expected_action(scenario_id, ticket) for ticket in evaluation
        )
        report = identifiability_report(scenario_id)
        assert counts == {"learning": 10, "boundary": 8, "evaluation": 20}
        assert evaluation_rules == {rule: 4 for rule in RULES}
        assert evaluation_actions == {action: 4 for action in ACTIONS}
        assert report["identifiable"] is True
        assert len({ticket["ticket_id"] for ticket in tickets}) == len(tickets)
        scenario_summary[scenario_id] = {
            "phase_counts": dict(counts),
            "evaluation_rule_counts": dict(evaluation_rules),
            "evaluation_action_counts": dict(evaluation_actions),
            "identifiability": report,
        }
    return {
        "harness_version": HARNESS_VERSION,
        "scenario_count": len(scenario_summary),
        "scenarios": scenario_summary,
        "ticket_sequence_hash": stable_json_sha256(_CASE_TEMPLATES),
    }
