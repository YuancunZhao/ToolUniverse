"""Canonical finalization gate for ACMG overlay outputs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

import hashlib
import json


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

try:
    from .session import (
        evaluate_finalization_gate,
        session_from_dict,
        session_to_dict,
    )
except ImportError:  # pragma: no cover - direct file execution in tests.
    from tooluniverse.acmg_gate.session import (
        evaluate_finalization_gate,
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
    """Compute whether final ACMG classification wording is allowed.

    Deprecated: prefer evaluate_finalization_gate() which accepts a session object.
    This wrapper remains for backward compatibility with acmg_overlay_gate_tool.py.
    """
    import warnings

    warnings.warn(
        "compute_finalization_gate is deprecated; use evaluate_finalization_gate",
        DeprecationWarning,
        stacklevel=2,
    )

    gate = evaluate_finalization_gate(
        {
            "state": "READY_FOR_FINALIZER" if bundle_final_requested else "DRAFT_ONLY",
            "classification_status": "final classification" if bundle_final_requested else "draft classification",
            "validator_status": validator_status or "NOT_RUN",
            "semantic_combiner_status": semantic_combiner_status or "NOT_RUN",
            "final_classification_allowed": final_classification_allowed,
            "counted_evidence": counted_evidence or [],
            "literature_status": "ready" if literature_ready else "not_reviewed",
        }
    )
    blocking_reasons = list(gate.blocking_reasons)
    if not bundle_final_requested:
        blocking_reasons.append("bundle classification_status is not final classification")
    return {
        "final_allowed": not blocking_reasons,
        "gates": {
            "validator_status": gate.validator_status,
            "semantic_combiner_status": gate.semantic_combiner_status,
            "final_classification_allowed": gate.final_classification_allowed,
            "bundle_final_requested": bundle_final_requested,
            "has_counted_evidence": gate.counted_evidence_count > 0,
            "literature_ready": literature_ready,
        },
        "blocking_reasons": list(dict.fromkeys(blocking_reasons)),
        "finalization_gate": gate.to_dict(),
    }


def _token_basis(obj: Any, classification: str) -> dict[str, Any]:
    counted_hash = _stable_hash(obj.counted_evidence)
    required_hash = _stable_hash(
        {
            "required": obj.required_next_actions,
            "completed": obj.completed_actions,
            "route_requirements": obj.route_requirements,
        }
    )
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
    gate = evaluate_finalization_gate(obj)
    independence = gate.evidence_independence or {}
    if independence:
        obj.counted_evidence = independence.get("counted_evidence", obj.counted_evidence)
        obj.independence_warnings = independence.get("warnings", [])
    blocking_reasons: list[str] = list(gate.blocking_reasons)
    if not final_classification:
        blocking_reasons.append("classification is missing")
    if blocking_reasons:
        return {
            "status": "BLOCK",
            "finalization_token_issued": False,
            "blocking_reasons": list(dict.fromkeys(blocking_reasons)),
            "finalization_gate": gate.to_dict(),
            "evidence_independence": independence,
            "blocking_route_requirements": gate.blocking_route_requirements,
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
        "evidence_independence": independence,
        "acmg_session": session_to_dict(obj),
    }
    return {
        "status": "PASS",
        "finalization_token_issued": True,
        **payload,
    }


def _fail_response(reason: str, **extra: Any) -> dict[str, Any]:
    """Build a uniform FAIL dict with default-fill for common token-verification keys."""
    extra.setdefault("status", "FAIL")
    extra.setdefault("valid", False)
    extra.setdefault("classification", None)
    extra.setdefault("token_classification", None)
    extra.setdefault("expected_classification", None)
    extra["reason"] = reason
    return extra


def verify_finalization_token(
    finalization_token: str | None,
    session: dict[str, Any] | Any | None = None,
    *,
    expected_classification: str | None = None,
) -> dict[str, Any]:
    """Verify token shape and, when supplied, session/classification binding."""

    if not finalization_token or not str(finalization_token).startswith("acmg-final:v1:"):
        return _fail_response("missing or invalid ACMG finalization token")
    if session is None:
        if expected_classification:
            return _fail_response(
                "session is required to verify classification binding",
                expected_classification=expected_classification,
            )
        return {"status": "PASS", "valid": True, "reason": "token shape valid"}
    obj = session_from_dict(session)
    token_classification = obj.classification
    classification = expected_classification or token_classification
    if obj.finalization_token and obj.finalization_token != finalization_token:
        return _fail_response(
            "token does not match session",
            classification=token_classification,
            token_classification=token_classification,
            expected_classification=expected_classification,
        )
    if obj.state != "FINALIZED":
        return _fail_response(
            "session is not FINALIZED",
            classification=token_classification,
            token_classification=token_classification,
            expected_classification=expected_classification,
        )
    gate = evaluate_finalization_gate(obj)
    if not gate.can_finalize:
        return _fail_response(
            "session finalization gates do not pass",
            classification=token_classification,
            token_classification=token_classification,
            expected_classification=expected_classification,
            finalization_gate=gate.to_dict(),
            blocking_route_requirements=gate.blocking_route_requirements,
        )
    if not classification:
        return _fail_response(
            "classification is missing",
            classification=token_classification,
            token_classification=token_classification,
            expected_classification=expected_classification,
        )
    basis = _token_basis(obj, classification)
    expected_token = _token_from_basis(basis)
    if expected_token != finalization_token:
        return _fail_response(
            "token does not match session classification basis",
            classification=token_classification,
            token_classification=token_classification,
            expected_classification=expected_classification,
            counted_evidence_hash=basis["counted_evidence_hash"],
            required_actions_hash=basis["required_actions_hash"],
        )
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
