"""PS1/PM5 Amino Acid Equivalence overlay tool.

MCP tool: acmg_overlay_ps1_pm5

PS1: same amino acid change as established pathogenic variant → Strong (PS1)
PM5: different missense at same residue as pathogenic → Moderate (PM5)
"""

from __future__ import annotations

from typing import Any


def overlay_ps1_pm5(
    clinvar_same_aa_pathogenic: bool = False,
    clinvar_same_aa_pathogenic_count: int = 0,
    clinvar_same_residue_pathogenic: bool = False,
    clinvar_same_residue_pathogenic_count: int = 0,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """Determine PS1 or PM5 evidence from ClinVar amino acid comparisons.

    Args:
        clinvar_same_aa_pathogenic: Whether same AA change is annotated as pathogenic
        clinvar_same_aa_pathogenic_count: Number of pathogenic submissions for same AA
        clinvar_same_residue_pathogenic: Whether different AA at same residue is pathogenic
        clinvar_same_residue_pathogenic_count: Number of pathogenic submissions at same residue
        vcep_override: VCEP-specific rule name
    """
    from .base import output_template

    if vcep_override:
        return output_template("PS1/PM5", vcep_override, reason=f"VCEP override: {vcep_override}")

    # PS1: Same amino acid change as established pathogenic
    if clinvar_same_aa_pathogenic:
        strength = "PS1" if clinvar_same_aa_pathogenic_count >= 2 else "PS1_Supporting"
        return output_template(
            "PS1", strength,
            reason=f"Same amino acid change identified as pathogenic in ClinVar "
                   f"({clinvar_same_aa_pathogenic_count} submissions). "
                   "Per ACMG: PS1 — same AA change as established pathogenic variant.",
            source_of_truth="ClinVar",
        )

    # PM5: Different missense at same residue as pathogenic
    if clinvar_same_residue_pathogenic:
        strength = "PM5" if clinvar_same_residue_pathogenic_count >= 2 else "PM5_Supporting"
        return output_template(
            "PM5", strength,
            reason=f"Different missense at same residue identified as pathogenic in "
                   f"ClinVar ({clinvar_same_residue_pathogenic_count} submissions). "
                   "Per ACMG: PM5 — novel missense at residue with known pathogenic variant.",
            source_of_truth="ClinVar",
        )

    # No ClinVar comparison data
    if not clinvar_same_aa_pathogenic and not clinvar_same_residue_pathogenic:
        return output_template(
            "PS1/PM5", "not_met",
            status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No ClinVar evidence for same amino acid or same residue "
                   "pathogenic variant. PS1/PM5 not met.",
            source_of_truth="ClinVar",
            next_action="Search ClinVar for variants at this residue.",
        )

    return output_template(
        "PS1/PM5", "not_met",
        status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason="Insufficient ClinVar evidence for PS1/PM5 comparison.",
        source_of_truth="ClinVar",
    )


__all__ = ["overlay_ps1_pm5"]
