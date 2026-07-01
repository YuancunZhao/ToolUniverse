"""Canonical finalization gate for ACMG overlay outputs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

try:
    from .session import (
        LITERATURE_READY_STATES,
        missing_required_actions,
        session_can_finalize,
        session_from_dict,
        session_to_dict,
    )
except ImportError:  # pragma: no cover - direct file execution in tests.
    from tooluniverse.acmg_gate.session import (
        LITERATURE_READY_STATES,
        missing_required_actions,
        session_can_finalize,
        session_from_dict,
        session_to_dict,
    )


def compute_finalization_gate(
    validator_status: str | None,
    semantic_combiner_status: str | None,
    final_classification_allowed: bool,
    bundle_final_requested: bool,
    counted_evidence: list[Any] | None,
    literature_ready: bool,
) -> dict[str, Any]:
    """Compute whether final ACMG classification wording is allowed."""

    has_counted_evidence = bool(counted_evidence)
    gates = {
        "validator_status": validator_status,
        "semantic_combiner_status": semantic_combiner_status,
        "final_classification_allowed": final_classification_allowed,
        "bundle_final_requested": bundle_final_requested,
        "has_counted_evidence": has_counted_evidence,
        "literature_ready": literature_ready,
    }
    blocking_reasons: list[str] = []
    if validator_status != "PASS":
        blocking_reasons.append("validator_status is not PASS")
    if semantic_combiner_status != "PASS":
        blocking_reasons.append("semantic_combiner_status is not PASS")
    if final_classification_allowed is not True:
        blocking_reasons.append("final_classification_allowed is not true")
    if not bundle_final_requested:
        blocking_reasons.append("bundle classification_status is not final classification")
    if not has_counted_evidence:
        blocking_reasons.append("no compatibility-resolved counted evidence")
    if not literature_ready:
        blocking_reasons.append("literature hits are not fully reviewed or no literature coverage is documented")
    return {
        "final_allowed": not blocking_reasons,
        "gates": gates,
        "blocking_reasons": blocking_reasons,
    }


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _token_basis(obj: Any, classification: str) -> dict[str, Any]:
    counted_hash = _stable_hash(obj.counted_evidence)
    required_hash = _stable_hash({"required": obj.required_next_actions, "completed": obj.completed_actions})
    return {
        "session_id": obj.session_id,
        "variant": obj.variant,
        "gene": obj.gene,
        "classification": classification,
        "counted_evidence_hash": counted_hash,
        "required_actions_hash": required_hash,
    }


def _token_from_basis(basis: dict[str, Any]) -> str:
    return f"acmg-final:v1:{_stable_hash(basis)[:32]}"


def issue_finalization_token(
    session: dict[str, Any] | Any,
    *,
    classification: str | None = None,
) -> dict[str, Any]:
    """Issue a deterministic finalization token only after all protocol gates pass."""

    obj = session_from_dict(session)
    final_classification = classification or obj.classification
    blocking_reasons: list[str] = []
    if not session_can_finalize(obj):
        if obj.validator_status != "PASS":
            blocking_reasons.append("validator_status is not PASS")
        if obj.semantic_combiner_status != "PASS":
            blocking_reasons.append("semantic_combiner_status is not PASS")
        if obj.final_classification_allowed is not True:
            blocking_reasons.append("final_classification_allowed is not true")
        if missing_required_actions(obj):
            blocking_reasons.append("required overlay actions are incomplete")
        if obj.literature_status not in LITERATURE_READY_STATES:
            blocking_reasons.append("literature is not ready")
        if not obj.counted_evidence:
            blocking_reasons.append("counted evidence is empty")
    if not final_classification:
        blocking_reasons.append("classification is missing")
    if blocking_reasons:
        return {
            "status": "BLOCK",
            "finalization_token_issued": False,
            "blocking_reasons": list(dict.fromkeys(blocking_reasons)),
        }

    basis = _token_basis(obj, final_classification)
    counted_hash = basis["counted_evidence_hash"]
    required_hash = basis["required_actions_hash"]
    token = _token_from_basis(basis)
    obj.finalization_token = token
    obj.state = "FINALIZED"
    obj.classification = final_classification
    payload = {
        "acmg_finalization_token": token,
        "session_id": obj.session_id,
        "variant": obj.variant,
        "gene": obj.gene,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "validator_status": obj.validator_status,
        "semantic_combiner_status": obj.semantic_combiner_status,
        "final_classification_allowed": True,
        "classification": final_classification,
        "counted_evidence_hash": counted_hash,
        "required_actions_hash": required_hash,
        "classification_basis": obj.counted_evidence,
        "acmg_session": session_to_dict(obj),
    }
    return {
        "status": "PASS",
        "finalization_token_issued": True,
        **payload,
    }


def verify_finalization_token(
    finalization_token: str | None,
    session: dict[str, Any] | Any | None = None,
    *,
    expected_classification: str | None = None,
) -> dict[str, Any]:
    """Verify token shape and, when supplied, session/classification binding."""

    if not finalization_token or not str(finalization_token).startswith("acmg-final:v1:"):
        return {"status": "FAIL", "valid": False, "reason": "missing or invalid ACMG finalization token"}
    if session is None:
        if expected_classification:
            return {
                "status": "FAIL",
                "valid": False,
                "reason": "session is required to verify classification binding",
                "expected_classification": expected_classification,
            }
        return {"status": "PASS", "valid": True, "reason": "token shape valid"}
    obj = session_from_dict(session)
    token_classification = obj.classification
    classification = expected_classification or token_classification
    if obj.finalization_token and obj.finalization_token != finalization_token:
        return {
            "status": "FAIL",
            "valid": False,
            "reason": "token does not match session",
            "classification": token_classification,
            "token_classification": token_classification,
            "expected_classification": expected_classification,
        }
    if obj.state != "FINALIZED":
        return {
            "status": "FAIL",
            "valid": False,
            "reason": "session is not FINALIZED",
            "classification": token_classification,
            "token_classification": token_classification,
            "expected_classification": expected_classification,
        }
    if not session_can_finalize(obj):
        return {
            "status": "FAIL",
            "valid": False,
            "reason": "session finalization gates do not pass",
            "classification": token_classification,
            "token_classification": token_classification,
            "expected_classification": expected_classification,
        }
    if not classification:
        return {
            "status": "FAIL",
            "valid": False,
            "reason": "classification is missing",
            "classification": token_classification,
            "token_classification": token_classification,
            "expected_classification": expected_classification,
        }
    basis = _token_basis(obj, classification)
    expected_token = _token_from_basis(basis)
    if expected_token != finalization_token:
        return {
            "status": "FAIL",
            "valid": False,
            "reason": "token does not match session classification basis",
            "classification": token_classification,
            "token_classification": token_classification,
            "expected_classification": expected_classification,
            "counted_evidence_hash": basis["counted_evidence_hash"],
            "required_actions_hash": basis["required_actions_hash"],
        }
    return {
        "status": "PASS",
        "valid": True,
        "reason": "token verified",
        "classification": token_classification,
        "token_classification": token_classification,
        "expected_classification": expected_classification,
        "counted_evidence_hash": basis["counted_evidence_hash"],
        "required_actions_hash": basis["required_actions_hash"],
    }


__all__ = ["compute_finalization_gate", "issue_finalization_token", "verify_finalization_token"]
