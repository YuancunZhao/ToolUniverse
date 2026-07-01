"""ACMG runtime gate — single public import surface.

All ToolUniverse code should import ACMG symbols from here:

    from .acmg_gate import (
        ACMG_GATE_NOTICE,
        ACMGIntent,
        looks_like_acmg_gate_query,
        contains_final_acmg_label,
        compute_finalization_gate,
        discover_user_context_routes,
        criterion_to_group,
        ...
    )

Internal details live in the sub-modules; this __init__ re-exports the
stable public API.
"""

from .context_triggers import discover_user_context_routes
from .final_answer_guard import build_draft_only_response, explain_why_final_blocked, guard_acmg_final_answer
from .final_label_detector import (
    contains_final_acmg_label,
    contains_manual_acmg_counting,
    final_acmg_label_matches,
    manual_acmg_counting_matches,
    normalize_final_acmg_classification,
    normalized_final_acmg_classifications,
)
from .finalizer import compute_finalization_gate, issue_finalization_token, verify_finalization_token
from .evidence_independence import evaluate_evidence_independence
from .intent_detector import ACMGIntent, detect_acmg_intent, looks_like_acmg_gate_query
from .pre_router import route_acmg_intent
from .policy import (
    ACMG_ALLOWED_USE,
    ACMG_FRONT_DOOR_TOOL_NAME,
    ACMG_GATE_NOTICE,
    ACMG_ORDINARY_INTERNAL_STEPS,
    DISCOVERY_NO_HIT_ROUTES,
    HIGH_RISK_ACMG_GATE_TOOLS,
    RECOMMENDED_ACMG_INTAKE_TOOLS,
    RECOMMENDED_ACMG_INTAKE_TOOL_NAMES,
    REQUIRED_ACMG_COVERAGE_CATEGORIES,
    SOURCE_LEAD_NOTICE,
    acmg_source_lead_metadata,
    attach_acmg_gate_notice,
    is_high_risk_acmg_tool,
)
from .registry import (
    baseline_routes_for_variant_type,
    criterion_to_group,
    criterion_to_overlay,
    discovery_routes,
    load_overlay_registry,
    required_coverage_for_criterion,
    resolve_overlay_registry_path,
    source_lead_routes,
)
from .route_policy import (
    blocking_route_requirements,
)
from .session import (
    ACMGAssessmentSession,
    FinalizationGateResult,
    add_overlay_validated_evidence,
    add_route_candidate,
    add_source_lead,
    create_acmg_session,
    evaluate_finalization_gate,
    is_acmg_finalization_blocked,
    mark_completed_action,
    mark_required_action,
    session_can_emit_final_label,
    session_can_finalize,
    session_from_dict,
    session_to_dict,
    session_to_policy_envelope,
    update_session_state,
)
from .semantic_combiner import (
    FAIL as SEMANTIC_FAIL,
    NOT_APPLICABLE as SEMANTIC_NOT_APPLICABLE,
    PASS as SEMANTIC_PASS,
    compute_classification,
    validate_bundle_semantics,
)
from .source_lead_sandbox import sandbox_source_output, source_category_for_tool
from .transaction import (
    add_required_actions_from_plan,
)
from .validate_acmg_overlay_bundle import validate as validate_bundle

__all__ = [
    # Policy constants
    "ACMG_ALLOWED_USE",
    "ACMG_FRONT_DOOR_TOOL_NAME",
    "ACMG_GATE_NOTICE",
    "ACMG_ORDINARY_INTERNAL_STEPS",
    "DISCOVERY_NO_HIT_ROUTES",
    "HIGH_RISK_ACMG_GATE_TOOLS",
    "RECOMMENDED_ACMG_INTAKE_TOOLS",
    "RECOMMENDED_ACMG_INTAKE_TOOL_NAMES",
    "REQUIRED_ACMG_COVERAGE_CATEGORIES",
    "SOURCE_LEAD_NOTICE",
    # Intent detection
    "ACMGIntent",
    "detect_acmg_intent",
    "looks_like_acmg_gate_query",
    # Deprecated intent alias
    "classify_acmg_intent",
    # Final label detection
    "contains_final_acmg_label",
    "contains_manual_acmg_counting",
    "final_acmg_label_matches",
    "manual_acmg_counting_matches",
    "normalize_final_acmg_classification",
    "normalized_final_acmg_classifications",
    # Final answer guard
    "build_draft_only_response",
    "explain_why_final_blocked",
    "guard_acmg_final_answer",
    # Finalization gate
    "compute_finalization_gate",
    "evaluate_finalization_gate",
    "FinalizationGateResult",
    "issue_finalization_token",
    "verify_finalization_token",
    "evaluate_evidence_independence",
    # Pre-router
    "route_acmg_intent",
    # Route policy / provenance
    "blocking_route_requirements",
    # Session
    "ACMGAssessmentSession",
    "add_overlay_validated_evidence",
    "add_route_candidate",
    "add_source_lead",
    "create_acmg_session",
    "is_acmg_finalization_blocked",
    "mark_completed_action",
    "mark_required_action",
    "session_can_emit_final_label",
    "session_can_finalize",
    "session_from_dict",
    "session_to_dict",
    "session_to_policy_envelope",
    "update_session_state",
    # Transaction helpers
    "add_required_actions_from_plan",
    # Sandbox
    "sandbox_source_output",
    "source_category_for_tool",
    "discover_user_context_routes",
    # Registry
    "baseline_routes_for_variant_type",
    "criterion_to_group",
    "criterion_to_overlay",
    "discovery_routes",
    "load_overlay_registry",
    "required_coverage_for_criterion",
    "resolve_overlay_registry_path",
    "source_lead_routes",
    # Semantic combiner
    "SEMANTIC_PASS",
    "SEMANTIC_FAIL",
    "SEMANTIC_NOT_APPLICABLE",
    "compute_classification",
    "validate_bundle_semantics",
    # Policy helpers
    "acmg_source_lead_metadata",
    "attach_acmg_gate_notice",
    "is_high_risk_acmg_tool",
    # Validation
    "validate_bundle",
]
