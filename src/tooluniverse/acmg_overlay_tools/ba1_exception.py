"""BA1 Exception List overlay tool.

MCP tool: acmg_overlay_ba1_exception
"""
from __future__ import annotations
from typing import Any


def overlay_ba1_exception(
    gnomad_af_popmax: float = 0.0,
    gnomad_af_global: float = 0.0,
    gene_disease_prevalence: str = "rare",
    vcep_override: str | None = None,
) -> dict[str, Any]:
    from .base import output_template, vcep_deferred_template
    if vcep_override:
        return vcep_deferred_template(
            "BA1",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )
    if gnomad_af_popmax > 0.05 or gnomad_af_global > 0.05:
        return output_template("BA1", "BA1",
            reason=f"gnomAD AF={gnomad_af_global:.4f}, popmax={gnomad_af_popmax:.4f}. "
                   "Exceeds 5% stand-alone benign threshold. BA1 met.",
            source_of_truth="gnomAD")
    return output_template("BA1", "not_met", status="not_applicable",
        route_outcome="overlay_not_applicable",
        reason="Population frequency below BA1 threshold (5%). BA1 not met.",
        source_of_truth="gnomAD")

__all__ = ["overlay_ba1_exception"]
