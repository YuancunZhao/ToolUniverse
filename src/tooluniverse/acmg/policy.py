"""Internal ACMG evidence-collection policy boundary."""

from __future__ import annotations

from typing import Any

from .source_adapters import adapt_source_output


ACMG_POLICY_CONTEXT = {"acmg_evidence_collection": True}
ACMG_FRONT_DOOR_TOOL_NAME = "ACMG_evidence_collector"
ACMG_ALLOWED_USE = "source_lead_or_audit_context"

ACMG_EVIDENCE_NOTICE = (
    "Within an explicit ACMG evidence-collection policy context, direct provider "
    "outputs are retained as review-only source leads. Use ACMG_evidence_collector "
    "for deterministic EvidenceCards. Search recommendation alone cannot constrain "
    "reasoning outside ToolUniverse, and this runtime does not produce a five-tier "
    "classification. Ordinary ToolUniverse calls retain upstream output."
)

SOURCE_LEAD_NOTICE = (
    "Automated classifier, database label, predictor score, or annotation output "
    "is a source lead or audit fact, not independently adopted ACMG evidence."
)

HIGH_RISK_ACMG_TOOLS = {
    "GeneBe_classify_variant",
    "GeneBe_classify_variants_batch",
    "InterVar_classify_variant",
    "ClinVar_get_clinical_significance",
    "ClinVar_get_variant_details",
    "ClinVar_search_variants",
    "ClinVar_get_submitted_records",
    "ClinVarSubmitted_get_assertions",
    "CADD_get_variant_score",
    "CADD_get_position_scores",
    "CADD_get_range_scores",
    "AlphaMissense_get_protein_scores",
    "AlphaMissense_get_variant_score",
    "AlphaMissense_get_residue_scores",
    "SpliceAI_predict_splice",
    "SpliceAI_get_max_delta",
    "SpliceAI_predict_pangolin",
    "MyVariant_get_pathogenicity_scores",
    "MyVariant_get_variant",
    "EnsemblVEP_annotate_hgvs",
    "EnsemblVEP_annotate_rsid",
    "EnsemblVEP_variant_recoder",
    "ensembl_vep_region",
    "VariantValidator_validate_variant",
    "VariantValidator_format_genomic_to_transcripts",
    "FAVOR_annotate_variant",
    "OpenTargets_get_variant_info",
    "OpenTargets_get_variant_transcript_consequences",
    "Mutalyzer_normalize_variant",
    "GenomeNexus_annotate_variant",
    "GenomeNexus_annotate_dbsnp",
    "ProtVar_map_variant",
    "gProfiler_annotate_snps",
    "EnsemblVar_get_population_frequencies",
    "OpenCRAVAT_annotate_variant",
    "OpenCRAVAT_list_annotators",
    "gnomad_search_variants",
    "gnomad_get_variant",
    "gnomad_get_region",
    "gnomad_get_site_callability",
    "gnomad_get_variant_populations",
    "gnomad_get_constraint",
    "gnomad_get_region_variants",
    "ensembl_lookup_gene",
    "MaveDB_search_score_sets",
    "MaveDB_get_score_set",
    "MaveDB_get_variant_scores",
    "MaveDB_get_effect_matrix",
    "MaveDB_get_mapped_variants",
    "MaveDB_get_clinical_controls",
    "MaveDB_get_gnomad_variants",
    "ClinGen_search_gene_validity",
    "ClinGen_get_dosage_sensitivity",
    "ClinGen_get_actionability_adult",
    "ClinGen_get_actionability_pediatric",
    "ClinGen_get_variant_classifications",
    "G2P_search",
    "G2P_get_record",
    "G2P_get_gene",
    "MedGen_search",
    "EBIProteins_get_variation_by_hgvs",
    "EBIProteins_get_features",
    "InterPro_get_entries_for_protein",
    "UniProt_get_entry_by_accession",
    "HPO_get_term",
    "HPO_search_terms",
    "HPO_get_genes_by_phenotype",
    "HPO_get_diseases_by_phenotype",
    "PubMed_search_articles",
    "LitVar_search_variants",
    "LitVar_get_variant_publications",
    "EuropePMC_search_articles",
    "PubTator3_LiteratureSearch",
    "PubTator3_get_annotations",
    "EPMC_get_text_mined_annotations",
}


class ACMGScopedExecutor:
    """Execute provider tools and quarantine conclusions inside ACMG only."""

    def __init__(self, tooluniverse: Any | None) -> None:
        self.tooluniverse = tooluniverse

    def call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        use_cache: bool = False,
    ) -> Any:
        if self.tooluniverse is None:
            raise RuntimeError("no ToolUniverse executor")
        result = self.tooluniverse.run_one_function(
            {"name": tool_name, "arguments": arguments},
            use_cache=use_cache,
        )
        return sanitize_high_risk_acmg_result(
            tool_name,
            result,
            policy_context=ACMG_POLICY_CONTEXT,
        )

    def call_many(
        self,
        function_calls: list[dict[str, Any]],
        *,
        use_cache: bool = False,
        max_workers: int | None = None,
    ) -> list[Any]:
        if self.tooluniverse is None:
            raise RuntimeError("no ToolUniverse executor")
        run_many = getattr(self.tooluniverse, "run_many_functions", None)
        if callable(run_many):
            results = run_many(
                function_calls,
                use_cache=use_cache,
                max_workers=max_workers,
            )
        else:
            results = [
                self.tooluniverse.run_one_function(call, use_cache=use_cache)
                for call in function_calls
            ]
        return [
            sanitize_high_risk_acmg_result(
                str(call.get("name") or ""),
                result,
                policy_context=ACMG_POLICY_CONTEXT,
            )
            for call, result in zip(function_calls, results, strict=True)
        ]


def acmg_source_lead_metadata() -> dict[str, Any]:
    return {
        "source_lead_only": True,
        "final_classification_allowed": False,
        "allowed_use": ACMG_ALLOWED_USE,
        "acmg_evidence_notice": ACMG_EVIDENCE_NOTICE,
        "recommended_front_door_tool": ACMG_FRONT_DOOR_TOOL_NAME,
    }


def sanitize_high_risk_acmg_result(
    tool_name: str,
    result: Any,
    *,
    status: str | None = None,
    policy_context: dict[str, Any] | None = None,
) -> Any:
    """Adapt a direct provider result only inside an explicit ACMG context."""
    active = (
        isinstance(policy_context, dict)
        and policy_context.get("acmg_evidence_collection") is True
    )
    if not active or tool_name not in HIGH_RISK_ACMG_TOOLS:
        return result
    if isinstance(result, dict) and isinstance(
        result.get("source_lead_sandbox"), dict
    ):
        return result
    response_status = status
    if response_status is None and isinstance(result, dict):
        response_status = str(result.get("status") or "success")
    if isinstance(result, dict) and isinstance(
        result.get("reviewable_features"), dict
    ):
        source_lead = {
            "tool_name": tool_name,
            "source_category": "provider",
            "reviewable_features": dict(result["reviewable_features"]),
            "quarantined_conclusions": {},
            "source_provenance": {},
            "source_lead_only": True,
            "final_classification_allowed": False,
            "raw_source_present": True,
        }
    else:
        source_lead = adapt_source_output(tool_name, result)
    return {
        "status": response_status or "success",
        "tool_name": tool_name,
        "source_lead_only": True,
        "final_classification_allowed": False,
        "recommended_front_door_tool": ACMG_FRONT_DOOR_TOOL_NAME,
        "source_lead_sandbox": source_lead,
        "acmg_evidence_notice": ACMG_EVIDENCE_NOTICE,
    }


__all__ = [
    "ACMG_ALLOWED_USE",
    "ACMG_EVIDENCE_NOTICE",
    "ACMG_FRONT_DOOR_TOOL_NAME",
    "ACMG_POLICY_CONTEXT",
    "ACMGScopedExecutor",
    "HIGH_RISK_ACMG_TOOLS",
    "SOURCE_LEAD_NOTICE",
    "acmg_source_lead_metadata",
    "sanitize_high_risk_acmg_result",
]
