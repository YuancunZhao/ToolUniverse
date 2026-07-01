"""Draft-only response policy for blocked ACMG finalization."""

from __future__ import annotations

from typing import Any

from .final_label_detector import final_acmg_label_matches
from .session import LITERATURE_READY_STATES, missing_required_actions, session_from_dict, session_to_dict


def explain_why_final_blocked(session: Any) -> list[str]:
    obj = session_from_dict(session)
    reasons: list[str] = []
    if obj.validator_status != "PASS":
        reasons.append("validator_status is not PASS")
    if obj.semantic_combiner_status != "PASS":
        reasons.append("semantic_combiner_status is not PASS")
    if obj.final_classification_allowed is not True:
        reasons.append("final_classification_allowed is not true")
    if not obj.counted_evidence:
        reasons.append("no overlay-validated counted evidence")
    if obj.literature_status not in LITERATURE_READY_STATES:
        reasons.append("literature review is not complete")
    for action in missing_required_actions(obj):
        reasons.append(f"required overlay action incomplete: {action}")
    if not obj.finalization_token:
        reasons.append("missing ACMG finalization token")
    return list(dict.fromkeys(reasons))


def build_draft_only_response(session: Any) -> dict[str, Any]:
    obj = session_from_dict(session)
    return {
        "status": "DRAFT_ONLY",
        "allowed_sections": [
            "variant_normalization",
            "source_leads",
            "source_lead_sandbox_summary",
            "counted_false_route_candidates",
            "missing_required_overlays",
            "missing_literature_review",
            "missing_population_frequency_adequacy",
            "missing_functional_evidence",
            "why_final_classification_is_blocked",
            "next_recommended_tooluniverse_actions",
        ],
        "forbidden_without_finalization_token": [
            "final ACMG labels",
            "draft or provisional final-like labels",
            "manual ACMG criteria assignment",
            "counted evidence table unless overlay-validated",
        ],
        "variant": {
            "variant": obj.variant,
            "gene": obj.gene,
            "transcript": obj.transcript,
        },
        "source_lead_sandbox": obj.source_lead_sandbox,
        "route_candidates": obj.route_candidates,
        "missing_required_overlays": missing_required_actions(obj),
        "why_final_classification_is_blocked": explain_why_final_blocked(obj),
        "next_recommended_tooluniverse_actions": [
            "complete required overlay routes",
            "complete or document literature review",
            "validate acmg_assessment_bundle",
            "run ACMG finalizer and final-answer guard",
        ],
        "acmg_session": session_to_dict(obj),
        "final_classification_allowed": False,
        "may_emit_final_label": False,
    }


def sanitize_draft_output(answer_text: str, session: Any) -> dict[str, Any]:
    labels = final_acmg_label_matches(answer_text or "")
    response = build_draft_only_response(session)
    response["removed_final_like_labels"] = labels
    response["original_text_had_final_like_label"] = bool(labels)
    return response


__all__ = ["build_draft_only_response", "explain_why_final_blocked", "sanitize_draft_output"]
