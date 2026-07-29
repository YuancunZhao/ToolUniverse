"""Deterministic ClinGen SVI PVS1 decision-tree tests (Abou Tayoun 2018)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg.functional import functional_evidence
from tooluniverse.acmg.collector import ACMGEvidencePipeline
from tooluniverse.acmg.models import SourceFact
from tooluniverse.acmg.pvs1 import (
    assess_pvs1,
    infer_mechanism_from_population_facts,
)
from tooluniverse.acmg.rule_catalog import (
    bayesian_odds_for_output,
    rule_allows_system_preview_strength,
)
from tooluniverse.acmg.spliceai import bind_spliceai_site, normalize_spliceai_profile


def _profile(**overrides):
    profile = {
        "status": "resolved",
        "selected_transcript": "NM_000142.5",
        "selected_transcript_terms": ["frameshift_variant"],
        "protein_effect": "lof",
        "splice_class": "none",
        "splice_position": None,
        "protein_position": 167,
    }
    profile.update(overrides)
    return profile


def _facts(**overrides):
    facts = {
        "lof_mechanism": {"established": True, "source": "cspec_contract"},
        "transcript": {"biotype": "protein_coding", "exon": "3/10"},
        "protein": {"position": 167, "length": 800},
    }
    facts.update(overrides)
    return facts


def _splice_profile(
    site_type: str,
    loss_score: float,
    *,
    other_score: float = 0.0,
    loss_position: int = 0,
    hgvs_c: str = "",
    variant_position: int | None = None,
    canonical_site_position: int | None = None,
):
    loss_channel = "DS_DL" if site_type == "donor" else "DS_AL"
    deltas = {
        "DS_AG": other_score,
        "DS_AL": 0.0,
        "DS_DG": 0.0,
        "DS_DL": 0.0,
    }
    deltas[loss_channel] = loss_score
    positions = {
        "DP_AG": 0,
        "DP_AL": 0,
        "DP_DG": 0,
        "DP_DL": 0,
    }
    positions[loss_channel.replace("DS_", "DP_")] = loss_position
    profile = normalize_spliceai_profile({**deltas, **positions})
    return bind_spliceai_site(
        profile,
        site_type,
        hgvs_c=hgvs_c,
        variant_position=variant_position,
        canonical_site_position=canonical_site_position,
    )


def _cspec_override(**pvs1_contract):
    return {
        "specification_id": "GN000-PVS1",
        "rule_id": "clingen-cspec-gn000-pvs1",
        "version": "1.0.0",
        "primary_reference": "https://example.test/cspec",
        "criteria": {"PVS1": dict(pvs1_contract)},
    }


def test_spliceai_binding_reports_loss_and_local_gain_positions():
    profile = normalize_spliceai_profile(
        {
            "DS_AG": 0.0,
            "DS_AL": 0.0,
            "DS_DG": 0.72,
            "DS_DL": 0.91,
            "DP_AG": 0,
            "DP_AL": 0,
            "DP_DG": 4,
            "DP_DL": -1,
            "gene": "GENE1",
            "transcript": "NM_000001.1",
            "t_strand": "-",
        }
    )
    bound = bind_spliceai_site(
        profile,
        "donor",
        hgvs_c="NM_000001.1:c.100+1_100+2dup",
        variant_position=1000,
        canonical_site_position=999,
    )

    assert bound["native_loss_channel"] == "DS_DL"
    assert bound["native_loss_position_channel"] == "DP_DL"
    assert bound["native_loss_position"] == -1
    assert bound["native_loss_event_coordinate"] == 999
    assert bound["native_loss_position_status"] == "exact_selected_transcript_site"
    assert bound["native_loss_supported"] is True
    assert bound["transcript_strand"] == "-"
    assert bound["supported_gain_events"] == [
        {
            "event": "donor_gain",
            "score_channel": "DS_DG",
            "score": 0.72,
            "position_channel": "DP_DG",
            "position": 4,
            "event_coordinate": 1004,
            "distance_from_canonical_site": 5,
            "threshold": 0.5,
        }
    ]


def test_unresolved_literature_mechanism_does_not_establish_pvs1_gate():
    fact = SourceFact(
        fact_id="mechanism-unresolved",
        tool_name="EuropePMC_get_full_text",
        status="success",
        query_identity={"gene": "GENE1"},
        result_identity={"gene": "GENE1"},
        identity_verified=True,
        features={
            "fact_type": "mechanism",
            "semantic_status": "unresolved",
            "values": {"gene_disease_mechanism": "loss_of_function"},
        },
        raw_result_hash="fixture",
        assessment_ready=True,
    )

    facts, fact_ids = ACMGEvidencePipeline._pvs1_facts(
        {"status": "unavailable"}, {fact.fact_id: fact}
    )

    assert "lof_mechanism" not in facts
    assert fact.fact_id not in fact_ids


def test_nmd_predicted_truncating_variant_yields_full_pvs1():
    card = assess_pvs1(consequence_profile=_profile(), pvs1_facts=_facts())
    assert card.strength == "PVS1"
    assert card.rule_id == "clingen-svi-pvs1"
    assert card.rule_version == "1.2"
    assert card.rule_reference == "Abou Tayoun et al. 2018, PMID:30192042"
    assert any("NMD predicted" in step for step in card.provenance_chain)


def test_penultimate_exon_conservatively_downgrades():
    card = assess_pvs1(
        consequence_profile=_profile(),
        pvs1_facts=_facts(transcript={"biotype": "protein_coding", "exon": "9/10"}),
    )
    assert card.strength == "PVS1_Strong"
    assert any("penultimate exon" in step for step in card.provenance_chain)


def test_last_exon_large_truncation_yields_strong():
    card = assess_pvs1(
        consequence_profile=_profile(protein_position=400),
        pvs1_facts=_facts(
            transcript={"biotype": "protein_coding", "exon": "10/10"},
            protein={"position": 400, "length": 800},
        ),
    )
    assert card.strength == "PVS1_Strong"
    assert any(">10%" in step for step in card.provenance_chain)


def test_last_exon_small_truncation_yields_moderate():
    card = assess_pvs1(
        consequence_profile=_profile(protein_position=770),
        pvs1_facts=_facts(
            transcript={"biotype": "protein_coding", "exon": "10/10"},
            protein={"position": 770, "length": 800},
        ),
    )
    assert card.strength == "PVS1_Moderate"


def test_last_exon_unknown_length_conservatively_moderate():
    card = assess_pvs1(
        consequence_profile=_profile(),
        pvs1_facts=_facts(
            transcript={"biotype": "protein_coding", "exon": "10/10"},
            protein={"position": 770, "length": None},
        ),
    )
    assert card.strength == "PVS1_Moderate"
    assert any("protein length unavailable" in step for step in card.provenance_chain)


def test_missing_mechanism_fails_closed():
    card = assess_pvs1(consequence_profile=_profile(), pvs1_facts={})
    assert card.strength == "not_assessed"
    assert any("mechanism not established" in step for step in card.provenance_chain)


def test_non_lof_mechanism_is_not_applicable():
    card = assess_pvs1(
        consequence_profile=_profile(),
        pvs1_facts=_facts(
            lof_mechanism={"value": "gain_of_function", "source": "document_fact"}
        ),
    )
    assert card.strength == "not_applicable"


def test_document_fact_lof_mechanism_value_establishes_mechanism():
    card = assess_pvs1(
        consequence_profile=_profile(),
        pvs1_facts=_facts(
            lof_mechanism={"value": "haploinsufficiency", "source": "document_fact"}
        ),
    )
    assert card.strength == "PVS1"


def test_cspec_contract_establishes_mechanism_without_facts():
    facts = _facts()
    facts.pop("lof_mechanism")
    card = assess_pvs1(
        consequence_profile=_profile(),
        pvs1_facts=facts,
        rule_override=_cspec_override(lof_mechanism_established=True),
    )
    assert card.strength == "PVS1"
    assert "cspec_contract_applied" in card.input_values


def test_non_coding_biotype_fails_closed():
    card = assess_pvs1(
        consequence_profile=_profile(),
        pvs1_facts=_facts(
            transcript={"biotype": "nonsense_mediated_decay", "exon": "3/10"}
        ),
    )
    assert card.strength == "not_assessed"
    assert any("biotype" in step for step in card.provenance_chain)


def test_missing_exon_position_fails_closed():
    card = assess_pvs1(
        consequence_profile=_profile(),
        pvs1_facts=_facts(transcript={"biotype": "protein_coding"}),
    )
    assert card.strength == "not_assessed"
    assert any("exon position unavailable" in step for step in card.provenance_chain)


def test_canonical_splice_default_is_conservative_strong():
    profile = _profile(
        selected_transcript_terms=["splice_donor_variant"],
        protein_effect="unresolved",
        splice_class="canonical",
        splice_position=1,
        canonical_site_type="donor",
        canonical_motif_effect="disrupted",
        hgvs_operation="substitution",
    )
    facts = _facts(spliceai_profile=_splice_profile("donor", 0.62))
    card = assess_pvs1(consequence_profile=profile, pvs1_facts=facts)
    assert card.strength == "PVS1_Strong"
    assert any("applicable threshold (>=0.5)" in step for step in card.provenance_chain)


def test_canonical_splice_low_spliceai_downgrades():
    profile = _profile(
        selected_transcript_terms=["splice_acceptor_variant"],
        protein_effect="unresolved",
        splice_class="canonical",
        splice_position=-2,
        canonical_site_type="acceptor",
        canonical_motif_effect="disrupted",
        hgvs_operation="substitution",
    )
    card = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(spliceai_profile=_splice_profile("acceptor", 0.1)),
    )
    assert card.strength == "PVS1_Moderate"
    assert any("0.5 interpretation threshold" in step for step in card.provenance_chain)


def test_canonical_donor_uses_ds_dl_not_four_channel_maximum():
    profile = _profile(
        selected_transcript_terms=["splice_donor_variant"],
        protein_effect="unresolved",
        splice_class="canonical",
        splice_position=1,
        canonical_site_type="donor",
        canonical_motif_effect="disrupted",
        hgvs_operation="substitution",
    )
    spliceai = _splice_profile("donor", 0.02, other_score=0.22)
    card = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(spliceai_profile=spliceai),
    )

    assert spliceai["max_delta_score"] == 0.22
    assert card.strength == "PVS1_Moderate"
    assert any("DS_DL=0.02" in step for step in card.provenance_chain)


def test_collector_pvs1_facts_preserve_profile_and_native_loss_channel():
    profile = _profile(
        selected_transcript_terms=["splice_donor_variant"],
        protein_effect="unresolved",
        splice_class="canonical",
        splice_position=1,
        canonical_site_type="donor",
        canonical_motif_effect="disrupted",
        hgvs_operation="substitution",
    )
    source_profile = _splice_profile("none", 0.0, other_score=0.22)
    source_profile["canonical_site_type"] = "none"
    source_profile["native_loss_channel"] = None
    source_profile["native_loss_score"] = None
    fact = SourceFact(
        fact_id="spliceai-ready",
        tool_name="SpliceAI_predict_splice",
        status="success",
        query_identity={"gene": "GENE1"},
        result_identity={"gene": "GENE1"},
        identity_verified=True,
        features={"spliceai_profile": source_profile},
        raw_result_hash="fixture",
        assessment_ready=True,
    )

    facts, fact_ids = ACMGEvidencePipeline._pvs1_facts(
        profile,
        {fact.fact_id: fact},
    )

    assert fact_ids == ["spliceai-ready"]
    assert facts["spliceai_profile"]["canonical_site_type"] == "donor"
    assert facts["spliceai_profile"]["native_loss_channel"] == "DS_DL"
    assert facts["spliceai_profile"]["native_loss_score"] == 0.0
    assert facts["spliceai_profile"]["max_delta_score"] == 0.22


def test_collector_binds_spliceai_loss_dp_to_selected_transcript_exon_boundary():
    profile = _profile(
        selected_transcript="NM_000142.5",
        selected_transcript_terms=["splice_donor_variant"],
        protein_effect="unresolved",
        splice_class="canonical",
        splice_position=2,
        canonical_site_type="donor",
        canonical_motif_effect="disrupted",
        hgvs_operation="substitution",
        hgvs_c="NM_000142.5:c.1075+2T>A",
        genomic_position=1002,
    )
    source_profile = _splice_profile("none", 0.0)
    source_profile["delta_scores"]["DS_DL"] = 0.91
    source_profile["delta_positions"]["DP_DL"] = -2
    source_profile["max_delta_score"] = 0.91
    source_profile["max_delta_channels"] = ["DS_DL"]
    source_profile["max_delta_events"] = ["donor_loss"]
    vep = SourceFact(
        fact_id="vep-ready",
        tool_name="EnsemblVEP_annotate_hgvs",
        status="success",
        query_identity={"gene": "FGFR3"},
        result_identity={"gene": "FGFR3"},
        identity_verified=True,
        features={
            "vep_transcript_candidates": [
                {
                    "transcript": "ENST00000440486.7",
                    "mane_select": "NM_000142.5",
                    "exon": "3/10",
                    "biotype": "protein_coding",
                }
            ]
        },
        raw_result_hash="vep",
        assessment_ready=True,
    )
    lookup = SourceFact(
        fact_id="lookup-ready",
        tool_name="ensembl_lookup_gene",
        status="success",
        query_identity={"transcript": "ENST00000440486.7"},
        result_identity={"transcript": "ENST00000440486.7"},
        identity_verified=True,
        features={
            "exons": [
                {
                    "rank": 3,
                    "start": 900,
                    "end": 1000,
                    "strand": 1,
                }
            ]
        },
        raw_result_hash="lookup",
        assessment_ready=True,
    )
    splice = SourceFact(
        fact_id="splice-ready",
        tool_name="SpliceAI_predict_splice",
        status="success",
        query_identity={"gene": "FGFR3"},
        result_identity={"gene": "FGFR3"},
        identity_verified=True,
        features={"spliceai_profile": source_profile},
        raw_result_hash="splice",
        assessment_ready=True,
    )

    facts, fact_ids = ACMGEvidencePipeline._pvs1_facts(
        profile,
        {row.fact_id: row for row in (vep, lookup, splice)},
    )

    assert facts["transcript"]["canonical_site_position"] == 1000
    assert facts["spliceai_profile"]["native_loss_event_coordinate"] == 1000
    assert facts["spliceai_profile"]["expected_native_loss_position"] == -2
    assert (
        facts["spliceai_profile"]["native_loss_position_status"]
        == "exact_selected_transcript_site"
    )
    assert facts["spliceai_profile"]["native_loss_supported"] is True
    assert {"vep-ready", "lookup-ready", "splice-ready"} <= set(fact_ids)


def test_canonical_duplication_uses_selected_transcript_spliceai_before_rna_or_cspec():
    profile = _profile(
        selected_transcript_terms=["splice_donor_variant"],
        protein_effect="unresolved",
        splice_class="canonical",
        splice_position=1,
        splice_positions=[1, 2],
        canonical_site_type="donor",
        canonical_motif_effect="potentially_preserved",
        hgvs_operation="duplication",
    )
    facts = _facts(
        spliceai_profile=_splice_profile(
            "donor",
            0.02,
            other_score=0.22,
            variant_position=1000,
            canonical_site_position=1000,
        )
    )

    unresolved = assess_pvs1(consequence_profile=profile, pvs1_facts=facts)
    predicted_loss = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(
            spliceai_profile=_splice_profile(
                "donor",
                0.72,
                variant_position=1000,
                canonical_site_position=1000,
            )
        ),
    )
    cspec = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=facts,
        rule_override=_cspec_override(
            variant_types=["duplication"],
            predicted_frame_outcome="disrupts_reading_frame",
        ),
    )
    rna = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(
            spliceai_profile=facts["spliceai_profile"],
            rna_evidence={"outcome": "lof_confirmed", "source": "document_fact"},
        ),
    )

    assert unresolved.strength == "not_assessed"
    assert any(
        "canonical_native_site_loss_not_predicted" in step
        for step in unresolved.provenance_chain
    )
    assert predicted_loss.strength == "PVS1_Strong"
    assert any(
        "selected-transcript SpliceAI predicts canonical donor loss" in step
        for step in predicted_loss.provenance_chain
    )
    assert cspec.strength == "PVS1"
    assert rna.strength == "PVS1"


def test_plus_2_t_to_c_uses_point_8_threshold_and_dp_window():
    profile = _profile(
        selected_transcript_terms=["splice_donor_variant"],
        protein_effect="unresolved",
        splice_class="canonical",
        splice_position=2,
        canonical_site_type="donor",
        canonical_motif_effect="disrupted",
        hgvs_operation="substitution",
        hgvs_c="NM_000142.5:c.1075+2T>C",
    )
    below = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(
            spliceai_profile=_splice_profile(
                "donor",
                0.79,
                hgvs_c=profile["hgvs_c"],
            )
        ),
    )
    supported = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(
            spliceai_profile=_splice_profile(
                "donor",
                0.81,
                loss_position=-2,
                hgvs_c=profile["hgvs_c"],
            )
        ),
    )
    outside = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(
            spliceai_profile=_splice_profile(
                "donor",
                0.95,
                loss_position=21,
                hgvs_c=profile["hgvs_c"],
            )
        ),
    )

    assert below.strength == "PVS1_Moderate"
    assert any(
        "0.8 interpretation threshold" in step for step in below.provenance_chain
    )
    assert supported.strength == "PVS1_Strong"
    assert any("DP=-2" in step for step in supported.provenance_chain)
    assert outside.strength == "not_assessed"
    assert any("does not bind" in step for step in outside.provenance_chain)


def test_canonical_splice_terminal_exon_downgrades():
    profile = _profile(
        selected_transcript_terms=["splice_donor_variant"],
        protein_effect="unresolved",
        splice_class="canonical",
        splice_position=1,
        canonical_site_type="donor",
        canonical_motif_effect="disrupted",
        hgvs_operation="substitution",
    )
    card = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(
            transcript={"biotype": "protein_coding", "exon": "10/10"},
            spliceai_profile=_splice_profile("donor", 0.8),
        ),
    )
    assert card.strength == "PVS1_Moderate"


def test_canonical_splice_rna_lof_restores_full_pvs1():
    profile = _profile(
        selected_transcript_terms=["splice_donor_variant"],
        protein_effect="unresolved",
        splice_class="canonical",
        splice_position=1,
    )
    card = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(
            spliceai_profile=_splice_profile("donor", 0.7),
            rna_evidence={"outcome": "lof_confirmed", "source": "document_fact"},
        ),
    )
    assert card.strength == "PVS1"


def test_canonical_splice_rna_no_lof_not_applicable():
    profile = _profile(
        selected_transcript_terms=["splice_donor_variant"],
        protein_effect="unresolved",
        splice_class="canonical",
        splice_position=1,
    )
    card = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(
            rna_evidence={"outcome": "in_frame_rescue", "source": "document_fact"}
        ),
    )
    assert card.strength == "not_applicable"


def test_start_lost_unknown_alternative_start_fails_closed():
    profile = _profile(
        selected_transcript_terms=["start_lost"],
        protein_effect="lof",
    )
    card = assess_pvs1(consequence_profile=profile, pvs1_facts=_facts())
    assert card.strength == "not_assessed"


def test_start_lost_official_tree_branches():
    profile = _profile(
        selected_transcript_terms=["start_lost"],
        protein_effect="lof",
    )
    alternative = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(),
        rule_override=_cspec_override(alternative_in_frame_start=True),
    )
    pathogenic_upstream = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(),
        rule_override=_cspec_override(
            alternative_in_frame_start=False,
            pathogenic_upstream_of_alternative_start=True,
        ),
    )
    no_pathogenic_upstream = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(),
        rule_override=_cspec_override(
            alternative_in_frame_start=False,
            pathogenic_upstream_of_alternative_start=False,
        ),
    )
    unknown_upstream = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(),
        rule_override=_cspec_override(alternative_in_frame_start=False),
    )
    assert alternative.strength == "not_applicable"
    assert pathogenic_upstream.strength == "PVS1_Moderate"
    assert no_pathogenic_upstream.strength == "PVS1_Supporting"
    assert unknown_upstream.strength == "PVS1_Supporting"


def test_escape_critical_region_is_strong_not_full_pvs1():
    card = assess_pvs1(
        consequence_profile=_profile(protein_position=770),
        pvs1_facts=_facts(
            transcript={"biotype": "protein_coding", "exon": "10/10"},
            protein={"position": 770, "length": 800},
        ),
        rule_override=_cspec_override(critical_exons=[10]),
    )
    assert card.strength == "PVS1_Strong"


def test_exon_lof_frequent_in_population_is_not_applicable():
    card = assess_pvs1(
        consequence_profile=_profile(protein_position=770),
        pvs1_facts=_facts(
            transcript={"biotype": "protein_coding", "exon": "10/10"},
            protein={"position": 770, "length": 800},
        ),
        rule_override=_cspec_override(exon_lof_frequent_in_population=True),
    )
    assert card.strength == "not_applicable"


def _escape_facts(**overrides):
    facts = _facts(
        transcript={"biotype": "protein_coding", "exon": "10/10"},
        protein={"position": 770, "length": 800},
    )
    facts.update(overrides)
    return facts


def _escape_profile():
    return _profile(protein_position=770)


def test_gnomad_exon_lof_frequency_gate():
    frequent = assess_pvs1(
        consequence_profile=_escape_profile(),
        pvs1_facts=_escape_facts(
            exon_context={
                "lof_variants": [
                    {
                        "variant_id": "4-100-A-T",
                        "consequence": "stop_gained",
                        "af_exome": 0.002,
                        "af_genome": None,
                        "homozygote_count_exome": 0,
                        "homozygote_count_genome": None,
                    }
                ]
            }
        ),
    )
    assert frequent.strength == "not_applicable"

    homozygous = assess_pvs1(
        consequence_profile=_escape_profile(),
        pvs1_facts=_escape_facts(
            exon_context={
                "lof_variants": [
                    {
                        "variant_id": "4-100-A-T",
                        "consequence": "frameshift_variant",
                        "af_exome": 0.0002,
                        "af_genome": None,
                        "homozygote_count_exome": 1,
                        "homozygote_count_genome": None,
                    }
                ]
            }
        ),
    )
    assert homozygous.strength == "not_applicable"

    rare = assess_pvs1(
        consequence_profile=_escape_profile(),
        pvs1_facts=_escape_facts(
            exon_context={
                "lof_variants": [
                    {
                        "variant_id": "4-100-A-T",
                        "consequence": "stop_gained",
                        "af_exome": 0.0002,
                        "af_genome": None,
                        "homozygote_count_exome": 0,
                        "homozygote_count_genome": None,
                    },
                    {
                        "variant_id": "4-101-G-C",
                        "consequence": "missense_variant",
                        "af_exome": 0.5,
                        "af_genome": None,
                        "homozygote_count_exome": 10,
                        "homozygote_count_genome": None,
                    },
                ]
            }
        ),
    )
    assert rare.strength == "PVS1_Moderate"


def test_gnomad_exon_lof_threshold_contract_override():
    card = assess_pvs1(
        consequence_profile=_escape_profile(),
        pvs1_facts=_escape_facts(
            exon_context={
                "lof_variants": [
                    {
                        "variant_id": "4-100-A-T",
                        "consequence": "stop_gained",
                        "af_exome": 0.0002,
                        "af_genome": None,
                        "homozygote_count_exome": 0,
                        "homozygote_count_genome": None,
                    }
                ]
            }
        ),
        rule_override=_cspec_override(exon_lof_frequent_af_threshold=0.0001),
    )
    assert card.strength == "not_applicable"


def test_uniprot_critical_feature_overlap_is_strong():
    critical = assess_pvs1(
        consequence_profile=_escape_profile(),
        pvs1_facts=_escape_facts(
            critical_region={
                "overlapping_features": [
                    {
                        "type": "ACT_SITE",
                        "position_start": 775,
                        "position_end": 780,
                        "description": "active site",
                    }
                ],
                "source": "uniprot_features",
            }
        ),
    )
    assert critical.strength == "PVS1_Strong"
    assert any("ACT_SITE" in step for step in critical.provenance_chain)

    domain_only = assess_pvs1(
        consequence_profile=_escape_profile(),
        pvs1_facts=_escape_facts(
            critical_region={
                "overlapping_features": [
                    {
                        "type": "DOMAIN",
                        "position_start": 700,
                        "position_end": 800,
                        "description": "kinase domain",
                    }
                ],
                "source": "uniprot_features",
            }
        ),
    )
    assert domain_only.strength == "PVS1_Moderate"


def test_splice_frame_disrupts_nmd_predicted_yields_full_pvs1():
    profile = _profile(
        selected_transcript_terms=["splice_donor_variant"],
        protein_effect="unresolved",
        splice_class="canonical",
        splice_position=1,
    )
    card = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(spliceai_profile=_splice_profile("donor", 0.7)),
        rule_override=_cspec_override(predicted_frame_outcome="disrupts_reading_frame"),
    )
    assert card.strength == "PVS1"


def test_splice_frame_disrupts_escape_uses_fraction():
    profile = _profile(
        selected_transcript_terms=["splice_donor_variant"],
        protein_effect="unresolved",
        splice_class="canonical",
        splice_position=1,
        protein_position=400,
    )
    card = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(
            transcript={"biotype": "protein_coding", "exon": "10/10"},
            protein={"position": 400, "length": 800},
        ),
        rule_override=_cspec_override(predicted_frame_outcome="disrupts_reading_frame"),
    )
    assert card.strength == "PVS1_Strong"


def test_splice_frame_preserves_uses_fraction_and_critical_region():
    profile = _profile(
        selected_transcript_terms=["splice_acceptor_variant"],
        protein_effect="unresolved",
        splice_class="canonical",
        splice_position=-2,
        protein_position=770,
    )
    small = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(protein={"position": 770, "length": 800}),
        rule_override=_cspec_override(
            predicted_frame_outcome="preserves_reading_frame"
        ),
    )
    critical = assess_pvs1(
        consequence_profile=profile,
        pvs1_facts=_facts(protein={"position": 770, "length": 800}),
        rule_override=_cspec_override(
            predicted_frame_outcome="preserves_reading_frame", critical_exons=[3]
        ),
    )
    assert small.strength == "PVS1_Moderate"
    assert critical.strength == "PVS1_Strong"


def test_strength_ceiling_and_rescue_transcript_adjustments():
    capped = assess_pvs1(
        consequence_profile=_profile(),
        pvs1_facts=_facts(),
        rule_override=_cspec_override(strength_ceiling="PVS1_Moderate"),
    )
    rescued = assess_pvs1(
        consequence_profile=_profile(),
        pvs1_facts=_facts(),
        rule_override=_cspec_override(rescue_transcript_known=True),
    )
    absent = assess_pvs1(
        consequence_profile=_profile(),
        pvs1_facts=_facts(),
        rule_override=_cspec_override(exon_absent_from_relevant_transcripts=True),
    )
    assert capped.strength == "PVS1_Moderate"
    assert rescued.strength == "not_applicable"
    assert absent.strength == "not_applicable"


def test_non_applicable_consequence():
    profile = _profile(
        protein_effect="missense", selected_transcript_terms=["missense_variant"]
    )
    card = assess_pvs1(consequence_profile=profile, pvs1_facts=_facts())
    assert card.strength == "not_applicable"


def test_functional_evidence_integrates_tree():
    cards = functional_evidence(
        consequence_profile=_profile(),
        pvs1_facts=_facts(),
    )
    card = next(row for row in cards if row.criterion == "PVS1")
    assert card.strength == "PVS1"


def test_functional_evidence_without_facts_fails_closed():
    cards = functional_evidence(consequence_profile=_profile())
    card = next(row for row in cards if row.criterion == "PVS1")
    assert card.strength == "not_assessed"


def test_removed_boolean_shortcuts_are_rejected():
    with pytest.raises(TypeError):
        functional_evidence(
            variant_type="frameshift_variant",
            gene_lof_mechanism=True,
            biologically_relevant_transcript=True,
            pvs1_decision_complete=True,
            predicted_nmd=True,
        )


def test_validity_and_constraint_are_context_not_lof_mechanism_proof():
    confirmed = infer_mechanism_from_population_facts(
        [{"gene_disease_validity": "Definitive"}], {"pli": 0.98, "loeuf": 0.21}
    )
    assert confirmed["established"] is None
    assert confirmed["lof_intolerant"] is True
    assert confirmed["source"] == "clingen_gnomad_review_context"
    tolerant = infer_mechanism_from_population_facts(
        [{"gene_disease_validity": "Definitive"}], {"pli": 0.1, "loeuf": 1.4}
    )
    assert tolerant["established"] is None
    limited = infer_mechanism_from_population_facts(
        [{"gene_disease_validity": "Limited"}], {"pli": 0.98}
    )
    assert limited["established"] is None
    missing = infer_mechanism_from_population_facts([], {})
    assert missing["established"] is None


def test_pvs1_strengths_are_eligible_for_preview_with_tavtigian_odds():
    for strength, odds in (
        ("PVS1", 350.0),
        ("PVS1_Strong", 18.7),
        ("PVS1_Moderate", 4.3),
        ("PVS1_Supporting", 2.08),
    ):
        assert rule_allows_system_preview_strength(
            "PVS1", strength, rule_id="clingen-svi-pvs1", rule_version="1.2"
        )
        assert (
            bayesian_odds_for_output(
                "PVS1", strength, rule_id="clingen-svi-pvs1", rule_version="1.2"
            )
            == odds
        )
    assert not rule_allows_system_preview_strength(
        "PVS1", "not_assessed", rule_id="clingen-svi-pvs1", rule_version="1.2"
    )
