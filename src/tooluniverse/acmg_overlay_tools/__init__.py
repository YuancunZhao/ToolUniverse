"""Overlay MCP Tools for ACMG variant classification.

Each module implements a deterministic ACMG criterion overlay as an
independent tool. LLM collects evidence; tools do judgment.

Key tools:
- route_overlays(): determine which overlays apply
- overlay_pm2(), overlay_pp3_bp4(), ... : individual criterion tools
- combine_criteria(): aggregate into five-tier classification
"""

from __future__ import annotations

from .router import route_overlays
from .combine import combine_criteria
from .pm2 import overlay_pm2
from .pp3_bp4 import overlay_pp3_bp4
from .ps1_pm5 import overlay_ps1_pm5
from .ba1_exception import overlay_ba1_exception
from .benign_context import overlay_benign_context
from .overlays import (
    overlay_case_enrichment,
    overlay_de_novo,
    overlay_functional_assay,
    overlay_pm1_bp1,
    overlay_pm3_in_trans,
    overlay_protein_length,
    overlay_ps1_splicing,
    overlay_pvs1_lof,
    overlay_pvs1_splicing,
    overlay_segregation,
    overlay_source_review,
)

__all__ = [
    "combine_criteria",
    "overlay_ba1_exception",
    "overlay_benign_context",
    "overlay_case_enrichment",
    "overlay_de_novo",
    "overlay_functional_assay",
    "overlay_pm1_bp1",
    "overlay_pm2",
    "overlay_pm3_in_trans",
    "overlay_pp3_bp4",
    "overlay_protein_length",
    "overlay_ps1_pm5",
    "overlay_ps1_splicing",
    "overlay_pvs1_lof",
    "overlay_pvs1_splicing",
    "overlay_segregation",
    "overlay_source_review",
    "route_overlays",
]
