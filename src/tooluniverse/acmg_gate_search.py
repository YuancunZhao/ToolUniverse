"""Shared ACMG overlay gate search helpers."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

ACMG_FRONT_DOOR_TOOL_NAME = "ACMG_overlay_gate_assess_variant"
ACMG_GATE_NOTICE = (
    "ACMG gate: direct ToolUniverse tools such as GeneBe, InterVar, ClinVar, "
    "SpliceAI, MyVariant, and Ensembl VEP provide source leads, route triggers, "
    "or annotation inputs only; they are not ACMG counted evidence. Final "
    "germline ACMG/pathogenicity output requires ACMG_overlay_gate_assess_variant, "
    "an acmg_assessment_bundle, and validator_status: PASS."
)

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


def prepend_acmg_gate_tool(tools: List[Any]) -> List[Any]:
    for index, item in enumerate(tools):
        if not isinstance(item, dict):
            continue
        if str(item.get("name") or item.get("tool_name")) == ACMG_FRONT_DOOR_TOOL_NAME:
            return [item, *tools[:index], *tools[index + 1 :]]
    return [acmg_gate_tool_search_entry(), *tools]


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


def add_acmg_gate_to_search_payload(payload: Any) -> Any:
    if isinstance(payload, list):
        return prepend_acmg_gate_tool(payload)
    if isinstance(payload, dict):
        payload.setdefault("acmg_gate_notice", ACMG_GATE_NOTICE)
        payload.setdefault("recommended_front_door_tool", ACMG_FRONT_DOOR_TOOL_NAME)
        for key in ("tools", "results", "data"):
            if isinstance(payload.get(key), list):
                payload[key] = prepend_acmg_gate_tool(payload[key])
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
