"""Unit tests for de novo evidence through the clinical evidence group."""

from __future__ import annotations

import pytest

from tooluniverse.acmg.clinical import clinical_evidence


def _de_novo_card(**kwargs):
    return next(
        card
        for card in clinical_evidence(**kwargs)
        if card.criterion in {"PS2/PM6", "PS2", "PM6"}
    )


def test_ps2_strong():
    assert (
        _de_novo_card(
            de_novo_probands=[
                {
                    "case_id": "case-1",
                    "parental_relationships": "confirmed",
                    "phenotype_consistency": "highly_specific",
                }
            ],
            inheritance_mode="autosomal_dominant",
        ).strength
        == "PS2"
    )


def test_ps2_moderate():
    assert (
        _de_novo_card(
            de_novo_probands=[
                {
                    "case_id": "case-1",
                    "parental_relationships": "confirmed",
                    "phenotype_consistency": "consistent",
                }
            ],
            inheritance_mode="autosomal_dominant",
        ).strength
        == "PS2_Moderate"
    )


def test_pm6_no_parentage():
    assert (
        _de_novo_card(
            de_novo_probands=[
                {
                    "case_id": "case-1",
                    "parental_relationships": "assumed",
                    "phenotype_consistency": "highly_specific",
                }
            ],
            inheritance_mode="autosomal_dominant",
        ).strength
        == "PM6"
    )


def test_not_de_novo():
    assert clinical_evidence() == []


def test_ps2_multiple_probands_accumulate_to_very_strong():
    assert (
        _de_novo_card(
            de_novo_probands=[
                {
                    "case_id": "case-1",
                    "parental_relationships": "confirmed",
                    "phenotype_consistency": "highly_specific",
                },
                {
                    "case_id": "case-2",
                    "parental_relationships": "confirmed",
                    "phenotype_consistency": "highly_specific",
                },
            ],
            inheritance_mode="autosomal_dominant",
        ).strength
        == "PS2_VeryStrong"
    )


def test_removed_de_novo_boolean_inputs_are_rejected():
    with pytest.raises(TypeError):
        _de_novo_card(
            de_novo_confirmed=True,
            paternity_confirmed=True,
            phenotype_highly_specific=True,
            inheritance_mode="autosomal_dominant",
        )


def test_high_heterogeneity_contribution_is_capped_at_one_point():
    card = _de_novo_card(
        de_novo_probands=[
            {
                "case_id": f"case-{index}",
                "parental_relationships": "confirmed",
                "phenotype_consistency": "consistent_high_heterogeneity",
            }
            for index in range(4)
        ],
        inheritance_mode="autosomal_dominant",
    )
    assert card.strength == "PS2_Moderate"
    assert card.input_values["total_points"] == 1.0


def test_recessive_de_novo_without_second_pathogenic_variant_downgrades_one_level():
    card = _de_novo_card(
        de_novo_probands=[
            {
                "case_id": "case-1",
                "parental_relationships": "confirmed",
                "phenotype_consistency": "highly_specific",
                "second_variant_pathogenic": False,
            }
        ],
        inheritance_mode="autosomal_recessive",
    )
    assert card.strength == "PS2_Moderate"


def test_duplicate_de_novo_case_ids_are_not_assessed():
    card = _de_novo_card(
        de_novo_probands=[
            {
                "case_id": "same-case",
                "parental_relationships": "confirmed",
                "phenotype_consistency": "highly_specific",
            },
            {
                "case_id": "same-case",
                "parental_relationships": "confirmed",
                "phenotype_consistency": "highly_specific",
            },
        ],
        inheritance_mode="autosomal_dominant",
    )
    assert card.strength == "not_assessed"
