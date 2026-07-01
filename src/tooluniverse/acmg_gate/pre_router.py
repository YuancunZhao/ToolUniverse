"""Protocol pre-router for ACMG overlay-gated workflows."""

from __future__ import annotations

from typing import Any

from .intent_detector import ACMGIntent, detect_acmg_intent
from .policy import ACMG_ALLOWED_USE, ACMG_FRONT_DOOR_TOOL_NAME, ACMG_GATE_NOTICE


def route_acmg_intent(query: str, tool_search_context: Any | None = None) -> dict[str, Any]:
    """Return the canonical routing decision for an incoming user query."""

    intent = detect_acmg_intent(query)
    requires_session = intent == ACMGIntent.ACMG_FINAL_CLASSIFICATION
    related = intent == ACMGIntent.ACMG_RELATED
    decision = {
        "intent": intent.value,
        "requires_acmg_session": requires_session,
        "front_door_tool": ACMG_FRONT_DOOR_TOOL_NAME if intent != ACMGIntent.NONE else None,
        "allow_direct_answer": intent == ACMGIntent.NONE,
        "allow_final_label_without_token": False if intent != ACMGIntent.NONE else True,
        "draft_only_until_finalized": requires_session,
        "source_tools_must_use_sandbox": requires_session,
        "pathogenicity_tools_source_lead_only": requires_session or related,
        "allowed_use": ACMG_ALLOWED_USE if intent != ACMGIntent.NONE else "normal_tool_use",
        "acmg_gate_notice": ACMG_GATE_NOTICE if intent != ACMGIntent.NONE else None,
    }
    if tool_search_context is not None:
        decision["tool_search_context_present"] = True
    return decision


__all__ = ["route_acmg_intent"]
