"""Tests for ACMG evidence conflict detection."""

from __future__ import annotations

from tooluniverse.acmg.summary import detect_conflicts
from tooluniverse.acmg.rule_catalog import rule_for_criterion


def _previewed(criterion: str, strength: str, fact_id: str) -> dict:
    rule = rule_for_criterion(criterion)
    return {
        "card_id": f"card-{criterion}",
        "criterion": criterion,
        "strength": strength,
        "evidence_status": "rule_mapped",
        "rule_source": {"type": "versioned_svi"},
        "verification_dimensions": {"identity_status": "matched"},
        "calculation_roles": {"automatic": True, "verified": True},
        "source_fact_ids": [fact_id],
        "rule_id": rule.get("rule_id", ""),
        "rule_version": rule.get("version", ""),
    }


def _detect(rows):
    trusted = {
        fact_id
        for row in rows
        for fact_id in row.get("source_fact_ids", [])
        if isinstance(fact_id, str)
    }
    return detect_conflicts(rows, known_source_fact_ids=trusted)


def test_no_conflicts_when_all_pathogenic():
    results = [
        _previewed("PVS1", "PVS1", "fixture-pvs1"),
        _previewed("PM2", "PM2_Supporting", "fixture-pm2"),
        _previewed("PP3", "PP3_Supporting", "fixture-pp3"),
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


def test_source_less_rows_cannot_create_a_conflict():
    results = [
        {
            "criterion": "BA1",
            "strength": "BA1",
        },
        {
            "criterion": "PVS1",
            "strength": "PVS1_VeryStrong",
        },
        {
            "criterion": "PS1",
            "strength": "PS1_Strong",
        },
    ]
    report = _detect(results)
    assert report["has_conflicts"] is False


def test_empty_results():
    report = detect_conflicts([])
    assert report["has_conflicts"] is False
