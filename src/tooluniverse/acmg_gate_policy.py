"""Canonical ACMG overlay gate policy shared by search and gate tools."""

from __future__ import annotations

from typing import Any, Dict, List

ACMG_FRONT_DOOR_TOOL_NAME = "ACMG_overlay_gate_assess_variant"
ACMG_ALLOWED_USE = "source_lead_or_route_input"

ACMG_GATE_NOTICE = (
    "ACMG gate: direct ToolUniverse tools such as GeneBe, InterVar, ClinVar, "
    "SpliceAI, MyVariant, Ensembl VEP, gnomAD, MaveDB/DMS, ClinGen/G2P, "
    "GeneReviews, and related variant evidence tools provide source leads, "
    "coverage hits, route triggers, or annotation inputs only; they are not "
    "ACMG counted evidence. Final germline ACMG/pathogenicity output requires "
    "ACMG_overlay_gate_assess_variant, an acmg_assessment_bundle, and "
    "validator_status: PASS."
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
