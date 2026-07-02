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
    phenotype_highly_specific: bool = False,
    phenotype_consistent: bool = False,
    genetic_heterogeneity_low: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """PS2/PM6 per SVI De Novo Criteria v1.1 (PMID:38103545).
    LLM input: from clinical report / published case literature.
    2pt=PS2, 1pt=PS2_Moderate, 0pt=PM6, not de novo=not_assessed.
    """
    from .base import output_template
    if vcep_override:
        return output_template("PS2/PM6", vcep_override, reason=f"VCEP: {vcep_override}")
    if not de_novo_confirmed:
        return output_template("PS2/PM6", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No de novo evidence or variant is inherited.",
            next_action="Trio testing required.")
    if not paternity_confirmed:
        return output_template("PM6", "PM6",
            reason="De novo observed without confirmed parentage → PM6.",
            source_of_truth="Trio testing")
    pts = 2 if phenotype_highly_specific else (1 if phenotype_consistent else 0)
    if genetic_heterogeneity_low and pts > 0:
        pts = min(pts + 1, 2)
    if pts >= 2:
        return output_template("PS2", "PS2",
            reason=f"De novo + parentage confirmed, phenotype score {pts}/2 → PS2.",
            source_of_truth="Trio testing")
    if pts == 1:
        return output_template("PS2", "PS2_Moderate",
            reason=f"De novo + parentage confirmed, phenotype score {pts}/2 → PS2_Moderate.",
            source_of_truth="Trio testing")
    return output_template("PM6", "PM6",
        reason="De novo + parentage confirmed but phenotype insufficient → PM6.",
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
    nmd_predicted: bool | None = None,
    exon_position: str = "",
    truncated_region_percent: float = 100.0,
    region_criticality: str = "unknown",
    rescue_transcript: bool = False,
    spliceai_dl: float | None = None,
    ar_disease: bool = False,
    second_allele_found: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """PVS1 strength per ClinGen SVI decision tree (Abou Tayoun 2018, PMID:30192042).

    Args:
        variant_type: null/frameshift/nonsense/splice/canonical_splice
        gene_lof_mechanism: LOF established as disease mechanism
        lof_intolerant: gnomAD pLI >= 0.9 or LOEUF < 0.35
        nmd_predicted: NMD predicted (None = unknown, use defaults)
        exon_position: last/penultimate/middle/first (for NMD prediction)
        truncated_region_percent: % of protein removed by truncation
        region_criticality: critical/important/unknown (for biologically relevant regions)
        rescue_transcript: rescue transcript or alternative initiation exists
        spliceai_dl: SpliceAI donor loss delta score (for splice variants)
        ar_disease: autosomal recessive disease
        second_allele_found: second pathogenic allele confirmed (for AR)
        vcep_override: VCEP-specific rule name
    """
    from .base import output_template
    if vcep_override:
        return output_template("PVS1", vcep_override, reason=f"VCEP: {vcep_override}")

    vt = variant_type.lower().strip()

    # === Table 1: Applicability Gate ===
    if vt not in ("null", "frameshift", "nonsense", "splice", "canonical_splice"):
        return output_template("PVS1", "not_met", status="not_applicable",
            route_outcome="overlay_not_applicable",
            reason=f"PVS1 requires null variant (nonsense/frameshift/canonical splice). Got: {vt}.")

    if not gene_lof_mechanism:
        return output_template("PVS1", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="Gene LOF mechanism not confirmed.",
            next_action="Check ClinGen gene-disease validity.")

    # === AR disease: single heterozygous null variant ===
    if ar_disease and not second_allele_found:
        return output_template("PVS1", "not_applicable_ar_heterozygous",
            status="not_assessed", route_outcome="overlay_not_assessed",
            reason="Autosomal recessive disease with single heterozygous null variant. "
                   "PVS1 requires biallelic status. Search for second pathogenic allele.",
            next_action="Sequence full gene for second allele; check CNV for deletion/duplication.")

    # === Splice variants: check SpliceAI before proceeding ===
    if vt in ("splice", "canonical_splice"):
        if spliceai_dl is not None and spliceai_dl < 0.2:
            return output_template("PVS1", "not_met", status="not_applicable",
                route_outcome="overlay_not_applicable",
                reason=f"SpliceAI donor loss={spliceai_dl:.2f} (<0.2). "
                       "Computational prediction does not support splice disruption. "
                       "RNA evidence recommended.",
                next_action="Perform RT-PCR/minigene assay to confirm splicing impact.")
        if nmd_predicted is False:
            return output_template("PVS1", "PVS1_Supporting",
                reason="Canonical splice variant but NMD not predicted. "
                       "Protein may retain partial function. "
                       "Per PVS1 decision tree: PTC not predicted to undergo NMD → downgrade.",
                source_of_truth="SpliceAI, VEP")
        if nmd_predicted is True:
            return output_template("PVS1", "PVS1",
                reason="Canonical splice variant predicted to cause NMD. "
                       "Full PVS1 strength applies.",
                source_of_truth="SpliceAI, VEP, NMD prediction")
        # NMD unknown — default to full strength for canonical splice
        return output_template("PVS1", "PVS1",
            reason="Canonical splice variant. NMD prediction unavailable — "
                   "defaulting to full PVS1 for canonical ±1,2 positions.",
            source_of_truth="VEP, SpliceAI")

    # === NMD Decision Branch ===
    if nmd_predicted is True:
        # NMD predicted → check exon location
        if exon_position == "last" or truncated_region_percent < 10:
            return output_template("PVS1", "PVS1_Moderate",
                reason=f"NMD predicted but PTC in last exon or truncation <10% ({truncated_region_percent:.1f}%). "
                       "Per PVS1 decision tree: downgrade to PVS1_Moderate.",
                source_of_truth="VEP, NMD prediction")

        if region_criticality == "critical" and truncated_region_percent >= 10:
            return output_template("PVS1", "PVS1",
                reason=f"NMD predicted. Truncation removes {truncated_region_percent:.0f}% "
                       "including a critical functional domain. PVS1 at full strength.",
                source_of_truth="VEP, InterPro")

        if rescue_transcript:
            return output_template("PVS1", "PVS1_Supporting",
                reason="NMD predicted but rescue transcript or alternative "
                       "initiation exists. Downgrade to PVS1_Supporting.",
                source_of_truth="literature, VEP")

        # NMD predicted, standard case
        return output_template("PVS1", "PVS1",
            reason="NMD predicted for null variant in LOF-mechanism gene. PVS1 applies.",
            source_of_truth="VEP, NMD prediction, ClinGen")

    elif nmd_predicted is False:
        # NMD not predicted → truncated/altered region assessment
        if truncated_region_percent >= 10:
            if region_criticality == "critical":
                return output_template("PVS1", "PVS1_Strong",
                    reason=f"NMD not predicted but truncation removes {truncated_region_percent:.0f}% "
                           "including critical domain. PVS1_Strong per decision tree.",
                    source_of_truth="VEP, InterPro")
            else:
                return output_template("PVS1", "PVS1_Moderate",
                    reason=f"NMD not predicted. Truncation removes {truncated_region_percent:.0f}% "
                           "but region criticality unknown. PVS1_Moderate per decision tree.",
                    source_of_truth="VEP")
        else:
            return output_template("PVS1", "PVS1_Supporting",
                reason=f"NMD not predicted and truncation <10% ({truncated_region_percent:.1f}%). "
                       "PVS1_Supporting per decision tree.",
                source_of_truth="VEP")

    # NMD unknown — use defaults
    if "nonsense" in vt or "frameshift" in vt:
        strength = "PVS1" if lof_intolerant else "PVS1_Strong"
        return output_template("PVS1", strength,
            reason=f"Null variant ({vt}) in LOF-mechanism gene. "
                   f"LOF intolerance: {lof_intolerant}. "
                   "NMD prediction unavailable — assuming standard PVS1.",
            source_of_truth="ClinGen, gnomAD constraint")

    return output_template("PVS1", "not_assessed", status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason=f"Insufficient data to complete PVS1 decision tree for {vt}.",
        next_action="Provide NMD prediction, exon position, and region information.")


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
