"""Shared ACMG overlay gate search helpers."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

try:
    from .acmg_gate_policy import (
        ACMG_FRONT_DOOR_TOOL_NAME,
        ACMG_GATE_NOTICE,
        HIGH_RISK_ACMG_GATE_TOOLS,
    )
except ImportError:  # pragma: no cover - used by standalone regression checker imports.
    import importlib.util
    from pathlib import Path

    _policy_path = Path(__file__).with_name("acmg_gate_policy.py")
    _policy_spec = importlib.util.spec_from_file_location("acmg_gate_policy", _policy_path)
    if _policy_spec is None or _policy_spec.loader is None:
        raise
    _policy_module = importlib.util.module_from_spec(_policy_spec)
    _policy_spec.loader.exec_module(_policy_module)
    ACMG_FRONT_DOOR_TOOL_NAME = _policy_module.ACMG_FRONT_DOOR_TOOL_NAME
    ACMG_GATE_NOTICE = _policy_module.ACMG_GATE_NOTICE
    HIGH_RISK_ACMG_GATE_TOOLS = _policy_module.HIGH_RISK_ACMG_GATE_TOOLS


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
            "for germline ACMG/pathogenicity final classification. It provides "
            "preflight guidance, normalizes source leads, validates an "
            "acmg_assessment_bundle, and reports whether final classification is allowed."
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
    return [gate_entry, *high_risk, *other]


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
