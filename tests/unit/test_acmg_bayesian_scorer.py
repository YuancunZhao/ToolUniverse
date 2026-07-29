"""Tests for ACMG Bayesian scorer."""

from __future__ import annotations

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg.summary import compute_bayesian_score
from tooluniverse.acmg.rule_catalog import rule_for_criterion


def _trusted(rows):
    trusted = []
    for row in rows:
        rule = rule_for_criterion(row["criterion"])
        trusted.append(
            {
                **row,
                "source_fact_ids": ["fixture-source"],
                "rule_id": rule["rule_id"],
                "rule_version": rule["version"],
            }
        )
    return trusted


def _score(rows):
    return compute_bayesian_score(rows, trusted_source_fact_ids={"fixture-source"})


def test_bayesian_score_with_pathogenic_evidence():
    results = [
        {
            "criterion": "PS2",
            "strength": "PS2",
            "assessment_status": "met",
            "system_preview_included": True,
            "overlay_validated": True,
        },
        {
            "criterion": "PS3",
            "strength": "PS3",
            "assessment_status": "met",
            "system_preview_included": True,
            "overlay_validated": True,
        },
        {
            "criterion": "PP3",
            "strength": "PP3_Supporting",
            "assessment_status": "met",
            "system_preview_included": True,
            "overlay_validated": True,
        },
    ]
    score = _score(_trusted(results))
    assert "posterior_probability" in score
    assert "odds_path" in score
    assert "strength_summary" in score
    assert score["posterior_probability"] > 0.9


def test_bayesian_score_with_benign_evidence():
    results = [
        {
            "criterion": "BS3",
            "strength": "BS3",
            "assessment_status": "met",
            "system_preview_included": True,
            "overlay_validated": True,
        },
        {
            "criterion": "BP4",
            "strength": "BP4_Supporting",
            "assessment_status": "met",
            "system_preview_included": True,
            "overlay_validated": True,
        },
    ]
    score = _score(_trusted(results))
    assert score["posterior_probability"] < 0.1


def test_bayesian_score_with_mixed_evidence():
    results = [
        {
            "criterion": "PS3",
            "strength": "PS3",
            "assessment_status": "met",
            "system_preview_included": True,
            "overlay_validated": True,
        },
        {
            "criterion": "BP4",
            "strength": "BP4_Supporting",
            "assessment_status": "met",
            "system_preview_included": True,
            "overlay_validated": True,
        },
    ]
    score = _score(_trusted(results))
    # Mixed evidence should produce moderate probability
    # PS3 (strong, 18.7) * BP4_Supporting (0.48) -> odds 8.976.
    assert 0.2 < score["posterior_probability"] < 0.8


def test_bayesian_score_empty():
    score = compute_bayesian_score([])
    assert score["prior_probability"] == 0.1
    assert score["posterior_probability"] == 0.1
    assert score["odds_path"] == 1.0


def test_bayesian_score_preserves_calibrated_pp3_bp4_strengths():
    score = _score(
        _trusted(
            [
                {
                    "criterion": "PP3",
                    "strength": "PP3_Moderate",
                    "assessment_status": "met",
                    "system_preview_included": True,
                    "overlay_validated": True,
                },
                {
                    "criterion": "PP3",
                    "strength": "PP3_Strong",
                    "assessment_status": "met",
                    "system_preview_included": True,
                    "overlay_validated": True,
                },
                {
                    "criterion": "BP4",
                    "strength": "BP4_Moderate",
                    "assessment_status": "met",
                    "system_preview_included": True,
                    "overlay_validated": True,
                },
                {
                    "criterion": "BP4",
                    "strength": "BP4_Strong",
                    "assessment_status": "met",
                    "system_preview_included": True,
                    "overlay_validated": True,
                },
                {
                    "criterion": "BP4",
                    "strength": "BP4_VeryStrong",
                    "assessment_status": "met",
                    "system_preview_included": True,
                    "overlay_validated": True,
                },
            ]
        )
    )

    assert score["strengths_used"] == [
        "PP3_Moderate",
        "PP3_Strong",
        "BP4_Moderate",
        "BP4_Strong",
        "BP4_VeryStrong",
    ]


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
    score = _score(
        _trusted(
            [
                {
                    "criterion": strength.split("_")[0],
                    "strength": strength,
                    "assessment_status": "met",
                    "system_preview_included": True,
                    "overlay_validated": True,
                },
            ]
        )
    )

    assert score["odds_path"] == pytest.approx(expected_odds)


def test_bayesian_score_excludes_rows_without_explicit_authorization():
    rows = [
        {"criterion": "PP3", "strength": "PP3_Moderate"},
        {
            "criterion": "PP3",
            "strength": "PP3_Moderate",
            "system_preview_included": True,
        },
        {"criterion": "PP3", "strength": "PP3_Moderate", "overlay_validated": True},
        {
            "criterion": "PP3",
            "strength": "PP3_Moderate",
            "system_preview_included": False,
            "overlay_validated": True,
        },
        {
            "criterion": "PP3",
            "strength": "PP3_Moderate",
            "assessment_status": "met",
            "system_preview_included": True,
            "overlay_validated": False,
        },
        {
            "criterion": "PP3",
            "strength": "PP3_Moderate",
            "assessment_status": "not_assessed",
            "system_preview_included": True,
            "overlay_validated": True,
            "source_fact_ids": ["forged-source"],
        },
    ]

    score = compute_bayesian_score(rows, trusted_source_fact_ids={"forged-source"})

    assert score["strengths_used"] == []
    assert score["odds_path"] == 1.0


def test_bayesian_score_rejects_fabricated_source_fact_ids():
    row = _trusted(
        [
            {
                "criterion": "PP3",
                "strength": "PP3_Supporting",
                "assessment_status": "met",
                "system_preview_included": True,
                "overlay_validated": True,
            }
        ]
    )[0]
    score = compute_bayesian_score([row])
    assert score["strengths_used"] == []
    assert score["odds_path"] == 1.0


def test_generic_review_proposal_records_generic_odds_source():
    row = {
        "card_id": "generic-pm5",
        "criterion": "PM5",
        "strength": "PM5_Supporting",
        "assessment_status": "met",
        "proposal_status": "requires_user_review",
        "rule_verification": "review_only",
        "system_preview_included": True,
        "overlay_validated": True,
        "source_fact_ids": ["fixture-source"],
    }
    score = _score([row])
    assert score["odds_path"] == pytest.approx(2.08)
    assert score["evidence_odds"][0]["odds_source"] == "tavtigian_generic_strength"


def test_ba1_is_reported_as_special_and_not_multiplied():
    row = {
        "card_id": "ba1",
        "criterion": "BA1",
        "strength": "BA1",
        "assessment_status": "met",
        "proposal_status": "suggested",
        "rule_verification": "generic_svi",
        "system_preview_included": True,
        "overlay_validated": True,
        "source_fact_ids": ["fixture-source"],
    }
    score = _score([row])
    assert score["odds_path"] == 1.0
    assert score["included_card_ids"] == []
    assert score["special_criteria"][0]["criterion"] == "BA1"


if __name__ == "__main__":
    test_bayesian_score_with_pathogenic_evidence()
    test_bayesian_score_with_benign_evidence()
    test_bayesian_score_with_mixed_evidence()
    test_bayesian_score_empty()
    print("PASS test_acmg_bayesian_scorer")
