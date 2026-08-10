import pytest

from tooluniverse.acmg.collector import (
    ACMGEvidencePipeline,
    _literature_mapping_requirements_met,
    _mapped_literature_criterion,
)
from tooluniverse.acmg.document_facts import LITERATURE_FACT_CRITERIA
from tooluniverse.acmg.models import SourceFact


@pytest.mark.parametrize(
    ("fact_type", "values", "suggested", "criterion"),
    [
        ("phenotype_specificity", {}, "", "PP4"),
        ("healthy_observation", {}, "", "BS2"),
        ("allelic_phase", {}, "", "BP2"),
        ("alternative_cause", {}, "", "BP5"),
        (
            "segregation",
            {"segregation_direction": "segregates"},
            "",
            "PP1",
        ),
        (
            "segregation",
            {"segregation_direction": "does_not_segregate"},
            "BS4",
            "BS4",
        ),
        (
            "prior_variant",
            {"amino_acid_relation": "same amino acid change"},
            "",
            "PS1",
        ),
        (
            "prior_variant",
            {"amino_acid_relation": "same residue different change"},
            "",
            "PM5",
        ),
        (
            "protein_length_repeat",
            {"effect_type": "length change outside repeat"},
            "",
            "PM4",
        ),
        (
            "protein_length_repeat",
            {"effect_type": "inframe change in repeat"},
            "",
            "BP3",
        ),
    ],
)
def test_fact_types_map_only_to_allowed_criteria(
    fact_type, values, suggested, criterion
):
    mapped, status = _mapped_literature_criterion(fact_type, values, suggested)

    assert mapped == criterion
    assert mapped in LITERATURE_FACT_CRITERIA[fact_type]
    assert status == "generic_acmg_candidate"


def test_cross_criterion_llm_suggestion_is_not_trusted():
    mapped, status = _mapped_literature_criterion("healthy_observation", {}, "PS4")

    assert mapped == "BS2"
    assert status == "generic_acmg_candidate"


def test_rna_splicing_fact_cannot_bypass_pvs1():
    mapped, status = _mapped_literature_criterion(
        "rna_splicing", {"splice_effect": "abnormal"}, "PVS1"
    )
    usable, missing = _literature_mapping_requirements_met(
        "rna_splicing", {"splice_effect": "abnormal"}, mapped
    )

    assert mapped == ""
    assert status == "unmapped"
    assert usable is False
    assert any("PVS1" in value for value in missing)


def test_prior_variant_requires_independent_pathogenic_evidence():
    usable, missing = _literature_mapping_requirements_met(
        "prior_variant",
        {
            "prior_variant_identity": "NM_000142.5:c.1A>G",
            "amino_acid_relation": "same amino acid change",
            "independent_pathogenic_evidence": False,
        },
        "PS1",
    )

    assert usable is False
    assert "independent pathogenic evidence for the prior variant" in missing


@pytest.mark.parametrize(
    "fact_type",
    [
        "case_control",
        "case_series",
        "de_novo",
        "pm3",
        "recessive_allelic",
        "functional",
    ],
)
def test_criterion_specific_literature_proposals_do_not_create_generic_duplicate_cards(
    fact_type,
):
    fact = SourceFact(
        fact_id=f"fact-{fact_type}",
        tool_name="EuropePMC_get_full_text",
        status="success",
        query_identity={"variant": "NM_000001.1:c.1A>G", "gene": "GENE"},
        result_identity={"hgvs_c": "NM_000001.1:c.1A>G", "gene": "GENE"},
        features={
            "fact_type": fact_type,
            "values": {},
            "anchor_status": "verified",
            "semantic_status": "verified",
        },
        raw_result_hash="fixture",
        identity_status="matched",
        source_status="available",
        extraction_status="rule_extracted",
        version_status="versioned",
    )

    cards = ACMGEvidencePipeline._literature_proposal_cards(
        {fact.fact_id: fact},
        {"status": "resolved"},
    )

    assert cards == []
