#!/usr/bin/env python3
"""Block or downgrade final ACMG labels unless validator and semantics pass."""

from __future__ import annotations

import json
import sys
import importlib.util
from pathlib import Path
from typing import Any


def _canonical_detector_path() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "src" / "tooluniverse" / "acmg_gate" / "final_label_detector.py"
        if candidate.exists():
            return candidate
    return None


try:
    from tooluniverse.acmg_gate.final_label_detector import (
        contains_final_acmg_label as _canonical_contains_final_acmg_label,
        final_acmg_label_matches,
    )
except Exception:  # pragma: no cover - standalone script from canonical repo.
    _detector_path = _canonical_detector_path()
    if _detector_path is None:
        raise
    _spec = importlib.util.spec_from_file_location("acmg_final_label_detector", _detector_path)
    if _spec is None or _spec.loader is None:
        raise
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    _canonical_contains_final_acmg_label = _module.contains_final_acmg_label
    final_acmg_label_matches = _module.final_acmg_label_matches


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


def guard_final_answer(text: str, bundle_or_status: dict[str, Any]) -> dict[str, Any]:
    payload = _status_payload(bundle_or_status)
    matched = _matches(text)
    required_gates = {
        "validator_status": payload.get("validator_status"),
        "semantic_combiner_status": payload.get("semantic_combiner_status"),
        "final_classification_allowed": payload.get("final_classification_allowed"),
    }
    gates_pass = (
        required_gates["validator_status"] == "PASS"
        and required_gates["semantic_combiner_status"] == "PASS"
        and required_gates["final_classification_allowed"] is True
    )
    if matched and not gates_pass:
        message = "Final ACMG labels require validator_status PASS, semantic_combiner_status PASS, and final_classification_allowed true."
        return {
            "status": "BLOCK",
            "has_final_label": True,
            "matched_labels": matched,
            "required_gates": required_gates,
            "message": message,
            "final_answer_allowed": False,
            "guard_status": "BLOCKED",
            "safe_answer": "Draft/preliminary only: insufficient for final ACMG five-tier classification.",
            "reason": message,
        }
    message = "No blocked final ACMG label detected, or required finalization gates passed."
    return {
        "status": "PASS",
        "has_final_label": bool(matched),
        "matched_labels": matched,
        "required_gates": required_gates,
        "message": message,
        "final_answer_allowed": True,
        "guard_status": "PASS",
        "safe_answer": text,
        "reason": message,
    }


def main() -> int:
    payload = json.loads(sys.stdin.read())
    result = guard_final_answer(str(payload.get("answer", payload.get("final_answer_text", ""))), payload.get("validation", payload.get("bundle_or_status", {})))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
