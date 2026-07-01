"""Required overlay transaction helpers for ACMG protocol enforcement.

Boundary:
- session.py owns the state dataclass, primitive state transitions, and the
  canonical finalization gate.
- provenance.py owns tool-call receipts and evidence provenance matching.
- this module applies route plans and overlay results to a session.

It intentionally does not decide finalization eligibility.
"""

from __future__ import annotations

import json
from typing import Any

from .session import missing_required_actions, session_from_dict, session_to_dict

UNIVERSAL_REQUIRED_ACTIONS = (
    "pm2_absence_rarity",
    "ba1_bs1_frequency",
    "evidence_compatibility_resolution",
)


def _append_unique(items: list[Any], action: Any) -> None:
    key = json.dumps(action, sort_keys=True, ensure_ascii=False) if isinstance(action, dict) else str(action)
    seen = {
        json.dumps(item, sort_keys=True, ensure_ascii=False) if isinstance(item, dict) else str(item)
        for item in items
    }
    if key not in seen:
        items.append(action)


def _compute_required_overlay_actions(session: Any, evidence_context: Any = None) -> list[str]:
    """Compute protocol-required overlay actions from session and source context."""

    obj = session_from_dict(session)
    actions = list(UNIVERSAL_REQUIRED_ACTIONS)
    context_text = json.dumps(
        {
            "source_lead_sandbox": obj.source_lead_sandbox,
            "route_candidates": obj.route_candidates,
            "evidence_context": evidence_context,
        },
        ensure_ascii=False,
    ).lower()
    if any(term in context_text for term in ("spliceai", "ds_dg", "splice", "donor", "acceptor")):
        actions.extend(["pp3_bp4_splicing_prediction", "pvs1_splicing_refinement"])
    if any(term in context_text for term in ("cadd", "revel", "alphamissense", "myvariant", "prediction")):
        actions.append("computational_evidence_overlay")
    if any(term in context_text for term in ("genebe", "intervar", "clinvar", "clinical_significance", "classification")):
        actions.append("reputable_source_review")
    if any(term in context_text for term in ("literature", "pubmed", "pmid", "hit_count")):
        actions.append("literature_review")
    if any(term in context_text for term in ("conflict", "unresolved")):
        actions.append("evidence_compatibility_resolution")
    return list(dict.fromkeys(actions))


def add_required_actions_from_plan(session: Any, plan_or_gate_result: Any) -> dict[str, Any]:
    obj = session_from_dict(session)
    for action in _compute_required_overlay_actions(obj, plan_or_gate_result):
        _append_unique(obj.required_next_actions, action)
    if isinstance(plan_or_gate_result, dict):
        for key in ("required_next_actions", "route_triggers", "required_baseline_routes", "triggered_discovery_routes"):
            values = plan_or_gate_result.get(key)
            if not isinstance(values, list):
                continue
            for value in values:
                if isinstance(value, dict):
                    action = value.get("action") or value.get("route") or value.get("route_family") or value.get("criterion_group")
                    if action:
                        _append_unique(obj.required_next_actions, str(action))
                elif value:
                    _append_unique(obj.required_next_actions, str(value))
    if obj.required_next_actions and obj.state not in {"FINALIZED", "ERROR"}:
        obj.state = "OVERLAYS_REQUIRED"
    return session_to_dict(obj)


def apply_overlay_result(session: Any, overlay_result: dict[str, Any]) -> dict[str, Any]:
    obj = session_from_dict(session)
    route = overlay_result.get("route") or overlay_result.get("criterion_group") or overlay_result.get("action")
    if route and route not in obj.completed_actions:
        obj.completed_actions.append(route)
    evidence = overlay_result.get("counted_evidence")
    if isinstance(evidence, dict):
        evidence = [evidence]
    if isinstance(evidence, list):
        for row in evidence:
            if isinstance(row, dict):
                counted = dict(row)
                counted["overlay_validated"] = True
                counted["counted"] = True
                obj.overlay_validated_evidence.append(counted)
                obj.counted_evidence.append(counted)
    if not missing_required_actions(obj):
        obj.state = "READY_FOR_FINALIZER"
    else:
        obj.state = "OVERLAYS_REQUIRED"
    return session_to_dict(obj)


def validate_required_actions_completed(session: Any) -> dict[str, Any]:
    missing = missing_required_actions(session)
    return {
        "status": "PASS" if not missing else "BLOCK",
        "required_actions_complete": not missing,
        "missing_required_actions": missing,
    }


def explain_missing_actions(session: Any) -> list[str]:
    return [f"Required ACMG overlay action is incomplete: {action}" for action in missing_required_actions(session)]


__all__ = [
    "UNIVERSAL_REQUIRED_ACTIONS",
    "add_required_actions_from_plan",
]
