"""Unit tests for ACMG_overlay_pm2 — ClinGen SVI PM2 v1.0."""

from __future__ import annotations
from tooluniverse.acmg_overlay_tools.pm2 import overlay_pm2


def test_pm2_absent():
    """Absent from gnomAD with adequate coverage → PM2_Supporting."""
    r = overlay_pm2(gnomad_af_global=0.0, gnomad_ac=0, gnomad_an=125748, coverage_adequate=True)
    assert r["strength"] == "PM2_Supporting"
    assert r["counted"] is True


def test_pm2_present_not_rare():
    """Present at >0.01% → not met."""
    r = overlay_pm2(gnomad_af_global=0.02, gnomad_ac=2000, gnomad_an=100000)
    assert r["strength"] == "not_met"


def test_pm2_ba1_threshold():
    """>5% frequency → BA1 applies, PM2 not applicable."""
    r = overlay_pm2(gnomad_af_global=0.06, gnomad_af_popmax=0.08, gnomad_an=100000)
    assert r["strength"] == "not_met"
    assert r["route_outcome"] == "overlay_not_applicable"


def test_pm2_no_data():
    """No gnomAD data → not_assessed."""
    r = overlay_pm2()
    assert r["strength"] == "not_assessed"


def test_pm2_coverage_inadequate():
    """Inadequate coverage → not_assessed."""
    r = overlay_pm2(gnomad_af_global=0.0, gnomad_ac=0, gnomad_an=125748, coverage_adequate=False)
    assert r["strength"] == "not_assessed"
