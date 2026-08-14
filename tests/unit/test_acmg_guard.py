"""Fail-closed tests for the evidence-only ACMG v3 answer guard."""

from __future__ import annotations

from copy import deepcopy

from tooluniverse.acmg.guard import (
    GUARD_CONTEXT_SCHEMA_VERSION,
    guard_acmg_answer,
    guard_context_hash,
)
from tooluniverse.acmg.models import EvidenceCard, evidence_cards_to_result
from tooluniverse.acmg.runtime_manifest import ruleset_hash
from tooluniverse.acmg_runtime_tools import ACMGGuardFinalAnswerTool


def _candidate_pp3() -> dict:
    card = EvidenceCard(
        card_id="fixture",
        criterion="PP3",
        strength="PP3_Supporting",
        input_source="REVEL",
        input_values={"revel_score": 0.7},
        clinvar_rule_applied="ClinGen SVI Pejaver 2022",
        evidence_status="rule_mapped",
        strength_source="versioned_rule",
        rule_source={"type": "versioned_svi"},
        verification_dimensions={
            "identity_status": "matched",
            "source_status": "available",
            "extraction_status": "structured",
            "version_status": "versioned",
            "disease_match_status": "matched",
            "independence_status": "independent",
        },
        rule_id="clingen-svi-pejaver-pp3-bp4",
        rule_version="2022",
        source_fact_ids=["fixture-source"],
    )
    return evidence_cards_to_result(
        [card],
        known_source_fact_ids={"fixture-source"},
        verified_source_fact_ids={"fixture-source"},
    )["evidence_cards"][0]


def _context(card: dict | None = None) -> dict:
    row = deepcopy(card or _candidate_pp3())
    compact = {
        key: row.get(key)
        for key in (
            "card_id",
            "criterion",
            "strength",
            "evidence_status",
        )
    }
    compact["role"] = "verified"
    context = {
        "schema_version": GUARD_CONTEXT_SCHEMA_VERSION,
        "variant_identity_hash": "a" * 64,
        "ruleset_hash": ruleset_hash(),
        "claims": [compact],
    }
    context["context_hash"] = guard_context_hash(context)
    return context


def test_guard_accepts_source_backed_criterion_summary():
    result = guard_acmg_answer(
        "PP3 supporting evidence is present.",
        [_candidate_pp3()],
        known_source_fact_ids={"fixture-source"},
        verified_source_fact_ids={"fixture-source"},
    )
    assert result["status"] == "PASS"
    assert result["card_roles"][0]["role"] == "verified"


def test_guard_rejects_source_less_or_identity_conflicted_cards():
    source_less = {**_candidate_pp3(), "source_fact_ids": []}
    conflicted = deepcopy(_candidate_pp3())
    conflicted["verification_dimensions"]["identity_status"] = "conflict"
    for card in (source_less, conflicted):
        result = guard_acmg_answer(
            "PP3 supporting evidence is present.",
            [card],
            known_source_fact_ids={"fixture-source"},
        )
        assert result["status"] == "BLOCK"
        assert result["unsupported_codes"] == ["PP3"]


def test_runtime_guard_accepts_bare_source_backed_evidence_cards():
    result = ACMGGuardFinalAnswerTool({"name": "ACMG_guard_final_answer"}).run(
        {
            "final_answer_text": "PP3 is present as a source-backed card.",
            "evidence_cards": [_candidate_pp3()],
        }
    )

    assert result["status"] == "PASS"


def test_guard_allows_discussion_of_not_met_and_excluded_claims():
    for role, status in (("not_met", "not_met"), ("excluded", "excluded")):
        context = _context()
        context["claims"][0]["evidence_status"] = status
        context["claims"][0]["strength"] = "not_met"
        context["claims"][0]["role"] = role
        context["context_hash"] = guard_context_hash(context)
        result = ACMGGuardFinalAnswerTool({}).run(
            {
                "final_answer_text": "PP3 was not met in this result.",
                "guard_context": context,
            }
        )
        assert result["status"] == "PASS"
        assert result["card_roles"][0]["role"] == role


def test_guard_blocks_tool_owned_five_tier_labels():
    for label in (
        "This variant is Pathogenic with PP3.",
        "likely_pathogenic",
        "likely-pathogenic",
        "LIKELY   PATHOGENIC",
        "ＶＵＳ",
        "classification: P",
        "classification: B",
    ):
        result = guard_acmg_answer(
            label,
            [_candidate_pp3()],
            known_source_fact_ids={"fixture-source"},
        )
        assert result["status"] == "BLOCK", label


def test_guard_allows_attributed_external_vcep_assertion():
    result = guard_acmg_answer(
        "ClinGen VCEP classified this variant as Pathogenic; PP3 is reported here.",
        [_candidate_pp3()],
        known_source_fact_ids={"fixture-source"},
    )
    assert result["status"] == "PASS"


def test_guard_does_not_misread_protein_hgvs_p_value_or_group_b():
    result = guard_acmg_answer(
        (
            "PP3 remains a candidate for p.Arg249Gln; card "
            "acmg-card:v3:9b2cb01d1d06d28379a9, p-value=0.01, group B control."
        ),
        [_candidate_pp3()],
        known_source_fact_ids={"fixture-source"},
    )
    assert result["status"] == "PASS"


def test_guard_expands_combined_criterion_codes():
    card = deepcopy(_candidate_pp3())
    card["criterion"] = "PS2/PM6"
    card["strength"] = "PS2"
    card["rule_id"] = "clingen-svi-de-novo"
    result = guard_acmg_answer(
        "PS2 and PM6 are source-backed candidates.",
        [card],
        known_source_fact_ids={"fixture-source"},
    )
    assert result["status"] == "PASS"


def test_runtime_guard_uses_v3_source_facts_from_collector_result():
    collector_result = {
        "evidence_cards": [_candidate_pp3()],
        "source_facts": [
            {
                "fact_id": "fixture-source",
                "status": "success",
                "identity_status": "matched",
                "source_status": "available",
                "extraction_status": "structured",
                "version_status": "versioned",
                "disease_match_status": "matched",
                "independence_status": "independent",
            }
        ],
    }
    result = ACMGGuardFinalAnswerTool({"name": "ACMG_guard_final_answer"}).run(
        {"final_answer_text": "PP3", "collector_result": collector_result}
    )
    assert result["status"] == "PASS"


def test_runtime_guard_accepts_compact_guard_context():
    result = ACMGGuardFinalAnswerTool({"name": "ACMG_guard_final_answer"}).run(
        {"final_answer_text": "PP3 is a candidate.", "guard_context": _context()}
    )
    assert result["status"] == "PASS"


def test_runtime_guard_fails_closed_for_mutated_or_stale_context():
    base = _context()
    invalid_contexts = [
        {key: value for key, value in base.items() if key != "context_hash"},
        {**base, "schema_version": "stale"},
        {**base, "claims": [{**base["claims"][0], "criterion": "PS4"}]},
        {**base, "claims": [{**base["claims"][0], "role": "unknown"}]},
        ["not-an-object"],
    ]
    tool = ACMGGuardFinalAnswerTool({"name": "ACMG_guard_final_answer"})
    for context in invalid_contexts:
        result = tool.run({"final_answer_text": "PP3", "guard_context": context})
        assert result["status"] == "BLOCK"
        assert result["blocking_reasons"] == ["guard_context_invalid"]


def test_runtime_guard_rejects_rehashed_context_from_another_ruleset():
    context = _context()
    context["ruleset_hash"] = "b" * 64
    context["context_hash"] = guard_context_hash(context)
    result = ACMGGuardFinalAnswerTool({}).run(
        {"final_answer_text": "PP3 is a candidate.", "guard_context": context}
    )
    assert result["status"] == "BLOCK"
    assert "ruleset_hash" in result["guard_context_error"]


def test_runtime_guard_rejects_rehashed_duplicate_cards():
    context = _context()
    context["claims"] = [
        context["claims"][0],
        deepcopy(context["claims"][0]),
    ]
    context["context_hash"] = guard_context_hash(context)

    result = ACMGGuardFinalAnswerTool({}).run(
        {"final_answer_text": "PP3 is a candidate.", "guard_context": context}
    )

    assert result["status"] == "BLOCK"
    assert result["blocking_reasons"] == ["guard_context_invalid"]
    assert "unique" in result["guard_context_error"]
