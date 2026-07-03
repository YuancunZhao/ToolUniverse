"""Unit tests for ACMG_overlay_de_novo — SVI De Novo Criteria v1.1."""

from __future__ import annotations
from tooluniverse.acmg_overlay_tools.overlays import overlay_de_novo


def test_ps2_strong():
    """Confirmed de novo + parentage + highly specific phenotype → PS2 (2pt)."""
    r = overlay_de_novo(de_novo_confirmed=True, paternity_confirmed=True, phenotype_highly_specific=True)
    assert r["strength"] == "PS2"


def test_ps2_moderate():
    """Confirmed de novo + parentage + consistent phenotype → PS2_Moderate (1pt)."""
    r = overlay_de_novo(de_novo_confirmed=True, paternity_confirmed=True, phenotype_consistent=True)
    assert r["strength"] == "PS2_Moderate"


def test_pm6_no_parentage():
    """De novo but paternity not confirmed → PM6."""
    r = overlay_de_novo(de_novo_confirmed=True, paternity_confirmed=False)
    assert r["strength"] == "PM6"


def test_not_de_novo():
    """Not de novo → not_assessed."""
    r = overlay_de_novo(de_novo_confirmed=False)
    assert r["strength"] == "not_assessed"


def test_ps2_with_low_heterogeneity():
    """PS2 + low genetic heterogeneity → bonus point, still PS2."""
    r = overlay_de_novo(de_novo_confirmed=True, paternity_confirmed=True, phenotype_highly_specific=True, genetic_heterogeneity_low=True)
    assert r["strength"] == "PS2"
