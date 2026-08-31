"""Deterministic hidden-policy workload for retained-reasoning experiments."""
 
from __future__ import annotations
 
import hashlib
import json
from copy import deepcopy
from typing import Any
 
 
HARNESS_VERSION = "support-policy-retained-reasoning-v1"
ACTIONS = ("monitor", "retry", "workaround", "escalate", "rollback")
RULE_PRECEDENCE = (
    "dependency_degraded",
    "repeat_without_workaround",
    "enterprise_freeze",
    "workaround_available",
    "default",
)
 
# Each profile uses the same latent rule structure but a different arbitrary
# action codebook. This prevents common-sense priors from revealing the answer.
POLICY_PROFILES: dict[str, dict[str, str]] = {
    "POL-301": dict(zip(RULE_PRECEDENCE, ACTIONS, strict=True)),
    "POL-302": dict(zip(RULE_PRECEDENCE, ACTIONS[1:] + ACTIONS[:1], strict=True)),
    "POL-303": dict(zip(RULE_PRECEDENCE, ACTIONS[2:] + ACTIONS[:2], strict=True)),
    "POL-304": dict(zip(RULE_PRECEDENCE, ACTIONS[3:] + ACTIONS[:3], strict=True)),
    "POL-305": dict(zip(RULE_PRECEDENCE, ACTIONS[4:] + ACTIONS[:4], strict=True)),
}
 
 
_CASE_TEMPLATES: tuple[dict[str, Any], ...] = (
    # Learning cases isolate each rule once.
    {"case": "L01", "phase": "learning", "tier": "standard", "recurrence": "first", "workaround": False, "region": "amer", "dependency": "degraded", "freeze": False},
    {"case": "L02", "phase": "learning", "tier": "pro", "recurrence": "repeat", "workaround": False, "region": "emea", "dependency": "healthy", "freeze": False},
    {"case": "L03", "phase": "learning", "tier": "enterprise", "recurrence": "first", "workaround": False, "region": "apac", "dependency": "healthy", "freeze": True},
    {"case": "L04", "phase": "learning", "tier": "standard", "recurrence": "first", "workaround": True, "region": "emea", "dependency": "healthy", "freeze": False},
    {"case": "L05", "phase": "learning", "tier": "pro", "recurrence": "first", "workaround": False, "region": "amer", "dependency": "healthy", "freeze": False},
    # Transfer cases combine learned rules and therefore test precedence.
    {"case": "T01", "phase": "transfer", "tier": "enterprise", "recurrence": "repeat", "workaround": True, "region": "apac", "dependency": "degraded", "freeze": True},
    {"case": "T02", "phase": "transfer", "tier": "enterprise", "recurrence": "repeat", "workaround": False, "region": "amer", "dependency": "healthy", "freeze": True},
    {"case": "T03", "phase": "transfer", "tier": "enterprise", "recurrence": "first", "workaround": True, "region": "emea", "dependency": "healthy", "freeze": True},
    {"case": "T04", "phase": "transfer", "tier": "pro", "recurrence": "first", "workaround": True, "region": "apac", "dependency": "healthy", "freeze": False},
    {"case": "T05", "phase": "transfer", "tier": "standard", "recurrence": "first", "workaround": False, "region": "emea", "dependency": "healthy", "freeze": True},
    {"case": "T06", "phase": "transfer", "tier": "pro", "recurrence": "repeat", "workaround": False, "region": "apac", "dependency": "degraded", "freeze": False},
    {"case": "T07", "phase": "transfer", "tier": "standard", "recurrence": "repeat", "workaround": True, "region": "amer", "dependency": "healthy", "freeze": False},
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
        ticket["ticket_id"] = f"{scenario_id}-{ticket.pop('case')}"
        tickets.append(ticket)
    return tickets
 
 
def decisive_rule(ticket: dict[str, Any]) -> str:
    if ticket["dependency"] == "degraded":
        return "dependency_degraded"
    if ticket["recurrence"] == "repeat" and not ticket["workaround"]:
        return "repeat_without_workaround"
    if ticket["tier"] == "enterprise" and ticket["freeze"]:
        return "enterprise_freeze"
    if ticket["workaround"]:
        return "workaround_available"
    return "default"
 
 
def expected_action(scenario_id: str, ticket: dict[str, Any]) -> str:
    try:
        profile = POLICY_PROFILES[scenario_id]
    except KeyError as exc:
        raise ValueError(f"Unknown scenario_id: {scenario_id}") from exc
    return profile[decisive_rule(ticket)]
 
 
class SupportPolicySimulator:
    """Black-box ticket system with feedback but no exposed policy rationale."""
 
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
            "tier": ticket["tier"],
            "recurrence": ticket["recurrence"],
            "workaround_available": ticket["workaround"],
            "region": ticket["region"],
            "dependency_health": ticket["dependency"],
            "change_freeze": ticket["freeze"],
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
        accepted = action == expected
        row = {
            "ticket_id": ticket_id,
            "phase": ticket["phase"],
            "action": action,
            "accepted": accepted,
            "inspected_first": ticket_id in self.inspected,
            "decisive_rule": decisive_rule(ticket),
            "expected_action": expected,
        }
        self.decisions.append(row)
        feedback = {
            "ticket_id": ticket_id,
            "accepted": accepted,
            "feedback": "policy_match" if accepted else "policy_mismatch",
        }
        if not accepted:
            # A rejected training example supplies a label, not the latent rule or
            # precedence explanation. The model must induce those across cases.
            feedback["accepted_action"] = expected
        return feedback
 
    def grade(self) -> dict[str, Any]:
        by_phase = {
            phase: [row for row in self.decisions if row["phase"] == phase]
            for phase in ("learning", "transfer")
        }
 
        def accuracy(rows: list[dict[str, Any]]) -> float | None:
            return (
                sum(row["accepted"] for row in rows) / len(rows) if rows else None
            )
 
        expected_count = len(self._tickets)
        transfer_rows = by_phase["transfer"]
        return {
            "complete": len(self.decisions) == expected_count,
            "expected_ticket_count": expected_count,
            "completed_ticket_count": len(self.decisions),
            "learning_accuracy": accuracy(by_phase["learning"]),
            "transfer_accuracy": accuracy(transfer_rows),
            "transfer_errors": sum(not row["accepted"] for row in transfer_rows),
            "inspected_before_decision_rate": (
                sum(row["inspected_first"] for row in self.decisions)
                / len(self.decisions)
                if self.decisions
                else None
            ),
            "decisions": deepcopy(self.decisions),
        }
 
 
def validate_workload() -> dict[str, Any]:
    """Run free invariants without revealing profiles to the model."""
    scenario_summary = {}
    for scenario_id in scenario_ids():
        tickets = ticket_sequence(scenario_id)
        learning_rules = {
            decisive_rule(ticket) for ticket in tickets if ticket["phase"] == "learning"
        }
        transfer_rules = {
            decisive_rule(ticket) for ticket in tickets if ticket["phase"] == "transfer"
        }
        actions = {expected_action(scenario_id, ticket) for ticket in tickets}
        assert learning_rules == set(RULE_PRECEDENCE)
        assert transfer_rules == set(RULE_PRECEDENCE)
        assert actions == set(ACTIONS)
        assert len({ticket["ticket_id"] for ticket in tickets}) == len(tickets)
        scenario_summary[scenario_id] = {
            "learning_cases": sum(ticket["phase"] == "learning" for ticket in tickets),
            "transfer_cases": sum(ticket["phase"] == "transfer" for ticket in tickets),
            "covered_rules": len(transfer_rules),
        }
    return {
        "harness_version": HARNESS_VERSION,
        "scenario_count": len(scenario_summary),
        "scenarios": scenario_summary,
        "ticket_sequence_hash": stable_json_sha256(_CASE_TEMPLATES),
    }
