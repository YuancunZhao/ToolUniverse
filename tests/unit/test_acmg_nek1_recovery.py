"""NEK1 fallback regression; reported identifiers, synthetic exon boundaries.

No patient data or online calls. The 36-exon model tests strand/rank handling,
not the biological accuracy of a cached NEK1 transcript annotation.
"""

from copy import deepcopy
from dataclasses import replace
import json

import pytest

from tooluniverse.acmg.collector import (
    ACMGEvidencePipeline,
    SourceCall,
    _caller_context_facts,
    _normalize_caller_verified_context,
    _recoverable_gaps,
)
from tooluniverse.acmg_runtime_tools import ACMGGuardFinalAnswerTool
from tooluniverse.acmg.models import fact_is_strictly_verified
from tooluniverse.acmg.pvs1 import _nmd_region, NMD_POSITION_POLICY_VERSION
from tooluniverse.acmg.source_adapters import adapt_source_output


NM = "NM_001199397.3"
ENST = "ENST00000507142.6"
C = NM + ":c.2449G>T"
G = "NC_000004.12:g.169463381C>A"
IDENTITY = {
    "gene": "NEK1",
    "transcript": NM,
    "hgvs_c": C,
    "validated_hgvs_c": C,
    "hgvs_g": G,
    "hgvs_p": "p.Glu817Ter",
    "build": "GRCh38",
    "coordinates": {"chr": "4", "pos": 169463381, "ref": "C", "alt": "A"},
    "identity_verified": True,
}


class NEK1Providers:
    def __init__(self, *, marrvel=True, transient=False):
        self.calls = []
        self.marrvel = marrvel
        self.transient = transient

    def run_many_functions(self, calls, **kwargs):
        return [self.run_one_function(call, **kwargs) for call in calls]

    def run_one_function(self, call, **kwargs):
        self.calls.append(call)
        name = call["name"]
        if name == "Tark_get_mane_transcripts":
            if self.transient and sum(c["name"] == name for c in self.calls) == 1:
                return {
                    "status": "error",
                    "status_code": 503,
                    "retryable": True,
                    "detail": "temporarily unavailable",
                    "url": "https://tark.ensembl.org/api/transcript/manelist/",
                }
            return {
                "status": "success",
                "data": [
                    {
                        "gene": "NEK1",
                        "mane_type": "MANE SELECT",
                        "refseq_transcript": NM,
                        "ensembl_transcript": ENST,
                    }
                ],
                "metadata": {"source": "Tark fixture release 115"},
            }
        if name == "Tark_get_transcript":
            return {
                "status": "success",
                "data": [
                    {
                        "stable_id": ENST,
                        "assembly": "GRCh38",
                        "biotype": "protein_coding",
                        "region": "4",
                        "start": 169392809,
                        "end": 169612583,
                        "strand": -1,
                        "releases": ["fixture-115"],
                    }
                ],
            }
        if name == "ensembl_get_overlap_features":
            return [
                {
                    "id": f"EXON-{rank}",
                    "Parent": ENST.split(".")[0],
                    "rank": rank,
                    "seq_region_name": "4",
                    "assembly_name": "GRCh38",
                    "strand": -1,
                    "start": 169463300 + (27 - rank) * 1000,
                    "end": 169463500 + (27 - rank) * 1000,
                }
                for rank in range(1, 37)
            ]
        if name == "MARRVEL_get_omim_phenotypes":
            if not self.marrvel:
                return {
                    "status": "error",
                    "retryable": False,
                    "error": "provider offline",
                }
            return {
                "status": "success",
                "data": [
                    {
                        "gene_mim_number": 604588,
                        "phenotype": "ALS susceptibility 24",
                        "phenotype_mim_number": 617892,
                        "inheritance": "Autosomal dominant",
                    },
                    {
                        "phenotype": "Short-rib thoracic dysplasia 6",
                        "phenotype_mim_number": 263520,
                        "inheritance": "Autosomal recessive",
                    },
                    {
                        "phenotype": "?Orofaciodigital syndrome II",
                        "phenotype_mim_number": 252100,
                        "inheritance": "Autosomal recessive",
                    },
                ],
                "metadata": {"source": "MARRVEL fixture"},
            }
        if name == "gather_gene_disease_associations":
            return {
                "status": "success",
                "data": {
                    "query": {"gene": "NEK1"},
                    "num_associations": 1,
                    "associations": [
                        {
                            "name": "ALS susceptibility 24",
                            "sources": ["GenCC"],
                            "inheritance": "AD",
                        }
                    ],
                    "sources_queried": ["GenCC", "OMIM"],
                    "sources_failed": ["OMIM: missing key"],
                    "per_source_result_counts": {"GenCC": 1, "OMIM": 0},
                },
            }
        if name == "gnomad_get_variant":
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        **IDENTITY["coordinates"],
                        "build": "GRCh38",
                        "af": 0.00001,
                        "ac": 1,
                        "an": 100000,
                        "popmax_af": 0.00001,
                        "provider_version": "gnomAD fixture",
                    }
                },
            }
        return {"status": "unavailable", "retryable": False, "error": "offline fixture"}


def profile():
    return {
        "status": "resolved",
        "selected_transcript": NM,
        "selected_transcript_terms": ["stop_gained"],
        "annotation_status": "resolved",
        "protein_effect": "lof",
        "splice_class": "none",
        "hgvs_c": C,
        "hgvs_p": "p.Glu817Ter",
        "genomic_position": 169463381,
        "genomic_ref": "C",
        "genomic_alt": "A",
        "selected_observation": {
            "transcript": NM,
            "gene": "NEK1",
            "hgvs_c": C,
            "hgvs_p": "p.Glu817Ter",
            "consequence_terms": ["stop_gained"],
        },
    }


def structure_facts(runtime=None):
    runtime = runtime or NEK1Providers()
    pipeline = ACMGEvidencePipeline(runtime)
    calls = pipeline._pvs1_context_calls(IDENTITY, profile(), {})
    return pipeline, calls, pipeline._source_facts(calls, IDENTITY)


def test_nek1_structure_retry_and_source_provenance():
    runtime = NEK1Providers(transient=True)
    pipeline, calls, facts = structure_facts(runtime)
    context = pipeline._pvs1_structure_context(IDENTITY, profile(), facts)
    assert context["ensembl_transcript"] == ENST
    assert context["selected_refseq_transcript"] == NM
    assert (context["exon_number"], context["exon_total"]) == (27, 36)
    assert context["biotype"] == "protein_coding"
    assert context["nmd"]["region"] == "nmd_predicted"
    assert context["nmd"]["distance_to_final_exon_junction_bp"] == 81 + 8 * 201
    mane = [f for f in facts.values() if f.tool_name == "Tark_get_mane_transcripts"]
    assert {f.status for f in mane} == {"success", "failed"}
    assert all(f.features.get("retrieved_at") for f in mane)
    assert sum(c["name"] == "Tark_get_mane_transcripts" for c in runtime.calls) == 2
    pvs1, _ = pipeline._pvs1_facts(profile(), facts, IDENTITY)
    assert _nmd_region(pvs1["transcript"], [])[0] == "nmd_predicted"
    assert "lof_mechanism" not in pvs1


@pytest.mark.parametrize("mutation", ["build", "transcript", "rank", "strand", "chrom"])
def test_invalid_models_do_not_produce_nmd(mutation):
    pipeline, calls, _ = structure_facts()
    exon_call = calls[-1]
    rows = exon_call.result["source_lead_sandbox"]["reviewable_features"]["exons"]
    for row in rows:
        if mutation == "build":
            row["assembly"] = "GRCh37"
        elif mutation == "transcript":
            row["transcript"] = "ENST999999"
        elif mutation == "rank":
            row.pop("rank")
        elif mutation == "strand":
            row["strand"] = 0
        else:
            row["chrom"] = "1"
    facts = pipeline._source_facts(calls, IDENTITY)
    assert not pipeline._pvs1_structure_context(IDENTITY, profile(), facts)["nmd"]


def test_frameshift_does_not_use_variant_coordinate_as_ptc():
    pipeline, _, facts = structure_facts()
    altered = profile()
    altered["selected_transcript_terms"] = ["frameshift_variant"]
    altered["selected_observation"]["consequence_terms"] = ["frameshift_variant"]
    assert not pipeline._pvs1_structure_context(IDENTITY, altered, facts)["nmd"]
    wrong_build = {**IDENTITY, "build": "GRCh37"}
    calls = pipeline._pvs1_context_calls(wrong_build, profile(), {})
    assert "ensembl_get_overlap_features" not in [c.tool_name for c in calls]


@pytest.mark.parametrize("marrvel,count,expected", [(True, 3, False), (False, 1, True)])
def test_omim_real_envelope_and_fallback(marrvel, count, expected):
    runtime = NEK1Providers(marrvel=marrvel)
    pipeline = ACMGEvidencePipeline(runtime)
    calls = pipeline._call_batch(
        [("MARRVEL_get_omim_phenotypes", {"symbol": "NEK1"}, "disease_context")]
    )
    calls += pipeline._disease_context_recovery_calls(calls, "NEK1")
    context = pipeline._omim_context(pipeline._source_facts(calls, IDENTITY), "NEK1")
    assert context["association_count"] == count
    assert context["association_status"] == "resolved"
    assert context["review_only"] is True
    assert (
        "gather_gene_disease_associations" in [c["name"] for c in runtime.calls]
    ) == expected
    if marrvel:
        assert context["associations"][0]["inheritance_enum"] == "AD"
        assert context["associations"][0]["phenotype_mim"] == 617892


def test_caller_attribution_is_not_verification():
    runtime = NEK1Providers()
    entries = []
    for context_type, name, query in [
        ("transcript_mapping", "Tark_get_mane_transcripts", {"refseq_id": NM}),
        ("transcript_record", "Tark_get_transcript", {"stable_id": ENST}),
    ]:
        entries.append(
            {
                "context_id": context_type,
                "context_type": context_type,
                "tool_name": name,
                "query": query,
                "values": runtime.run_one_function({"name": name, "arguments": query}),
                "provider_version": "fixture-115",
                "retrieved_at": "2026-09-04T10:00:00+08:00",
            }
        )
    normalized, errors = _normalize_caller_verified_context(entries)
    assert not errors
    facts = _caller_context_facts(normalized, IDENTITY)
    assert len(facts) == 2
    assert all(f.identity_status == "matched" for f in facts.values())
    assert not any(fact_is_strictly_verified(f) for f in facts.values())
    bad = deepcopy(entries)
    bad[0]["tool_name"] = "arbitrary_http_request"
    assert _normalize_caller_verified_context(bad)[1]

    # Region overlap contains many transcripts; select only through the NM/MANE pair.
    exons = runtime.run_one_function(
        {"name": "ensembl_get_overlap_features", "arguments": {}}
    )
    exons.append({**exons[0], "Parent": "ENST999999"})
    entries.insert(
        0,
        {
            "context_id": "exons",
            "context_type": "exon_model",
            "tool_name": "ensembl_get_overlap_features",
            "query": {
                "species": "human",
                "region": "4:169392809-169612583",
                "feature": "exon",
            },
            "values": exons,
            "provider_version": "fixture-115",
            "retrieved_at": "2026-09-04T10:00:00+08:00",
        },
    )
    normalized, errors = _normalize_caller_verified_context(entries)
    assert not errors
    facts = _caller_context_facts(normalized, IDENTITY)
    structure = ACMGEvidencePipeline._pvs1_structure_context(IDENTITY, profile(), facts)
    assert structure["exon_number"] == 27
    assert structure["verification_level"] == "caller_attributed"
    assert not any(fact_is_strictly_verified(fact) for fact in facts.values())

    entries[1]["values"] = {"status": "error", "error": "provider unavailable"}
    normalized, _ = _normalize_caller_verified_context(entries)
    facts = _caller_context_facts(normalized, IDENTITY)
    assert any(fact.status == "failed" for fact in facts.values())


def test_nek1_collector_guard_two_call_path(monkeypatch):
    runtime = NEK1Providers()
    pipeline = ACMGEvidencePipeline(runtime)
    # Identity resolution is covered separately. This isolates provider recovery
    # after the reported allele has already been independently confirmed.
    monkeypatch.setattr(pipeline, "_identity", lambda *args: ([], deepcopy(IDENTITY)))
    monkeypatch.setattr(pipeline, "_consequence_calls", lambda *args: ([], {}))
    monkeypatch.setattr(pipeline, "_profile_from_facts", lambda *args: profile())
    result = pipeline.run(
        {
            "variant": "NEK1;" + C + "(p.Glu817Ter)",
            "gene": "NEK1",
            "clinical_context": {"zygosity": "heterozygous"},
        }
    )
    assert result["omim_context"]["association_count"] == 3
    structure = result["consequence_profile"]["transcript_structure"]
    assert (structure["exon_number"], structure["exon_total"]) == (27, 36)
    assert structure["nmd"]["region"] == "nmd_predicted"
    assert not {"exon_structure_missing", "nmd_facts_missing"}.intersection(
        row["code"] for row in result["recoverable_gaps"]
    )
    assert not result["final_classification_allowed"]
    pvs1 = next(
        row for row in result["criterion_reviews"] if row["criterion"] == "PVS1"
    )
    assert pvs1["missing_requirements"] == ["gene LoF disease mechanism"]
    text = "NEK1: selected transcript NM_001199397.3; exon 27/36. PVS1 needs disease-specific LoF mechanism evidence."
    guarded = ACMGGuardFinalAnswerTool(
        {
            "name": "ACMG_guard_final_answer",
            "type": "ACMG_guard_final_answer",
            "fields": {},
        }
    ).run({"final_answer_text": text, "guard_context": result["guard_context"]})
    assert guarded["status"] == "PASS"
    assert len(json.dumps(result["guard_context"]).encode()) < 5000


def test_independently_retrieved_model_takes_priority_over_caller_context():
    pipeline, _, retrieved = structure_facts()
    caller = {
        "caller:" + fact.fact_id: replace(
            fact,
            fact_id="caller:" + fact.fact_id,
            verification_level="caller_attributed",
            features=deepcopy(fact.features),
        )
        for fact in retrieved.values()
    }
    for fact in caller.values():
        for row in fact.features.get("mane_transcripts") or []:
            row["ensembl_transcript"] = "ENST999999.1"
        for row in fact.features.get("transcript_records") or []:
            row["start"] = 1
    context = pipeline._pvs1_structure_context(
        IDENTITY, profile(), {**caller, **retrieved}
    )
    assert context["ensembl_transcript"] == ENST
    assert context["start"] == 169392809
    assert context["verification_level"] == "provider_retrieved"
    assert not set(context["source_fact_ids"]).intersection(caller)


@pytest.mark.parametrize(
    "distance,region",
    [
        (48, "nmd_escape"),
        (50, "nmd_uncertain"),
        (52, "nmd_uncertain"),
        (53, "nmd_predicted"),
    ],
)
def test_nmd_boundary_retains_codon_uncertainty(distance, region):
    transcript = {
        "exon": "35/36",
        "nmd_region": region,
        "distance_to_final_exon_junction_bp": distance,
        "nmd_policy_version": NMD_POSITION_POLICY_VERSION,
    }
    assert _nmd_region(transcript, [])[0] == region
    if region != "nmd_predicted":
        transcript["nmd_region"] = "nmd_predicted"
        assert _nmd_region(transcript, [])[0] is None


def test_disease_empty_failed_and_clinvar_gap_are_distinct():
    def facts(data, *, clinvar=False):
        call = SourceCall(
            "gather_gene_disease_associations",
            "disease_context",
            "success",
            {
                "source_lead_sandbox": adapt_source_output(
                    "gather_gene_disease_associations",
                    {"status": "success", "data": data},
                )
            },
            arguments={"gene": "NEK1"},
        )
        calls = [call]
        if clinvar:
            calls.append(
                SourceCall(
                    "ClinVar_search_variants",
                    "source_assertion",
                    "success",
                    {
                        "source_lead_sandbox": {
                            "reviewable_features": {"total_count": 100}
                        }
                    },
                    arguments={"gene": "NEK1"},
                )
            )
        return ACMGEvidencePipeline._source_facts(calls, IDENTITY)

    data = {
        "query": {"gene": "NEK1"},
        "associations": [],
        "sources_queried": ["OMIM", "GenCC"],
        "sources_failed": [],
        "per_source_result_counts": {"OMIM": 0, "GenCC": 0},
    }
    context = ACMGEvidencePipeline._omim_context(facts(data), "NEK1")
    assert context["association_status"] == "confirmed_no_association"
    assert "queried sources only" in context["absence_scope"]
    with_signal = ACMGEvidencePipeline._omim_context(facts(data, clinvar=True), "NEK1")
    assert with_signal["association_status"] == "provider_gap"
    assert with_signal["consistency_warnings"]
    data["sources_failed"] = ["OMIM: no API key"]
    assert (
        ACMGEvidencePipeline._omim_context(facts(data), "NEK1")["association_status"]
        == "provider_gap"
    )


def test_exhausted_retry_is_bounded_and_each_attempt_remains_a_fact():
    class Offline(NEK1Providers):
        def run_one_function(self, call, **kwargs):
            self.calls.append(call)
            return {
                "status": "error",
                "status_code": 503,
                "retryable": True,
                "detail": "overloaded",
            }

    runtime = Offline()
    pipeline = ACMGEvidencePipeline(runtime)
    call = pipeline._call("Tark_get_transcript", {"stable_id": ENST}, "functional")
    assert len(runtime.calls) == 2
    assert len(pipeline._source_facts([call], IDENTITY)) == 2


def test_repair_plan_uses_selected_nm_and_explicit_dependencies():
    gaps = _recoverable_gaps(profile(), {}, identity=IDENTITY)
    gap = next(row for row in gaps if row["code"] == "exon_structure_missing")
    assert gap["repair_plan"][0]["arguments"] == {"refseq_id": NM}
    assert gap["repair_plan"][1]["arguments_from"]
    assert gap["caller_enrichment_target"] == "caller_verified_context"
    grch37 = _recoverable_gaps(profile(), {}, identity={**IDENTITY, "build": "GRCh37"})
    gap = next(row for row in grch37 if row["code"] == "exon_structure_missing")
    assert gap["blocking_reason"]
    assert "ensembl_get_overlap_features" not in [
        step["tool_name"] for step in gap["repair_plan"]
    ]


def test_source_fact_ids_do_not_change_when_timestamp_is_serialized_twice():
    pipeline, calls, facts = structure_facts()
    assert list(facts) == list(pipeline._source_facts(calls, IDENTITY))
