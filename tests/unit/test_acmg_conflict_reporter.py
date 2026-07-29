"""Tests for ACMG evidence conflict detection."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg.summary import detect_conflicts
from tooluniverse.acmg.rule_catalog import rule_for_criterion


def _previewed(criterion: str, strength: str, fact_id: str) -> dict:
    rule = rule_for_criterion(criterion)
    return {
        "criterion": criterion,
        "strength": strength,
        "assessment_status": "met",
        "system_preview_included": True,
        "overlay_validated": True,
        "source_fact_ids": [fact_id],
        "rule_id": rule["rule_id"],
        "rule_version": rule["version"],
    }


def _detect(rows):
    trusted = {
        fact_id
        for row in rows
        for fact_id in row.get("source_fact_ids", [])
        if isinstance(fact_id, str)
    }
    return detect_conflicts(rows, trusted_source_fact_ids=trusted)


def test_no_conflicts_when_all_pathogenic():
    results = [
        {"criterion": "PVS1", "strength": "PVS1_VeryStrong"},
        {"criterion": "PM2", "strength": "PM2_Supporting"},
        {"criterion": "PP3", "strength": "PP3_Supporting"},
    ]
    report = _detect(results)
    assert report["has_conflicts"] is False
    assert report["conflicts"] == []


def test_conflict_when_pathogenic_and_benign():
    results = [
        _previewed("PS2", "PS2", "fixture-ps2"),
        _previewed("BS3", "BS3", "fixture-bs3"),
    ]
    report = _detect(results)
    assert report["has_conflicts"] is True
    assert len(report["conflicts"]) > 0
    assert "PS2" in report["conflicts"][0]["criteria"]
    assert "BS3" in report["conflicts"][0]["criteria"]


def test_non_catalogued_ba1_cannot_create_a_conflict():
    results = [
        {
            "criterion": "BA1",
            "strength": "BA1",
            "assessment_status": "met",
            "system_preview_included": True,
            "overlay_validated": True,
            "source_fact_ids": ["fixture-ba1"],
        },
        {
            "criterion": "PVS1",
            "strength": "PVS1_VeryStrong",
            "assessment_status": "met",
            "system_preview_included": True,
            "overlay_validated": True,
            "source_fact_ids": ["fixture-pvs1"],
        },
        {
            "criterion": "PS1",
            "strength": "PS1_Strong",
            "assessment_status": "met",
            "system_preview_included": True,
            "overlay_validated": True,
            "source_fact_ids": ["fixture-ps1"],
        },
    ]
    report = _detect(results)
    assert report["has_conflicts"] is False


def test_empty_results():
    report = detect_conflicts([])
    assert report["has_conflicts"] is False


def test_unflagged_rows_cannot_create_conflicts():
    report = detect_conflicts(
        [
            {"criterion": "PS1", "strength": "PS1_Strong"},
            {"criterion": "BS1", "strength": "BS1_Strong"},
        ]
    )

    assert report["has_conflicts"] is False


if __name__ == "__main__":
    test_no_conflicts_when_all_pathogenic()
    test_conflict_when_pathogenic_and_benign()
    test_non_catalogued_ba1_cannot_create_a_conflict()
    test_empty_results()
    print("PASS test_acmg_conflict_reporter")
