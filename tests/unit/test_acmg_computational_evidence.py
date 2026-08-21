"""EvidenceCard computational evidence policy tests."""

from __future__ import annotations

import pytest

from tooluniverse.acmg.computational import computational_evidence
from tooluniverse.acmg.models import evidence_cards_to_result
from tooluniverse.tools.ACMG_computational_evidence import ACMG_computational_evidence


def _pp3_bp4_card(**kwargs):
    return next(
        card
        for card in computational_evidence(variant_type="missense_variant", **kwargs)
        if card.criterion in {"PP3/BP4", "PP3", "BP4"}
    )


def _walker_metadata(score: float) -> dict:
    row = {
        "gene": "GENE1",
        "transcript": "NM_000001.1",
        "DS_AG": score,
        "DS_AL": 0.0,
        "DS_DG": 0.0,
        "DS_DL": 0.0,
        "DP_AG": 3,
        "DP_AL": 0,
        "DP_DG": 0,
        "DP_DL": 0,
    }
    return {
        "model_version": "1.3.1",
        "annotation_version": "MANE fixture release",
        "score_mode": "raw",
        "distance": 500,
        "mask": False,
        "transcript_set": "MANE",
        "selected_transcript": "NM_000001.1",
        "selected_gene": "GENE1",
        "selected_score_row": row,
    }


@pytest.mark.parametrize(
    ("revel_score", "strength"),
    [
        (0.70, "PP3_Supporting"),
        (0.80, "PP3_Moderate"),
        (0.932, "PP3_Strong"),
    ],
)
def test_revel_pathogenic_intervals(revel_score, strength):
    card = _pp3_bp4_card(revel_score=revel_score)

    assert card.criterion == "PP3"
    assert card.strength == strength


@pytest.mark.parametrize(
    ("revel_score", "strength"),
    [
        (0.003, "BP4_VeryStrong"),
        (0.010, "BP4_Strong"),
        (0.10, "BP4_Moderate"),
        (0.20, "BP4_Supporting"),
    ],
)
def test_revel_benign_intervals(revel_score, strength):
    card = _pp3_bp4_card(revel_score=revel_score)

    assert card.criterion == "BP4"
    assert card.strength == strength


def test_revel_neutral_interval_is_not_in_preview():
    cards = computational_evidence(revel_score=0.50)
    card = _pp3_bp4_card(revel_score=0.50)

    assert card.strength == "not_met"
    assert all(
        not row["calculation_roles"]["automatic"]
        for row in evidence_cards_to_result(cards)["evidence_cards"]
    )


def test_missing_default_revel_score_is_not_assessed():
    card = _pp3_bp4_card()

    assert card.criterion == "PP3/BP4"
    assert card.strength == "not_assessed"


def test_cadd_is_retained_as_audit_but_cannot_replace_revel():
    result = ACMG_computational_evidence(
        cadd_phred=26.0,
        variant_type="missense_variant",
    )

    assert result["evidence_cards"] == []
    raw = _pp3_bp4_card(cadd_phred=26.0)
    assert raw.observed_facts["cadd_phred"] == 26.0
    assert raw.strength == "not_assessed"


def test_unselected_non_revel_score_does_not_enter_preview():
    cards = computational_evidence(cadd_phred=30.0, spliceai_max_delta=0.9)
    card = _pp3_bp4_card(cadd_phred=30.0, spliceai_max_delta=0.9)

    assert card.strength == "not_assessed"
    assert all(
        not row["calculation_roles"]["automatic"]
        for row in evidence_cards_to_result(cards)["evidence_cards"]
    )


def test_canonical_splice_profile_emits_review_only_pvs1_route():
    cards = computational_evidence(
        spliceai_max_delta=0.9,
        consequence_profile={
            "status": "resolved",
            "protein_effect": "noncoding",
            "splice_class": "canonical",
            "splice_position": 1,
            "selected_transcript_terms": ["splice_donor_variant"],
        },
    )

    assert next(card for card in cards if card.criterion == "PVS1").strength == (
        "not_assessed"
    )
    splice_card = next(card for card in cards if card.source_label == "SpliceAI")
    assert splice_card.strength == "not_assessed"


@pytest.mark.parametrize(
    ("score", "criterion", "strength"),
    [
        (0.20, "PP3", "PP3_Supporting"),
        (0.10, "BP4", "BP4_Supporting"),
        (0.100001, "PP3/BP4", "not_met"),
        (0.199999, "PP3/BP4", "not_met"),
        (0.15, "PP3/BP4", "not_met"),
    ],
)
def test_spliceai_general_svi_candidate_boundaries(score, criterion, strength):
    cards = computational_evidence(
        spliceai_max_delta=score,
        spliceai_scores=_walker_metadata(score)["selected_score_row"],
        spliceai_run_metadata=_walker_metadata(score),
        consequence_terms=["intron_variant", "splice_region_variant"],
        hgvs_c="NM_000001.1:c.100+5A>G",
        variant_type="intron_variant",
    )

    card = next(card for card in cards if card.source_label == "SpliceAI")
    assert card.criterion == criterion
    assert card.strength == strength
    assert card.observed_facts["spliceai_scores"]["DS_AG"] == score
    assert card.observed_facts["spliceai_profile"]["max_delta_channels"] == ["DS_AG"]


def test_missense_keeps_revel_and_spliceai_as_separate_candidates():
    cards = computational_evidence(
        revel_score=0.80,
        spliceai_max_delta=0.25,
        spliceai_scores={"DS_AG": 0.25, "DP_AG": 3},
        spliceai_run_metadata=_walker_metadata(0.25),
        consequence_terms=["missense_variant", "splice_region_variant"],
        hgvs_c="NM_000001.1:c.100+5A>G",
        variant_type="missense_variant",
    )

    assert [(card.source_label, card.criterion) for card in cards] == [
        ("REVEL", "PP3"),
        ("SpliceAI", "PP3"),
    ]


def test_spliceai_reports_all_delta_channels_and_trigger_event():
    metadata = _walker_metadata(0.0)
    metadata["selected_score_row"].update(
        {"DS_AG": 0.0, "DS_AL": 0.22, "DS_DG": 0.20, "DS_DL": 0.02}
    )
    cards = computational_evidence(
        spliceai_max_delta=0.22,
        spliceai_scores=metadata["selected_score_row"],
        spliceai_run_metadata=metadata,
        consequence_terms=["intron_variant", "splice_region_variant"],
        hgvs_c="NM_000001.1:c.100+5A>G",
        variant_type="intron_variant",
    )

    card = next(card for card in cards if card.source_label == "SpliceAI")
    profile = card.observed_facts["spliceai_profile"]
    assert card.strength == "PP3_Supporting"
    assert profile["delta_scores"] == {
        "DS_AG": 0.0,
        "DS_AL": 0.22,
        "DS_DG": 0.20,
        "DS_DL": 0.02,
    }
    assert profile["max_delta_events"] == ["acceptor_loss"]


def test_spliceai_scalar_only_is_audit_only_and_conflicts_fail_closed():
    scalar_only = computational_evidence(
        spliceai_max_delta=0.25,
        consequence_terms=["intron_variant"],
        variant_type="intron_variant",
    )
    metadata = _walker_metadata(0.25)
    conflicting = computational_evidence(
        spliceai_max_delta=0.9,
        spliceai_scores=metadata["selected_score_row"],
        spliceai_run_metadata=metadata,
        consequence_terms=["intron_variant"],
        variant_type="intron_variant",
    )

    scalar_card = next(card for card in scalar_only if card.source_label == "SpliceAI")
    conflict_card = next(
        card for card in conflicting if card.source_label == "SpliceAI"
    )
    assert scalar_card.strength == "not_assessed"
    assert scalar_card.observed_facts["spliceai_profile"]["status"] == "unavailable"
    assert conflict_card.strength == "not_assessed"
    assert conflict_card.observed_facts["spliceai_profile"]["status"] == "conflicting"


@pytest.mark.parametrize(
    "missing_key",
    [
        "model_version",
        "annotation_version",
        "score_mode",
        "distance",
        "mask",
        "transcript_set",
        "selected_transcript",
        "selected_gene",
        "selected_score_row",
    ],
)
def test_spliceai_missing_walker_metadata_is_not_assessed(missing_key):
    metadata = _walker_metadata(0.25)
    metadata.pop(missing_key)
    cards = computational_evidence(
        spliceai_max_delta=0.25,
        spliceai_scores=_walker_metadata(0.25)["selected_score_row"],
        spliceai_run_metadata=metadata,
        consequence_terms=["intron_variant"],
        variant_type="intron_variant",
    )

    card = next(card for card in cards if card.source_label == "SpliceAI")
    assert card.strength == "not_assessed"


def test_internal_synonymous_variant_can_use_strict_walker_path():
    cards = computational_evidence(
        spliceai_max_delta=0.20,
        spliceai_scores=_walker_metadata(0.20)["selected_score_row"],
        spliceai_run_metadata=_walker_metadata(0.20),
        consequence_profile={
            "status": "resolved",
            "protein_effect": "synonymous",
            "splice_class": "none",
            "splice_position": None,
            "selected_transcript_terms": ["synonymous_variant"],
            "is_small_variant": True,
        },
    )

    card = next(card for card in cards if card.source_label == "SpliceAI")
    assert (card.criterion, card.strength) == ("PP3", "PP3_Supporting")


def test_bp7_supporting_follows_walker_bp4_for_synonymous_variant():
    cards = computational_evidence(
        spliceai_max_delta=0.10,
        spliceai_scores=_walker_metadata(0.10)["selected_score_row"],
        spliceai_run_metadata=_walker_metadata(0.10),
        consequence_profile={
            "status": "resolved",
            "protein_effect": "synonymous",
            "splice_class": "none",
            "splice_position": None,
            "selected_transcript_terms": ["synonymous_variant"],
            "is_small_variant": True,
        },
    )

    assert [
        (card.criterion, card.strength)
        for card in cards
        if card.source_label == "SpliceAI"
    ] == [
        ("BP4", "BP4_Supporting"),
        ("BP7", "BP7_Supporting"),
    ]


@pytest.mark.parametrize(
    ("position", "bp7_expected"),
    [(8, True), (-22, True), (7, False), (-21, False)],
)
def test_bp7_deep_intronic_boundaries(position, bp7_expected):
    cards = computational_evidence(
        spliceai_max_delta=0.10,
        spliceai_scores=_walker_metadata(0.10)["selected_score_row"],
        spliceai_run_metadata=_walker_metadata(0.10),
        consequence_profile={
            "status": "resolved",
            "protein_effect": "noncoding",
            "splice_class": "noncanonical",
            "splice_position": position,
            "selected_transcript_terms": ["intron_variant"],
            "is_small_variant": True,
        },
    )

    assert any(card.criterion == "BP7" for card in cards) is bp7_expected


def test_canonical_derived_context_emits_only_pvs1_route():
    cards = computational_evidence(
        spliceai_max_delta=0.9,
        splice_context={
            "applicable": True,
            "derived_from": "VariantValidator and EnsemblVEP consequence",
            "splice_position": 1,
            "consequence_terms": ["splice_donor_variant"],
        },
        variant_type="splice_donor_variant",
    )

    splice_card = next(card for card in cards if card.source_label == "SpliceAI")
    assert splice_card.strength == "not_assessed"
    assert (
        next(card for card in cards if card.criterion == "PVS1").strength
        == "not_assessed"
    )


def test_locally_reviewed_cspec_can_override_revel_threshold():
    contract = {
        "specification_id": "fixture-cspec",
        "rule_id": "fixture-cspec-rule",
        "version": "1.0",
        "primary_reference": "https://example.test/cspec",
        "criteria": {
            "PP3": {
                "predictor": "REVEL",
                "threshold": 0.7,
                "operator": ">=",
                "strength": "PP3_Moderate",
                "variant_types": ["missense_variant"],
            }
        },
    }
    card = _pp3_bp4_card(revel_score=0.72, rule_override=contract)

    assert card.strength == "PP3_Moderate"
    assert card.rule_id == "fixture-cspec-rule"
    assert (
        card.observed_facts["cspec_contract_applied"]["specification_id"]
        == "fixture-cspec"
    )
