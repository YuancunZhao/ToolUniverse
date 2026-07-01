"""Explicit ACMG assessment session state machine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any

from .intent_detector import ACMGIntent

SESSION_STATES = {
    "NEW",
    "PLANNED",
    "EVIDENCE_COLLECTED",
    "OVERLAYS_REQUIRED",
    "OVERLAYS_APPLIED",
    "LITERATURE_REQUIRED",
    "READY_FOR_FINALIZER",
    "FINALIZED",
    "DRAFT_ONLY",
    "BLOCKED",
    "ERROR",
}

LITERATURE_READY_STATES = {"reviewed", "reviewed_full", "reviewed_not_needed", "not_required", "no_hit", "ready"}


@dataclass
class ACMGAssessmentSession:
    session_id: str
    variant: str | None = None
    gene: str | None = None
    transcript: str | None = None
    intent: str = ACMGIntent.ACMG_FINAL_CLASSIFICATION.value
    state: str = "DRAFT_ONLY"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    required_next_actions: list[Any] = field(default_factory=list)
    completed_actions: list[Any] = field(default_factory=list)
    source_lead_sandbox: list[dict[str, Any]] = field(default_factory=list)
    route_candidates: list[dict[str, Any]] = field(default_factory=list)
    overlay_validated_evidence: list[dict[str, Any]] = field(default_factory=list)
    counted_evidence: list[dict[str, Any]] = field(default_factory=list)
    validator_status: str = "NOT_RUN"
    semantic_combiner_status: str = "NOT_RUN"
    literature_status: str = "not_reviewed"
    final_classification_allowed: bool = False
    finalization_token: str | None = None
    policy_warnings: list[str] = field(default_factory=list)
    classification: str | None = None


def _new_id() -> str:
    return f"acmg-session-{uuid.uuid4()}"


def create_acmg_session(
    *,
    variant: str | None = None,
    gene: str | None = None,
    transcript: str | None = None,
    intent: str | ACMGIntent = ACMGIntent.ACMG_FINAL_CLASSIFICATION,
) -> ACMGAssessmentSession:
    intent_value = intent.value if isinstance(intent, ACMGIntent) else str(intent)
    state = "DRAFT_ONLY" if intent_value == ACMGIntent.ACMG_FINAL_CLASSIFICATION.value else "NEW"
    return ACMGAssessmentSession(
        session_id=_new_id(),
        variant=variant,
        gene=gene,
        transcript=transcript,
        intent=intent_value,
        state=state,
    )


def session_from_dict(payload: dict[str, Any] | ACMGAssessmentSession) -> ACMGAssessmentSession:
    if isinstance(payload, ACMGAssessmentSession):
        return payload
    data = dict(payload or {})
    data.setdefault("session_id", _new_id())
    data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    allowed = set(ACMGAssessmentSession.__dataclass_fields__)
    return ACMGAssessmentSession(**{key: value for key, value in data.items() if key in allowed})


def session_to_dict(session: dict[str, Any] | ACMGAssessmentSession) -> dict[str, Any]:
    if isinstance(session, ACMGAssessmentSession):
        return asdict(session)
    return dict(session or {})


def update_session_state(session: dict[str, Any] | ACMGAssessmentSession, state: str) -> ACMGAssessmentSession:
    if state not in SESSION_STATES:
        raise ValueError(f"Invalid ACMG session state: {state}")
    obj = session_from_dict(session)
    obj.state = state
    return obj


def add_source_lead(session: dict[str, Any] | ACMGAssessmentSession, source_lead: dict[str, Any]) -> ACMGAssessmentSession:
    obj = session_from_dict(session)
    lead = dict(source_lead)
    lead["counted"] = False
    lead["source_lead_only"] = True
    lead["acmg_countable_evidence"] = False
    lead["final_classification_allowed"] = False
    obj.source_lead_sandbox.append(lead)
    if obj.state in {"NEW", "PLANNED", "DRAFT_ONLY"}:
        obj.state = "EVIDENCE_COLLECTED"
    return obj


def add_route_candidate(session: dict[str, Any] | ACMGAssessmentSession, route_candidate: dict[str, Any]) -> ACMGAssessmentSession:
    obj = session_from_dict(session)
    candidate = dict(route_candidate)
    candidate["counted"] = False
    obj.route_candidates.append(candidate)
    if obj.state not in {"BLOCKED", "ERROR", "FINALIZED"}:
        obj.state = "OVERLAYS_REQUIRED"
    return obj


def add_overlay_validated_evidence(session: dict[str, Any] | ACMGAssessmentSession, evidence: dict[str, Any]) -> ACMGAssessmentSession:
    obj = session_from_dict(session)
    row = dict(evidence)
    row["overlay_validated"] = True
    row["counted"] = True
    obj.overlay_validated_evidence.append(row)
    obj.counted_evidence.append(row)
    if obj.state not in {"BLOCKED", "ERROR", "FINALIZED"}:
        obj.state = "OVERLAYS_APPLIED"
    return obj


def mark_required_action(session: dict[str, Any] | ACMGAssessmentSession, action: Any) -> ACMGAssessmentSession:
    obj = session_from_dict(session)
    if action not in obj.required_next_actions:
        obj.required_next_actions.append(action)
    if obj.state not in {"BLOCKED", "ERROR", "FINALIZED"}:
        obj.state = "OVERLAYS_REQUIRED"
    return obj


def mark_completed_action(session: dict[str, Any] | ACMGAssessmentSession, action: Any) -> ACMGAssessmentSession:
    obj = session_from_dict(session)
    if action not in obj.completed_actions:
        obj.completed_actions.append(action)
    return obj


def _action_key(action: Any) -> str:
    if isinstance(action, dict):
        return str(action.get("action") or action.get("route") or action.get("criterion_group") or action)
    return str(action)


def missing_required_actions(session: dict[str, Any] | ACMGAssessmentSession) -> list[Any]:
    obj = session_from_dict(session)
    completed = {_action_key(action) for action in obj.completed_actions}
    return [action for action in obj.required_next_actions if _action_key(action) not in completed]


def session_can_finalize(session: dict[str, Any] | ACMGAssessmentSession) -> bool:
    obj = session_from_dict(session)
    literature_ready = obj.literature_status in LITERATURE_READY_STATES
    return (
        obj.intent == ACMGIntent.ACMG_FINAL_CLASSIFICATION.value
        and not missing_required_actions(obj)
        and obj.validator_status == "PASS"
        and obj.semantic_combiner_status == "PASS"
        and obj.final_classification_allowed is True
        and literature_ready
        and bool(obj.counted_evidence)
    )


def session_can_emit_final_label(session: dict[str, Any] | ACMGAssessmentSession) -> bool:
    obj = session_from_dict(session)
    return obj.state == "FINALIZED" and bool(obj.finalization_token) and session_can_finalize(obj)


def session_to_policy_envelope(session: dict[str, Any] | ACMGAssessmentSession) -> dict[str, Any]:
    obj = session_from_dict(session)
    missing = missing_required_actions(obj)
    return {
        "acmg_session": session_to_dict(obj),
        "state": obj.state,
        "allowed_response_type": "FINAL" if session_can_emit_final_label(obj) else "DRAFT_ONLY",
        "final_classification_allowed": session_can_emit_final_label(obj),
        "may_emit_final_label": session_can_emit_final_label(obj),
        "missing_required_actions": missing,
        "source_lead_sandbox": obj.source_lead_sandbox,
        "route_candidates": obj.route_candidates,
        "counted_evidence": obj.counted_evidence if session_can_emit_final_label(obj) else [],
        "policy_warnings": obj.policy_warnings,
    }


__all__ = [
    "ACMGAssessmentSession",
    "LITERATURE_READY_STATES",
    "SESSION_STATES",
    "add_overlay_validated_evidence",
    "add_route_candidate",
    "add_source_lead",
    "create_acmg_session",
    "mark_completed_action",
    "mark_required_action",
    "missing_required_actions",
    "session_can_emit_final_label",
    "session_can_finalize",
    "session_from_dict",
    "session_to_dict",
    "session_to_policy_envelope",
    "update_session_state",
]
