#!/usr/bin/env python3
"""Minimal ToolUniverse ACMG overlay anti-bypass validator.

This validator checks trace compliance only. It does not query databases, run
ToolUniverse tools, assign ACMG strengths, or compute final classifications.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PASS = "PASS"
DRAFT_ONLY = "DRAFT_ONLY"
FAIL = "FAIL"

COUNTABLE_ROUTE_OUTCOMES = {"overlay_applied", "overlay_deferred_to_vcep"}
CLASSIFICATION_STATUS_VALUES = {"final classification", "draft classification"}
ROUTE_OUTCOME_VALUES = {
    "overlay_applied",
    "overlay_not_applicable",
    "overlay_not_assessed",
    "overlay_deferred_to_vcep",
}
QUERY_STATUS_VALUES = {"success", "no_hit", "unavailable", "failed", "not_applicable"}
GUIDANCE_AUTHORITY_VALUES = {
    "ClinGen/SVI primary",
    "ACMG/AMP baseline",
    "VCEP-specific",
    "practice/local refinement",
    "source lead only",
}
FINAL_CLASSIFICATION_LABELS = {
    "pathogenic",
    "likely pathogenic",
    "vus",
    "variant of uncertain significance",
    "likely benign",
    "benign",
}
SOURCE_LABEL_RE = re.compile(
    r"\b(clinvar|hgmd|lovd|expert\s*panel|laboratory|lab\s+assertion|"
    r"paper\s+(?:acmg\s+)?label|author\s+classification|source\s+label)\b",
    re.IGNORECASE,
)
PRIMARY_EVIDENCE_RE = re.compile(r"\b(primary|assay|pedigree|segregation|trio|de novo|case-control|cohort|functional)\b", re.IGNORECASE)
STANDALONE_BENIGN_RE = re.compile(r"\bBA1\b", re.IGNORECASE)
DISCOVERY_TRIGGER_PATTERNS = {
    "pp1_bs4_pp4_segregation": re.compile(r"\b(family|pedigree|segregation|cascade|affected relative|meios(?:is|es))\b", re.IGNORECASE),
    "ps4_case_enrichment": re.compile(r"\b(case-control|cohort|meta-analysis|recurrence|odds ratio|OR\b|confidence interval|unrelated case|case series)\b", re.IGNORECASE),
    "de_novo_ps2_pm6": re.compile(r"\b(de novo|trio|parental testing|paternity|maternity)\b", re.IGNORECASE),
    "pm3_in_trans": re.compile(r"\b(biallelic|in trans|in-trans|phase|phasing|compound heterozyg)\b", re.IGNORECASE),
    "ps3_bs3_functional_assay": re.compile(r"\b(functional assay|in vitro|enzyme activity|minigene|luciferase|western blot|flow cytometry|uptake assay|MaveDB|MAVE|DMS)\b", re.IGNORECASE),
}
DISCOVERY_COVERAGE_ROUTES = set(DISCOVERY_TRIGGER_PATTERNS)


def severity_rank(status: str) -> int:
    return {PASS: 0, DRAFT_ONLY: 1, FAIL: 2}[status]


def max_status(current: str, new_status: str) -> str:
    return new_status if severity_rank(new_status) > severity_rank(current) else current


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def scalar(value: str) -> str:
    value = value.strip()
    if value.startswith(("'", '"')) and value.endswith(("'", '"')):
        return value[1:-1]
    return value


def load_registry(path: Path) -> list[dict[str, Any]]:
    """Parse the small YAML subset used by overlay_registry.yaml.

    PyYAML is intentionally not required so this skill remains portable.
    """

    overlays: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    list_key: str | None = None
    in_overlays = False

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            stripped = line.strip()
            if stripped == "overlays:":
                in_overlays = True
                continue
            if not in_overlays or not stripped or stripped.startswith("#"):
                continue
            if line.startswith("- criterion_group:"):
                if current:
                    overlays.append(current)
                current = {"criterion_group": scalar(line.split(":", 1)[1])}
                list_key = None
                continue
            if current is None:
                continue
            if line.startswith("  ") and not line.startswith("    ") and ":" in stripped:
                key, value = stripped.split(":", 1)
                value = value.strip()
                if value:
                    current[key] = scalar(value)
                    list_key = None
                else:
                    current[key] = []
                    list_key = key
                continue
            if list_key and stripped.startswith("- "):
                current.setdefault(list_key, []).append(scalar(stripped[2:]))

    if current:
        overlays.append(current)
    return overlays


def get_bundle(payload: Any) -> tuple[dict[str, Any] | None, bool]:
    if not isinstance(payload, dict):
        return None, False
    for key in ("acmg_assessment_bundle", "assessment_bundle", "bundle"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value, True
    artifact_keys = {"route_plan", "coverage_audit", "overlay_results", "route_audit", "compatibility_resolution"}
    if artifact_keys.intersection(payload.keys()):
        return payload, True
    return None, False


def text_of(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def is_final_classification(bundle: dict[str, Any] | None, payload: Any) -> bool:
    data = bundle if bundle is not None else payload
    if not isinstance(data, dict):
        return False
    status = str(data.get("classification_status", "")).strip().lower()
    if status == "final classification":
        return True
    if status == "draft classification":
        return False
    label = str(data.get("classification", data.get("final_classification", ""))).strip().lower()
    return label in FINAL_CLASSIFICATION_LABELS


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def consequence_tokens(bundle: dict[str, Any]) -> set[str]:
    variant = bundle.get("variant") if isinstance(bundle.get("variant"), dict) else {}
    raw = " ".join(
        text_of(variant.get(key))
        for key in ("consequence", "variant_type", "hgvs_p", "protein_change")
    ).lower()
    tokens = set(re.split(r"[^a-z0-9_]+", raw))
    if "missense" in raw or re.search(r"p\.[a-z]{3}\d+[a-z]{3}", raw):
        tokens.add("missense_variant")
    return tokens


def route_keys(route: Any) -> set[str]:
    if not isinstance(route, dict):
        return {str(route)}
    keys = set()
    for key in ("criterion_group", "criterion", "overlay_skill", "route_id"):
        value = route.get(key)
        if isinstance(value, str):
            keys.add(value)
        elif isinstance(value, list):
            keys.update(str(v) for v in value)
    return keys


def has_route_for(route_plan: list[Any], group_or_skill: str) -> bool:
    return any(group_or_skill in route_keys(row) for row in route_plan)


def coverage_categories(coverage: list[Any]) -> set[str]:
    categories = set()
    for row in coverage:
        if isinstance(row, dict):
            category = row.get("source_category")
            if isinstance(category, str):
                categories.add(category)
    return categories


def coverage_for_route(coverage: list[Any], route: str) -> list[dict[str, Any]]:
    rows = []
    for row in coverage:
        if not isinstance(row, dict):
            continue
        refs = set(str(v) for v in as_list(row.get("triggered_routes")))
        refs.update(str(v) for v in as_list(row.get("not_triggered_routes")))
        if route in refs:
            rows.append(row)
    return rows


def row_counted(row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    counted = row.get("counted")
    if isinstance(counted, bool):
        return counted
    return False


def covered_criteria(registry: list[dict[str, Any]]) -> set[str]:
    criteria = set()
    for row in registry:
        for criterion in as_list(row.get("covered_criteria")):
            criteria.add(str(criterion))
    return criteria


def required_baseline_groups(registry: list[dict[str, Any]], bundle: dict[str, Any]) -> set[str]:
    tokens = consequence_tokens(bundle)
    required = set()
    for row in registry:
        group = str(row.get("criterion_group", ""))
        policy = row.get("trigger_policy")
        enforcement = row.get("enforcement_level")
        route_kind = row.get("route_kind")
        applies = set(str(v) for v in as_list(row.get("applies_when")))
        if group == "evidence_compatibility_resolution":
            continue
        if policy == "universal_baseline" and enforcement in {"must_plan", "must_query"}:
            if group == "reputable_source_review" and not bundle.get("source_assertions_or_leads"):
                continue
            required.add(group)
        if "missense_variant" in tokens and policy == "variant_type_baseline":
            if "missense_variant" in applies:
                if enforcement in {"must_plan", "must_query"}:
                    required.add(group)
    return required


def resolved_item_text(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        values = []
        for key in ("criterion", "evidence", "applied_evidence", "label", "code"):
            if key in item:
                values.append(text_of(item.get(key)))
        return " ".join(values) or text_of(item)
    return text_of(item)


def counted_row_matches_resolved(row: dict[str, Any], resolved: list[Any]) -> bool:
    criterion = str(row.get("criterion", ""))
    proposed = str(row.get("proposed_evidence", ""))
    for item in resolved:
        text = resolved_item_text(item)
        if criterion and criterion in text:
            return True
        if proposed and proposed in text:
            return True
    return False


def literature_rows(coverage: list[Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in coverage
        if isinstance(row, dict) and str(row.get("source_category", "")) == "literature"
    ]


def validate(payload: Any, registry: list[dict[str, Any]]) -> dict[str, Any]:
    status = PASS
    violations: list[dict[str, str]] = []
    bundle, has_bundle = get_bundle(payload)
    final_requested = is_final_classification(bundle, payload)

    def add(new_status: str, code: str, message: str) -> None:
        nonlocal status
        status = max_status(status, new_status)
        violations.append({"severity": new_status, "code": code, "message": message})

    if not has_bundle or bundle is None:
        if final_requested:
            add(FAIL, "missing_assessment_bundle", "Final ACMG classification was presented without an ACMG overlay assessment bundle.")
        else:
            add(DRAFT_ONLY, "missing_assessment_bundle", "No ACMG overlay assessment bundle was found; only draft output is allowed.")
        return {"status": status, "violations": violations}

    required_sections = ["route_plan", "coverage_audit", "overlay_results", "route_audit", "compatibility_resolution", "classification_status"]
    for section in required_sections:
        if section not in bundle:
            add(DRAFT_ONLY, f"missing_{section}", f"Assessment bundle is missing required section `{section}`.")

    route_plan = as_list(bundle.get("route_plan"))
    coverage = as_list(bundle.get("coverage_audit"))
    route_audit = as_list(bundle.get("route_audit"))
    compatibility = bundle.get("compatibility_resolution")
    covered = covered_criteria(registry)

    classification_status = bundle.get("classification_status")
    if classification_status not in CLASSIFICATION_STATUS_VALUES:
        add(DRAFT_ONLY, "invalid_classification_status", "classification_status must be `final classification` or `draft classification`.")
    for section_name, section_value in (
        ("route_plan", bundle.get("route_plan")),
        ("coverage_audit", bundle.get("coverage_audit")),
        ("overlay_results", bundle.get("overlay_results")),
        ("route_audit", bundle.get("route_audit")),
    ):
        if section_name in bundle and not isinstance(section_value, list):
            add(DRAFT_ONLY, f"invalid_{section_name}_type", f"`{section_name}` must be an array.")
    for row in route_audit:
        if not isinstance(row, dict):
            add(DRAFT_ONLY, "invalid_route_audit_row", "Every route_audit row must be an object.")
            continue
        if "counted" not in row or not isinstance(row.get("counted"), bool):
            add(DRAFT_ONLY, "invalid_counted_type", "route_audit.counted must be a boolean.")
        outcome = row.get("route_outcome")
        if outcome not in ROUTE_OUTCOME_VALUES:
            add(DRAFT_ONLY, "invalid_route_outcome", f"route_audit.route_outcome `{outcome}` is not a controlled value.")
        authority = row.get("guidance_authority")
        if authority is not None and authority not in GUIDANCE_AUTHORITY_VALUES:
            add(DRAFT_ONLY, "invalid_guidance_authority", f"guidance_authority `{authority}` is not a controlled value.")
    for row in coverage:
        if not isinstance(row, dict):
            add(DRAFT_ONLY, "invalid_coverage_audit_row", "Every coverage_audit row must be an object.")
            continue
        query_status = row.get("query_status")
        if query_status not in QUERY_STATUS_VALUES:
            add(DRAFT_ONLY, "invalid_query_status", f"coverage_audit.query_status `{query_status}` is not a controlled value.")

    for row in route_audit:
        if not row_counted(row):
            continue
        criterion = str(row.get("criterion", "")) if isinstance(row, dict) else ""
        outcome = str(row.get("route_outcome", "")) if isinstance(row, dict) else ""
        authority = str(row.get("guidance_authority", "")) if isinstance(row, dict) else ""
        proposed = text_of(row.get("proposed_evidence")) if isinstance(row, dict) else text_of(row)
        source = text_of(row.get("overlay_or_vcep_source")) if isinstance(row, dict) else ""
        combined = " ".join([proposed, source, text_of(row.get("reason") if isinstance(row, dict) else "")])
        if outcome not in COUNTABLE_ROUTE_OUTCOMES:
            add(FAIL, "counted_without_countable_route_outcome", f"Counted evidence `{criterion}` has route outcome `{outcome}`.")
        if authority == "source lead only":
            add(FAIL, "source_lead_counted", f"Counted evidence `{criterion}` is marked as source lead only.")
        if SOURCE_LABEL_RE.search(combined) and not PRIMARY_EVIDENCE_RE.search(combined):
            add(FAIL, "source_label_counted", f"Counted evidence `{criterion}` appears to rely directly on a source label.")
        if criterion in covered and not source:
            add(FAIL, "covered_criterion_missing_overlay_source", f"Covered criterion `{criterion}` is counted without overlay or VCEP source.")

    for group in required_baseline_groups(registry, bundle):
        if not has_route_for(route_plan, group):
            add(DRAFT_ONLY, "missing_applicable_baseline_route", f"Applicable baseline route `{group}` is missing from route_plan.")

    categories = coverage_categories(coverage)
    if "missense_variant" in consequence_tokens(bundle):
        for category in ("population", "computational", "functional_database"):
            if category not in categories:
                add(DRAFT_ONLY, "missing_missense_coverage_audit", f"Missense assessment lacks `{category}` coverage audit.")

    for row in coverage:
        if not isinstance(row, dict):
            continue
        hits = as_list(row.get("hits"))
        triggered = [str(v) for v in as_list(row.get("triggered_routes"))]
        source_category = str(row.get("source_category", ""))
        if hits and not triggered and row.get("query_status") == "success" and source_category in {"functional_database", "literature", "clinical_context", "source_assertion"}:
            add(DRAFT_ONLY, "coverage_hit_without_triggered_route", "Coverage audit reports hits but no triggered route.")
        for route in triggered:
            if not has_route_for(route_plan, route):
                add(DRAFT_ONLY, "triggered_route_missing_from_plan", f"Coverage triggered `{route}` but route_plan does not include it.")

    if final_requested:
        lit_rows = literature_rows(coverage)
        if not lit_rows:
            add(DRAFT_ONLY, "missing_literature_discovery_coverage", "Final classification requires literature discovery coverage, or an explicit unavailable/not_applicable literature row.")
        else:
            not_triggered = set()
            for row in lit_rows:
                not_triggered.update(str(v) for v in as_list(row.get("not_triggered_routes")))
                hit_text = text_of(row.get("hits"))
                for route, pattern in DISCOVERY_TRIGGER_PATTERNS.items():
                    if pattern.search(hit_text) and not has_route_for(route_plan, route):
                        add(DRAFT_ONLY, "literature_trigger_missing_route", f"Literature coverage has a `{route}` trigger but route_plan does not include it.")
            if not any(str(row.get("query_status")) in {"unavailable", "not_applicable"} for row in lit_rows):
                missing_no_hit_routes = sorted(DISCOVERY_COVERAGE_ROUTES - not_triggered - {route for route in DISCOVERY_COVERAGE_ROUTES if has_route_for(route_plan, route)})
                if missing_no_hit_routes:
                    add(DRAFT_ONLY, "incomplete_literature_no_hit_audit", f"Literature coverage must document not_triggered_routes for discovery families: {', '.join(missing_no_hit_routes)}.")

    discovery_groups = [
        str(row.get("criterion_group"))
        for row in registry
        if row.get("trigger_policy") == "evidence_discovery"
    ]
    for group in discovery_groups:
        if has_route_for(route_plan, group):
            continue
        rows = coverage_for_route(coverage, group)
        if rows:
            no_hit_or_na = any(str(row.get("query_status")) in {"no_hit", "not_applicable", "unavailable"} for row in rows)
            if no_hit_or_na:
                continue
        if final_requested and any(group in text_of(row) for row in route_audit):
            add(DRAFT_ONLY, "discovery_route_referenced_but_missing", f"Discovery route `{group}` is referenced but missing from route_plan.")

    if not isinstance(compatibility, dict):
        add(DRAFT_ONLY, "missing_compatibility_resolution", "Compatibility resolution is missing or not an object.")
    else:
        unresolved = as_list(compatibility.get("unresolved_conflicts"))
        resolved = as_list(compatibility.get("current_counted_evidence_resolved"))
        if unresolved and final_requested:
            add(DRAFT_ONLY, "unresolved_compatibility_conflicts", "Unresolved compatibility conflicts block final classification.")
        if "current_counted_evidence_resolved" not in compatibility and final_requested:
            add(DRAFT_ONLY, "missing_resolved_counted_evidence", "Compatibility resolution lacks current_counted_evidence_resolved.")
        if final_requested and not resolved:
            add(DRAFT_ONLY, "empty_resolved_counted_evidence", "Final classification requires non-empty current_counted_evidence_resolved.")
        counted_rows = [row for row in route_audit if isinstance(row, dict) and row_counted(row)]
        valid_counted_rows = [
            row
            for row in counted_rows
            if row.get("route_outcome") in COUNTABLE_ROUTE_OUTCOMES
        ]
        if final_requested and not valid_counted_rows:
            add(DRAFT_ONLY, "missing_counted_route_audit", "Final classification requires at least one counted route_audit row with a countable overlay/VCEP outcome.")
        if final_requested and resolved and not any(STANDALONE_BENIGN_RE.search(resolved_item_text(item)) for item in resolved):
            if not any(counted_row_matches_resolved(row, resolved) for row in valid_counted_rows):
                add(DRAFT_ONLY, "resolved_evidence_without_counted_audit_match", "Resolved counted evidence must match at least one counted route_audit row.")

    if status != PASS and final_requested and str(bundle.get("classification_status", "")).lower() == "final classification":
        # DRAFT_ONLY is the normal downgrade for incomplete traces. FAIL remains
        # reserved for direct bypass patterns such as counted source labels.
        pass

    return {"status": status, "violations": violations}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a ToolUniverse ACMG overlay assessment bundle.")
    parser.add_argument("output_json", type=Path, help="Agent output JSON or raw ACMG assessment bundle JSON.")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "overlay_registry.yaml",
        help="Path to overlay_registry.yaml.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print validation JSON.")
    args = parser.parse_args(argv)

    payload = load_json(args.output_json)
    registry = load_registry(args.registry)
    result = validate(payload, registry)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return {PASS: 0, DRAFT_ONLY: 2, FAIL: 1}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
