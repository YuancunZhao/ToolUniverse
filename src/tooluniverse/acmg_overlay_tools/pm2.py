"""PM2 Absence/Rarity overlay tool.

MCP tool: acmg_overlay_pm2

Per ClinGen SVI PM2 Recommendation Version 1.0 (approved 2020-09-04):
PM2 is applied as PM2_Supporting when absent from population controls.
"""

from __future__ import annotations

from typing import Any


def overlay_pm2(
    gnomad_af_global: float = 0.0,
    gnomad_af_popmax: float = 0.0,
    gnomad_ac: int = 0,
    gnomad_an: int = 0,
    coverage_adequate: bool = True,
    disease_prevalence: str = "rare",
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """Determine PM2 evidence strength from population frequency data.

    Args:
        gnomad_af_global: Global allele frequency from gnomAD
        gnomad_af_popmax: Maximum population-specific AF
        gnomad_ac: Allele count
        gnomad_an: Allele number (total alleles tested)
        coverage_adequate: Whether the variant's region is adequately covered
        disease_prevalence: "rare" or "common" — affects BA1 threshold
        vcep_override: VCEP-specific rule name if applicable
    """
    from .base import output_template, vcep_deferred_template

    # VCEP override takes precedence
    if vcep_override:
        return vcep_deferred_template(
            "PM2",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )

    # No data available
    if gnomad_an == 0:
        return output_template(
            "PM2", "not_assessed",
            status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="Population frequency data unavailable (AN=0). Cannot assess PM2.",
            source_of_truth="gnomAD",
        )

    # Coverage inadequate
    if not coverage_adequate:
        return output_template(
            "PM2", "not_assessed",
            status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="Variant locus coverage inadequate. Cannot confirm true absence.",
            source_of_truth="gnomAD coverage metrics",
            next_action="Check sequencing depth and mappability at this locus.",
        )

    # BA1 stand-alone benign check (>5% AF in any population)
    if gnomad_af_popmax > 0.05 or gnomad_af_global > 0.05:
        return output_template(
            "PM2", "not_met",
            status="not_applicable",
            route_outcome="overlay_not_applicable",
            reason=f"gnomAD AF={gnomad_af_global:.4f}, popmax={gnomad_af_popmax:.4f}. "
                   "Exceeds BA1 stand-alone benign threshold (5%). PM2 not applicable.",
            source_of_truth="gnomAD",
            next_action="Apply BA1 stand-alone benign instead.",
        )

    # BS1 check (>1% population frequency for rare disease, per ClinGen)
    if disease_prevalence == "rare" and (gnomad_af_popmax > 0.01 or gnomad_af_global > 0.01):
        return output_template(
            "PM2", "not_met",
            status="not_applicable",
            route_outcome="overlay_not_applicable",
            reason=f"gnomAD AF={gnomad_af_global:.4f}. Too common for rare disease. "
                   "Consider BS1 instead of PM2.",
            source_of_truth="gnomAD",
            next_action="Apply BS1 if frequency exceeds disease-specific threshold.",
        )

    # Extremely rare but present (<0.001% or 1 in 100K)
    if gnomad_ac > 0 and gnomad_af_global < 0.00001:
        return output_template(
            "PM2", "PM2_Supporting",
            reason=f"Extremely rare: gnomAD AC={gnomad_ac}, AN={gnomad_an}, "
                   f"AF={gnomad_af_global:.6f}. Per ClinGen SVI PM2 v1.0: "
                   "PM2_Supporting when extremely rare and compatible with disease prevalence.",
            source_of_truth="gnomAD",
            next_action="Pair with other evidence. PVS1+PM2_Supporting = Likely Pathogenic.",
        )

    # Absent from population controls
    if gnomad_ac == 0:
        return output_template(
            "PM2", "PM2_Supporting",
            reason=f"Absent from gnomAD: AC=0, AN={gnomad_an}. "
                   "Per ClinGen SVI PM2 Recommendation v1.0: "
                   "PM2_Supporting when absent from population controls with adequate coverage. "
                   "Moderate strength (PM2) only per VCEP specification.",
            source_of_truth="gnomAD",
            next_action="If PVS1 also met, PVS1+PM2_Supporting = Likely Pathogenic.",
        )

    # Present at non-trivial frequency
    return output_template(
        "PM2", "not_met",
        status="not_applicable",
        route_outcome="overlay_not_applicable",
        reason=f"gnomAD AF={gnomad_af_global:.6f}, AC={gnomad_ac}, AN={gnomad_an}. "
               "Variant present in population at frequency incompatible with PM2.",
        source_of_truth="gnomAD",
    )


__all__ = ["overlay_pm2"]
