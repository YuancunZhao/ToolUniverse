"""EvidenceCard serialization semantics for ACMG evidence tools."""

from __future__ import annotations

from tooluniverse.acmg.models import (
    EvidenceCard,
    evidence_cards_to_result,
    is_candidate_evidence,
)


def _card(criterion: str, strength: str, *, trusted: bool = False) -> EvidenceCard:
    return EvidenceCard(
        card_id=f"{criterion}-{strength}",
        criterion=criterion,
        strength=strength,
        input_source="fixture",
        input_values={},
        clinvar_rule_applied="fixture rule",
        provenance_chain=["fixture"],
        overlay_validated=trusted,
        source_fact_ids=["source-1"] if trusted else [],
    )


def test_only_met_source_backed_pm2_is_system_preview_eligible():
    result = evidence_cards_to_result(
        [
            _card("BA1", "not_met"),
            _card("PM2", "not_assessed"),
            _card("PM2", "PM2_Supporting", trusted=True),
        ],
        trusted_source_fact_ids={"source-1"},
    )

    assert [
        c["system_preview_included"] for c in result["evidence_cards"]
    ] == [False, False, True]


def test_review_cards_cannot_enter_preview_without_a_trusted_source_fact():
    result = evidence_cards_to_result([_card("PM2", "PM2_Supporting")])

    assert result["evidence_cards"][0]["system_preview_included"] is False
    assert result["evidence_cards"][0]["overlay_validated"] is False


def test_unresolved_source_backed_suggestion_enters_broad_not_validated_preview():
    card = _card("PM2", "not_assessed")
    card.source_fact_ids = ["source-1"]
    card.suggested_criterion = "PM2"
    card.suggested_strength = "PM2_Supporting"
    card.proposal_status = "requires_user_review"
    card.rule_verification = "generic_svi"
    card.rule_mapping_status = "llm_review_required"
    card.verification_status = "unresolved"

    row = evidence_cards_to_result(
        [card],
        trusted_source_fact_ids=set(),
        known_source_fact_ids={"source-1"},
    )["evidence_cards"][0]

    assert row["suggested_criterion"] == "PM2"
    assert row["suggested_strength"] == "PM2_Supporting"
    assert row["system_preview_included"] is True
    assert row["validated_subset_included"] is False
    assert row["preview_inclusion_basis"] == "source_backed_candidate"


def test_semantic_contradiction_cannot_be_inferred_as_strictly_verified():
    card = _card("PS4", "PS4_Supporting", trusted=True)
    card.proposal_status = "requires_user_review"
    card.rule_mapping_status = "llm_review_required"
    card.input_values = {
        "anchor_status": "verified",
        "semantic_status": "contradicted",
    }

    row = evidence_cards_to_result(
        [card],
        trusted_source_fact_ids={"source-1"},
        known_source_fact_ids={"source-1"},
    )["evidence_cards"][0]

    assert row["verification_status"] == "contradicted"
    assert row["system_preview_included"] is False
    assert row["validated_subset_included"] is False


def test_all_non_met_assessment_states_fail_closed():
    cards = [
        _card("PM2", "not_met"),
        _card("PP3", "not_assessed"),
        _card("PM1", "not_applicable"),
        _card("PP5", "deprecated"),
        _card("BP6", "deprecated"),
    ]

    result = evidence_cards_to_result(cards)

    assert [row["assessment_status"] for row in result["evidence_cards"]] == [
        "not_met",
        "not_assessed",
        "not_applicable",
        "deprecated",
        "deprecated",
    ]
    assert all(
        row["system_preview_included"] is False
        for row in result["evidence_cards"]
    )


def test_serialized_card_id_is_stable_for_same_evidence():
    first = evidence_cards_to_result([_card("PM2", "PM2_Supporting")])[
        "evidence_cards"
    ][0]
    second = evidence_cards_to_result([_card("PM2", "PM2_Supporting")])[
        "evidence_cards"
    ][0]

    assert first["card_id"] == second["card_id"]
    assert first["card_id"].startswith("acmg-card:v1:")


def test_shared_candidate_predicate_requires_status_and_source_facts():
    base = {
        "criterion": "PP3",
        "strength": "PP3_Supporting",
        "rule_id": "clingen-svi-pejaver-pp3-bp4",
        "rule_version": "2022",
        "assessment_status": "met",
        "system_preview_included": True,
        "overlay_validated": True,
        "source_fact_ids": ["fixture-source"],
    }
    trusted = {"fixture-source"}
    assert is_candidate_evidence(base, trusted_source_fact_ids=trusted) is True
    assert (
        is_candidate_evidence(
            {**base, "assessment_status": "not_assessed"},
            trusted_source_fact_ids=trusted,
        )
        is False
    )
    assert (
        is_candidate_evidence({**base, "source_fact_ids": []}, trusted_source_fact_ids=trusted)
        is False
    )
    assert (
        is_candidate_evidence(
            {**base, "system_preview_included": "true"},
            trusted_source_fact_ids=trusted,
        )
        is False
    )
    assert (
        is_candidate_evidence(
            {**base, "strength": "arbitrary_strength"},
            trusted_source_fact_ids=trusted,
        )
        is False
    )
    assert (
        is_candidate_evidence(
            {**base, "rule_version": "forged"},
            trusted_source_fact_ids=trusted,
        )
        is False
    )
    assert is_candidate_evidence(base) is False
    assert (
        is_candidate_evidence(base, trusted_source_fact_ids={"different-source"})
        is False
    )
