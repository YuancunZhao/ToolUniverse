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
    assert card.proposal_status == "requires_user_review"
    assert card.rule_verification == "generic_svi"
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
    assert card.proposal_status == "suggested"
    assert card.rule_verification == "versioned_deterministic"


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


def test_pm2_uses_general_svi_without_vcep():
    card = _card(
        population_evidence(
            gnomad_af_global=0.0,
            gnomad_ac=0,
            gnomad_an=100000,
            coverage_adequate=True,
        ),
        "PM2",
    )
    assert card.strength == "PM2_Supporting"


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
