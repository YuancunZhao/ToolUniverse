"""EvidenceCard v3 display, automatic, and verified calculation semantics."""

from __future__ import annotations

from tooluniverse.acmg.models import (
    EvidenceCard,
    evidence_cards_to_result,
    is_automatic_evidence,
    is_verified_evidence,
)


def _card(
    criterion: str,
    strength: str,
    *,
    evidence_status: str = "source_backed_candidate",
    source: bool = True,
    verified: bool = False,
) -> EvidenceCard:
    return EvidenceCard(
        criterion=criterion,
        strength=strength,
        evidence_status=evidence_status,
        source_label="fixture",
        observed_facts={},
        rule_basis="fixture rule",
        provenance_chain=["fixture"],
        source_fact_ids=["source-1"] if source else [],
        rule_source={
            "type": "versioned_svi" if verified else "generic_acmg_candidate",
            "rule_id": "fixture-rule",
            "version": "1",
        },
        verification_dimensions={
            "identity_status": "matched",
            "source_status": "available",
            "extraction_status": "structured" if verified else "unresolved",
            "version_status": "versioned" if verified else "unversioned",
            "disease_match_status": "unspecified",
            "independence_status": "unknown",
        },
    )


def test_source_backed_candidate_enters_automatic_not_verified_estimate():
    row = evidence_cards_to_result(
        [_card("PM2", "PM2_Supporting")],
        known_source_fact_ids={"source-1"},
        verified_source_fact_ids=set(),
    )["evidence_cards"][0]

    assert row["evidence_status"] == "source_backed_candidate"
    assert row["calculation_roles"] == {
        "automatic": True,
        "verified": False,
        "user_selected": False,
    }


def test_versioned_rule_with_verified_fact_enters_both_estimates():
    row = evidence_cards_to_result(
        [_card("PP3", "PP3_Supporting", evidence_status="rule_mapped", verified=True)],
        known_source_fact_ids={"source-1"},
        verified_source_fact_ids={"source-1"},
    )["evidence_cards"][0]

    assert row["calculation_roles"]["automatic"] is True
    assert row["calculation_roles"]["verified"] is True


def test_hard_verification_error_keeps_card_visible_but_excludes_calculation():
    card = _card("PS4", "PS4_Supporting")
    card.verification_dimensions["extraction_status"] = "contradicted"
    row = evidence_cards_to_result([card], known_source_fact_ids={"source-1"})[
        "evidence_cards"
    ][0]

    assert row["calculation_roles"]["automatic"] is False
    assert row["calculation_roles"]["verified"] is False


def test_empty_placeholder_card_is_not_serialized():
    card = EvidenceCard(
        criterion="PM1",
        strength="not_assessed",
        source_label="fixture",
        observed_facts={},
        rule_basis="fixture",
    )
    assert evidence_cards_to_result([card])["evidence_cards"] == []


def test_explicit_bad_atom_remains_visible_as_excluded_card():
    card = EvidenceCard(
        criterion="PM3",
        strength="not_assessed",
        evidence_status="excluded",
        exclusion_reason="duplicate_case",
        source_label="fixture",
        observed_facts={},
        rule_basis="fixture",
        source_fact_ids=["source-1"],
    )
    row = evidence_cards_to_result([card], known_source_fact_ids={"source-1"})[
        "evidence_cards"
    ][0]
    assert row["evidence_status"] == "excluded"
    assert row["calculation_roles"]["automatic"] is False


def test_serialized_card_id_is_v3_and_stable():
    first = evidence_cards_to_result(
        [_card("PM2", "PM2_Supporting")], known_source_fact_ids={"source-1"}
    )["evidence_cards"][0]
    second = evidence_cards_to_result(
        [_card("PM2", "PM2_Supporting")], known_source_fact_ids={"source-1"}
    )["evidence_cards"][0]
    assert first["card_id"] == second["card_id"]
    assert first["card_id"].startswith("acmg-card:v4:")
    assert {
        "assessment_status",
        "suggested_criterion",
        "suggested_strength",
        "effective_strength",
    }.isdisjoint(first)


def test_shared_predicates_require_real_source_ids_and_legal_strength():
    row = evidence_cards_to_result(
        [_card("PP3", "PP3_Supporting", evidence_status="rule_mapped", verified=True)],
        known_source_fact_ids={"source-1"},
        verified_source_fact_ids={"source-1"},
    )["evidence_cards"][0]
    assert is_automatic_evidence(row, known_source_fact_ids={"source-1"}) is True
    assert is_verified_evidence(row, verified_source_fact_ids={"source-1"}) is True
    assert is_automatic_evidence(row, known_source_fact_ids=set()) is False
    assert (
        is_automatic_evidence(
            {**row, "strength": "arbitrary_strength"},
            known_source_fact_ids={"source-1"},
        )
        is False
    )
