"""Shared ACMG overlay gate search helpers."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

ACMG_FRONT_DOOR_TOOL_NAME = "ACMG_overlay_gate_assess_variant"
ACMG_GATE_NOTICE = (
    "ACMG gate: direct ToolUniverse tools such as GeneBe, InterVar, ClinVar, "
    "SpliceAI, MyVariant, Ensembl VEP, gnomAD, MaveDB/DMS, ClinGen/G2P, "
    "GeneReviews, and related variant evidence tools provide source leads, "
    "coverage hits, route triggers, or annotation inputs only; they are not "
    "ACMG counted evidence. Final germline ACMG/pathogenicity output requires "
    "ACMG_overlay_gate_assess_variant, an acmg_assessment_bundle, and "
    "validator_status: PASS."
)

HIGH_RISK_ACMG_GATE_TOOLS = {
    "GeneBe_classify_variant",
    "GeneBe_classify_variants_batch",
    "InterVar_classify_variant",
    "ClinVar_get_clinical_significance",
    "ClinVar_get_variant_details",
    "ClinVar_search_variants",
    "ClinVarSubmitted_get_assertions",
    "SpliceAI_predict_splice",
    "SpliceAI_get_max_delta",
    "SpliceAI_predict_pangolin",
    "MyVariant_get_pathogenicity_scores",
    "MyVariant_get_variant",
    "EnsemblVEP_annotate_hgvs",
    "EnsemblVEP_variant_recoder",
    "gnomad_search_variants",
    "gnomad_get_variant",
    "gnomad_get_variant_populations",
    "MaveDB_search_score_sets",
    "MaveDB_get_score_set",
    "MaveDB_get_variant_scores",
    "MaveDB_get_effect_matrix",
    "MaveDB_get_mapped_variants",
    "MaveDB_get_clinical_controls",
    "MaveDB_get_gnomad_variants",
    "ClinGen_search_gene_validity",
    "G2P_search",
    "G2P_get_record",
    "G2P_get_gene",
    "MedGen_search",
}

RECOMMENDED_ACMG_DIRECT_TOOLS = (
    "EnsemblVEP_variant_recoder",
    "EnsemblVEP_annotate_hgvs",
    "ClinVar_get_clinical_significance",
    "MyVariant_get_pathogenicity_scores",
    "SpliceAI_predict_splice",
    "GeneBe_classify_variant",
    "InterVar_classify_variant",
)


def acmg_direct_tool_search_entry(tool_name: str) -> Dict[str, Any]:
    return {
        "name": tool_name,
        "tool_name": tool_name,
        "description": (
            "Recommended direct ToolUniverse evidence-intake tool for ACMG workflows. "
            "Use only after ACMG_overlay_gate_assess_variant; output is a source lead, "
            "coverage hit, route trigger, or annotation input, not counted ACMG evidence."
        ),
        "category": "acmg_evidence_intake",
        "acmg_gate_notice": ACMG_GATE_NOTICE,
        "recommended_front_door_tool": ACMG_FRONT_DOOR_TOOL_NAME,
        "priority": "direct_tool_after_acmg_front_door",
    }

_ACMG_INTENT_TERMS = (
    "acmg",
    "pathogenicity",
    "clinical significance",
    "variant classification",
    "variant interpretation",
    "five-tier",
    "5-tier",
    "likely pathogenic",
    "pathogenic",
    "vus",
    "致病性",
    "变异解读",
    "临床意义",
    "评级",
    "分类",
    "杂合",
    "纯合",
    "acmg规则",
)
_VARIANT_CONTEXT_TERMS = (
    "variant",
    "germline",
    "hgvs",
    "gene",
    "变异",
    "基因",
    "杂合",
    "纯合",
)
_HGVS_PATTERNS = (
    re.compile(r"\bN[MR]_\d+(?:\.\d+)?:[cgmnpr]\.", re.IGNORECASE),
    re.compile(r"\b[gcpmn]\.\d+", re.IGNORECASE),
    re.compile(r":[cp]\.", re.IGNORECASE),
    re.compile(r"\bchr(?:[0-9]{1,2}|x|y|m):", re.IGNORECASE),
    re.compile(r";\s*N[MR]_\d+", re.IGNORECASE),
)


def looks_like_acmg_gate_query(query: str) -> bool:
    lowered = (query or "").lower()
    has_intent = any(term in lowered for term in _ACMG_INTENT_TERMS)
    has_variant_context = any(term in lowered for term in _VARIANT_CONTEXT_TERMS)
    has_hgvs = any(pattern.search(query or "") for pattern in _HGVS_PATTERNS)
    return has_intent and (has_variant_context or has_hgvs)


def acmg_gate_tool_search_entry() -> Dict[str, Any]:
    return {
        "name": ACMG_FRONT_DOOR_TOOL_NAME,
        "tool_name": ACMG_FRONT_DOOR_TOOL_NAME,
        "description": (
            "Front-door ACMG overlay compliance gate. Use this before GeneBe, "
            "InterVar, ClinVar, SpliceAI, MyVariant, VEP, or other direct tools "
            "for germline ACMG/pathogenicity final classification. It creates "
            "route plans, normalizes source leads, validates acmg_assessment_bundle, "
            "and reports whether final classification is allowed."
        ),
        "type": "ACMGOverlayGateTool",
        "category": "acmg_overlay_gate",
        "parameters": {
            "type": "object",
            "properties": {"variant": {"type": "string"}},
            "required": ["variant"],
        },
        "acmg_gate_notice": ACMG_GATE_NOTICE,
        "priority": "front_door_required_for_final_acmg_classification",
        "relevance_score": 9999.0,
    }


def _search_item_name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or item.get("tool_name") or "")
    return str(item or "")


def _split_high_risk_tools(tools: List[Any]) -> tuple[List[Any], List[Any]]:
    high_risk: List[Any] = []
    other: List[Any] = []
    for item in tools:
        name = _search_item_name(item)
        if name in HIGH_RISK_ACMG_GATE_TOOLS:
            high_risk.append(item)
        else:
            other.append(item)
    return high_risk, other


def prepend_acmg_gate_tool(tools: List[Any]) -> List[Any]:
    gate_entry = None
    remaining: List[Any] = []
    for item in tools:
        if _search_item_name(item) == ACMG_FRONT_DOOR_TOOL_NAME and gate_entry is None:
            gate_entry = item
        else:
            remaining.append(item)
    if gate_entry is None:
        gate_entry = acmg_gate_tool_search_entry()

    high_risk, other = _split_high_risk_tools(remaining)
    seen = {_search_item_name(item) for item in [gate_entry, *high_risk, *other]}
    default_intake = [
        acmg_direct_tool_search_entry(tool_name)
        for tool_name in RECOMMENDED_ACMG_DIRECT_TOOLS
        if tool_name not in seen
    ]
    return [gate_entry, *high_risk, *default_intake, *other]


def add_acmg_gate_notice_to_search(serialized: str, query: str) -> str:
    if not looks_like_acmg_gate_query(query):
        return serialized
    try:
        payload = json.loads(serialized)
    except (json.JSONDecodeError, ValueError):
        return json.dumps(
            {
                "acmg_gate_notice": ACMG_GATE_NOTICE,
                "recommended_front_door_tool": ACMG_FRONT_DOOR_TOOL_NAME,
                "result": serialized,
            },
            ensure_ascii=False,
        )
    payload = add_acmg_gate_to_search_payload(payload)
    return json.dumps(payload, ensure_ascii=False, default=str)


def _payload_limit(payload: Dict[str, Any]) -> int | None:
    try:
        limit = int(payload.get("limit"))
    except (TypeError, ValueError):
        return None
    return limit if limit > 0 else None


def add_acmg_gate_to_search_payload(payload: Any) -> Any:
    if isinstance(payload, list):
        return prepend_acmg_gate_tool(payload)
    if isinstance(payload, dict):
        payload.setdefault("acmg_gate_notice", ACMG_GATE_NOTICE)
        payload.setdefault("recommended_front_door_tool", ACMG_FRONT_DOOR_TOOL_NAME)
        limit = _payload_limit(payload)
        for key in ("tools", "results", "data"):
            if isinstance(payload.get(key), list):
                tools = prepend_acmg_gate_tool(payload[key])
                payload[key] = tools[:limit] if limit else tools
                break
        else:
            payload.setdefault("tools", [acmg_gate_tool_search_entry()])
        return payload
    return {
        "acmg_gate_notice": ACMG_GATE_NOTICE,
        "recommended_front_door_tool": ACMG_FRONT_DOOR_TOOL_NAME,
        "result": payload,
        "tools": [acmg_gate_tool_search_entry()],
    }


def is_high_risk_acmg_tool(tool_name: str) -> bool:
    return tool_name in HIGH_RISK_ACMG_GATE_TOOLS


def attach_acmg_gate_notice(tool_name: str, result: Any) -> Any:
    if not is_high_risk_acmg_tool(tool_name) or not isinstance(result, dict):
        return result
    result.setdefault("acmg_gate_notice", ACMG_GATE_NOTICE)
    result.setdefault("recommended_front_door_tool", ACMG_FRONT_DOOR_TOOL_NAME)
    metadata = result.setdefault("metadata", {})
    if isinstance(metadata, dict):
        metadata.setdefault("acmg_gate_notice", ACMG_GATE_NOTICE)
        metadata.setdefault("recommended_front_door_tool", ACMG_FRONT_DOOR_TOOL_NAME)
    else:
        result["metadata"] = {
            "original_metadata": metadata,
            "acmg_gate_notice": ACMG_GATE_NOTICE,
            "recommended_front_door_tool": ACMG_FRONT_DOOR_TOOL_NAME,
        }
    return result
