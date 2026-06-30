"""Canonical ACMG overlay gate policy shared by runtime and skill scripts."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, List

try:
    from .final_label_detector import contains_final_acmg_label, final_acmg_label_matches
    from .intent_detector import ACMGIntent, detect_acmg_intent, looks_like_acmg_gate_query
except ImportError:  # pragma: no cover - file-path imports from standalone checks.
    _here = Path(__file__).resolve().parent
    _final_spec = importlib.util.spec_from_file_location(
        "acmg_final_label_detector",
        _here / "final_label_detector.py",
    )
    _intent_spec = importlib.util.spec_from_file_location(
        "acmg_intent_detector",
        _here / "intent_detector.py",
    )
    if _final_spec is None or _final_spec.loader is None or _intent_spec is None or _intent_spec.loader is None:
        raise
    _final_module = importlib.util.module_from_spec(_final_spec)
    _intent_module = importlib.util.module_from_spec(_intent_spec)
    _final_spec.loader.exec_module(_final_module)
    _intent_spec.loader.exec_module(_intent_module)
    contains_final_acmg_label = _final_module.contains_final_acmg_label
    final_acmg_label_matches = _final_module.final_acmg_label_matches
    ACMGIntent = _intent_module.ACMGIntent
    detect_acmg_intent = _intent_module.detect_acmg_intent
    looks_like_acmg_gate_query = _intent_module.looks_like_acmg_gate_query

ACMG_FRONT_DOOR_TOOL_NAME = "ACMG_overlay_gate_assess_variant"
ACMG_ALLOWED_USE = "source_lead_or_route_input"

ACMG_GATE_NOTICE = (
    "ACMG gate: direct ToolUniverse tools such as GeneBe, InterVar, ClinVar, "
    "SpliceAI, MyVariant, Ensembl VEP, gnomAD, MaveDB/DMS, ClinGen/G2P, "
    "GeneReviews, and related variant evidence tools provide source leads, "
    "coverage hits, route triggers, or annotation inputs only; they are not "
    "ACMG counted evidence. Final germline ACMG/pathogenicity output requires "
    "ACMG_overlay_gate_assess_variant, an acmg_assessment_bundle, "
    "validator_status: PASS, semantic_combiner_status: PASS, "
    "final_classification_allowed: true, and ACMG_guard_final_answer PASS."
)

SOURCE_LEAD_NOTICE = (
    "Automated classifier, database label, predictor score, or annotation output "
    "is a source lead or route trigger only. It is not ACMG counted evidence "
    "until routed through an overlay or in-scope VCEP and validated in an "
    "acmg_assessment_bundle."
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

ACMG_ORDINARY_INTERNAL_STEPS = {
    "ACMG_plan_variant_assessment",
    "ACMG_collect_variant_evidence",
    "ACMG_apply_overlay_routes",
    "ACMG_finalize_assessment",
    "ACMG_guard_final_answer",
}

RECOMMENDED_ACMG_INTAKE_TOOLS: List[Dict[str, Any]] = [
    {
        "tool_name": "tooluniverse-literature-deep-research",
        "source_category": "literature",
        "purpose": "Run online literature discovery before final ACMG classification; record no-hit results as coverage, not evidence.",
        "route_input_for": ["PP1/BS4/PP4", "PS4", "PS2/PM6", "PM3", "PS3/BS3"],
    },
    {
        "tool_name": "NCBI/PubMed literature search",
        "source_category": "literature",
        "purpose": "Search PubMed for variant, rsID, gene-disease, family, cohort, and functional/RNA evidence.",
        "route_input_for": ["literature coverage audit"],
    },
    {
        "tool_name": "PMC/EuropePMC full-text search",
        "source_category": "literature",
        "purpose": "Search full text, tables, supplements, and figures when abstracts or source assertions mention primary evidence.",
        "route_input_for": ["literature provenance", "full-text/supplement coverage"],
    },
    {
        "tool_name": "tooluniverse-literature-figure-evidence-extraction",
        "source_category": "literature",
        "purpose": "Extract primary evidence from figures, pedigrees, assay panels, tables, or supplements when literature hits require it.",
        "route_input_for": ["PS3/BS3", "PP1/BS4/PP4", "PS4"],
    },
    {
        "tool_name": "EnsemblVEP_annotate_hgvs",
        "source_category": "computational",
        "purpose": "Normalize consequence, transcript, protein effect, and colocated variant context.",
        "route_input_for": ["PVS1", "PM4/BP3", "PS1/PM5", "PP3/BP4"],
    },
    {
        "tool_name": "ClinVar_get_clinical_significance",
        "source_category": "source_assertion",
        "purpose": "Retrieve ClinVar assertion as source lead only; do not count the label directly.",
        "route_input_for": ["PP5/BP6 source review", "source_assertions_or_leads"],
    },
    {
        "tool_name": "MyVariant_get_pathogenicity_scores",
        "source_category": "computational",
        "purpose": "Retrieve predictor and dbNSFP context as PP3/BP4 route input only.",
        "route_input_for": ["PP3/BP4"],
    },
    {
        "tool_name": "SpliceAI_predict_splice",
        "source_category": "computational",
        "purpose": "Retrieve splice prediction as splicing/prediction route input only.",
        "route_input_for": ["splice bundle", "PP3-style prediction", "PVS1-splicing boundary"],
    },
    {
        "tool_name": "GeneBe_classify_variant",
        "source_category": "source_assertion",
        "purpose": "Retrieve automated ACMG-style label as source lead only.",
        "route_input_for": ["source_assertions_or_leads"],
    },
    {
        "tool_name": "InterVar_classify_variant",
        "source_category": "source_assertion",
        "purpose": "Retrieve automated ACMG-style label as source lead/comparator only.",
        "route_input_for": ["source_assertions_or_leads"],
    },
]

RECOMMENDED_ACMG_INTAKE_TOOL_NAMES = tuple(
    row["tool_name"]
    for row in RECOMMENDED_ACMG_INTAKE_TOOLS
    if isinstance(row.get("tool_name"), str) and "_" in row["tool_name"]
)

REQUIRED_ACMG_COVERAGE_CATEGORIES: List[Dict[str, Any]] = [
    {
        "source_category": "literature",
        "required_before_final": True,
        "must_be_online": True,
        "acceptable_query_status": ["success", "no_hit", "failed", "unavailable"],
        "reason": "Final classification requires actual online literature discovery; no-hit is acceptable, no-search is not.",
    },
    {
        "source_category": "population",
        "required_before_final": True,
        "reason": "Population frequency outputs are coverage inputs; BA1/BS1/PM2 require overlay routing.",
    },
    {
        "source_category": "computational",
        "required_before_final": True,
        "reason": "VEP/SpliceAI/MyVariant/CADD/SIFT/PolyPhen outputs are route inputs, not counted evidence.",
    },
    {
        "source_category": "functional_database",
        "required_before_final": True,
        "reason": "MaveDB/DMS hits trigger PS3/BS3 overlay; no-hit is documented coverage.",
    },
    {
        "source_category": "disease_context",
        "required_before_final": True,
        "reason": "ClinGen/G2P/GeneReviews resolve disease/mechanism context but do not count as ACMG evidence.",
    },
]

DISCOVERY_NO_HIT_ROUTES = [
    "pp1_bs4_pp4_segregation",
    "ps4_case_enrichment",
    "de_novo_ps2_pm6",
    "pm3_in_trans",
    "ps3_bs3_functional_assay",
]


def acmg_source_lead_metadata() -> dict[str, Any]:
    """Return the required metadata for high-risk direct tools."""

    return {
        "source_lead_only": True,
        "acmg_countable_evidence": False,
        "final_classification_allowed": False,
        "allowed_use": ACMG_ALLOWED_USE,
        "must_route_through": ACMG_FRONT_DOOR_TOOL_NAME,
        "acmg_gate_notice": ACMG_GATE_NOTICE,
        "recommended_front_door_tool": ACMG_FRONT_DOOR_TOOL_NAME,
    }


def source_lead_only_metadata() -> dict[str, Any]:
    """Public alias for high-risk source-lead-only metadata."""

    return acmg_source_lead_metadata()


def is_high_risk_acmg_tool(name: str) -> bool:
    """Return true when a direct tool must be treated as source-lead-only."""

    return name in HIGH_RISK_ACMG_GATE_TOOLS


def attach_acmg_gate_notice(payload_or_result: Any) -> Any:
    """Attach canonical source-lead metadata to a dict payload/result."""

    if not isinstance(payload_or_result, dict):
        return payload_or_result
    payload_or_result.update(acmg_source_lead_metadata())
    metadata = payload_or_result.setdefault("metadata", {})
    if isinstance(metadata, dict):
        metadata.update(acmg_source_lead_metadata())
    else:
        payload_or_result["metadata"] = {
            "original_metadata": metadata,
            **acmg_source_lead_metadata(),
        }
    return payload_or_result


__all__ = [
    "ACMG_ALLOWED_USE",
    "ACMG_FRONT_DOOR_TOOL_NAME",
    "ACMG_GATE_NOTICE",
    "ACMGIntent",
    "ACMG_ORDINARY_INTERNAL_STEPS",
    "DISCOVERY_NO_HIT_ROUTES",
    "HIGH_RISK_ACMG_GATE_TOOLS",
    "RECOMMENDED_ACMG_INTAKE_TOOLS",
    "RECOMMENDED_ACMG_INTAKE_TOOL_NAMES",
    "REQUIRED_ACMG_COVERAGE_CATEGORIES",
    "SOURCE_LEAD_NOTICE",
    "acmg_source_lead_metadata",
    "attach_acmg_gate_notice",
    "contains_final_acmg_label",
    "detect_acmg_intent",
    "final_acmg_label_matches",
    "looks_like_acmg_gate_query",
    "is_high_risk_acmg_tool",
    "source_lead_only_metadata",
]
