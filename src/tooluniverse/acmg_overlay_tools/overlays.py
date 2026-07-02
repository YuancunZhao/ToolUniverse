"""Overlay tool stubs: functional_assay, case_enrichment, segregation,
   de_novo, pm3_in_trans, protein_length, source_review, pvs1_lof,
   pvs1_splicing, ps1_splicing, pm1_bp1.
Each stub returns not_assessed with a recommendation to collect evidence.
"""

from __future__ import annotations
from typing import Any
from .base import output_template


def overlay_functional_assay(
    functional_evidence: str = "",
    assay_type: str = "",
    effect_magnitude: str = "",
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return output_template("PS3/BS3", vcep_override, reason=f"VCEP: {vcep_override}")
    if not functional_evidence:
        return output_template("PS3/BS3", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No functional assay evidence provided.",
            next_action="Search PubMed for functional studies of this variant.")
    # Simple heuristic: minigene or in vitro assay with loss-of-function
    if assay_type in ("minigene", "in_vitro", "enzymatic", "reporter") and "loss" in functional_evidence.lower():
        return output_template("PS3", "PS3_Supporting",
            reason=f"{assay_type}: {functional_evidence[:100]}. PS3_Supporting per ClinGen.",
            source_of_truth="PubMed literature")
    return output_template("PS3/BS3", "not_assessed", status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason=f"Evidence type '{assay_type}' requires expert review.",
        source_of_truth="PubMed literature")


def overlay_case_enrichment(
    case_count: int = 0, control_count: int = 0,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return output_template("PS4", vcep_override, reason=f"VCEP: {vcep_override}")
    if case_count == 0:
        return output_template("PS4", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No case enrichment data provided.",
            next_action="Search literature for case-control studies.")
    if case_count >= 5 and control_count >= 100:
        return output_template("PS4", "PS4_Supporting",
            reason=f"{case_count} cases vs {control_count} controls. PS4_Supporting.",
            source_of_truth="PubMed literature")
    return output_template("PS4", "not_assessed", status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason=f"Insufficient case data: {case_count} cases.",
        source_of_truth="PubMed literature")


def overlay_segregation(
    segregation_present: bool = False,
    affected_relatives: int = 0,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return output_template("PP1/BS4/PP4", vcep_override, reason=f"VCEP: {vcep_override}")
    if not segregation_present:
        return output_template("PP1/BS4/PP4", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No segregation data provided.",
            next_action="Obtain family segregation data if available.")
    if affected_relatives >= 5:
        return output_template("PP1", "PP1_Moderate",
            reason=f"Segregation in {affected_relatives} affected relatives.",
            source_of_truth="Family study")
    if affected_relatives >= 3:
        return output_template("PP1", "PP1",
            reason=f"Segregation in {affected_relatives} affected relatives.",
            source_of_truth="Family study")
    return output_template("PP1", "PP1_Supporting",
        reason=f"Segregation in {affected_relatives} affected relatives.",
        source_of_truth="Family study")


def overlay_de_novo(
    de_novo_confirmed: bool = False,
    paternity_confirmed: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return output_template("PS2/PM6", vcep_override, reason=f"VCEP: {vcep_override}")
    if not de_novo_confirmed:
        return output_template("PS2/PM6", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No de novo evidence provided.",
            next_action="Trio testing required for de novo assessment.")
    if de_novo_confirmed and paternity_confirmed:
        return output_template("PS2", "PS2",
            reason="Confirmed de novo with paternity/maternity confirmed.",
            source_of_truth="Trio testing")
    return output_template("PM6", "PM6",
        reason="De novo observed. Paternity not confirmed → PM6 per ACMG.",
        source_of_truth="Trio testing")


def overlay_pm3_in_trans(
    second_variant_pathogenic: bool = False,
    phase_confirmed: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return output_template("PM3", vcep_override, reason=f"VCEP: {vcep_override}")
    if not second_variant_pathogenic:
        return output_template("PM3", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No second pathogenic variant in trans identified.",
            next_action="Test for second variant in recessive gene.")
    if phase_confirmed:
        return output_template("PM3", "PM3",
            reason="Second pathogenic variant confirmed in trans.",
            source_of_truth="Genetic testing")
    return output_template("PM3", "PM3_Supporting",
        reason="Second pathogenic variant identified. Phase not confirmed.",
        source_of_truth="Genetic testing")


def overlay_protein_length(
    variant_type: str = "",
    in_repeat_region: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return output_template("PM4/BP3", vcep_override, reason=f"VCEP: {vcep_override}")
    if variant_type in ("indel_inframe", "null"):
        return output_template("PM4", "PM4",
            reason=f"Protein length change due to {variant_type}.",
            source_of_truth="Variant annotation")
    return output_template("PM4/BP3", "not_met", status="not_applicable",
        route_outcome="overlay_not_applicable",
        reason="Variant does not change protein length.")


def overlay_source_review(
    clinvar_review_stars: int = 0,
    clinvar_pathogenic_submitters: int = 0,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return output_template("PP5/BP6", vcep_override, reason=f"VCEP: {vcep_override}")
    # ClinGen SVI: PP5/BP6 are deprecated — use as leads to primary evidence
    return output_template("PP5/BP6", "not_counted",
        status="not_applicable",
        route_outcome="overlay_not_applicable",
        reason="ClinGen SVI recommends discontinuing PP5/BP6. "
               "Use ClinVar assertions as leads to retrieve primary evidence.",
        guidance_authority="ClinGen/SVI primary",
        next_action="Retrieve primary evidence supporting ClinVar classification.")


def overlay_pvs1_lof(
    variant_type: str = "",
    gene_lof_mechanism: bool = False,
    lof_intolerant: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return output_template("PVS1", vcep_override, reason=f"VCEP: {vcep_override}")
    if variant_type not in ("null", "frameshift", "nonsense"):
        return output_template("PVS1", "not_met", status="not_applicable",
            route_outcome="overlay_not_applicable",
            reason=f"PVS1 only applies to null variants (nonsense, frameshift, "
                   f"canonical splice). Variant type: {variant_type}.")
    if not gene_lof_mechanism:
        return output_template("PVS1", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="Gene LOF mechanism not confirmed. PVS1 requires established "
                   "LOF as disease mechanism.",
            next_action="Check ClinGen gene-disease validity and gnomAD constraint.")
    if "nonsense" in variant_type or "frameshift" in variant_type:
        strength = "PVS1" if lof_intolerant else "PVS1_Strong"
        return output_template("PVS1", strength,
            reason=f"Null variant ({variant_type}) in LOF-mechanism gene. "
                   f"LOF intolerance: {lof_intolerant}.",
            source_of_truth="ClinGen, gnomAD constraint")


def overlay_pvs1_splicing(
    splice_prediction: str = "",
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return output_template("PVS1/BP7", vcep_override, reason=f"VCEP: {vcep_override}")
    if not splice_prediction:
        return output_template("PVS1/BP7", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No splice prediction data.")
    return output_template("BP7", "BP7",
        reason=f"Splice prediction: {splice_prediction}. May support BP7 for synonymous.",
        source_of_truth="SpliceAI")


def overlay_ps1_splicing(
    same_splice_event_pathogenic: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return output_template("PS1_splice", vcep_override, reason=f"VCEP: {vcep_override}")
    if not same_splice_event_pathogenic:
        return output_template("PS1_splice", "not_met", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No evidence of same predicted splicing event as known pathogenic.")
    return output_template("PS1", "PS1",
        reason="Same predicted splicing event as established pathogenic variant.",
        source_of_truth="SpliceAI, literature")


def overlay_pm1_bp1(
    in_functional_domain: bool = False,
    domain_has_pathogenic_enrichment: bool = False,
    gene_missense_mechanism: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return output_template("PM1/BP1", vcep_override, reason=f"VCEP: {vcep_override}")
    if in_functional_domain and domain_has_pathogenic_enrichment:
        return output_template("PM1", "PM1_Moderate",
            reason="Variant in functional domain with pathogenic missense enrichment.",
            source_of_truth="InterPro, ClinVar")
    # BP1: missense in LOF-only gene
    if not gene_missense_mechanism:
        return output_template("BP1", "BP1_Supporting",
            reason="Missense in gene where only LOF causes disease. BP1 applicable.",
            source_of_truth="ClinGen, gnomAD constraint")
    return output_template("PM1/BP1", "not_met", status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason="No domain or constraint evidence for PM1/BP1.")


__all__ = [
    "overlay_case_enrichment",
    "overlay_de_novo",
    "overlay_functional_assay",
    "overlay_pm1_bp1",
    "overlay_pm3_in_trans",
    "overlay_protein_length",
    "overlay_ps1_splicing",
    "overlay_pvs1_lof",
    "overlay_pvs1_splicing",
    "overlay_segregation",
    "overlay_source_review",
]
