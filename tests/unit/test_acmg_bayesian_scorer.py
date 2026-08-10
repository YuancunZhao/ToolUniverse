"""Tests for the ACMG v3 automatic and verified Bayesian estimates."""

from __future__ import annotations

import pytest

from tooluniverse.acmg.rule_catalog import rule_for_criterion
from tooluniverse.acmg.summary import compute_bayesian_score


def _row(
    criterion: str,
    strength: str,
    *,
    card_id: str | None = None,
    verified: bool = True,
    **overrides,
):
    rule = rule_for_criterion(criterion)
    row = {
        "card_id": card_id or f"card-{criterion}-{strength}",
        "criterion": criterion,
        "strength": strength,
        "evidence_status": "rule_mapped" if verified else "source_backed_candidate",
        "strength_source": "versioned_rule" if verified else "acmg_base_candidate",
        "rule_source": {
            "type": "versioned_svi" if verified else "fork_candidate_policy"
        },
        "verification_dimensions": {
            "identity_status": "matched",
            "source_status": "available",
            "extraction_status": "structured" if verified else "unresolved",
            "version_status": "versioned" if verified else "unversioned",
            "disease_match_status": "matched" if verified else "unspecified",
            "independence_status": "independent",
        },
        "calculation_roles": {
            "automatic": True,
            "verified": verified,
            "user_selected": False,
        },
        "source_fact_ids": ["fixture-source"],
        "rule_id": rule.get("rule_id", ""),
        "rule_version": rule.get("version", ""),
    }
    row.update(overrides)
    return row


def _automatic(rows):
    return compute_bayesian_score(
        rows,
        known_source_fact_ids={"fixture-source"},
        estimate_type="automatic",
        calculation_role="automatic",
        eligibility="automatic",
    )


def test_bayesian_score_with_pathogenic_evidence():
    score = _automatic(
        [
            _row("PS2", "PS2"),
            _row("PS3", "PS3"),
            _row("PP3", "PP3_Supporting"),
        ]
    )
    assert score["posterior_probability"] > 0.9
    assert score["estimate_policy"] == "source_backed_candidates"


def test_bayesian_score_with_benign_evidence():
    score = _automatic([_row("BS3", "BS3"), _row("BP4", "BP4_Supporting")])
    assert score["posterior_probability"] < 0.1


def test_bayesian_score_with_mixed_evidence():
    score = _automatic([_row("PS3", "PS3"), _row("BP4", "BP4_Supporting")])
    assert 0.2 < score["posterior_probability"] < 0.8


def test_bayesian_score_empty_returns_fixed_prior():
    score = compute_bayesian_score([])
    assert score["prior_probability"] == 0.1
    assert score["posterior_probability"] == 0.1
    assert score["odds_path"] == 1.0
    assert score["not_a_final_classification"] is True


@pytest.mark.parametrize(
    ("strength", "expected_odds"),
    [
        ("PP3_Moderate", 4.3),
        ("PP3_Strong", 18.7),
        ("BP4_Moderate", 0.233),
        ("BP4_Strong", 0.053),
        ("BP4_VeryStrong", 0.00286),
        ("BP7_Supporting", 0.48),
    ],
)
def test_bayesian_score_keeps_calibrated_odds_precision(strength, expected_odds):
    criterion = strength.split("_")[0]
    score = _automatic([_row(criterion, strength)])
    assert score["odds_path"] == pytest.approx(expected_odds)


def test_automatic_score_requires_role_source_and_legal_dimensions():
    missing_role = _row("PP3", "PP3_Moderate")
    missing_role["calculation_roles"]["automatic"] = False
    unknown_source = _row("PP3", "PP3_Moderate", card_id="unknown")
    conflicted = _row("PP3", "PP3_Moderate", card_id="conflicted")
    conflicted["verification_dimensions"]["identity_status"] = "conflict"

    score = compute_bayesian_score(
        [missing_role, unknown_source, conflicted],
        known_source_fact_ids={"different-source"},
    )
    assert score["strengths_used"] == []
    assert score["odds_path"] == 1.0


def test_generic_source_backed_candidate_uses_tavtigian_odds_only_automatically():
    row = _row("PM5", "PM5_Supporting", verified=False)
    automatic = _automatic([row])
    verified = compute_bayesian_score(
        [row],
        verified_source_fact_ids={"fixture-source"},
        estimate_type="verified",
        calculation_role="verified",
        eligibility="verified",
    )
    assert automatic["odds_path"] == pytest.approx(2.08)
    assert automatic["evidence_odds"][0]["odds_source"] == (
        "generic_tavtigian_strength"
    )
    assert verified["included_card_ids"] == []


def test_ba1_is_reported_as_special_and_not_multiplied():
    score = _automatic([_row("BA1", "BA1")])
    assert score["odds_path"] == 1.0
    assert score["included_card_ids"] == []
    assert score["special_criteria"][0]["criterion"] == "BA1"
