"""SMCHD1 regression for non-veto repeat-normalized HGVS representations."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from tooluniverse.acmg.collector import ACMGEvidencePipeline


class SMCHD1ProviderFixture:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    @staticmethod
    def _identity_features() -> dict[str, Any]:
        return {
            "chr": "18",
            "pos": 2790123,
            "ref": "A",
            "alt": "AAA",
            "build": "GRCh38",
            "validated_hgvs_c": "NM_015295.3:c.106_107dup",
            "hgvs_c": "NM_015295.3:c.106_107dup",
            "hgvs_g": "NC_000018.10:g.2790123_2790124dup",
            "hgvs_p": "NP_056110.2:p.Glu37GlyfsTer8",
            "gene": "SMCHD1",
            "transcript": "NM_015295.3",
            "provider_version": "SMCHD1 identity fixture 1",
        }

    @classmethod
    def _consequence_features(cls) -> dict[str, Any]:
        return {
            **cls._identity_features(),
            "most_severe_consequence": "frameshift_variant",
            "consequence_candidates": [
                {
                    "gene": "SMCHD1",
                    "transcript": "NM_015295.3",
                    "mane_select": "NM_015295.3",
                    "hgvsc": "NM_015295.3:c.106_107dup",
                    "hgvsp": "NP_056110.2:p.Glu37GlyfsTer8",
                    "consequence": ["frameshift_variant"],
                    "impact": "HIGH",
                    "exon": "2/48",
                }
            ],
        }

    def run_one_function(self, call: dict[str, Any], **_kwargs: Any) -> Any:
        self.calls.append(deepcopy(call))
        name = str(call.get("name") or "")
        if name == "VariantValidator_gene2transcripts":
            return {
                "status": "success",
                "data": [
                    {
                        "current_symbol": "SMCHD1",
                        "transcripts": [
                            {
                                "reference": "NM_015295.3",
                                "annotations": {"mane_select": True},
                            }
                        ],
                    }
                ],
            }
        if name in {
            "VariantValidator_validate_variant",
            "VariantValidator_format_genomic_to_transcripts",
            "EnsemblVEP_annotate_hgvs",
        }:
            return {
                "status": "success",
                "reviewable_features": self._consequence_features(),
            }
        if name == "EnsemblVEP_variant_recoder":
            return {
                "status": "success",
                "reviewable_features": self._identity_features(),
            }
        if name == "Mutalyzer_normalize_variant":
            return {
                "status": "success",
                "data": {
                    "normalized_description": "NM_015295.3:c.104_107A[6]",
                    "protein": {"description": "NP_056110.2:p.Glu37GlyfsTer8"},
                },
            }
        return {"status": "unavailable", "reason": "fixture has no result"}

    def run_many_functions(
        self, calls: list[dict[str, Any]], **kwargs: Any
    ) -> list[Any]:
        return [self.run_one_function(call, **kwargs) for call in calls]


def test_smchd1_normalized_repeat_representation_does_not_veto_consequence():
    result = ACMGEvidencePipeline(SMCHD1ProviderFixture()).run(
        {
            "variant": "SMCHD1;NM_015295.3:c.106_107dup",
            "gene": "SMCHD1",
            "transcript": "NM_015295.3",
            "genome_build": "GRCh38",
            "response_detail": "full",
        }
    )

    consequence = result["consequence_profile"]
    assert consequence["annotation_status"] == "resolved"
    assert consequence["hard_identity_conflicts"] == []
    assert consequence["automatic_usable"] is True
    assert consequence["verified_usable"] is True
    assert "frameshift_variant" in consequence["selected_transcript_terms"]
    assert {
        row["value"]
        for row in consequence["equivalent_or_alternate_representations"]
    } >= {
        "NM_015295.3:c.106_107dup",
        "NM_015295.3:c.104_107A[6]",
    }

    mutalyzer = next(
        fact
        for fact in result["source_facts"]
        if fact["tool_name"] == "Mutalyzer_normalize_variant"
    )
    assert mutalyzer["identity_status"] in {"partial", "unknown"}
    assert mutalyzer["identity_status"] != "conflict"

    pvs1_review = next(
        row for row in result["criterion_reviews"] if row["criterion"] == "PVS1"
    )
    assert pvs1_review["route_status"] in {
        "candidate_available",
        "insufficient_information",
        "review_pending",
    }
    assert not any(card["criterion"] == "PVS1" for card in result["evidence_cards"])
    assert result["final_classification_allowed"] is False
