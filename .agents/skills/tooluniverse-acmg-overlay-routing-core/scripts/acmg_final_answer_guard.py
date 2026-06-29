#!/usr/bin/env python3
"""Block or downgrade final ACMG labels unless validator and semantics pass."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


FULL_FINAL_LABEL_RE = re.compile(
    r"\b("
    r"Likely\s+Pathogenic|Likely\s+Benign|"
    r"Pathogenic|Benign|VUS|"
    r"Variants?\s+of\s+(?:Uncertain|Unknown)\s+Significance|"
    r"Uncertain\s+Significance"
    r")\b",
    re.IGNORECASE,
)
PAIRED_ABBREVIATION_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:P\s*/\s*LP|LP\s*/\s*P|LB\s*/\s*B|B\s*/\s*LB)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
STANDALONE_ABBREVIATION_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:LP|LB|VUS)(?![A-Za-z0-9])"
    r"(?!(?:\s+(?:score|value|cell|phenotype|domain|gene|frequency|population|protein))\b)",
    re.IGNORECASE,
)
CONTEXTUAL_SINGLE_LETTER_RE = re.compile(
    r"\b(?:ACMG(?:\s+classification)?|final(?:\s+classification)?|classification|"
    r"classified\s+as|result|verdict)\b"
    r"\s*(?::|=|\bis\b|\bas\b)?\s*['\"]?(P|B)['\"]?"
    r"(?=$|[\s.;,)\]])",
    re.IGNORECASE,
)


def _matches(text: str) -> list[str]:
    labels: list[str] = []
    for pattern in (FULL_FINAL_LABEL_RE, PAIRED_ABBREVIATION_RE, STANDALONE_ABBREVIATION_RE):
        labels.extend(match.group(0) for match in pattern.finditer(text or ""))
    labels.extend(match.group(1) for match in CONTEXTUAL_SINGLE_LETTER_RE.finditer(text or ""))
    seen: set[str] = set()
    unique: list[str] = []
    for label in labels:
        key = label.lower()
        if key not in seen:
            seen.add(key)
            unique.append(label)
    return unique


def contains_final_acmg_label(text: str) -> bool:
    """Return true when text contains a final ACMG five-tier label or guarded abbreviation."""
    return bool(_matches(text))


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
