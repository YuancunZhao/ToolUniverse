"""Unit tests for ACMG_overlay_pp3_bp4 — Pejaver 2022 calibration."""

from __future__ import annotations
from tooluniverse.acmg_overlay_tools.pp3_bp4 import overlay_pp3_bp4


def test_pp3_strong_revel():
    """REVEL >= 0.932 → PP3_Strong."""
    r = overlay_pp3_bp4(revel_score=0.95)
    assert r["strength"] == "PP3_Strong"
    assert r["counted"] is True


def test_revel_supporting_moderate_and_strong_intervals():
    """REVEL uses Pejaver 2022 calibrated intervals."""
    assert overlay_pp3_bp4(revel_score=0.70)["strength"] == "PP3_Supporting"
    assert overlay_pp3_bp4(revel_score=0.80)["strength"] == "PP3_Moderate"
    assert overlay_pp3_bp4(revel_score=0.932)["strength"] == "PP3_Strong"


def test_revel_benign_intervals():
    """REVEL benign-side intervals preserve calibrated BP4 strengths."""
    assert overlay_pp3_bp4(revel_score=0.003)["strength"] == "BP4_VeryStrong"
    assert overlay_pp3_bp4(revel_score=0.010)["strength"] == "BP4_Strong"
    assert overlay_pp3_bp4(revel_score=0.10)["strength"] == "BP4_Moderate"
    assert overlay_pp3_bp4(revel_score=0.20)["strength"] == "BP4_Supporting"


def test_no_evidence_interval():
    """REVEL in (0.290, 0.644) → no PP3/BP4."""
    r = overlay_pp3_bp4(revel_score=0.50)
    assert r["strength"] == "not_assessed"
    assert r["counted"] is False


def test_cadd_selected_tool_uses_cadd_interval_not_voting():
    """CADD can count only through its own calibrated interval."""
    r = overlay_pp3_bp4(selected_tool="CADD", cadd_phred=26.0, sift_score=0.001, polyphen_score=0.99)
    assert r["criterion"] == "PP3"
    assert r["strength"] == "PP3_Supporting"
    assert "majority vote" in r["reason"]


def test_no_majority_vote_when_selected_score_missing():
    """Selected predictor must have a raw score; other predictors are not substituted."""
    r = overlay_pp3_bp4(selected_tool="REVEL", cadd_phred=30, sift_score=0.001, polyphen_score=0.99)
    assert r["strength"] == "not_assessed"
    assert r["counted"] is False


def test_default_hierarchy_uses_revel_when_present():
    """When no tool is specified, the fixed hierarchy uses REVEL before other supplied scores."""
    r = overlay_pp3_bp4(revel_score=0.80, cadd_phred=30.0)
    assert r["strength"] == "PP3_Moderate"
    assert "revel" in r["source_of_truth"]


def test_no_revel_fallback_can_use_other_calibrated_selected_tool():
    """No REVEL is fine if another calibrated predictor is selected explicitly."""
    r = overlay_pp3_bp4(selected_tool="VEST4", vest4_score=0.97)
    assert r["strength"] == "PP3_Strong"


def test_unselected_multiple_non_revel_scores_use_fixed_hierarchy_not_vote():
    """Multiple non-REVEL scores use the documented fixed hierarchy, not consensus voting."""
    r = overlay_pp3_bp4(cadd_phred=30, sift_score=0.001, polyphen_score=0.99)
    assert r["strength"] == "PP3_Moderate"
    assert "cadd" in r["source_of_truth"]


def test_spliceai_only_not_used_for_missense_pp3_bp4():
    """SpliceAI routes to splicing overlays, not missense PP3/BP4."""
    r = overlay_pp3_bp4(spliceai_ds_dg=0.9)
    assert r["strength"] == "not_assessed"
    assert r["counted"] is False
    assert "SpliceAI" in r["next_action"]
