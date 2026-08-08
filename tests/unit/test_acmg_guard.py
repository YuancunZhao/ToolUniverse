"""Fail-closed tests for the evidence-only ACMG answer guard."""

from __future__ import annotations

from tooluniverse.acmg.models import EvidenceCard, evidence_cards_to_result
from tooluniverse.acmg.guard import guard_acmg_answer, guard_context_hash
from tooluniverse.acmg.runtime_manifest import ruleset_hash


def _validated_pp3() -> dict:
    card = EvidenceCard(
        card_id="fixture",
        criterion="PP3",
        strength="PP3_Supporting",
        input_source="REVEL",
        input_values={"revel_score": 0.7},
        clinvar_rule_applied="Pejaver 2022",
        overlay_validated=True,
        source_fact_ids=["fixture-source"],
    )
    return evidence_cards_to_result(
        [card], trusted_source_fact_ids={"fixture-source"}
    )["evidence_cards"][0]


def test_guard_accepts_serialized_validated_cards_for_criterion_summary():
    result = guard_acmg_answer(
        "PP3 supporting evidence is present.",
        [_validated_pp3()],
        trusted_source_fact_ids={"fixture-source"},
    )
    assert result["status"] == "PASS"


def test_guard_rejects_unvalidated_candidate_card():
    candidate = {
        **_validated_pp3(),
        "system_preview_included": False,
        "overlay_validated": False,
    }
    result = guard_acmg_answer("PP3 supporting evidence is present.", [candidate])
    assert result["status"] == "BLOCK"
    assert result["unsupported_codes"] == ["PP3"]


def test_guard_blocks_final_five_tier_labels_even_with_validated_cards():
    result = guard_acmg_answer(
        "This variant is Pathogenic with PP3.",
        [_validated_pp3()],
        trusted_source_fact_ids={"fixture-source"},
    )
    assert result["status"] == "BLOCK"
    assert any("final" in reason.lower() for reason in result["blocking_reasons"])


def test_guard_rejects_forged_not_assessed_preview_dict():
    forged = {
        "criterion": "PP3",
        "strength": "PP3_Supporting",
        "assessment_status": "not_assessed",
        "system_preview_included": True,
        "overlay_validated": True,
        "source_fact_ids": ["forged-source"],
    }
    result = guard_acmg_answer("PP3 supporting evidence is present.", [forged])
    assert result["status"] == "BLOCK"
    assert result["unsupported_codes"] == ["PP3"]


def test_guard_blocks_short_form_final_labels():
    for label in ("LP", "LB", "VUS", "classification: P", "classification: B"):
        result = guard_acmg_answer(
            label,
            [_validated_pp3()],
            trusted_source_fact_ids={"fixture-source"},
        )
        assert result["status"] == "BLOCK", label


def test_guard_requires_a_trusted_fact_set_for_dict_cards():
    result = guard_acmg_answer("PP3", [_validated_pp3()])
    assert result["status"] == "BLOCK"


def test_guard_normalizes_final_label_separators_and_unicode_width():
    for label in (
        "likely_pathogenic",
        "likely-pathogenic",
        "likely\u2011pathogenic",
        "LIKELY   PATHOGENIC",
        "ＶＵＳ",
    ):
        result = guard_acmg_answer(
            label,
            [_validated_pp3()],
            trusted_source_fact_ids={"fixture-source"},
        )
        assert result["status"] == "BLOCK", label


def test_guard_does_not_treat_ordinary_letters_or_p_value_as_classification():
    result = guard_acmg_answer(
        "PP3 remains under review; p = 0.01 and group B was the control.",
        [_validated_pp3()],
        trusted_source_fact_ids={"fixture-source"},
    )
    assert result["status"] == "PASS"


def test_guard_allows_protein_hgvs_card_ids_and_group_b_text():
    result = guard_acmg_answer(
        (
            "The protein change p.Arg249Gln is linked to card "
            "acmg-card:v1:9b2cb01d1d06d28379a9; p-value=0.01 and group B "
            "was the control."
        ),
        [_validated_pp3()],
        trusted_source_fact_ids={"fixture-source"},
    )

    assert result["status"] == "PASS"


def test_guard_expands_combined_criterion_cards_for_single_code_citations():
    card = {
        **_validated_pp3(),
        "criterion": "PS2/PM6",
        "suggested_criterion": "PS2/PM6",
    }

    result = guard_acmg_answer(
        "PS2 and PM6 remain candidate evidence.",
        [card],
        known_source_fact_ids={"fixture-source"},
    )

    assert result["status"] == "PASS"
    assert result["unsupported_codes"] == []


def test_guard_allows_citing_visible_excluded_proposal_with_role_metadata():
    proposal = {
        **_validated_pp3(),
        "proposal_status": "requires_user_review",
        "system_preview_included": False,
        "exclusion_reason": "unresolved_directional_conflict",
    }
    result = guard_acmg_answer(
        "PP3 is a system suggestion under review.",
        [proposal],
        known_source_fact_ids={"fixture-source"},
    )
    assert result["status"] == "PASS"
    assert result["card_roles"][0]["proposal_status"] == "requires_user_review"
    assert result["card_roles"][0]["system_preview_included"] is False


def test_guard_rejects_unserialized_forged_proposal():
    forged = {
        "criterion": "PP3",
        "strength": "PP3_Supporting",
        "proposal_status": "requires_user_review",
    }
    result = guard_acmg_answer("PP3 is suggested.", [forged])
    assert result["status"] == "BLOCK"


def test_runtime_guard_uses_ready_source_facts_from_collector_result():
    from tooluniverse.acmg_runtime_tools import ACMGGuardFinalAnswerTool

    card = _validated_pp3()
    collector_result = {
        "evidence_cards": [card],
        "source_facts": [
            {
                "fact_id": "fixture-source",
                "status": "success",
                "identity_verified": True,
                "assessment_ready": True,
            }
        ],
    }
    result = ACMGGuardFinalAnswerTool(
        {"name": "ACMG_guard_final_answer"}
    ).run({"final_answer_text": "PP3", "collector_result": collector_result})
    assert result["status"] == "PASS"


def test_runtime_guard_accepts_compact_guard_context_without_collector_payload():
    from tooluniverse.acmg_runtime_tools import ACMGGuardFinalAnswerTool

    context = {
        "schema_version": "2026-08-07",
        "variant_identity_hash": "a" * 64,
        "ruleset_hash": ruleset_hash(),
        "known_source_fact_ids": ["fixture-source"],
        "trusted_source_fact_ids": [],
        "cards": [
            {
                "card_id": "acmg-card:v1:fixture",
                "criterion": "PS2/PM6",
                "proposal_status": "requires_user_review",
                "role": "candidate",
                "source_fact_ids": ["fixture-source"],
            }
        ],
    }
    context["context_hash"] = guard_context_hash(context)
    result = ACMGGuardFinalAnswerTool(
        {"name": "ACMG_guard_final_answer"}
    ).run({"final_answer_text": "PS2 and PM6 are candidates.", "guard_context": context})

    assert result["status"] == "PASS"
    assert result["card_roles"][0]["role"] == "candidate"


def test_runtime_guard_fails_closed_for_invalid_compact_context():
    from tooluniverse.acmg_runtime_tools import ACMGGuardFinalAnswerTool

    base = {
        "schema_version": "2026-08-07",
        "variant_identity_hash": "a" * 64,
        "ruleset_hash": ruleset_hash(),
        "known_source_fact_ids": ["fixture-source"],
        "trusted_source_fact_ids": [],
        "cards": [
            {
                "card_id": "acmg-card:v1:fixture",
                "criterion": "PP3",
                "proposal_status": "requires_user_review",
                "role": "candidate",
                "source_fact_ids": ["fixture-source"],
            }
        ],
    }
    base["context_hash"] = guard_context_hash(base)
    invalid_contexts = [
        {key: value for key, value in base.items() if key != "context_hash"},
        {**base, "schema_version": "stale"},
        {**base, "cards": [{**base["cards"][0], "criterion": "PS4"}]},
        {**base, "known_source_fact_ids": ["different-source"]},
        ["not-an-object"],
    ]

    tool = ACMGGuardFinalAnswerTool({"name": "ACMG_guard_final_answer"})
    for context in invalid_contexts:
        result = tool.run({"final_answer_text": "PP3", "guard_context": context})
        assert result["status"] == "BLOCK"
    assert result["blocking_reasons"] == ["guard_context_invalid"]


def test_runtime_guard_rejects_rehashed_context_from_another_ruleset():
    from tooluniverse.acmg_runtime_tools import ACMGGuardFinalAnswerTool

    context = {
        "schema_version": "2026-08-07",
        "variant_identity_hash": "a" * 64,
        "ruleset_hash": ruleset_hash(),
        "known_source_fact_ids": ["fixture-source"],
        "trusted_source_fact_ids": [],
        "cards": [
            {
                "card_id": "acmg-card:v1:fixture",
                "criterion": "PS4",
                "proposal_status": "requires_user_review",
                "role": "candidate",
                "source_fact_ids": ["fixture-source"],
            }
        ],
    }
    context["ruleset_hash"] = "b" * 64
    context["context_hash"] = guard_context_hash(context)

    result = ACMGGuardFinalAnswerTool({}).run(
        {"final_answer_text": "PS4 is a candidate.", "guard_context": context}
    )

    assert result["status"] == "BLOCK"
    assert result["blocking_reasons"] == ["guard_context_invalid"]
    assert "ruleset_hash" in result["guard_context_error"]
