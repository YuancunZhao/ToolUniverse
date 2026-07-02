"""Shared ACMG overlay gate search helpers."""

from __future__ import annotations

import json
from typing import Any, Dict, List

# ACMG overlay MCP tools — exposed in search so LLM can discover them
# independently of the Gate
ACMG_OVERLAY_TOOLS = {
    "ACMG_combine_criteria",
    "ACMG_overlay_ba1_exception",
    "ACMG_overlay_benign_context",
    "ACMG_overlay_case_enrichment",
    "ACMG_overlay_de_novo",
    "ACMG_overlay_functional_assay",
    "ACMG_overlay_pm1_bp1",
    "ACMG_overlay_pm2",
    "ACMG_overlay_pm3_in_trans",
    "ACMG_overlay_pp3_bp4",
    "ACMG_overlay_protein_length",
    "ACMG_overlay_ps1_pm5",
    "ACMG_overlay_ps1_splicing",
    "ACMG_overlay_pvs1_lof",
    "ACMG_overlay_pvs1_splicing",
    "ACMG_overlay_segregation",
    "ACMG_overlay_source_review",
    "ACMG_route_overlays",
}

try:
    from .acmg_gate import (
        ACMG_ALLOWED_USE,
        ACMG_FRONT_DOOR_TOOL_NAME,
        ACMG_GATE_NOTICE,
        ACMGIntent,
        HIGH_RISK_ACMG_GATE_TOOLS,
        acmg_source_lead_metadata,
        attach_acmg_gate_notice as attach_source_lead_policy,
        detect_acmg_intent,
        is_high_risk_acmg_tool as policy_is_high_risk_acmg_tool,
        looks_like_acmg_gate_query,
        route_acmg_intent,
    )
except ImportError:  # pragma: no cover - used by standalone regression checker imports.
    import importlib.util
    from pathlib import Path

    _here = Path(__file__).resolve().parent / "acmg_gate"
    _policy_path = _here / "policy.py"
    _intent_path = _here / "intent_detector.py"
    _policy_spec = importlib.util.spec_from_file_location("acmg_gate_policy", _policy_path)
    _intent_spec = importlib.util.spec_from_file_location("acmg_intent_detector", _intent_path)
    if _policy_spec is None or _policy_spec.loader is None or _intent_spec is None or _intent_spec.loader is None:
        raise
    _policy_module = importlib.util.module_from_spec(_policy_spec)
    _intent_module = importlib.util.module_from_spec(_intent_spec)
    _policy_spec.loader.exec_module(_policy_module)
    _intent_spec.loader.exec_module(_intent_module)
    ACMG_FRONT_DOOR_TOOL_NAME = _policy_module.ACMG_FRONT_DOOR_TOOL_NAME
    ACMG_ALLOWED_USE = _policy_module.ACMG_ALLOWED_USE
    ACMG_GATE_NOTICE = _policy_module.ACMG_GATE_NOTICE
    HIGH_RISK_ACMG_GATE_TOOLS = _policy_module.HIGH_RISK_ACMG_GATE_TOOLS
    ACMGIntent = _intent_module.ACMGIntent
    attach_source_lead_policy = _policy_module.attach_acmg_gate_notice
    detect_acmg_intent = _intent_module.detect_acmg_intent
    policy_is_high_risk_acmg_tool = _policy_module.is_high_risk_acmg_tool
    looks_like_acmg_gate_query = _intent_module.looks_like_acmg_gate_query
    def route_acmg_intent(query: str, tool_search_context: Any | None = None) -> dict[str, Any]:
        intent_value = detect_acmg_intent(query)
        requires_session = intent_value == ACMGIntent.ACMG_FINAL_CLASSIFICATION
        return {
            "intent": intent_value.value,
            "requires_acmg_session": requires_session,
            "front_door_tool": ACMG_FRONT_DOOR_TOOL_NAME if intent_value != ACMGIntent.NONE else None,
            "allow_direct_answer": intent_value == ACMGIntent.NONE,
            "allow_final_label_without_token": False if intent_value != ACMGIntent.NONE else True,
            "draft_only_until_finalized": requires_session,
            "source_tools_must_use_sandbox": requires_session,
            "pathogenicity_tools_source_lead_only": intent_value != ACMGIntent.NONE,
            "allowed_use": ACMG_ALLOWED_USE if intent_value != ACMGIntent.NONE else "normal_tool_use",
            "acmg_gate_notice": ACMG_GATE_NOTICE if intent_value != ACMGIntent.NONE else None,
        }
    acmg_source_lead_metadata = _policy_module.acmg_source_lead_metadata


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
        "source_tools_must_use_sandbox": True,
        "allow_final_label_without_token": False,
        "draft_only_until_finalized": True,
    }


def _search_item_name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or item.get("tool_name") or "")
    return str(item or "")


def _split_high_risk_tools(tools: List[Any]) -> tuple[List[Any], List[Any], List[Any]]:
    high_risk: List[Any] = []
    overlay: List[Any] = []
    other: List[Any] = []
    for item in tools:
        name = _search_item_name(item)
        if name in HIGH_RISK_ACMG_GATE_TOOLS:
            if isinstance(item, dict):
                item.update(acmg_source_lead_metadata())
                item["source_tools_must_use_sandbox"] = True
                item["may_emit_final_label"] = False
            high_risk.append(item)
        elif name in ACMG_OVERLAY_TOOLS:
            if isinstance(item, dict):
                _inject_overlay_description(item, name)
            overlay.append(item)
        else:
            other.append(item)
    return high_risk, overlay, other


def _inject_overlay_description(item: dict, name: str) -> None:
    descriptions = {
        "ACMG_route_overlays": (
            "Determine which ACMG criteria overlays apply to a variant. "
            "Call this FIRST after identifying variant type (missense/nonsense/splice). "
            "Input: variant HGVS + gene symbol. "
            "Output: list of applicable baseline overlays + literature-dependent overlays "
            "with recommended evidence sources for each."
        ),
        "ACMG_overlay_pm2": (
            "Judge PM2 evidence (population absence/rarity) per ClinGen SVI PM2 v1.0. "
            "Input: gnomAD allele frequency, coverage adequacy, disease prevalence. "
            "Output: PM2_Supporting / not_met / not_assessed with ClinGen reasoning. "
            "Use this instead of manually interpreting gnomAD frequencies."
        ),
        "ACMG_combine_criteria": (
            "Combine ACMG overlay results into a 5-tier ACMG/AMP 2015 classification. "
            "Input: list of overlay outputs (criterion + strength from each overlay tool). "
            "Output: Pathogenic / Likely Pathogenic / VUS / Likely Benign / Benign "
            "with counted criteria, explanation, and recommended next steps. "
            "Includes ClinGen SVI special rules (PVS1+PM2_Supporting→LP)."
        ),
    }
    if name in descriptions:
        item["description"] = descriptions[name]
        item["category"] = "acmg_overlay_tool"
        item["deterministic"] = True
        item["overlay_validated"] = True


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

    high_risk, overlay, other = _split_high_risk_tools(remaining)
    if final_classification_intent:
        return [gate_entry, *overlay, *high_risk]
    return [gate_entry, *overlay, *high_risk, *other]


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
    routing_decision = None
    if isinstance(intent_value, ACMGIntent):
        routing_decision = route_acmg_intent(intent_value.value)
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
        if routing_decision:
            payload["acmg_routing_decision"] = routing_decision
            payload["allow_direct_answer"] = routing_decision["allow_direct_answer"]
            payload["allow_final_label_without_token"] = routing_decision["allow_final_label_without_token"]
            payload["source_tools_must_use_sandbox"] = routing_decision["source_tools_must_use_sandbox"]
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
