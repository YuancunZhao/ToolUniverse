"""PVS1 Loss-of-Function overlay tool.

Per ClinGen SVI PVS1 decision tree (Abou Tayoun 2018, PMID:30192042).
"""

from __future__ import annotations
from typing import Any
from .base import output_template, vcep_deferred_template


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
    """PVS1 strength per ClinGen SVI decision tree (Abou Tayoun 2018, PMID:30192042)."""
    if vcep_override:
        return vcep_deferred_template(
            "PVS1",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )

    vt = variant_type.lower().strip()

    if vt not in ("null", "frameshift", "nonsense", "splice", "canonical_splice"):
        return output_template("PVS1", "not_met", status="not_applicable",
            route_outcome="overlay_not_applicable",
            reason=f"PVS1 requires null variant (nonsense/frameshift/canonical splice). Got: {vt}.")

    if not gene_lof_mechanism:
        return output_template("PVS1", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="Gene LOF mechanism not confirmed.",
            next_action="Check ClinGen gene-disease validity.")

    if ar_disease and not second_allele_found:
        return output_template("PVS1", "not_applicable_ar_heterozygous",
            status="not_assessed", route_outcome="overlay_not_assessed",
            reason="Autosomal recessive disease with single heterozygous null variant. "
                   "PVS1 requires biallelic status. Search for second pathogenic allele.",
            next_action="Sequence full gene for second allele; check CNV for deletion/duplication.")

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
        return output_template("PVS1", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="Canonical splice variant but NMD prediction unavailable. "
                   "PVS1 strength assignment requires NMD prediction. "
                   "Do NOT default to full PVS1 for canonical ±1,2 positions "
                   "without NMD confirmation.",
            source_of_truth="VEP, SpliceAI",
            next_action="Provide NMD prediction or RNA evidence before PVS1 assessment.")

    if nmd_predicted is True:
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

        return output_template("PVS1", "PVS1",
            reason="NMD predicted for null variant in LOF-mechanism gene. PVS1 applies.",
            source_of_truth="VEP, NMD prediction, ClinGen")

    elif nmd_predicted is False:
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

    return output_template("PVS1", "not_assessed", status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason=f"Null variant ({vt}) in LOF-mechanism gene but NMD prediction unavailable. "
               "PVS1 strength assignment requires NMD prediction. "
               "Do NOT default to PVS1 without confirming NMD.",
        source_of_truth="ClinGen, gnomAD constraint",
        next_action="Provide NMD prediction (from VEP or manual assessment) before PVS1 assessment.")
