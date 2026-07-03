"""Unit tests for ACMG_overlay_pp3_bp4 — Pejaver 2022 calibration."""

from __future__ import annotations
from tooluniverse.acmg_overlay_tools.pp3_bp4 import overlay_pp3_bp4


def test_pp3_strong_revel():
    """REVEL >= 0.932 → PP3_Strong."""
    r = overlay_pp3_bp4(revel_score=0.95)
    assert r["strength"] == "PP3_Strong"
    assert r["counted"] is True


def test_pp3_standard_revel():
    """REVEL >= 0.7 → PP3."""
    r = overlay_pp3_bp4(revel_score=0.75)
    assert r["strength"] == "PP3"


def test_bp4_revel_low():
    """REVEL < 0.15 and CADD < 15 → BP4."""
    r = overlay_pp3_bp4(revel_score=0.10, cadd_phred=10)
    assert r["strength"] == "BP4"


def test_no_evidence_interval():
    """REVEL in (0.29, 0.64) with no concordant CADD → no PP3/BP4."""
    r = overlay_pp3_bp4(revel_score=0.50)
    assert r["strength"] == "not_met"


def test_no_revel_fallback():
    """No REVEL score → not_assessed (forbidden to use CADD/SIFT/PolyPhen fallback)."""
    r = overlay_pp3_bp4(cadd_phred=30, sift_score=0.001, polyphen_score=0.99)
    assert r["strength"] == "not_assessed"
    assert "Pejaver" in r["reason"]
