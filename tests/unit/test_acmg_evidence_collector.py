"""Smoke test for ACMG evidence collector tool.

The harness runner's ``run_tool`` dependency will fail at runtime (no real MCP
backend in tests).  The collector may return an error dict; these tests accept
either the full-success structure or the error format, as long as the structure
contract is right.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_runtime_tools import ACMGEvidenceCollector
from tooluniverse.acmg.collector import (
    ACMGEvidencePipeline,
    _literature_candidate_index,
    _literature_review_state,
)
from tooluniverse.acmg.cspec import cspec_content_hash
from tooluniverse.acmg.models import SourceFact
from tooluniverse.acmg.rule_catalog import CSPEC_RULE_CATALOG


def _make_tool(tooluniverse=None):
    return ACMGEvidenceCollector(
        {
            "name": "ACMG_evidence_collector",
            "type": "ACMG_evidence_collector",
            "fields": {},
        },
        tooluniverse=tooluniverse,
    )


def _run(args: dict) -> dict:
    tool = _make_tool()
    return tool.run(args)


def _is_error(result: dict) -> bool:
    return result.get("status") == "error"


def _system_preview_criteria(result: dict) -> set[str]:
    return {
        str(row.get("criterion") or "")
        for row in result.get("evidence_cards") or []
        if row.get("system_preview_included") is True
    }


def _source_fact(tool_name: str, fact_id: str, features: dict) -> SourceFact:
    return SourceFact(
        fact_id=fact_id,
        tool_name=tool_name,
        status="success",
        query_identity={},
        result_identity={},
        identity_verified=True,
        features=features,
        raw_result_hash=f"hash-{fact_id}",
        assessment_ready=True,
    )


def test_literature_candidate_index_deduplicates_cross_provider_hits():
    facts = {
        "litvar": _source_fact(
            "LitVar_get_variant_publications",
            "litvar",
            {"articles": [{"pmid": "123", "pmcid": "PMC123"}]},
        ),
        "pubmed": _source_fact(
            "PubMed_search_articles",
            "pubmed",
            {
                "articles": [
                    {
                        "pmid": "123",
                        "title": "Variant study",
                        "abstract": "Abstract text",
                    }
                ]
            },
        ),
        "epmc": _source_fact(
            "EuropePMC_search_articles",
            "epmc",
            {
                "articles": [
                    {
                        "pmid": "123",
                        "pmcid": "PMC123",
                        "doi": "10.1/example",
                        "fulltext_snippets": ["variant"],
                    }
                ]
            },
        ),
    }

    candidates = _literature_candidate_index(facts)

    assert len(candidates) == 1
    assert candidates[0]["pmid"] == "123"
    assert candidates[0]["sources"] == [
        "EuropePMC_search_articles",
        "LitVar_get_variant_publications",
        "PubMed_search_articles",
    ]
    assert candidates[0]["source_fact_ids"] == ["epmc", "litvar", "pubmed"]
    assert candidates[0]["full_text_available"] is True


def test_literature_candidate_index_does_not_treat_inepmc_as_full_text():
    facts = {
        "epmc": _source_fact(
            "EuropePMC_search_articles",
            "epmc",
            {
                "query": 'DNAH1 AND "NM_015512.5:c.11726_11727del"',
                "articles": [
                    {
                        "pmid": "999",
                        "title": "DNAH1 NM_015512.5:c.11726_11727del",
                        "abstract": "The variant was observed in one family.",
                        "inEPMC": True,
                    }
                ],
            },
        )
    }

    candidates = _literature_candidate_index(
        facts,
        identity={
            "gene": "DNAH1",
            "validated_hgvs_c": "NM_015512.5:c.11726_11727del",
        },
        arguments={"gene": "DNAH1"},
    )

    assert candidates[0]["match_class"] == "exact_variant_match"
    assert candidates[0]["full_text_available"] is False
    assert candidates[0]["full_text_status"] == "abstract_only"


def test_literature_candidate_recognizes_historical_deletion_and_protein_aliases():
    facts = {
        "pubmed": _source_fact(
            "PubMed_search_articles",
            "pubmed",
            {
                "articles": [
                    {
                        "pmid": "27573432",
                        "title": (
                            "DNAH1 c.11726_11727delCT "
                            "(p.P3909Rfs*33) in infertility"
                        ),
                    }
                ]
            },
        )
    }
    candidates = _literature_candidate_index(
        facts,
        identity={
            "gene": "DNAH1",
            "validated_hgvs_c": "NM_015512.5:c.11726_11727del",
            "hgvs_p": "NP_056327.4:p.Pro3909ArgfsTer33",
            "coordinates": {
                "chr": "3",
                "pos": 52396982,
                "ref": "CCT",
                "alt": "C",
            },
        },
        arguments={
            "variant": "NM_015512.5:c.11726_11727del",
            "gene": "DNAH1",
        },
    )

    assert candidates[0]["match_class"] == "equivalent_variant_match"
    assert {
        "NM_015512.5:c.11726_11727delCT",
        "c.11726_11727delCT",
        "p.P3909Rfs*33",
    }.intersection(candidates[0]["matched_variant_aliases"])


def test_literature_candidate_does_not_promote_gene_only_article_to_variant_match():
    facts = {
        "pubmed": _source_fact(
            "PubMed_search_articles",
            "pubmed",
            {
                "articles": [
                    {
                        "pmid": "37457836",
                        "title": "Novel compound heterozygous variants in DNAH1",
                        "abstract": "DNAH1 was studied in one family.",
                    }
                ]
            },
        )
    }
    candidates = _literature_candidate_index(
        facts,
        identity={
            "gene": "DNAH1",
            "validated_hgvs_c": "NM_015512.5:c.11726_11727del",
        },
        arguments={
            "variant": "NM_015512.5:c.11726_11727del",
            "gene": "DNAH1",
        },
    )

    assert candidates[0]["match_class"] == "gene_disease_background"


def test_literature_identifier_conflicts_do_not_merge_records():
    facts = {
        "pubmed": _source_fact(
            "PubMed_search_articles",
            "pubmed",
            {
                "articles": [
                    {
                        "pmid": "123",
                        "doi": "10.1/left",
                        "title": "First record",
                    }
                ]
            },
        ),
        "epmc": _source_fact(
            "EuropePMC_search_articles",
            "epmc",
            {
                "articles": [
                    {
                        "pmid": "123",
                        "doi": "10.1/right",
                        "title": "Second record",
                    }
                ]
            },
        ),
    }

    candidates = _literature_candidate_index(facts)

    assert len(candidates) == 2
    assert len({row["publication_id"] for row in candidates}) == 2
    assert all(row["identifier_conflicts"] for row in candidates)


def test_literature_review_request_is_executable_and_idempotent():
    candidates = [
        {
            "publication_id": "pmid:999",
            "pmid": "999",
            "pmcid": "",
            "match_class": "exact_variant_match",
            "matched_variant_aliases": ["NM_015512.5:c.11726_11727del"],
            "full_text_status": "availability_unknown",
        }
    ]
    state = _literature_review_state(
        candidates,
        {},
        identity={
            "gene": "DNAH1",
            "validated_hgvs_c": "NM_015512.5:c.11726_11727del",
        },
        arguments={"gene": "DNAH1"},
    )

    request = state["review_requests"][0]
    assert state["workflow_status"] == "literature_review_required"
    assert request["state"] == "pending"
    assert request["tool_attempts"] == [
        {
            "tool_name": "EuropePMC_get_full_text",
            "arguments": {"pmid": "999"},
            "max_attempts": 1,
        },
        {
            "tool_name": "EuropePMC_get_fulltext",
            "arguments": {
                "source_db": "MED",
                "article_id": "999",
                "output_format": "text",
                "max_chars": 2000000,
            },
            "max_attempts": 1,
        },
    ]
    repeated = _literature_review_state(
        candidates,
        {},
        identity={
            "gene": "DNAH1",
            "validated_hgvs_c": "NM_015512.5:c.11726_11727del",
        },
        arguments={"gene": "DNAH1"},
    )
    assert repeated["review_requests"][0]["request_id"] == request["request_id"]


def test_collector_accepts_minimal_input():
    result = _run(
        {
            "variant": "NM_182931.3:c.2484_2487del",
            "gene": "KMT2E",
            "transcript": "NM_182931.3",
            "consequence": "frameshift_variant",
        }
    )
    assert isinstance(result, dict)
    if _is_error(result):
        # Acceptable — harness has no real MCP backend.
        assert "error" in result
    else:
        assert "coverage_summary" in result
        assert "evidence_cards" in result
        assert "source_assertions" in result


def test_collector_returns_conflict_report():
    result = _run(
        {
            "variant": "NM_182931.3:c.2484_2487del",
            "gene": "KMT2E",
        }
    )
    assert isinstance(result, dict)
    if _is_error(result):
        assert "error" in result
    else:
        assert "conflict_report" in result
        assert isinstance(result["conflict_report"], dict)
        assert "has_conflicts" in result["conflict_report"]


def test_collector_returns_system_preview_bayesian():
    result = _run(
        {
            "variant": "NM_182931.3:c.2484_2487del",
            "gene": "KMT2E",
        }
    )
    assert isinstance(result, dict)
    if _is_error(result):
        assert "error" in result
    else:
        assert "system_preview_bayesian" in result
        assert "posterior_probability" in result["system_preview_bayesian"]


def test_collector_does_not_claim_success_from_stubbed_collection():
    result = _run(
        {
            "variant": "NM_182931.3:c.2484_2487del",
            "gene": "KMT2E",
        }
    )

    assert isinstance(result, dict)
    if _is_error(result):
        assert "error" in result
    else:
        assert result["status"] in {"success", "degraded"}
        assert result["status"] == "degraded"
        assert result["limitations"]
        assert all(row["hit_count"] == 0 for row in result["coverage_summary"])
        assert all(
            row["query_status"] in {"unavailable", "not_applicable", "no_hit"}
            for row in result["coverage_summary"]
        )


class _FakeToolUniverse:
    def __init__(self):
        self.calls = []

    def run_one_function(self, call, **kwargs):
        self.calls.append((call, kwargs))
        name = call["name"]
        if name == "VariantValidator_gene2transcripts":
            return {
                "status": "success",
                "data": [
                    {
                        "current_symbol": "FGFR3",
                        "transcripts": [
                            {
                                "reference": "NM_000142.5",
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
                    "validated_hgvs_c": "NM_000142.5:c.1075+95C>G",
                    "hgvs_g": "NC_000004.12:g.1803931C>G",
                    "hgvs_g_grch37": "chr4:g.1803931C>G",
                    "coordinates_grch37": {
                        "chr": "4",
                        "pos": 1803931,
                        "ref": "C",
                        "alt": "G",
                    },
                    "consequence": "missense_variant",
                    "gene": "FGFR3",
                    "provider_version": "VariantValidator REST",
                },
            }
        if name == "EnsemblVEP_variant_recoder":
            return {
                "status": "success",
                "reviewable_features": {
                    "chr": "4",
                    "pos": 1803931,
                    "ref": "C",
                    "alt": "G",
                    "hgvs_c": "NM_000142.5:c.1075+95C>G",
                    "hgvs_g": "NC_000004.12:g.1803931C>G",
                    "consequence": "missense_variant",
                    "provider_version": "Ensembl Variant Recoder REST",
                },
            }
        if name == "gnomad_get_variant":
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "variant_id": "4-1803931-C-G",
                        "build": "GRCh38",
                        "AF": 0.0,
                        "AC": 0,
                        "AN": 120000,
                        "popmax": 0.0,
                        "dataset": "gnomad_r4",
                        "callset": "exome",
                    },
                },
            }
        if name == "gnomad_get_site_callability":
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "chrom": "4",
                        "position": 1803931,
                        "reference_genome": "GRCh38",
                        "dataset": "gnomad_r4",
                        "callsets": {
                            "exome": {
                                "position": 1803931,
                                "median": 30,
                                "over_20": 0.9,
                            },
                            "genome": {
                                "position": 1803931,
                                "median": 32,
                                "over_20": 0.95,
                            },
                        },
                    }
                },
            }
        if name == "MyVariant_get_metadata":
            return {
                "status": "success",
                "source": "dbnsfp",
                "version": "4.8a",
                "provider": "MyVariant.info",
            }
        if name == "MyVariant_get_pathogenicity_scores":
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "revel_score": 0.80,
                        "variant_id": "4-1803931-C-G",
                        "build": "GRCh37",
                    },
                },
            }
        if name in {"EnsemblVEP_annotate_hgvs", "EnsemblVEP_annotate_rsid"}:
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "chr": "4",
                        "pos": 1803931,
                        "ref": "C",
                        "alt": "G",
                        "build": "GRCh38",
                        "most_severe_consequence": "splice_region_variant",
                        "vep_transcript_candidates": [
                            {
                                "gene": "FGFR3",
                                "transcript": "NM_000142.5",
                                "mane_select": "NM_000142.5",
                                "hgvsc": "NM_000142.5:c.1075+95C>G",
                                "consequence": [
                                    "intron_variant",
                                    "splice_region_variant",
                                ],
                            }
                        ],
                        "provider_version": "Ensembl VEP REST",
                    },
                },
            }
        if name == "SpliceAI_predict_splice":
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "variant_id": "4-1803931-C-G",
                        "chr": "4",
                        "pos": 1803931,
                        "ref": "C",
                        "alt": "G",
                        "build": "GRCh38",
                        "scores": [
                            {
                                "gene": "FGFR3",
                                "transcript": "NM_000142.5",
                                "DS_AG": 0.25,
                                "DS_AL": 0.0,
                                "DS_DG": 0.0,
                                "DS_DL": 0.0,
                                "DP_AG": 3,
                                "DP_AL": 0,
                                "DP_DG": 0,
                                "DP_DL": 0,
                            }
                        ],
                        "run_metadata": {
                            "model_version": "1.3.1",
                            "annotation_version": "MANE fixture release",
                            "score_mode": "raw",
                        },
                    },
                },
            }
        if name == "EuropePMC_get_full_text":
            return {
                "status": "success",
                "data": {
                    "pmid": "12345678",
                    "sections": {
                        "results": (
                            "FGFR3 NM_000142.5:c.1075+95C>G was observed in 12 cases and "
                            "1000 controls with odds ratio 6.2 and lower confidence limit 1.4."
                        )
                    },
                },
            }
        if name == "ClinVar_search_variants":
            return {"status": "no_hit", "data": {"variants": []}}
        if name == "ClinVar_get_clinical_significance":
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "quarantined_conclusions": {"clinical_significance": "Pathogenic"},
                    "reviewable_features": {"review_status": "criteria provided"},
                },
            }
        return {"status": "unavailable", "reason": "fixture has no result"}


class _CSpecToolUniverse(_FakeToolUniverse):
    def run_one_function(self, call, **kwargs):
        if call["name"] == "ClinGen_search_cspec":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "gene": "FGFR3",
                "provider": "ClinGen CSpec Registry",
                "provider_version": "fixture",
                "request_url": "https://cspec.example/SequenceVariantInterpretation/id",
                "data": [
                    {
                        "specification_id": "GN078",
                        "gene": "FGFR3",
                        "vcep": "FGFR3 Variant Curation Expert Panel",
                        "version": "1.0.0",
                        "status": "Released",
                        "diseases": [
                            {
                                "name": "achondroplasia",
                                "mondo_id": "MONDO:0007037",
                                "inheritance": ["Autosomal dominant inheritance"],
                            }
                        ],
                        "criterion_modifications": [
                            {
                                "criterion": "PM2",
                                "applicability": "Applicable",
                                "default_strength": "Supporting",
                                "instructions": "Use the VCEP population rule.",
                            }
                        ],
                    }
                ],
            }
        return super().run_one_function(call, **kwargs)


class _ProteinContextToolUniverse(_FakeToolUniverse):
    def run_one_function(self, call, **kwargs):
        name = call["name"]
        if name in {"EnsemblVEP_annotate_hgvs", "EnsemblVEP_annotate_rsid"}:
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "chr": "4",
                        "pos": 1803931,
                        "ref": "C",
                        "alt": "G",
                        "build": "GRCh38",
                        "most_severe_consequence": "missense_variant",
                        "vep_transcript_candidates": [
                            {
                                "gene": "FGFR3",
                                "transcript": "NM_000142.5",
                                "mane_select": "NM_000142.5",
                                "hgvsc": "NM_000142.5:c.1075+95C>G",
                                "hgvsp": "NP_000133.1:p.Gly380Arg",
                                "consequence": ["missense_variant"],
                            }
                        ],
                        "provider_version": "Ensembl VEP REST",
                    }
                },
            }
        if name == "EBIProteins_get_variation_by_hgvs":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "hgvs_g": "NC_000004.12:g.1803931C>G",
                        "protein_candidates": [
                            {
                                "protein_accession": "P22607",
                                "gene": "FGFR3",
                                "taxid": 9606,
                                "protein_position_start": 380,
                                "protein_position_end": 380,
                                "wild_type": "G",
                                "alternative_sequence": "R",
                            }
                        ],
                        "provider_version": "EBI Proteins API",
                    }
                },
            }
        if name == "EBIProteins_get_features":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "protein_accession": "P22607",
                        "features": [
                            {
                                "type": "DOMAIN",
                                "position_start": 350,
                                "position_end": 400,
                                "description": "protein kinase domain",
                            }
                        ],
                        "provider_version": "EBI Proteins API",
                    }
                },
            }
        if name == "InterPro_get_entries_for_protein":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "protein_accession": "P22607",
                        "interpro_entries": [
                            {
                                "accession": "IPR000719",
                                "name": "Protein kinase domain",
                            }
                        ],
                        "provider_version": "InterPro API",
                    }
                },
            }
        if name == "UniProt_get_entry_by_accession":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "protein_accession": "P22607",
                        "entry_status": "reviewed",
                        "protein_name": "Fibroblast growth factor receptor 3",
                        "sequence_length": 806,
                        "provider_version": "UniProt REST API",
                    }
                },
            }
        return super().run_one_function(call, **kwargs)


class _ProteinContextCSpecToolUniverse(_ProteinContextToolUniverse):
    def run_one_function(self, call, **kwargs):
        if call["name"] == "ClinGen_search_cspec":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "gene": "FGFR3",
                "provider": "ClinGen CSpec Registry",
                "provider_version": "fixture",
                "request_url": "https://cspec.example/SequenceVariantInterpretation/id",
                "data": [
                    {
                        "specification_id": "GN078-PM1",
                        "gene": "FGFR3",
                        "vcep": "FGFR3 Variant Curation Expert Panel",
                        "version": "1.0.0",
                        "status": "Released",
                        "diseases": [
                            {
                                "name": "achondroplasia",
                                "mondo_id": "MONDO:0007037",
                                "inheritance": ["Autosomal dominant inheritance"],
                            }
                        ],
                        "criterion_modifications": [
                            {
                                "criterion": "PM1",
                                "applicability": "Applicable",
                                "default_strength": "Moderate",
                                "instructions": "Residue 380 is a critical hotspot.",
                            }
                        ],
                    }
                ],
            }
        return super().run_one_function(call, **kwargs)


class _IdentityRoutingToolUniverse:
    def __init__(self, *, resolver_result=None):
        self.calls = []
        self.resolver_result = resolver_result or [
            {
                "current_symbol": "BRCA2",
                "transcripts": [
                    {
                        "reference": "NM_000059.4",
                        "annotations": {
                            "mane_select": True,
                            "mane_plus_clinical": False,
                        },
                    }
                ],
            }
        ]

    @staticmethod
    def _identity_features(variant: str) -> dict:
        return {
            "validated_hgvs_c": variant,
            "hgvs_c": variant,
            "gene": "BRCA2",
            "transcript": "NM_000059.4",
            "provider_version": "fixture",
            "chr": "13",
            "pos": 32316461,
            "ref": "T",
            "alt": "A",
        }

    def run_one_function(self, call, **kwargs):
        self.calls.append((call, kwargs))
        name = call["name"]
        args = call.get("arguments", {})
        if name == "VariantValidator_gene2transcripts":
            return self.resolver_result
        if name == "EnsemblVEP_annotate_hgvs":
            return {
                "status": "success",
                "reviewable_features": {
                    "gene": "BRCA2",
                    "build": "GRCh38",
                    "chr": "13",
                    "pos": 32316461,
                    "ref": "T",
                    "alt": "A",
                    "transcript_candidates": [
                        {"gene": "BRCA2", "transcript": "ENST00000380152.8"}
                    ],
                },
            }
        if name == "VariantValidator_format_genomic_to_transcripts":
            return {
                "metadata": {"variantformatter_version": "fixture"},
                "submitted": {
                    "normalized": {
                        "g_hgvs": "NC_000013.11:g.32316461T>A",
                        "hgvs_t_and_p": {
                            "NM_000059.4": {
                                "t_hgvs": "NM_000059.4:c.5946delT",
                                "gene_info": {"symbol": "BRCA2"},
                                "select_status": {"mane_select": True},
                            }
                        },
                    }
                },
            }
        if name == "EnsemblVEP_variant_recoder":
            variant = str(args.get("variant_id") or "")
            if variant.lower() == "rs80359550":
                variant = "NM_000059.4:c.5946delT"
            features = self._identity_features(variant)
            features.update(
                {
                    "hgvsc_candidates": ["NM_000059.4:c.5946delT"],
                    "hgvsg_candidates": ["NC_000013.11:g.32316461T>A"],
                    "allele_candidates": [
                        {
                            "hgvsc": ["NM_000059.4:c.5946delT"],
                            "hgvsg": ["NC_000013.11:g.32316461T>A"],
                            "hgvsp": [],
                        }
                    ],
                }
            )
            if ":p." in variant:
                # Protein notation resolves through the recoder to the same
                # canonical coding HGVS plus a forward-strand genomic HGVS.
                features = self._identity_features("NM_000059.4:c.5946delT")
                features["hgvs_g"] = "NC_000013.11:g.32316461T>A"
            return {
                "status": "success",
                "reviewable_features": features,
            }
        if name == "VariantValidator_validate_variant":
            return {
                "status": "success",
                "reviewable_features": self._identity_features(
                    str(args.get("variant_description") or "")
                ),
            }
        return {"status": "unavailable", "reason": "identity fixture only"}


class _NoManeIdentityToolUniverse(_IdentityRoutingToolUniverse):
    def __init__(self):
        super().__init__(
            resolver_result=[
                {"current_symbol": "BRCA2", "transcripts": []},
            ]
        )


class _MismatchedGeneIdentityToolUniverse(_IdentityRoutingToolUniverse):
    def run_one_function(self, call, **kwargs):
        result = super().run_one_function(call, **kwargs)
        if call["name"] in {
            "VariantValidator_validate_variant",
            "EnsemblVEP_variant_recoder",
        }:
            result["reviewable_features"]["gene"] = "TP53"
        return result


class _NoIdentityToolUniverse(_FakeToolUniverse):
    def __init__(self):
        self.calls = []

    def run_one_function(self, call, **kwargs):
        self.calls.append(call["name"])
        result = super().run_one_function(call, **kwargs)
        if call["name"] in {
            "VariantValidator_validate_variant",
            "EnsemblVEP_variant_recoder",
        }:
            return {"status": "success", "reviewable_features": {}}
        return result


class _PopulationIdentityMismatchToolUniverse(_FakeToolUniverse):
    def run_one_function(self, call, **kwargs):
        result = super().run_one_function(call, **kwargs)
        if call["name"] == "gnomad_get_variant":
            result["source_lead_sandbox"]["reviewable_features"]["variant_id"] = (
                "4-1803931-A-T"
            )
        return result


class _GeneOnlyIdentityToolUniverse(_FakeToolUniverse):
    def run_one_function(self, call, **kwargs):
        if call["name"] in {
            "VariantValidator_validate_variant",
            "EnsemblVEP_variant_recoder",
        }:
            return {
                "status": "success",
                "reviewable_features": {
                    "gene": "FGFR3",
                    "build": "GRCh38",
                    "provider_version": "fixture",
                },
            }
        return super().run_one_function(call, **kwargs)


class _BuildMismatchIdentityToolUniverse(_FakeToolUniverse):
    def run_one_function(self, call, **kwargs):
        result = super().run_one_function(call, **kwargs)
        if call["name"] == "VariantValidator_validate_variant":
            result["reviewable_features"]["build"] = "GRCh37"
        return result


class _ClinVarVariationIdToolUniverse(_FakeToolUniverse):
    def run_one_function(self, call, **kwargs):
        result = super().run_one_function(call, **kwargs)
        if call["name"] in {
            "VariantValidator_validate_variant",
            "EnsemblVEP_variant_recoder",
        }:
            result["reviewable_features"]["variation_id"] = 12345
        return result


def test_collector_fails_closed_when_identity_cannot_be_normalized():
    runtime = _NoIdentityToolUniverse()
    result = _make_tool(runtime).run(
        {"variant": "NM_000142.5:c.1075+95C>G", "gene": "FGFR3"}
    )

    assert result["status"] == "error"
    assert result["error"] == "variant_identity_unverified"
    assert _system_preview_criteria(result) == set()
    assert result["system_preview_bayesian"]["prior_probability"] == 0.1
    called_names = {
        item if isinstance(item, str) else item[0]["name"] for item in runtime.calls
    }
    assert called_names == {
        "VariantValidator_validate_variant",
        "EnsemblVEP_variant_recoder",
        "EnsemblVEP_annotate_hgvs",
    }


def test_gene_coding_shorthand_uses_variantvalidator_mane_resolution():
    runtime = _IdentityRoutingToolUniverse()
    result = _make_tool(runtime).run({"variant": "c.5946delT", "gene": "BRCA2"})

    assert result["status"] == "degraded"
    assert result["variant"]["hgvs_c"] == "NM_000059.4:c.5946delT"
    assert result["variant"]["transcript"] == "NM_000059.4"
    assert (
        result["variant"]["normalization"]["transcript_source"]
        == "VariantValidator_gene2transcripts"
    )
    assert result["variant"]["normalization"]["selected_candidate"]["transcript"] == (
        "NM_000059.4"
    )
    assert isinstance(result["variant_identity"]["excluded_candidates"], list)
    names = [call[0]["name"] for call in runtime.calls]
    assert names[:3] == [
        "VariantValidator_gene2transcripts",
        "VariantValidator_validate_variant",
        "EnsemblVEP_variant_recoder",
    ]
    assert all("policy_context" not in kwargs for _call, kwargs in runtime.calls)


def test_embedded_gene_coding_shorthand_is_resolved():
    runtime = _IdentityRoutingToolUniverse()
    result = _make_tool(runtime).run({"variant": "BRCA2 c.5946delT"})

    assert result["status"] == "degraded"
    assert result["variant"]["hgvs_c"] == "NM_000059.4:c.5946delT"
    assert result["variant"]["input_variant"] == "BRCA2 c.5946delT"


def test_gene_transcript_coding_input_is_validated_directly():
    runtime = _IdentityRoutingToolUniverse()
    result = _make_tool(runtime).run({"variant": "BRCA2;NM_000059.4:c.5946delT"})

    assert result["status"] == "degraded"
    assert result["variant"]["hgvs_c"] == "NM_000059.4:c.5946delT"
    assert result["variant"]["normalization"]["input_kind"] == ("gene_transcript_hgvs")
    assert [call[0]["name"] for call in runtime.calls][:2] == [
        "VariantValidator_validate_variant",
        "EnsemblVEP_variant_recoder",
    ]


def test_gene_protein_input_uses_vep_then_mane_projection():
    runtime = _IdentityRoutingToolUniverse()
    result = _make_tool(runtime).run({"variant": "BRCA2 p.Ser1982ArgfsTer22"})

    assert result["status"] == "degraded"
    assert result["variant"]["hgvs_c"] == "NM_000059.4:c.5946delT"
    assert result["variant"]["normalization"]["input_kind"] == ("gene_protein_hgvs")
    assert result["variant"]["normalization"]["formatter_candidates"]
    assert [call[0]["name"] for call in runtime.calls][:4] == [
        "EnsemblVEP_variant_recoder",
        "VariantValidator_format_genomic_to_transcripts",
        "VariantValidator_validate_variant",
        "EnsemblVEP_variant_recoder",
    ]
    assert all("policy_context" not in kwargs for _call, kwargs in runtime.calls)


def test_genomic_input_uses_variantformatter_mane_projection():
    runtime = _IdentityRoutingToolUniverse()
    result = _make_tool(runtime).run(
        {"variant": "NC_000013.11:g.32316461T>A", "gene": "BRCA2"}
    )

    assert result["status"] == "degraded"
    assert result["variant"]["hgvs_c"] == "NM_000059.4:c.5946delT"
    assert result["variant"]["normalization"]["transcript_source"] == (
        "VariantValidator_format_genomic_to_transcripts"
    )
    names = [call[0]["name"] for call in runtime.calls]
    assert names[:3] == [
        "VariantValidator_format_genomic_to_transcripts",
        "VariantValidator_validate_variant",
        "EnsemblVEP_variant_recoder",
    ]
    assert runtime.calls[0][0]["arguments"]["variant_description"] == (
        "NC_000013.11:g.32316461T>A"
    )


def test_compact_genomic_input_is_adapted_for_variantformatter():
    runtime = _IdentityRoutingToolUniverse()
    result = _make_tool(runtime).run({"variant": "chr13:32316461T>A", "gene": "BRCA2"})

    assert result["status"] == "degraded"
    assert result["variant"]["hgvs_c"] == "NM_000059.4:c.5946delT"
    assert runtime.calls[0][0]["arguments"]["variant_description"] == (
        "13-32316461-T-A"
    )


def test_rsid_is_recoded_before_variant_validation():
    runtime = _IdentityRoutingToolUniverse()
    result = _make_tool(runtime).run({"variant": "rs80359550", "gene": "BRCA2"})

    assert result["status"] == "degraded"
    assert result["variant"]["hgvs_c"] == "NM_000059.4:c.5946delT"
    names = [call[0]["name"] for call in runtime.calls]
    # NCBI refsnp is tried first; the fixture has no result for it, so the
    # Ensembl recoder fallback resolves the rsID as before.
    assert names[:4] == [
        "NCBIVariation_rsid_lookup",
        "EnsemblVEP_variant_recoder",
        "VariantValidator_gene2transcripts",
        "VariantValidator_validate_variant",
    ]


def test_rsid_resolves_via_ncbi_refsnp_without_ensembl_recoder():
    class _NcbiRsidToolUniverse(_IdentityRoutingToolUniverse):
        def run_one_function(self, call, **kwargs):
            name = call["name"]
            if name == "NCBIVariation_rsid_lookup":
                return {
                    "status": "success",
                    "data": {
                        "refsnp_id": "80359550",
                        "mane_select_ids": ["NM_000059.4"],
                        "variant_type": "snv",
                        "grch38_placements": [
                            {
                                "seq_id": "NC_000013.11",
                                "position": 32316460,
                                "deleted_sequence": "T",
                                "inserted_sequence": "T",
                            },
                            {
                                "seq_id": "NC_000013.11",
                                "position": 32316460,
                                "deleted_sequence": "T",
                                "inserted_sequence": "A",
                            },
                        ],
                        "genes": [{"gene": "BRCA2", "gene_id": 675}],
                    },
                }
            if name == "VariantValidator_format_genomic_to_transcripts":
                return {
                    "metadata": {"variantformatter_version": "fixture"},
                    "submitted": {
                        "normalized": {
                            "g_hgvs": "NC_000013.11:g.32316461T>A",
                            "hgvs_t_and_p": {
                                "NM_000059.4": {
                                    "t_hgvs": "NM_000059.4:c.5946delT",
                                    "gene_info": {"symbol": "BRCA2"},
                                    "select_status": {"mane_select": True},
                                }
                            },
                        }
                    },
                }
            if name == "EnsemblVEP_variant_recoder":
                raise AssertionError("recoder must not be needed on the NCBI path")
            return super().run_one_function(call, **kwargs)

    runtime = _NcbiRsidToolUniverse()
    result = _make_tool(runtime).run({"variant": "rs80359550", "gene": "BRCA2"})

    assert result["status"] == "degraded"
    assert result["variant"]["hgvs_c"] == "NM_000059.4:c.5946delT"
    assert result["variant"]["normalization"]["rsid_resolver"] == (
        "NCBIVariation_rsid_lookup"
    )
    names = [call[0]["name"] for call in runtime.calls]
    assert "EnsemblVEP_variant_recoder" not in names


class _MultiAlleleRsidToolUniverse:
    """PMM2 rs104894531: alleles T and G BOTH map to NM_000303.3."""

    def __init__(self):
        self.calls = []

    def run_one_function(self, call, **kwargs):
        self.calls.append((call, kwargs))
        name = call["name"]
        if name == "EnsemblVEP_variant_recoder":
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "rsid": "rs104894531",
                        "provider_version": "Ensembl Variant Recoder REST",
                        "hgvs_c": "NM_000303.3:c.669C>T",
                        "hgvs_g": "NC_000016.10:g.8847753C>T",
                        "hgvsc_candidates": [
                            "NM_000303.3:c.669C>T",
                            "NM_000303.3:c.669C>G",
                        ],
                        "allele_candidates": [
                            {
                                "hgvsg": ["NC_000016.10:g.8847753C>T"],
                                "hgvsc": ["NM_000303.3:c.669C>T"],
                                "hgvsp": [],
                            },
                            {
                                "hgvsg": ["NC_000016.10:g.8847753C>G"],
                                "hgvsc": ["NM_000303.3:c.669C>G"],
                                "hgvsp": [],
                            },
                        ],
                    }
                },
            }
        if name == "VariantValidator_gene2transcripts":
            return [
                {
                    "current_symbol": "PMM2",
                    "transcripts": [
                        {
                            "reference": "NM_000303.3",
                            "annotations": {"mane_select": True},
                        }
                    ],
                }
            ]
        return {"status": "unavailable", "reason": "identity fixture only"}


def test_multi_allele_rsid_fails_closed_with_alternatives_and_no_downstream_calls():
    """PMM2 rs104894531 must never be silently merged into one allele."""
    runtime = _MultiAlleleRsidToolUniverse()
    result = _make_tool(runtime).run({"variant": "rs104894531", "gene": "PMM2"})

    assert result["status"] == "error"
    assert result["error"] == "variant_identity_unverified"
    assert result["variant"]["normalization_error"] == "ambiguous_rsid_allele"
    normalization = result["variant"]["normalization"]
    assert normalization["resolution_reason"] == (
        "rsid_maps_to_multiple_alleles_on_the_selected_transcript"
    )
    assert normalization["allele_alternatives"] == [
        "NM_000303.3:c.669C>T",
        "NM_000303.3:c.669C>G",
    ]
    # Zero downstream evidence calls: only identity-resolution tools may run.
    evidence_source_tools = {
        "ClinVar_search_variants",
        "ClinVar_get_clinical_significance",
        "gnomad_get_variant",
        "gnomad_get_variant_populations",
        "gnomad_get_site_callability",
        "SpliceAI_predict_splice",
        "MyVariant_get_pathogenicity_scores",
        "LitVar_search_variants",
        "EuropePMC_search_articles",
    }
    called = {call[0]["name"] for call in runtime.calls}
    assert not (called & evidence_source_tools)
    assert called <= {
        "NCBIVariation_rsid_lookup",
        "EnsemblVEP_variant_recoder",
        "VariantValidator_gene2transcripts",
        "VariantValidator_format_genomic_to_transcripts",
    }
    assert _system_preview_criteria(result) == set()
    assert result["evidence_cards"] == []


def test_missing_mane_transcript_stops_before_evidence_sources():
    runtime = _NoManeIdentityToolUniverse()
    result = _make_tool(runtime).run({"variant": "c.5946delT", "gene": "BRCA2"})

    assert result["status"] == "error"
    assert result["error"] == "variant_identity_unverified"
    assert result["evidence_cards"] == []
    assert _system_preview_criteria(result) == set()
    assert [call[0]["name"] for call in runtime.calls] == [
        "VariantValidator_gene2transcripts"
    ]


def test_provider_gene_mismatch_blocks_identity_verification():
    runtime = _MismatchedGeneIdentityToolUniverse()
    result = _make_tool(runtime).run({"variant": "c.5946delT", "gene": "BRCA2"})

    assert result["status"] == "error"
    assert result["error"] == "variant_identity_unverified"
    assert result["variant"]["normalization_error"] == "provider_identity_conflict"
    assert _system_preview_criteria(result) == set()
    assert [call[0]["name"] for call in runtime.calls] == [
        "VariantValidator_gene2transcripts",
        "VariantValidator_validate_variant",
        "EnsemblVEP_variant_recoder",
    ]


def test_conflicting_explicit_transcript_blocks_identity_verification():
    runtime = _IdentityRoutingToolUniverse()
    result = _make_tool(runtime).run(
        {
            "variant": "NM_000059.4:c.5946delT",
            "gene": "BRCA2",
            "transcript": "NM_007294.4",
        }
    )

    assert result["status"] == "error"
    assert result["error"] == "variant_identity_unverified"
    assert result["variant"]["normalization_error"] == "transcript_identity_mismatch"
    assert [call[0]["name"] for call in runtime.calls] == []


def test_gene_only_provider_output_cannot_verify_variant_identity():
    result = _make_tool(_GeneOnlyIdentityToolUniverse()).run(
        {"variant": "NM_000142.5:c.1075+95C>G", "gene": "FGFR3"}
    )

    assert result["status"] == "error"
    assert result["error"] == "variant_identity_unverified"


def test_provider_build_mismatch_blocks_identity_verification():
    result = _make_tool(_BuildMismatchIdentityToolUniverse()).run(
        {"variant": "NM_000142.5:c.1075+95C>G", "gene": "FGFR3"}
    )

    assert result["status"] == "error"
    assert result["error"] == "variant_identity_unverified"


def test_provider_result_for_another_variant_cannot_be_counted():
    result = _make_tool(_PopulationIdentityMismatchToolUniverse()).run(
        {"variant": "NM_000142.5:c.1075+95C>G", "gene": "FGFR3"}
    )

    assert "PM2" not in _system_preview_criteria(result)
    population_facts = [
        fact
        for fact in result["source_facts"]
        if fact["tool_name"] == "gnomad_get_variant"
    ]
    assert population_facts
    assert population_facts[0]["identity_verified"] is False
    assert population_facts[0]["assessment_ready"] is False


def test_collector_runtime_executes_sources_and_group_rules():
    runtime = _FakeToolUniverse()
    result = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
        }
    )

    assert result["status"] == "degraded"
    assert result["final_classification_allowed"] is False
    assert "PP3" in _system_preview_criteria(result)
    assert "PM2" in _system_preview_criteria(result)
    splice_pp3 = next(
        row
        for row in result["evidence_cards"]
        if row["criterion"] == "PP3" and row["input_source"] == "SpliceAI"
    )
    assert splice_pp3["strength"] == "PP3_Supporting"
    assert splice_pp3["rule_version"] == "2023.1"
    splice_profile = result["predictor_scores"]["spliceai"]["profile"]
    assert splice_profile["delta_scores"] == {
        "DS_AG": 0.25,
        "DS_AL": 0.0,
        "DS_DG": 0.0,
        "DS_DL": 0.0,
    }
    assert splice_profile["max_delta_events"] == ["acceptor_gain"]
    assert (
        splice_pp3["input_values"]["spliceai_profile"]["delta_scores"]
        == splice_profile["delta_scores"]
    )
    pm2 = next(row for row in result["evidence_cards"] if row["criterion"] == "PM2")
    assert pm2["assessment_status"] == "met"
    assert len(pm2["source_fact_ids"]) == 2
    assert all(
        row["source_fact_ids"]
        for row in result["evidence_cards"]
        if row["system_preview_included"] is True
    )
    assert all(
        row["criterion"] != "PP5" or row["system_preview_included"] is False
        for row in result["evidence_cards"]
    )
    assert any(
        row["source_category"] == "source_assertion"
        for row in result["coverage_summary"]
    )
    assert all("policy_context" not in kwargs for _call, kwargs in runtime.calls)
    splice_call = next(
        call
        for call, _kwargs in runtime.calls
        if call["name"] == "SpliceAI_predict_splice"
    )
    assert splice_call["arguments"]["distance"] == 500
    assert splice_call["arguments"]["mask"] is False
    assert set(result) == {
        "status",
        "execution_status",
        "coverage_status",
        "variant",
        "variant_identity",
        "clinical_context",
        "response_detail",
        "consequence_profile",
        "rule_context",
        "runtime_manifest",
        "coverage_summary",
        "source_facts",
        "source_assertions",
        "predictor_scores",
        "criterion_reviews",
        "evidence_cards",
        "compatibility_report",
        "conflict_report",
        "literature_candidates",
        "literature_review",
        "recoverable_gaps",
        "workflow_status",
        "next_actions",
        "system_preview_bayesian",
        "user_selected_bayesian",
        "decision_report",
        "limitations",
        "final_classification_allowed",
    }
    assert result["user_selected_bayesian"]["status"] == "not_requested"


def test_collector_promotes_bp7_only_after_strict_walker_bp4():
    class _BP4Runtime(_FakeToolUniverse):
        def run_one_function(self, call, **kwargs):
            result = super().run_one_function(call, **kwargs)
            if call["name"] == "SpliceAI_predict_splice":
                row = result["source_lead_sandbox"]["reviewable_features"]["scores"][0]
                row["DS_AG"] = 0.10
            return result

    result = _make_tool(_BP4Runtime()).run(
        {"variant": "NM_000142.5:c.1075+95C>G", "gene": "FGFR3"}
    )

    assert {"BP4", "BP7"} <= _system_preview_criteria(result)
    strengths = {
        row["criterion"]: row["strength"]
        for row in result["evidence_cards"]
        if row["criterion"] in {"BP4", "BP7"}
    }
    assert strengths == {"BP4": "BP4_Supporting", "BP7": "BP7_Supporting"}


def test_collector_exposes_pm1_domain_context_without_counting_it():
    runtime = _ProteinContextToolUniverse()
    result = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
        }
    )

    names = [call[0]["name"] for call in runtime.calls]
    assert "EBIProteins_get_variation_by_hgvs" in names
    assert "EBIProteins_get_features" in names
    assert "InterPro_get_entries_for_protein" in names
    pm1 = next(row for row in result["evidence_cards"] if row["criterion"] == "PM1")
    assert pm1["assessment_status"] == "indeterminate"
    assert pm1["system_preview_included"] is False
    assert pm1["observed_facts"]["protein_context"]["overlapping_features"]
    protein_coverage = next(
        row
        for row in result["coverage_summary"]
        if row["source_category"] == "protein_context"
    )
    assert protein_coverage["query_completed"] is True
    assert protein_coverage["assessment_ready"] is True


def test_pm1_protein_mapping_requires_gene_and_selected_transcript_protein_change():
    features = {
        "protein_candidates": [
            {
                "protein_accession": "P22607",
                "gene": "FGFR3",
                "taxid": 9606,
                "protein_position_start": 380,
                "protein_position_end": 380,
                "wild_type": "G",
                "alternative_sequence": "R",
            }
        ]
    }

    missing_protein = ACMGEvidencePipeline._select_protein_mapping(
        features,
        gene="FGFR3",
        profile={"hgvs_p": ""},
        protein_accession_hint="",
    )
    missing_gene = ACMGEvidencePipeline._select_protein_mapping(
        features,
        gene="",
        profile={"hgvs_p": "NP_000133.1:p.Gly380Arg"},
        protein_accession_hint="",
    )

    assert missing_protein["status"] == "unavailable"
    assert missing_gene["status"] == "unavailable"

    inframe = ACMGEvidencePipeline._select_protein_mapping(
        {
            "protein_candidates": [
                {
                    **features["protein_candidates"][0],
                    "alternative_sequence": "",
                }
            ]
        },
        gene="FGFR3",
        profile={
            "hgvs_p": "NP_000133.1:p.Gly380del",
            "protein_effect": "inframe",
            "protein_position": 380,
        },
        protein_accession_hint="",
    )
    assert inframe["status"] == "resolved"


def test_exact_reviewed_cspec_pm1_contract_can_enter_candidate_bayesian(monkeypatch):
    online_candidate = {
        "specification_id": "GN078-PM1",
        "gene": "FGFR3",
        "vcep": "FGFR3 Variant Curation Expert Panel",
        "version": "1.0.0",
        "status": "Released",
        "diseases": [
            {
                "name": "achondroplasia",
                "mondo_id": "MONDO:0007037",
                "inheritance": ["Autosomal dominant inheritance"],
            }
        ],
        "criterion_modifications": [
            {
                "criterion": "PM1",
                "applicability": "Applicable",
                "default_strength": "Moderate",
                "instructions": "Residue 380 is a critical hotspot.",
            }
        ],
    }
    monkeypatch.setitem(
        CSPEC_RULE_CATALOG,
        ("GN078-PM1", "1.0.0"),
        {
            "specification_id": "GN078-PM1",
            "rule_id": "clingen-cspec-gn078-pm1",
            "version": "1.0.0",
            "gene": "FGFR3",
            "mondo": "MONDO:0007037",
            "inheritance": "AD",
            "status": "approved_active",
            "primary_reference": "https://cspec.example/GN078-PM1",
            "content_hash": cspec_content_hash(online_candidate),
            "criteria": {
                "PM1": {
                    "protein_accession": "P22607",
                    "transcript": "NM_000142.5",
                    "residues": [380],
                    "variant_types": ["missense"],
                    "critical_region_established": True,
                    "benign_variation_depleted": True,
                    "strength": "PM1_Moderate",
                    "mutually_exclusive_with": ["PM5"],
                }
            },
            "countable_strengths": ["PM1_Moderate"],
            "bayesian_odds": {"PM1_Moderate": 4.3},
        },
    )
    result = _make_tool(_ProteinContextCSpecToolUniverse()).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "disease": "MONDO:0007037",
            "inheritance": "AD",
            "response_detail": "full",
        }
    )

    pm1 = next(row for row in result["evidence_cards"] if row["criterion"] == "PM1")
    assert result["rule_context"]["cspec_status"] == "dynamic_structured_applied"
    assert result["rule_context"]["compiled_contract_status"] == "hash_verified"
    assert pm1["assessment_status"] == "met"
    assert pm1["suggested_strength"] == "PM1_Moderate"
    assert pm1["system_preview_included"] is True
    assert "PM1" in _system_preview_criteria(result)


def test_cspec_is_discovered_online_and_matched_to_context():
    result = _make_tool(_CSpecToolUniverse()).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "disease": "MONDO:0007037",
            "inheritance": "AD",
            "response_detail": "full",
        }
    )

    context = result["rule_context"]
    assert context["vcep_discovered"] is True
    assert context["cspec_status"] == "dynamic_structured_applied"
    assert context["fallback_policy"] == "applicable_clingen_cspec"
    assert context["applicable_specification"]["specification_id"] == "GN078"
    assert context["source_fact_ids"]
    pm2 = next(row for row in result["evidence_cards"] if row["criterion"] == "PM2")
    assert pm2["observed_facts"]["applicable_cspec"]["specification_id"] == "GN078"
    assert "Online ClinGen CSpec" in pm2["rule_basis"]
    assert pm2["rule_verification"] == "dynamic_cspec_structured"


def _consequence_identity(*, multiallelic: bool = False) -> dict:
    normalization = {
        "selected_genomic_allele": "NC_000004.12:g.1803931C>G",
    }
    if multiallelic:
        normalization["allele_alternatives"] = [
            "NM_000142.5:c.1075+95C>G",
            "NM_000142.5:c.1075+95C>T",
        ]
    return {
        "identity_verified": True,
        "identity_conflict": False,
        "validated_hgvs_c": "NM_000142.5:c.1075+95C>G",
        "hgvs_c": "NM_000142.5:c.1075+95C>G",
        "hgvs_g": "NC_000004.12:g.1803931C>G",
        "rsid": "rs123",
        "gene": "FGFR3",
        "transcript": "NM_000142.5",
        "build": "GRCh38",
        "coordinates": {"chr": "4", "pos": 1803931, "ref": "C", "alt": "G"},
        "normalization": normalization,
    }


class _ConsequenceFallbackToolUniverse:
    def __init__(self, outcomes: list[str]):
        self.outcomes = list(outcomes)
        self.calls = []
        self.vep_call_count = 0

    def run_one_function(self, call, **kwargs):
        self.calls.append(call)
        if call["name"] not in {
            "EnsemblVEP_annotate_hgvs",
            "EnsemblVEP_annotate_rsid",
        }:
            return {"status": "unavailable", "reason": "fixture provider unavailable"}
        outcome = (
            self.outcomes[self.vep_call_count]
            if self.vep_call_count < len(self.outcomes)
            else "empty"
        )
        self.vep_call_count += 1
        features = {
            "chr": "4",
            "pos": 1803931,
            "ref": "C",
            "alt": "G",
            "build": "GRCh38",
            "provider_version": "Ensembl VEP REST",
            "vep_transcript_candidates": [],
        }
        if outcome == "resolved":
            features["vep_transcript_candidates"] = [
                {
                    "gene": "FGFR3",
                    "transcript": "NM_000142.5",
                    "mane_select": "NM_000142.5",
                    "hgvsc": "NM_000142.5:c.1075+95C>G",
                    "consequence": ["intron_variant", "splice_region_variant"],
                }
            ]
        elif outcome == "conflict":
            features.update({"pos": 1803932, "alt": "T"})
        return {
            "status": "success",
            "source_lead_sandbox": {"reviewable_features": features},
        }


def test_consequence_collects_all_sources_but_prefers_selected_transcript_hgvs():
    runtime = _ConsequenceFallbackToolUniverse(["resolved"])
    pipeline = ACMGEvidencePipeline(runtime)
    calls, diagnostics = pipeline._consequence_calls(_consequence_identity())

    assert len(calls) > 3
    assert calls[0].arguments == {"hgvs_notation": "NM_000142.5:c.1075+95C>G"}
    assert diagnostics["annotation_status"] == "resolved"
    assert any(call.tool_name == "FAVOR_annotate_variant" for call in calls)
    assert any(
        call.tool_name == "OpenTargets_get_variant_transcript_consequences"
        for call in calls
    )
    assert diagnostics["attempted_representations"][0]["representation"] == (
        "selected_transcript_hgvs"
    )


def test_consequence_empty_transcript_result_falls_back_to_genomic_hgvs():
    runtime = _ConsequenceFallbackToolUniverse(["empty", "resolved"])
    pipeline = ACMGEvidencePipeline(runtime)
    calls, diagnostics = pipeline._consequence_calls(_consequence_identity())

    assert [call.arguments for call in calls[:2]] == [
        {"hgvs_notation": "NM_000142.5:c.1075+95C>G"},
        {"hgvs_notation": "NC_000004.12:g.1803931C>G"},
    ]
    assert diagnostics["annotation_status"] == "resolved"
    assert diagnostics["attempted_representations"][0]["outcome"] == (
        "queried"
    )


def test_consequence_all_representations_empty_reports_exact_limitation():
    runtime = _ConsequenceFallbackToolUniverse(["empty", "empty", "empty"])
    pipeline = ACMGEvidencePipeline(runtime)
    identity = _consequence_identity()
    calls, diagnostics = pipeline._consequence_calls(identity)
    facts = pipeline._source_facts(calls, identity)
    profile = pipeline._profile_from_facts(identity, facts, diagnostics)

    representations = {
        row["representation"] for row in profile["attempted_representations"]
    }
    assert {
        "selected_transcript_hgvs",
        "genomic_hgvs",
        "rsid_single_allele",
        "vep_region",
        "variantvalidator_all_transcripts",
        "favor_grch38",
        "opentargets_transcripts",
    } <= representations
    assert profile["status"] == "unavailable"
    assert profile["annotation_status"] == "unavailable"
    assert profile["annotation_reason"] == (
        "no_identity_bound_selected_transcript_consequence"
    )


def test_consequence_identity_conflict_fails_closed_after_all_sources_run():
    runtime = _ConsequenceFallbackToolUniverse(["conflict"])
    pipeline = ACMGEvidencePipeline(runtime)
    calls, diagnostics = pipeline._consequence_calls(_consequence_identity())

    assert len(calls) > 3
    assert diagnostics["annotation_status"] == "identity_conflict"
    assert diagnostics["annotation_reason"] == (
        "consequence_provider_identity_conflict"
    )


def test_consequence_rsid_fallback_requires_verified_single_allele():
    single_runtime = _ConsequenceFallbackToolUniverse(["empty", "empty", "resolved"])
    single_pipeline = ACMGEvidencePipeline(single_runtime)
    single_calls, single_diagnostics = single_pipeline._consequence_calls(
        _consequence_identity()
    )

    assert any(call.tool_name == "EnsemblVEP_annotate_rsid" for call in single_calls)
    assert single_diagnostics["annotation_status"] == "resolved"

    runtime = _ConsequenceFallbackToolUniverse(["empty", "empty"])
    pipeline = ACMGEvidencePipeline(runtime)
    calls, diagnostics = pipeline._consequence_calls(
        _consequence_identity(multiallelic=True)
    )

    assert all(call.tool_name != "EnsemblVEP_annotate_rsid" for call in calls)
    assert all(call.tool_name != "GenomeNexus_annotate_dbsnp" for call in calls)
    assert all(call.tool_name != "gProfiler_annotate_snps" for call in calls)
    assert diagnostics["annotation_reason"] == (
        "no_identity_bound_selected_transcript_consequence"
    )


class _DNAH1ConsequenceRecoveryToolUniverse:
    """Frozen DNAH1 identity where VEP annotation is unavailable."""

    def __init__(self):
        self.calls = []

    def run_one_function(self, call, **kwargs):
        self.calls.append((call, kwargs))
        name = call["name"]
        if name == "VariantValidator_validate_variant":
            return {
                "status": "success",
                "reviewable_features": {
                    "validated_hgvs_c": "NM_015512.5:c.11726_11727del",
                    "hgvs_c": "NM_015512.5:c.11726_11727del",
                    "hgvs_g": "NC_000003.12:g.52396983_52396984del",
                    "hgvs_p": "NP_056327.4:p.Pro3909ArgfsTer33",
                    "gene": "DNAH1",
                    "transcript": "NM_015512.5",
                    "build": "GRCh38",
                    "chr": "3",
                    "pos": 52396982,
                    "ref": "CCT",
                    "alt": "C",
                    "provider_version": "VariantValidator fixture",
                },
            }
        if name == "EnsemblVEP_variant_recoder":
            return {
                "status": "success",
                "reviewable_features": {
                    "validated_hgvs_c": "NM_015512.5:c.11726_11727del",
                    "hgvs_c": "NM_015512.5:c.11726_11727del",
                    "hgvs_g": "NC_000003.12:g.52396983_52396984del",
                    "hgvs_p": "NP_056327.4:p.Pro3909ArgfsTer33",
                    "hgvsc_candidates": ["NM_015512.5:c.11726_11727del"],
                    "hgvsg_candidates": [
                        "NC_000003.12:g.52396983_52396984del"
                    ],
                    "allele_candidates": [
                        {
                            "hgvsc": ["NM_015512.5:c.11726_11727del"],
                            "hgvsg": [
                                "NC_000003.12:g.52396983_52396984del"
                            ],
                            "hgvsp": [
                                "NP_056327.4:p.Pro3909ArgfsTer33"
                            ],
                        }
                    ],
                    "gene": "DNAH1",
                    "transcript": "NM_015512.5",
                    "build": "GRCh38",
                    "chr": "3",
                    "pos": 52396982,
                    "ref": "CCT",
                    "alt": "C",
                    "provider_version": "Ensembl recoder fixture",
                },
            }
        if name in {
            "EnsemblVEP_annotate_hgvs",
            "EnsemblVEP_annotate_rsid",
            "ensembl_vep_region",
        }:
            return {"status": "unavailable", "reason": "VEP fixture outage"}
        if name == "VariantValidator_format_genomic_to_transcripts":
            return {
                "metadata": {"variantformatter_version": "fixture-2.2"},
                "submitted": {
                    "normalized": {
                        "g_hgvs": "NC_000003.12:g.52396983_52396984del",
                        "hgvs_t_and_p": {
                            "NM_015512.5": {
                                "t_hgvs": "NM_015512.5:c.11726_11727del",
                                "p_hgvs": (
                                    "NP_056327.4:p.Pro3909ArgfsTer33"
                                ),
                                "gene_info": {"symbol": "DNAH1"},
                                "select_status": {"mane_select": True},
                            }
                        },
                    }
                },
            }
        return {"status": "unavailable", "reason": "fixture provider unavailable"}


def test_dnah1_vep_outage_recovers_consequence_without_inventing_nmd():
    runtime = _DNAH1ConsequenceRecoveryToolUniverse()
    result = _make_tool(runtime).run(
        {
            "variant": "NM_015512.5:c.11726_11727del",
            "gene": "DNAH1",
            "transcript": "NM_015512.5",
            "response_detail": "full",
        }
    )

    assert result["status"] == "degraded"
    assert result["variant_identity"]["hgvs_c"] == (
        "NM_015512.5:c.11726_11727del"
    )
    assert result["consequence_profile"]["annotation_status"] == "resolved"
    assert result["consequence_profile"]["selected_provider"] == (
        "VariantValidator_format_genomic_to_transcripts"
    )
    assert result["consequence_profile"]["selected_transcript_terms"] == [
        "frameshift_variant"
    ]
    assert any(
        row["code"] == "consequence_primary_provider_failed_but_alternatives_available"
        and row["status"] == "recovered"
        for row in result["recoverable_gaps"]
    )
    assert {
        row["code"]
        for row in result["recoverable_gaps"]
        if row["status"] == "unresolved"
    } >= {"exon_structure_missing", "nmd_facts_missing"}
    pvs1 = next(
        row for row in result["evidence_cards"] if row["criterion"] == "PVS1"
    )
    assert pvs1["assessment_status"] == "not_assessed"
    serialized = json.dumps(result, ensure_ascii=False)
    assert "73/82" not in serialized
    assert "PTC in exon 73" not in serialized


def test_summary_mode_returns_compact_indexes_without_bulky_payloads():
    runtime = _FakeToolUniverse()
    result = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
        }
    )

    assert result["response_detail"] == "summary"
    assert _system_preview_criteria(result)
    assert all(
        set(fact)
        <= {
            "fact_id",
            "tool_name",
            "status",
            "identity_verified",
            "assessment_ready",
            "provider_version",
            "request_arguments",
            "provenance",
            "limitation",
            "observed_values",
            "excerpt",
            "locator",
        }
        for fact in result["source_facts"]
    )
    for card in result["evidence_cards"]:
        assert "input_values" not in card
        assert card["criterion"]
        assert card["route"]
        assert "system_preview_included" in card
        assert "decision_basis" in card
    splice_index = next(
        row for row in result["evidence_cards"] if row.get("source") == "SpliceAI"
    )
    assert splice_index["route"] == "spliceai_splice"
    revel_index = next(
        (row for row in result["evidence_cards"] if row.get("source") == "REVEL"),
        None,
    )
    if revel_index is not None:
        assert revel_index["route"] == "missense_revel"
    assert (
        len(
            json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        <= 50_000
    )
    assert set(result["compatibility_report"]) == {
        "compatible_card_ids",
        "excluded_evidence",
    }
    assert all(
        set(row) <= {"card_id", "criterion", "reason"}
        for row in result["compatibility_report"]["excluded_evidence"]
    )
    assert "compatibility_exclusions" not in result["system_preview_bayesian"]
    assert "included_card_ids" in result["system_preview_bayesian"]
    assert "excluded_card_ids" in result["system_preview_bayesian"]
    assert all(
        "observed_facts" not in review and "required_facts" not in review
        for review in result["criterion_reviews"]
    )


def test_full_mode_preserves_complete_payloads():
    runtime = _FakeToolUniverse()
    result = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
        }
    )

    assert result["response_detail"] == "full"
    assert any("features" in fact for fact in result["source_facts"])
    pm2 = next(row for row in result["evidence_cards"] if row["criterion"] == "PM2")
    assert pm2["input_values"]
    assert result["compatibility_report"]["compatible_evidence"]
    assert "compatibility_exclusions" in result["system_preview_bayesian"]
    assert any("observed_facts" in review for review in result["criterion_reviews"])


def test_clinical_context_is_review_only_and_never_becomes_evidence():
    runtime = _FakeToolUniverse()
    result = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "clinical_context": {
                "zygosity": "heterozygous",
                "parental_origin": "paternal",
                "phenotype": "fetal ventriculomegaly",
                "unexpected_field": "dropped",
            },
        }
    )

    context = result["clinical_context"]
    assert context["review_only"] is True
    assert context["not_evidence"] is True
    assert context["status"] == "accepted"
    assert context["values"] == {
        "zygosity": "heterozygous",
        "parental_origin": "paternal",
        "phenotype": "fetal ventriculomegaly",
    }
    assert context["ignored_fields"] == ["unexpected_field"]
    # Review context must never create evidence criteria.
    for card in result["evidence_cards"]:
        assert card["criterion"] not in {"PS2", "PP4"} or not card.get(
            "system_preview_included"
        )


def test_clinical_context_absent_returns_null():
    runtime = _FakeToolUniverse()
    result = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
        }
    )

    assert result["clinical_context"] is None


def test_clinical_context_survives_identity_failure():
    runtime = _MultiAlleleRsidToolUniverse()
    result = _make_tool(runtime).run(
        {
            "variant": "rs104894531",
            "gene": "PMM2",
            "clinical_context": {"zygosity": "heterozygous"},
        }
    )

    assert result["status"] == "error"
    assert result["clinical_context"]["values"]["zygosity"] == "heterozygous"
    assert result["clinical_context"]["review_only"] is True


def test_discovered_cspec_without_local_contract_is_executable_online():
    result = _make_tool(_CSpecToolUniverse()).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "disease": "MONDO:0007037",
            "inheritance": "AD",
        }
    )

    context = result["rule_context"]
    assert context["cspec_status"] == "dynamic_structured_applied"
    assert context["applicable_specification"]["specification_id"] == "GN078"
    assert context["fallback_policy"] == "applicable_clingen_cspec"
    assert context["compiled_contract_status"] == "not_available"


def test_cspec_llm_proposal_is_reverified_against_online_document():
    base_arguments = {
        "variant": "NM_000142.5:c.1075+95C>G",
        "gene": "FGFR3",
        "disease": "MONDO:0007037",
        "inheritance": "AD",
        "response_detail": "full",
    }
    initial = _make_tool(_CSpecToolUniverse()).run(base_arguments)
    proposal = {
        "specification_id": "GN078",
        "version": "1.0.0",
        "content_hash": initial["rule_context"]["cspec_content_hash"],
        "criterion": "PM2",
        "locator": "PM2",
        "excerpt": "Use the VCEP population rule.",
        "structured_interpretation": {
            "strength": "PM2_Supporting",
            "maximum_credible_af": 0.0001,
        },
        "suggested_strength": "PM2_Supporting",
        "interpretation": "The VCEP retains PM2 at supporting strength.",
        "confidence": 0.9,
        "extractor": {"name": "fixture-llm", "version": "1"},
    }
    reviewed = _make_tool(_CSpecToolUniverse()).run(
        {**base_arguments, "cspec_proposals": [proposal]}
    )

    assert reviewed["rule_context"]["cspec_proposal_report"][0]["status"] == (
        "verified"
    )
    pm2 = next(row for row in reviewed["evidence_cards"] if row["criterion"] == "PM2")
    assert pm2["proposal_origin"] == "llm_cspec"
    assert pm2["rule_mapping_status"] == "llm_review_required"
    assert pm2["llm_suggestion"]["cspec"]["extractor"]["version"] == "1"
    assert (
        reviewed["rule_context"]["executable_contract"]["criteria"]["PM2"][
            "maximum_credible_af"
        ]
        == 0.0001
    )

    stale = _make_tool(_CSpecToolUniverse()).run(
        {
            **base_arguments,
            "cspec_proposals": [{**proposal, "content_hash": "stale"}],
        }
    )
    assert stale["rule_context"]["cspec_proposal_report"][0]["status"] == "rejected"


def test_cspec_gene_hit_without_disease_context_falls_back_to_general_svi():
    result = _make_tool(_CSpecToolUniverse()).run(
        {"variant": "NM_000142.5:c.1075+95C>G", "gene": "FGFR3"}
    )

    context = result["rule_context"]
    assert context["vcep_discovered"] is True
    assert context["applicable_specification"] is None
    assert context["fallback_policy"] == "general_clingen_svi"


def test_collector_validates_document_backed_literature_fact():
    runtime = _FakeToolUniverse()
    runtime.acmg_review_assertion_verifier = (
        lambda assertion: assertion["fact_id"] == "pmid-123-results"
    )
    result = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
            "literature_proposals": [
                {
                    "fact_id": "pmid-123-results",
                    "fact_type": "case_control",
                    "pmid": "12345678",
                    "locator": "results",
                    "excerpt": "FGFR3 NM_000142.5:c.1075+95C>G was observed in 12 cases",
                    "variant_identity": "NM_000142.5:c.1075+95C>G",
                    "gene": "FGFR3",
                    "extractor": {"name": "fixture", "version": "1"},
                    "verification_status": "curator_verified",
                    "verified_by": "curator-1",
                    "values": {
                        "variant_identity": "NM_000142.5:c.1075+95C>G",
                        "gene": "FGFR3",
                        "case_count": 12,
                        "control_count": 1000,
                        "odds_ratio": 6.2,
                        "ci_lower": 1.4,
                    },
                    "field_excerpts": {
                        "case_count": "12 cases",
                        "control_count": "1000 controls",
                        "odds_ratio": "odds ratio 6.2",
                        "ci_lower": "lower confidence limit 1.4",
                    },
                }
            ],
        }
    )

    ps4 = [row for row in result["evidence_cards"] if row["criterion"] == "PS4"]
    assert len(ps4) == 1
    assert ps4[0]["system_preview_included"] is True
    assert ps4[0]["assessment_status"] == "met"
    assert ps4[0]["proposal_status"] == "requires_user_review"
    assert any(fact["assessment_ready"] for fact in result["source_facts"])


def _case_control_literature_proposal(**overrides):
    proposal = {
        "fact_id": "llm-case-control",
        "fact_type": "case_control",
        "pmid": "12345678",
        "locator": "results",
        "excerpt": "FGFR3 NM_000142.5:c.1075+95C>G was observed in 12 cases",
        "variant_identity": "NM_000142.5:c.1075+95C>G",
        "gene": "FGFR3",
        "values": {
            "variant_identity": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "case_count": 12,
            "control_count": 1000,
            "odds_ratio": 6.2,
            "ci_lower": 1.4,
        },
        "field_excerpts": {
            "case_count": "12 cases",
            "control_count": "1000 controls",
            "odds_ratio": "odds ratio 6.2",
            "ci_lower": "lower confidence limit 1.4",
        },
        "criterion": "PS4",
        "suggested_strength": "PS4_Supporting",
        "interpretation": "The case-control result may support PS4.",
        "confidence": 0.82,
        "questions": ["Confirm cohort independence."],
        "extractor": {"name": "fixture-llm", "version": "1.0"},
    }
    proposal.update(overrides)
    return proposal


def test_verified_llm_literature_proposal_enters_system_preview_for_review():
    result = _make_tool(_FakeToolUniverse()).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
            "literature_proposals": [_case_control_literature_proposal()],
        }
    )

    proposals = [row for row in result["evidence_cards"] if row["criterion"] == "PS4"]
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["proposal_origin"] == "llm_literature"
    assert proposal["proposal_status"] == "requires_user_review"
    assert proposal["rule_mapping_status"] == "llm_review_required"
    assert proposal["llm_suggestion"]["items"][0]["criterion"] == "PS4"
    assert proposal["system_preview_included"] is True
    assert proposal["card_id"] in result["system_preview_bayesian"]["included_card_ids"]
    fact = next(
        row
        for row in result["source_facts"]
        if row["fact_id"] in proposal["source_fact_ids"]
    )
    assert fact["features"]["anchor_status"] == "verified"
    assert fact["features"]["semantic_status"] == "verified"


def test_contradicted_llm_literature_proposal_remains_visible_but_excluded():
    proposal = _case_control_literature_proposal()
    proposal["values"] = {**proposal["values"], "odds_ratio": 9.9}
    result = _make_tool(_FakeToolUniverse()).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
            "literature_proposals": [proposal],
        }
    )

    card = next(row for row in result["evidence_cards"] if row["criterion"] == "PS4")
    assert card["proposal_status"] == "insufficient_information"
    assert card["system_preview_included"] is False
    fact = next(
        row
        for row in result["source_facts"]
        if row["fact_id"] in card["source_fact_ids"]
    )
    assert fact["features"]["anchor_status"] == "verified"
    assert fact["features"]["semantic_status"] == "contradicted"


def test_stale_document_hash_excludes_literature_proposal():
    proposal = _case_control_literature_proposal(
        document_hash="stale-document-hash",
        review_request_id="acmg-literature-review:v1:fixture",
        reading_manifest={
            "status": "complete",
            "sections_read": ["methods", "results"],
            "tables_read": ["table 1"],
            "figures_read": [],
            "supplements_read": [],
            "variant_match_locations": ["results"],
            "limitations": [],
        },
    )
    result = _make_tool(_FakeToolUniverse()).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
            "literature_proposals": [proposal],
        }
    )

    card = next(row for row in result["evidence_cards"] if row["criterion"] == "PS4")
    fact = next(
        row
        for row in result["source_facts"]
        if row["fact_id"] in card["source_fact_ids"]
    )
    assert card["system_preview_included"] is False
    assert fact["assessment_ready"] is False
    assert fact["features"]["anchor_status"] == "mismatch"
    assert any(
        "document_hash" in message
        for message in fact["features"]["validation_errors"]
    )


def test_abstract_only_literature_proposal_stays_source_lead():
    proposal = _case_control_literature_proposal(
        reading_manifest={
            "status": "abstract_only",
            "sections_read": ["abstract"],
            "tables_read": [],
            "figures_read": [],
            "supplements_read": [],
            "variant_match_locations": ["abstract"],
            "limitations": ["full text unavailable"],
        }
    )
    result = _make_tool(_FakeToolUniverse()).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
            "literature_proposals": [proposal],
        }
    )

    card = next(row for row in result["evidence_cards"] if row["criterion"] == "PS4")
    fact = next(
        row
        for row in result["source_facts"]
        if row["fact_id"] in card["source_fact_ids"]
    )
    assert card["system_preview_included"] is False
    assert fact["assessment_ready"] is False
    assert fact["features"]["reading_manifest"]["status"] == "abstract_only"


def test_user_decision_recalculates_only_accepted_stable_cards():
    runtime = _FakeToolUniverse()
    initial = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
        }
    )
    pm2 = next(row for row in initial["evidence_cards"] if row["criterion"] == "PM2")
    reviewed = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
            "evidence_decisions": [
                {
                    "card_id": pm2["card_id"],
                    "decision": "accept",
                    "strength_override": "PM2_Moderate",
                    "reason": "Reviewed disease-specific frequency context.",
                    "reviewer": "fixture-reviewer",
                }
            ],
        }
    )

    selected = next(
        row for row in reviewed["evidence_cards"] if row["card_id"] == pm2["card_id"]
    )
    assert selected["user_decision"] == "modified"
    assert selected["effective_strength"] == "PM2_Moderate"
    assert selected["user_selected_included"] is True
    assert reviewed["user_selected_bayesian"]["included_card_ids"] == [pm2["card_id"]]
    assert (
        reviewed["user_selected_bayesian"]["evidence_odds"][0]["odds_source"]
        == "tavtigian_generic_strength"
    )


def test_user_decision_reports_rejections_unmatched_and_duplicate_inputs():
    runtime = _FakeToolUniverse()
    initial = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
        }
    )
    pm2 = next(row for row in initial["evidence_cards"] if row["criterion"] == "PM2")
    reviewed = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
            "evidence_decisions": [
                {"card_id": pm2["card_id"], "decision": "reject"},
                {"card_id": "acmg-card:v1:stale", "decision": "accept"},
            ],
        }
    )
    assert reviewed["user_selected_bayesian"]["included_card_ids"] == []
    assert reviewed["decision_report"]["unmatched_decisions"][0]["card_id"].endswith(
        "stale"
    )

    duplicate = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "evidence_decisions": [
                {"card_id": pm2["card_id"], "decision": "accept"},
                {"card_id": pm2["card_id"], "decision": "reject"},
            ],
        }
    )
    assert duplicate["status"] == "error"
    assert "duplicate evidence decision" in duplicate["input_errors"][0]

    invalid_strength = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
            "evidence_decisions": [
                {
                    "card_id": pm2["card_id"],
                    "decision": "accept",
                    "strength_override": "BS1_Strong",
                    "reason": "Invalid cross-direction override fixture.",
                }
            ],
        }
    )
    assert invalid_strength["decision_report"]["decision_errors"] == [
        {
            "card_id": pm2["card_id"],
            "reason": "invalid_strength_for_criterion",
            "criterion": "PM2",
            "strength": "BS1_Strong",
        }
    ]
    assert invalid_strength["user_selected_bayesian"]["included_card_ids"] == []


def test_collector_does_not_trust_public_curator_fields():
    result = _make_tool(_FakeToolUniverse()).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
            "literature_proposals": [
                {
                    "fact_id": "caller-claimed-review",
                    "fact_type": "case_control",
                    "pmid": "12345678",
                    "locator": "results",
                    "excerpt": "FGFR3 NM_000142.5:c.1075+95C>G was observed in 12 cases",
                    "variant_identity": "NM_000142.5:c.1075+95C>G",
                    "gene": "FGFR3",
                    "extractor": {"name": "fixture", "version": "1"},
                    "verification_status": "curator_verified",
                    "verified_by": "caller-controlled-string",
                    "values": {
                        "variant_identity": "NM_000142.5:c.1075+95C>G",
                        "gene": "FGFR3",
                        "case_count": 12,
                        "control_count": 1000,
                        "odds_ratio": 6.2,
                        "ci_lower": 1.4,
                    },
                    "field_excerpts": {
                        "case_count": "12 cases",
                        "control_count": "1000 controls",
                        "odds_ratio": "odds ratio 6.2",
                        "ci_lower": "lower confidence limit 1.4",
                    },
                }
            ],
        }
    )

    document_facts = [
        fact
        for fact in result["source_facts"]
        if fact["tool_name"] == "EuropePMC_get_full_text"
    ]
    anchored = [
        fact
        for fact in document_facts
        if fact["features"].get("fact_type") == "case_control"
    ]
    assert anchored and anchored[0]["assessment_ready"] is True
    assert anchored[0]["verification_level"] == "machine_document_anchored"


def test_independent_literature_proposals_at_one_locator_have_distinct_ids():
    runtime = _FakeToolUniverse()
    runtime.acmg_review_assertion_verifier = lambda assertion: True
    fact = {
        "fact_id": "case-control-a",
        "fact_type": "case_control",
        "pmid": "12345678",
        "locator": "results",
        "excerpt": "FGFR3 NM_000142.5:c.1075+95C>G was observed in 12 cases",
        "variant_identity": "NM_000142.5:c.1075+95C>G",
        "gene": "FGFR3",
        "extractor": {"name": "fixture", "version": "1"},
        "values": {
            "variant_identity": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "case_count": 12,
            "control_count": 1000,
            "odds_ratio": 6.2,
            "ci_lower": 1.4,
        },
        "field_excerpts": {
            "case_count": "12 cases",
            "control_count": "1000 controls",
            "odds_ratio": "odds ratio 6.2",
            "ci_lower": "lower confidence limit 1.4",
        },
    }
    second = dict(fact)
    second["fact_id"] = "case-control-b"
    second["values"] = {**fact["values"], "case_count": 11}

    result = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "response_detail": "full",
            "literature_proposals": [fact, second],
        }
    )

    document_facts = [
        row
        for row in result["source_facts"]
        if row["tool_name"] == "EuropePMC_get_full_text"
        and row["features"].get("fact_type") == "case_control"
    ]
    assert len(document_facts) == 2
    assert len({row["fact_id"] for row in document_facts}) == 2


def test_collector_rejects_literature_fields_without_matching_full_text():
    result = _make_tool(_FakeToolUniverse()).run(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "literature_proposals": [
                {
                    "fact_id": "bad-excerpt",
                    "fact_type": "de_novo",
                    "pmid": "12345678",
                    "locator": "results",
                    "excerpt": "FGFR3 NM_000142.5:c.1075+95C>G was observed in 12 cases",
                    "variant_identity": "NM_000142.5:c.1075+95C>G",
                    "gene": "FGFR3",
                    "extractor": {"name": "fixture", "version": "1"},
                    "values": {
                        "case_id": "case-1",
                        "parental_relationships": "confirmed",
                        "phenotype_consistency": "highly_specific",
                        "inheritance_mode": "autosomal_dominant",
                    },
                    "field_excerpts": {
                        "case_id": "case-1",  # Not present in the returned paper.
                        "parental_relationships": "confirmed",
                        "phenotype_consistency": "highly specific",
                        "inheritance_mode": "autosomal dominant",
                    },
                }
            ],
        }
    )

    document_facts = [
        fact
        for fact in result["source_facts"]
        if fact["tool_name"] == "EuropePMC_get_full_text"
    ]
    assert document_facts and all(
        fact["assessment_ready"] is False for fact in document_facts
    )
    assert "PS2" not in _system_preview_criteria(result)


def test_collector_does_not_query_clinvar_with_hgvs_or_rsid():
    runtime = _FakeToolUniverse()
    _make_tool(runtime).run({"variant": "NM_000142.5:c.1075+95C>G", "gene": "FGFR3"})

    assert all(
        call["name"] != "ClinVar_get_clinical_significance" for call, _ in runtime.calls
    )


def test_collector_queries_clinvar_only_with_numeric_variation_id():
    runtime = _ClinVarVariationIdToolUniverse()
    _make_tool(runtime).run({"variant": "NM_000142.5:c.1075+95C>G", "gene": "FGFR3"})
    clinvar_calls = [
        call
        for call, _kwargs in runtime.calls
        if call["name"] == "ClinVar_get_clinical_significance"
    ]
    assert len(clinvar_calls) == 1
    assert clinvar_calls[0]["arguments"]["variant_id"] == "12345"


def test_collector_source_specs_use_registered_provider_contracts():
    specs = _make_tool(_FakeToolUniverse()).tooluniverse
    pipeline = ACMGEvidencePipeline(specs)
    rows = pipeline._source_specs(
        {
            "variant": "NM_000142.5:c.1A>G",
            "gene": "FGFR3",
            "clinical_context": {
                "hpo_terms": ["HP_0001250", "0001251"],
                "phenotype": "short stature",
            },
        },
        {"gene": "FGFR3", "rsid": "rs123"},
    )
    by_name = {name: arguments for name, arguments, _category in rows}
    assert by_name["gnomad_get_constraint"] == {
        "gene_symbol": "FGFR3",
        "dataset": "gnomad_r4",
    }
    assert "gnomad_get_gene_constraints" not in by_name
    assert "InterPro_get_entries_for_protein" not in by_name
    assert {
        "ClinGen_search_gene_validity",
        "ClinGen_get_dosage_sensitivity",
        "ClinGen_get_actionability_adult",
        "ClinGen_get_actionability_pediatric",
        "ClinGen_get_variant_classifications",
        "LitVar_search_variants",
        "LitVar_get_variant_publications",
        "PubMed_search_articles",
        "EuropePMC_search_articles",
        "HPO_get_term",
        "HPO_get_genes_by_phenotype",
        "HPO_get_diseases_by_phenotype",
        "HPO_search_terms",
    } <= set(by_name)
    assert by_name["PubMed_search_articles"]["include_abstract"] is True
    assert by_name["PubMed_search_articles"]["max_results"] == 50
    assert by_name["LitVar_get_variant_publications"] == {
        "rsid": "rs123",
        "max": 50,
    }
    assert by_name["EuropePMC_search_articles"]["require_has_ft"] is False
    assert by_name["HPO_get_genes_by_phenotype"]["term_id"] == "HP:0001251"
    assert by_name["HPO_get_genes_by_phenotype"]["limit"] == 500


class _ClinVarRepresentationToolUniverse:
    def __init__(self, *, conflict: bool = False):
        self.calls = []
        self.conflict = conflict

    def run_one_function(self, call, **kwargs):
        self.calls.append(call)
        name = call["name"]
        if name == "ClinVar_search_variants":
            arguments = call["arguments"]
            if arguments.get("rsid"):
                rows = (
                    [
                        {
                            "variant_id": "999",
                            "title": "NM_999999.1(OTHER):c.1A>G",
                            "genes": ["OTHER"],
                        }
                    ]
                    if self.conflict
                    else []
                )
                return {
                    "status": "success",
                    "source_lead_sandbox": {
                        "reviewable_features": {
                            "variants": rows,
                            "total_count": len(rows),
                        }
                    },
                }
            if arguments.get("variant_name"):
                return {
                    "status": "success",
                    "source_lead_sandbox": {
                        "reviewable_features": {
                            "variants": [
                                {
                                    "variant_id": "12345",
                                    "title": "NM_000518.5(HBB):c.20A>T (p.Glu7Val)",
                                    "genes": ["HBB"],
                                }
                            ],
                            "total_count": 1,
                        }
                    },
                }
            raise AssertionError("gene fallback should not be reached")
        if name == "ClinVar_get_clinical_significance":
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {"variation_id": "12345"}
                },
            }
        raise AssertionError(name)


def test_clinvar_resolution_uses_rsid_then_identity_hgvs():
    runtime = _ClinVarRepresentationToolUniverse()
    pipeline = ACMGEvidencePipeline(runtime)
    calls, variation_id = pipeline._resolve_clinvar_calls(
        {"variant": "NM_000518.5:c.20A>T", "gene": "HBB"},
        {
            "gene": "HBB",
            "rsid": "rs334",
            "validated_hgvs_c": "NM_000518.5:c.20A>T",
            "hgvs_p": "NP_000509.1:p.Glu7Val",
        },
    )
    assert variation_id == "12345"
    assert [call.tool_name for call in calls] == [
        "ClinVar_search_variants",
        "ClinVar_search_variants",
        "ClinVar_get_clinical_significance",
    ]
    assert runtime.calls[1]["arguments"]["variant_name"] == [
        "NM_000518.5:c.20A>T",
        "NP_000509.1:p.Glu7Val",
    ]


def test_clinvar_resolution_stops_on_nonempty_identity_conflict():
    runtime = _ClinVarRepresentationToolUniverse(conflict=True)
    calls, variation_id = ACMGEvidencePipeline(
        runtime
    )._resolve_clinvar_calls(
        {"variant": "NM_000518.5:c.20A>T", "gene": "HBB"},
        {
            "gene": "HBB",
            "rsid": "rs334",
            "validated_hgvs_c": "NM_000518.5:c.20A>T",
        },
    )
    assert variation_id is None
    assert len(calls) == 1
    assert len(runtime.calls) == 1


class _ConstraintOnlyToolUniverse(_FakeToolUniverse):
    def __init__(self, *, primary_ready: bool):
        super().__init__()
        self.primary_ready = primary_ready

    def run_one_function(self, call, **kwargs):
        if call["name"] == "gnomad_get_constraint":
            self.calls.append((call, kwargs))
            if not self.primary_ready:
                return {"status": "error", "error": "primary unavailable"}
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "gene": "FGFR3",
                        "dataset": "gnomad_r4",
                        "reference_genome": "GRCh38",
                        "pli": 0.98,
                        "loeuf": 0.21,
                        "mis_z": 3.2,
                        "provider_version": "gnomAD constraint gnomad_r4",
                    }
                },
            }
        if call["name"] == "gnomad_get_gene_constraints":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "gene": "FGFR3",
                        "reference_genome": "GRCh38",
                        "pli": 0.97,
                        "provider_version": "legacy gnomAD constraint",
                    }
                },
            }
        return super().run_one_function(call, **kwargs)


def test_constraint_provider_never_calls_removed_acmg_fallback():
    identity = {"gene": "FGFR3", "build": "GRCh38"}
    failed = _ConstraintOnlyToolUniverse(primary_ready=False)
    failed_calls = ACMGEvidencePipeline(failed)._collect_sources(
        {"variant": "NM_000142.5:c.1A>G", "gene": "FGFR3"}, identity
    )
    assert any(call.tool_name == "gnomad_get_constraint" for call in failed_calls)
    assert not any(
        call.tool_name == "gnomad_get_gene_constraints" for call in failed_calls
    )

    ready = _ConstraintOnlyToolUniverse(primary_ready=True)
    ready_calls = ACMGEvidencePipeline(ready)._collect_sources(
        {"variant": "NM_000142.5:c.1A>G", "gene": "FGFR3"}, identity
    )
    assert not any(
        call.tool_name == "gnomad_get_gene_constraints"
        for call in ready_calls
    )


class _PVS1ToolUniverse(_FakeToolUniverse):
    """Frameshift variant with machine-verifiable PVS1 facts."""

    def run_one_function(self, call, **kwargs):
        name = call["name"]
        if name == "VariantValidator_validate_variant":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "reviewable_features": {
                    "validated_hgvs_c": "NM_000142.5:c.500del",
                    "hgvs_g": "NC_000004.12:g.1803931del",
                    "hgvs_g_grch37": "chr4:g.1803931del",
                    "coordinates_grch37": {
                        "chr": "4",
                        "pos": 1803931,
                        "ref": "CA",
                        "alt": "C",
                    },
                    "consequence": "frameshift_variant",
                    "gene": "FGFR3",
                    "provider_version": "VariantValidator REST",
                },
            }
        if name == "EnsemblVEP_variant_recoder":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "reviewable_features": {
                    "chr": "4",
                    "pos": 1803931,
                    "ref": "CA",
                    "alt": "C",
                    "hgvs_c": "NM_000142.5:c.500del",
                    "hgvs_g": "NC_000004.12:g.1803931del",
                    "consequence": "frameshift_variant",
                    "provider_version": "Ensembl Variant Recoder REST",
                },
            }
        if name in {"EnsemblVEP_annotate_hgvs", "EnsemblVEP_annotate_rsid"}:
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "chr": "4",
                        "pos": 1803931,
                        "ref": "CA",
                        "alt": "C",
                        "build": "GRCh38",
                        "most_severe_consequence": "frameshift_variant",
                        "vep_transcript_candidates": [
                            {
                                "gene": "FGFR3",
                                "transcript": "NM_000142.5",
                                "mane_select": "NM_000142.5",
                                "hgvsc": "NM_000142.5:c.500del",
                                "biotype": "protein_coding",
                                "exon": "3/10",
                                "consequence": ["frameshift_variant"],
                            }
                        ],
                        "provider_version": "Ensembl VEP REST",
                    },
                },
            }
        if name == "ClinGen_search_gene_validity":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "gene": "FGFR3",
                        "validity_curations": [
                            {
                                "gene": "FGFR3",
                                "disease_label": "achondroplasia",
                                "disease_id": "MONDO:0007037",
                                "moi": "AD",
                                "gene_disease_validity": "Definitive",
                            }
                        ],
                        "provider_version": "ClinGen Gene-Disease Validity",
                    },
                },
            }
        if name == "gnomad_get_constraint":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "gene": "FGFR3",
                        "dataset": "gnomad_r4",
                        "reference_genome": "GRCh38",
                        "pli": 0.98,
                        "loeuf": 0.21,
                        "provider_version": "gnomAD gene constraint GraphQL",
                    },
                },
            }
        if name == "EuropePMC_get_full_text":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "data": {
                    "pmid": "99999999",
                    "sections": {
                        "mechanism": (
                            "FGFR3 NM_000142.5:c.500del is evaluated in a "
                            "haploinsufficiency loss-of-function disease mechanism."
                        )
                    },
                },
            }
        return super().run_one_function(call, **kwargs)


def _pvs1_arguments() -> dict:
    return {
        "variant": "NM_000142.5:c.500del",
        "gene": "FGFR3",
        "response_detail": "full",
        "literature_proposals": [
            {
                "fact_id": "fgfr3-lof-mechanism",
                "fact_type": "mechanism",
                "pmid": "99999999",
                "locator": "mechanism",
                "excerpt": (
                    "FGFR3 NM_000142.5:c.500del is evaluated in a "
                    "haploinsufficiency loss-of-function disease mechanism."
                ),
                "variant_identity": "NM_000142.5:c.500del",
                "gene": "FGFR3",
                "values": {
                    "variant_identity": "NM_000142.5:c.500del",
                    "gene": "FGFR3",
                    "gene_disease_mechanism": "haploinsufficiency",
                },
                "field_excerpts": {
                    "gene_disease_mechanism": (
                        "haploinsufficiency loss-of-function disease mechanism"
                    )
                },
                "criterion": "PVS1",
                "suggested_strength": "PVS1",
                "interpretation": (
                    "The cited passage establishes a loss-of-function mechanism."
                ),
                "confidence": 0.9,
                "questions": ["Confirm disease and inheritance match."],
                "extractor": {"name": "fixture-llm", "version": "1.0"},
            }
        ],
    }


def test_pvs1_decision_tree_enters_system_preview_when_facts_verified():
    runtime = _PVS1ToolUniverse()
    result = _make_tool(runtime).run(_pvs1_arguments())

    assert result.get("status") != "error"
    names = [call[0]["name"] for call in runtime.calls]
    assert "ClinGen_search_gene_validity" in names
    assert "gnomad_get_constraint" in names
    pvs1 = next(row for row in result["evidence_cards"] if row["criterion"] == "PVS1")
    assert pvs1["strength"] == "PVS1"
    assert pvs1["assessment_status"] == "met"
    assert pvs1["rule_id"] == "clingen-svi-pvs1"
    assert pvs1["rule_version"] == "1.2"
    assert pvs1["overlay_validated"] is True
    assert pvs1["system_preview_included"] is True
    assert "PVS1" in _system_preview_criteria(result)
    mechanism = pvs1["observed_facts"]["lof_mechanism"]
    assert mechanism["value"] == "haploinsufficiency"
    assert mechanism["source"] == "document_fact"
    assert any("NMD predicted" in step for step in pvs1["provenance_chain"])


class _PVS1NoMechanismToolUniverse(_PVS1ToolUniverse):
    def run_one_function(self, call, **kwargs):
        if call["name"] == "ClinGen_search_gene_validity":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "gene": "FGFR3",
                        "validity_curations": [
                            {"gene": "FGFR3", "gene_disease_validity": "Limited"}
                        ],
                        "provider_version": "ClinGen Gene-Disease Validity",
                    },
                },
            }
        if call["name"] == "gnomad_get_constraint":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "gene": "FGFR3",
                        "dataset": "gnomad_r4",
                        "pli": 0.05,
                        "loeuf": 1.4,
                        "provider_version": "gnomAD gene constraint GraphQL",
                    },
                },
            }
        return super().run_one_function(call, **kwargs)


def test_pvs1_without_mechanism_facts_stays_out_of_preview():
    runtime = _PVS1NoMechanismToolUniverse()
    result = _make_tool(runtime).run(
        {
            "variant": "NM_000142.5:c.500del",
            "gene": "FGFR3",
            "response_detail": "full",
        }
    )

    assert result.get("status") != "error"
    pvs1 = next(row for row in result["evidence_cards"] if row["criterion"] == "PVS1")
    assert pvs1["strength"] == "not_assessed"
    assert pvs1["assessment_status"] == "not_assessed"
    assert pvs1["system_preview_included"] is False
    assert "PVS1" not in _system_preview_criteria(result)
    assert any("mechanism not established" in step for step in pvs1["provenance_chain"])


class _PVS1LastExonToolUniverse(_PVS1ToolUniverse):
    """Terminal-exon frameshift with a provider-verified protein length."""

    def run_one_function(self, call, **kwargs):
        name = call["name"]
        if name in {"EnsemblVEP_annotate_hgvs", "EnsemblVEP_annotate_rsid"}:
            result = super().run_one_function(call, **kwargs)
            row = result["source_lead_sandbox"]["reviewable_features"][
                "vep_transcript_candidates"
            ][0]
            row["exon"] = "10/10"
            row["hgvsp"] = "NP_000133.1:p.Gly400AlafsTer30"
            return result
        if name == "EBIProteins_get_variation_by_hgvs":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "hgvs_g": "NC_000004.12:g.1803931del",
                        "protein_candidates": [
                            {
                                "protein_accession": "P22607",
                                "gene": "FGFR3",
                                "taxid": 9606,
                                "protein_position_start": 400,
                                "protein_position_end": 400,
                                "wild_type": "G",
                                "alternative_sequence": "A",
                            }
                        ],
                        "provider_version": "EBI Proteins API",
                    },
                },
            }
        if name == "EBIProteins_get_features":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "protein_accession": "P22607",
                        "sequence_length": 800,
                        "features": [],
                        "provider_version": "EBI Proteins API",
                    },
                },
            }
        return super().run_one_function(call, **kwargs)


def test_pvs1_escape_fraction_uses_provider_protein_length():
    runtime = _PVS1LastExonToolUniverse()
    result = _make_tool(runtime).run(_pvs1_arguments())

    assert result.get("status") != "error"
    pvs1 = next(row for row in result["evidence_cards"] if row["criterion"] == "PVS1")
    assert pvs1["strength"] == "PVS1_Strong"
    assert pvs1["system_preview_included"] is True
    assert any("50.0%" in step and ">10%" in step for step in pvs1["provenance_chain"])


class _PVS1ExonLofToolUniverse(_PVS1ToolUniverse):
    """Terminal-exon frameshift whose exon carries a frequent gnomAD LoF."""

    def run_one_function(self, call, **kwargs):
        name = call["name"]
        if name in {"EnsemblVEP_annotate_hgvs", "EnsemblVEP_annotate_rsid"}:
            result = super().run_one_function(call, **kwargs)
            row = result["source_lead_sandbox"]["reviewable_features"][
                "vep_transcript_candidates"
            ][0]
            row["transcript"] = "ENST00000357654"
            row["mane_select"] = "NM_000142.5"
            row["exon"] = "10/10"
            return result
        if name == "ensembl_lookup_gene":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "transcript_id": "ENST00000357654",
                        "chrom": "4",
                        "exons": [
                            {
                                "exon_id": "ENSE00001",
                                "transcript": "ENST00000357654",
                                "rank": 10,
                                "chrom": "4",
                                "start": 1803900,
                                "end": 1804200,
                                "strand": 1,
                            }
                        ],
                        "provider_version": "Ensembl REST lookup",
                    },
                },
            }
        if name == "gnomad_get_region_variants":
            self.calls.append((call, kwargs))
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "chrom": "4",
                        "start": 1803900,
                        "stop": 1804200,
                        "variants": [
                            {
                                "variant_id": "4-1804000-A-T",
                                "consequence": "stop_gained",
                                "af_exome": 0.003,
                                "af_genome": None,
                                "homozygote_count_exome": 0,
                                "homozygote_count_genome": None,
                            }
                        ],
                        "provider_version": "gnomAD GraphQL region variants",
                    },
                },
            }
        return super().run_one_function(call, **kwargs)


def test_pvs1_exon_lof_frequent_gate_via_ensembl_and_gnomad():
    runtime = _PVS1ExonLofToolUniverse()
    result = _make_tool(runtime).run(_pvs1_arguments())

    assert result.get("status") != "error"
    names = [call[0]["name"] for call in runtime.calls]
    assert "ensembl_lookup_gene" in names
    assert "gnomad_get_region_variants" in names
    pvs1 = next(row for row in result["evidence_cards"] if row["criterion"] == "PVS1")
    assert pvs1["strength"] == "not_applicable"
    assert pvs1["system_preview_included"] is False
    assert any(
        "frequent" in step and "gnomAD" in step for step in pvs1["provenance_chain"]
    )


if __name__ == "__main__":
    test_collector_accepts_minimal_input()
    test_collector_returns_conflict_report()
    test_collector_returns_system_preview_bayesian()
    print("PASS test_acmg_evidence_collector")
