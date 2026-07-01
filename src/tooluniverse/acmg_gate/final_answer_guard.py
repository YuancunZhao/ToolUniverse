#!/usr/bin/env python3
"""Token-gated final-answer guard for ACMG labels."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _canonical_detector_path() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "src" / "tooluniverse" / "acmg_gate" / "final_label_detector.py"
        if candidate.exists():
            return candidate
    return None


try:
    from . import contains_final_acmg_label as _canonical_contains_final_acmg_label
    from . import final_acmg_label_matches
    from .draft_policy import build_draft_only_response, explain_why_final_blocked
    from .final_label_detector import normalize_final_acmg_classification, normalized_final_acmg_classifications
    from .finalizer import verify_finalization_token
    from .pre_router import route_acmg_intent
    from .session import session_from_dict
except ImportError:
    try:
        from tooluniverse.acmg_gate import (
            contains_final_acmg_label as _canonical_contains_final_acmg_label,
        )
        from tooluniverse.acmg_gate import final_acmg_label_matches
        from tooluniverse.acmg_gate.draft_policy import build_draft_only_response, explain_why_final_blocked
        from tooluniverse.acmg_gate.final_label_detector import normalize_final_acmg_classification, normalized_final_acmg_classifications
        from tooluniverse.acmg_gate.finalizer import verify_finalization_token
        from tooluniverse.acmg_gate.pre_router import route_acmg_intent
        from tooluniverse.acmg_gate.session import session_from_dict
    except Exception:  # pragma: no cover - standalone script from canonical repo.
        detector_path = _canonical_detector_path()
        if detector_path is None:
            raise
        package_dir = detector_path.parent
        tooluniverse_pkg = type(sys)("tooluniverse")
        tooluniverse_pkg.__path__ = [str(package_dir.parent)]
        acmg_pkg = type(sys)("tooluniverse.acmg_gate")
        acmg_pkg.__path__ = [str(package_dir)]
        sys.modules.setdefault("tooluniverse", tooluniverse_pkg)
        sys.modules.setdefault("tooluniverse.acmg_gate", acmg_pkg)
        spec = importlib.util.spec_from_file_location("acmg_final_label_detector", detector_path)
        if spec is None or spec.loader is None:
            raise
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _canonical_contains_final_acmg_label = module.contains_final_acmg_label
        final_acmg_label_matches = module.final_acmg_label_matches
        normalize_final_acmg_classification = module.normalize_final_acmg_classification
        normalized_final_acmg_classifications = module.normalized_final_acmg_classifications
        from tooluniverse.acmg_gate.draft_policy import build_draft_only_response, explain_why_final_blocked
        from tooluniverse.acmg_gate.finalizer import verify_finalization_token
        from tooluniverse.acmg_gate.pre_router import route_acmg_intent
        from tooluniverse.acmg_gate.session import session_from_dict


def _matches(text: str) -> list[str]:
    return final_acmg_label_matches(text)


def contains_final_acmg_label(text: str) -> bool:
    """Return true when text contains a final ACMG five-tier label or guarded abbreviation."""

    return _canonical_contains_final_acmg_label(text)


def has_final_acmg_label(text: str) -> bool:
    """Backward-compatible alias for older callers."""

    return contains_final_acmg_label(text)


def _status_payload(bundle_or_status: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(bundle_or_status, dict):
        return {}
    payload = bundle_or_status.get("acmg_assessment_bundle")
    if isinstance(payload, dict):
        merged = dict(payload)
        merged.update({key: value for key, value in bundle_or_status.items() if key != "acmg_assessment_bundle"})
        return merged
    return bundle_or_status


def _session_payload(payload: dict[str, Any]) -> dict[str, Any]:
    nested = payload.get("acmg_session")
    if isinstance(nested, dict):
        merged = dict(nested)
        for key in (
            "validator_status",
            "semantic_combiner_status",
            "final_classification_allowed",
            "counted_evidence",
            "literature_status",
            "finalization_token",
        ):
            if key in payload:
                merged[key] = payload[key]
        return merged
    return payload


def guard_final_answer(text: str, bundle_or_status: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible wrapper around the stricter protocol guard."""

    payload = _status_payload(bundle_or_status)
    return guard_acmg_final_answer(
        answer_text=text,
        session=payload,
        finalization_token=payload.get("finalization_token") or payload.get("acmg_finalization_token"),
        intent=payload.get("intent") or payload.get("acmg_intent"),
    )


def guard_acmg_final_answer(
    answer_text: str,
    session: dict[str, Any] | Any | None,
    finalization_token: str | None,
    intent: str | None,
) -> dict[str, Any]:
    """Block final-like ACMG labels unless the finalizer token and session verify."""

    text = answer_text or ""
    payload = _status_payload(session if isinstance(session, dict) else {})
    session_payload = dict(_session_payload(payload))
    if finalization_token and not session_payload.get("finalization_token"):
        session_payload["finalization_token"] = finalization_token
    matched = _matches(text)
    normalized_answer_classifications = normalized_final_acmg_classifications(text)
    session_classification = session_payload.get("classification") if isinstance(session_payload, dict) else None
    normalized_session_classification = normalize_final_acmg_classification(session_classification)
    required_gates = {
        "validator_status": session_payload.get("validator_status"),
        "semantic_combiner_status": session_payload.get("semantic_combiner_status"),
        "final_classification_allowed": session_payload.get("final_classification_allowed"),
    }
    gates_pass = (
        required_gates["validator_status"] == "PASS"
        and required_gates["semantic_combiner_status"] == "PASS"
        and required_gates["final_classification_allowed"] is True
    )
    token_check = verify_finalization_token(
        finalization_token,
        session_payload if session_payload else None,
        expected_classification=session_classification if session_payload else None,
    )
    session_state = session_payload.get("state") if isinstance(session_payload, dict) else None
    finalized = session_state == "FINALIZED"
    token_pass = token_check.get("status") == "PASS"
    token_classification = token_check.get("token_classification") or token_check.get("classification") or session_classification
    routed_intent = intent or session_payload.get("intent") or session_payload.get("acmg_intent") or route_acmg_intent(text).get("intent")
    answer_classification_set = set(normalized_answer_classifications)
    conflicting_answer_labels = len(answer_classification_set) > 1
    classification_binding_ok = True
    if matched:
        classification_binding_ok = (
            token_pass
            and bool(normalized_session_classification)
            and not conflicting_answer_labels
            and bool(normalized_answer_classifications)
            and all(value == normalized_session_classification for value in normalized_answer_classifications)
        )

    if matched and (not gates_pass or not token_pass or not finalized or not classification_binding_ok):
        reasons: list[str] = []
        if not gates_pass:
            reasons.append("Final ACMG labels require validator_status PASS, semantic_combiner_status PASS, and final_classification_allowed true.")
        if not token_pass:
            reasons.append("Final ACMG labels require a valid ACMG finalization token.")
        if not finalized:
            reasons.append("Final ACMG labels require session.state FINALIZED.")
        if conflicting_answer_labels:
            reasons.append("Final ACMG answer contains conflicting final classifications.")
        if matched and not normalized_session_classification:
            reasons.append("Final ACMG labels require a session classification bound to the finalization token.")
        if (
            normalized_answer_classifications
            and normalized_session_classification
            and any(value != normalized_session_classification for value in normalized_answer_classifications)
        ):
            reasons.append("Final ACMG answer classification does not match the token-bound session classification.")
        if session_payload:
            try:
                reasons.extend(explain_why_final_blocked(session_from_dict(session_payload)))
            except Exception:
                pass
        message = " ".join(list(dict.fromkeys(reasons)))
        draft_response = build_draft_only_response(session_payload) if isinstance(session_payload, dict) else None
        return {
            "status": "BLOCK",
            "has_final_label": True,
            "matched_labels": matched,
            "detected_final_labels": matched,
            "normalized_answer_classifications": normalized_answer_classifications,
            "token_classification": token_classification,
            "session_classification": session_classification,
            "classification_binding_ok": False,
            "required_gates": required_gates,
            "token_verification": token_check,
            "session_state": session_state,
            "acmg_intent": routed_intent,
            "message": message,
            "final_answer_allowed": False,
            "guard_status": "BLOCKED",
            "safe_answer": "Draft/preliminary only: insufficient for final ACMG five-tier classification.",
            "reason": message,
            "allowed_response_type": "DRAFT_ONLY",
            "draft_only_response": draft_response,
        }

    message = "No blocked final ACMG label detected, or token-gated finalization verified."
    return {
        "status": "PASS",
        "has_final_label": bool(matched),
        "matched_labels": matched,
        "detected_final_labels": matched,
        "normalized_answer_classifications": normalized_answer_classifications,
        "token_classification": token_classification,
        "session_classification": session_classification,
        "classification_binding_ok": classification_binding_ok,
        "required_gates": required_gates,
        "token_verification": token_check,
        "session_state": session_state,
        "acmg_intent": routed_intent,
        "message": message,
        "final_answer_allowed": True,
        "guard_status": "PASS",
        "safe_answer": text,
        "reason": message,
    }


def main() -> int:
    payload = json.loads(sys.stdin.read())
    result = guard_final_answer(
        str(payload.get("answer", payload.get("final_answer_text", ""))),
        payload.get("validation", payload.get("bundle_or_status", {})),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
