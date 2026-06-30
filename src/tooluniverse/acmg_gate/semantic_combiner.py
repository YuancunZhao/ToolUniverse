#!/usr/bin/env python3
"""Conservative semantic ACMG combiner used by the overlay bundle validator.

This is a guardrail, not a clinical classifier. It implements only explicit,
high-confidence ACMG qualitative combinations and returns VUS when evidence is
insufficient, conflicting, or outside the supported rule subset.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


PASS = "PASS"
FAIL = "FAIL"
NOT_APPLICABLE = "NOT_APPLICABLE"

FINAL_LABELS = {
    "pathogenic": "Pathogenic",
    "likely pathogenic": "Likely_pathogenic",
    "likely_pathogenic": "Likely_pathogenic",
    "vus": "VUS",
    "variant of uncertain significance": "VUS",
    "likely benign": "Likely_benign",
    "likely_benign": "Likely_benign",
    "benign": "Benign",
}

CRITERION_RE = re.compile(r"\b(BA1|BS[1-4]|BP[1-7]|PVS1|PS[1-4]|PM[1-6]|PP[1-5])(?:_([A-Za-z]+))?\b")
STRENGTH_ALIASES = {
    "verystrong": "very_strong",
    "very_strong": "very_strong",
    "strong": "strong",
    "moderate": "moderate",
    "supporting": "supporting",
    "standalone": "standalone",
    "stand_alone": "standalone",
}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def text_of(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def normalize_label(value: Any) -> str:
    raw = str(value or "").strip().lower().replace("-", " ").replace("_", " ")
    return FINAL_LABELS.get(raw, str(value or "").strip())


def evidence_text(item: Any) -> str:
    if isinstance(item, dict):
        parts = []
        for key in ("criterion", "evidence", "applied_evidence", "label", "code", "strength"):
            if key in item:
                parts.append(text_of(item.get(key)))
        return " ".join(parts) or text_of(item)
    return text_of(item)


def parse_strength(criterion: str, suffix: str | None) -> str:
    if criterion == "BA1":
        return "standalone"
    if suffix:
        return STRENGTH_ALIASES.get(suffix.replace(" ", "").lower(), suffix.lower())
    if criterion == "PVS1":
        return "very_strong"
    if criterion.startswith("PS") or criterion.startswith("BS"):
        return "strong"
    if criterion.startswith("PM"):
        return "moderate"
    if criterion.startswith("PP") or criterion.startswith("BP"):
        return "supporting"
    return "supporting"


def parse_evidence(items: list[Any]) -> list[dict[str, str]]:
    parsed: list[dict[str, str]] = []
    for item in items:
        text = evidence_text(item)
        for match in CRITERION_RE.finditer(text):
            criterion = match.group(1)
            parsed.append({"criterion": criterion, "strength": parse_strength(criterion, match.group(2)), "source_text": text})
    return parsed


def _counts(evidence: list[dict[str, str]], prefix: str) -> dict[str, int]:
    counts = {"very_strong": 0, "strong": 0, "moderate": 0, "supporting": 0, "standalone": 0}
    for item in evidence:
        criterion = item["criterion"]
        if prefix == "pathogenic" and not criterion.startswith(("PVS", "PS", "PM", "PP")):
            continue
        if prefix == "benign" and not criterion.startswith(("BA", "BS", "BP")):
            continue
        counts[item["strength"]] = counts.get(item["strength"], 0) + 1
    return counts


def _pathogenic_classification(counts: dict[str, int]) -> str:
    vs = counts.get("very_strong", 0)
    strong = counts.get("strong", 0)
    moderate = counts.get("moderate", 0)
    supporting = counts.get("supporting", 0)
    if vs >= 1 and (strong >= 1 or moderate >= 2 or (moderate >= 1 and supporting >= 1) or supporting >= 2):
        return "Pathogenic"
    if strong >= 2:
        return "Pathogenic"
    if vs >= 1 and moderate >= 1:
        return "Likely_pathogenic"
    if strong >= 1 and moderate >= 1:
        return "Likely_pathogenic"
    if strong >= 1 and supporting >= 2:
        return "Likely_pathogenic"
    if moderate >= 3:
        return "Likely_pathogenic"
    if moderate >= 2 and supporting >= 2:
        return "Likely_pathogenic"
    return "VUS"


def _benign_classification(counts: dict[str, int]) -> str:
    if counts.get("standalone", 0) > 0:
        return "Benign"
    strong = counts.get("strong", 0)
    supporting = counts.get("supporting", 0)
    if strong >= 2:
        return "Benign"
    if strong >= 1 and supporting >= 1:
        return "Likely_benign"
    if supporting >= 2:
        return "Likely_benign"
    return "VUS"


def compute_classification(evidence: list[dict[str, str]], unresolved_conflicts: list[Any] | None = None) -> tuple[str, list[str]]:
    violations: list[str] = []
    if unresolved_conflicts:
        return "VUS", ["unresolved_conflicts_block_non_vus_classification"]
    pathogenic = _counts(evidence, "pathogenic")
    benign = _counts(evidence, "benign")
    has_pathogenic = any(pathogenic.values())
    has_benign = any(benign.values())
    if has_pathogenic and has_benign:
        return "VUS", ["pathogenic_and_benign_evidence_requires_documented_compatibility_resolution"]
    if has_benign:
        return _benign_classification(benign), violations
    if has_pathogenic:
        return _pathogenic_classification(pathogenic), violations
    return "VUS", violations


def validate_bundle_semantics(bundle: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(bundle, dict):
        return {
            "semantic_combiner_status": NOT_APPLICABLE,
            "computed_classification": None,
            "reported_classification": None,
            "semantic_violations": [],
        }

    classification_status = str(bundle.get("classification_status", "")).strip().lower()
    reported = normalize_label(bundle.get("classification") or bundle.get("final_classification"))
    if classification_status != "final classification":
        return {
            "semantic_combiner_status": NOT_APPLICABLE,
            "computed_classification": None,
            "reported_classification": reported or None,
            "semantic_violations": [],
        }

    compatibility = bundle.get("compatibility_resolution") if isinstance(bundle.get("compatibility_resolution"), dict) else {}
    resolved = as_list(compatibility.get("current_counted_evidence_resolved"))
    unresolved = as_list(compatibility.get("unresolved_conflicts"))
    evidence = parse_evidence(resolved)
    computed, semantic_violations = compute_classification(evidence, unresolved)
    status = PASS
    if not reported:
        semantic_violations.append("final_classification_missing_reported_label")
    elif reported != computed:
        semantic_violations.append(f"reported_classification_{reported}_unsupported_by_computed_{computed}")
    if semantic_violations:
        status = FAIL
    return {
        "semantic_combiner_status": status,
        "computed_classification": computed,
        "reported_classification": reported or None,
        "semantic_violations": semantic_violations,
    }


def main(argv: list[str] | None = None) -> int:
    path = Path((argv or sys.argv[1:])[0])
    payload = json.loads(path.read_text(encoding="utf-8"))
    bundle = payload.get("acmg_assessment_bundle", payload) if isinstance(payload, dict) else None
    result = validate_bundle_semantics(bundle)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["semantic_combiner_status"] in {PASS, NOT_APPLICABLE} else 1


if __name__ == "__main__":
    raise SystemExit(main())
