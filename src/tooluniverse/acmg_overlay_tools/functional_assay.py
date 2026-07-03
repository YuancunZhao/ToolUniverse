"""PS3/BS3 Functional Assay overlay tool.

Per ClinGen SVI Brnich 2019 functional assay classification (PMID:31892348).
"""

from __future__ import annotations
from typing import Any
from .base import output_template, vcep_deferred_template


def overlay_functional_assay(
    functional_evidence: str = "",
    assay_type: str = "",
    assay_category: str = "",
    assay_applicable_to_disease_mechanism: bool = False,
    variant_specific: bool = False,
    replicated: bool = False,
    has_controls: bool = False,
    statistically_significant: bool = False,
    effect_direction: str = "",
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """PS3/BS3 per ClinGen SVI functional assay classification (Brnich 2019, PMID:31892348)."""
    if vcep_override:
        return vcep_deferred_template(
            "PS3/BS3",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )
    if not functional_evidence:
        return output_template("PS3/BS3", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No functional assay evidence provided.",
            next_action="Search PubMed (full text) for functional studies of this variant using "
                         "the variant HGVS, rsID, or protein change as query terms.")
    if not variant_specific:
        return output_template("PS3/BS3", "not_applicable",
            status="not_assessed", route_outcome="overlay_not_assessed",
            reason="Functional evidence is gene-level, not variant-specific. PS3/BS3 requires "
                   "variant-specific functional data.",
            next_action="Search for functional studies specifically testing this variant "
                         "(not general gene function).")

    if replicated and has_controls and statistically_significant:
        level = 1
    elif has_controls and statistically_significant:
        level = 2
    elif has_controls:
        level = 3
    elif variant_specific:
        level = 4
    else:
        level = 5

    is_lof = "loss" in effect_direction.lower() or "lof" in effect_direction.lower()
    is_no_effect = "no" in effect_direction.lower() or "normal" in effect_direction.lower() or "wt" in effect_direction.lower()

    if level == 1:
        if is_no_effect:
            return output_template("BS3", "BS3",
                reason=f"Level 1 validated assay ({assay_type}) shows no functional effect. BS3 applies.",
                source_of_truth="PubMed functional study")
        return output_template("PS3", "PS3",
            reason=f"Level 1 validated assay ({assay_type}) shows {effect_direction}. PS3 applies.",
            source_of_truth="PubMed functional study")
    elif level == 2:
        if is_no_effect:
            return output_template("BS3", "BS3_Supporting",
                reason=f"Level 2 well-established assay ({assay_type}) shows no effect. BS3_Supporting.",
                source_of_truth="PubMed functional study")
        return output_template("PS3", "PS3_Moderate",
            reason=f"Level 2 well-established assay ({assay_type}) shows {effect_direction}. PS3_Moderate.",
            source_of_truth="PubMed functional study")
    elif level == 3:
        return output_template("PS3", "PS3_Supporting",
            reason=f"Level 3 emerging assay ({assay_type}) shows {effect_direction}. PS3_Supporting.",
            source_of_truth="PubMed functional study")
    elif level == 4:
        return output_template("PS3", "PS3_Supporting",
            reason=f"Level 4 supportive assay ({assay_type}) shows {effect_direction}. "
                   "PS3_Supporting. Not replicated — consider independent verification.",
            source_of_truth="PubMed functional study")
    else:
        return output_template("PS3/BS3", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason=f"Level 5 non-validated assay ({assay_type}). Cannot assign PS3/BS3. "
                   "Needs: replication, controls, or statistical validation.",
            source_of_truth="PubMed functional study")
