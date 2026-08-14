"""Unit tests for the surviving population evidence group."""

from __future__ import annotations

from tooluniverse.acmg.population import population_evidence


def _card(cards, criterion):
    return next(card for card in cards if card.criterion == criterion)


def test_pm2_absent_with_auditable_callability_suggests_supporting():
    card = _card(
        population_evidence(
            gnomad_ac=0,
            gnomad_an=125748,
            gnomad_af_global=0.0,
            gnomad_af_popmax=0.0,
            coverage_adequate=True,
        ),
        "PM2",
    )
    assert card.strength == "PM2_Supporting"


def test_population_card_preserves_frequency_and_callability_audit_fields():
    card = _card(
        population_evidence(
            gnomad_ac=0,
            gnomad_an=125748,
            gnomad_af_global=0.0,
            callability_available=True,
            population_details={"dataset": "gnomad_r4", "callset": "exome"},
            callability_metrics={"mean": 31.2, "over_20": 0.98},
        ),
        "PM2",
    )
    assert card.input_values["population_details"]["dataset"] == "gnomad_r4"
    assert card.input_values["callability_metrics"]["over_20"] == 0.98
    assert card.evidence_status == "source_backed_candidate"
    assert card.rule_source["type"] == "fork_candidate_policy"
    assert "versioned site-coverage adequacy assessment" in card.missing_requirements


def test_pm2_explicit_adequate_coverage_is_deterministic():
    card = _card(
        population_evidence(
            gnomad_ac=0,
            gnomad_an=125748,
            gnomad_af_global=0.0,
            coverage_adequate=True,
            population_details={"dataset": "gnomad_r4", "callset": "exome"},
        ),
        "PM2",
    )
    assert card.evidence_status == "rule_mapped"
    assert card.rule_source["type"] == "versioned_svi"


def test_pm2_present_without_disease_threshold_is_indeterminate():
    card = _card(
        population_evidence(
            gnomad_af_global=0.02,
            gnomad_af_popmax=0.02,
            gnomad_ac=2000,
            gnomad_an=100000,
        ),
        "PM2",
    )
    assert card.strength == "indeterminate"


def test_pm2_extremely_rare_observation_preserves_supporting_candidate():
    card = _card(
        population_evidence(
            gnomad_af_global=4.1e-6,
            gnomad_af_popmax=1.01e-4,
            gnomad_ac=6,
            gnomad_an=1_461_796,
            callability_available=True,
            population_details={"dataset": "gnomad_r4", "callset": "exome"},
            callability_metrics={"median": 31, "over_20": 0.94},
        ),
        "PM2",
    )

    assert card.strength == "PM2_Supporting"
    assert card.evidence_status == "source_backed_candidate"
    assert card.verification_dimensions["extraction_status"] == "unresolved"
    assert card.input_values["af_global"] == 4.1e-6
    assert "maximum credible allele frequency" in card.caveats[0]
    assert "not a deterministic ClinGen SVI PM2 threshold" in card.rule_basis
    assert card.missing_requirements == [
        "disease-specific maximum credible allele frequency"
    ]


def test_pm2_observed_variant_uses_cspec_frequency_rule_before_callability():
    card = _card(
        population_evidence(
            gnomad_af_global=0.00018,
            gnomad_af_popmax=0.00099,
            gnomad_ac=267,
            gnomad_an=1_461_676,
            callability_available=False,
            rule_override={
                "specification_id": "GN079",
                "version": "1.1.0",
                "rule_id": "clingen-cspec-runtime-gn079",
                "criteria": {
                    "PM2": {
                        "strength": "PM2_Supporting",
                        "population_frequency_threshold": 0.0001114,
                        "operator": "<=",
                    }
                },
            },
        ),
        "PM2",
    )

    assert card.strength == "not_met"
    assert card.evidence_status == "not_met"
    assert card.missing_requirements == []
    assert card.rule_evaluation["threshold"] == 0.0001114
    assert card.rule_evaluation["comparison"] == "<="
    assert card.rule_evaluation["status"] == "condition_not_met"
    assert "coverage" not in card.rule_evaluation["primary_reason"].casefold()
    assert card.clinvar_rule_applied == "ClinGen CSpec population-frequency condition"
    assert "released CSpec" in card.rule_basis


def test_pm2_cspec_frequency_rule_can_be_met_for_observed_variant():
    card = _card(
        population_evidence(
            gnomad_af_global=0.00001,
            gnomad_af_popmax=0.00005,
            gnomad_ac=2,
            gnomad_an=200_000,
            rule_override={
                "specification_id": "GN079",
                "version": "1.1.0",
                "criteria": {
                    "PM2": {
                        "strength": "PM2_Supporting",
                        "population_frequency_threshold": 0.0001114,
                        "operator": "<=",
                    }
                },
            },
        ),
        "PM2",
    )

    assert card.strength == "PM2_Supporting"
    assert card.evidence_status == "rule_mapped"
    assert card.rule_evaluation["status"] == "condition_met"
    assert card.missing_requirements == []


def test_bs1_contract_does_not_suppress_pm2_candidate_without_pm2_threshold():
    cards = population_evidence(
        gnomad_af_global=0.00001,
        gnomad_af_popmax=0.00005,
        gnomad_ac=2,
        gnomad_an=200_000,
        rule_override={"criteria": {"BS1": {"maximum_credible_af": 0.00001}}},
    )

    pm2 = _card(cards, "PM2")
    bs1 = _card(cards, "BS1")
    assert pm2.evidence_status == "source_backed_candidate"
    assert pm2.missing_requirements == [
        "disease-specific maximum credible allele frequency"
    ]
    assert bs1.strength == "BS1"


def test_ba1_threshold_requires_reviewed_exception_status():
    """A >5% frequency is visible but cannot bypass exception review."""
    cards = population_evidence(
        gnomad_af_global=0.06,
        gnomad_af_popmax=0.08,
        gnomad_an=100000,
    )
    assert _card(cards, "PM2").strength == "not_assessed"
    assert _card(cards, "BA1").strength == "not_assessed"


def test_unverified_ba1_exception_cannot_disable_ba1():
    cards = population_evidence(
        gnomad_af_global=0.06,
        gnomad_af_popmax=0.08,
        gnomad_an=100000,
        ba1_exception=True,
        ba1_exception_verified=False,
    )
    assert _card(cards, "BA1").strength == "not_assessed"


def test_verified_ba1_exception_is_not_applicable():
    cards = population_evidence(
        gnomad_af_global=0.06,
        gnomad_af_popmax=0.08,
        gnomad_an=100000,
        ba1_exception=True,
        ba1_exception_verified=True,
    )
    assert _card(cards, "BA1").strength == "not_applicable"


def test_verified_non_exception_can_suggest_ba1():
    cards = population_evidence(
        gnomad_af_global=0.06,
        gnomad_af_popmax=0.08,
        gnomad_an=100000,
        ba1_exception=False,
        ba1_exception_verified=True,
    )
    assert _card(cards, "BA1").strength == "BA1"


def test_pm2_no_data():
    """No gnomAD data leaves PM2 unassessed."""
    assert _card(population_evidence(), "PM2").strength == "not_assessed"


def test_pm2_missing_af_is_not_assessed():
    cards = population_evidence(
        gnomad_ac=0,
        gnomad_an=125748,
        coverage_adequate=True,
    )
    assert _card(cards, "PM2").strength == "not_assessed"


def test_pm2_coverage_inadequate():
    """Inadequate coverage leaves PM2 unassessed."""
    card = _card(
        population_evidence(gnomad_ac=0, gnomad_an=125748, coverage_adequate=False),
        "PM2",
    )
    assert card.strength == "not_assessed"
