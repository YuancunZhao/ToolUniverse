"""Evidence independence and double-counting guard for ACMG finalization."""

from __future__ import annotations

from collections import defaultdict
import json
from typing import Any

try:
    from .session import session_from_dict
except ImportError:  # pragma: no cover - direct file execution in tests.
    from tooluniverse.acmg_gate.session import session_from_dict


def _source_key(row: dict[str, Any]) -> str:
    return str(
        row.get("evidence_id")
        or row.get("source_id")
        or row.get("pmid")
        or row.get("case_id")
        or row.get("source")
        or row.get("provenance")
        or row.get("tool_name")
        or ""
    )


def _criterion(row: dict[str, Any]) -> str:
    return str(row.get("criterion") or row.get("suggested_criterion") or "").split("_", 1)[0]


def _blob(*values: Any) -> str:
    return json.dumps(values, ensure_ascii=False, sort_keys=True, default=str).lower()


def evaluate_evidence_independence(session: dict[str, Any] | Any) -> dict[str, Any]:
    """Inspect counted evidence and route candidates for independence violations."""

    obj = session_from_dict(session)
    counted = [row for row in obj.counted_evidence if isinstance(row, dict)]
    route_candidates = [row for row in obj.route_candidates if isinstance(row, dict)]
    source_leads = [row for row in obj.source_lead_sandbox if isinstance(row, dict)]
    warnings: list[dict[str, Any]] = []
    blocking_reasons: list[str] = []

    for row in counted:
        if row.get("source_lead_only") or row.get("acmg_countable_evidence") is False:
            blocking_reasons.append(f"source lead cannot be counted: {_criterion(row) or row.get('tool_name')}")
        if str(row.get("criterion")).upper() in {"PP5", "BP6"}:
            blocking_reasons.append("PP5/BP6 source assertions are deprecated and cannot be counted")

    pp1_rows = [row for row in counted if _criterion(row) == "PP1"]
    for row in pp1_rows:
        if not row.get("confirmed_relative_genotypes") and not row.get("genotype_supported"):
            blocking_reasons.append("PP1 requires genotype-supported segregation; phenotype-only family history is candidate-only")
            warnings.append(
                {
                    "code": "pp1_requires_relative_genotypes",
                    "criterion": "PP1",
                    "required_action": "test_relatives_for_variant",
                    "counted": False,
                }
            )

    pp4_sources = {_source_key(row) for row in counted if _criterion(row) == "PP4" and _source_key(row)}
    for row in pp1_rows:
        key = _source_key(row)
        if key and key in pp4_sources:
            warnings.append(
                {
                    "code": "pp1_pp4_overlap",
                    "message": "PP1 and PP4 appear to rely on the same phenotype/family source",
                    "preferred_counting": "PP4_counted_PP1_candidate_until_genotype_supported",
                }
            )
            if not row.get("confirmed_relative_genotypes") and not row.get("genotype_supported"):
                blocking_reasons.append("PP1/PP4 overlap without genotype-supported segregation")

    by_source: dict[str, set[str]] = defaultdict(set)
    for row in counted:
        key = _source_key(row)
        if key:
            by_source[key].add(_criterion(row))
    for key, criteria in by_source.items():
        if {"PS3", "PM4"}.issubset(criteria):
            blocking_reasons.append("PS3 and PM4 cannot both be counted from the same functional/minigene source")
            warnings.append({"code": "ps3_pm4_same_source_overlap", "source": key})

    ps4_rows = [row for row in counted if _criterion(row) == "PS4"]
    seen_cases: set[str] = set()
    duplicate_cases: set[str] = set()
    for row in ps4_rows:
        case_ids = row.get("case_ids") or row.get("cases") or row.get("case_id")
        if isinstance(case_ids, str):
            case_ids = [case_ids]
        if not case_ids:
            warnings.append({"code": "ps4_missing_case_level_provenance", "max_strength": "Supporting"})
            continue
        for case_id in case_ids:
            case_key = str(case_id)
            if case_key in seen_cases:
                duplicate_cases.add(case_key)
            seen_cases.add(case_key)
    if duplicate_cases:
        warnings.append({"code": "ps4_duplicate_cases", "duplicate_case_ids": sorted(duplicate_cases), "max_strength": "Supporting"})
        blocking_reasons.append("PS4 case counting requires deduplicated case-level provenance")

    for row in counted:
        if _criterion(row) == "PM2" and row.get("variant_region") in {"intronic", "deep_intronic"}:
            if not row.get("coverage_adequacy"):
                row["strength"] = "supporting"
                row["population_absence_status"] = "absent_but_intronic_coverage_uncertain"
                warnings.append(
                    {
                        "code": "pm2_intronic_coverage_uncertain",
                        "criterion": "PM2",
                        "max_strength": "Supporting",
                    }
                )

    source_blob = _blob(source_leads, route_candidates)
    if "genebe" in source_blob and any(term in source_blob for term in ("ps3", "pm2", "pp3", "pp5", "likely_pathogenic")):
        warnings.append({"code": "genebe_criteria_source_lead_only", "counted": False})

    return {
        "status": "BLOCK" if blocking_reasons else "PASS",
        "blocking_reasons": list(dict.fromkeys(blocking_reasons)),
        "warnings": warnings,
        "counted_evidence": counted,
    }


__all__ = ["evaluate_evidence_independence"]
