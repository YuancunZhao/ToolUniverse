"""Explicit ACMG assessment session state machine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any

from .intent_detector import ACMGIntent
from .route_policy import (
    blocking_route_requirements,
)

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
    route_requirements: list[dict[str, Any]] = field(default_factory=list)
    tool_call_receipts: list[dict[str, Any]] = field(default_factory=list)
    evidence_provenance: list[dict[str, Any]] = field(default_factory=list)
    overlay_validated_evidence: list[dict[str, Any]] = field(default_factory=list)
    counted_evidence: list[dict[str, Any]] = field(default_factory=list)
    independence_warnings: list[dict[str, Any]] = field(default_factory=list)
    validator_status: str = "NOT_RUN"
    semantic_combiner_status: str = "NOT_RUN"
    literature_status: str = "not_reviewed"
    final_classification_allowed: bool = False
    finalization_token: str | None = None
    policy_warnings: list[str] = field(default_factory=list)
    classification: str | None = None
    classification_status: str | None = None


@dataclass
class FinalizationGateResult:
    can_finalize: bool
    blocking_reasons: list[str]
    warnings: list[Any]
    missing_required_actions: list[Any]
    blocking_route_requirements: list[dict[str, Any]]
    counted_evidence_count: int
    validator_status: str
    semantic_combiner_status: str
    final_classification_allowed: bool
    literature_status: str
    evidence_independence: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def action_key(action: Any) -> str:
    if isinstance(action, dict):
        return str(action.get("action") or action.get("route") or action.get("criterion_group") or action)
    return str(action)


def missing_required_actions(session: dict[str, Any] | ACMGAssessmentSession) -> list[Any]:
    obj = session_from_dict(session)
    completed = {action_key(action) for action in obj.completed_actions}
    return [action for action in obj.required_next_actions if action_key(action) not in completed]


def evaluate_finalization_gate(session: dict[str, Any] | ACMGAssessmentSession) -> FinalizationGateResult:
    """Evaluate all session-level gates required before ACMG finalization.

    Token verification and answer-label binding are intentionally handled by
    final_answer_guard.py after this session gate passes.
    """

    obj = session_from_dict(session)
    missing = missing_required_actions(obj)
    route_blockers: list[dict[str, Any]] = blocking_route_requirements(obj.route_requirements or [])
    blocking_reasons: list[str] = []
    warnings: list[Any] = list(obj.policy_warnings)
    classification_status = str(obj.classification_status or "").strip().lower()

    if obj.intent != ACMGIntent.ACMG_FINAL_CLASSIFICATION.value:
        blocking_reasons.append("intent is not ACMG_FINAL_CLASSIFICATION")
    if obj.state == "DRAFT_ONLY" or classification_status in {"draft", "draft classification", "provisional", "preliminary"}:
        blocking_reasons.append("classification status is draft/provisional")
    if obj.validator_status != "PASS":
        blocking_reasons.append("validator_status is not PASS")
    if obj.semantic_combiner_status != "PASS":
        blocking_reasons.append("semantic_combiner_status is not PASS")
    if obj.final_classification_allowed is not True:
        blocking_reasons.append("final_classification_allowed is not true")
    if missing:
        blocking_reasons.append("required overlay actions are incomplete")
    if route_blockers:
        blocking_reasons.append("required ACMG routes are incomplete")
    if obj.literature_status not in LITERATURE_READY_STATES:
        blocking_reasons.append("literature is not ready")
    if not obj.counted_evidence:
        blocking_reasons.append("counted evidence is empty")
    for row in obj.counted_evidence:
        if not isinstance(row, dict):
            continue
        route_outcome = str(row.get("route_outcome") or "")
        if row.get("overlay_validated") is not True and route_outcome not in {"overlay_applied", "overlay_deferred_to_vcep"}:
            blocking_reasons.append("counted evidence is not overlay-validated")
            break

    independence: dict[str, Any] | None = None
    try:
        from .evidence_independence import evaluate_evidence_independence
        independence = evaluate_evidence_independence(obj)
    except ImportError:  # pragma: no cover
        from tooluniverse.acmg_gate.evidence_independence import evaluate_evidence_independence
        independence = evaluate_evidence_independence(obj)
    if independence:
        warnings.extend(independence.get("warnings", []))
        if independence.get("status") == "BLOCK":
            blocking_reasons.extend(str(reason) for reason in independence.get("blocking_reasons", []))

    return FinalizationGateResult(
        can_finalize=not blocking_reasons,
        blocking_reasons=list(dict.fromkeys(blocking_reasons)),
        warnings=warnings,
        missing_required_actions=missing,
        blocking_route_requirements=route_blockers,
        counted_evidence_count=len(obj.counted_evidence),
        validator_status=obj.validator_status,
        semantic_combiner_status=obj.semantic_combiner_status,
        final_classification_allowed=obj.final_classification_allowed,
        literature_status=obj.literature_status,
        evidence_independence=independence,
    )


def session_can_finalize(session: dict[str, Any] | ACMGAssessmentSession) -> bool:
    return evaluate_finalization_gate(session).can_finalize


def is_acmg_finalization_blocked(
    session: dict[str, Any] | ACMGAssessmentSession,
    *,
    require_token: bool = False,
) -> dict[str, Any]:
    """Return a structured hard-block status for ACMG finalization/output."""

    obj = session_from_dict(session)
    gate = evaluate_finalization_gate(obj)
    blocking_reasons = list(gate.blocking_reasons)
    if require_token and not obj.finalization_token:
        blocking_reasons.append("ACMG finalization token is missing")
    return {
        "blocked": bool(blocking_reasons),
        "status": "BLOCK" if blocking_reasons else "PASS",
        "blocking_reasons": list(dict.fromkeys(blocking_reasons)),
        "missing_required_actions": gate.missing_required_actions,
        "blocking_route_requirements": gate.blocking_route_requirements,
        "finalization_gate": gate.to_dict(),
    }


def session_can_emit_final_label(session: dict[str, Any] | ACMGAssessmentSession) -> bool:
    obj = session_from_dict(session)
    return obj.state == "FINALIZED" and bool(obj.finalization_token) and session_can_finalize(obj)


def session_to_policy_envelope(session: dict[str, Any] | ACMGAssessmentSession) -> dict[str, Any]:
    obj = session_from_dict(session)
    missing = missing_required_actions(obj)
    gate = evaluate_finalization_gate(obj)
    can_emit = gate.can_finalize and obj.state == "FINALIZED" and bool(obj.finalization_token)
    return {
        "acmg_session": session_to_dict(obj),
        "state": obj.state,
        "allowed_response_type": "FINAL" if can_emit else "DRAFT_ONLY",
        "final_classification_allowed": can_emit,
        "may_emit_final_label": can_emit,
        "missing_required_actions": missing,
        "blocking_route_requirements": gate.blocking_route_requirements,
        "finalization_gate": gate.to_dict(),
        "source_lead_sandbox": obj.source_lead_sandbox,
        "route_candidates": obj.route_candidates,
        "route_requirements": obj.route_requirements,
        "counted_evidence": obj.counted_evidence if can_emit else [],
        "policy_warnings": obj.policy_warnings,
        "independence_warnings": obj.independence_warnings,
    }


__all__ = [
    "ACMGAssessmentSession",
    "FinalizationGateResult",
    "LITERATURE_READY_STATES",
    "SESSION_STATES",
    "action_key",
    "add_overlay_validated_evidence",
    "add_route_candidate",
    "add_source_lead",
    "create_acmg_session",
    "evaluate_finalization_gate",
    "is_acmg_finalization_blocked",
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
