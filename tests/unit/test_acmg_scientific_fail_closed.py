"""Conservative boundaries for family and functional evidence."""

import pytest

from tooluniverse.acmg.clinical import clinical_evidence
from tooluniverse.acmg.computational import computational_evidence
from tooluniverse.acmg.functional import functional_evidence
from tooluniverse.acmg.literature import literature_evidence


def _card(cards, criterion):
    return next(card for card in cards if card.criterion == criterion)


def _brnich_assay(**overrides):
    assay = {
        "gene_disease_mechanism": "gain of function",
        "assay_scope": "protein_or_cell_function",
        "assay_effect_consistent": True,
        "assay_class": "cell signaling",
        "assay_instance_id": "assay-1",
        "model_system": "human chondrocytes",
        "disease_relevance": True,
        "readout_name": "phospho-ERK",
        "readout_unit": "relative signal",
        "normal_threshold": "0.8-1.2",
        "abnormal_threshold": ">1.5",
        "variant_result": "2.1",
        "positive_experimental_controls": ["positive-1"],
        "negative_experimental_controls": ["negative-1"],
        "technical_replicates": 3,
        "biological_replicates": 3,
        "pathogenic_validation_controls": 2,
        "benign_validation_controls": 2,
        "validation_control_provenance": "independent ClinVar expert panel set",
        "dynamic_range": 4.2,
        "calibration_method": "reported_odds_path",
        "reported_odds_path": 4.31,
        "direction": "damaging",
    }
    assay.update(overrides)
    return assay


def test_functional_assay_missing_model_and_readout_is_not_assessed():
    cards = functional_evidence(
        functional_assays=[
            {"assay_id": "assay-1", "replicated": True, "has_controls": True}
        ],
    )
    assert _card(cards, "PS3/BS3").strength == "not_assessed"


def test_functional_assay_with_unclear_direction_is_not_assessed():
    cards = functional_evidence(
        functional_assays=[
            {
                "assay_id": "assay-1",
                "replicated": True,
                "has_controls": True,
                "model_appropriate": True,
                "readout_validated": True,
                "odds_path": 4.3,
            }
        ],
    )
    assert _card(cards, "PS3/BS3").strength == "not_assessed"


def test_functional_odds_path_controls_ps3_strength():
    cards = functional_evidence(functional_assays=[_brnich_assay()])
    assert _card(cards, "PS3").strength == "PS3_Moderate"


def test_functional_odds_path_controls_bs3_strength():
    cards = functional_evidence(
        functional_assays=[_brnich_assay(reported_odds_path=0.229, direction="normal")]
    )
    assert _card(cards, "BS3").strength == "BS3_Moderate"


def test_bare_odds_path_is_rejected():
    cards = functional_evidence(
        functional_assays=[{"odds_path": 18.8, "direction": "damaging"}]
    )
    assert _card(cards, "PS3/BS3").strength == "not_assessed"


def test_brnich_boundary_values_do_not_round_up():
    pathogenic = functional_evidence(
        functional_assays=[_brnich_assay(reported_odds_path=4.3)]
    )
    benign = functional_evidence(
        functional_assays=[_brnich_assay(reported_odds_path=0.23, direction="normal")]
    )
    assert _card(pathogenic, "PS3").strength == "PS3_Supporting"
    assert _card(benign, "BS3").strength == "BS3_Supporting"


def test_direct_rna_splicing_assay_cannot_generate_ps3_or_bs3():
    cards = functional_evidence(
        functional_assays=[_brnich_assay(assay_scope="direct_rna_splicing")]
    )

    card = _card(cards, "PS3/BS3")
    assert card.strength == "not_assessed"
    assert "Walker RNA evidence route" in card.provenance_chain[0]


def test_missing_assay_scope_fails_closed():
    assay = _brnich_assay()
    assay.pop("assay_scope")

    card = _card(functional_evidence(functional_assays=[assay]), "PS3/BS3")
    assert card.strength == "not_assessed"


def test_frameshift_revel_is_outside_pejaver_missense_scope():
    cards = computational_evidence(
        revel_score=0.95,
        variant_type="frameshift_variant",
    )
    assert _card(cards, "PP3/BP4").strength == "not_applicable"


def test_empty_case_control_input_produces_no_literature_cards():
    cards = literature_evidence(case_control_facts=[])
    assert cards == []


def _verified_case_control_fact(**overrides):
    fact = {
        "fact_id": "pmid-123-table-2-cohort-a",
        "source_pmid": "12345678",
        "section_locator": "Table 2",
        "variant_identity": "NM_000142.5:c.1075+95C>G",
        "gene": "FGFR3",
        "case_count": 12,
        "control_count": 1000,
        "odds_ratio": 6.2,
        "ci_lower": 1.4,
        "phenotype_consistent": True,
        "cases_independent": True,
        "evidence_verified": True,
        "verified_by": "curator-1",
        "extraction_method": "manual_full_text_review",
    }
    fact.update(overrides)
    return fact


def test_literature_fact_requires_verification_provenance_and_identity_binding():
    unverified = _verified_case_control_fact(evidence_verified=False)
    mismatch = _verified_case_control_fact(
        fact_id="mismatch", variant_identity="NM_999999.1:c.1A>G"
    )

    cards = literature_evidence(
        case_control_facts=[unverified, mismatch],
        expected_variant="NM_000142.5:c.1075+95C>G",
        expected_gene="FGFR3",
    )

    assert cards[0].evidence_status == "source_backed_candidate"
    assert cards[1].evidence_status == "excluded"


def test_literature_fact_without_expected_identity_cannot_count():
    cards = literature_evidence(case_control_facts=[_verified_case_control_fact()])

    assert cards[0].evidence_status == "excluded"
    assert "identity" in cards[0].provenance_chain[0]


def test_literature_fact_without_disease_policy_becomes_review_proposal():
    fact = _verified_case_control_fact()
    cards = literature_evidence(
        case_control_facts=[fact, dict(fact)],
        expected_variant="NM_000142.5:c.1075+95C>G",
        expected_gene="FGFR3",
    )

    assert cards[0].evidence_status == "source_backed_candidate"
    assert cards[0].strength == "PS4"
    assert cards[0].rule_source["type"] == "generic_acmg_candidate"
    assert cards[1].evidence_status == "excluded"
    assert "duplicate" in cards[1].provenance_chain[0]


def test_pm3_requires_recessive_inheritance_context():
    cards = clinical_evidence(
        inheritance_mode="autosomal_dominant",
        pm3_frequency_eligible=True,
        pm3_observations=[
            {
                "case_id": "case-1",
                "zygosity": "compound_heterozygous",
                "other_variant_classification": "PATHOGENIC",
                "phase": "confirmed_in_trans",
                "other_variant_frequency_eligible": True,
            }
        ],
    )
    assert cards == []


def test_pm3_structured_confirmed_in_trans_proband_scores_moderate():
    cards = clinical_evidence(
        inheritance_mode="autosomal_recessive",
        pm3_frequency_eligible=True,
        pm3_observations=[
            {
                "case_id": "case-1",
                "zygosity": "compound_heterozygous",
                "other_variant_classification": "PATHOGENIC",
                "phase": "confirmed_in_trans",
                "other_variant_frequency_eligible": True,
            }
        ],
    )
    assert _card(cards, "PM3").strength == "PM3"


def test_pm3_phase_unknown_likely_pathogenic_is_quarter_point():
    cards = clinical_evidence(
        inheritance_mode="autosomal_recessive",
        pm3_frequency_eligible=True,
        pm3_observations=[
            {
                "case_id": "case-1",
                "zygosity": "compound_heterozygous",
                "other_variant_classification": "LP",
                "phase": "unknown",
                "other_variant_frequency_eligible": True,
            }
        ],
    )
    card = _card(cards, "PM3")
    assert card.strength == "not_met"
    assert card.evidence_status == "not_met"
    assert card.observed_facts["total_points"] == 0.25


def test_pm3_homozygous_points_are_capped_at_one():
    cards = clinical_evidence(
        inheritance_mode="autosomal_recessive",
        pm3_frequency_eligible=True,
        pm3_observations=[
            {
                "case_id": f"case-{index}",
                "zygosity": "homozygous",
                "other_variant_frequency_eligible": True,
            }
            for index in range(4)
        ],
    )
    card = _card(cards, "PM3")
    assert card.strength == "PM3"
    assert card.observed_facts["total_points"] == 1.0


def test_removed_functional_boolean_inputs_are_rejected():
    with pytest.raises(TypeError):
        functional_evidence(
            variant_type="missense_variant",
            in_functional_domain=True,
            domain_has_pathogenic_enrichment=True,
            gene_lof_mechanism=True,
            indel_type="indel_inframe",
        )


def _pm1_profile(effect="missense"):
    return {
        "status": "resolved",
        "selected_transcript": "NM_000142.5",
        "selected_transcript_terms": [f"{effect}_variant"],
        "protein_effect": effect,
        "splice_class": "none",
        "protein_position": 380,
    }


def _pm1_protein_context(**overrides):
    context = {
        "mapping_status": "resolved",
        "selected_mapping": {
            "protein_accession": "P22607",
            "protein_position_start": 380,
            "protein_position_end": 380,
        },
        "protein_position": 380,
        "overlapping_features": [
            {
                "type": "DOMAIN",
                "position_start": 350,
                "position_end": 400,
                "description": "protein kinase domain",
            }
        ],
        "interpro_entries": [
            {"accession": "IPR000719", "name": "Protein kinase domain"}
        ],
    }
    context.update(overrides)
    return context


def _pm1_contract(**criterion_overrides):
    criterion = {
        "protein_accession": "P22607",
        "transcript": "NM_000142.5",
        "regions": [{"start": 370, "end": 390}],
        "variant_types": ["missense"],
        "critical_region_established": True,
        "benign_variation_depleted": True,
        "strength": "PM1_Moderate",
        "mutually_exclusive_with": ["PM5"],
    }
    criterion.update(criterion_overrides)
    return {
        "specification_id": "fixture-pm1",
        "rule_id": "fixture-pm1-rule",
        "version": "1.0",
        "primary_reference": "https://example.test/pm1",
        "criteria": {"PM1": criterion},
    }


def test_pm1_domain_overlap_is_visible_as_source_backed_candidate():
    card = _card(
        functional_evidence(
            consequence_profile=_pm1_profile(),
            protein_context=_pm1_protein_context(),
        ),
        "PM1",
    )

    assert card.strength == "PM1"
    assert card.observed_facts["protein_context"]["overlapping_features"]
    assert card.evidence_status == "source_backed_candidate"
    assert card.rule_source["type"] == "generic_acmg_candidate"


def test_pm1_exact_reviewed_contract_can_suggest_configured_strength():
    card = _card(
        functional_evidence(
            consequence_profile=_pm1_profile(),
            protein_context=_pm1_protein_context(),
            rule_override=_pm1_contract(),
        ),
        "PM1",
    )

    assert card.strength == "PM1_Moderate"
    assert card.rule_id == "fixture-pm1-rule"
    assert card.observed_facts["cspec_contract_applied"]["protein_accession"] == (
        "P22607"
    )
    assert card.evidence_status == "rule_mapped"
    assert card.rule_source["type"] == "dynamic_cspec_structured"


def test_pm1_contract_mismatch_and_nonapplicable_consequence_fail_closed():
    mismatch = _card(
        functional_evidence(
            consequence_profile=_pm1_profile(),
            protein_context=_pm1_protein_context(),
            rule_override=_pm1_contract(protein_accession="P99999"),
        ),
        "PM1",
    )
    frameshift = functional_evidence(
        consequence_profile=_pm1_profile("lof"),
        protein_context=_pm1_protein_context(),
    )

    assert mismatch.strength == "PM1"
    assert mismatch.evidence_status == "source_backed_candidate"
    assert not any(card.criterion == "PM1" for card in frameshift)


def test_removed_pvs1_boolean_context_is_rejected():
    with pytest.raises(TypeError):
        functional_evidence(
            variant_type="frameshift_variant",
            gene_lof_mechanism=True,
        )


def test_de_novo_points_do_not_require_an_inheritance_label_to_remain_visible():
    cards = clinical_evidence(
        de_novo_probands=[
            {
                "case_id": "case-1",
                "parental_relationships": "confirmed",
                "phenotype_consistency": "highly_specific",
            }
        ],
    )
    assert _card(cards, "PS2").strength == "PS2"


def test_pp4_requires_complete_disease_and_phenotype_context():
    cards = clinical_evidence(inheritance_mode="autosomal_dominant")
    assert cards == []


def test_case_only_ps4_requires_independent_cases():
    incomplete = literature_evidence(
        case_control_facts=[
            {
                "fact_id": "series-incomplete",
                "fact_type": "case_series",
                "variant_identity": "NM_000142.5:c.1075+95C>G",
                "gene": "FGFR3",
                "case_count": 8,
                "cases_independent": False,
            }
        ],
        expected_variant="NM_000142.5:c.1075+95C>G",
        expected_gene="FGFR3",
    )
    complete = literature_evidence(
        case_control_facts=[
            {
                "fact_id": "series-complete",
                "fact_type": "case_series",
                "variant_identity": "NM_000142.5:c.1075+95C>G",
                "gene": "FGFR3",
                "case_count": 8,
                "cases_independent": True,
            }
        ],
        expected_variant="NM_000142.5:c.1075+95C>G",
        expected_gene="FGFR3",
    )
    assert _card(incomplete, "PS4").evidence_status == "source_backed_candidate"
    assert _card(complete, "PS4").evidence_status == "source_backed_candidate"
    assert _card(complete, "PS4").strength == "PS4_Supporting"


def test_case_control_crossing_the_null_is_not_met():
    cards = literature_evidence(
        case_control_facts=[
            {
                "fact_id": "case-control-null",
                "fact_type": "case_control",
                "variant_identity": "NM_000142.5:c.1075+95C>G",
                "gene": "FGFR3",
                "case_count": 20,
                "control_count": 100,
                "odds_ratio": 2.0,
                "ci_lower": 0.8,
            }
        ],
        expected_variant="NM_000142.5:c.1075+95C>G",
        expected_gene="FGFR3",
    )
    assert _card(cards, "PS4").strength == "not_met"
