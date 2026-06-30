#!/usr/bin/env python3
"""Unit tests for the canonical ACMG semantic combiner."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "acmg_gate" / "semantic_combiner.py"
    spec = importlib.util.spec_from_file_location("acmg_semantic_combiner_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_ba1_benign_pass():
    """BA1 standalone counted -> computed Benign, reported Benign -> PASS."""
    sc = _load()
    bundle = {
        "classification": "Benign",
        "classification_status": "final classification",
        "final_classification_allowed": True,
        "compatibility_resolution": {
            "current_counted_evidence_resolved": [
                {"criterion": "BA1", "strength": "standalone"},
            ],
        },
    }
    result = sc.validate_bundle_semantics(bundle)
    assert result["semantic_combiner_status"] == "PASS", result
    assert result["computed_classification"] == "Benign", result
    assert result["semantic_violations"] == [], result


def test_ba1_pathogenic_fail():
    """BA1 standalone -> computed Benign, reported Pathogenic -> FAIL."""
    sc = _load()
    bundle = {
        "classification": "Pathogenic",
        "classification_status": "final classification",
        "final_classification_allowed": True,
        "compatibility_resolution": {
            "current_counted_evidence_resolved": [
                {"criterion": "BA1", "strength": "standalone"},
            ],
        },
    }
    result = sc.validate_bundle_semantics(bundle)
    assert result["semantic_combiner_status"] == "FAIL", result
    assert result["computed_classification"] == "Benign", result
    assert any("unsupported" in v.lower() or "pathogenic" in v.lower() for v in result["semantic_violations"]), result


def test_no_counted_evidence_lp_fail():
    """No counted evidence -> computed VUS, reported Likely_pathogenic -> FAIL."""
    sc = _load()
    bundle = {
        "classification": "Likely_pathogenic",
        "classification_status": "final classification",
        "final_classification_allowed": True,
        "compatibility_resolution": {
            "current_counted_evidence_resolved": [],
        },
    }
    result = sc.validate_bundle_semantics(bundle)
    assert result["semantic_combiner_status"] == "FAIL", result
    assert result["computed_classification"] == "VUS", result


def test_pm2_supporting_only_pathogenic_fail():
    """PM2_Supporting only -> computed VUS, reported Pathogenic -> FAIL."""
    sc = _load()
    bundle = {
        "classification": "Pathogenic",
        "classification_status": "final classification",
        "final_classification_allowed": True,
        "compatibility_resolution": {
            "current_counted_evidence_resolved": [
                {"criterion": "PM2", "strength": "supporting"},
            ],
        },
    }
    result = sc.validate_bundle_semantics(bundle)
    assert result["semantic_combiner_status"] == "FAIL", result
    assert result["computed_classification"] == "VUS", result


def test_conflict_pathogenic_fail():
    """Pathogenic + benign evidence conflict without resolution -> FAIL."""
    sc = _load()
    bundle = {
        "classification": "Pathogenic",
        "classification_status": "final classification",
        "final_classification_allowed": True,
        "compatibility_resolution": {
            "current_counted_evidence_resolved": [
                {"criterion": "PS1", "strength": "strong"},
                {"criterion": "BS1", "strength": "strong"},
            ],
        },
    }
    result = sc.validate_bundle_semantics(bundle)
    assert result["semantic_combiner_status"] == "FAIL", result
    assert result["computed_classification"] == "VUS", result


def test_draft_only_pass():
    """Draft-only with no final classification -> NOT_APPLICABLE."""
    sc = _load()
    bundle = {
        "classification": None,
        "classification_status": "draft",
        "final_classification_allowed": False,
        "compatibility_resolution": {},
    }
    result = sc.validate_bundle_semantics(bundle)
    assert result["semantic_combiner_status"] in ("PASS", "NOT_APPLICABLE"), result
    assert result["computed_classification"] is None, result
    assert result["semantic_violations"] == [], result


def test_pathogenic_evidence_likely_pathogenic_pass():
    """PS1 strong + PM2 moderate + PP3 supporting -> Likely_pathogenic -> PASS."""
    sc = _load()
    bundle = {
        "classification": "Likely_pathogenic",
        "classification_status": "final classification",
        "final_classification_allowed": True,
        "compatibility_resolution": {
            "current_counted_evidence_resolved": [
                {"criterion": "PS1", "strength": "strong"},
                {"criterion": "PM2", "strength": "moderate"},
                {"criterion": "PP3", "strength": "supporting"},
            ],
        },
    }
    result = sc.validate_bundle_semantics(bundle)
    assert result["semantic_combiner_status"] == "PASS", result
    assert result["computed_classification"] == "Likely_pathogenic", result


def test_benign_evidence_likely_benign_pass():
    """BS1 strong + BP1 supporting -> Likely_benign -> PASS."""
    sc = _load()
    bundle = {
        "classification": "Likely_benign",
        "classification_status": "final classification",
        "final_classification_allowed": True,
        "compatibility_resolution": {
            "current_counted_evidence_resolved": [
                {"criterion": "BS1", "strength": "strong"},
                {"criterion": "BP1", "strength": "supporting"},
            ],
        },
    }
    result = sc.validate_bundle_semantics(bundle)
    assert result["semantic_combiner_status"] == "PASS", result
    assert result["computed_classification"] == "Likely_benign", result


def test_pvs1_pm2_likely_pathogenic_pass():
    """PVS1 very_strong + PM2 moderate -> Likely_pathogenic -> PASS."""
    sc = _load()
    bundle = {
        "classification": "Likely_pathogenic",
        "classification_status": "final classification",
        "final_classification_allowed": True,
        "compatibility_resolution": {
            "current_counted_evidence_resolved": [
                {"criterion": "PVS1", "strength": "very_strong"},
                {"criterion": "PM2", "strength": "moderate"},
            ],
        },
    }
    result = sc.validate_bundle_semantics(bundle)
    assert result["semantic_combiner_status"] == "PASS", result
    assert result["computed_classification"] == "Likely_pathogenic", result


def test_computed_vs_reported_mismatch_fails():
    """Computed VUS vs reported Pathogenic -> FAIL."""
    sc = _load()
    bundle = {
        "classification": "Pathogenic",
        "classification_status": "final classification",
        "final_classification_allowed": True,
        "compatibility_resolution": {
            "current_counted_evidence_resolved": [
                {"criterion": "PP3", "strength": "supporting"},
            ],
        },
    }
    result = sc.validate_bundle_semantics(bundle)
    assert result["semantic_combiner_status"] == "FAIL", result
    assert result["computed_classification"] == "VUS", result


if __name__ == "__main__":
    test_ba1_benign_pass()
    test_ba1_pathogenic_fail()
    test_no_counted_evidence_lp_fail()
    test_pm2_supporting_only_pathogenic_fail()
    test_conflict_pathogenic_fail()
    test_draft_only_pass()
    test_pathogenic_evidence_likely_pathogenic_pass()
    test_benign_evidence_likely_benign_pass()
    test_pvs1_pm2_likely_pathogenic_pass()
    test_computed_vs_reported_mismatch_fails()
    print("PASS test_acmg_semantic_combiner")
