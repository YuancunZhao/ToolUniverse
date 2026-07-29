"""Unit tests for the surviving computational evidence group."""

from __future__ import annotations

from tooluniverse.acmg.computational import computational_evidence


def _pp3_bp4_card(**kwargs):
    return next(
        card
        for card in computational_evidence(variant_type="missense_variant", **kwargs)
        if card.criterion in {"PP3/BP4", "PP3", "BP4"}
    )


def test_pp3_strong_revel():
    card = _pp3_bp4_card(revel_score=0.95)
    assert card.strength == "PP3_Strong"


def test_revel_supporting_moderate_and_strong_intervals():
    assert _pp3_bp4_card(revel_score=0.70).strength == "PP3_Supporting"
    assert _pp3_bp4_card(revel_score=0.80).strength == "PP3_Moderate"
    assert _pp3_bp4_card(revel_score=0.932).strength == "PP3_Strong"


def test_revel_benign_intervals():
    assert _pp3_bp4_card(revel_score=0.003).strength == "BP4_VeryStrong"
    assert _pp3_bp4_card(revel_score=0.010).strength == "BP4_Strong"
    assert _pp3_bp4_card(revel_score=0.10).strength == "BP4_Moderate"
    assert _pp3_bp4_card(revel_score=0.20).strength == "BP4_Supporting"


def test_no_evidence_interval():
    assert _pp3_bp4_card(revel_score=0.50).strength == "not_met"


def test_cadd_is_audit_only_and_cannot_replace_revel():
    card = _pp3_bp4_card(cadd_phred=26.0)
    assert card.criterion == "PP3/BP4"
    assert card.strength == "not_assessed"


def test_missing_selected_score_does_not_fallback_to_another_predictor():
    card = _pp3_bp4_card(cadd_phred=30.0)
    assert card.strength == "not_assessed"
