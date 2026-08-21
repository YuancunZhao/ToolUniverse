"""NEK8 regression for nonblocking provider context and SpliceAI row scope."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from tooluniverse.acmg.collector import ACMGEvidencePipeline


class NEK8ProviderFixture:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def run_one_function(self, call: dict[str, Any], **_kwargs: Any) -> Any:
        self.calls.append(deepcopy(call))
        name = str(call.get("name") or "")
        if name == "VariantValidator_gene2transcripts":
            return {
                "status": "success",
                "data": [
                    {
                        "current_symbol": "NEK8",
                        "transcripts": [
                            {
                                "reference": "NM_178170.3",
                                "annotations": {
                                    "mane_select": True,
                                    "mane_plus_clinical": False,
                                },
                            }
                        ],
                    }
                ],
            }
        if name == "VariantValidator_validate_variant":
            return {
                "status": "success",
                "reviewable_features": {
                    "chr": "17",
                    "pos": 28740462,
                    "ref": "G",
                    "alt": "A",
                    "build": "GRCh38",
                    "validated_hgvs_c": "NM_178170.3:c.1418-1G>A",
                    "hgvs_c": "NM_178170.3:c.1418-1G>A",
                    "hgvs_g": "NC_000017.11:g.28740462G>A",
                    "gene": "NEK8",
                    "transcript": "NM_178170.3",
                    "consequence_candidates": [
                        {
                            "gene": "NEK8",
                            "transcript": "NM_178170.3",
                            "mane_select": "NM_178170.3",
                            "hgvsc": "NM_178170.3:c.1418-1G>A",
                            "consequence": ["splice_acceptor_variant"],
                            "exon": "11/14",
                        }
                    ],
                    "provider_version": "VariantValidator NEK8 fixture 1",
                },
            }
        if name == "VariantValidator_format_genomic_to_transcripts":
            return {
                "status": "success",
                "reviewable_features": {
                    "chr": "17",
                    "pos": 28740462,
                    "ref": "G",
                    "alt": "A",
                    "build": "GRCh38",
                    "hgvs_g": "NC_000017.11:g.28740462G>A",
                    "gene": "NEK8",
                    "transcript": "NM_178170.3",
                    "consequence_candidates": [
                        {
                            "gene": "NEK8",
                            "transcript": "NM_178170.3",
                            "mane_select": "NM_178170.3",
                            "hgvsc": "NM_178170.3:c.1418-1G>A",
                            "consequence": ["splice_acceptor_variant"],
                            "exon": "11/14",
                        }
                    ],
                    "provider_version": "VariantFormatter NEK8 fixture 1",
                },
            }
        if name == "EnsemblVEP_variant_recoder":
            return {
                "status": "success",
                "reviewable_features": {
                    "chr": "17",
                    "pos": 28740462,
                    "ref": "G",
                    "alt": "A",
                    "build": "GRCh38",
                    "hgvs_c": "NM_178170.3:c.1418-1G>A",
                    "hgvs_g": "NC_000017.11:g.28740462G>A",
                    "gene": "NEK8",
                    "transcript": "NM_178170.3",
                    "provider_version": "Ensembl recoder NEK8 fixture 1",
                },
            }
        if name == "EnsemblVEP_annotate_hgvs":
            return {
                "status": "success",
                "reviewable_features": {
                    "chr": "17",
                    "pos": 28740462,
                    "ref": "G",
                    "alt": "A",
                    "build": "GRCh38",
                    "gene": "NEK8",
                    "transcript": "NM_178170.3",
                    "hgvs_c": "NM_178170.3:c.1418-1G>A",
                    "most_severe_consequence": "splice_acceptor_variant",
                    "vep_transcript_candidates": [
                        {
                            "gene": "NEK8",
                            "transcript": "NM_178170.3",
                            "mane_select": "NM_178170.3",
                            "hgvsc": "NM_178170.3:c.1418-1G>A",
                            "consequence": ["splice_acceptor_variant"],
                            "impact": "HIGH",
                            "exon": "11/14",
                        }
                    ],
                    "provider_version": "Ensembl VEP NEK8 fixture 1",
                },
            }
        if name == "FAVOR_annotate_variant":
            return {
                "status": "success",
                "metadata": {"source": "FAVOR NEK8 fixture 1"},
                "data": {
                    "variant": {"variant_vcf": "17-28740462-G-A"},
                    "gene_consequence": {
                        "gene": ("AC010761.1(ENST00000268766.11:exon11:c.1418-1G>A)")
                    },
                },
            }
        if name == "OpenTargets_get_variant_transcript_consequences":
            return {
                "status": "success",
                "data": {
                    "id": "17_28740462_G_A",
                    "transcriptConsequences": [
                        {
                            "target": {"approvedSymbol": "NEK8"},
                            "transcriptId": "ENST00000268766.11",
                            "variantConsequences": [
                                {"label": "splice_acceptor_variant"}
                            ],
                            "impact": "HIGH",
                            "isEnsemblCanonical": True,
                        }
                    ],
                    "mostSevereConsequence": {"label": "splice_acceptor_variant"},
                },
            }
        if name == "SpliceAI_predict_splice":
            return {
                "status": "success",
                "data": {
                    "variant": "17-28740462-G-A",
                    "genome": "GRCh38",
                    "max_delta_score": 0.723,
                    "scores": [
                        {
                            "DS_AG": 0.092,
                            "DS_AL": 0.716,
                            "DS_DG": 0.0,
                            "DS_DL": 0.563,
                            "DP_AG": 2,
                            "DP_AL": 1,
                            "DP_DG": -4,
                            "DP_DL": 151,
                            "g_name": "NEK8",
                            "t_id": "ENST00000268766.11",
                            "t_refseq_ids": ["NM_178170.3"],
                            "t_strand": "+",
                        },
                        {
                            "DS_AG": 0.0,
                            "DS_AL": 0.723,
                            "DS_DG": 0.0,
                            "DS_DL": 0.0,
                            "DP_AG": 0,
                            "DP_AL": 1,
                            "DP_DG": 0,
                            "DP_DL": 0,
                            "g_name": "NEK8",
                            "t_id": "ENST99999999.1",
                            "t_refseq_ids": ["NM_999999.1"],
                            "t_strand": "+",
                        },
                    ],
                    "run_metadata": {
                        "model_version": "1.3.1",
                        "annotation_version": "MANE NEK8 fixture 1",
                        "score_mode": "raw",
                    },
                },
            }
        return {"status": "unavailable", "reason": "NEK8 fixture has no result"}

    def run_many_functions(
        self, calls: list[dict[str, Any]], **kwargs: Any
    ) -> list[Any]:
        return [self.run_one_function(call, **kwargs) for call in calls]


def test_nek8_favor_context_and_spliceai_global_max_do_not_block_consequence():
    result = ACMGEvidencePipeline(NEK8ProviderFixture()).run(
        {
            "variant": "NEK8;NM_178170.3:c.1418-1G>A",
            "gene": "NEK8",
            "transcript": "NM_178170.3",
            "genome_build": "GRCh38",
            "response_detail": "full",
        }
    )

    consequence = result["consequence_profile"]
    assert consequence["annotation_status"] == "resolved"
    assert consequence["resolution_confidence"] == "authoritative_corroborated"
    assert consequence["hard_identity_conflicts"] == []
    favor = next(
        row
        for row in consequence["observations"]
        if row.get("provider") == "FAVOR_annotate_variant"
    )
    assert favor["provider_role"] == "aggregation"
    assert favor["gene"] == ""
    assert favor["provider_gene_label"].startswith("AC010761.1(")
    assert favor["observation_role"] == "alternate_transcript"

    splice = next(
        fact
        for fact in result["source_facts"]
        if fact["tool_name"] == "SpliceAI_predict_splice"
    )["features"]["spliceai_profile"]
    assert splice["status"] == "resolved"
    assert splice["provider_global_max_delta_score"] == 0.723
    assert splice["provider_global_max_transcript"] == "ENST99999999.1"
    assert splice["provider_global_max_event"] == "acceptor_loss"
    assert splice["selected_transcript_max_delta_score"] == 0.716
    assert splice["max_delta_channels"] == ["DS_AL"]
    assert (
        "selected_transcript_claimed_max_delta_score_mismatch" not in splice["issues"]
    )

    pvs1_review = next(
        row for row in result["criterion_reviews"] if row["criterion"] == "PVS1"
    )
    assert (
        "selected-transcript consequence"
        not in " ".join(pvs1_review.get("missing_requirements") or []).casefold()
    )
    assert result["final_classification_allowed"] is False
