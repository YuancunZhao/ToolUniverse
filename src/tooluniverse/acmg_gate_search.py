"""Shared ACMG overlay gate search helpers."""

from __future__ import annotations

import json
from typing import Any, Dict, List

try:
    from .acmg_gate import (
        ACMG_ALLOWED_USE,
        ACMG_FRONT_DOOR_TOOL_NAME,
        ACMG_GATE_NOTICE,
        ACMGIntent,
        HIGH_RISK_ACMG_GATE_TOOLS,
        attach_acmg_gate_notice as attach_source_lead_policy,
        detect_acmg_intent,
        is_high_risk_acmg_tool as policy_is_high_risk_acmg_tool,
        looks_like_acmg_gate_query,
        source_lead_only_metadata,
    )
except ImportError:  # pragma: no cover - used by standalone regression checker imports.
    import importlib.util
    from pathlib import Path

    _here = Path(__file__).resolve().parent / "acmg_gate"
    _policy_path = _here / "policy.py"
    _policy_spec = importlib.util.spec_from_file_location("acmg_gate_policy", _policy_path)
    if _policy_spec is None or _policy_spec.loader is None:
        raise
    _policy_module = importlib.util.module_from_spec(_policy_spec)
    _policy_spec.loader.exec_module(_policy_module)
    ACMG_FRONT_DOOR_TOOL_NAME = _policy_module.ACMG_FRONT_DOOR_TOOL_NAME
    ACMG_ALLOWED_USE = _policy_module.ACMG_ALLOWED_USE
    ACMG_GATE_NOTICE = _policy_module.ACMG_GATE_NOTICE
    HIGH_RISK_ACMG_GATE_TOOLS = _policy_module.HIGH_RISK_ACMG_GATE_TOOLS
    ACMGIntent = _policy_module.ACMGIntent
    attach_source_lead_policy = _policy_module.attach_acmg_gate_notice
    detect_acmg_intent = _policy_module.detect_acmg_intent
    policy_is_high_risk_acmg_tool = _policy_module.is_high_risk_acmg_tool
    looks_like_acmg_gate_query = _policy_module.looks_like_acmg_gate_query
    source_lead_only_metadata = _policy_module.source_lead_only_metadata


def acmg_gate_tool_search_entry() -> Dict[str, Any]:
    return {
        "name": ACMG_FRONT_DOOR_TOOL_NAME,
        "tool_name": ACMG_FRONT_DOOR_TOOL_NAME,
        "description": (
            "Front-door ACMG workflow controller. Use this before GeneBe, "
            "InterVar, ClinVar, SpliceAI, MyVariant, VEP, or other direct tools "
            "for germline ACMG/pathogenicity final classification. Use mode=assess "
            "to run plan, collect, literature review tracking, overlay routing, "
            "bundle validation, and final gate; do not manually combine GeneBe, "
            "ClinVar, SpliceAI, or literature outputs into ACMG criteria."
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
        "acmg_countable_evidence": False,
        "final_classification_allowed": False,
        "allowed_use": ACMG_ALLOWED_USE,
        "must_route_through": ACMG_FRONT_DOOR_TOOL_NAME,
        "source_lead_only": True,
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
            if isinstance(item, dict):
                item.update(source_lead_only_metadata())
            high_risk.append(item)
        else:
            other.append(item)
    return high_risk, other


def prepend_acmg_gate_tool(tools: List[Any], *, final_classification_intent: bool = False) -> List[Any]:
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
    if final_classification_intent:
        return [gate_entry, *high_risk]
    return [gate_entry, *high_risk, *other]


def add_acmg_gate_notice_to_search(serialized: str, query: str) -> str:
    intent = detect_acmg_intent(query)
    if intent == ACMGIntent.NONE:
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
    payload = add_acmg_gate_to_search_payload(payload, intent=intent)
    return json.dumps(payload, ensure_ascii=False, default=str)


def _payload_limit(payload: Dict[str, Any]) -> int | None:
    try:
        limit = int(payload.get("limit"))
    except (TypeError, ValueError):
        return None
    return limit if limit > 0 else None


def _coerce_intent(intent_or_query: ACMGIntent | str | None) -> ACMGIntent | None:
    if isinstance(intent_or_query, ACMGIntent) or intent_or_query is None:
        return intent_or_query
    if isinstance(intent_or_query, str):
        try:
            return ACMGIntent(intent_or_query)
        except ValueError:
            return detect_acmg_intent(intent_or_query)
    return None


def add_acmg_gate_to_search_payload(
    payload: Any,
    intent_or_query: ACMGIntent | str | None = None,
    *,
    intent: ACMGIntent | str | None = None,
) -> Any:
    if intent is not None and intent_or_query is not None:
        raise TypeError("Pass either positional intent_or_query or keyword-only intent, not both.")
    intent_value = _coerce_intent(intent if intent is not None else intent_or_query)
    final_classification_intent = intent_value == ACMGIntent.ACMG_FINAL_CLASSIFICATION
    if isinstance(payload, list):
        return prepend_acmg_gate_tool(payload, final_classification_intent=final_classification_intent)
    if isinstance(payload, dict):
        payload.setdefault("acmg_gate_notice", ACMG_GATE_NOTICE)
        payload.setdefault("recommended_front_door_tool", ACMG_FRONT_DOOR_TOOL_NAME)
        payload.setdefault("final_classification_allowed", False)
        payload.setdefault("source_lead_only", True)
        payload.setdefault("acmg_countable_evidence", False)
        payload.setdefault("must_route_through", ACMG_FRONT_DOOR_TOOL_NAME)
        payload["acmg_intent"] = (intent_value or ACMGIntent.ACMG_RELATED).value
        limit = _payload_limit(payload)
        for key in ("tools", "results", "data"):
            if isinstance(payload.get(key), list):
                tools = prepend_acmg_gate_tool(
                    payload[key],
                    final_classification_intent=final_classification_intent,
                )
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


def add_acmg_gate_to_search_payload_for_query(payload: Any, query: str) -> Any:
    return add_acmg_gate_to_search_payload(payload, intent=detect_acmg_intent(query))


def is_high_risk_acmg_tool(tool_name: str) -> bool:
    return policy_is_high_risk_acmg_tool(tool_name)


def attach_acmg_gate_notice(tool_name: str, result: Any) -> Any:
    if not is_high_risk_acmg_tool(tool_name) or not isinstance(result, dict):
        return result
    return attach_source_lead_policy(result)
