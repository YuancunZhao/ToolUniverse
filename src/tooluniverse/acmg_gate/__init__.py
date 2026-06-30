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
from .final_answer_guard import guard_final_answer
from .final_label_detector import (
    contains_final_acmg_label,
    detect_final_acmg_labels,
    final_acmg_label_matches,
)
from .finalizer import compute_finalization_gate
from .intent_detector import ACMGIntent, classify_acmg_intent, detect_acmg_intent, looks_like_acmg_gate_query
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
    source_lead_only_metadata,
)
from .registry import (
    baseline_routes_for_variant_type,
    criterion_to_group,
    criterion_to_overlay,
    discovery_routes,
    load_overlay_registry,
    required_coverage_for_criterion,
    source_lead_routes,
)
from .semantic_combiner import (
    FAIL as SEMANTIC_FAIL,
    NOT_APPLICABLE as SEMANTIC_NOT_APPLICABLE,
    PASS as SEMANTIC_PASS,
    compute_classification,
    validate_bundle_semantics,
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
    "classify_acmg_intent",
    "detect_acmg_intent",
    "looks_like_acmg_gate_query",
    # Final label detection
    "contains_final_acmg_label",
    "detect_final_acmg_labels",
    "final_acmg_label_matches",
    # Final answer guard
    "guard_final_answer",
    # Finalization gate
    "compute_finalization_gate",
    # Context triggers
    "discover_user_context_routes",
    # Registry
    "baseline_routes_for_variant_type",
    "criterion_to_group",
    "criterion_to_overlay",
    "discovery_routes",
    "load_overlay_registry",
    "required_coverage_for_criterion",
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
    "source_lead_only_metadata",
    # Validation
    "validate_bundle",
]
